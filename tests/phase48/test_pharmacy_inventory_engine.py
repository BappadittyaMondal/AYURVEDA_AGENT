"""
tests/phase48/test_pharmacy_inventory_engine.py - Unit tests for Phase 48 Pharmacy Inventory & Barcode Dispensation.
"""

import pytest
from core.database import get_sqlite_connection, init_database
from models.schemas import UserResponse
from core.security import ClinicalRole
from models.pharmacy_inventory import (
    PharmacyLotCreate,
    DispensationCreate,
)
from core.pharmacy_inventory import (
    intake_pharmacy_lot,
    get_pharmacy_lot,
    dispense_medication,
    get_patient_dispensations,
    PharmacyInventoryError,
)
from core.exceptions import HerbDrugInteractionViolation, ScheduleE1ShodhanaMissingException


@pytest.fixture
def conn():
    init_database()
    connection = get_sqlite_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO patients (
            patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("pat-pharma-test-01", "aiia-delhi-central-001", "Anand", "Verma", "1978-09-09", "MALE", "+919811001122", 1700000000)
    )
    cursor.execute("DELETE FROM dispensation_records WHERE patient_id = 'pat-pharma-test-01';")
    cursor.execute("DELETE FROM pharmacy_inventory_lots WHERE batch_number LIKE 'TEST-BATCH-%';")
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def rmp_user():
    return UserResponse(
        user_id="user-physician-001",
        hospital_id="aiia-delhi-central-001",
        username="physician_rmp",
        full_name="Dr. Ananya Sen",
        arn="ARN-NCISM-2015-8832",
        role=ClinicalRole.PHYSICIAN_RMP,
        is_active=True,
        created_at=1700000000
    )


def test_lot_intake_and_barcode_uniqueness(conn, rmp_user):
    req = PharmacyLotCreate(
        hospital_id="aiia-delhi-central-001",
        formulation_name="Chandraprabha Vati",
        batch_number="TEST-BATCH-CPV-01",
        gs1_datamatrix_barcode="(01)08901234567890(17)281231(10)CPV01",
        manufacturer_name="Indian Medicines Pharmaceutical Corporation Ltd (IMPCL)",
        stock_quantity_units=200,
        unit_measure="BOTTLE_60_TABS",
        expiry_date="2028-12-31",
        is_quarantined=False
    )
    lot = intake_pharmacy_lot(req, current_user=rmp_user, conn=conn)
    assert lot.lot_id.startswith("lot-")
    assert lot.stock_quantity_units == 200

    # Duplicate barcode rejection
    with pytest.raises(PharmacyInventoryError):
        intake_pharmacy_lot(req, current_user=rmp_user, conn=conn)


def test_dispensation_and_stock_deduction(conn, rmp_user):
    # Intake lot
    lot = intake_pharmacy_lot(
        PharmacyLotCreate(
            hospital_id="aiia-delhi-central-001",
            formulation_name="Triphala Guggulu",
            batch_number="TEST-BATCH-TPG-02",
            gs1_datamatrix_barcode="(01)08901234567890(17)281231(10)TPG02",
            manufacturer_name="IMPCL",
            stock_quantity_units=50,
            unit_measure="BOTTLE_60_TABS",
            expiry_date="2028-12-31",
            is_quarantined=False
        ),
        current_user=rmp_user,
        conn=conn
    )

    # Dispense 5 units
    disp_req = DispensationCreate(
        prescription_id="rx-test-001",
        patient_id="pat-pharma-test-01",
        hospital_id="aiia-delhi-central-001",
        lot_id=lot.lot_id,
        quantity_dispensed=5,
        pharmacist_user_id="user-pharmacist-001"
    )
    disp = dispense_medication(disp_req, current_user=rmp_user, conn=conn)
    assert disp.dispensation_id.startswith("dsp-")
    assert disp.remaining_stock_units == 45

    # Check updated lot stock
    updated_lot = get_pharmacy_lot(lot.lot_id, conn=conn)
    assert updated_lot.stock_quantity_units == 45

    # Attempt to dispense more than remaining stock -> Error
    excess_req = DispensationCreate(
        prescription_id="rx-test-002",
        patient_id="pat-pharma-test-01",
        hospital_id="aiia-delhi-central-001",
        lot_id=lot.lot_id,
        quantity_dispensed=100,
        pharmacist_user_id="user-pharmacist-001"
    )
    with pytest.raises(PharmacyInventoryError):
        dispense_medication(excess_req, current_user=rmp_user, conn=conn)


def test_dispensation_pregnancy_invariant_blocks_contraindicated_herbs(conn, rmp_user):
    """Verify that formulations with uterine stimulants/abortifacients are blocked in active pregnancy."""
    lot = intake_pharmacy_lot(
        PharmacyLotCreate(
            hospital_id="aiia-delhi-central-001",
            formulation_name="Kanchanara Guggulu",
            batch_number="TEST-BATCH-KCG-03",
            gs1_datamatrix_barcode="(01)08901234567890(17)281231(10)KCG03",
            manufacturer_name="IMPCL",
            stock_quantity_units=30,
            unit_measure="BOTTLE_60_TABS",
            expiry_date="2028-12-31",
            is_quarantined=False
        ),
        current_user=rmp_user,
        conn=conn
    )

    # Attempt to dispense to pregnant patient -> Rejection
    disp_preg = DispensationCreate(
        prescription_id="rx-preg-001",
        patient_id="pat-pharma-test-01",
        hospital_id="aiia-delhi-central-001",
        lot_id=lot.lot_id,
        quantity_dispensed=1,
        pharmacist_user_id="user-pharmacist-001",
        is_pregnant=True
    )
    with pytest.raises(PharmacyInventoryError) as exc_info:
        dispense_medication(disp_preg, current_user=rmp_user, conn=conn)
    assert "TERATOGENIC_ABORTIFACIENT_HAZARD" in str(exc_info.value)

    # Dispense to non-pregnant patient -> Allowed
    disp_non_preg = DispensationCreate(
        prescription_id="rx-non-preg-001",
        patient_id="pat-pharma-test-01",
        hospital_id="aiia-delhi-central-001",
        lot_id=lot.lot_id,
        quantity_dispensed=1,
        pharmacist_user_id="user-pharmacist-001",
        is_pregnant=False
    )
    res = dispense_medication(disp_non_preg, current_user=rmp_user, conn=conn)
    assert res.dispensation_id.startswith("dsp-")


def test_dispensation_schedule_e1_shodhana_and_two_physician_firewall(conn, rmp_user):
    """Verify Schedule E(1) requires certified Shodhana lot and two distinct physician countersignatures."""
    lot = intake_pharmacy_lot(
        PharmacyLotCreate(
            hospital_id="aiia-delhi-central-001",
            formulation_name="Vatsanabha Churna",
            batch_number="TEST-BATCH-VAT-04",
            gs1_datamatrix_barcode="(01)08901234567890(17)281231(10)VAT04",
            manufacturer_name="IMPCL",
            stock_quantity_units=20,
            unit_measure="JAR_100G",
            expiry_date="2028-12-31",
            is_quarantined=False,
            contains_schedule_e1=True
        ),
        current_user=rmp_user,
        conn=conn
    )

    # 1. Missing Shodhana -> Raises ScheduleE1ShodhanaMissingException
    disp_no_shodhana = DispensationCreate(
        prescription_id="rx-e1-001",
        patient_id="pat-pharma-test-01",
        hospital_id="aiia-delhi-central-001",
        lot_id=lot.lot_id,
        quantity_dispensed=1,
        pharmacist_user_id="user-pharmacist-001",
        primary_prescriber_arn="ARN-NCISM-2015-8832",
        secondary_physician_countersign_arn="ARN-NCISM-2018-4421"
    )
    with pytest.raises(ScheduleE1ShodhanaMissingException):
        dispense_medication(disp_no_shodhana, current_user=rmp_user, conn=conn)

    # 2. Missing secondary physician countersignature
    disp_missing_counter = DispensationCreate(
        prescription_id="rx-e1-002",
        patient_id="pat-pharma-test-01",
        hospital_id="aiia-delhi-central-001",
        lot_id=lot.lot_id,
        quantity_dispensed=1,
        pharmacist_user_id="user-pharmacist-001",
        verified_shodhana_batch_code="SHODHANA-GOMUTRA-SWEDANA-2026",
        primary_prescriber_arn="ARN-NCISM-2015-8832",
        secondary_physician_countersign_arn=None
    )
    with pytest.raises(PharmacyInventoryError) as exc_info:
        dispense_medication(disp_missing_counter, current_user=rmp_user, conn=conn)
    assert "TWO-PHYSICIAN SIGNOFF MANDATORY" in str(exc_info.value)

    # 3. Same physician ARN for both primary and secondary
    disp_same_physician = DispensationCreate(
        prescription_id="rx-e1-003",
        patient_id="pat-pharma-test-01",
        hospital_id="aiia-delhi-central-001",
        lot_id=lot.lot_id,
        quantity_dispensed=1,
        pharmacist_user_id="user-pharmacist-001",
        verified_shodhana_batch_code="SHODHANA-GOMUTRA-SWEDANA-2026",
        primary_prescriber_arn="ARN-NCISM-2015-8832",
        secondary_physician_countersign_arn="ARN-NCISM-2015-8832"
    )
    with pytest.raises(PharmacyInventoryError) as exc_info:
        dispense_medication(disp_same_physician, current_user=rmp_user, conn=conn)
    assert "TWO-PHYSICIAN SIGNOFF VIOLATION" in str(exc_info.value)

    # 4. Valid Shodhana + Two distinct RMP physicians -> Success
    disp_valid_e1 = DispensationCreate(
        prescription_id="rx-e1-004",
        patient_id="pat-pharma-test-01",
        hospital_id="aiia-delhi-central-001",
        lot_id=lot.lot_id,
        quantity_dispensed=1,
        pharmacist_user_id="user-pharmacist-001",
        verified_shodhana_batch_code="SHODHANA-GOMUTRA-SWEDANA-2026",
        primary_prescriber_arn="ARN-NCISM-2015-8832",
        secondary_physician_countersign_arn="ARN-NCISM-2018-4421"
    )
    rec = dispense_medication(disp_valid_e1, current_user=rmp_user, conn=conn)
    assert rec.dispensation_id.startswith("dsp-")
    assert rec.two_physician_verified is True
    assert rec.safety_invariants_verified is True


def test_dispensation_herb_drug_interaction_firewall(conn, rmp_user):
    """Verify 28-point Herb-Drug Interaction firewall halts dangerous co-prescriptions."""
    # 1. Guggulu + Warfarin / Aspirin
    lot_guggulu = intake_pharmacy_lot(
        PharmacyLotCreate(
            hospital_id="aiia-delhi-central-001",
            formulation_name="Yograj Guggulu",
            batch_number="TEST-BATCH-YGJ-05",
            gs1_datamatrix_barcode="(01)08901234567890(17)281231(10)YGJ05",
            manufacturer_name="IMPCL",
            stock_quantity_units=25,
            unit_measure="BOTTLE_60_TABS",
            expiry_date="2028-12-31",
            is_quarantined=False
        ),
        current_user=rmp_user,
        conn=conn
    )
    disp_warfarin = DispensationCreate(
        prescription_id="rx-hdi-001",
        patient_id="pat-pharma-test-01",
        hospital_id="aiia-delhi-central-001",
        lot_id=lot_guggulu.lot_id,
        quantity_dispensed=1,
        pharmacist_user_id="user-pharmacist-001",
        active_allopathic_medications=["Warfarin 5mg daily"]
    )
    with pytest.raises(HerbDrugInteractionViolation) as exc_info:
        dispense_medication(disp_warfarin, current_user=rmp_user, conn=conn)
    assert "Synergistic platelet inhibition" in str(exc_info.value)

    # 2. Yashtimadhu + Digoxin
    lot_yashtimadhu = intake_pharmacy_lot(
        PharmacyLotCreate(
            hospital_id="aiia-delhi-central-001",
            formulation_name="Yashtimadhu Churna",
            batch_number="TEST-BATCH-YST-06",
            gs1_datamatrix_barcode="(01)08901234567890(17)281231(10)YST06",
            manufacturer_name="IMPCL",
            stock_quantity_units=25,
            unit_measure="JAR_100G",
            expiry_date="2028-12-31",
            is_quarantined=False
        ),
        current_user=rmp_user,
        conn=conn
    )
    disp_digoxin = DispensationCreate(
        prescription_id="rx-hdi-002",
        patient_id="pat-pharma-test-01",
        hospital_id="aiia-delhi-central-001",
        lot_id=lot_yashtimadhu.lot_id,
        quantity_dispensed=1,
        pharmacist_user_id="user-pharmacist-001",
        active_allopathic_medications=["Digoxin 0.25mg"]
    )
    with pytest.raises(HerbDrugInteractionViolation) as exc_info:
        dispense_medication(disp_digoxin, current_user=rmp_user, conn=conn)
    assert "hypokalemia" in str(exc_info.value)

