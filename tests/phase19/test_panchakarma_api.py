"""
Integration Tests for Clinical Panchakarma Protocol & Bedside Vega API (Phase 19).
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
        test_db_path = Path(tmpdir) / "panchakarma_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-API-001", "aiia-delhi-central-001", "Anil", "Deshmukh", "1982-07-22", "MALE", "+919876543211", 1700000000)
        )
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "panchakarma_api_test.db")

        with TestClient(app) as client:
            yield client


def test_plan_creation_and_retrieval_endpoints(client_with_db):
    """Verify creating a valid Panchakarma treatment plan and retrieving its dossier."""
    # 1. Login as Physician
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Plan
    plan_payload = {
        "patient_id": "PAT-API-001",
        "procedure_type": "VAMANA",
        "target_shuddhi_tier": "PRAVARA",
        "purva_karma": {
            "deepana_pachana_days": 3,
            "snehapana_daily_doses_ml": [30.0, 60.0, 100.0, 150.0],
            "samyak_snigdha_lakshanas_present": True,
            "swedana_completed": True,
            "pre_op_agi_score": 1.10,
        },
        "prescribed_by_arn": "ARN-NCISM-2015-8832",
    }
    resp = client_with_db.post("/api/v1/panchakarma/plans", json=plan_payload, headers=headers)
    assert resp.status_code == 201
    plan_data = resp.json()
    assert plan_data["procedure_type"] == "VAMANA"
    assert plan_data["current_stage"] == "PURVA_KARMA"
    plan_id = plan_data["plan_id"]

    # 3. Retrieve Plan Details
    get_resp = client_with_db.get(f"/api/v1/panchakarma/plans/{plan_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["plan_id"] == plan_id


def test_plan_creation_ama_gating_violation(client_with_db):
    """Verify that Pre-Op AGI >= 1.80 (Sama Avastha) is blocked with HTTP 422."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    toxic_payload = {
        "patient_id": "PAT-API-001",
        "procedure_type": "VIRECHANA",
        "target_shuddhi_tier": "MADHYAMA",
        "purva_karma": {
            "deepana_pachana_days": 1,
            "snehapana_daily_doses_ml": [30.0],
            "samyak_snigdha_lakshanas_present": True,
            "swedana_completed": True,
            "pre_op_agi_score": 2.10,  # High Ama!
        },
        "prescribed_by_arn": "ARN-NCISM-2015-8832",
    }
    resp = client_with_db.post("/api/v1/panchakarma/plans", json=toxic_payload, headers=headers)
    assert resp.status_code == 422
    assert "Sama Avastha" in resp.json()["detail"]


def test_bedside_vega_logging_and_listing_endpoints(client_with_db):
    """Verify bedside bout submission and chronological retrieval."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Setup plan
    plan_resp = client_with_db.post(
        "/api/v1/panchakarma/plans",
        json={
            "patient_id": "PAT-API-001",
            "procedure_type": "VAMANA",
            "target_shuddhi_tier": "MADHYAMA",
            "purva_karma": {
                "deepana_pachana_days": 3,
                "snehapana_daily_doses_ml": [30.0, 60.0, 100.0],
                "samyak_snigdha_lakshanas_present": True,
                "swedana_completed": True,
                "pre_op_agi_score": 1.15,
            },
            "prescribed_by_arn": "ARN-NCISM-2015-8832",
        },
        headers=headers,
    )
    plan_id = plan_resp.json()["plan_id"]

    # Log 1st Vega
    vega_payload = {
        "plan_id": plan_id,
        "bout_number": 1,
        "output_volume_ml": 250.0,
        "dominant_content": "ANNA",
        "vitals_bp_systolic": 120,
        "vitals_bp_diastolic": 80,
        "vitals_pulse_bpm": 74,
        "attending_nurse_id": "NURSE-BEDSIDE-01",
        "clinical_notes": "Stomach content evacuated smoothly",
    }
    v_resp = client_with_db.post("/api/v1/panchakarma/vegas", json=vega_payload, headers=headers)
    assert v_resp.status_code == 201
    assert v_resp.json()["bout_number"] == 1

    # Log 2nd Vega
    client_with_db.post(
        "/api/v1/panchakarma/vegas",
        json={
            "plan_id": plan_id,
            "bout_number": 2,
            "output_volume_ml": 220.0,
            "dominant_content": "KAPHA",
            "vitals_bp_systolic": 118,
            "vitals_bp_diastolic": 78,
            "vitals_pulse_bpm": 78,
            "attending_nurse_id": "NURSE-BEDSIDE-01",
        },
        headers=headers,
    )

    # List Vegas
    list_resp = client_with_db.get(f"/api/v1/panchakarma/vegas/{plan_id}", headers=headers)
    assert list_resp.status_code == 200
    vegas = list_resp.json()
    assert len(vegas) == 2


def test_shuddhi_evaluation_endpoint(client_with_db):
    """Verify full Chaturvidha Shuddhi evaluation endpoint and Samsarjana diet schedule."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Setup plan
    plan_resp = client_with_db.post(
        "/api/v1/panchakarma/plans",
        json={
            "patient_id": "PAT-API-001",
            "procedure_type": "VAMANA",
            "target_shuddhi_tier": "MADHYAMA",
            "purva_karma": {
                "deepana_pachana_days": 3,
                "snehapana_daily_doses_ml": [30.0, 60.0, 100.0],
                "samyak_snigdha_lakshanas_present": True,
                "swedana_completed": True,
                "pre_op_agi_score": 1.10,
            },
            "prescribed_by_arn": "ARN-NCISM-2015-8832",
        },
        headers=headers,
    )
    plan_id = plan_resp.json()["plan_id"]

    # Log 6 bouts (Madhyama): 1 Anna, 2-4 Kapha, 5-6 Pitta
    contents = ["ANNA", "KAPHA", "KAPHA", "KAPHA", "PITTA", "PITTA"]
    for i, cnt in enumerate(contents, start=1):
        client_with_db.post(
            "/api/v1/panchakarma/vegas",
            json={
                "plan_id": plan_id,
                "bout_number": i,
                "output_volume_ml": 200.0,
                "dominant_content": cnt,
                "vitals_bp_systolic": 116,
                "vitals_bp_diastolic": 76,
                "vitals_pulse_bpm": 80,
                "attending_nurse_id": "NURSE-01",
            },
            headers=headers,
        )

    # Evaluate Shuddhi
    eval_resp = client_with_db.post(
        "/api/v1/panchakarma/shuddhi/evaluate",
        json={
            "plan_id": plan_id,
            "laingiki_symptoms": ["Urolaghava", "Kaphapittashuddhi", "Indriya Prasadana"],
            "assessed_by_arn": "ARN-NCISM-2015-8832",
        },
        headers=headers,
    )
    assert eval_resp.status_code == 200
    res = eval_resp.json()
    assert res["vaigiki_vega_count"] == 6
    assert res["antiki_milestone"] == "PITTANTA"
    assert res["antiki_passed"] is True
    assert res["overall_shuddhi_grade"] == "MADHYAMA"
    assert len(res["samsarjana_krama_schedule"]) == 10
