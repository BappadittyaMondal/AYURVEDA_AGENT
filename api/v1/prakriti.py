"""Prakriti Diagnostic Assessment and 2-Simplex Analysis Router."""
import json
import sqlite3
import time
import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_current_user, get_db_session, require_action
from core.database import append_audit_log
from core.prakriti import PRAKRITI_QUESTIONS, compute_prakriti_simplex
from core.security import ClinicalAction
from models.clinical import PrakritiAssessmentInput, PrakritiVectorOutput
from models.schemas import UserResponse

router = APIRouter(prefix="/prakriti", tags=["Prakriti Simplex Diagnostic Engine"])


@router.get("/questions", response_model=List[Dict[str, Any]])
def get_prakriti_questionnaire(
    current_user: UserResponse = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Retrieve the 30-parameter classical Sharirika and Manasika intake questionnaire."""
    return PRAKRITI_QUESTIONS


@router.post("/patients/{patient_id}/assess", response_model=PrakritiVectorOutput, status_code=status.HTTP_201_CREATED)
def evaluate_patient_prakriti(
    patient_id: str,
    assessment: PrakritiAssessmentInput,
    current_user: UserResponse = Depends(require_action(ClinicalAction.ASSESS_TRIDOSHA)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> PrakritiVectorOutput:
    """
    Evaluate 30-question intake, compute Barycentric simplex coordinates on Delta^2,
    and persist the patient's baseline Deha Prakriti vector.
    """
    cursor = conn.cursor()

    # Verify patient exists and belongs to current hospital
    cursor.execute(
        "SELECT patient_id, hospital_id FROM patients WHERE patient_id = ? AND hospital_id = ?;",
        (patient_id, current_user.hospital_id)
    )
    patient = cursor.fetchone()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found in current hospital tenant"
        )

    # Compute Simplex Coordinates
    v, p, k, primary_dosha, classification = compute_prakriti_simplex(assessment.answers)

    scores = [("VATA", v), ("PITTA", p), ("KAPHA", k)]
    scores.sort(key=lambda x: x[1], reverse=True)
    secondary_dosha = scores[1][0] if scores[1][1] > 0.25 else None

    assessment_id = f"prk-{uuid.uuid4().hex[:12]}"
    now = int(time.time())
    answers_json = json.dumps(assessment.answers)
    evaluator_arn = current_user.arn or "SYSTEM_EVALUATOR"

    cursor.execute("BEGIN IMMEDIATE;")
    try:
        # Save assessment record
        cursor.execute(
            """
            INSERT INTO prakriti_assessments (
                assessment_id, patient_id, hospital_id, evaluated_by_arn,
                vata_score, pitta_score, kapha_score, classification, answers_json, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                assessment_id, patient_id, current_user.hospital_id, evaluator_arn,
                v, p, k, classification, answers_json, now
            )
        )

        # Update baseline patient record
        cursor.execute(
            """
            UPDATE patients
            SET prakriti_vata = ?, prakriti_pitta = ?, prakriti_kapha = ?
            WHERE patient_id = ?;
            """,
            (v, p, k, patient_id)
        )

        append_audit_log(
            conn,
            hospital_id=current_user.hospital_id,
            actor_id=current_user.user_id,
            action="ASSESS_DEHA_PRAKRITI",
            entity_type="PRAKRITI_ASSESSMENT",
            entity_id=assessment_id,
            details={
                "patient_id": patient_id,
                "vata": v,
                "pitta": p,
                "kapha": k,
                "classification": classification
            }
        )
        cursor.execute("COMMIT;")
    except Exception:
        cursor.execute("ROLLBACK;")
        raise

    return PrakritiVectorOutput(
        assessment_id=assessment_id,
        patient_id=patient_id,
        hospital_id=current_user.hospital_id,
        evaluated_by_arn=evaluator_arn,
        vata=v,
        pitta=p,
        kapha=k,
        primary_dosha=primary_dosha,
        secondary_dosha=secondary_dosha,
        classification=classification,
        timestamp=now
    )


@router.get("/patients/{patient_id}/history", response_model=List[PrakritiVectorOutput])
def get_patient_prakriti_history(
    patient_id: str,
    current_user: UserResponse = Depends(require_action(ClinicalAction.VIEW_PATIENT_PHI)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> List[PrakritiVectorOutput]:
    """Retrieve historical Prakriti assessments for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT assessment_id, patient_id, hospital_id, evaluated_by_arn,
               vata_score, pitta_score, kapha_score, classification, timestamp
        FROM prakriti_assessments
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC;
        """,
        (patient_id, current_user.hospital_id)
    )
    rows = cursor.fetchall()

    result = []
    for r in rows:
        v, p, k = float(r["vata_score"]), float(r["pitta_score"]), float(r["kapha_score"])
        scores = [("VATA", v), ("PITTA", p), ("KAPHA", k)]
        scores.sort(key=lambda x: x[1], reverse=True)
        primary = scores[0][0]
        secondary = scores[1][0] if scores[1][1] > 0.25 else None

        result.append(
            PrakritiVectorOutput(
                assessment_id=r["assessment_id"],
                patient_id=r["patient_id"],
                hospital_id=r["hospital_id"],
                evaluated_by_arn=r["evaluated_by_arn"],
                vata=v,
                pitta=p,
                kapha=k,
                primary_dosha=primary,
                secondary_dosha=secondary,
                classification=r["classification"],
                timestamp=r["timestamp"]
            )
        )
    return result
