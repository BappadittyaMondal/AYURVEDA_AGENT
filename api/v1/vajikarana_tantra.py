"""
API Endpoints for Vajikarana Tantra, Shukra Dushti & Reproductive Eugenics Engine.
"""

import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, get_db_session
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.vajikarana_tantra import (
    evaluate_semen_analysis,
    get_shukra_dushti_by_code,
    initialize_vajikarana_tables,
    list_all_shukra_dushtis,
    list_patient_semen_analyses,
    list_patient_vajikarana_prescriptions,
    prescribe_vajikarana_protocol,
)
from models.schemas import UserResponse
from models.vajikarana_tantra import (
    SemenAnalysisCreate,
    SemenAnalysisResponse,
    ShukraDushtiProfile,
    VajikaranaPrescriptionCreate,
    VajikaranaPrescriptionResponse,
)

router = APIRouter(prefix="/vajikarana", tags=["Vajikarana Tantra, Shukra Dushti & Andrology Engine"])


@router.get("/dushti-registry", response_model=List[ShukraDushtiProfile])
def list_dushtis(
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[ShukraDushtiProfile]:
    """List the 8 classical Shukra Dushtis with Doshic etiologies and WHO semen correlates."""
    initialize_vajikarana_tables(conn)
    return list_all_shukra_dushtis(conn)


@router.get("/dushti-registry/{dushti_code}", response_model=ShukraDushtiProfile)
def get_dushti_detail(
    dushti_code: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> ShukraDushtiProfile:
    """Retrieve full classical profile, WHO semen correlate, and Shodhana therapies by code."""
    initialize_vajikarana_tables(conn)
    try:
        return get_shukra_dushti_by_code(dushti_code, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/semen-analysis", response_model=SemenAnalysisResponse, status_code=status.HTTP_201_CREATED)
def analyze_semen(
    request: SemenAnalysisCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> SemenAnalysisResponse:
    """
    Ingest WHO 6th edition semen analysis, calculate composite Shukra Shuddhi Score,
    map to Ayurvedic Ashta Shukra Dushti, and assess fertility prognosis.
    """
    initialize_vajikarana_tables(conn)
    return evaluate_semen_analysis(conn, current_user.hospital_id, request)


@router.get("/semen-analysis/patient/{patient_id}", response_model=List[SemenAnalysisResponse])
def get_patient_semen_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[SemenAnalysisResponse]:
    """Retrieve historical semen analysis diagnostic records for a patient."""
    initialize_vajikarana_tables(conn)
    return list_patient_semen_analyses(patient_id, conn)


@router.post("/prescriptions", response_model=VajikaranaPrescriptionResponse, status_code=status.HTTP_201_CREATED)
def prescribe_vajikarana(
    request: VajikaranaPrescriptionCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> VajikaranaPrescriptionResponse:
    """
    Formulate personalized Vajikarana regimen matching Klaibya pathology,
    enforcing pre-Vajikarana Shodhana verification and Ama safety firewalls.
    """
    initialize_vajikarana_tables(conn)
    return prescribe_vajikarana_protocol(conn, current_user.hospital_id, request)


@router.get("/prescriptions/patient/{patient_id}", response_model=List[VajikaranaPrescriptionResponse])
def get_patient_prescription_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[VajikaranaPrescriptionResponse]:
    """Retrieve historical Vajikarana treatment protocols for a patient."""
    initialize_vajikarana_tables(conn)
    return list_patient_vajikarana_prescriptions(patient_id, conn)
