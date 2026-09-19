"""
API Endpoints for Upakarma & Bahya Parimarjana Therapy Matrix.
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
from core.upakarma import (
    get_therapy_profile,
    list_all_therapies,
    list_patient_upakarma_sessions,
    log_upakarma_session,
    screen_pre_session_safety,
)
from models.schemas import UserResponse
from models.upakarma import (
    PreSessionScreeningRequest,
    PreSessionScreeningResponse,
    UpakarmaModality,
    UpakarmaSessionCreate,
    UpakarmaSessionRecord,
    UpakarmaTherapy,
)

router = APIRouter(prefix="/upakarma", tags=["Upakarma & Bahya Parimarjana External Therapies"])


@router.get("/therapies", response_model=List[UpakarmaTherapy])
def list_therapies(
    modality: Optional[UpakarmaModality] = Query(default=None, description="Filter by modality code"),
    q: Optional[str] = Query(default=None, description="Search by Sanskrit name, indication, or medium"),
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[UpakarmaTherapy]:
    """Search and browse classical Bahya Parimarjana therapies."""
    all_items = list_all_therapies(conn)
    results: List[UpakarmaTherapy] = []

    for t in all_items:
        if modality and t.modality_code != modality:
            continue
        if q:
            term = q.lower()
            if (
                term in t.sanskrit_name.lower()
                or term in t.doshic_affinity.lower()
                or any(term in ind.lower() for ind in t.cardinal_indications)
                or any(term in med.lower() for med in t.recommended_media)
            ):
                results.append(t)
        else:
            results.append(t)

    return results


@router.get("/therapies/{therapy_id}", response_model=UpakarmaTherapy)
def get_therapy_detail(
    therapy_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> UpakarmaTherapy:
    """Retrieve full therapy specifications, temperature boundaries, and contraindications."""
    try:
        return get_therapy_profile(therapy_id, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/safety/validate", response_model=PreSessionScreeningResponse)
def validate_pre_session_safety(
    request: PreSessionScreeningRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> PreSessionScreeningResponse:
    """Screen patient for contraindications and validate proposed delivery temperature."""
    try:
        return screen_pre_session_safety(request, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/sessions", response_model=UpakarmaSessionRecord, status_code=status.HTTP_201_CREATED)
def record_session(
    request: UpakarmaSessionCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> UpakarmaSessionRecord:
    """Log an administered Upakarma therapy session with thermodynamic safety verification."""
    try:
        return log_upakarma_session(request, current_user.hospital_id, conn)
    except ClinicalGovernanceException as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/sessions/patient/{patient_id}", response_model=List[UpakarmaSessionRecord])
def get_patient_sessions(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[UpakarmaSessionRecord]:
    """Retrieve all external therapy sessions for a patient."""
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM patients WHERE patient_id = ?;", (patient_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient '{patient_id}' not found")

    return list_patient_upakarma_sessions(patient_id, conn)
