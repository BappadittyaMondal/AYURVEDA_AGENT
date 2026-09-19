"""Phase 05: Integration Test Suite for Dashavidha Pariksha API Endpoints."""
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
        test_db_path = Path(tmpdir) / "dashavidha_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "dashavidha_api_test.db")

        with TestClient(app) as client:
            yield client


def test_dashavidha_api_lifecycle(client_with_db):
    """Verify end-to-end clinical workflow: create patient, record 10-fold examination, query latest & history."""
    # 1. Login as physician RMP
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Register patient
    pat_payload = {
        "hospital_id": "aiia-delhi-central-001",
        "abha_id": "44-5566-7788-9900",
        "first_name": "Kavita",
        "last_name": "Joshi",
        "dob": "1992-12-05",
        "gender": "FEMALE"
    }
    pat_resp = client_with_db.post("/api/v1/patients", json=pat_payload, headers=headers)
    assert pat_resp.status_code == 201
    patient_id = pat_resp.json()["patient_id"]

    # 3. Submit 10-fold systemic assessment
    exam_payload = {
        "dushya": {
            "primary_dushyas": ["RASA", "RAKTA"],
            "chronicity_days": 15
        },
        "desha": {
            "bhumi": "SADHARANA",
            "deha": "SHAKHA"
        },
        "bala": {
            "sahaja": "PRAVARA",
            "kalaja": "PRAVARA",
            "yuktikrita": "MADHYAMA"
        },
        "kala_season": "SHARAD",
        "anala": {
            "agni": "TIKSHNAGNI",
            "postprandial_heaviness": False
        },
        "vayas_stage": "MADHYAMA",
        "sattva": "PRAVARA",
        "satmya": "PRAVARA",
        "ahara_shakti": {
            "abhyavaharana": "PRAVARA",
            "jarana": "MADHYAMA"
        }
    }

    exam_resp = client_with_db.post(
        f"/api/v1/dashavidha/patients/{patient_id}",
        json=exam_payload,
        headers=headers
    )
    assert exam_resp.status_code == 201
    data = exam_resp.json()

    assert data["assessment_id"].startswith("dsh-")
    assert data["rogi_bala_score"] > 70.0
    assert data["roga_bala_score"] < 50.0
    assert data["rogi_roga_ratio"] > 1.20
    assert data["therapeutic_eligibility"] == "SHODHANA_ELIGIBLE"
    assert data["evaluator_arn"] == "ARN-NCISM-2015-8832"

    # 4. Fetch latest assessment
    latest_resp = client_with_db.get(f"/api/v1/dashavidha/patients/{patient_id}/latest", headers=headers)
    assert latest_resp.status_code == 200
    latest_data = latest_resp.json()
    assert latest_data["assessment_id"] == data["assessment_id"]
    assert latest_data["rogi_bala_score"] == data["rogi_bala_score"]

    # 5. Fetch history
    hist_resp = client_with_db.get(f"/api/v1/dashavidha/patients/{patient_id}/history", headers=headers)
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()) == 1
    assert hist_resp.json()[0]["assessment_id"] == data["assessment_id"]
