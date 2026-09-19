"""
api/v1/pharmacovigilance.py - API Endpoints for Phase 44: Pharmacovigilance & NPvCC Gateway.
"""

import sqlite3
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_current_user, get_db_session
from models.schemas import UserResponse
from models.pharmacovigilance import (
    AdrReportCreate,
    AdrReportRecord,
    NpvccYellowCardExport,
)
from core.pharmacovigilance import (
    create_adr_report,
    export_npvcc_yellow_card,
    get_patient_adr_reports,
    PharmacovigilanceError,
)

router = APIRouter(prefix="/pharmacovigilance", tags=["Phase 44: Pharmacovigilance & NPvCC Gateway"])


@router.post(
    "/reports",
    response_model=AdrReportRecord,
    status_code=status.HTTP_201_CREATED,
    summary="File statutory ADR report with Modified Naranjo ASU causality scoring"
)
def create_report_endpoint(
    req: AdrReportCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
):
    return create_adr_report(req, current_user=current_user, conn=conn)


@router.post(
    "/reports/{report_id}/export-yellow-card",
    response_model=NpvccYellowCardExport,
    summary="Export ADR report to statutory NPvCC Yellow Card XML format"
)
def export_yellow_card_endpoint(
    report_id: str,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return export_npvcc_yellow_card(report_id, conn=conn)
    except PharmacovigilanceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/patient/{patient_id}/reports",
    response_model=List[AdrReportRecord],
    summary="Get ADR pharmacovigilance reports for a patient"
)
def get_patient_reports_endpoint(
    patient_id: str,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    return get_patient_adr_reports(patient_id, conn=conn)
