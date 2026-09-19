"""
API Endpoints for Clinical Dietetics, Ahara Varga & Viruddha Ahara Expert System.
"""

import json
import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, get_db_session
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.dietetics import (
    audit_viruddha_ahara,
    create_and_evaluate_diet_plan,
    get_disease_pathya_guidelines,
    get_ingredient_profile,
    list_all_ingredients,
)
from models.dietetics import (
    AharaVarga,
    DietIngredient,
    DietPlanCreateRequest,
    DietPlanResponse,
    DiseasePathyaApathya,
    PlannedMeal,
    ViruddhaViolation,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/dietetics", tags=["Clinical Dietetics & Viruddha Ahara Expert System"])


@router.get("/ingredients", response_model=List[DietIngredient])
def list_ingredients(
    varga: Optional[AharaVarga] = Query(default=None, description="Filter by Ahara Varga food group"),
    q: Optional[str] = Query(default=None, description="Search by Sanskrit name or English name"),
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[DietIngredient]:
    """Search and browse classical Ahara Varga food ingredients."""
    all_ings = list_all_ingredients(conn)
    results: List[DietIngredient] = []

    for ing in all_ings:
        if varga and ing.ahara_varga != varga:
            continue
        if q:
            term = q.lower()
            if (
                term in ing.sanskrit_name.lower()
                or term in ing.english_name.lower()
                or term in ing.rasa.lower()
            ):
                results.append(ing)
        else:
            results.append(ing)

    return results


@router.get("/ingredients/{ingredient_id}", response_model=DietIngredient)
def get_ingredient_detail(
    ingredient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> DietIngredient:
    """Retrieve full nutritional, caloric, and Rasa-Panchaka profile of a food ingredient."""
    try:
        return get_ingredient_profile(ingredient_id, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/pathya-apathya/{disease_code}", response_model=DiseasePathyaApathya)
def get_pathya_apathya(
    disease_code: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> DiseasePathyaApathya:
    """Retrieve disease-specific Pathya and Apathya guidelines."""
    guideline = get_disease_pathya_guidelines(disease_code, conn)
    if not guideline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pathya-Apathya guidelines for disease '{disease_code}' not found",
        )
    return guideline


@router.post("/audit-viruddha", response_model=List[ViruddhaViolation])
def audit_meals_for_viruddha(
    meals: List[PlannedMeal],
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[ViruddhaViolation]:
    """Perform fast 18-fold Viruddha Ahara audit on planned meals."""
    return audit_viruddha_ahara(meals, conn)


@router.post("/prescriptions", response_model=DietPlanResponse, status_code=status.HTTP_201_CREATED)
def prescribe_diet_plan(
    request: DietPlanCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> DietPlanResponse:
    """
    Evaluate, audit for Viruddha Ahara, and prescribe a clinical meal plan.
    Blocks plan creation if critical Viruddha Ahara combinations (e.g. Fish+Milk, 1:1 Honey-Ghee) are detected.
    """
    try:
        return create_and_evaluate_diet_plan(request, current_user.hospital_id, conn)
    except ClinicalGovernanceException as e:
        raise HTTPException(status_code=422, detail=f"[{e.error_code}] {e.message}")
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
