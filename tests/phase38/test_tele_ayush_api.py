"""
Phase 38: Integration Tests for Tele-AYUSH REST API
===================================================
Verifies:
1. POST /api/v1/tele-ayush/sessions
2. POST /api/v1/tele-ayush/prescriptions
3. GET /api/v1/tele-ayush/prescriptions/{prescription_id}/verify
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
        test_db_path = Path(tmpdir) / "tele_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-TELE-API-01", "aiia-delhi-central-001", "Meenakshi", "Sundaram", "1990-11-04", "FEMALE", "+919876543444", 1700000000)
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "tele_api_test.db")

        with TestClient(app) as client:
            yield client


def test_tele_ayush_api_lifecycle(client_with_db):
    """Verify scheduling and e-prescription issuance via API."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Schedule Tele-session
    sess_payload = {
        "patient_id": "PAT-TELE-API-01",
        "hospital_id": "aiia-delhi-central-001",
        "physician_arn": "ARN-NCISM-2015-8832",
        "scheduled_timestamp": 1750000000,
        "call_type": "VIDEO_CONFERENCE",
        "clinical_notes": "Tele-consultation."
    }
    sess_resp = client_with_db.post("/api/v1/tele-ayush/sessions", json=sess_payload, headers=headers)
    assert sess_resp.status_code == 201
    sess_id = sess_resp.json()["session_id"]

    # 2. Issue e-Prescription
    rx_payload = {
        "session_id": sess_id,
        "patient_id": "PAT-TELE-API-01",
        "hospital_id": "aiia-delhi-central-001",
        "physician_arn": "ARN-NCISM-2015-8832",
        "formulations": [
            {
                "formulation_name": "Nishamalaki Churna",
                "dosage": "3g twice daily",
                "timing": "Before food",
                "anupana": "Warm water"
            }
        ],
        "pathya_diet_instructions": "Pathya Ahara."
    }
    rx_resp = client_with_db.post("/api/v1/tele-ayush/prescriptions", json=rx_payload, headers=headers)
    assert rx_resp.status_code == 201
    rx_id = rx_resp.json()["prescription_id"]

    # 3. Verify e-Prescription
    verif_resp = client_with_db.get(f"/api/v1/tele-ayush/prescriptions/{rx_id}/verify")
    assert verif_resp.status_code == 200
    assert verif_resp.json()["is_authentic"]
