"""Phase 12: Integration Test Suite for Shat Kriya Kala Staging API."""
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
        test_db_path = Path(tmpdir) / "kriya_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "kriya_api_test.db")

        with TestClient(app) as client:
            yield client


def test_kriya_kala_stages_endpoint(client_with_db):
    """Verify listing of the 6 pathogenesis stages."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client_with_db.get("/api/v1/kriya-kala/stages", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 6
    assert any(s["stage"] == "STHANASAMSHRAYA" for s in data)


def test_kriya_kala_evaluation_and_retrieval_lifecycle(client_with_db):
    """Verify complete Kriya Kala staging lifecycle, latest retrieval, and history."""
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
        "first_name": "Arjun",
        "last_name": "Natarajan",
        "dob": "1994-02-10",
        "gender": "MALE",
        "contact_phone": "+919876543255",
        "abha_id": "14-6677-8899-0011",
    }
    reg_resp = client_with_db.post("/api/v1/patients", json=pat_payload, headers=headers)
    assert reg_resp.status_code == 201
    patient_id = reg_resp.json()["patient_id"]

    # 3. Evaluate first: Sthanasamshraya (Prodromal Stage 4)
    eval_payload = {
        "patient_id": patient_id,
        "observations": {
            "sanchaya_features": 0,
            "prakopa_features": 1,
            "prasara_features": 1,
            "sthanasamshraya_features": 3,
            "vyakti_features": 0,
            "bheda_features": 0,
            "prodromal_symptoms": ["Lethargy", "Bitter mouth taste", "Mild joint stiffness"],
            "manifest_symptoms": [],
            "complications": [],
        },
    }
    eval_resp = client_with_db.post("/api/v1/kriya-kala/evaluate", json=eval_payload, headers=headers)
    assert eval_resp.status_code == 201
    data = eval_resp.json()
    assert data["patient_id"] == patient_id
    assert data["current_stage"] == "STHANASAMSHRAYA"
    assert data["curability_prognosis"] == "KRICHRASADHYA"
    assert 3.5 <= data["pathological_progression_index"] <= 4.8

    # 4. Evaluate second: Early Sanchaya after preventive intervention
    eval_payload_2 = {
        "patient_id": patient_id,
        "observations": {
            "sanchaya_features": 2,
            "prakopa_features": 0,
            "prasara_features": 0,
            "sthanasamshraya_features": 0,
            "vyakti_features": 0,
            "bheda_features": 0,
            "prodromal_symptoms": [],
            "manifest_symptoms": [],
            "complications": [],
        },
    }
    eval_resp_2 = client_with_db.post("/api/v1/kriya-kala/evaluate", json=eval_payload_2, headers=headers)
    assert eval_resp_2.status_code == 201
    data2 = eval_resp_2.json()
    assert data2["current_stage"] == "SANCHAYA"
    assert data2["curability_prognosis"] == "SUKHASADHYA"

    # 5. Retrieve latest
    latest_resp = client_with_db.get(f"/api/v1/kriya-kala/patients/{patient_id}/latest", headers=headers)
    assert latest_resp.status_code == 200
    assert latest_resp.json()["current_stage"] == "SANCHAYA"

    # 6. Retrieve history
    hist_resp = client_with_db.get(f"/api/v1/kriya-kala/patients/{patient_id}/history", headers=headers)
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()) == 2


def test_kriya_kala_nonexistent_patient_returns_404(client_with_db):
    """Verify 404 response for non-existent patient."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": "nonexistent-patient-uuid",
        "observations": {"sanchaya_features": 1},
    }
    resp = client_with_db.post("/api/v1/kriya-kala/evaluate", json=payload, headers=headers)
    assert resp.status_code == 404
