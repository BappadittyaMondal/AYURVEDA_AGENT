"""API Endpoints for Roga Rogi Bala Ganan Yantra (Bi-Directional Balance Engine)."""
import json
import sqlite3
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_db_session, require_action
from core.database import append_audit_log
from core.roga_rogi_bala import evaluate_roga_rogi_bala
from core.security import ClinicalAction
from models.roga_rogi_bala import (
    RogaRogiBalaInput,
    RogaRogiBalaOutput,
    ShodhanaEligibilityStatus,
    TherapeuticCategory,
    TherapeuticGovernorDirective,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/roga-rogi-bala", tags=["Roga Rogi Bala Balance Engine"])


@router.post("/evaluate", response_model=RogaRogiBalaOutput, status_code=status.HTTP_201_CREATED)
def evaluate_patient_roga_rogi_balance(
    eval_input: RogaRogiBalaInput,
    current_user: UserResponse = Depends(require_action(ClinicalAction.ASSESS_TRIDOSHA)),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> RogaRogiBalaOutput:
    """Evaluate host resilience vs disease virulence, calculate dosage scalar, and gate therapeutic intensity."""
    cursor = conn.cursor()

    # Validate patient exists in current hospital
    cursor.execute(
        "SELECT patient_id FROM patients WHERE patient_id = ? AND hospital_id = ?;",
        (eval_input.patient_id, current_user.hospital_id),
    )
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{eval_input.patient_id}' not found in current hospital tenant",
        )

    evaluator_arn = current_user.arn or "NCISM-ARN-UNREGISTERED"

    output = evaluate_roga_rogi_bala(
        input_data=eval_input,
        evaluator_arn=evaluator_arn,
        hospital_id=current_user.hospital_id,
    )

    directives_json = json.dumps([d.model_dump() for d in output.governor_directives])

    cursor.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute(
            """
            INSERT INTO roga_rogi_bala_assessments (
                assessment_id, patient_id, hospital_id, evaluator_arn,
                rogi_bala_score, roga_bala_score, bala_ratio, bala_differential,
                therapeutic_category, dosage_scalar, shodhana_eligibility_status,
                governor_directives_json, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                output.assessment_id,
                output.patient_id,
                output.hospital_id,
                output.evaluator_arn,
                output.rogi_bala_score,
                output.roga_bala_score,
                output.bala_ratio,
                output.bala_differential,
                output.therapeutic_category.value,
                output.dosage_scalar,
                output.shodhana_eligibility_status.value,
                directives_json,
                output.timestamp,
            ),
        )

        append_audit_log(
            conn=conn,
            hospital_id=current_user.hospital_id,
            actor_id=current_user.user_id,
            action="EVALUATE_ROGA_ROGI_BALA",
            entity_type="roga_rogi_bala_assessment",
            entity_id=output.assessment_id,
            details={
                "patient_id": output.patient_id,
                "rogi_bala": output.rogi_bala_score,
                "roga_bala": output.roga_bala_score,
                "category": output.therapeutic_category.value,
                "dosage_scalar": output.dosage_scalar,
            },
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database transaction failure: {str(e)}",
        )

    return output


@router.get("/patients/{patient_id}/latest", response_model=RogaRogiBalaOutput)
def get_latest_roga_rogi_bala_assessment(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> RogaRogiBalaOutput:
    """Retrieve the most recent Roga Rogi Bala evaluation for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT assessment_id, patient_id, hospital_id, evaluator_arn,
               rogi_bala_score, roga_bala_score, bala_ratio, bala_differential,
               therapeutic_category, dosage_scalar, shodhana_eligibility_status,
               governor_directives_json, timestamp
        FROM roga_rogi_bala_assessments
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC, rowid DESC LIMIT 1;
        """,
        (patient_id, current_user.hospital_id),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Roga Rogi Bala assessments recorded for patient '{patient_id}'",
        )

    directives_raw = json.loads(row["governor_directives_json"])
    directives = [TherapeuticGovernorDirective(**d) for d in directives_raw]

    return RogaRogiBalaOutput(
        assessment_id=row["assessment_id"],
        patient_id=row["patient_id"],
        hospital_id=row["hospital_id"],
        evaluator_arn=row["evaluator_arn"],
        rogi_bala_score=row["rogi_bala_score"],
        roga_bala_score=row["roga_bala_score"],
        bala_ratio=row["bala_ratio"],
        bala_differential=row["bala_differential"],
        therapeutic_category=TherapeuticCategory(row["therapeutic_category"]),
        dosage_scalar=row["dosage_scalar"],
        shodhana_eligibility_status=ShodhanaEligibilityStatus(row["shodhana_eligibility_status"]),
        governor_directives=directives,
        timestamp=row["timestamp"],
    )


@router.get("/patients/{patient_id}/history", response_model=List[RogaRogiBalaOutput])
def get_roga_rogi_bala_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[RogaRogiBalaOutput]:
    """Retrieve full chronological history of Roga Rogi Bala assessments for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT assessment_id, patient_id, hospital_id, evaluator_arn,
               rogi_bala_score, roga_bala_score, bala_ratio, bala_differential,
               therapeutic_category, dosage_scalar, shodhana_eligibility_status,
               governor_directives_json, timestamp
        FROM roga_rogi_bala_assessments
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC, rowid DESC;
        """,
        (patient_id, current_user.hospital_id),
    )
    rows = cursor.fetchall()

    results = []
    for r in rows:
        directives_raw = json.loads(r["governor_directives_json"])
        directives = [TherapeuticGovernorDirective(**d) for d in directives_raw]
        results.append(
            RogaRogiBalaOutput(
                assessment_id=r["assessment_id"],
                patient_id=r["patient_id"],
                hospital_id=r["hospital_id"],
                evaluator_arn=r["evaluator_arn"],
                rogi_bala_score=r["rogi_bala_score"],
                roga_bala_score=r["roga_bala_score"],
                bala_ratio=r["bala_ratio"],
                bala_differential=r["bala_differential"],
                therapeutic_category=TherapeuticCategory(r["therapeutic_category"]),
                dosage_scalar=r["dosage_scalar"],
                shodhana_eligibility_status=ShodhanaEligibilityStatus(r["shodhana_eligibility_status"]),
                governor_directives=directives,
                timestamp=r["timestamp"],
            )
        )
    return results
