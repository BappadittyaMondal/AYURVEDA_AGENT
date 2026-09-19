"""
Integration Tests for Upakarma & Bahya Parimarjana API (Phase 20).
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
        test_db_path = Path(tmpdir) / "upakarma_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-UP-API-01", "aiia-delhi-central-001", "Kavita", "Rao", "1990-02-14", "FEMALE", "+919876543233", 1700000000)
        )
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "upakarma_api_test.db")

        with TestClient(app) as client:
            yield client


def test_therapies_listing_and_filtering_endpoints(client_with_db):
    """Verify catalog listing, modality filtering, and text search."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List all therapies
    resp = client_with_db.get("/api/v1/upakarma/therapies", headers=headers)
    assert resp.status_code == 200
    therapies = resp.json()
    assert len(therapies) >= 12

    # 2. Filter by modality 'ABHYANGA'
    resp_abhyanga = client_with_db.get("/api/v1/upakarma/therapies?modality=ABHYANGA", headers=headers)
    assert resp_abhyanga.status_code == 200
    ab_list = resp_abhyanga.json()
    assert len(ab_list) == 1
    assert ab_list[0]["therapy_id"] == "UPAKARMA-ABHYANGA"

    # 3. Search query 'Psoriasis' (matches Takradhara indication)
    resp_q = client_with_db.get("/api/v1/upakarma/therapies?q=Psoriasis", headers=headers)
    assert resp_q.status_code == 200
    found = resp_q.json()
    assert any(t["therapy_id"] == "UPAKARMA-TAKRADHARA" for t in found)


def test_therapy_detail_endpoint(client_with_db):
    """Verify single therapy retrieval and 404 handling."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client_with_db.get("/api/v1/upakarma/therapies/UPAKARMA-KATI-BASTI", headers=headers)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["therapy_id"] == "UPAKARMA-KATI-BASTI"
    assert detail["target_temperature_min_c"] == 40.0

    resp_404 = client_with_db.get("/api/v1/upakarma/therapies/UPAKARMA-UNKNOWN", headers=headers)
    assert resp_404.status_code == 404


def test_safety_validate_endpoint(client_with_db):
    """Verify thermodynamic pre-session screening API."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Safe request: Abhyanga at 39.0°C
    safe_payload = {
        "patient_id": "PAT-UP-API-01",
        "therapy_id": "UPAKARMA-ABHYANGA",
        "proposed_temperature_c": 39.0,
        "patient_conditions": ["Mild fatigue"],
        "pre_op_agi_score": 1.10,
    }
    resp_safe = client_with_db.post("/api/v1/upakarma/safety/validate", json=safe_payload, headers=headers)
    assert resp_safe.status_code == 200
    assert resp_safe.json()["is_safe_to_proceed"] is True
    assert resp_safe.json()["temperature_compliance"] == "COMPLIANT"

    # Burn hazard request: Bashpa Sweda at 50.0°C
    burn_payload = {
        "patient_id": "PAT-UP-API-01",
        "therapy_id": "UPAKARMA-BASHPA-SWEDA",
        "proposed_temperature_c": 50.0,
        "patient_conditions": [],
    }
    resp_burn = client_with_db.post("/api/v1/upakarma/safety/validate", json=burn_payload, headers=headers)
    assert resp_burn.status_code == 200
    assert resp_burn.json()["is_safe_to_proceed"] is False
    assert resp_burn.json()["temperature_compliance"] == "EXCESSIVE_RISK_OF_BURNS"


def test_session_logging_and_patient_history_endpoints(client_with_db):
    """Verify logging an Upakarma session and querying patient history."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    session_payload = {
        "patient_id": "PAT-UP-API-01",
        "therapy_id": "UPAKARMA-KATI-BASTI",
        "medium_used": "Mahanarayana Taila",
        "operating_temperature_c": 41.0,
        "duration_minutes": 30,
        "pre_vitals_bp": "120/80",
        "post_vitals_bp": "118/76",
        "therapist_id": "THERAPIST-01",
        "clinical_notes": "Warm oil retained in Masha ring for 30 minutes without leak",
    }
    resp_log = client_with_db.post("/api/v1/upakarma/sessions", json=session_payload, headers=headers)
    assert resp_log.status_code == 201
    res_data = resp_log.json()
    assert res_data["therapy_id"] == "UPAKARMA-KATI-BASTI"

    # Query patient history
    resp_hist = client_with_db.get("/api/v1/upakarma/sessions/patient/PAT-UP-API-01", headers=headers)
    assert resp_hist.status_code == 200
    sessions = resp_hist.json()
    assert len(sessions) >= 1
    assert sessions[0]["therapy_id"] == "UPAKARMA-KATI-BASTI"
