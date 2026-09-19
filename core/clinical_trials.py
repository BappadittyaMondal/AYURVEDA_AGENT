"""
core/clinical_trials.py - Core Engine for Phase 45: Clinical Trial Registry & Integrative Research (CTRI).
Handles CTRI study registration, cohort enrollment, and longitudinal comparative statistical analytics.
"""

import time
import uuid
import math
import sqlite3
from typing import Optional, List
from core.database import get_sqlite_connection, append_audit_log
from models.clinical_trials import (
    TrialStatus,
    ProtocolCreate,
    ProtocolRecord,
    SubjectEnrollmentCreate,
    SubjectRecord,
    SubjectProgressUpdate,
    TrialAnalyticsSummary,
)
from models.schemas import UserResponse


class ClinicalTrialError(Exception):
    pass


def register_trial_protocol(
    req: ProtocolCreate,
    current_user: Optional[UserResponse] = None,
    conn: Optional[sqlite3.Connection] = None
) -> ProtocolRecord:
    """Registers an evidence-based clinical trial protocol compliant with CTRI standards."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        if not req.ctri_registration_number.startswith("CTRI/"):
            raise ClinicalTrialError("CTRI registration number must conform to official standard (CTRI/YYYY/...)")

        protocol_id = f"ctri-{uuid.uuid4().hex[:12]}"
        now = int(time.time())

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO clinical_trial_protocols (
                protocol_id, ctri_registration_number, trial_title, ayurvedic_intervention_arm,
                control_arm, sample_size_target, primary_outcome_measure,
                principal_investigator_arn, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                protocol_id,
                req.ctri_registration_number,
                req.trial_title,
                req.ayurvedic_intervention_arm,
                req.control_arm,
                req.sample_size_target,
                req.primary_outcome_measure,
                req.principal_investigator_arn,
                TrialStatus.RECRUITING.value,
                now,
            )
        )

        user_id = current_user.user_id if current_user else req.principal_investigator_arn
        append_audit_log(
            conn,
            "aiia-delhi-central-001",
            user_id,
            "REGISTER_TRIAL_PROTOCOL",
            "CTRI_PROTOCOL",
            protocol_id,
            {"ctri_num": req.ctri_registration_number, "target": req.sample_size_target}
        )
        conn.commit()

        return ProtocolRecord(
            protocol_id=protocol_id,
            ctri_registration_number=req.ctri_registration_number,
            trial_title=req.trial_title,
            ayurvedic_intervention_arm=req.ayurvedic_intervention_arm,
            control_arm=req.control_arm,
            sample_size_target=req.sample_size_target,
            primary_outcome_measure=req.primary_outcome_measure,
            principal_investigator_arn=req.principal_investigator_arn,
            status=TrialStatus.RECRUITING,
            created_at=now
        )
    finally:
        if should_close:
            conn.close()


def get_trial_protocol(
    protocol_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> Optional[ProtocolRecord]:
    """Retrieves clinical trial protocol by ID."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clinical_trial_protocols WHERE protocol_id = ?;", (protocol_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return ProtocolRecord(
            protocol_id=row["protocol_id"],
            ctri_registration_number=row["ctri_registration_number"],
            trial_title=row["trial_title"],
            ayurvedic_intervention_arm=row["ayurvedic_intervention_arm"],
            control_arm=row["control_arm"],
            sample_size_target=row["sample_size_target"],
            primary_outcome_measure=row["primary_outcome_measure"],
            principal_investigator_arn=row["principal_investigator_arn"],
            status=TrialStatus(row["status"]),
            created_at=row["created_at"]
        )
    finally:
        if should_close:
            conn.close()


def enroll_trial_subject(
    req: SubjectEnrollmentCreate,
    current_user: Optional[UserResponse] = None,
    conn: Optional[sqlite3.Connection] = None
) -> SubjectRecord:
    """Enrolls an eligible patient into a trial arm with baseline Prakriti stratification."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        protocol = get_trial_protocol(req.protocol_id, conn=conn)
        if not protocol:
            raise ClinicalTrialError(f"Trial protocol '{req.protocol_id}' does not exist.")

        subject_id = f"sub-{uuid.uuid4().hex[:12]}"
        now = int(time.time())

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO trial_cohort_subjects (
                subject_id, protocol_id, patient_id, assigned_arm, baseline_prakriti,
                baseline_score, current_score, compliance_rate_pct, enrolled_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 100.0, ?);
            """,
            (
                subject_id,
                req.protocol_id,
                req.patient_id,
                req.assigned_arm.upper(),
                req.baseline_prakriti,
                req.baseline_score,
                req.baseline_score,
                now,
            )
        )
        conn.commit()

        return SubjectRecord(
            subject_id=subject_id,
            protocol_id=req.protocol_id,
            patient_id=req.patient_id,
            assigned_arm=req.assigned_arm.upper(),
            baseline_prakriti=req.baseline_prakriti,
            baseline_score=req.baseline_score,
            current_score=req.baseline_score,
            compliance_rate_pct=100.0,
            enrolled_at=now
        )
    finally:
        if should_close:
            conn.close()


def update_subject_progress(
    subject_id: str,
    update: SubjectProgressUpdate,
    conn: Optional[sqlite3.Connection] = None
) -> SubjectRecord:
    """Updates follow-up clinical scores and therapy compliance for a trial subject."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE trial_cohort_subjects
            SET current_score = ?, compliance_rate_pct = ?
            WHERE subject_id = ?;
            """,
            (update.current_score, update.compliance_rate_pct, subject_id)
        )
        conn.commit()

        cursor.execute("SELECT * FROM trial_cohort_subjects WHERE subject_id = ?;", (subject_id,))
        row = cursor.fetchone()
        if not row:
            raise ClinicalTrialError(f"Subject '{subject_id}' not found.")

        return SubjectRecord(
            subject_id=row["subject_id"],
            protocol_id=row["protocol_id"],
            patient_id=row["patient_id"],
            assigned_arm=row["assigned_arm"],
            baseline_prakriti=row["baseline_prakriti"],
            baseline_score=row["baseline_score"],
            current_score=row["current_score"],
            compliance_rate_pct=row["compliance_rate_pct"],
            enrolled_at=row["enrolled_at"]
        )
    finally:
        if should_close:
            conn.close()


def compute_trial_analytics(
    protocol_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> TrialAnalyticsSummary:
    """Computes comparative efficacy analytics, mean delta improvement, and effect size."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        protocol = get_trial_protocol(protocol_id, conn=conn)
        if not protocol:
            raise ClinicalTrialError(f"Trial protocol '{protocol_id}' does not exist.")

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trial_cohort_subjects WHERE protocol_id = ?;", (protocol_id,))
        rows = cursor.fetchall()

        intervention = [r for r in rows if r["assigned_arm"] == "INTERVENTION"]
        control = [r for r in rows if r["assigned_arm"] == "CONTROL"]

        total = len(rows)
        int_cnt = len(intervention)
        ctrl_cnt = len(control)

        mean_base_int = sum(r["baseline_score"] for r in intervention) / int_cnt if int_cnt > 0 else 0.0
        mean_curr_int = sum(r["current_score"] for r in intervention) / int_cnt if int_cnt > 0 else 0.0
        delta_int = mean_base_int - mean_curr_int

        mean_base_ctrl = sum(r["baseline_score"] for r in control) / ctrl_cnt if ctrl_cnt > 0 else 0.0
        mean_curr_ctrl = sum(r["current_score"] for r in control) / ctrl_cnt if ctrl_cnt > 0 else 0.0
        delta_ctrl = mean_base_ctrl - mean_curr_ctrl

        # Estimated pooled standard deviation and Cohen's d effect size
        all_diffs = [(r["baseline_score"] - r["current_score"]) for r in rows]
        if len(all_diffs) > 1:
            mean_diff = sum(all_diffs) / len(all_diffs)
            variance = sum((x - mean_diff) ** 2 for x in all_diffs) / (len(all_diffs) - 1)
            std_dev = math.sqrt(variance) if variance > 0.0001 else 1.0
            cohens_d = round(abs(delta_int - delta_ctrl) / std_dev, 2)
        else:
            cohens_d = 0.5

        compliance = sum(r["compliance_rate_pct"] for r in rows) / total if total > 0 else 100.0

        return TrialAnalyticsSummary(
            protocol_id=protocol.protocol_id,
            trial_title=protocol.trial_title,
            status=protocol.status,
            total_enrolled=total,
            intervention_count=int_cnt,
            control_count=ctrl_cnt,
            mean_baseline_score_intervention=round(mean_base_int, 2),
            mean_current_score_intervention=round(mean_curr_int, 2),
            mean_delta_improvement_intervention=round(delta_int, 2),
            mean_delta_improvement_control=round(delta_ctrl, 2),
            cohens_d_effect_size=cohens_d,
            overall_compliance_rate_pct=round(compliance, 1)
        )
    finally:
        if should_close:
            conn.close()
