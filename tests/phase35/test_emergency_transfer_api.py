"""
Phase 35: Integration Tests for Emergency Break-Glass REST API (NABH COP.6)
===========================================================================
Verifies:
1. POST /api/v1/emergency/break-glass
2. POST /api/v1/emergency/transfer
3. GET /api/v1/emergency/events/{event_id}
4. POST /api/v1/emergency/vitals/evaluate
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
        test_db_path = Path(tmpdir) / "emergency_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-EMERG-API-01", "aiia-delhi-central-001", "Ramesh", "Shukla", "1960-05-14", "MALE", "+919876543111", 1700000000)
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "emergency_api_test.db")

        with TestClient(app) as client:
            yield client


def test_emergency_api_lifecycle(client_with_db):
    """Verify full emergency break-glass and transfer workflow via REST API."""
    # 1. Login as Physician
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Rapid Vitals Screening
    vitals_payload = {
        "systolic_bp": 78,
        "diastolic_bp": 48,
        "heart_rate_bpm": 132,
        "respiratory_rate_bpm": 34,
        "spo2_percentage": 87.5,
        "glasgow_coma_scale": 9
    }
    screen_resp = client_with_db.post("/api/v1/emergency/vitals/evaluate", json=vitals_payload, headers=headers)
    assert screen_resp.status_code == 200
    flags = screen_resp.json()
    assert len(flags) >= 3

    # 3. Trigger Emergency Break-Glass
    breakglass_payload = {
        "patient_id": "PAT-EMERG-API-01",
        "hospital_id": "aiia-delhi-central-001",
        "trigger_reason": "CARDIOGENIC_SHOCK",
        "vitals": vitals_payload,
        "initiating_user_id": "user-physician-001",
        "initiating_role": "PHYSICIAN_RMP",
        "physician_arn": "ARN-NCISM-2015-8832",
        "emergency_icu_destination": "AIIMS Trauma Centre"
    }
    bg_resp = client_with_db.post("/api/v1/emergency/break-glass", json=breakglass_payload, headers=headers)
    assert bg_resp.status_code == 201
    bg_data = bg_resp.json()
    event_id = bg_data["event_id"]
    assert bg_data["state_lockdown_enforced"]

    # 4. Retrieve Break-Glass Event and SBAR
    event_resp = client_with_db.get(f"/api/v1/emergency/events/{event_id}", headers=headers)
    assert event_resp.status_code == 200
    assert event_resp.json()["event_id"] == event_id

    # 5. Execute Critical Care Transfer
    transfer_payload = {
        "event_id": event_id,
        "allopathic_physician_notified": "Dr. S. K. Verma, Incharge ICU",
        "receiving_hospital_name": "AIIMS Emergency",
        "receiving_doctor_name": "Dr. S. K. Verma",
        "handover_signed_by_arn": "ARN-NCISM-2015-8832",
        "paramedic_unit_code": "ALS-01",
        "clinical_notes": "Patient handed over with continuous monitor and oxygen."
    }
    tf_resp = client_with_db.post("/api/v1/emergency/transfer", json=transfer_payload, headers=headers)
    assert tf_resp.status_code == 201
    tf_data = tf_resp.json()
    assert tf_data["event_id"] == event_id
    assert tf_data["ambulance_service_called"]
