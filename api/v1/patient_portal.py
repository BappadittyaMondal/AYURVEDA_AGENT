"""
api/v1/patient_portal.py - API Endpoints for Phase 41: Patient Portal & PWA Interface.
"""

import sqlite3
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_db_session
from models.patient_portal import (
    PatientPortalAccountCreate,
    PatientPortalAccountResponse,
    PatientPortalLoginRequest,
    PatientPortalTokenResponse,
    PatientDailyLogCreate,
    PatientDailyLogRecord,
    PatientHealthSummary,
)
from core.patient_portal import (
    register_patient_portal_account,
    authenticate_patient_portal,
    record_patient_daily_log,
    get_patient_daily_logs,
    get_patient_health_summary,
    PatientPortalError,
)

router = APIRouter(prefix="/patient-portal", tags=["Phase 41: Patient Portal & PWA Interface"])


@router.post(
    "/register",
    response_model=PatientPortalAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a patient portal login account linked to MPI"
)
def register_account_endpoint(
    req: PatientPortalAccountCreate,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return register_patient_portal_account(req, conn=conn)
    except PatientPortalError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/login",
    response_model=PatientPortalTokenResponse,
    summary="Authenticate patient and obtain access token"
)
def login_endpoint(
    req: PatientPortalLoginRequest,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return authenticate_patient_portal(req, conn=conn)
    except PatientPortalError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post(
    "/daily-logs",
    response_model=PatientDailyLogRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Submit daily diet, bowel, sleep, and stress log"
)
def submit_daily_log_endpoint(
    req: PatientDailyLogCreate,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    return record_patient_daily_log(req, conn=conn)


@router.get(
    "/daily-logs/{patient_id}",
    response_model=List[PatientDailyLogRecord],
    summary="Get recent daily logs for a patient"
)
def get_daily_logs_endpoint(
    patient_id: str,
    limit: int = 14,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    return get_patient_daily_logs(patient_id, limit=limit, conn=conn)


@router.get(
    "/summary/{patient_id}",
    response_model=PatientHealthSummary,
    summary="Get patient portal holistic health summary"
)
def get_health_summary_endpoint(
    patient_id: str,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return get_patient_health_summary(patient_id, conn=conn)
    except PatientPortalError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
