"""
core/ipd_management.py - Core Engine for Phase 46: IPD Inpatient Bed Management & Nursing Charting.
Handles ward occupancy management, admission/discharge workflows, and bedside Panchakarma rounds charting.
"""

import time
import uuid
import sqlite3
from typing import Optional, List
from core.database import get_sqlite_connection, append_audit_log
from models.ipd_management import (
    IpdBedStatus,
    BedAllocationCreate,
    BedAllocationRecord,
    NursingChartCreate,
    NursingChartRecord,
)
from models.schemas import UserResponse


class IpdManagementError(Exception):
    pass


def allocate_ipd_bed(
    req: BedAllocationCreate,
    current_user: Optional[UserResponse] = None,
    conn: Optional[sqlite3.Connection] = None
) -> BedAllocationRecord:
    """Admits a patient and allocates an IPD hospital bed."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        # Check if bed is already occupied
        cursor.execute(
            """
            SELECT allocation_id FROM ipd_bed_allocations
            WHERE ward_name = ? AND bed_number = ? AND status = ?;
            """,
            (req.ward_name, req.bed_number, IpdBedStatus.OCCUPIED.value)
        )
        if cursor.fetchone():
            raise IpdManagementError(f"Bed '{req.bed_number}' in ward '{req.ward_name}' is currently occupied.")

        allocation_id = f"ipd-{uuid.uuid4().hex[:12]}"
        now = int(time.time())

        cursor.execute(
            """
            INSERT INTO ipd_bed_allocations (
                allocation_id, patient_id, hospital_id, ward_name, bed_number,
                admission_timestamp, discharge_timestamp, status, attending_rmp_arn
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?);
            """,
            (
                allocation_id,
                req.patient_id,
                req.hospital_id,
                req.ward_name,
                req.bed_number,
                now,
                IpdBedStatus.OCCUPIED.value,
                req.attending_rmp_arn,
            )
        )

        user_id = current_user.user_id if current_user else req.attending_rmp_arn
        append_audit_log(
            conn,
            req.hospital_id,
            user_id,
            "ALLOCATE_IPD_BED",
            "IPD_BED_ALLOCATION",
            allocation_id,
            {
                "patient_id": req.patient_id,
                "ward": req.ward_name,
                "bed": req.bed_number,
                "arn": req.attending_rmp_arn
            }
        )
        conn.commit()

        return BedAllocationRecord(
            allocation_id=allocation_id,
            patient_id=req.patient_id,
            hospital_id=req.hospital_id,
            ward_name=req.ward_name,
            bed_number=req.bed_number,
            admission_timestamp=now,
            discharge_timestamp=None,
            status=IpdBedStatus.OCCUPIED,
            attending_rmp_arn=req.attending_rmp_arn
        )
    finally:
        if should_close:
            conn.close()


def discharge_ipd_patient(
    allocation_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> BedAllocationRecord:
    """Discharges a patient and marks the bed allocation as DISCHARGED."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        now = int(time.time())
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE ipd_bed_allocations
            SET status = ?, discharge_timestamp = ?
            WHERE allocation_id = ?;
            """,
            (IpdBedStatus.DISCHARGED.value, now, allocation_id)
        )
        conn.commit()

        cursor.execute("SELECT * FROM ipd_bed_allocations WHERE allocation_id = ?;", (allocation_id,))
        row = cursor.fetchone()
        if not row:
            raise IpdManagementError(f"Allocation '{allocation_id}' not found.")

        return BedAllocationRecord(
            allocation_id=row["allocation_id"],
            patient_id=row["patient_id"],
            hospital_id=row["hospital_id"],
            ward_name=row["ward_name"],
            bed_number=row["bed_number"],
            admission_timestamp=row["admission_timestamp"],
            discharge_timestamp=row["discharge_timestamp"],
            status=IpdBedStatus(row["status"]),
            attending_rmp_arn=row["attending_rmp_arn"]
        )
    finally:
        if should_close:
            conn.close()


def record_nursing_chart(
    req: NursingChartCreate,
    current_user: Optional[UserResponse] = None,
    conn: Optional[sqlite3.Connection] = None
) -> NursingChartRecord:
    """Records daily bedside vital signs and Panchakarma Vega monitoring by nursing staff."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM ipd_bed_allocations WHERE allocation_id = ?;", (req.allocation_id,))
        alloc = cursor.fetchone()
        if not alloc:
            raise IpdManagementError(f"Allocation '{req.allocation_id}' not found.")
        if alloc["status"] != IpdBedStatus.OCCUPIED.value:
            raise IpdManagementError(f"Allocation '{req.allocation_id}' is not in active OCCUPIED status.")

        chart_id = f"nrs-{uuid.uuid4().hex[:12]}"
        now = int(time.time())

        cursor.execute(
            """
            INSERT INTO panchakarma_daily_nursing_charts (
                chart_id, allocation_id, patient_id, vital_bp_systolic,
                vital_bp_diastolic, vital_pulse_bpm, panchakarma_therapy_administered,
                vega_count, jeerna_ahara_lakshana, nursing_notes, nurse_name, charted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                chart_id,
                req.allocation_id,
                req.patient_id,
                req.vital_bp_systolic,
                req.vital_bp_diastolic,
                req.vital_pulse_bpm,
                req.panchakarma_therapy_administered,
                req.vega_count,
                req.jeerna_ahara_lakshana,
                req.nursing_notes,
                req.nurse_name,
                now,
            )
        )
        conn.commit()

        return NursingChartRecord(
            chart_id=chart_id,
            allocation_id=req.allocation_id,
            patient_id=req.patient_id,
            vital_bp_systolic=req.vital_bp_systolic,
            vital_bp_diastolic=req.vital_bp_diastolic,
            vital_pulse_bpm=req.vital_pulse_bpm,
            panchakarma_therapy_administered=req.panchakarma_therapy_administered,
            vega_count=req.vega_count,
            jeerna_ahara_lakshana=req.jeerna_ahara_lakshana,
            nursing_notes=req.nursing_notes,
            nurse_name=req.nurse_name,
            charted_at=now
        )
    finally:
        if should_close:
            conn.close()


def get_ward_bed_occupancy(
    ward_name: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None
) -> List[BedAllocationRecord]:
    """Lists current occupied bed allocations."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        if ward_name:
            cursor.execute(
                """
                SELECT * FROM ipd_bed_allocations
                WHERE ward_name = ? AND status = ?
                ORDER BY admission_timestamp DESC;
                """,
                (ward_name, IpdBedStatus.OCCUPIED.value)
            )
        else:
            cursor.execute(
                """
                SELECT * FROM ipd_bed_allocations
                WHERE status = ?
                ORDER BY admission_timestamp DESC;
                """,
                (IpdBedStatus.OCCUPIED.value,)
            )
        rows = cursor.fetchall()
        return [
            BedAllocationRecord(
                allocation_id=r["allocation_id"],
                patient_id=r["patient_id"],
                hospital_id=r["hospital_id"],
                ward_name=r["ward_name"],
                bed_number=r["bed_number"],
                admission_timestamp=r["admission_timestamp"],
                discharge_timestamp=r["discharge_timestamp"],
                status=IpdBedStatus(r["status"]),
                attending_rmp_arn=r["attending_rmp_arn"]
            )
            for r in rows
        ]
    finally:
        if should_close:
            conn.close()


def get_patient_nursing_charts(
    allocation_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> List[NursingChartRecord]:
    """Retrieves nursing charts for an allocation."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM panchakarma_daily_nursing_charts
            WHERE allocation_id = ?
            ORDER BY charted_at DESC;
            """,
            (allocation_id,)
        )
        rows = cursor.fetchall()
        return [
            NursingChartRecord(
                chart_id=r["chart_id"],
                allocation_id=r["allocation_id"],
                patient_id=r["patient_id"],
                vital_bp_systolic=r["vital_bp_systolic"],
                vital_bp_diastolic=r["vital_bp_diastolic"],
                vital_pulse_bpm=r["vital_pulse_bpm"],
                panchakarma_therapy_administered=r["panchakarma_therapy_administered"],
                vega_count=r["vega_count"],
                jeerna_ahara_lakshana=r["jeerna_ahara_lakshana"],
                nursing_notes=r["nursing_notes"],
                nurse_name=r["nurse_name"],
                charted_at=r["charted_at"]
            )
            for r in rows
        ]
    finally:
        if should_close:
            conn.close()
