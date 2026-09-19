"""
API Endpoints for Shalya Tantra Yantra-Shastra Microsurgical Instruments & Operative Suite.
"""

import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, get_db_session
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.shalya_instruments import (
    get_instrument_by_code,
    initialize_shalya_tables,
    list_all_instruments,
    list_patient_operative_procedures,
    list_practitioner_yogya_assessments,
    record_operative_procedure,
    record_yogya_assessment,
)
from models.schemas import UserResponse
from models.shalya_instruments import (
    InstrumentClass,
    OperativeProcedureCreate,
    OperativeProcedureResponse,
    SurgicalInstrumentProfile,
    YantraCategory,
    YogyaAssessmentCreate,
    YogyaAssessmentResponse,
)

router = APIRouter(prefix="/surgical", tags=["Shalya Tantra Yantra-Shastra & Operative Suite"])


@router.get("/instruments", response_model=List[SurgicalInstrumentProfile])
def list_instruments(
    instrument_type: Optional[InstrumentClass] = Query(default=None, description="Filter by instrument type (YANTRA, SHASTRA)"),
    category: Optional[YantraCategory] = Query(default=None, description="Filter by instrument group (SVASTIKA, SANDAMSHA, TALA, NADI, SHALAKA, UPAYANTRA, SHASTRA)"),
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[SurgicalInstrumentProfile]:
    """List classical blunt (Yantra) and sharp (Shastra) surgical instruments."""
    initialize_shalya_tables(conn)
    return list_all_instruments(conn, instrument_type=instrument_type, category=category)


@router.get("/instruments/{instrument_code}", response_model=SurgicalInstrumentProfile)
def get_instrument_detail(
    instrument_code: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> SurgicalInstrumentProfile:
    """Retrieve full classical specification, target tissues, and sterilization protocol by code."""
    initialize_shalya_tables(conn)
    try:
        return get_instrument_by_code(instrument_code, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/procedures", response_model=OperativeProcedureResponse, status_code=status.HTTP_201_CREATED)
def log_operative_procedure(
    request: OperativeProcedureCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> OperativeProcedureResponse:
    """
    Log an Ashtavidha Shastra Karma surgical procedure, enforcing instrument tracking
    and Kshara-Agni Karma operative safety firewalls.
    """
    initialize_shalya_tables(conn)
    return record_operative_procedure(conn, current_user.hospital_id, request)


@router.get("/procedures/patient/{patient_id}", response_model=List[OperativeProcedureResponse])
def get_patient_operative_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[OperativeProcedureResponse]:
    """Retrieve historical surgical procedures logged for a patient."""
    initialize_shalya_tables(conn)
    return list_patient_operative_procedures(patient_id, conn)


@router.post("/yogya-assessments", response_model=YogyaAssessmentResponse, status_code=status.HTTP_201_CREATED)
def assess_yogya_simulation(
    request: YogyaAssessmentCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> YogyaAssessmentResponse:
    """
    Record surgical simulation training on classical models (Sushruta Sutrasthana Ch. 9)
    and verify competency score threshold (>= 80.0) for clinical operative privileges.
    """
    initialize_shalya_tables(conn)
    return record_yogya_assessment(conn, current_user.hospital_id, request)


@router.get("/yogya-assessments/practitioner/{practitioner_arn}", response_model=List[YogyaAssessmentResponse])
def get_practitioner_simulation_history(
    practitioner_arn: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[YogyaAssessmentResponse]:
    """Retrieve historical Yogya surgical simulation competency assessments for a surgeon."""
    initialize_shalya_tables(conn)
    return list_practitioner_yogya_assessments(practitioner_arn, conn)
