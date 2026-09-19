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
