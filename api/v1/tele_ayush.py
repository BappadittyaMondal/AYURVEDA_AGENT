"""
Phase 38: REST API Router for Tele-AYUSH & Digital e-Prescription
=================================================================
Provides clinical endpoints for:
1. Scheduling and managing Tele-AYUSH consultations
2. Generating cryptographic QR-verified e-prescriptions
3. Verifying prescription authenticity
"""

import sqlite3
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_db_session
from core.tele_ayush import (
    schedule_tele_consultation,
    issue_digital_eprescription,
    verify_eprescription,
)
from models.tele_ayush import (
    TeleConsultationCreate,
    TeleConsultationResponse,
    DigitalPrescriptionCreate,
    DigitalPrescriptionResponse,
    PrescriptionVerificationResponse,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/tele-ayush", tags=["Phase 38: Tele-AYUSH & Digital e-Prescriptions"])


@router.post("/sessions", response_model=TeleConsultationResponse, status_code=status.HTTP_201_CREATED)
def schedule_session_endpoint(
    req: TeleConsultationCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> TeleConsultationResponse:
    """Schedule a remote Tele-AYUSH clinical consultation."""
    return schedule_tele_consultation(req, conn=conn)


@router.post("/prescriptions", response_model=DigitalPrescriptionResponse, status_code=status.HTTP_201_CREATED)
def issue_prescription_endpoint(
    req: DigitalPrescriptionCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> DigitalPrescriptionResponse:
    """Issue a tamper-evident, cryptographic QR-verified digital prescription."""
    return issue_digital_eprescription(req, conn=conn)


@router.get("/prescriptions/{prescription_id}/verify", response_model=PrescriptionVerificationResponse)
def verify_prescription_endpoint(
    prescription_id: str,
    conn: sqlite3.Connection = Depends(get_db_session)
) -> PrescriptionVerificationResponse:
    """Verify cryptographic authenticity and validity of an issued digital e-prescription."""
    try:
        return verify_eprescription(prescription_id, conn=conn)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
