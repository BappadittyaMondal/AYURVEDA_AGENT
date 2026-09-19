"""API Endpoints for Dhatu Sarata Quantitative Tissue Vitality Index (7 Dhatus + Sattva)."""
import json
import sqlite3
import time
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_db_session, require_action
from core.database import append_audit_log
from core.dhatu_sarata import evaluate_dhatu_sarata
from core.security import ClinicalAction
from models.dhatu_sarata import (
    DhatuType,
    SarataTier,
    DhatuSarataInput,
    DhatuSarataOutput,
    DhatuRasayanaDirective,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/dhatu-sarata", tags=["Dhatu Sarata Tissue Vitality Index"])


@router.get("/reference", response_model=List[Dict[str, str]])
def get_dhatu_sarata_reference(
    current_user: UserResponse = Depends(get_current_user),
) -> List[Dict[str, str]]:
    """Retrieve the Ashta Sara Purusha classification reference from Charaka Vimanasthana 8."""
    return [
        {"dhatu": "RASA", "sanskrit": "Tvak / Rasa Sara", "attribute": "Plasma/lymph vitality, dermal lustre, unctuous hair"},
        {"dhatu": "RAKTA", "sanskrit": "Rakta Sara", "attribute": "Blood vitality, crimson lips/tongue/palms, brilliance"},
        {"dhatu": "MAMSA", "sanskrit": "Mamsa Sara", "attribute": "Muscle vitality, muscular development, firmness, stability"},
        {"dhatu": "MEDA", "sanskrit": "Meda Sara", "attribute": "Adipose vitality, joint lubrication, resonant voice"},
        {"dhatu": "ASTHI", "sanskrit": "Asthi Sara", "attribute": "Bone tissue vitality, teeth integrity, skeletal endurance"},
        {"dhatu": "MAJJA", "sanskrit": "Majja Sara", "attribute": "Bone marrow / neural vitality, joint suppleness, intellect"},
        {"dhatu": "SHUKRA", "sanskrit": "Shukra Sara", "attribute": "Reproductive / regenerative tissue, cellular vigor, Ojas"},
        {"dhatu": "SATTVA", "sanskrit": "Sattva Sara", "attribute": "Psychological vitality, mental resilience, fortitude"},
    ]


@router.post("/evaluate", response_model=DhatuSarataOutput, status_code=status.HTTP_201_CREATED)
def evaluate_patient_dhatu_sarata(
    eval_input: DhatuSarataInput,
    current_user: UserResponse = Depends(require_action(ClinicalAction.ASSESS_TRIDOSHA)),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> DhatuSarataOutput:
    """Evaluate 8-fold tissue vitality, calculate Overall Sarata Index, and generate Rasayana protocols."""
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

    output = evaluate_dhatu_sarata(
        input_data=eval_input,
        evaluator_arn=evaluator_arn,
        hospital_id=current_user.hospital_id,
    )

    directives_json = json.dumps([d.model_dump() for d in output.rasayana_directives])

    cursor.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute(
            """
            INSERT INTO dhatu_sarata_assessments (
                assessment_id, patient_id, hospital_id, evaluator_arn,
                overall_sarata_index, sarata_tier, dhatu_scores_json,
                vulnerable_dhatus_json, rasayana_directives_json, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                output.assessment_id,
                output.patient_id,
                output.hospital_id,
                output.evaluator_arn,
                output.overall_sarata_index,
                output.sarata_tier.value,
                json.dumps(output.dhatu_scores),
                json.dumps(output.vulnerable_dhatus),
                directives_json,
                output.timestamp,
            ),
        )

        append_audit_log(
            conn=conn,
            hospital_id=current_user.hospital_id,
            actor_id=current_user.user_id,
            action="EVALUATE_DHATU_SARATA",
            entity_type="dhatu_sarata_assessment",
            entity_id=output.assessment_id,
            details={
                "patient_id": output.patient_id,
                "overall_sarata_index": output.overall_sarata_index,
                "sarata_tier": output.sarata_tier.value,
                "vulnerable_dhatus_count": len(output.vulnerable_dhatus),
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


@router.get("/patients/{patient_id}/latest", response_model=DhatuSarataOutput)
def get_latest_dhatu_sarata_assessment(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> DhatuSarataOutput:
    """Retrieve the most recent Dhatu Sarata evaluation for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT assessment_id, patient_id, hospital_id, evaluator_arn,
               overall_sarata_index, sarata_tier, dhatu_scores_json,
               vulnerable_dhatus_json, rasayana_directives_json, timestamp
        FROM dhatu_sarata_assessments
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC, rowid DESC LIMIT 1;
        """,
        (patient_id, current_user.hospital_id),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Dhatu Sarata assessments recorded for patient '{patient_id}'",
        )

    directives_raw = json.loads(row["rasayana_directives_json"])
    directives = [DhatuRasayanaDirective(**d) for d in directives_raw]

    return DhatuSarataOutput(
        assessment_id=row["assessment_id"],
        patient_id=row["patient_id"],
        hospital_id=row["hospital_id"],
        evaluator_arn=row["evaluator_arn"],
        overall_sarata_index=row["overall_sarata_index"],
        sarata_tier=SarataTier(row["sarata_tier"]),
        dhatu_scores=json.loads(row["dhatu_scores_json"]),
        vulnerable_dhatus=json.loads(row["vulnerable_dhatus_json"]),
        rasayana_directives=directives,
        timestamp=row["timestamp"],
    )


@router.get("/patients/{patient_id}/history", response_model=List[DhatuSarataOutput])
def get_dhatu_sarata_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[DhatuSarataOutput]:
    """Retrieve full chronological history of Dhatu Sarata evaluations for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT assessment_id, patient_id, hospital_id, evaluator_arn,
               overall_sarata_index, sarata_tier, dhatu_scores_json,
               vulnerable_dhatus_json, rasayana_directives_json, timestamp
        FROM dhatu_sarata_assessments
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC, rowid DESC;
        """,
        (patient_id, current_user.hospital_id),
    )
    rows = cursor.fetchall()

    results = []
    for r in rows:
        directives_raw = json.loads(r["rasayana_directives_json"])
        directives = [DhatuRasayanaDirective(**d) for d in directives_raw]
        results.append(
            DhatuSarataOutput(
                assessment_id=r["assessment_id"],
                patient_id=r["patient_id"],
                hospital_id=r["hospital_id"],
                evaluator_arn=r["evaluator_arn"],
                overall_sarata_index=r["overall_sarata_index"],
                sarata_tier=SarataTier(r["sarata_tier"]),
                dhatu_scores=json.loads(r["dhatu_scores_json"]),
                vulnerable_dhatus=json.loads(r["vulnerable_dhatus_json"]),
                rasayana_directives=directives,
                timestamp=r["timestamp"],
            )
        )
    return results
