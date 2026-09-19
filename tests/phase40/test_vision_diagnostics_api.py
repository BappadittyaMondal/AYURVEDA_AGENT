"""
tests/phase40/test_vision_diagnostics_api.py - Integration API tests for Phase 40 Computer Vision Optical Diagnostics.
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
        test_db_path = Path(tmpdir) / "vision_api_test.db"
        init_database(test_db_path)

        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("pat-api-p40-01", "aiia-delhi-central-001", "Kavita", "Deshmukh", "1992-03-24", "FEMALE", "+919876543111", 1700000000)
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "vision_api_test.db")

        with TestClient(app) as client:
            yield client


def test_vision_diagnostics_api_full_lifecycle(client_with_db):
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Register Calibration Target
    calib_payload = {
        "target_id": "API-CALIB-01",
        "color_card_standard": "AYUR_CLINICAL_GREY_18PCT",
        "reference_l": 50.0,
        "reference_a": 0.0,
        "reference_b": 0.0,
        "tolerance_delta_e": 2.0
    }
    calib_res = client_with_db.post("/api/v1/vision-diagnostics/calibration-targets", json=calib_payload, headers=headers)
    assert calib_res.status_code == 201
    assert calib_res.json()["target_id"] == "API-CALIB-01"

    # 2. Get Calibration Target
    get_res = client_with_db.get("/api/v1/vision-diagnostics/calibration-targets/API-CALIB-01")
    assert get_res.status_code == 200
    assert get_res.json()["reference_l"] == 50.0

    # 3. Analyze Tongue Optical Image
    analyze_payload = {
        "patient_id": "pat-api-p40-01",
        "hospital_id": "aiia-delhi-central-001",
        "anatomical_target": "JIHWA_TONGUE",
        "image_base64_or_bytes_hash": "sha256-tongue-optical-api-test",
        "raw_cielab_l": 64.0,
        "raw_cielab_a": 28.5,
        "raw_cielab_b": 15.0,
        "coating_coverage_pct": 12.0,
        "calibration_target_id": "API-CALIB-01"
    }
    inf_res = client_with_db.post("/api/v1/vision-diagnostics/analyze", json=analyze_payload, headers=headers)
    assert inf_res.status_code == 201
    data = inf_res.json()
    assert data["inference_id"].startswith("inf-")
    assert "Paittika Jihwa" in data["clinical_interpretation"]

    # 4. Fetch Patient Inferences
    hist_res = client_with_db.get("/api/v1/vision-diagnostics/patient/pat-api-p40-01/inferences")
    assert hist_res.status_code == 200
    inferences = hist_res.json()
    assert len(inferences) >= 1
    assert inferences[0]["inference_id"] == data["inference_id"]
