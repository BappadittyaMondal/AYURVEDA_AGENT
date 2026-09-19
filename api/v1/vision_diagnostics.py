"""
api/v1/vision_diagnostics.py - API Endpoints for Phase 40: Computer Vision Optical Diagnostics Pipeline.
"""

import sqlite3
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_current_user, get_db_session
from models.schemas import UserResponse
from models.vision_diagnostics import (
    CalibrationTargetCreate,
    CalibrationTargetRecord,
    OpticalInferenceRequest,
    OpticalInferenceResult,
)
from core.vision_diagnostics import (
    create_calibration_target,
    get_calibration_target,
    analyze_optical_image,
    get_patient_vision_inferences,
    VisionDiagnosticError,
)

router = APIRouter(prefix="/vision-diagnostics", tags=["Phase 40: Computer Vision Optical Diagnostics"])


@router.post(
    "/calibration-targets",
    response_model=CalibrationTargetRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Register optical calibration target card"
)
def create_calibration_target_endpoint(
    target_in: CalibrationTargetCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
):
    return create_calibration_target(target_in, conn=conn)


@router.get(
    "/calibration-targets/{target_id}",
    response_model=CalibrationTargetRecord,
    summary="Get optical calibration target details"
)
def get_calibration_target_endpoint(
    target_id: str,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    target = get_calibration_target(target_id, conn=conn)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Target '{target_id}' not found.")
    return target


@router.post(
    "/analyze",
    response_model=OpticalInferenceResult,
    status_code=status.HTTP_201_CREATED,
    summary="Analyze tongue coating or scleral icterus via calibrated optical diagnostics"
)
def analyze_optical_image_endpoint(
    req: OpticalInferenceRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return analyze_optical_image(req, current_user=current_user, conn=conn)
    except VisionDiagnosticError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/patient/{patient_id}/inferences",
    response_model=List[OpticalInferenceResult],
    summary="Get historical optical diagnostic inferences for a patient"
)
def get_patient_inferences_endpoint(
    patient_id: str,
    limit: int = 20,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    return get_patient_vision_inferences(patient_id, limit=limit, conn=conn)
