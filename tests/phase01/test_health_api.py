"""Phase 01: Test Suite for FastAPI Health, Authentication, and Multi-Tenancy Endpoints."""
import tempfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from config.settings import get_settings
from core.database import init_database
from main import app


@pytest.fixture
def client_with_isolated_db(monkeypatch):
    """Fixture providing a TestClient backed by an isolated temporary SQLite database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "api_test.db")

        with TestClient(app) as client:
            yield client


def test_root_identity_endpoint(client_with_isolated_db):
    """Verify system root displays statutory compliance and operational metadata."""
    response = client_with_isolated_db.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["system"] == "AYURVEDA_AGENT"
    assert "NCISM Act 2020" in data["compliance"]
    assert "NAMASTE Portal" in data["ontologies"]


def test_health_check_endpoint(client_with_isolated_db):
    """Verify health endpoint confirms SQLite WAL mode and PRAGMA settings."""
    response = client_with_isolated_db.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["database_connected"] is True
    assert data["journal_mode"] == "WAL"
    assert data["foreign_keys_enabled"] is True


def test_auth_login_and_me_lifecycle(client_with_isolated_db):
    """Verify full authentication cycle: login with seeded credentials, obtain token, query /me."""
    # 1. Login as seeded superintendent
    login_resp = client_with_isolated_db.post(
        "/api/v1/auth/login",
        json={
            "username": "superintendent",
            "password": "Superintendent@AIIA2026",
            "hospital_id": "aiia-delhi-central-001"
        }
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    token = login_data["access_token"]
    assert token is not None
    assert login_data["role"] == "SUPERINTENDENT"

    # 2. Query /me endpoint using Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client_with_isolated_db.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["username"] == "superintendent"
    assert me_data["role"] == "SUPERINTENDENT"
    assert me_data["arn"] == "ARN-NCISM-1998-0421"


def test_create_staff_account_enforces_arn(client_with_isolated_db):
    """Verify that creating a PHYSICIAN_RMP account strictly mandates an active NCISM ARN."""
    # Login as superintendent
    login_resp = client_with_isolated_db.post(
        "/api/v1/auth/login",
        json={
            "username": "superintendent",
            "password": "Superintendent@AIIA2026",
            "hospital_id": "aiia-delhi-central-001"
        }
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Attempt to create physician WITHOUT ARN -> Must fail with 422
    fail_payload = {
        "hospital_id": "aiia-delhi-central-001",
        "username": "dr_no_arn",
        "password": "Password123!",
        "full_name": "Dr. Candidate Without ARN",
        "role": "PHYSICIAN_RMP",
        "arn": None
    }
    fail_resp = client_with_isolated_db.post("/api/v1/auth/users", json=fail_payload, headers=headers)
    assert fail_resp.status_code == 422

    # 2. Attempt with valid ARN -> Must succeed with 201
    success_payload = {
        "hospital_id": "aiia-delhi-central-001",
        "username": "dr_rajesh_sharma",
        "password": "Password123!",
        "full_name": "Dr. Rajesh Sharma, MD(Ayu)",
        "role": "PHYSICIAN_RMP",
        "arn": "ARN-NCISM-2020-4491"
    }
    success_resp = client_with_isolated_db.post("/api/v1/auth/users", json=success_payload, headers=headers)
    assert success_resp.status_code == 201
    created_data = success_resp.json()
    assert created_data["username"] == "dr_rajesh_sharma"
    assert created_data["arn"] == "ARN-NCISM-2020-4491"
