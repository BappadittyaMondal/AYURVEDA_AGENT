"""
api/v1/production_readiness.py - REST API endpoints for Phase 51 Final Production Certification & Blueprint.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, require_role
from core.security import ClinicalRole
from models.schemas import UserResponse
from models.production_readiness import (
    ProductionCertCreate,
    ProductionCertResponse,
    HospitalSiteConfigCreate,
    HospitalSiteConfigResponse,
)
from core.production_readiness import (
    audit_and_certify_production_readiness,
    configure_hospital_site,
    get_hospital_site_config,
    list_production_certifications,
    ProductionReadinessError,
)

router = APIRouter(prefix="/production-readiness", tags=["Phase 51: Production Certification & Blueprint"])


@router.post(
    "/verify-and-certify",
    response_model=ProductionCertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute comprehensive 51-phase pre-flight audit and issue Superintendent SHA-256 Release Seal",
)
def certify_production_endpoint(
    payload: ProductionCertCreate,
    current_user: UserResponse = Depends(require_role(ClinicalRole.SUPERINTENDENT)),
):
    try:
        return audit_and_certify_production_readiness(payload, current_user)
    except ProductionReadinessError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/certifications",
    response_model=List[ProductionCertResponse],
    summary="List all issued production release certifications",
)
def list_certifications_endpoint(
    current_user: UserResponse = Depends(get_current_user),
):
    return list_production_certifications()


@router.post(
    "/site-configurations",
    response_model=HospitalSiteConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Configure hospital site production deployment blueprint",
)
def configure_site_endpoint(
    payload: HospitalSiteConfigCreate,
    current_user: UserResponse = Depends(require_role(ClinicalRole.SUPERINTENDENT)),
):
    try:
        return configure_hospital_site(payload, current_user)
    except ProductionReadinessError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/site-configurations/{hospital_id}",
    response_model=HospitalSiteConfigResponse,
    summary="Get hospital production site deployment configuration",
)
def get_site_config_endpoint(
    hospital_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    try:
        return get_hospital_site_config(hospital_id)
    except ProductionReadinessError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
