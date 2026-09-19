"""Phase 08: Integration Test Suite for Jihwa Pariksha Computer Vision & Micro-Colorimetry API."""
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
        test_db_path = Path(tmpdir) / "jihwa_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "jihwa_api_test.db")

        with TestClient(app) as client:
            yield client


def test_jihwa_simulation_endpoint(client_with_db):
    """Verify on-demand generation of synthetic Jihwa calibration parameters."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sim_payload = {"target_condition": "KAPHA_AMA"}
    resp = client_with_db.post("/api/v1/jihwa/simulate", json=sim_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_condition"] == "KAPHA_AMA"
    assert data["expected_dominant_color"] == "WHITE"
    assert data["expected_dosha"] == "KAPHA"
    assert len(data["regions"]) == 3


def test_jihwa_evaluation_and_retrieval_lifecycle(client_with_db):
    """Verify complete diagnostic workflow: registration, evaluate tongue test, retrieve latest and history."""
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
        "first_name": "Kalyani",
        "last_name": "Iyer",
        "dob": "1985-04-12",
        "gender": "FEMALE",
        "contact_phone": "+919876543219",
        "abha_id": "14-8899-7766-5544",
    }
    reg_resp = client_with_db.post("/api/v1/patients", json=pat_payload, headers=headers)
    assert reg_resp.status_code == 201
    patient_id = reg_resp.json()["patient_id"]

    # 3. Evaluate first exam (Kapha-Ama coating)
    eval_payload = {
        "patient_id": patient_id,
        "coating_ratio_percent": 72.0,
        "fissure_density": 0.0,
        "papillary_roughness": 0.2,
        "observed_moisture": 0.8,
        "image_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "regions": [
            {"region": "ROOT", "rgb_hex": "#F0F0EE", "cie_l": 88.0, "cie_a": -0.5, "cie_b": 3.0},
            {"region": "CENTER", "rgb_hex": "#EAEAEA", "cie_l": 85.0, "cie_a": 0.0, "cie_b": 2.5},
            {"region": "TIP_MARGINS", "rgb_hex": "#E0E0DA", "cie_l": 82.0, "cie_a": 1.0, "cie_b": 4.0},
        ],
    }
    eval_resp = client_with_db.post("/api/v1/jihwa/evaluate", json=eval_payload, headers=headers)
    assert eval_resp.status_code == 201
    eval_data = eval_resp.json()
    assert eval_data["patient_id"] == patient_id
    assert eval_data["primary_dosha"] == "KAPHA"
    assert eval_data["dominant_color"] == "WHITE"
    assert eval_data["coating_thickness"] == "THICK"
    assert eval_data["is_sama"] is True
    assert eval_data["ama_score"] > 60.0

    # 4. Evaluate second exam (Vata-Dry cracked tongue)
    eval_payload_2 = {
        "patient_id": patient_id,
        "coating_ratio_percent": 10.0,
        "fissure_density": 0.75,
        "papillary_roughness": 0.8,
        "observed_moisture": 0.1,
        "regions": [
            {"region": "ROOT", "rgb_hex": "#504035", "cie_l": 30.0, "cie_a": 5.0, "cie_b": 10.0},
            {"region": "CENTER", "rgb_hex": "#5A453A", "cie_l": 32.0, "cie_a": 6.0, "cie_b": 12.0},
            {"region": "TIP_MARGINS", "rgb_hex": "#4D382C", "cie_l": 28.0, "cie_a": 4.5, "cie_b": 9.0},
        ],
    }
    eval_resp_2 = client_with_db.post("/api/v1/jihwa/evaluate", json=eval_payload_2, headers=headers)
    assert eval_resp_2.status_code == 201
    assert eval_resp_2.json()["primary_dosha"] == "VATA"
    assert eval_resp_2.json()["dominant_color"] == "BROWN_BLACK"

    # 5. Retrieve latest
    latest_resp = client_with_db.get(f"/api/v1/jihwa/patients/{patient_id}/latest", headers=headers)
    assert latest_resp.status_code == 200
    assert latest_resp.json()["primary_dosha"] == "VATA"

    # 6. Retrieve history
    history_resp = client_with_db.get(f"/api/v1/jihwa/patients/{patient_id}/history", headers=headers)
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) == 2


def test_jihwa_nonexistent_patient_returns_404(client_with_db):
    """Verify 404 response when patient does not exist."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": "nonexistent-patient-uuid",
        "coating_ratio_percent": 15.0,
        "regions": [
            {"region": "CENTER", "rgb_hex": "#FFFFFF", "cie_l": 90.0, "cie_a": 0.0, "cie_b": 0.0}
        ],
    }
    resp = client_with_db.post("/api/v1/jihwa/evaluate", json=payload, headers=headers)
    assert resp.status_code == 404
