"""
api/v1/ipd_management.py - API Endpoints for Phase 46: IPD Inpatient Bed Management & Nursing Charting.
"""

import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_current_user, get_db_session
from models.schemas import UserResponse
from models.ipd_management import (
    BedAllocationCreate,
    BedAllocationRecord,
    NursingChartCreate,
    NursingChartRecord,
)
from core.ipd_management import (
    allocate_ipd_bed,
    discharge_ipd_patient,
    record_nursing_chart,
    get_ward_bed_occupancy,
    get_patient_nursing_charts,
    IpdManagementError,
)

router = APIRouter(prefix="/ipd", tags=["Phase 46: IPD Inpatient Bed Management & Nursing"])


@router.post(
    "/allocations",
    response_model=BedAllocationRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Allocate an inpatient bed to a patient"
)
def allocate_bed_endpoint(
    req: BedAllocationCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return allocate_ipd_bed(req, current_user=current_user, conn=conn)
    except IpdManagementError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/allocations/{allocation_id}/discharge",
    response_model=BedAllocationRecord,
    summary="Discharge an inpatient bed allocation"
)
def discharge_patient_endpoint(
    allocation_id: str,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return discharge_ipd_patient(allocation_id, conn=conn)
    except IpdManagementError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/beds/occupancy",
    response_model=List[BedAllocationRecord],
    summary="Get current ward bed occupancy"
)
def get_occupancy_endpoint(
    ward_name: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    return get_ward_bed_occupancy(ward_name, conn=conn)


@router.post(
    "/nursing-charts",
    response_model=NursingChartRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Record bedside Panchakarma rounds nursing chart"
)
def record_chart_endpoint(
    req: NursingChartCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return record_nursing_chart(req, current_user=current_user, conn=conn)
    except IpdManagementError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/allocations/{allocation_id}/charts",
    response_model=List[NursingChartRecord],
    summary="Get nursing charts for an allocation"
)
def get_charts_endpoint(
    allocation_id: str,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    return get_patient_nursing_charts(allocation_id, conn=conn)
