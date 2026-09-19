"""
tests/phase50/test_security_hardening_engine.py - Unit tests for Phase 50 Security Hardening & DAST Penetration engine.
"""

import pytest
from core.database import get_sqlite_connection, init_database
from models.schemas import UserResponse
from core.security import ClinicalRole
from models.security_hardening import (
    ThreatCategory,
    InterceptionAction,
    SeverityLevel,
    MitigationStatus,
    ThreatTelemetryCreate,
)
from core.security_hardening import (
    record_threat_event,
    run_dast_security_audit,
    get_security_posture_summary,
    list_threat_events,
    list_audit_findings,
)


@pytest.fixture
def superintendent_user():
    return UserResponse(
        user_id="user-superintendent-001",
        hospital_id="aiia-delhi-central-001",
        username="superintendent",
        full_name="Prof. Dr. V. Sharma",
        arn="ARN-NCISM-1998-0421",
        role=ClinicalRole.SUPERINTENDENT,
        is_active=True,
        created_at=1700000000
    )


@pytest.fixture
def conn():
    init_database()
    connection = get_sqlite_connection()
    yield connection
    connection.close()


def test_record_threat_telemetry_event(conn, superintendent_user):
    payload = ThreatTelemetryCreate(
        hospital_id="aiia-delhi-central-001",
        source_ip="192.168.1.105",
        threat_category=ThreatCategory.SQLI_ATTEMPT,
        request_uri="/api/v1/patients/search?query=' OR '1'='1",
        action_intercepted=InterceptionAction.BLOCKED_403,
        severity_level=SeverityLevel.HIGH,
    )
    result = record_threat_event(payload, superintendent_user)
    assert result.event_id.startswith("threat-")
    assert result.source_ip == "192.168.1.105"
    assert result.threat_category == ThreatCategory.SQLI_ATTEMPT
    assert result.action_intercepted == InterceptionAction.BLOCKED_403

    events = list_threat_events("aiia-delhi-central-001")
    assert any(e.event_id == result.event_id for e in events)


def test_run_dast_security_audit_suite(conn, superintendent_user):
    suite_name = "OWASP_API_SECURITY_VERIFICATION"
    findings = run_dast_security_audit(suite_name, superintendent_user)
    assert len(findings) == 6
    for f in findings:
        assert f.audit_suite_name == suite_name
        assert f.mitigation_status == MitigationStatus.SECURED
        assert f.cve_or_cwe_identifier is not None

    all_findings = list_audit_findings(suite_name)
    assert len(all_findings) >= 6


def test_security_posture_summary_calculation(conn, superintendent_user):
    summary = get_security_posture_summary("aiia-delhi-central-001")
    assert summary.hospital_id == "aiia-delhi-central-001"
    assert summary.zero_trust_hardening_score_pct >= 85.0
    assert summary.posture_status in ("EXEMPLARY_ZERO_TRUST", "HARDENED")
