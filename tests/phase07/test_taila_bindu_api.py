"""Phase 07: Integration Test Suite for Taila Bindu Pariksha Diagnostic API."""
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
        test_db_path = Path(tmpdir) / "taila_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "taila_api_test.db")

        with TestClient(app) as client:
            yield client


def test_taila_bindu_simulation_endpoint(client_with_db):
    """Verify on-demand generation of synthetic Taila Bindu physical parameters."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sim_payload = {
        "doshic_condition": "VATA",
        "urine_temp": 25.0,
        "drop_height_angula": 1.0,
    }
    resp = client_with_db.post("/api/v1/taila-bindu/simulate", json=sim_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["doshic_condition"] == "VATA"
    assert data["doshic_shape"] == "SARPA"
    assert data["prognosis_verdict"] == "SADHYA"
    assert data["eccentricity"] > 0.8


def test_taila_bindu_evaluation_and_retrieval_lifecycle(client_with_db):
    """Verify complete diagnostic workflow: registration, evaluate droplet test, retrieve latest and history."""
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
        "first_name": "Devavrata",
        "last_name": "Shastri",
        "dob": "1978-11-20",
        "gender": "MALE",
        "contact_phone": "+919876543210",
        "abha_id": "14-7654-3210-9876",
    }
    reg_resp = client_with_db.post("/api/v1/patients", json=pat_payload, headers=headers)
    assert reg_resp.status_code == 201
    patient_id = reg_resp.json()["patient_id"]

    # 3. Evaluate droplet test (Curable / Sadhya pattern)
    eval_payload = {
        "patient_id": patient_id,
        "urine_temperature_c": 26.5,
        "urine_surface_tension": 64.0,
        "oil_surface_tension": 32.5,
        "interfacial_tension": 15.0,
        "semi_major_axis_mm": 12.0,
        "semi_minor_axis_mm": 11.5,
        "observation_time_sec": 8.0,
        "direction": "NORTH",
        "fragment_count": 1,
        "submerged": False,
    }
    eval_resp = client_with_db.post("/api/v1/taila-bindu/evaluate", json=eval_payload, headers=headers)
    assert eval_resp.status_code == 201
    eval_data = eval_resp.json()
    assert eval_data["patient_id"] == patient_id
    assert eval_data["prognosis_verdict"] == "SADHYA"
    assert eval_data["spreading_coeff"] == pytest.approx(16.5, abs=1e-2)
    assert eval_data["circularity"] > 0.95

    # 4. Evaluate second droplet test (Incurable / Asadhya pattern: Northeast direction)
    eval_payload_2 = {
        "patient_id": patient_id,
        "urine_temperature_c": 28.0,
        "urine_surface_tension": 48.0,
        "semi_major_axis_mm": 16.0,
        "semi_minor_axis_mm": 6.0,
        "observation_time_sec": 5.0,
        "direction": "NORTHEAST",
        "fragment_count": 3,
        "submerged": False,
    }
    eval_resp_2 = client_with_db.post("/api/v1/taila-bindu/evaluate", json=eval_payload_2, headers=headers)
    assert eval_resp_2.status_code == 201
    assert eval_resp_2.json()["prognosis_verdict"] == "ASADHYA"

    # 5. Retrieve latest
    latest_resp = client_with_db.get(f"/api/v1/taila-bindu/patients/{patient_id}/latest", headers=headers)
    assert latest_resp.status_code == 200
    assert latest_resp.json()["prognosis_verdict"] == "ASADHYA"

    # 6. Retrieve history
    history_resp = client_with_db.get(f"/api/v1/taila-bindu/patients/{patient_id}/history", headers=headers)
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) == 2


def test_taila_bindu_nonexistent_patient_returns_404(client_with_db):
    """Verify 404 response when patient does not exist."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": "nonexistent-patient-uuid",
        "urine_temperature_c": 25.0,
        "urine_surface_tension": 60.0,
        "semi_major_axis_mm": 10.0,
        "semi_minor_axis_mm": 10.0,
        "observation_time_sec": 5.0,
        "direction": "EAST",
        "fragment_count": 1,
        "submerged": False,
    }
    resp = client_with_db.post("/api/v1/taila-bindu/evaluate", json=payload, headers=headers)
    assert resp.status_code == 404
