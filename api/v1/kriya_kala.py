"""API Endpoints for Shat Kriya Kala Pathological Stage Tracker (6 Stages)."""
import json
import sqlite3
import time
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_db_session, require_action
from core.database import append_audit_log
from core.kriya_kala import evaluate_kriya_kala
from core.security import ClinicalAction
from models.kriya_kala import (
    CurabilityPrognosis,
    KriyaKalaInput,
    KriyaKalaOutput,
    KriyaKalaStage,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/kriya-kala", tags=["Shat Kriya Kala Pathological Staging"])


@router.get("/stages", response_model=List[Dict[str, str]])
def get_kriya_kala_stages_reference(
    current_user: UserResponse = Depends(get_current_user),
) -> List[Dict[str, str]]:
    """Retrieve the six classical pathogenesis stages from Sushruta Sutrasthana 21."""
    return [
        {"stage": "SANCHAYA", "sanskrit": "Sanchaya", "translation": "Accumulation", "opportunity": "High reversibility; dietary/lifestyle pacification"},
        {"stage": "PRAKOPA", "sanskrit": "Prakopa", "translation": "Excitation", "opportunity": "Localized Shamana or mild Shodhana"},
        {"stage": "PRASARA", "sanskrit": "Prasara", "translation": "Dissemination", "opportunity": "Rogamarga Anulomana before localization"},
        {"stage": "STHANASAMSHRAYA", "sanskrit": "Sthanasamshraya", "translation": "Cellular lodging", "opportunity": "Prodromal Purvaroopa window; clear Khavaigunya"},
        {"stage": "VYAKTI", "sanskrit": "Vyakti", "translation": "Full manifestation", "opportunity": "Full-scale Vyadhi-pratyanika therapy"},
        {"stage": "BHEDA", "sanskrit": "Bheda", "translation": "Complications / chronicity", "opportunity": "Ulceration/suppuration management; palliative Yapya maintenance"},
    ]


@router.post("/evaluate", response_model=KriyaKalaOutput, status_code=status.HTTP_201_CREATED)
def evaluate_patient_kriya_kala(
    eval_input: KriyaKalaInput,
    current_user: UserResponse = Depends(require_action(ClinicalAction.ASSESS_TRIDOSHA)),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> KriyaKalaOutput:
    """Evaluate pathological pathogenesis stage, progression index, reversibility, and therapeutic window."""
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

    output = evaluate_kriya_kala(
        input_data=eval_input,
        evaluator_arn=evaluator_arn,
        hospital_id=current_user.hospital_id,
    )

    cursor.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute(
            """
            INSERT INTO kriya_kala_assessments (
                assessment_id, patient_id, hospital_id, evaluator_arn,
                current_stage, pathological_progression_index, stage_probabilities_json,
                prodromal_symptoms_json, manifest_symptoms_json, complications_json,
                reversibility_percentage, curability_prognosis,
                therapeutic_window_directive, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                output.assessment_id,
                output.patient_id,
                output.hospital_id,
                output.evaluator_arn,
                output.current_stage.value,
                output.pathological_progression_index,
                json.dumps(output.stage_probabilities),
                json.dumps(output.prodromal_symptoms),
                json.dumps(output.manifest_symptoms),
                json.dumps(output.complications),
                output.reversibility_percentage,
                output.curability_prognosis.value,
                output.therapeutic_window_directive,
                output.timestamp,
            ),
        )

        append_audit_log(
            conn=conn,
            hospital_id=current_user.hospital_id,
            actor_id=current_user.user_id,
            action="EVALUATE_KRIYA_KALA",
            entity_type="kriya_kala_assessment",
            entity_id=output.assessment_id,
            details={
                "patient_id": output.patient_id,
                "current_stage": output.current_stage.value,
                "ppi": output.pathological_progression_index,
                "prognosis": output.curability_prognosis.value,
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


@router.get("/patients/{patient_id}/latest", response_model=KriyaKalaOutput)
def get_latest_kriya_kala_assessment(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> KriyaKalaOutput:
    """Retrieve the most recent Kriya Kala staging assessment for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT assessment_id, patient_id, hospital_id, evaluator_arn,
               current_stage, pathological_progression_index, stage_probabilities_json,
               prodromal_symptoms_json, manifest_symptoms_json, complications_json,
               reversibility_percentage, curability_prognosis,
               therapeutic_window_directive, timestamp
        FROM kriya_kala_assessments
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC, rowid DESC LIMIT 1;
        """,
        (patient_id, current_user.hospital_id),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Kriya Kala assessments recorded for patient '{patient_id}'",
        )

    return KriyaKalaOutput(
        assessment_id=row["assessment_id"],
        patient_id=row["patient_id"],
        hospital_id=row["hospital_id"],
        evaluator_arn=row["evaluator_arn"],
        current_stage=KriyaKalaStage(row["current_stage"]),
        pathological_progression_index=row["pathological_progression_index"],
        stage_probabilities=json.loads(row["stage_probabilities_json"]),
        prodromal_symptoms=json.loads(row["prodromal_symptoms_json"]),
        manifest_symptoms=json.loads(row["manifest_symptoms_json"]),
        complications=json.loads(row["complications_json"]),
        reversibility_percentage=row["reversibility_percentage"],
        curability_prognosis=CurabilityPrognosis(row["curability_prognosis"]),
        therapeutic_window_directive=row["therapeutic_window_directive"],
        timestamp=row["timestamp"],
    )


@router.get("/patients/{patient_id}/history", response_model=List[KriyaKalaOutput])
def get_kriya_kala_assessment_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[KriyaKalaOutput]:
    """Retrieve full chronological history of Kriya Kala staging assessments for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT assessment_id, patient_id, hospital_id, evaluator_arn,
               current_stage, pathological_progression_index, stage_probabilities_json,
               prodromal_symptoms_json, manifest_symptoms_json, complications_json,
               reversibility_percentage, curability_prognosis,
               therapeutic_window_directive, timestamp
        FROM kriya_kala_assessments
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC, rowid DESC;
        """,
        (patient_id, current_user.hospital_id),
    )
    rows = cursor.fetchall()

    return [
        KriyaKalaOutput(
            assessment_id=r["assessment_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            evaluator_arn=r["evaluator_arn"],
            current_stage=KriyaKalaStage(r["current_stage"]),
            pathological_progression_index=r["pathological_progression_index"],
            stage_probabilities=json.loads(r["stage_probabilities_json"]),
            prodromal_symptoms=json.loads(r["prodromal_symptoms_json"]),
            manifest_symptoms=json.loads(r["manifest_symptoms_json"]),
            complications=json.loads(r["complications_json"]),
            reversibility_percentage=r["reversibility_percentage"],
            curability_prognosis=CurabilityPrognosis(r["curability_prognosis"]),
            therapeutic_window_directive=r["therapeutic_window_directive"],
            timestamp=r["timestamp"],
        )
        for r in rows
    ]
