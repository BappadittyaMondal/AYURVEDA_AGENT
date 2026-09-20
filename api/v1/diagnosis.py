"""API Endpoints for Unified Clinical Diagnostic & Decision Support Orchestrator (A-CDSS)."""
import sqlite3
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_db_session
from core.exceptions import IncompleteClinicalIntakeException, RedFlagEmergencyException
from core.diagnosis_orchestrator import (
    CLASSICAL_DISEASE_PROFILES,
    countersign_diagnosis_episode,
    evaluate_clinical_diagnosis,
    get_patient_diagnosis_episodes,
)
from models.diagnosis_orchestrator import (
    ClinicalIntakeData,
    CounterSignRequest,
    DiagnosisEpisodeResponse,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/diagnosis", tags=["Unified Clinical Diagnosis & Decision Support (A-CDSS)"])


@router.post("/evaluate", response_model=DiagnosisEpisodeResponse, status_code=status.HTTP_201_CREATED)
def run_clinical_diagnosis_evaluation(
    intake: ClinicalIntakeData,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> DiagnosisEpisodeResponse:
    """
    Run autonomous multi-modular diagnostic synthesis, dual-coding (NAMASTE & ICD-11 TM2),
    Ama-Agni gating, and personalized polyherbal treatment formulation.
    """
    try:
        return evaluate_clinical_diagnosis(intake, conn=conn)
    except IncompleteClinicalIntakeException as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)
    except RedFlagEmergencyException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.post("/episodes/{episode_id}/countersign", response_model=DiagnosisEpisodeResponse)
def countersign_episode(
    episode_id: str,
    payload: CounterSignRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> DiagnosisEpisodeResponse:
    """
    Statutory NCISM Physician Digital Counter-signature, transitioning episode
    from DRAFT_DECISION_SUPPORT to PHYSICIAN_COUNTERSIGNED.
    """
    try:
        return countersign_diagnosis_episode(episode_id, payload, conn=conn)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/episodes/patient/{patient_id}", response_model=List[DiagnosisEpisodeResponse])
def get_patient_episodes(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[DiagnosisEpisodeResponse]:
    """Retrieve all diagnostic evaluation episodes for a patient."""
    return get_patient_diagnosis_episodes(patient_id, conn=conn)


@router.get("/disease-catalog", response_model=List[Dict[str, Any]])
def get_morbidity_catalog(
    current_user: UserResponse = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Retrieve available classical disease profiles with dual NAMASTE and ICD-11 TM2 classifications."""
    catalog = []
    for k, v in CLASSICAL_DISEASE_PROFILES.items():
        catalog.append({
            "key": k,
            "sanskrit_name": v["sanskrit_name"],
            "namaste_code": v["namaste_code"],
            "icd11_tm2_code": v["icd11_tm2_code"],
            "icd11_title": v["icd11_title"]
        })
    return catalog
