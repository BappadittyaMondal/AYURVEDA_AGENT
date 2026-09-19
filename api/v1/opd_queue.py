"""
api/v1/opd_queue.py - API Endpoints for Phase 47: OPD Queue Optimization & Token Flow Management.
"""

import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_current_user, get_db_session
from models.schemas import UserResponse
from models.opd_queue import (
    OpdTokenCreate,
    OpdTokenRecord,
    ConsultationAuditRecord,
    OpdDepartmentQueueStatus,
)
from core.opd_queue import (
    issue_opd_token,
    call_next_opd_token,
    complete_opd_consultation,
    get_department_queue_status,
    OpdQueueError,
)

router = APIRouter(prefix="/opd-queue", tags=["Phase 47: OPD Queue Optimization & Token Flow"])


@router.post(
    "/tokens",
    response_model=OpdTokenRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a multi-priority outpatient queue token"
)
def issue_token_endpoint(
    req: OpdTokenCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
):
    return issue_opd_token(req, current_user=current_user, conn=conn)


@router.post(
    "/departments/{department}/call-next",
    response_model=Optional[OpdTokenRecord],
    summary="Call next highest priority waiting patient for physician"
)
def call_next_endpoint(
    department: str,
    physician_arn: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
):
    token = call_next_opd_token(department, physician_arn=physician_arn, conn=conn)
    if not token:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="No waiting patients in this department queue.")
    return token


@router.post(
    "/tokens/{token_id}/complete",
    response_model=ConsultationAuditRecord,
    summary="Complete consultation and record efficiency audit"
)
def complete_consultation_endpoint(
    token_id: str,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return complete_opd_consultation(token_id, conn=conn)
    except OpdQueueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/departments/{department}/status",
    response_model=OpdDepartmentQueueStatus,
    summary="Get live queue status for an OPD department"
)
def get_queue_status_endpoint(
    department: str,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    return get_department_queue_status(department, conn=conn)
