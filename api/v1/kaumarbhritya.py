"""
API Endpoints for Kaumarbhritya, Bala Roga & Suvarnaprashana Engine.
"""

import json
import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, get_db_session
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.kaumarbhritya import (
    calculate_pediatric_posology,
    initialize_kaumarbhritya_tables,
    list_developmental_milestones,
    list_pediatric_consultations,
    list_suvarnaprashana_doses,
    record_pediatric_consultation,
    record_suvarnaprashana_dose,
)
from models.kaumarbhritya import (
    BalaRogaSyndrome,
    KaumarbhrityaMilestone,
    PediatricConsultationCreate,
    PediatricConsultationResponse,
    PediatricDosageCalculationRequest,
    PediatricDosageCalculationResponse,
    SuvarnaprashanaAdminCreate,
    SuvarnaprashanaAdminResponse,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/kaumarbhritya", tags=["Kaumarbhritya, Bala Roga & Suvarnaprashana Engine"])


@router.get("/milestones", response_model=List[KaumarbhrityaMilestone])
def list_pediatric_milestones(
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[KaumarbhrityaMilestone]:
    """List classical Kaumarbhritya developmental milestones, Samskaras, and age-based posology."""
    return list_developmental_milestones(conn)


@router.post("/posology/calculate", response_model=PediatricDosageCalculationResponse)
def calculate_posology(
    request: PediatricDosageCalculationRequest,
    current_user: UserResponse = Depends(get_current_user),
) -> PediatricDosageCalculationResponse:
    """
    Calculate pediatric drug posology using dual Ayurvedic (Sharngadhara) and Western (Clark/Cowling) rules.
    Enforces Strict Toxicology Firewall against Schedule E-1 poisons and heavy metal Bhasmas in pediatrics.
    """
    try:
        return calculate_pediatric_posology(request)
    except ClinicalGovernanceException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.post("/consultations", response_model=PediatricConsultationResponse, status_code=status.HTTP_201_CREATED)
def log_pediatric_consultation(
    request: PediatricConsultationCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> PediatricConsultationResponse:
    """
    Log a pediatric clinical consultation, diagnose classical Bala Roga syndrome,
    and generate dual-posology calibrated prescription.
    """
    initialize_kaumarbhritya_tables(conn)
    try:
        return record_pediatric_consultation(conn, current_user.hospital_id, request)
    except ClinicalGovernanceException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("/consultations/patient/{patient_id}", response_model=List[PediatricConsultationResponse])
def get_patient_pediatric_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[PediatricConsultationResponse]:
    """Retrieve historical pediatric consultations for a child."""
    initialize_kaumarbhritya_tables(conn)
    return list_pediatric_consultations(patient_id, conn)


@router.post("/suvarnaprashana", response_model=SuvarnaprashanaAdminResponse, status_code=status.HTTP_201_CREATED)
def log_suvarnaprashana_administration(
    request: SuvarnaprashanaAdminCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> SuvarnaprashanaAdminResponse:
    """
    Log administration of Suvarnaprashana on Pushya Nakshatra.
    Enforces Viruddha Ahara firewall: strictly verifies honey and ghee are in non-equal proportion.
    """
    try:
        return record_suvarnaprashana_dose(conn, current_user.hospital_id, request)
    except ClinicalGovernanceException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("/suvarnaprashana/patient/{patient_id}", response_model=List[SuvarnaprashanaAdminResponse])
def get_patient_suvarnaprashana_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[SuvarnaprashanaAdminResponse]:
    """Retrieve historical Suvarnaprashana immunopassport doses for a child."""
    return list_suvarnaprashana_doses(patient_id, conn)
