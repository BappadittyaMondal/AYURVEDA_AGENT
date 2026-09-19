"""
API Endpoints for Prasuti Tantra, Stri Roga & Garbhini Paricharya Engine.
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
from core.prasuti_tantra import (
    evaluate_fertility_readiness,
    get_garbhini_month_regimen,
    get_yoni_vyapad_profile,
    initialize_prasuti_tables,
    list_all_month_regimens,
    list_all_yoni_vyapads,
    list_antenatal_consultations,
    list_yoni_vyapad_assessments,
    record_antenatal_consultation,
    record_yoni_vyapad_assessment,
)
from models.prasuti_tantra import (
    AntenatalConsultationCreate,
    AntenatalConsultationResponse,
    DoshicClass,
    FertilityReadinessRequest,
    FertilityReadinessResponse,
    GarbhiniMonthRegimen,
    YoniVyapadAssessmentCreate,
    YoniVyapadAssessmentResponse,
    YoniVyapadProfile,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/prasuti", tags=["Prasuti Tantra, Stri Roga & Garbhini Paricharya Engine"])


@router.post("/fertility-readiness", response_model=FertilityReadinessResponse)
def assess_fertility_readiness(
    request: FertilityReadinessRequest,
    current_user: UserResponse = Depends(get_current_user),
) -> FertilityReadinessResponse:
    """
    Evaluate Garbha Sambhava Samagri 4-factor preconception readiness (Ritu, Kshetra, Ambu, Beeja).
    Returns Composite Readiness Score (CRS) and preconception Shodhana/Rasayana guidance.
    """
    return evaluate_fertility_readiness(request)


@router.get("/garbhini-regimen", response_model=List[GarbhiniMonthRegimen])
def list_garbhini_regimens(
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[GarbhiniMonthRegimen]:
    """List classical month-by-month Garbhini Paricharya regimens for all 9 months."""
    return list_all_month_regimens(conn)


@router.get("/garbhini-regimen/{month_number}", response_model=GarbhiniMonthRegimen)
def get_garbhini_regimen_by_month(
    month_number: int,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> GarbhiniMonthRegimen:
    """Retrieve detailed Garbhini Paricharya regimen for a specific gestational month (1-9)."""
    if month_number < 1 or month_number > 9:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gestational month must be between 1 and 9."
        )
    try:
        return get_garbhini_month_regimen(month_number, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/antenatal-consultations", response_model=AntenatalConsultationResponse, status_code=status.HTTP_201_CREATED)
def log_antenatal_consultation(
    request: AntenatalConsultationCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> AntenatalConsultationResponse:
    """
    Log an antenatal consultation examination.
    Evaluates gestational month regimen, Dauhrida fulfillment, and triggers High-Risk Obstetric Triage.
    """
    initialize_prasuti_tables(conn)
    return record_antenatal_consultation(conn, current_user.hospital_id, request)


@router.get("/antenatal-consultations/patient/{patient_id}", response_model=List[AntenatalConsultationResponse])
def get_patient_antenatal_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[AntenatalConsultationResponse]:
    """Retrieve historical antenatal consultation records for a patient."""
    initialize_prasuti_tables(conn)
    return list_antenatal_consultations(patient_id, conn)


@router.get("/yoni-vyapads", response_model=List[YoniVyapadProfile])
def list_yoni_vyapads(
    doshic_class: Optional[DoshicClass] = Query(default=None, description="Filter by Doshic class (VATAJA, PITTAJA, KAPHAJA, SANNIPATAJA)"),
    current_user: UserResponse = Depends(get_current_user),
) -> List[YoniVyapadProfile]:
    """List all 20 classical Yoni Vyapad gynecological conditions with dual ICD-11 coding."""
    return list_all_yoni_vyapads(doshic_class)


@router.get("/yoni-vyapads/{vyapad_code}", response_model=YoniVyapadProfile)
def get_yoni_vyapad_detail(
    vyapad_code: str,
    current_user: UserResponse = Depends(get_current_user),
) -> YoniVyapadProfile:
    """Retrieve full specification, pathogenesis, and treatment of a Yoni Vyapad."""
    try:
        return get_yoni_vyapad_profile(vyapad_code)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/yoni-vyapad/assessments", response_model=YoniVyapadAssessmentResponse, status_code=status.HTTP_201_CREATED)
def assess_yoni_vyapad_condition(
    request: YoniVyapadAssessmentCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> YoniVyapadAssessmentResponse:
    """Record a clinical Yoni Vyapad gynecological diagnosis and generate localized/oral prescription."""
    try:
        return record_yoni_vyapad_assessment(conn, current_user.hospital_id, request)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/yoni-vyapad/assessments/patient/{patient_id}", response_model=List[YoniVyapadAssessmentResponse])
def get_patient_yoni_vyapad_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[YoniVyapadAssessmentResponse]:
    """Retrieve historical Yoni Vyapad assessments for a patient."""
    return list_yoni_vyapad_assessments(patient_id, conn)
