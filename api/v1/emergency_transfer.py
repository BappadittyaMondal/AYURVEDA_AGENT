"""
Phase 35: REST API Router for Western Emergency Break-Glass & Acute Critical Care Transfer (NABH COP.6)
=======================================================================================================
Provides clinical endpoints for:
1. Triggering emergency break-glass protocol and state lockdown
2. Generating standardized bilingual SBAR transfer handover reports
3. Dispatching advanced cardiac life support ambulances and notifying allopathic ICUs
4. Real-time physiological telemetry risk screening
"""

import sqlite3
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_db_session
from core.emergency_transfer import (
    trigger_emergency_break_glass,
    execute_critical_care_transfer,
    get_break_glass_event,
    evaluate_vital_instability,
)
from models.emergency_transfer import (
    EmergencyBreakGlassRequest,
    EmergencyBreakGlassResponse,
    CriticalCareTransferRequest,
    CriticalCareTransferResponse,
    VitalSignsTelemetry,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/emergency", tags=["Phase 35: Western Emergency Break-Glass & Transfer (NABH COP.6)"])


@router.post("/break-glass", response_model=EmergencyBreakGlassResponse, status_code=status.HTTP_201_CREATED)
def trigger_break_glass_endpoint(
    req: EmergencyBreakGlassRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> EmergencyBreakGlassResponse:
    """Execute immediate emergency break-glass protocol and initiate tertiary ICU transfer under NABH COP.6."""
    try:
        return trigger_emergency_break_glass(req, conn=conn)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/transfer", response_model=CriticalCareTransferResponse, status_code=status.HTTP_201_CREATED)
def execute_transfer_endpoint(
    req: CriticalCareTransferRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> CriticalCareTransferResponse:
    """Record execution of ambulance dispatch, allopathic ICU notification, and signed handover."""
    try:
        return execute_critical_care_transfer(req, conn=conn)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/events/{event_id}", response_model=EmergencyBreakGlassResponse)
def get_event_endpoint(
    event_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> EmergencyBreakGlassResponse:
    """Retrieve full details of an emergency break-glass event and bilingual SBAR report."""
    try:
        return get_break_glass_event(event_id, conn=conn)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/vitals/evaluate", response_model=List[str])
def evaluate_vitals_endpoint(
    vitals: VitalSignsTelemetry,
    current_user: UserResponse = Depends(get_current_user)
) -> List[str]:
    """Rapidly screen patient vitals telemetry for physiological deterioration flags."""
    return evaluate_vital_instability(vitals)
