"""API Endpoints for Jalaukavacharana, Siravedha & Raktamokshana Biotherapy Suite.

Classical reference:
- Sushruta Samhita Sutrasthana Ch. 13 & 14
- Sushruta Samhita Sharirasthana Ch. 8
"""
import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, get_db_session
from core.raktamokshana import (
    evaluate_raktamokshana_safety,
    get_patient_raktamokshana_history,
    list_jalauka_species,
    list_siravedha_veins,
    record_raktamokshana_procedure,
    seed_raktamokshana_catalogs,
)
from models.raktamokshana import (
    BodyQuadrant,
    JalaukaSpecies,
    JalaukaType,
    RaktamokshanaProcedureLogCreate,
    RaktamokshanaProcedureLogResponse,
    SafetyEvaluationRequest,
    SafetyEvaluationResponse,
    SiravedhaVein,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/raktamokshana", tags=["Raktamokshana, Jalaukavacharana & Siravedha Biotherapy Suite"])


@router.get("/jalauka-species", response_model=List[JalaukaSpecies])
def get_jalauka_species_catalog(
    species_type: Optional[JalaukaType] = Query(default=None, description="Filter by NIRVISHA (medicinal) or SAVISHA (toxic)"),
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[JalaukaSpecies]:
    """Retrieve the classical 12 leeches taxonomy with morphology and salivary pharmacology."""
    seed_raktamokshana_catalogs(conn)
    return list_jalauka_species(species_type=species_type, conn=conn)


@router.get("/siravedha-veins", response_model=List[SiravedhaVein])
def get_siravedha_veins_matrix(
    only_avadhya: Optional[bool] = Query(default=None, description="Filter only strictly prohibited 98 Avadhya Siras"),
    quadrant: Optional[BodyQuadrant] = Query(default=None, description="Filter by anatomical body quadrant"),
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[SiravedhaVein]:
    """Retrieve Siravedha vein matrix with 98 Avadhya Siras mapping and indicated disease veins."""
    seed_raktamokshana_catalogs(conn)
    return list_siravedha_veins(only_avadhya=only_avadhya, quadrant=quadrant, conn=conn)


@router.post("/safety-evaluation", response_model=SafetyEvaluationResponse)
def run_safety_firewall_evaluation(
    request: SafetyEvaluationRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> SafetyEvaluationResponse:
    """Pre-procedure safety firewall evaluating baseline Hb, Rogi Bala, coagulopathy, and Avadhya Siras."""
    seed_raktamokshana_catalogs(conn)
    return evaluate_raktamokshana_safety(request, conn=conn)


@router.post("/procedure-logs", response_model=RaktamokshanaProcedureLogResponse, status_code=status.HTTP_201_CREATED)
def log_raktamokshana_procedure(
    payload: RaktamokshanaProcedureLogCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> RaktamokshanaProcedureLogResponse:
    """Log an operative Raktamokshana procedure with strict pre-procedure firewall verification."""
    seed_raktamokshana_catalogs(conn)
    try:
        return record_raktamokshana_procedure(payload, conn=conn)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/procedure-logs/{patient_id}", response_model=List[RaktamokshanaProcedureLogResponse])
def get_patient_procedure_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[RaktamokshanaProcedureLogResponse]:
    """Retrieve all historical Raktamokshana sessions recorded for a patient."""
    seed_raktamokshana_catalogs(conn)
    return get_patient_raktamokshana_history(patient_id, conn=conn)
