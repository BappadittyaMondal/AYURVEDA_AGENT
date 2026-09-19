"""
tests/phase45/test_clinical_trials_api.py - Integration API tests for Phase 45 Clinical Trials endpoints.
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
        test_db_path = Path(tmpdir) / "trials_api_test.db"
        init_database(test_db_path)

        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("pat-api-trial-01", "aiia-delhi-central-001", "Subhash", "Bose", "1982-01-23", "MALE", "+919876543888", 1700000000)
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "trials_api_test.db")

        with TestClient(app) as client:
            yield client


def test_clinical_trials_api_lifecycle(client_with_db):
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Register Protocol
    proto_payload = {
        "ctri_registration_number": "CTRI/2026/06/044556",
        "trial_title": "Integrative Management of Essential Hypertension via Sarpagandha Ghanavati",
        "ayurvedic_intervention_arm": "Sarpagandha Ghanavati 250mg HS + Shirodhara with Brahmi Taila",
        "control_arm": "Standard Telmisartan 40mg OD",
        "sample_size_target": 120,
        "primary_outcome_measure": "Systolic Blood Pressure Reduction at 8 Weeks",
        "principal_investigator_arn": "ARN-NCISM-2015-8832"
    }
    p_res = client_with_db.post("/api/v1/clinical-trials/protocols", json=proto_payload, headers=headers)
    assert p_res.status_code == 201
    proto_id = p_res.json()["protocol_id"]

    # 2. Get Protocol
    get_p = client_with_db.get(f"/api/v1/clinical-trials/protocols/{proto_id}")
    assert get_p.status_code == 200
    assert get_p.json()["ctri_registration_number"] == "CTRI/2026/06/044556"

    # 3. Enroll Subject
    sub_payload = {
        "protocol_id": proto_id,
        "patient_id": "pat-api-trial-01",
        "assigned_arm": "INTERVENTION",
        "baseline_prakriti": "Pitta-Vata",
        "baseline_score": 156.0
    }
    s_res = client_with_db.post("/api/v1/clinical-trials/subjects", json=sub_payload, headers=headers)
    assert s_res.status_code == 201
    sub_id = s_res.json()["subject_id"]

    # 4. Update Progress
    up_payload = {
        "current_score": 134.0,
        "compliance_rate_pct": 98.0
    }
    up_res = client_with_db.patch(f"/api/v1/clinical-trials/subjects/{sub_id}/progress", json=up_payload)
    assert up_res.status_code == 200
    assert up_res.json()["current_score"] == 134.0

    # 5. Get Analytics
    analytics_res = client_with_db.get(f"/api/v1/clinical-trials/protocols/{proto_id}/analytics")
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()
    assert analytics["total_enrolled"] == 1
    assert analytics["mean_delta_improvement_intervention"] == 22.0  # 156 - 134
