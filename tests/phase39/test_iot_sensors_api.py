"""
tests/phase39/test_iot_sensors_api.py - Integration API tests for Phase 39 IoT pulse sensor endpoints.
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
        test_db_path = Path(tmpdir) / "iot_api_test.db"
        init_database(test_db_path)

        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("pat-api-p39-01", "aiia-delhi-central-001", "Naveen", "Sharma", "1985-05-12", "MALE", "+919876543210", 1700000000)
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "iot_api_test.db")

        with TestClient(app) as client:
            yield client


def test_iot_sensor_api_full_lifecycle(client_with_db):
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Register Sensor
    reg_payload = {
        "device_id": "DEVICE-API-TEST-001",
        "hospital_id": "aiia-delhi-central-001",
        "device_model": "NADI_TARANGINI_PRO_V3",
        "sampling_rate_hz": 500,
        "calibration_factor": 1.0,
        "assigned_ward_or_clinic": "PANCHAKARMA-UNIT-3"
    }
    reg_res = client_with_db.post("/api/v1/iot-sensors/devices", json=reg_payload, headers=headers)
    assert reg_res.status_code == 201
    assert reg_res.json()["device_id"] == "DEVICE-API-TEST-001"

    # 2. Get Sensor Details
    get_res = client_with_db.get("/api/v1/iot-sensors/devices/DEVICE-API-TEST-001", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["sampling_rate_hz"] == 500

    # 3. Ingest Waveform Packet
    samples = [45.0 + i * 0.5 for i in range(50)]
    ingest_payload = {
        "device_id": "DEVICE-API-TEST-001",
        "patient_id": "pat-api-p39-01",
        "hospital_id": "aiia-delhi-central-001",
        "packet_index": 0,
        "pressure_samples": samples
    }
    ing_res = client_with_db.post("/api/v1/iot-sensors/ingest", json=ingest_payload, headers=headers)
    assert ing_res.status_code == 201
    data = ing_res.json()
    assert data["packet_id"].startswith("pkt-")
    assert data["sample_count"] == 50
    assert "pulse_wave_velocity_mps" in data

    # 4. Fetch Patient Waveform Packets
    list_res = client_with_db.get("/api/v1/iot-sensors/patient/pat-api-p39-01/packets", headers=headers)
    assert list_res.status_code == 200
    pkts = list_res.json()
    assert len(pkts) >= 1
    assert pkts[0]["device_id"] == "DEVICE-API-TEST-001"
