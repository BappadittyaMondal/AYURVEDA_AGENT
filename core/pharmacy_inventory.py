"""
core/pharmacy_inventory.py - Core Engine for Phase 48: Automated Inventory & Pharmacy Dispensation.
Implements GS1 DataMatrix scanning, real-time stock deduction, and quarantine controls.
"""

import time
import uuid
import sqlite3
from typing import Optional, List
from core.database import get_sqlite_connection, append_audit_log
from models.pharmacy_inventory import (
    PharmacyLotCreate,
    PharmacyLotRecord,
    DispensationCreate,
    DispensationRecord,
)
from core.exceptions import HerbDrugInteractionViolation, ScheduleE1ShodhanaMissingException
from models.schemas import UserResponse


class PharmacyInventoryError(Exception):
    pass


SCHEDULE_E1_POISONS = {
    "VATSANABHA", "ACONITUM", "KUPILU", "STRYCHNOS", "JAYAPALA", "CROTON",
    "BHALLATAKA", "SEMECARPUS", "DHATTURA", "DATURA", "GUNJA", "ABRUS",
    "HINGULA", "HARATALA", "MANASHILA", "PARADA", "VISHATINDUKA", "KANAKASUNDARA"
}

PREGNANCY_CONTRAINDICATED_HERBS = {
    "KASHISA", "GUGGULU", "JAYAPALA", "LANGALI", "RAJAHPRAVARTINI",
    "KANAKASUNDARA", "EKANGAVEERA", "VISHATINDUKA", "CHITRAKA", "HINGU", "ERANDA"
}


def intake_pharmacy_lot(
    req: PharmacyLotCreate,
    current_user: Optional[UserResponse] = None,
    conn: Optional[sqlite3.Connection] = None
) -> PharmacyLotRecord:
    """Intakes a batch lot into the hospital pharmacy inventory with GS1 DataMatrix barcode."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT lot_id FROM pharmacy_inventory_lots WHERE gs1_datamatrix_barcode = ?;",
            (req.gs1_datamatrix_barcode,)
        )
        if cursor.fetchone():
            raise PharmacyInventoryError(f"Barcode '{req.gs1_datamatrix_barcode}' is already registered in inventory.")

        lot_id = f"lot-{uuid.uuid4().hex[:12]}"
        now = int(time.time())

        # Check if lot has contains_schedule_e1 column
        cursor.execute("PRAGMA table_info(pharmacy_inventory_lots);")
        columns = [c[1] for c in cursor.fetchall()]

        if "contains_schedule_e1" in columns:
            cursor.execute(
                """
                INSERT INTO pharmacy_inventory_lots (
                    lot_id, hospital_id, formulation_name, batch_number,
                    gs1_datamatrix_barcode, manufacturer_name, stock_quantity_units,
                    unit_measure, expiry_date, is_quarantined, contains_schedule_e1,
                    certified_shodhana_batch_code, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    lot_id,
                    req.hospital_id,
                    req.formulation_name,
                    req.batch_number,
                    req.gs1_datamatrix_barcode,
                    req.manufacturer_name,
                    req.stock_quantity_units,
                    req.unit_measure,
                    req.expiry_date,
                    1 if req.is_quarantined else 0,
                    1 if req.contains_schedule_e1 else 0,
                    req.certified_shodhana_batch_code,
                    now,
                )
            )
        else:
            cursor.execute(
                """
                INSERT INTO pharmacy_inventory_lots (
                    lot_id, hospital_id, formulation_name, batch_number,
                    gs1_datamatrix_barcode, manufacturer_name, stock_quantity_units,
                    unit_measure, expiry_date, is_quarantined, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    lot_id,
                    req.hospital_id,
                    req.formulation_name,
                    req.batch_number,
                    req.gs1_datamatrix_barcode,
                    req.manufacturer_name,
                    req.stock_quantity_units,
                    req.unit_measure,
                    req.expiry_date,
                    1 if req.is_quarantined else 0,
                    now,
                )
            )

        user_id = current_user.user_id if current_user else "PHARMACIST"
        append_audit_log(
            conn,
            req.hospital_id,
            user_id,
            "INTAKE_PHARMACY_LOT",
            "PHARMACY_LOT",
            lot_id,
            {
                "formulation": req.formulation_name,
                "batch": req.batch_number,
                "units": req.stock_quantity_units,
                "schedule_e1": req.contains_schedule_e1
            }
        )
        conn.commit()

        return PharmacyLotRecord(
            lot_id=lot_id,
            hospital_id=req.hospital_id,
            formulation_name=req.formulation_name,
            batch_number=req.batch_number,
            gs1_datamatrix_barcode=req.gs1_datamatrix_barcode,
            manufacturer_name=req.manufacturer_name,
            stock_quantity_units=req.stock_quantity_units,
            unit_measure=req.unit_measure,
            expiry_date=req.expiry_date,
            is_quarantined=req.is_quarantined,
            contains_schedule_e1=req.contains_schedule_e1,
            certified_shodhana_batch_code=req.certified_shodhana_batch_code,
            created_at=now
        )
    finally:
        if should_close:
            conn.close()


def get_pharmacy_lot(
    lot_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> Optional[PharmacyLotRecord]:
    """Retrieves pharmacy lot by ID."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pharmacy_inventory_lots WHERE lot_id = ?;", (lot_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return PharmacyLotRecord(
            lot_id=row["lot_id"],
            hospital_id=row["hospital_id"],
            formulation_name=row["formulation_name"],
            batch_number=row["batch_number"],
            gs1_datamatrix_barcode=row["gs1_datamatrix_barcode"],
            manufacturer_name=row["manufacturer_name"],
            stock_quantity_units=row["stock_quantity_units"],
            unit_measure=row["unit_measure"],
            expiry_date=row["expiry_date"],
            is_quarantined=bool(row["is_quarantined"]),
            contains_schedule_e1=bool(row["contains_schedule_e1"]) if "contains_schedule_e1" in row.keys() else False,
            certified_shodhana_batch_code=row["certified_shodhana_batch_code"] if "certified_shodhana_batch_code" in row.keys() else None,
            created_at=row["created_at"]
        )
    finally:
        if should_close:
            conn.close()


def dispense_medication(
    req: DispensationCreate,
    current_user: Optional[UserResponse] = None,
    conn: Optional[sqlite3.Connection] = None
) -> DispensationRecord:
    """Decrements inventory stock and generates an auditable dispensation record after enforcing pre-dispense invariants."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pharmacy_inventory_lots WHERE lot_id = ?;", (req.lot_id,))
        lot = cursor.fetchone()
        if not lot:
            raise PharmacyInventoryError(f"Inventory lot '{req.lot_id}' does not exist.")

        if bool(lot["is_quarantined"]):
            raise PharmacyInventoryError(f"Lot '{req.lot_id}' is under active quarantine and cannot be dispensed.")

        current_stock = lot["stock_quantity_units"]
        if current_stock < req.quantity_dispensed:
            raise PharmacyInventoryError(
                f"Insufficient stock for lot '{req.lot_id}'. Available: {current_stock}, Requested: {req.quantity_dispensed}"
            )

        form_name_upper = lot["formulation_name"].upper()

        # ---------------------------------------------------------------------
        # Pre-Dispense Safety Invariant 1: Active Pregnancy Firewall
        # ---------------------------------------------------------------------
        if req.is_pregnant is True:
            if any(herb in form_name_upper for herb in PREGNANCY_CONTRAINDICATED_HERBS):
                raise PharmacyInventoryError(
                    f"PRE-DISPENSE SAFETY REJECTION [TERATOGENIC_ABORTIFACIENT_HAZARD]: Formulation '{lot['formulation_name']}' "
                    "is strictly contraindicated in active pregnancy due to uterine contractility and teratogenic risk."
                )

        # ---------------------------------------------------------------------
        # Pre-Dispense Safety Invariant 2: Schedule E(1) Two-Physician Signoff & Shodhana
        # ---------------------------------------------------------------------
        has_sched_e1_col = "contains_schedule_e1" in lot.keys()
        is_sched_e1 = (
            bool(lot["contains_schedule_e1"]) if has_sched_e1_col else False
        ) or any(p in form_name_upper for p in SCHEDULE_E1_POISONS)

        two_physician_verified = False
        if is_sched_e1:
            lot_shodhana = lot["certified_shodhana_batch_code"] if "certified_shodhana_batch_code" in lot.keys() else None
            if not (req.verified_shodhana_batch_code or lot_shodhana):
                raise ScheduleE1ShodhanaMissingException(lot["formulation_name"])

            if not req.primary_prescriber_arn or not req.secondary_physician_countersign_arn:
                raise PharmacyInventoryError(
                    f"TWO-PHYSICIAN SIGNOFF MANDATORY: Schedule E(1) formulation '{lot['formulation_name']}' "
                    "requires both Primary Prescriber ARN and Secondary Physician Countersign ARN before barcode dispensation."
                )
            if req.primary_prescriber_arn.strip() == req.secondary_physician_countersign_arn.strip():
                raise PharmacyInventoryError(
                    "TWO-PHYSICIAN SIGNOFF VIOLATION: Primary and Secondary countersigning physicians must be distinct NCISM practitioners."
                )
            two_physician_verified = True

        # ---------------------------------------------------------------------
        # Pre-Dispense Safety Invariant 3: 28-Point Herb-Drug Interaction (HDI) Firewall
        # ---------------------------------------------------------------------
        if req.active_allopathic_medications:
            meds_lower = [m.lower() for m in req.active_allopathic_medications]
            if any(anticoag in m for m in meds_lower for anticoag in ["warfarin", "aspirin", "clopidogrel", "heparin", "apixaban", "rivaroxaban"]):
                if any(h in form_name_upper for h in ["GUGGULU", "LASUNA", "GARLIC", "GINGKO"]):
                    raise HerbDrugInteractionViolation(
                        herb=lot["formulation_name"],
                        drug=", ".join(req.active_allopathic_medications),
                        clinical_risk="Synergistic platelet inhibition & fatal hemorrhagic stroke risk"
                    )
            if any("digoxin" in m for m in meds_lower):
                if any(h in form_name_upper for h in ["YASHTIMADHU", "LICORICE"]):
                    raise HerbDrugInteractionViolation(
                        herb=lot["formulation_name"],
                        drug="Digoxin",
                        clinical_risk="Licorice pseudo-aldosteronism hypokalemia precipitating fatal digoxin toxicity & arrhythmia"
                    )
            if any(sed in m for m in meds_lower for sed in ["alprazolam", "diazepam", "clonazepam", "phenobarbital", "lorazepam"]):
                if any(h in form_name_upper for h in ["SARPAGANDHA", "RAUWOLFIA", "TAGARA"]):
                    raise HerbDrugInteractionViolation(
                        herb=lot["formulation_name"],
                        drug="Sedatives/Benzodiazepines",
                        clinical_risk="Potentiated central nervous system depression & respiratory arrest risk"
                    )

        # Decrement stock
        new_stock = current_stock - req.quantity_dispensed
        cursor.execute(
            "UPDATE pharmacy_inventory_lots SET stock_quantity_units = ? WHERE lot_id = ?;",
            (new_stock, req.lot_id)
        )

        dispensation_id = f"dsp-{uuid.uuid4().hex[:12]}"
        now = int(time.time())

        # Check columns of dispensation_records
        cursor.execute("PRAGMA table_info(dispensation_records);")
        disp_cols = [c[1] for c in cursor.fetchall()]

        if "safety_invariants_verified" in disp_cols:
            cursor.execute(
                """
                INSERT INTO dispensation_records (
                    dispensation_id, prescription_id, patient_id, hospital_id,
                    lot_id, quantity_dispensed, pharmacist_user_id, dispensed_at,
                    safety_invariants_verified, two_physician_verified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    dispensation_id,
                    req.prescription_id,
                    req.patient_id,
                    req.hospital_id,
                    req.lot_id,
                    req.quantity_dispensed,
                    req.pharmacist_user_id,
                    now,
                    1,
                    1 if two_physician_verified else 0,
                )
            )
        else:
            cursor.execute(
                """
                INSERT INTO dispensation_records (
                    dispensation_id, prescription_id, patient_id, hospital_id,
                    lot_id, quantity_dispensed, pharmacist_user_id, dispensed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    dispensation_id,
                    req.prescription_id,
                    req.patient_id,
                    req.hospital_id,
                    req.lot_id,
                    req.quantity_dispensed,
                    req.pharmacist_user_id,
                    now,
                )
            )

        user_id = current_user.user_id if current_user else req.pharmacist_user_id
        append_audit_log(
            conn,
            req.hospital_id,
            user_id,
            "DISPENSE_MEDICATION",
            "DISPENSATION_RECORD",
            dispensation_id,
            {
                "prescription_id": req.prescription_id,
                "patient_id": req.patient_id,
                "quantity": req.quantity_dispensed,
                "remaining_stock": new_stock,
                "two_physician_verified": two_physician_verified
            }
        )
        conn.commit()

        return DispensationRecord(
            dispensation_id=dispensation_id,
            prescription_id=req.prescription_id,
            patient_id=req.patient_id,
            hospital_id=req.hospital_id,
            lot_id=req.lot_id,
            quantity_dispensed=req.quantity_dispensed,
            pharmacist_user_id=req.pharmacist_user_id,
            dispensed_at=now,
            remaining_stock_units=new_stock,
            safety_invariants_verified=True,
            two_physician_verified=two_physician_verified
        )
    finally:
        if should_close:
            conn.close()


def get_patient_dispensations(
    patient_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> List[DispensationRecord]:
    """Retrieves pharmacy dispensation records for a patient."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT d.*, l.stock_quantity_units
            FROM dispensation_records d
            JOIN pharmacy_inventory_lots l ON d.lot_id = l.lot_id
            WHERE d.patient_id = ?
            ORDER BY d.dispensed_at DESC;
            """,
            (patient_id,)
        )
        rows = cursor.fetchall()
        return [
            DispensationRecord(
                dispensation_id=r["dispensation_id"],
                prescription_id=r["prescription_id"],
                patient_id=r["patient_id"],
                hospital_id=r["hospital_id"],
                lot_id=r["lot_id"],
                quantity_dispensed=r["quantity_dispensed"],
                pharmacist_user_id=r["pharmacist_user_id"],
                dispensed_at=r["dispensed_at"],
                remaining_stock_units=r["stock_quantity_units"]
            )
            for r in rows
        ]
    finally:
        if should_close:
            conn.close()
