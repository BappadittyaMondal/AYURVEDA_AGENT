"""
API Endpoints for Shalya Tantra, Marma Sharira, Agnikarma & Ksharasutra.
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
from core.shalya_tantra import (
    assess_vrana_wound,
    execute_agnikarma_session,
    evaluate_ksharasutra_session,
    get_marma_profile,
    initialize_shalya_tables,
    list_all_marmas,
    screen_marma_incision_proximity,
)
from models.schemas import UserResponse
from models.shalya_tantra import (
    AgnikarmaSessionCreate,
    AgnikarmaSessionResponse,
    KsharasutraSessionCreate,
    KsharasutraSessionResponse,
    MarmaProfile,
    MarmaProximityCheckRequest,
    MarmaProximityCheckResponse,
    MarmaRegion,
    MarmaType,
    VranaAssessmentCreate,
    VranaAssessmentResponse,
)

router = APIRouter(prefix="/shalya", tags=["Shalya Tantra, Marma Sharira & Agnikarma / Ksharasutra Engine"])


@router.get("/marmas", response_model=List[MarmaProfile])
def list_marmas(
    region: Optional[MarmaRegion] = Query(default=None, description="Filter by anatomical region (SHAKHA, KOSHTHA, etc.)"),
    marma_type: Optional[MarmaType] = Query(default=None, description="Filter by prognostic type (SADYO_PRANAHARA, etc.)"),
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[MarmaProfile]:
    """List all registered classical Marmas with anatomical landmarks and vulnerability specifications."""
    all_marmas = list_all_marmas(conn)
    results: List[MarmaProfile] = []
    for m in all_marmas:
        if region and m.anatomical_region != region:
            continue
        if marma_type and m.marma_type != marma_type:
            continue
        results.append(m)
    return results


@router.get("/marmas/{marma_id}", response_model=MarmaProfile)
def get_marma_detail(
    marma_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> MarmaProfile:
    """Retrieve full anatomical specification and trauma manifestations of a Marma."""
    try:
        return get_marma_profile(marma_id, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/marmas/screen-proximity", response_model=MarmaProximityCheckResponse)
def screen_surgical_marma_proximity(
    request: MarmaProximityCheckRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> MarmaProximityCheckResponse:
    """
    Pre-operative surgical incision screening against vital Marmas.
    Enforces Sadyo-Pranahara shock firewall if incision infringes vulnerability radius.
    """
    try:
        return screen_marma_incision_proximity(request, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/agnikarma/sessions", response_model=AgnikarmaSessionResponse, status_code=status.HTTP_201_CREATED)
def log_agnikarma_procedure(
    request: AgnikarmaSessionCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> AgnikarmaSessionResponse:
    """
    Execute and log Agnikarma thermal cauterization procedure.
    Validates operating temperature, contact duration, and burn grade (Samyak Dagdha vs. Atidagdha).
    """
    initialize_shalya_tables(conn)
    try:
        return execute_agnikarma_session(request, current_user.hospital_id, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/ksharasutra/episodes", response_model=KsharasutraSessionResponse, status_code=status.HTTP_201_CREATED)
def log_ksharasutra_episode(
    request: KsharasutraSessionCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> KsharasutraSessionResponse:
    """
    Log Ksharasutra anorectal fistula treatment episode, compute Unit Cutting Time (UCT),
    and track healing progression.
    """
    initialize_shalya_tables(conn)
    try:
        return evaluate_ksharasutra_session(request, current_user.hospital_id, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/vrana/evaluations", response_model=VranaAssessmentResponse, status_code=status.HTTP_201_CREATED)
def evaluate_surgical_vrana(
    request: VranaAssessmentCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> VranaAssessmentResponse:
    """
    Clinical surgical wound evaluation and Shashti-Upakrama prescription.
    Stages Dusta Vrana vs. Shuddha Vrana vs. Ruhamana Vrana and prescribes topical therapies.
    """
    initialize_shalya_tables(conn)
    try:
        return assess_vrana_wound(request, current_user.hospital_id, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
