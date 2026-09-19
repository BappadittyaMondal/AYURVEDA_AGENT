"""
api/v1/pharmacy_inventory.py - API Endpoints for Phase 48: Automated Inventory & Pharmacy Dispensation.
"""

import sqlite3
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_current_user, get_db_session
from models.schemas import UserResponse
from models.pharmacy_inventory import (
    PharmacyLotCreate,
    PharmacyLotRecord,
    DispensationCreate,
    DispensationRecord,
)
from core.pharmacy_inventory import (
    intake_pharmacy_lot,
    get_pharmacy_lot,
    dispense_medication,
    get_patient_dispensations,
    PharmacyInventoryError,
)

router = APIRouter(prefix="/pharmacy-inventory", tags=["Phase 48: Pharmacy Inventory & Dispensation"])


@router.post(
    "/lots",
    response_model=PharmacyLotRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Intake a manufacturing batch lot with GS1 barcode into pharmacy inventory"
)
def intake_lot_endpoint(
    req: PharmacyLotCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return intake_pharmacy_lot(req, current_user=current_user, conn=conn)
    except PharmacyInventoryError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/lots/{lot_id}",
    response_model=PharmacyLotRecord,
    summary="Get pharmacy lot stock and quarantine details"
)
def get_lot_endpoint(
    lot_id: str,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    lot = get_pharmacy_lot(lot_id, conn=conn)
    if not lot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lot '{lot_id}' not found.")
    return lot


@router.post(
    "/dispense",
    response_model=DispensationRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Dispense formulation against digital prescription, decrementing inventory"
)
def dispense_endpoint(
    req: DispensationCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return dispense_medication(req, current_user=current_user, conn=conn)
    except PharmacyInventoryError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/patient/{patient_id}/dispensations",
    response_model=List[DispensationRecord],
    summary="Get dispensation history for a patient"
)
def get_dispensations_endpoint(
    patient_id: str,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    return get_patient_dispensations(patient_id, conn=conn)
