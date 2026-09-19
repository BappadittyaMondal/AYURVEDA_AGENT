"""
tests/phase42/test_ayush_grid_api.py - Integration API tests for Phase 42 AYUSH GRID Bridge & Zero-Knowledge Verification.
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
        test_db_path = Path(tmpdir) / "ayush_grid_api_test.db"
        init_database(test_db_path)

        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("pat-api-p42-01", "aiia-delhi-central-001", "Rajesh", "Verma", "1979-11-21", "MALE", "+919876541122", 1700000000)
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "ayush_grid_api_test.db")

        with TestClient(app) as client:
            yield client


def test_ayush_grid_api_lifecycle(client_with_db):
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Dispatch FHIR Bundle
    dispatch_payload = {
        "hospital_id": "aiia-delhi-central-001",
        "patient_id": "pat-api-p42-01",
        "abdm_bundle_type": "OP_CONSULTATION_NOTE",
        "clinical_data": {
            "prakriti": "Pitta-Kapha",
            "prescriptions": ["Triphala Churna 5g"]
        }
    }
    disp_res = client_with_db.post("/api/v1/ayush-grid/dispatch", json=dispatch_payload, headers=headers)
    assert disp_res.status_code == 201
    disp_data = disp_res.json()
    assert disp_data["bridge_id"].startswith("abdm-")
    assert disp_data["status"] == "ACKNOWLEDGED"

    # 2. Get ABDM Dispatch Logs
    log_res = client_with_db.get("/api/v1/ayush-grid/patient/pat-api-p42-01/logs")
    assert log_res.status_code == 200
    logs = log_res.json()
    assert len(logs) >= 1
    assert logs[0]["bridge_id"] == disp_data["bridge_id"]

    # 3. Generate ZKP Proof
    zkp_payload = {
        "hospital_id": "aiia-delhi-central-001",
        "patient_id": "pat-api-p42-01",
        "clinical_attribute": "AUTHENTIC_AYUSH_DIAGNOSIS_VALIDATED",
        "secret_salt": "MySuperSecretPatientKey777",
        "verifier_arn": "ARN-NCISM-2015-8832"
    }
    zkp_res = client_with_db.post("/api/v1/ayush-grid/zkp/generate", json=zkp_payload, headers=headers)
    assert zkp_res.status_code == 201
    zkp_data = zkp_res.json()
    assert zkp_data["proof_id"].startswith("zkp-")

    # 4. Verify ZKP Proof
    verify_payload = {
        "proof_id": zkp_data["proof_id"],
        "revealed_attribute": "AUTHENTIC_AYUSH_DIAGNOSIS_VALIDATED",
        "revealed_secret_salt": "MySuperSecretPatientKey777",
        "patient_id": "pat-api-p42-01"
    }
    v_res = client_with_db.post("/api/v1/ayush-grid/zkp/verify", json=verify_payload)
    assert v_res.status_code == 200
    assert v_res.json()["is_valid"] is True
