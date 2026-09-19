"""
Phase 34: Paschat Karma & Samsarjana Krama REST API Router
==========================================================
Provides clinical endpoints for:
1. Initiating post-Panchakarma rehabilitation episodes
2. Retrieving episode details, schedules, and patient history
3. Recording bedside Annakala meal consumption logs
4. Analyzing real-time Agni kindling trajectory curves
5. Auditing adherence to Ashta Mahadosha / Parihara Vishayas
6. Evaluating statutory Rasayana & Vajikarana readiness
"""

import sqlite3
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_db_session
from core.paschat_karma import (
    initiate_paschat_karma_episode,
    get_paschat_karma_episode,
    get_patient_paschat_episodes,
    log_samsarjana_meal,
    list_samsarjana_meal_logs,
    compute_samsarjana_trajectory,
    audit_parihara_adherence,
    evaluate_rasayana_readiness,
)
from models.paschat_karma import (
    PaschatKarmaEpisodeCreate,
    PaschatKarmaEpisodeResponse,
    SamsarjanaMealLogCreate,
    SamsarjanaMealLogResponse,
    SamsarjanaTrajectorySummary,
    PariharaAdherenceAuditRequest,
    PariharaAdherenceAuditResponse,
    RasayanaReadinessResponse,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/paschat-karma", tags=["Phase 34: Paschat Karma & Samsarjana Krama"])


@router.post("/episodes", response_model=PaschatKarmaEpisodeResponse, status_code=status.HTTP_201_CREATED)
def create_episode_endpoint(
    req: PaschatKarmaEpisodeCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> PaschatKarmaEpisodeResponse:
    """Initiate a structured post-Panchakarma Paschat Karma rehabilitation episode."""
    try:
        return initiate_paschat_karma_episode(req, conn=conn)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/episodes/{episode_id}", response_model=PaschatKarmaEpisodeResponse)
def get_episode_endpoint(
    episode_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> PaschatKarmaEpisodeResponse:
    """Retrieve full details, status, and Samsarjana Krama schedule for an episode."""
    try:
        return get_paschat_karma_episode(episode_id, conn=conn)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/patients/{patient_id}", response_model=List[PaschatKarmaEpisodeResponse])
def get_patient_episodes_endpoint(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> List[PaschatKarmaEpisodeResponse]:
    """List all historical and active Paschat Karma episodes for a patient."""
    return get_patient_paschat_episodes(patient_id, conn=conn)


@router.post("/episodes/{episode_id}/meals", response_model=SamsarjanaMealLogResponse, status_code=status.HTTP_201_CREATED)
def log_meal_endpoint(
    episode_id: str,
    req: SamsarjanaMealLogCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> SamsarjanaMealLogResponse:
    """Record consumption of a scheduled Annakala meal along with appetite and digestive tolerance."""
    try:
        return log_samsarjana_meal(episode_id, req, conn=conn)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/episodes/{episode_id}/meals", response_model=List[SamsarjanaMealLogResponse])
def list_meals_endpoint(
    episode_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> List[SamsarjanaMealLogResponse]:
    """Retrieve all logged meals recorded for an episode."""
    try:
        return list_samsarjana_meal_logs(episode_id, conn=conn)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/episodes/{episode_id}/trajectory", response_model=SamsarjanaTrajectorySummary)
def get_trajectory_endpoint(
    episode_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> SamsarjanaTrajectorySummary:
    """Compute empirical Agni kindling trajectory curve and clinical recommendations."""
    try:
        return compute_samsarjana_trajectory(episode_id, conn=conn)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/episodes/{episode_id}/parihara-audit", response_model=PariharaAdherenceAuditResponse)
def audit_parihara_endpoint(
    episode_id: str,
    req: PariharaAdherenceAuditRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> PariharaAdherenceAuditResponse:
    """Audit adherence to Ashta Mahadosha prohibitions and recommend classical remedies."""
    try:
        return audit_parihara_adherence(episode_id, req, conn=conn)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/episodes/{episode_id}/rasayana-readiness", response_model=RasayanaReadinessResponse)
def evaluate_rasayana_readiness_endpoint(
    episode_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> RasayanaReadinessResponse:
    """Evaluate whether the patient has completed Samsarjana Krama and is eligible for Rasayana / Vajikarana."""
    try:
        return evaluate_rasayana_readiness(episode_id, conn=conn)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
