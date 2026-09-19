"""Phase 10: Integration Test Suite for Dhatu Sarata Tissue Vitality Index API."""
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
        test_db_path = Path(tmpdir) / "dhatu_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "dhatu_api_test.db")

        with TestClient(app) as client:
            yield client


def test_dhatu_sarata_reference_endpoint(client_with_db):
    """Verify listing of Ashta Sara tissue domains."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client_with_db.get("/api/v1/dhatu-sarata/reference", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 8
    assert any(d["dhatu"] == "SHUKRA" for d in data)


def test_dhatu_sarata_evaluation_and_retrieval_lifecycle(client_with_db):
    """Verify complete evaluation workflow: patient registration, 8-dhatu evaluation, latest & history."""
    # 1. Login
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Register patient
    pat_payload = {
        "hospital_id": "aiia-delhi-central-001",
        "first_name": "Venkatesh",
        "last_name": "Pillai",
        "dob": "1990-09-25",
        "gender": "MALE",
        "contact_phone": "+919876543233",
        "abha_id": "14-5566-7788-9900",
    }
    reg_resp = client_with_db.post("/api/v1/patients", json=pat_payload, headers=headers)
    assert reg_resp.status_code == 201
    patient_id = reg_resp.json()["patient_id"]

    # 3. Evaluate Dhatu Sarata (Superior / Pravara profile)
    eval_payload = {
        "patient_id": patient_id,
        "dhatu_ratings": [
            {"dhatu": "RASA", "score": 0.85, "clinical_notes": "Radiant hydrated skin"},
            {"dhatu": "RAKTA", "score": 0.90, "clinical_notes": "Excellent vascular perfusion"},
            {"dhatu": "MAMSA", "score": 0.80, "clinical_notes": "Firm muscle tone"},
            {"dhatu": "MEDA", "score": 0.75, "clinical_notes": "Optimal joint lubrication"},
            {"dhatu": "ASTHI", "score": 0.85, "clinical_notes": "Strong skeletal integrity"},
            {"dhatu": "MAJJA", "score": 0.80, "clinical_notes": "Supple joints, good sleep"},
            {"dhatu": "SHUKRA", "score": 0.90, "clinical_notes": "High cellular vigor"},
            {"dhatu": "SATTVA", "score": 0.85, "clinical_notes": "Equanimous mind"},
        ],
    }
    eval_resp = client_with_db.post("/api/v1/dhatu-sarata/evaluate", json=eval_payload, headers=headers)
    assert eval_resp.status_code == 201
    data = eval_resp.json()
    assert data["patient_id"] == patient_id
    assert data["overall_sarata_index"] > 80.0
    assert data["sarata_tier"] == "PRAVARA"
    assert len(data["vulnerable_dhatus"]) == 0
    assert len(data["rasayana_directives"]) == 8

    # 4. Evaluate second exam (Depleted / Avara profile with multiple vulnerable tissues)
    eval_payload_2 = {
        "patient_id": patient_id,
        "dhatu_ratings": [
            {"dhatu": "RASA", "score": 0.40},
            {"dhatu": "RAKTA", "score": 0.35},
            {"dhatu": "MAMSA", "score": 0.45},
            {"dhatu": "MEDA", "score": 0.40},
            {"dhatu": "ASTHI", "score": 0.30},
            {"dhatu": "MAJJA", "score": 0.40},
            {"dhatu": "SHUKRA", "score": 0.35},
            {"dhatu": "SATTVA", "score": 0.40},
        ],
    }
    eval_resp_2 = client_with_db.post("/api/v1/dhatu-sarata/evaluate", json=eval_payload_2, headers=headers)
    assert eval_resp_2.status_code == 201
    data2 = eval_resp_2.json()
    assert data2["sarata_tier"] == "AVARA"
    assert len(data2["vulnerable_dhatus"]) == 8

    # 5. Retrieve latest
    latest_resp = client_with_db.get(f"/api/v1/dhatu-sarata/patients/{patient_id}/latest", headers=headers)
    assert latest_resp.status_code == 200
    assert latest_resp.json()["sarata_tier"] == "AVARA"

    # 6. Retrieve history
    hist_resp = client_with_db.get(f"/api/v1/dhatu-sarata/patients/{patient_id}/history", headers=headers)
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()) == 2


def test_dhatu_sarata_nonexistent_patient_returns_404(client_with_db):
    """Verify 404 response for unregistered patient."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ratings = [{"dhatu": d, "score": 0.5} for d in ["RASA", "RAKTA", "MAMSA", "MEDA", "ASTHI", "MAJJA", "SHUKRA", "SATTVA"]]
    resp = client_with_db.post(
        "/api/v1/dhatu-sarata/evaluate",
        json={"patient_id": "nonexistent-patient-uuid", "dhatu_ratings": ratings},
        headers=headers,
    )
    assert resp.status_code == 404
