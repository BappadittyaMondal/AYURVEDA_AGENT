"""Dashavidha Pariksha (10-Fold Systemic Clinical Evaluation) Router."""
import json
import sqlite3
import time
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_current_user, get_db_session, require_action
from core.dashavidha import evaluate_dashavidha_pariksha
from core.database import append_audit_log
from core.security import ClinicalAction
from models.dashavidha import (
    DashavidhaParikshaInput,
    DashavidhaParikshaOutput,
    TherapeuticEligibility,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/dashavidha", tags=["Dashavidha Pariksha Valuation Engine"])


@router.post("/patients/{patient_id}", response_model=DashavidhaParikshaOutput, status_code=status.HTTP_201_CREATED)
def record_dashavidha_examination(
    patient_id: str,
    exam_input: DashavidhaParikshaInput,
    current_user: UserResponse = Depends(require_action(ClinicalAction.ASSESS_TRIDOSHA)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> DashavidhaParikshaOutput:
    """
    Record 10-fold systemic clinical assessment (Dushya, Desha, Bala, Kala, Anala, etc.),
    compute Rogi Bala vs Roga Bala, and determine therapeutic intensity and Panchakarma eligibility.
    """
    cursor = conn.cursor()

    cursor.execute(
        "SELECT patient_id, hospital_id FROM patients WHERE patient_id = ? AND hospital_id = ?;",
        (patient_id, current_user.hospital_id)
    )
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found in current hospital tenant"
        )

    rogi_bala, roga_bala, ratio, eligibility, rationale = evaluate_dashavidha_pariksha(exam_input)

    assessment_id = f"dsh-{uuid.uuid4().hex[:12]}"
    now = int(time.time())
    evaluator_arn = current_user.arn or "EXAMINER_ARN_PENDING"

    cursor.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute(
            """
            INSERT INTO dashavidha_assessments (
                assessment_id, patient_id, hospital_id, evaluator_arn,
                dushya_json, desha_json, bala_json, anala_json, ahara_json,
                rogi_bala, roga_bala, rogi_roga_ratio, eligibility, rationale, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                assessment_id,
                patient_id,
                current_user.hospital_id,
                evaluator_arn,
                exam_input.dushya.model_dump_json(),
                exam_input.desha.model_dump_json(),
                exam_input.bala.model_dump_json(),
                exam_input.anala.model_dump_json(),
                exam_input.ahara_shakti.model_dump_json(),
                rogi_bala,
                roga_bala,
                ratio,
                eligibility.value,
                rationale,
                now
            )
        )

        append_audit_log(
            conn,
            hospital_id=current_user.hospital_id,
            actor_id=current_user.user_id,
            action="RECORD_DASHAVIDHA_EXAM",
            entity_type="DASHAVIDHA_ASSESSMENT",
            entity_id=assessment_id,
            details={
                "patient_id": patient_id,
                "rogi_bala": rogi_bala,
                "roga_bala": roga_bala,
                "rogi_roga_ratio": ratio,
                "eligibility": eligibility.value
            }
        )
        cursor.execute("COMMIT;")
    except Exception:
        cursor.execute("ROLLBACK;")
        raise

    return DashavidhaParikshaOutput(
        assessment_id=assessment_id,
        patient_id=patient_id,
        hospital_id=current_user.hospital_id,
        evaluator_arn=evaluator_arn,
        rogi_bala_score=rogi_bala,
        roga_bala_score=roga_bala,
        rogi_roga_ratio=ratio,
        therapeutic_eligibility=eligibility,
        clinical_rationale=rationale,
        timestamp=now
    )


@router.get("/patients/{patient_id}/latest", response_model=DashavidhaParikshaOutput)
def get_latest_dashavidha_examination(
    patient_id: str,
    current_user: UserResponse = Depends(require_action(ClinicalAction.VIEW_PATIENT_PHI)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> DashavidhaParikshaOutput:
    """Retrieve the most recent Dashavidha Pariksha valuation for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT assessment_id, patient_id, hospital_id, evaluator_arn,
               rogi_bala, roga_bala, rogi_roga_ratio, eligibility, rationale, timestamp
        FROM dashavidha_assessments
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC LIMIT 1;
        """,
        (patient_id, current_user.hospital_id)
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Dashavidha records found for patient '{patient_id}'"
        )

    return DashavidhaParikshaOutput(
        assessment_id=row["assessment_id"],
        patient_id=row["patient_id"],
        hospital_id=row["hospital_id"],
        evaluator_arn=row["evaluator_arn"],
        rogi_bala_score=float(row["rogi_bala"]),
        roga_bala_score=float(row["roga_bala"]),
        rogi_roga_ratio=float(row["rogi_roga_ratio"]),
        therapeutic_eligibility=TherapeuticEligibility(row["eligibility"]),
        clinical_rationale=row["rationale"],
        timestamp=row["timestamp"]
    )


@router.get("/patients/{patient_id}/history", response_model=List[DashavidhaParikshaOutput])
def get_dashavidha_history(
    patient_id: str,
    current_user: UserResponse = Depends(require_action(ClinicalAction.VIEW_PATIENT_PHI)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> List[DashavidhaParikshaOutput]:
    """Retrieve historical progression of Dashavidha Pariksha evaluations for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT assessment_id, patient_id, hospital_id, evaluator_arn,
               rogi_bala, roga_bala, rogi_roga_ratio, eligibility, rationale, timestamp
        FROM dashavidha_assessments
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC;
        """,
        (patient_id, current_user.hospital_id)
    )
    rows = cursor.fetchall()
    return [
        DashavidhaParikshaOutput(
            assessment_id=r["assessment_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            evaluator_arn=r["evaluator_arn"],
            rogi_bala_score=float(r["rogi_bala"]),
            roga_bala_score=float(r["roga_bala"]),
            rogi_roga_ratio=float(r["rogi_roga_ratio"]),
            therapeutic_eligibility=TherapeuticEligibility(r["eligibility"]),
            clinical_rationale=r["rationale"],
            timestamp=r["timestamp"]
        )
        for r in rows
    ]
