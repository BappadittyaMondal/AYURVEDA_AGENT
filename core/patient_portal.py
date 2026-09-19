"""
core/patient_portal.py - Core Engine for Phase 41: Patient Portal & PWA Interface.
Handles patient authentication, daily lifestyle/pathya adherence tracking, and holistic summary generation.
"""

import time
import uuid
import sqlite3
from typing import Optional, List
from core.database import get_sqlite_connection, append_audit_log
from core.security import hash_password, verify_password, create_access_token, ClinicalRole
from models.patient_portal import (
    PatientPortalAccountCreate,
    PatientPortalAccountResponse,
    PatientPortalLoginRequest,
    PatientPortalTokenResponse,
    PatientDailyLogCreate,
    PatientDailyLogRecord,
    BowelMovementType,
    PatientHealthSummary,
)
from models.schemas import UserResponse


class PatientPortalError(Exception):
    pass


def register_patient_portal_account(
    req: PatientPortalAccountCreate,
    conn: Optional[sqlite3.Connection] = None
) -> PatientPortalAccountResponse:
    """Registers a new patient portal login credential linked to Master Patient Index."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT patient_id FROM patients WHERE patient_id = ?;", (req.patient_id,))
        if not cursor.fetchone():
            raise PatientPortalError(f"Patient ID '{req.patient_id}' does not exist in Master Patient Index.")

        cursor.execute("SELECT account_id FROM patient_portal_accounts WHERE phone_number = ?;", (req.phone_number,))
        if cursor.fetchone():
            raise PatientPortalError(f"Phone number '{req.phone_number}' is already registered in patient portal.")

        account_id = f"acc-{uuid.uuid4().hex[:12]}"
        pwd_hash = hash_password(req.password)
        now = int(time.time())

        cursor.execute(
            """
            INSERT INTO patient_portal_accounts (
                account_id, patient_id, hospital_id, phone_number, password_hash, abha_address, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?);
            """,
            (account_id, req.patient_id, req.hospital_id, req.phone_number, pwd_hash, req.abha_address, now)
        )

        append_audit_log(
            conn,
            req.hospital_id,
            account_id,
            "REGISTER_PORTAL_ACCOUNT",
            "PATIENT_PORTAL",
            req.patient_id,
            {"phone": req.phone_number, "abha": req.abha_address}
        )
        conn.commit()

        return PatientPortalAccountResponse(
            account_id=account_id,
            patient_id=req.patient_id,
            hospital_id=req.hospital_id,
            phone_number=req.phone_number,
            abha_address=req.abha_address,
            is_active=True,
            created_at=now
        )
    finally:
        if should_close:
            conn.close()


def authenticate_patient_portal(
    req: PatientPortalLoginRequest,
    conn: Optional[sqlite3.Connection] = None
) -> PatientPortalTokenResponse:
    """Authenticates patient via phone number and password, issuing access token."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT a.account_id, a.patient_id, a.hospital_id, a.password_hash, a.is_active,
                   p.first_name, p.last_name
            FROM patient_portal_accounts a
            JOIN patients p ON a.patient_id = p.patient_id
            WHERE a.phone_number = ?;
            """,
            (req.phone_number,)
        )
        row = cursor.fetchone()
        if not row or not verify_password(req.password, row["password_hash"]):
            raise PatientPortalError("Invalid phone number or password.")
        if not bool(row["is_active"]):
            raise PatientPortalError("Account is inactive. Please contact hospital administration.")

        now = int(time.time())
        cursor.execute("UPDATE patient_portal_accounts SET last_login_at = ? WHERE account_id = ?;", (now, row["account_id"]))
        conn.commit()

        token = create_access_token(
            user_id=row["account_id"],
            hospital_id=row["hospital_id"],
            role=ClinicalRole.PATIENT,
            custom_claims={"patient_id": row["patient_id"]}
        )

        return PatientPortalTokenResponse(
            access_token=token,
            account_id=row["account_id"],
            patient_id=row["patient_id"],
            hospital_id=row["hospital_id"],
            first_name=row["first_name"],
            last_name=row["last_name"]
        )
    finally:
        if should_close:
            conn.close()


def evaluate_daily_log_doshic_risk(log_in: PatientDailyLogCreate) -> Optional[str]:
    """Evaluates early sub-clinical Doshic aggravation indicators based on daily logs."""
    warnings = []
    if log_in.bowel_movement_type == BowelMovementType.VATA_CONSTIPATED and log_in.sleep_duration_hours < 6.0:
        warnings.append("Vata Vriddhi alert: Inadequate sleep and Apana Vayu obstruction (vibandha)")
    if log_in.bowel_movement_type == BowelMovementType.PITTA_LOOSE or log_in.stress_level >= 8:
        warnings.append("Pitta/Manasika alert: Elevated emotional stress and loose stools indicate Ushna/Tikshna excess")
    if log_in.bowel_movement_type == BowelMovementType.KAPHA_HEAVY_MUCOID and log_in.diet_adherence_score < 70:
        warnings.append("Ama/Kapha alert: Heavy mucoid stool and dietary non-compliance suggest Agnimandya")
    return "; ".join(warnings) if warnings else None


def record_patient_daily_log(
    req: PatientDailyLogCreate,
    current_user: Optional[UserResponse] = None,
    conn: Optional[sqlite3.Connection] = None
) -> PatientDailyLogRecord:
    """Stores daily self-reported diet, bowel, sleep, and stress log."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        log_id = f"log-{uuid.uuid4().hex[:12]}"
        now = int(time.time())
        warning = evaluate_daily_log_doshic_risk(req)

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patient_daily_logs (
                log_id, patient_id, hospital_id, log_date, diet_adherence_score,
                pathya_followed_notes, ahara_craving, bowel_movement_type,
                sleep_duration_hours, stress_level, logged_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                log_id,
                req.patient_id,
                req.hospital_id,
                req.log_date,
                req.diet_adherence_score,
                req.pathya_followed_notes,
                req.ahara_craving,
                req.bowel_movement_type.value,
                req.sleep_duration_hours,
                req.stress_level,
                now,
            )
        )

        user_id = current_user.user_id if current_user else req.patient_id
        append_audit_log(
            conn,
            req.hospital_id,
            user_id,
            "RECORD_DAILY_LOG",
            "PATIENT_DAILY_LOG",
            log_id,
            {
                "patient_id": req.patient_id,
                "adherence": req.diet_adherence_score,
                "bowel": req.bowel_movement_type.value
            }
        )
        conn.commit()

        return PatientDailyLogRecord(
            log_id=log_id,
            patient_id=req.patient_id,
            hospital_id=req.hospital_id,
            log_date=req.log_date,
            diet_adherence_score=req.diet_adherence_score,
            pathya_followed_notes=req.pathya_followed_notes,
            ahara_craving=req.ahara_craving,
            bowel_movement_type=req.bowel_movement_type,
            sleep_duration_hours=req.sleep_duration_hours,
            stress_level=req.stress_level,
            doshic_aggravation_warning=warning,
            logged_at=now
        )
    finally:
        if should_close:
            conn.close()


def get_patient_daily_logs(
    patient_id: str,
    limit: int = 14,
    conn: Optional[sqlite3.Connection] = None
) -> List[PatientDailyLogRecord]:
    """Retrieves chronological daily logs for a patient."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM patient_daily_logs
            WHERE patient_id = ?
            ORDER BY logged_at DESC
            LIMIT ?;
            """,
            (patient_id, limit)
        )
        rows = cursor.fetchall()
        results = []
        for r in rows:
            dummy_in = PatientDailyLogCreate(
                patient_id=r["patient_id"],
                hospital_id=r["hospital_id"],
                log_date=r["log_date"],
                diet_adherence_score=r["diet_adherence_score"],
                pathya_followed_notes=r["pathya_followed_notes"],
                ahara_craving=r["ahara_craving"],
                bowel_movement_type=BowelMovementType(r["bowel_movement_type"]),
                sleep_duration_hours=r["sleep_duration_hours"],
                stress_level=r["stress_level"]
            )
            warning = evaluate_daily_log_doshic_risk(dummy_in)
            results.append(
                PatientDailyLogRecord(
                    log_id=r["log_id"],
                    patient_id=r["patient_id"],
                    hospital_id=r["hospital_id"],
                    log_date=r["log_date"],
                    diet_adherence_score=r["diet_adherence_score"],
                    pathya_followed_notes=r["pathya_followed_notes"],
                    ahara_craving=r["ahara_craving"],
                    bowel_movement_type=BowelMovementType(r["bowel_movement_type"]),
                    sleep_duration_hours=r["sleep_duration_hours"],
                    stress_level=r["stress_level"],
                    doshic_aggravation_warning=warning,
                    logged_at=r["logged_at"]
                )
            )
        return results
    finally:
        if should_close:
            conn.close()


def get_patient_health_summary(
    patient_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> PatientHealthSummary:
    """Generates holistic patient portal overview combining Prakriti, recent logs, and active prescriptions."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE patient_id = ?;", (patient_id,))
        p = cursor.fetchone()
        if not p:
            raise PatientPortalError(f"Patient '{patient_id}' not found.")

        # Prescriptions count
        cursor.execute("SELECT COUNT(*) as cnt FROM digital_eprescriptions WHERE patient_id = ?;", (patient_id,))
        rx_cnt = cursor.fetchone()["cnt"]

        # Logs
        recent_logs = get_patient_daily_logs(patient_id, limit=7, conn=conn)
        total_logs = len(recent_logs)
        avg_adh = sum(l.diet_adherence_score for l in recent_logs) / total_logs if total_logs > 0 else 100.0

        prakriti_dict = {
            "vata": p["prakriti_vata"] or 0.3333,
            "pitta": p["prakriti_pitta"] or 0.3333,
            "kapha": p["prakriti_kapha"] or 0.3334,
        }

        return PatientHealthSummary(
            patient_id=p["patient_id"],
            hospital_id=p["hospital_id"],
            full_name=f"{p['first_name']} {p['last_name']}",
            dob=p["dob"],
            gender=p["gender"],
            prakriti=prakriti_dict,
            total_logs=total_logs,
            average_diet_adherence=round(avg_adh, 1),
            active_prescriptions_count=rx_cnt,
            recent_logs=recent_logs
        )
    finally:
        if should_close:
            conn.close()
