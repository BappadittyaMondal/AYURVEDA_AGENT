"""
Phase 38: Tele-AYUSH Remote Consultation & Digital e-Prescription Engine
========================================================================
Implements:
1. MoHFW Telemedicine Practice Guidelines session management (Table 82)
2. Tamper-evident cryptographic SHA-256 digital e-prescription generation (Table 83)
3. QR-code verification endpoint logic and pharmacy dispensation tracking
"""

import hashlib
import json
import sqlite3
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any

from core.database import get_sqlite_connection, append_audit_log
from models.tele_ayush import (
    TeleConsultationType,
    TeleSessionStatus,
    DispensationStatus,
    PrescribedItem,
    TeleConsultationCreate,
    TeleConsultationResponse,
    DigitalPrescriptionCreate,
    DigitalPrescriptionResponse,
    PrescriptionVerificationResponse,
)


def schedule_tele_consultation(
    req: TeleConsultationCreate,
    conn: Optional[sqlite3.Connection] = None
) -> TeleConsultationResponse:
    """Schedule a Tele-AYUSH video/audio clinical encounter."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        now = int(time.time())
        session_id = f"TELE-{now}-{uuid.uuid4().hex[:6].upper()}"

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tele_ayush_consultations (
                session_id, patient_id, hospital_id, physician_arn,
                scheduled_timestamp, started_timestamp, ended_timestamp,
                session_status, call_type, clinical_notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                session_id,
                req.patient_id,
                req.hospital_id,
                req.physician_arn,
                req.scheduled_timestamp,
                None,
                None,
                TeleSessionStatus.SCHEDULED.value,
                req.call_type.value,
                req.clinical_notes,
                now
            )
        )

        append_audit_log(
            conn,
            req.hospital_id,
            req.physician_arn,
            "SCHEDULE_TELE_CONSULTATION",
            "TELE_SESSION",
            session_id,
            {"patient_id": req.patient_id, "call_type": req.call_type.value}
        )
        conn.commit()

        return TeleConsultationResponse(
            session_id=session_id,
            patient_id=req.patient_id,
            hospital_id=req.hospital_id,
            physician_arn=req.physician_arn,
            scheduled_timestamp=req.scheduled_timestamp,
            started_timestamp=None,
            ended_timestamp=None,
            session_status=TeleSessionStatus.SCHEDULED,
            call_type=req.call_type,
            clinical_notes=req.clinical_notes,
            created_at=now
        )
    finally:
        if should_close:
            conn.close()


def issue_digital_eprescription(
    req: DigitalPrescriptionCreate,
    conn: Optional[sqlite3.Connection] = None
) -> DigitalPrescriptionResponse:
    """Issue tamper-evident cryptographic QR-verified digital prescription."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        now = int(time.time())
        rx_id = f"RX-AYUSH-{now}-{uuid.uuid4().hex[:6].upper()}"

        formulations_json = json.dumps([f.model_dump() for f in req.formulations], sort_keys=True)
        hash_payload = f"{rx_id}|{req.session_id}|{req.patient_id}|{req.physician_arn}|{formulations_json}|{now}"
        verification_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()
        qr_payload = f"https://ayush-grid.gov.in/verify-rx?id={rx_id}&h={verification_hash[:16]}"

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO digital_eprescriptions (
                prescription_id, session_id, patient_id, hospital_id,
                physician_arn, formulations_json, pathya_diet_instructions,
                verification_hash, qr_code_payload, dispensation_status, issued_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                rx_id,
                req.session_id,
                req.patient_id,
                req.hospital_id,
                req.physician_arn,
                formulations_json,
                req.pathya_diet_instructions,
                verification_hash,
                qr_payload,
                DispensationStatus.ISSUED.value,
                now
            )
        )

        # Mark tele-session completed
        cursor.execute(
            "UPDATE tele_ayush_consultations SET session_status = ?, ended_timestamp = ? WHERE session_id = ?;",
            (TeleSessionStatus.COMPLETED.value, now, req.session_id)
        )

        append_audit_log(
            conn,
            req.hospital_id,
            req.physician_arn,
            "ISSUE_DIGITAL_EPRESCRIPTION",
            "DIGITAL_PRESCRIPTION",
            rx_id,
            {"patient_id": req.patient_id, "session_id": req.session_id, "hash": verification_hash[:16]}
        )
        conn.commit()

        return DigitalPrescriptionResponse(
            prescription_id=rx_id,
            session_id=req.session_id,
            patient_id=req.patient_id,
            hospital_id=req.hospital_id,
            physician_arn=req.physician_arn,
            formulations=req.formulations,
            pathya_diet_instructions=req.pathya_diet_instructions,
            verification_hash=verification_hash,
            qr_code_payload=qr_payload,
            dispensation_status=DispensationStatus.ISSUED,
            issued_at=now
        )
    finally:
        if should_close:
            conn.close()


def verify_eprescription(
    prescription_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> PrescriptionVerificationResponse:
    """Verify cryptographic authenticity of a digital e-prescription."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM digital_eprescriptions WHERE prescription_id = ?;", (prescription_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Prescription '{prescription_id}' not found.")

        # Verify hash integrity
        expected_payload = f"{row['prescription_id']}|{row['session_id']}|{row['patient_id']}|{row['physician_arn']}|{row['formulations_json']}|{row['issued_at']}"
        expected_hash = hashlib.sha256(expected_payload.encode("utf-8")).hexdigest()
        is_authentic = (expected_hash == row["verification_hash"])

        return PrescriptionVerificationResponse(
            is_authentic=is_authentic,
            prescription_id=row["prescription_id"],
            physician_arn=row["physician_arn"],
            patient_id=row["patient_id"],
            issued_at=row["issued_at"],
            dispensation_status=DispensationStatus(row["dispensation_status"])
        )
    finally:
        if should_close:
            conn.close()
