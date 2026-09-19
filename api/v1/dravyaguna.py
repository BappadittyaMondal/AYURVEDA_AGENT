"""
API Endpoints for Classical Herbology (Dravya Guna) Knowledge Graph & Phytochemistry.
"""

import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, get_db_session
from core.dravyaguna import (
    calculate_doshic_modulation_vector,
    get_herb_by_id,
    search_herbs,
)
from models.dravyaguna import (
    DoshicModulationScore,
    HerbProfile,
    Rasa,
    Veerya,
    Vipaka,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/dravyaguna", tags=["Dravya Guna Classical Herbology"])


@router.get("/herbs", response_model=List[HerbProfile])
def list_or_search_herbs(
    q: Optional[str] = Query(default=None, description="Search by Sanskrit name, botanical taxon, synonym, or bioactive constituent"),
    rasa: Optional[Rasa] = Query(default=None, description="Filter by classical Rasa (taste)"),
    veerya: Optional[Veerya] = Query(default=None, description="Filter by Veerya (thermal potency: USHNA or SHEETA)"),
    vipaka: Optional[Vipaka] = Query(default=None, description="Filter by Vipaka (post-digestive transformation)"),
    karma: Optional[str] = Query(default=None, description="Filter by therapeutic karma (e.g. Rasayana, Deepana, Medhya)"),
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[HerbProfile]:
    """Search and browse the classical Dravya Guna knowledge graph across multi-axial pharmacological dimensions."""
    return search_herbs(conn=conn, query=q, rasa=rasa, veerya=veerya, vipaka=vipaka, karma=karma)


@router.get("/herbs/{herb_id}", response_model=HerbProfile)
def get_herb_profile(
    herb_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> HerbProfile:
    """Retrieves comprehensive pharmacological, botanical, and phytochemical profile for an herb."""
    herb = get_herb_by_id(conn, herb_id)
    if not herb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Herb '{herb_id}' not found in Dravya Guna registry",
        )
    return herb


@router.get("/herbs/{herb_id}/doshic-impact", response_model=DoshicModulationScore)
def get_herb_doshic_modulation(
    herb_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> DoshicModulationScore:
    """Computes quantitative directional Doshic impact vector (Delta v, Delta p, Delta k) for clinical prescription planning."""
    herb = get_herb_by_id(conn, herb_id)
    if not herb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Herb '{herb_id}' not found in Dravya Guna registry",
        )
    return calculate_doshic_modulation_vector(herb)
