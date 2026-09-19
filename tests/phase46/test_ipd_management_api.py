"""
tests/phase46/test_ipd_management_api.py - Integration API tests for Phase 46 IPD Bed Management endpoints.
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
        test_db_path = Path(tmpdir) / "ipd_api_test.db"
        init_database(test_db_path)

        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("pat-api-ipd-01", "aiia-delhi-central-001", "Harish", "Chauhan", "1984-08-30", "MALE", "+919876542233", 1700000000)
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "ipd_api_test.db")

        with TestClient(app) as client:
            yield client


def test_ipd_management_api_lifecycle(client_with_db):
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Allocate Bed
    alloc_payload = {
        "patient_id": "pat-api-ipd-01",
        "hospital_id": "aiia-delhi-central-001",
        "ward_name": "SHALYA_SURGICAL_WARD",
        "bed_number": "BED-S-05",
        "attending_rmp_arn": "ARN-NCISM-2015-8832"
    }
    alloc_res = client_with_db.post("/api/v1/ipd/allocations", json=alloc_payload, headers=headers)
    assert alloc_res.status_code == 201
    alloc_id = alloc_res.json()["allocation_id"]

    # 2. Check Ward Occupancy
    occ_res = client_with_db.get("/api/v1/ipd/beds/occupancy?ward_name=SHALYA_SURGICAL_WARD")
    assert occ_res.status_code == 200
    assert len(occ_res.json()) >= 1

    # 3. Record Nursing Chart
    chart_payload = {
        "allocation_id": alloc_id,
        "patient_id": "pat-api-ipd-01",
        "vital_bp_systolic": 118,
        "vital_bp_diastolic": 76,
        "vital_pulse_bpm": 68,
        "panchakarma_therapy_administered": "Post-op Vrana Prakshalana with Triphala Kashaya",
        "vega_count": 0,
        "jeerna_ahara_lakshana": "Normal Agni",
        "nursing_notes": "Wound margins healthy, clean granulation",
        "nurse_name": "Nurse Suniti Roy"
    }
    chart_res = client_with_db.post("/api/v1/ipd/nursing-charts", json=chart_payload, headers=headers)
    assert chart_res.status_code == 201
    assert chart_res.json()["chart_id"].startswith("nrs-")

    # 4. Get Nursing Charts
    get_charts = client_with_db.get(f"/api/v1/ipd/allocations/{alloc_id}/charts")
    assert get_charts.status_code == 200
    assert len(get_charts.json()) >= 1

    # 5. Discharge Patient
    disch_res = client_with_db.post(f"/api/v1/ipd/allocations/{alloc_id}/discharge")
    assert disch_res.status_code == 200
    assert disch_res.json()["status"] == "DISCHARGED"
