"""
models/security_hardening.py - Pydantic schemas for Phase 50 Zero-Trust Penetration Testing & DAST Audit.
Tables 106 & 107: security_threat_telemetry, penetration_audit_findings.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from enum import Enum


class ThreatCategory(str, Enum):
    SQLI_ATTEMPT = "SQLI_ATTEMPT"
    CROSS_PRACTICE_VIOLATION = "CROSS_PRACTICE_VIOLATION"
    UNAUTHORIZED_PHI_ACCESS = "UNAUTHORIZED_PHI_ACCESS"
    MALFORMED_AUTH_TOKEN = "MALFORMED_AUTH_TOKEN"
    BRUTE_FORCE_BURST = "BRUTE_FORCE_BURST"
    XSS_INJECTION = "XSS_INJECTION"


class InterceptionAction(str, Enum):
    BLOCKED_403 = "BLOCKED_403"
    SANITIZED = "SANITIZED"
    RATE_LIMITED = "RATE_LIMITED"
    FLAGGED_AUDIT = "FLAGGED_AUDIT"


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MitigationStatus(str, Enum):
    SECURED = "SECURED"
    REMEDIATED = "REMEDIATED"
    IN_REVIEW = "IN_REVIEW"


class ThreatTelemetryCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hospital_id: str = Field(..., description="Target Hospital ID")
    source_ip: str = Field(..., description="Source IPv4 or IPv6 address")
    threat_category: ThreatCategory
    request_uri: str = Field(..., description="Intercepted request URI")
    action_intercepted: InterceptionAction
    severity_level: SeverityLevel


class ThreatTelemetryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    hospital_id: str
    source_ip: str
    threat_category: ThreatCategory
    request_uri: str
    action_intercepted: InterceptionAction
    severity_level: SeverityLevel
    detected_at: int


class DASTAuditRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_suite_name: str = Field(default="OWASP_API_TOP10_DAST", description="Audit suite identifier")


class AuditFindingRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    finding_id: str
    audit_suite_name: str
    target_endpoint: str
    cve_or_cwe_identifier: Optional[str]
    mitigation_status: MitigationStatus
    audited_by: str
    audited_at: int


class SecurityPostureSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hospital_id: str
    total_threats_intercepted: int
    critical_threats: int
    high_threats: int
    audit_findings_evaluated: int
    zero_trust_hardening_score_pct: float
    posture_status: str
