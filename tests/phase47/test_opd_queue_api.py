"""
tests/phase47/test_opd_queue_api.py - Integration API tests for Phase 47 OPD Queue Optimization.
"""

import tempfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from config.settings import get_settings
from core.database import get_sqlite_connection, init_database
from main import app


@pytest.fixture
def client_with_db(monkeypatch):
    """Fixture providing TestClient backed by an isolated temporary database with seeded patient."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "opd_api_test.db"
        init_database(test_db_path)

        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("pat-api-opd-01", "aiia-delhi-central-001", "Vijay", "Kumar", "1991-04-14", "MALE", "+919876547788", 1700000000)
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "opd_api_test.db")

        with TestClient(app) as client:
            yield client


def test_opd_queue_api_lifecycle(client_with_db):
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Issue Token
    issue_payload = {
        "hospital_id": "aiia-delhi-central-001",
        "patient_id": "pat-api-opd-01",
        "department": "KAYACHIKITSA",
        "priority_tier": "SENIOR_CITIZEN_GERIATRIC"
    }
    tok_res = client_with_db.post("/api/v1/opd-queue/tokens", json=issue_payload, headers=headers)
    assert tok_res.status_code == 201
    tok_data = tok_res.json()
    assert tok_data["token_id"].startswith("tok-")

    # 2. Get Queue Status
    stat_res = client_with_db.get("/api/v1/opd-queue/departments/KAYACHIKITSA/status")
    assert stat_res.status_code == 200
    assert stat_res.json()["total_waiting"] >= 1

    # 3. Call Next Token
    call_res = client_with_db.post(
        "/api/v1/opd-queue/departments/KAYACHIKITSA/call-next?physician_arn=ARN-NCISM-2015-8832",
        headers=headers
    )
    assert call_res.status_code == 200
    called_tok = call_res.json()
    assert called_tok["token_id"] == tok_data["token_id"]

    # 4. Complete Consultation
    comp_res = client_with_db.post(f"/api/v1/opd-queue/tokens/{called_tok['token_id']}/complete")
    assert comp_res.status_code == 200
    assert comp_res.json()["efficiency_rating"] is not None
