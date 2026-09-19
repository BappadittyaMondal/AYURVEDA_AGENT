"""
API Endpoints for Marma Sharira, Traumatological Interventions & Marma Chikitsa Engine.
"""

import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, get_db_session
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.marma_sharira import (
    get_marma_by_code,
    initialize_marma_tables,
    list_all_marmas,
    list_patient_marma_chikitsa_sessions,
    list_patient_marma_trauma_admissions,
    record_marma_chikitsa_session,
    triage_marma_trauma_admission,
)
from models.marma_sharira import (
    MarmaChikitsaSessionCreate,
    MarmaChikitsaSessionResponse,
    MarmaParinama,
    MarmaPointProfile,
    MarmaRachana,
    MarmaRegion,
    MarmaTraumaEmergencyCreate,
    MarmaTraumaEmergencyResponse,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/marmas", tags=["Marma Sharira, Traumatology & Marma Chikitsa Engine"])


@router.get("", response_model=List[MarmaPointProfile])
def list_marma_points(
    region: Optional[MarmaRegion] = Query(default=None, description="Filter by anatomical region (SHAKHA, MADHYA_SHARIRA, PRISHTHA, URDHVAJATRU)"),
    rachana: Optional[MarmaRachana] = Query(default=None, description="Filter by tissue structure (MAMSA, SIRA, SNAYU, ASTHI, SANDHI)"),
    parinama: Optional[MarmaParinama] = Query(default=None, description="Filter by prognostic outcome (SADHYO_PRANAHARA, KALANTARA_PRANAHARA, VISHALYAGHNA, VAIKALYAKARA, RUJAKARA)"),
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[MarmaPointProfile]:
    """List vital Marma points with optional multi-attribute filtering."""
    initialize_marma_tables(conn)
    return list_all_marmas(conn, region=region, rachana=rachana, parinama=parinama)


@router.get("/{marma_code}", response_model=MarmaPointProfile)
def get_marma_detail(
    marma_code: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> MarmaPointProfile:
    """Retrieve full anatomical, vulnerability, and emergency management profile by code."""
    initialize_marma_tables(conn)
    try:
        return get_marma_by_code(marma_code, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/trauma-admissions", response_model=MarmaTraumaEmergencyResponse, status_code=status.HTTP_201_CREATED)
def admit_marma_trauma(
    request: MarmaTraumaEmergencyCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> MarmaTraumaEmergencyResponse:
    """
    Log acute Marma trauma intake, triage vulnerability, enforce Tri-Marma
    emergency resuscitation, and enforce Vishalyaghna surgical extraction firewalls.
    """
    initialize_marma_tables(conn)
    return triage_marma_trauma_admission(conn, current_user.hospital_id, request)


@router.get("/trauma-admissions/patient/{patient_id}", response_model=List[MarmaTraumaEmergencyResponse])
def get_patient_trauma_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[MarmaTraumaEmergencyResponse]:
    """Retrieve historical Marma trauma admissions for a patient."""
    initialize_marma_tables(conn)
    return list_patient_marma_trauma_admissions(patient_id, conn)


@router.post("/chikitsa-sessions", response_model=MarmaChikitsaSessionResponse, status_code=status.HTTP_201_CREATED)
def record_chikitsa_session(
    request: MarmaChikitsaSessionCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> MarmaChikitsaSessionResponse:
    """
    Record therapeutic Marma Chikitsa stimulation session, calibrating
    applied pressure, respiratory cycles, and Pranic harmonization response.
    """
    initialize_marma_tables(conn)
    return record_marma_chikitsa_session(conn, current_user.hospital_id, request)


@router.get("/chikitsa-sessions/patient/{patient_id}", response_model=List[MarmaChikitsaSessionResponse])
def get_patient_chikitsa_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[MarmaChikitsaSessionResponse]:
    """Retrieve historical Marma Chikitsa stimulation sessions for a patient."""
    initialize_marma_tables(conn)
    return list_patient_marma_chikitsa_sessions(patient_id, conn)
