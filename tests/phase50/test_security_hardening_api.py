"""
tests/phase50/test_security_hardening_api.py - Integration API tests for Phase 50 Security Hardening endpoints.
"""

import tempfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from config.settings import get_settings
from core.database import init_database
from main import app


@pytest.fixture
def client_with_db(monkeypatch):
    """Fixture providing TestClient backed by an isolated temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "security_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "security_api_test.db")

        with TestClient(app) as client:
            yield client


def test_security_hardening_api_lifecycle(client_with_db):
    # 1. Login as Superintendent
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "superintendent", "password": "Superintendent@AIIA2026"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Ingest threat telemetry
    threat_payload = {
        "hospital_id": "aiia-delhi-central-001",
        "source_ip": "10.0.0.99",
        "threat_category": "CROSS_PRACTICE_VIOLATION",
        "request_uri": "/api/v1/prescriptions/sign",
        "action_intercepted": "BLOCKED_403",
        "severity_level": "CRITICAL",
    }
    threat_resp = client_with_db.post("/api/v1/security-hardening/threat-telemetry", json=threat_payload, headers=headers)
    assert threat_resp.status_code == 201
    assert threat_resp.json()["event_id"].startswith("threat-")

    # 3. List threat events
    list_resp = client_with_db.get("/api/v1/security-hardening/threat-telemetry?hospital_id=aiia-delhi-central-001", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # 4. Run DAST audit suite
    audit_resp = client_with_db.post(
        "/api/v1/security-hardening/dast-audit",
        json={"audit_suite_name": "API_ZERO_TRUST_SUITE_1"},
        headers=headers,
    )
    assert audit_resp.status_code == 201
    findings = audit_resp.json()
    assert len(findings) == 6
    assert all(f["mitigation_status"] == "SECURED" for f in findings)

    # 5. List findings
    findings_resp = client_with_db.get(
        "/api/v1/security-hardening/findings?audit_suite_name=API_ZERO_TRUST_SUITE_1",
        headers=headers,
    )
    assert findings_resp.status_code == 200
    assert len(findings_resp.json()) == 6

    # 6. Get security posture metrics
    posture_resp = client_with_db.get(
        "/api/v1/security-hardening/posture-metrics?hospital_id=aiia-delhi-central-001",
        headers=headers,
    )
    assert posture_resp.status_code == 200
    p_data = posture_resp.json()
    assert p_data["hospital_id"] == "aiia-delhi-central-001"
    assert p_data["zero_trust_hardening_score_pct"] > 0
