"""
api/v1/security_hardening.py - REST API endpoints for Phase 50 Zero-Trust Penetration Testing & DAST Audit.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, require_role
from core.security import ClinicalRole
from models.schemas import UserResponse
from models.security_hardening import (
    ThreatTelemetryCreate,
    ThreatTelemetryResponse,
    DASTAuditRequest,
    AuditFindingRecord,
    SecurityPostureSummary,
)
from core.security_hardening import (
    record_threat_event,
    run_dast_security_audit,
    get_security_posture_summary,
    list_threat_events,
    list_audit_findings,
    SecurityHardeningError,
)

router = APIRouter(prefix="/security-hardening", tags=["Phase 50: Security Hardening & Penetration Testing"])


@router.post(
    "/threat-telemetry",
    response_model=ThreatTelemetryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest intercepted threat telemetry event",
)
def record_threat_endpoint(
    payload: ThreatTelemetryCreate,
    current_user: UserResponse = Depends(get_current_user),
):
    try:
        return record_threat_event(payload, current_user)
    except SecurityHardeningError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/threat-telemetry",
    response_model=List[ThreatTelemetryResponse],
    summary="List intercepted security threat events",
)
def list_threats_endpoint(
    hospital_id: Optional[str] = Query(None, description="Filter by hospital ID"),
    current_user: UserResponse = Depends(require_role(ClinicalRole.SUPERINTENDENT, ClinicalRole.AUDITOR)),
):
    return list_threat_events(hospital_id=hospital_id)


@router.post(
    "/dast-audit",
    response_model=List[AuditFindingRecord],
    status_code=status.HTTP_201_CREATED,
    summary="Execute automated DAST zero-trust penetration audit suite",
)
def execute_dast_audit_endpoint(
    payload: DASTAuditRequest,
    current_user: UserResponse = Depends(require_role(ClinicalRole.SUPERINTENDENT, ClinicalRole.AUDITOR)),
):
    try:
        return run_dast_security_audit(payload.audit_suite_name, current_user)
    except SecurityHardeningError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/findings",
    response_model=List[AuditFindingRecord],
    summary="List penetration audit findings and CVE/CWE status",
)
def list_findings_endpoint(
    audit_suite_name: Optional[str] = Query(None, description="Filter by audit suite name"),
    current_user: UserResponse = Depends(require_role(ClinicalRole.SUPERINTENDENT, ClinicalRole.AUDITOR)),
):
    return list_audit_findings(audit_suite_name=audit_suite_name)


@router.get(
    "/posture-metrics",
    response_model=SecurityPostureSummary,
    summary="Get hospital zero-trust hardening score and posture summary",
)
def get_posture_endpoint(
    hospital_id: str = Query(..., description="Hospital ID to evaluate"),
    current_user: UserResponse = Depends(get_current_user),
):
    return get_security_posture_summary(hospital_id=hospital_id)
