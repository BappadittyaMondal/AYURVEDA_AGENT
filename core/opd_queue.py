"""
core/opd_queue.py - Core Engine for Phase 47: OPD Queue Optimization & Token Flow Management.
Implements multi-priority triage token flow and physician consultation duration time-audits.
"""

import time
import uuid
import sqlite3
from typing import Optional, List
from core.database import get_sqlite_connection, append_audit_log
from models.opd_queue import (
    PriorityTier,
    TokenStatus,
    OpdTokenCreate,
    OpdTokenRecord,
    ConsultationAuditRecord,
    OpdDepartmentQueueStatus,
)
from models.schemas import UserResponse


class OpdQueueError(Exception):
    pass


def issue_opd_token(
    req: OpdTokenCreate,
    current_user: Optional[UserResponse] = None,
    conn: Optional[sqlite3.Connection] = None
) -> OpdTokenRecord:
    """Issues a multi-priority outpatient queue token with dynamic wait-time calculation."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        now = int(time.time())
        cursor = conn.cursor()

        # Compute next token number in department
        cursor.execute(
            """
            SELECT COALESCE(MAX(token_number), 0) as max_tok
            FROM opd_token_queues
            WHERE department = ?;
            """,
            (req.department,)
        )
        next_tok = cursor.fetchone()["max_tok"] + 1

        # Calculate estimated wait minutes based on active queue
        cursor.execute(
            """
            SELECT COUNT(*) as waiting_count
            FROM opd_token_queues
            WHERE department = ? AND status = ?;
            """,
            (req.department, TokenStatus.WAITING.value)
        )
        waiting_count = cursor.fetchone()["waiting_count"]

        if req.priority_tier == PriorityTier.EMERGENCY_TIVRA:
            est_wait = 0
        elif req.priority_tier in [PriorityTier.SENIOR_CITIZEN_GERIATRIC, PriorityTier.PEDIATRIC_BALA]:
            est_wait = max(2, (waiting_count * 5) // 2)
        else:
            est_wait = max(5, waiting_count * 8)

        token_id = f"tok-{uuid.uuid4().hex[:12]}"
        cursor.execute(
            """
            INSERT INTO opd_token_queues (
                token_id, hospital_id, patient_id, department, token_number,
                priority_tier, status, estimated_wait_minutes, issued_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                token_id,
                req.hospital_id,
                req.patient_id,
                req.department,
                next_tok,
                req.priority_tier.value,
                TokenStatus.WAITING.value,
                est_wait,
                now,
            )
        )

        user_id = current_user.user_id if current_user else req.patient_id
        append_audit_log(
            conn,
            req.hospital_id,
            user_id,
            "ISSUE_OPD_TOKEN",
            "OPD_TOKEN",
            token_id,
            {"dept": req.department, "token_num": next_tok, "tier": req.priority_tier.value}
        )
        conn.commit()

        return OpdTokenRecord(
            token_id=token_id,
            hospital_id=req.hospital_id,
            patient_id=req.patient_id,
            department=req.department,
            token_number=next_tok,
            priority_tier=req.priority_tier,
            status=TokenStatus.WAITING,
            estimated_wait_minutes=est_wait,
            issued_at=now
        )
    finally:
        if should_close:
            conn.close()


def call_next_opd_token(
    department: str,
    physician_arn: str,
    conn: Optional[sqlite3.Connection] = None
) -> Optional[OpdTokenRecord]:
    """Pulls the next highest priority waiting patient in the department and starts consultation."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        now = int(time.time())
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM opd_token_queues
            WHERE department = ? AND status = ?
            ORDER BY
                CASE priority_tier
                    WHEN 'EMERGENCY_TIVRA' THEN 1
                    WHEN 'SENIOR_CITIZEN_GERIATRIC' THEN 2
                    WHEN 'PEDIATRIC_BALA' THEN 3
                    ELSE 4
                END ASC,
                issued_at ASC
            LIMIT 1;
            """,
            (department, TokenStatus.WAITING.value)
        )
        row = cursor.fetchone()
        if not row:
            return None

        token_id = row["token_id"]
        cursor.execute(
            "UPDATE opd_token_queues SET status = ? WHERE token_id = ?;",
            (TokenStatus.IN_CONSULTATION.value, token_id)
        )

        audit_id = f"aud-{uuid.uuid4().hex[:12]}"
        cursor.execute(
            """
            INSERT INTO consultation_time_audits (
                audit_id, token_id, physician_arn, consultation_start_timestamp,
                consultation_end_timestamp, duration_seconds, efficiency_rating
            ) VALUES (?, ?, ?, ?, NULL, NULL, NULL);
            """,
            (audit_id, token_id, physician_arn, now)
        )
        conn.commit()

        return OpdTokenRecord(
            token_id=row["token_id"],
            hospital_id=row["hospital_id"],
            patient_id=row["patient_id"],
            department=row["department"],
            token_number=row["token_number"],
            priority_tier=PriorityTier(row["priority_tier"]),
            status=TokenStatus.IN_CONSULTATION,
            estimated_wait_minutes=0,
            issued_at=row["issued_at"]
        )
    finally:
        if should_close:
            conn.close()


def complete_opd_consultation(
    token_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> ConsultationAuditRecord:
    """Marks outpatient consultation completed, computing duration and physician clinical throughput rating."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        now = int(time.time())
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM consultation_time_audits WHERE token_id = ?;", (token_id,))
        audit = cursor.fetchone()
        if not audit:
            raise OpdQueueError(f"No consultation audit found for token '{token_id}'.")

        start_ts = audit["consultation_start_timestamp"]
        duration = max(1, now - start_ts)
        # Optimal consultation target ~ 15 minutes (900 seconds)
        efficiency = round(min(1.0, max(0.2, 900.0 / max(duration, 60))), 2)

        cursor.execute(
            """
            UPDATE consultation_time_audits
            SET consultation_end_timestamp = ?, duration_seconds = ?, efficiency_rating = ?
            WHERE token_id = ?;
            """,
            (now, duration, efficiency, token_id)
        )
        cursor.execute(
            "UPDATE opd_token_queues SET status = ? WHERE token_id = ?;",
            (TokenStatus.COMPLETED.value, token_id)
        )
        conn.commit()

        return ConsultationAuditRecord(
            audit_id=audit["audit_id"],
            token_id=token_id,
            physician_arn=audit["physician_arn"],
            consultation_start_timestamp=start_ts,
            consultation_end_timestamp=now,
            duration_seconds=duration,
            efficiency_rating=efficiency
        )
    finally:
        if should_close:
            conn.close()


def get_department_queue_status(
    department: str,
    conn: Optional[sqlite3.Connection] = None
) -> OpdDepartmentQueueStatus:
    """Retrieves live queue status for an OPD department."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM opd_token_queues
            WHERE department = ? AND status IN (?, ?)
            ORDER BY issued_at ASC;
            """,
            (department, TokenStatus.WAITING.value, TokenStatus.IN_CONSULTATION.value)
        )
        rows = cursor.fetchall()

        waiting = [r for r in rows if r["status"] == TokenStatus.WAITING.value]
        in_consult = [r for r in rows if r["status"] == TokenStatus.IN_CONSULTATION.value]

        current_token = in_consult[0]["token_number"] if in_consult else None
        avg_wait = len(waiting) * 8

        token_records = [
            OpdTokenRecord(
                token_id=r["token_id"],
                hospital_id=r["hospital_id"],
                patient_id=r["patient_id"],
                department=r["department"],
                token_number=r["token_number"],
                priority_tier=PriorityTier(r["priority_tier"]),
                status=TokenStatus(r["status"]),
                estimated_wait_minutes=r["estimated_wait_minutes"],
                issued_at=r["issued_at"]
            )
            for r in rows
        ]

        return OpdDepartmentQueueStatus(
            department=department,
            total_waiting=len(waiting),
            in_consultation_count=len(in_consult),
            current_token_being_served=current_token,
            average_wait_minutes=avg_wait,
            active_tokens=token_records
        )
    finally:
        if should_close:
            conn.close()
