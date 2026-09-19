"""
API Endpoints for Classical Formulation Architecture (Bhaishajya Kalpana) & Polyherbal Synergy.
"""

import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, get_db_session
from core.bhaishajya_kalpana import (
    evaluate_polyherbal_synergy,
    get_all_anupana,
    get_formulation_by_id,
    search_formulations,
)
from models.bhaishajya_kalpana import (
    AnupanaProfile,
    ClassicalFormulation,
    KalpanaForm,
    SynergyEvaluationRequest,
    SynergyEvaluationResponse,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/bhaishajya-kalpana", tags=["Bhaishajya Kalpana Classical Formulations"])


@router.get("/formulations", response_model=List[ClassicalFormulation])
def list_or_search_formulations(
    q: Optional[str] = Query(default=None, description="Search by formulation name, reference, or keywords"),
    kalpana: Optional[KalpanaForm] = Query(default=None, description="Filter by Kalpana form (e.g. CHURNA, KWATHA, GHRITA, TAILA)"),
    indication: Optional[str] = Query(default=None, description="Filter by disease indication (e.g. Amavata, Jwara, Shvasa)"),
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[ClassicalFormulation]:
    """Search and browse classical Ayurvedic compound formulations across diverse Kalpana forms."""
    return search_formulations(conn=conn, query=q, kalpana=kalpana, indication=indication)


@router.get("/formulations/{formulation_id}", response_model=ClassicalFormulation)
def get_formulation_detail(
    formulation_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> ClassicalFormulation:
    """Retrieves full recipe, ingredients, composite pharmacodynamics, and posology for a classical formulation."""
    form = get_formulation_by_id(conn, formulation_id)
    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Formulation '{formulation_id}' not found in registry",
        )
    return form


@router.get("/anupana", response_model=List[AnupanaProfile])
def list_anupana_vehicles(
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[AnupanaProfile]:
    """Retrieves all classical Anupana (carrier vehicles) with their pharmacodynamic enhancement properties."""
    return get_all_anupana(conn)


@router.post("/evaluate-synergy", response_model=SynergyEvaluationResponse)
def evaluate_custom_formulation_synergy(
    request: SynergyEvaluationRequest,
    current_user: UserResponse = Depends(get_current_user),
) -> SynergyEvaluationResponse:
    """
    Computes polyherbal composite Doshic vector (V-P-K), determines composite Veerya/Vipaka,
    and enforces classical Viruddha Ahara safety firewalls (e.g. 1:1 Honey-Ghee and heated Honey checks).
    """
    return evaluate_polyherbal_synergy(request)
