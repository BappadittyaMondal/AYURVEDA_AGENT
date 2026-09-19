"""
tests/phase51/test_production_readiness_api.py - Integration API tests for Phase 51 Production Certification endpoints.
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
        test_db_path = Path(tmpdir) / "production_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "production_api_test.db")

        with TestClient(app) as client:
            yield client


def test_production_readiness_api_lifecycle(client_with_db):
    # 1. Login as Superintendent
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "superintendent", "password": "Superintendent@AIIA2026"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Execute 51-Phase Production Certification
    cert_payload = {
        "release_version": "v1.0.0-PROD-CERTIFIED",
        "total_tests_executed": 356,
    }
    cert_resp = client_with_db.post(
        "/api/v1/production-readiness/verify-and-certify",
        json=cert_payload,
        headers=headers,
    )
    assert cert_resp.status_code == 201
    c_data = cert_resp.json()
    assert c_data["cert_id"].startswith("cert-prod-")
    assert c_data["all_51_phases_verified"] is True
    assert len(c_data["sha256_manifest_seal"]) == 64

    # 3. List Certifications
    list_resp = client_with_db.get("/api/v1/production-readiness/certifications", headers=headers)
    assert list_resp.status_code == 200
    assert any(c["cert_id"] == c_data["cert_id"] for c in list_resp.json())

    # 4. Configure Hospital Site Blueprint
    site_payload = {
        "hospital_id": "aiia-delhi-central-001",
        "deployment_tier": "APEX_HOSPITAL",
        "hostinger_vps_specs": {
            "cpu_cores": 8,
            "ram_gb": 32,
            "disk_storage_gb": 400,
            "os_distribution": "Ubuntu 24.04 LTS",
            "wal_sync_mode": "NORMAL_WAL_ASYNC",
            "automated_backup_schedule": "CRON_HOURLY_PITR"
        },
        "active_modules": [
            "ALL_51_PHASES_ACTIVE"
        ],
        "status": "PRODUCTION_ACTIVE"
    }
    site_resp = client_with_db.post(
        "/api/v1/production-readiness/site-configurations",
        json=site_payload,
        headers=headers,
    )
    assert site_resp.status_code == 201
    s_data = site_resp.json()
    assert s_data["hospital_id"] == "aiia-delhi-central-001"
    assert s_data["deployment_tier"] == "APEX_HOSPITAL"

    # 5. Get Site Configuration
    get_site_resp = client_with_db.get(
        "/api/v1/production-readiness/site-configurations/aiia-delhi-central-001",
        headers=headers,
    )
    assert get_site_resp.status_code == 200
    assert get_site_resp.json()["hospital_id"] == "aiia-delhi-central-001"
