"""Phase 03: Integration Test Suite for Vikriti API Endpoints & Longitudinal History."""
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
        test_db_path = Path(tmpdir) / "vikriti_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "vikriti_api_test.db")

        with TestClient(app) as client:
            yield client


def test_vikriti_symptoms_list_endpoint(client_with_db):
    """Verify retrieval of the 24 standard clinical symptom parameters."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client_with_db.get("/api/v1/vikriti/symptoms", headers=headers)
    assert resp.status_code == 200
    symptoms = resp.json()
    assert len(symptoms) == 24
    doshas = {s["dosha"] for s in symptoms}
    assert doshas == {"V", "P", "K"}


def test_vikriti_evaluation_lifecycle(client_with_db):
    """Verify end-to-end clinical workflow: create patient, submit Vikriti, retrieve latest & history."""
    # 1. Login as physician RMP
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Register patient in MPI
    pat_payload = {
        "hospital_id": "aiia-delhi-central-001",
        "abha_id": "77-2233-4455-6677",
        "first_name": "Devendra",
        "last_name": "Mishra",
        "dob": "1985-08-10",
        "gender": "MALE"
    }
    pat_resp = client_with_db.post("/api/v1/patients", json=pat_payload, headers=headers)
    assert pat_resp.status_code == 201
    patient_id = pat_resp.json()["patient_id"]

    # 3. Submit acute Vikriti (Severe Vata presentation: pain, insomnia, tremors, bloating)
    acute_symptoms = {
        "VS01": 3,  # Shoola (severe pain)
        "VS02": 2,  # Rukshata (dryness)
        "VS03": 3,  # Anidra (severe insomnia)
        "VS04": 2,  # Vepathu (tremor)
        "VS05": 3,  # Adhmana (bloating)
        "VS08": 2,  # Anxiety
        "VS09": 0,  # Pitta signs absent
        "VS17": 0   # Kapha signs absent
    }

    assess_resp = client_with_db.post(
        f"/api/v1/vikriti/patients/{patient_id}",
        json={"symptoms": acute_symptoms},
        headers=headers
    )
    assert assess_resp.status_code == 201
    data = assess_resp.json()

    assert data["assessment_id"].startswith("vik-")
    assert data["vikriti_current"]["vata"] > 0.80
    assert data["kl_divergence"] > 0.0
    assert data["mahalanobis_distance"] > 0.0
    assert data["vsi_score"] > 40.0
    assert data["severity_tier"] in ["MADHYAMA_VIKRITI", "TIVRA_VIKRITI"]
    assert data["doshic_deltas"]["dominant_vitiation"] == "VATA"
    assert data["doshic_deltas"]["vata"]["state"] == "VRIDDHI"

    # 4. Fetch latest Vikriti
    latest_resp = client_with_db.get(f"/api/v1/vikriti/patients/{patient_id}/latest", headers=headers)
    assert latest_resp.status_code == 200
    latest_data = latest_resp.json()
    assert latest_data["assessment_id"] == data["assessment_id"]
    assert latest_data["vsi_score"] == data["vsi_score"]

    # 5. Fetch longitudinal history
    hist_resp = client_with_db.get(f"/api/v1/vikriti/patients/{patient_id}/history", headers=headers)
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 1
    assert history[0]["assessment_id"] == data["assessment_id"]
