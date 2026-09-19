"""API Endpoints for Quantitative Ama Grading Index (AGI) & Agni Vector Gating Engine."""
import json
import sqlite3
import time
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_db_session, require_action
from core.database import append_audit_log
from core.ama_agni import evaluate_ama_agni
from core.security import ClinicalAction
from models.ama_agni import (
    AgniType,
    AmaGrade,
    GatingStatus,
    AmaAgniEvaluationRequest,
    AmaAgniOutput,
    TherapeuticDirective,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/ama-agni", tags=["Ama Grading Index & Agni Gating"])


@router.get("/symptoms-list", response_model=List[Dict[str, str]])
def get_ama_cardinal_symptoms(
    current_user: UserResponse = Depends(get_current_user),
) -> List[Dict[str, str]]:
    """Retrieve the 10 classical cardinal Ama symptoms from Ashtanga Hridaya Sutrasthana 13."""
    return [
        {"id": "srotorodha", "sanskrit": "Srotorodha", "english": "Channel obstruction / microcirculatory stagnation", "weight": "1.2"},
        {"id": "balabhramsha", "sanskrit": "Balabhramsha", "english": "Loss of strength / debility", "weight": "1.0"},
        {"id": "gaurava", "sanskrit": "Gaurava", "english": "Bodily heaviness / lethargy", "weight": "1.1"},
        {"id": "anilamudhata", "sanskrit": "Anilamudhata", "english": "Stagnant / erratic peristaltic Vata", "weight": "1.0"},
        {"id": "alasya", "sanskrit": "Alasya", "english": "Psychomotor inertia / fatigue", "weight": "0.9"},
        {"id": "apakti", "sanskrit": "Apakti", "english": "Indigestion / dyspepsia", "weight": "1.2"},
        {"id": "nishthiva", "sanskrit": "Nishthiva", "english": "Excessive salivary expectoration / oral clamminess", "weight": "0.9"},
        {"id": "malasanga", "sanskrit": "Malasanga", "english": "Retention of excreta / obstipation", "weight": "1.0"},
        {"id": "aruchi", "sanskrit": "Aruchi", "english": "Anorexia / impaired taste", "weight": "0.9"},
        {"id": "klama", "sanskrit": "Klama", "english": "Exhaustion without muscular exertion", "weight": "0.8"},
    ]


@router.post("/evaluate", response_model=AmaAgniOutput, status_code=status.HTTP_201_CREATED)
def evaluate_patient_ama_and_agni(
    eval_req: AmaAgniEvaluationRequest,
    current_user: UserResponse = Depends(require_action(ClinicalAction.ASSESS_TRIDOSHA)),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> AmaAgniOutput:
    """Compute AGI score, Agni Vector, and Panchakarma Shodhana clearance firewall status."""
    cursor = conn.cursor()

    # Validate patient exists in current hospital
    cursor.execute(
        "SELECT patient_id FROM patients WHERE patient_id = ? AND hospital_id = ?;",
        (eval_req.patient_id, current_user.hospital_id),
    )
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{eval_req.patient_id}' not found in current hospital tenant",
        )

    evaluator_arn = current_user.arn or "NCISM-ARN-UNREGISTERED"

    output = evaluate_ama_agni(
        req=eval_req,
        evaluator_arn=evaluator_arn,
        hospital_id=current_user.hospital_id,
    )

    directives_json = json.dumps([d.model_dump() for d in output.therapeutic_directives])

    cursor.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute(
            """
            INSERT INTO ama_agni_assessments (
                assessment_id, patient_id, hospital_id, evaluator_arn,
                agi_score, ama_grade, agni_type, agni_vector_json,
                symptoms_json, shodhana_permitted, gating_status,
                therapeutic_directives_json, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                output.assessment_id,
                output.patient_id,
                output.hospital_id,
                output.evaluator_arn,
                output.agi_score,
                output.ama_grade.value,
                output.agni_type.value,
                json.dumps(output.agni_vector),
                eval_req.symptoms.model_dump_json(),
                1 if output.shodhana_permitted else 0,
                output.gating_status.value,
                directives_json,
                output.timestamp,
            ),
        )

        append_audit_log(
            conn=conn,
            hospital_id=current_user.hospital_id,
            actor_id=current_user.user_id,
            action="EVALUATE_AMA_AGNI",
            entity_type="ama_agni_assessment",
            entity_id=output.assessment_id,
            details={
                "patient_id": output.patient_id,
                "agi_score": output.agi_score,
                "ama_grade": output.ama_grade.value,
                "shodhana_permitted": output.shodhana_permitted,
                "gating_status": output.gating_status.value,
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


@router.get("/patients/{patient_id}/latest", response_model=AmaAgniOutput)
def get_latest_ama_agni_assessment(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> AmaAgniOutput:
    """Retrieve the most recent Ama & Agni evaluation for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT assessment_id, patient_id, hospital_id, evaluator_arn,
               agi_score, ama_grade, agni_type, agni_vector_json,
               shodhana_permitted, gating_status, therapeutic_directives_json, timestamp
        FROM ama_agni_assessments
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC, rowid DESC LIMIT 1;
        """,
        (patient_id, current_user.hospital_id),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Ama/Agni assessments recorded for patient '{patient_id}'",
        )

    directives_raw = json.loads(row["therapeutic_directives_json"])
    directives = [TherapeuticDirective(**d) for d in directives_raw]

    return AmaAgniOutput(
        assessment_id=row["assessment_id"],
        patient_id=row["patient_id"],
        hospital_id=row["hospital_id"],
        evaluator_arn=row["evaluator_arn"],
        agi_score=row["agi_score"],
        ama_grade=AmaGrade(row["ama_grade"]),
        agni_type=AgniType(row["agni_type"]),
        agni_vector=json.loads(row["agni_vector_json"]),
        shodhana_permitted=bool(row["shodhana_permitted"]),
        gating_status=GatingStatus(row["gating_status"]),
        therapeutic_directives=directives,
        timestamp=row["timestamp"],
    )


@router.get("/patients/{patient_id}/history", response_model=List[AmaAgniOutput])
def get_ama_agni_assessment_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[AmaAgniOutput]:
    """Retrieve full chronological history of Ama & Agni evaluations for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT assessment_id, patient_id, hospital_id, evaluator_arn,
               agi_score, ama_grade, agni_type, agni_vector_json,
               shodhana_permitted, gating_status, therapeutic_directives_json, timestamp
        FROM ama_agni_assessments
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC, rowid DESC;
        """,
        (patient_id, current_user.hospital_id),
    )
    rows = cursor.fetchall()

    results = []
    for r in rows:
        directives_raw = json.loads(r["therapeutic_directives_json"])
        directives = [TherapeuticDirective(**d) for d in directives_raw]
        results.append(
            AmaAgniOutput(
                assessment_id=r["assessment_id"],
                patient_id=r["patient_id"],
                hospital_id=r["hospital_id"],
                evaluator_arn=r["evaluator_arn"],
                agi_score=r["agi_score"],
                ama_grade=AmaGrade(r["ama_grade"]),
                agni_type=AgniType(r["agni_type"]),
                agni_vector=json.loads(r["agni_vector_json"]),
                shodhana_permitted=bool(r["shodhana_permitted"]),
                gating_status=GatingStatus(r["gating_status"]),
                therapeutic_directives=directives,
                timestamp=r["timestamp"],
            )
        )
    return results
