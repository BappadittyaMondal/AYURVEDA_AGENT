"""
api/v1/clinical_trials.py - API Endpoints for Phase 45: Clinical Trial Registry & Integrative Research (CTRI).
"""

import sqlite3
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_current_user, get_db_session
from models.schemas import UserResponse
from models.clinical_trials import (
    ProtocolCreate,
    ProtocolRecord,
    SubjectEnrollmentCreate,
    SubjectRecord,
    SubjectProgressUpdate,
    TrialAnalyticsSummary,
)
from core.clinical_trials import (
    register_trial_protocol,
    get_trial_protocol,
    enroll_trial_subject,
    update_subject_progress,
    compute_trial_analytics,
    ClinicalTrialError,
)

router = APIRouter(prefix="/clinical-trials", tags=["Phase 45: Clinical Trials & CTRI Module"])


@router.post(
    "/protocols",
    response_model=ProtocolRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new clinical trial protocol under CTRI governance"
)
def create_protocol_endpoint(
    req: ProtocolCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return register_trial_protocol(req, current_user=current_user, conn=conn)
    except ClinicalTrialError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/protocols/{protocol_id}",
    response_model=ProtocolRecord,
    summary="Get trial protocol specifications"
)
def get_protocol_endpoint(
    protocol_id: str,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    protocol = get_trial_protocol(protocol_id, conn=conn)
    if not protocol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Protocol '{protocol_id}' not found.")
    return protocol


@router.post(
    "/subjects",
    response_model=SubjectRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll patient subject into randomized study arm"
)
def enroll_subject_endpoint(
    req: SubjectEnrollmentCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return enroll_trial_subject(req, current_user=current_user, conn=conn)
    except ClinicalTrialError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/subjects/{subject_id}/progress",
    response_model=SubjectRecord,
    summary="Update subject outcome scores and therapy compliance"
)
def update_progress_endpoint(
    subject_id: str,
    update: SubjectProgressUpdate,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return update_subject_progress(subject_id, update, conn=conn)
    except ClinicalTrialError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/protocols/{protocol_id}/analytics",
    response_model=TrialAnalyticsSummary,
    summary="Compute comparative efficacy analytics and effect size for trial"
)
def get_analytics_endpoint(
    protocol_id: str,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return compute_trial_analytics(protocol_id, conn=conn)
    except ClinicalTrialError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
