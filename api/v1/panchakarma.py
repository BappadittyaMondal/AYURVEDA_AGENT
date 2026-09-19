"""
API Endpoints for Clinical Panchakarma Protocol & Bedside Vega Tracking.
"""

import json
import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_db_session
from core.exceptions import (
    AmaGatingException,
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.panchakarma import (
    create_panchakarma_plan,
    evaluate_panchakarma_shuddhi,
    get_panchakarma_plan,
    list_plan_vegas,
    record_bedside_vega,
)
from models.panchakarma import (
    BedsideVegaEntry,
    BedsideVegaRecord,
    PanchakarmaPlanCreate,
    PanchakarmaPlanResponse,
    ShuddhiEvaluationRequest,
    ShuddhiEvaluationResponse,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/panchakarma", tags=["Clinical Panchakarma Protocol & Bedside Vega Tracking"])


@router.post("/plans", response_model=PanchakarmaPlanResponse, status_code=status.HTTP_201_CREATED)
def initiate_panchakarma_plan(
    plan_in: PanchakarmaPlanCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> PanchakarmaPlanResponse:
    """
    Initiates a clinical Panchakarma treatment plan.
    Strictly gates on Pre-Op AGI score (< 1.80 required; Sama Avastha blocks Shodhana).
    """
    try:
        return create_panchakarma_plan(plan_in, current_user.hospital_id, conn)
    except AmaGatingException as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)
    except ClinicalGovernanceException as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/plans/{plan_id}", response_model=PanchakarmaPlanResponse)
def get_plan_details(
    plan_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> PanchakarmaPlanResponse:
    """Retrieve full clinical Panchakarma treatment plan details."""
    try:
        return get_panchakarma_plan(plan_id, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/vegas", response_model=BedsideVegaRecord, status_code=status.HTTP_201_CREATED)
def log_bedside_vega(
    entry: BedsideVegaEntry,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> BedsideVegaRecord:
    """
    Record real-time bedside Vega observation during Pradhana Karma.
    Advances plan to active PRADHANA_KARMA and monitors for Atiyoga signs.
    """
    try:
        return record_bedside_vega(entry, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/vegas/{plan_id}", response_model=List[BedsideVegaRecord])
def get_plan_vegas(
    plan_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[BedsideVegaRecord]:
    """Retrieve all chronological bedside bouts recorded for a plan."""
    try:
        get_panchakarma_plan(plan_id, conn)  # verify existence
        return list_plan_vegas(plan_id, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/shuddhi/evaluate", response_model=ShuddhiEvaluationResponse)
def evaluate_shuddhi(
    request: ShuddhiEvaluationRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> ShuddhiEvaluationResponse:
    """
    Perform four-fold classical Chaturvidha Shuddhi Pariksha (Vaigiki, Maniki, Antiki, Laingiki).
    Detects Atiyoga complications and generates personalized Samsarjana Krama diet recovery schedule.
    """
    try:
        return evaluate_panchakarma_shuddhi(request, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
