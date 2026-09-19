"""
API Endpoints for Agada Tantra, Visha Chikitsa & Environmental Toxicology Engine.
"""

import json
import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, get_db_session
from core.agada_tantra import (
    get_visha_profile,
    initialize_agada_tables,
    list_all_vishas,
    list_dushi_visha_assessments,
    list_visha_emergency_admissions,
    record_dushi_visha_assessment,
    record_visha_emergency_admission,
)
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from models.agada_tantra import (
    DushiVishaAssessmentCreate,
    DushiVishaAssessmentResponse,
    EnvenomationSyndrome,
    ToxicEmergencyTriage,
    VishaCategory,
    VishaEmergencyAdmissionCreate,
    VishaEmergencyAdmissionResponse,
    VishaProfile,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/agada", tags=["Agada Tantra, Visha Chikitsa & Toxicology Engine"])


@router.get("/toxins", response_model=List[VishaProfile])
def list_toxins(
    category: Optional[VishaCategory] = Query(default=None, description="Filter by category (STHAVARA, JANGAMA, DUSHI_VISHA, GARA_VISHA)"),
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[VishaProfile]:
    """List registered classical toxins, venoms, and environmental toxicants."""
    return list_all_vishas(conn, category=category)


@router.get("/toxins/{visha_code}", response_model=VishaProfile)
def get_toxin_detail(
    visha_code: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> VishaProfile:
    """Retrieve full toxicological profile and antidote mapping of a toxin by code."""
    try:
        return get_visha_profile(visha_code, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/envenomation-admissions", response_model=VishaEmergencyAdmissionResponse, status_code=status.HTTP_201_CREATED)
def admit_envenomation_emergency(
    request: VishaEmergencyAdmissionCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> VishaEmergencyAdmissionResponse:
    """
    Log acute envenomation admission, perform 20WBCT and neurotoxic triage,
    enforce Anti-Snake Venom (ASV) firewall, and coordinate classical 24-Upakramas.
    """
    initialize_agada_tables(conn)
    return record_visha_emergency_admission(conn, current_user.hospital_id, request)


@router.get("/envenomation-admissions/patient/{patient_id}", response_model=List[VishaEmergencyAdmissionResponse])
def get_patient_envenomation_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[VishaEmergencyAdmissionResponse]:
    """Retrieve historical envenomation admission episodes for a patient."""
    initialize_agada_tables(conn)
    return list_visha_emergency_admissions(patient_id, conn)


@router.post("/dushi-visha/assessments", response_model=DushiVishaAssessmentResponse, status_code=status.HTTP_201_CREATED)
def assess_dushi_visha_condition(
    request: DushiVishaAssessmentCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> DushiVishaAssessmentResponse:
    """
    Assess chronic latent toxic bioaccumulation (Dushi Visha),
    evaluate environmental triggers, and prescribe Dooshivishari Agada with Shodhana regimen.
    """
    initialize_agada_tables(conn)
    return record_dushi_visha_assessment(conn, current_user.hospital_id, request)


@router.get("/dushi-visha/assessments/patient/{patient_id}", response_model=List[DushiVishaAssessmentResponse])
def get_patient_dushi_visha_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[DushiVishaAssessmentResponse]:
    """Retrieve historical Dushi Visha assessments for a patient."""
    initialize_agada_tables(conn)
    return list_dushi_visha_assessments(patient_id, conn)
