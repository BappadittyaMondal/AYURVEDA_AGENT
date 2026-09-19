"""Phase 06: Integration Test Suite for Nadi Telemetry Processing & Simulation API."""
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
        test_db_path = Path(tmpdir) / "nadi_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "nadi_api_test.db")

        with TestClient(app) as client:
            yield client


def test_nadi_simulation_endpoint(client_with_db):
    """Verify on-demand generation of synthetic Nadi calibration waveforms."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sim_payload = {
        "gati": "SARPA",
        "duration_seconds": 4.0,
        "sampling_rate_hz": 250,
        "noise_level": 0.01
    }
    resp = client_with_db.post("/api/v1/nadi/simulate", json=sim_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["gati"] == "SARPA"
    assert data["sample_count"] == 1000  # 4s * 250 Hz
    assert len(data["synthetic_samples"]) == 1000


def test_nadi_telemetry_processing_lifecycle(client_with_db):
    """Verify full clinical pipeline: simulate Manduka telemetry, process via DSP, retrieve latest session."""
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
        "abha_id": "33-4455-6677-8899",
        "first_name": "Nandini",
        "last_name": "Rao",
        "dob": "1980-07-14",
        "gender": "FEMALE"
    }
    pat_resp = client_with_db.post("/api/v1/patients", json=pat_payload, headers=headers)
    assert pat_resp.status_code == 201
    patient_id = pat_resp.json()["patient_id"]

    # 3. Generate synthetic Manduka (Pitta) pulse telemetry
    sim_resp = client_with_db.post(
        "/api/v1/nadi/simulate",
        json={"gati": "MANDUKA", "duration_seconds": 4.0, "sampling_rate_hz": 250, "noise_level": 0.01},
        headers=headers
    )
    samples = sim_resp.json()["synthetic_samples"]

    # 4. Ingest and process telemetry stream
    ingest_payload = {
        "patient_id": patient_id,
        "device_id": "NADI_SENSOR_BENCH_01",
        "sampling_rate_hz": 250,
        "raw_pressure_samples": samples
    }
    proc_resp = client_with_db.post("/api/v1/nadi/process", json=ingest_payload, headers=headers)
    assert proc_resp.status_code == 201
    data = proc_resp.json()

    assert data["session_id"].startswith("nad-")
    assert data["primary_gati"] == "MANDUKA"
    assert data["doshic_weights"]["pitta"] > 0.45
    assert data["heart_rate_bpm"] > 50.0

    # 5. Retrieve latest Nadi telemetry session
    latest_resp = client_with_db.get(f"/api/v1/nadi/patients/{patient_id}/latest", headers=headers)
    assert latest_resp.status_code == 200
    latest_data = latest_resp.json()
    assert latest_data["session_id"] == data["session_id"]
    assert latest_data["primary_gati"] == "MANDUKA"
