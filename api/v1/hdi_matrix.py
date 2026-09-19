"""
Phase 36: REST API Router for Real-Time Herb-Drug Interaction (HDI) Engine
==========================================================================
Provides clinical endpoints for:
1. Real-time screening of Ayurvedic prescriptions against active modern drug regimens
2. Accessing the 28-point canonical evidence-based HDI rules catalog
3. Recording statutory NCISM physician overrides with clinical justification
"""

import sqlite3
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_db_session
from core.hdi_matrix import (
    cross_check_herb_drug_interactions,
    override_hdi_intercept,
    ensure_hdi_rules_seeded,
)
from models.hdi_matrix import (
    HdiCrossCheckRequest,
    HdiCrossCheckResponse,
    HdiOverrideRequest,
    HdiRule,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/hdi", tags=["Phase 36: Real-Time Herb-Drug Interaction Engine (28-Point Matrix)"])


@router.post("/cross-check", response_model=HdiCrossCheckResponse)
def cross_check_endpoint(
    req: HdiCrossCheckRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> HdiCrossCheckResponse:
    """Screen proposed Ayurvedic formulations against patient's active modern drug list in real-time."""
    return cross_check_herb_drug_interactions(req, conn=conn)


@router.post("/override", response_model=Dict[str, Any])
def override_intercept_endpoint(
    req: HdiOverrideRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> Dict[str, Any]:
    """Record an NCISM Registered Medical Practitioner clinical override with written justification."""
    return override_hdi_intercept(req, conn=conn)


@router.get("/rules", response_model=List[Dict[str, Any]])
def list_rules_endpoint(
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> List[Dict[str, Any]]:
    """Retrieve the authoritative 28-point evidence-based HDI interaction rules catalog."""
    ensure_hdi_rules_seeded(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hdi_interaction_rules ORDER BY rule_id ASC;")
    return [dict(r) for r in cursor.fetchall()]
