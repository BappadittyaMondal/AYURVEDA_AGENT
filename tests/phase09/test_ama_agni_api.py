"""Phase 09: Integration Test Suite for Quantitative Ama Grading Index (AGI) & Agni Gating API."""
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
        test_db_path = Path(tmpdir) / "ama_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "ama_api_test.db")

        with TestClient(app) as client:
            yield client


def test_symptoms_list_endpoint(client_with_db):
    """Verify metadata listing for cardinal Ama symptoms."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client_with_db.get("/api/v1/ama-agni/symptoms-list", headers=headers)
    assert resp.status_code == 200
    symptoms = resp.json()
    assert len(symptoms) == 10
    assert any(s["id"] == "srotorodha" for s in symptoms)


def test_ama_agni_evaluation_and_retrieval_lifecycle(client_with_db):
    """Verify complete diagnostic workflow: registration, evaluate AGI, retrieve latest and history."""
    # 1. Login as physician RMP
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Register patient
    pat_payload = {
        "hospital_id": "aiia-delhi-central-001",
        "first_name": "Raghavan",
        "last_name": "Nambiar",
        "dob": "1972-03-18",
        "gender": "MALE",
        "contact_phone": "+919876543222",
        "abha_id": "14-3322-1100-9988",
    }
    reg_resp = client_with_db.post("/api/v1/patients", json=pat_payload, headers=headers)
    assert reg_resp.status_code == 201
    patient_id = reg_resp.json()["patient_id"]

    # 3. Evaluate first: Moderate Ama state (Gated for Deepana-Pachana)
    eval_payload = {
        "patient_id": patient_id,
        "symptoms": {
            "srotorodha": 2,
            "balabhramsha": 2,
            "gaurava": 2,
            "anilamudhata": 1,
            "alasya": 2,
            "apakti": 2,
            "nishthiva": 1,
            "malasanga": 1,
            "aruchi": 2,
            "klama": 1,
        },
        "agni_params": {
            "appetite_regularity": 0.4,
            "digestion_speed_hours": 7.0,
            "post_prandial_heaviness": 0.7,
            "burning_sensation": 0.1,
            "abdominal_distension": 0.3,
        },
    }
    eval_resp = client_with_db.post("/api/v1/ama-agni/evaluate", json=eval_payload, headers=headers)
    assert eval_resp.status_code == 201
    data1 = eval_resp.json()
    assert data1["patient_id"] == patient_id
    assert data1["ama_grade"] == "MADHYAMA_AMA"
    assert data1["shodhana_permitted"] is False
    assert data1["gating_status"] == "GATED_FOR_DEEPANA_PACHANA"
    assert len(data1["therapeutic_directives"]) > 0

    # 4. Evaluate second: Nirama state after Pachana (Cleared for Shodhana)
    eval_payload_2 = {
        "patient_id": patient_id,
        "symptoms": {
            "srotorodha": 0,
            "balabhramsha": 0,
            "gaurava": 0,
            "anilamudhata": 0,
            "alasya": 0,
            "apakti": 0,
            "nishthiva": 0,
            "malasanga": 0,
            "aruchi": 0,
            "klama": 0,
        },
        "agni_params": {
            "appetite_regularity": 1.0,
            "digestion_speed_hours": 4.0,
            "post_prandial_heaviness": 0.0,
            "burning_sensation": 0.0,
            "abdominal_distension": 0.0,
        },
    }
    eval_resp_2 = client_with_db.post("/api/v1/ama-agni/evaluate", json=eval_payload_2, headers=headers)
    assert eval_resp_2.status_code == 201
    data2 = eval_resp_2.json()
    assert data2["ama_grade"] == "NIRAMA"
    assert data2["shodhana_permitted"] is True
    assert data2["gating_status"] == "CLEARED_FOR_SHODHANA"

    # 5. Retrieve latest (should be Nirama cleared)
    latest_resp = client_with_db.get(f"/api/v1/ama-agni/patients/{patient_id}/latest", headers=headers)
    assert latest_resp.status_code == 200
    assert latest_resp.json()["ama_grade"] == "NIRAMA"
    assert latest_resp.json()["shodhana_permitted"] is True

    # 6. Retrieve history (should have 2 assessments)
    history_resp = client_with_db.get(f"/api/v1/ama-agni/patients/{patient_id}/history", headers=headers)
    assert history_resp.status_code == 200
    assert len(history_resp.json()) == 2


def test_ama_agni_nonexistent_patient_returns_404(client_with_db):
    """Verify 404 error when evaluating non-existent patient."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": "nonexistent-patient-uuid",
        "symptoms": {},
        "agni_params": {},
    }
    resp = client_with_db.post("/api/v1/ama-agni/evaluate", json=payload, headers=headers)
    assert resp.status_code == 404
