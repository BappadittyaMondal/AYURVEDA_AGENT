"""
API Endpoints for Nidana Panchaka Diagnostic Knowledge Graph & Differential Diagnosis Engine.
"""

import json
import sqlite3
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_db_session, require_action
from core.database import append_audit_log
from core.nidana_panchaka import (
    DISEASE_ARCHETYPE_REGISTRY,
    evaluate_nidana_panchaka,
    get_latest_nidana_panchaka_assessment,
    get_nidana_panchaka_history,
    save_nidana_panchaka_assessment,
)
from core.security import ClinicalAction
from models.nidana_panchaka import (
    DiseaseArchetype,
    DifferentialDiagnosisItem,
    NidanaPanchakaEvaluationInput,
    NidanaPanchakaEvaluationOutput,
    SampraptiGhatakas,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/nidana-panchaka", tags=["Nidana Panchaka Differential Diagnostics"])


@router.get("/diseases", response_model=List[DiseaseArchetype])
def list_disease_archetypes(
    current_user: UserResponse = Depends(get_current_user),
) -> List[DiseaseArchetype]:
    """Retrieves all registered classical disease archetypes with full Nidana Panchaka ontologies."""
    return list(DISEASE_ARCHETYPE_REGISTRY.values())


@router.get("/diseases/{disease_code}", response_model=DiseaseArchetype)
def get_disease_archetype(
    disease_code: str,
    current_user: UserResponse = Depends(get_current_user),
) -> DiseaseArchetype:
    """Retrieves a specific disease archetype by classical code."""
    code_upper = disease_code.upper()
    if code_upper not in DISEASE_ARCHETYPE_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disease archetype '{disease_code}' not found in registry",
        )
    return DISEASE_ARCHETYPE_REGISTRY[code_upper]


@router.post("/evaluate", response_model=NidanaPanchakaEvaluationOutput, status_code=status.HTTP_201_CREATED)
def evaluate_differential_diagnosis(
    eval_input: NidanaPanchakaEvaluationInput,
    current_user: UserResponse = Depends(require_action(ClinicalAction.ASSESS_TRIDOSHA)),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> NidanaPanchakaEvaluationOutput:
    """
    Executes algorithmic differential diagnosis matching across all registered classical disease archetypes,
    evaluating Nidana, Purvaroopa, Roopa, Upashaya, and Samprapti vectors.
    """
    cursor = conn.cursor()

    # Verify patient exists in tenant hospital
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

    output = evaluate_nidana_panchaka(
        input_data=eval_input,
        evaluator_arn=evaluator_arn,
        hospital_id=current_user.hospital_id,
    )

    cursor.execute("BEGIN IMMEDIATE;")
    try:
        save_nidana_panchaka_assessment(conn, output, eval_input)

        append_audit_log(
            conn=conn,
            hospital_id=current_user.hospital_id,
            actor_id=current_user.user_id,
            action="EVALUATE_NIDANA_PANCHAKA",
            entity_type="nidana_panchaka_assessment",
            entity_id=output.assessment_id,
            details={
                "patient_id": output.patient_id,
                "primary_diagnosis_code": output.primary_diagnosis.disease_code,
                "confidence_score": output.primary_diagnosis.confidence_score,
                "match_score": output.primary_diagnosis.match_score,
                "pratyatma_linga_count": len(output.pratyatma_linga_matched),
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


def _row_to_output(row: dict) -> NidanaPanchakaEvaluationOutput:
    """Helper to deserialize database row into NidanaPanchakaEvaluationOutput."""
    differentials_raw = json.loads(row["differentials_json"])
    differentials = [DifferentialDiagnosisItem(**d) for d in differentials_raw]

    primary_diff = DifferentialDiagnosisItem(
        disease_code=row["primary_diagnosis_code"],
        disease_name=row["primary_diagnosis_name"],
        match_score=row["match_score"],
        confidence_score=row["confidence_score"],
        matched_roopa=json.loads(row["presented_roopa_json"]),
        matched_purvaroopa=json.loads(row["presented_purvaroopa_json"]),
        matched_nidana=json.loads(row["presented_nidana_json"]),
        matched_upashaya=[],
        pratyatma_linga_matched=json.loads(row["pratyatma_linga_matched_json"]),
        key_differentiators=[],
        exclusion_rationale=None,
    )

    samprapti = SampraptiGhatakas(**json.loads(row["samprapti_ghatakas_json"]))

    return NidanaPanchakaEvaluationOutput(
        assessment_id=row["assessment_id"],
        patient_id=row["patient_id"],
        hospital_id=row["hospital_id"],
        evaluator_arn=row["evaluator_arn"],
        primary_diagnosis=primary_diff,
        differential_diagnoses=differentials,
        samprapti_ghatakas=samprapti,
        pratyatma_linga_matched=json.loads(row["pratyatma_linga_matched_json"]),
        clinical_recommendations=json.loads(row["clinical_recommendations_json"]),
        timestamp=row["timestamp"],
    )


@router.get("/patients/{patient_id}/latest", response_model=NidanaPanchakaEvaluationOutput)
def get_latest_assessment(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> NidanaPanchakaEvaluationOutput:
    """Retrieves the latest verified Nidana Panchaka differential diagnostic evaluation for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT patient_id FROM patients WHERE patient_id = ? AND hospital_id = ?;",
        (patient_id, current_user.hospital_id),
    )
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found in current hospital tenant",
        )

    row = get_latest_nidana_panchaka_assessment(conn, patient_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Nidana Panchaka assessments found for patient '{patient_id}'",
        )

    return _row_to_output(row)


@router.get("/patients/{patient_id}/history", response_model=List[NidanaPanchakaEvaluationOutput])
def get_assessment_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[NidanaPanchakaEvaluationOutput]:
    """Retrieves chronological trajectory of differential diagnosis evaluations for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT patient_id FROM patients WHERE patient_id = ? AND hospital_id = ?;",
        (patient_id, current_user.hospital_id),
    )
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found in current hospital tenant",
        )

    rows = get_nidana_panchaka_history(conn, patient_id)
    return [_row_to_output(r) for r in rows]
