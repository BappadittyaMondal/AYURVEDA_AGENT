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
from models.schemas import UserResponse


class PharmacyInventoryError(Exception):
    pass


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
                "units": req.stock_quantity_units
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
    """Decrements inventory stock and generates an auditable dispensation record."""
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

        new_stock = current_stock - req.quantity_dispensed
        cursor.execute(
            "UPDATE pharmacy_inventory_lots SET stock_quantity_units = ? WHERE lot_id = ?;",
            (new_stock, req.lot_id)
        )

        dispensation_id = f"dsp-{uuid.uuid4().hex[:12]}"
        now = int(time.time())

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
                "remaining_stock": new_stock
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
            remaining_stock_units=new_stock
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
