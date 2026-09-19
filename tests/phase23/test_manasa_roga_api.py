"""
Integration Tests for Sattvavajaya Chikitsa & Manasa Roga API (Phase 23).
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
        test_db_path = Path(tmpdir) / "manasa_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-MANASA-API-01", "aiia-delhi-central-001", "Shalini", "Mukherjee", "1988-07-24", "FEMALE", "+919876543112", 1700000000)
        )
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "manasa_api_test.db")

        with TestClient(app) as client:
            yield client


def test_disorders_listing_and_detail_endpoints(client_with_db):
    """Verify listing all psychiatric disorders and fetching detail by code."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List all disorders
    resp = client_with_db.get("/api/v1/manasa-roga/disorders", headers=headers)
    assert resp.status_code == 200
    disorders = resp.json()
    assert len(disorders) >= 9

    # 2. Get detail of UNMADA_PITTAJA
    resp_detail = client_with_db.get("/api/v1/manasa-roga/disorders/UNMADA_PITTAJA", headers=headers)
    assert resp_detail.status_code == 200
    detail = resp_detail.json()
    assert detail["disorder_code"] == "UNMADA_PITTAJA"
    assert "Sadhaka Pitta" in detail["sharirika_dosha"]

    # 3. 404 for unknown
    resp_404 = client_with_db.get("/api/v1/manasa-roga/disorders/UNKNOWN_DISORDER", headers=headers)
    assert resp_404.status_code == 404


def test_manasa_assessment_standard_and_crisis(client_with_db):
    """Verify psychometric assessment endpoint for standard condition and suicide emergency escalation."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Standard Chittodvega (Anxiety)
    std_payload = {
        "patient_id": "PAT-MANASA-API-01",
        "disorder_code": "CHITTODVEGA",
        "raw_sattva": 35.0,
        "raw_rajas": 45.0,
        "raw_tamas": 20.0,
        "dhi_score": 6.0,
        "dhriti_score": 5.0,
        "smriti_score": 6.0,
        "has_suicidal_ideation": False,
        "assessed_by_arn": "AY-DL-2024-998811",
    }
    resp_std = client_with_db.post("/api/v1/manasa-roga/assessments", json=std_payload, headers=headers)
    assert resp_std.status_code == 201
    std_data = resp_std.json()
    assert std_data["crisis_risk_level"] in ["NONE", "LOW"]
    assert std_data["prajnaparadha_index"] < 50.0

    # 2. Crisis with Suicidal Ideation in Avasada
    crisis_payload = {
        "patient_id": "PAT-MANASA-API-01",
        "disorder_code": "AVASADA",
        "raw_sattva": 10.0,
        "raw_rajas": 20.0,
        "raw_tamas": 70.0,
        "dhi_score": 2.0,
        "dhriti_score": 1.0,
        "smriti_score": 2.0,
        "has_suicidal_ideation": True,
        "assessed_by_arn": "AY-DL-2024-998811",
    }
    resp_crisis = client_with_db.post("/api/v1/manasa-roga/assessments", json=crisis_payload, headers=headers)
    assert resp_crisis.status_code == 201
    crisis_data = resp_crisis.json()
    assert crisis_data["crisis_risk_level"] == "CRITICAL_EMERGENCY"
    assert crisis_data["emergency_alert"] is not None
    assert "SUICIDE_FIREWALL" in crisis_data["emergency_alert"]


def test_patient_assessments_history_and_prescriptions(client_with_db):
    """Verify retrieving patient psychiatric history and creating a Trividha Chikitsa prescription."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Assessment
    assess_payload = {
        "patient_id": "PAT-MANASA-API-01",
        "disorder_code": "CHITTODVEGA",
        "raw_sattva": 30.0,
        "raw_rajas": 50.0,
        "raw_tamas": 20.0,
        "dhi_score": 5.0,
        "dhriti_score": 4.0,
        "smriti_score": 6.0,
        "assessed_by_arn": "AY-DL-2024-998811",
    }
    resp_assess = client_with_db.post("/api/v1/manasa-roga/assessments", json=assess_payload, headers=headers)
    assert resp_assess.status_code == 201
    assess_id = resp_assess.json()["assessment_id"]

    # Retrieve history
    resp_hist = client_with_db.get("/api/v1/manasa-roga/assessments/patient/PAT-MANASA-API-01", headers=headers)
    assert resp_hist.status_code == 200
    history = resp_hist.json()
    assert len(history) >= 1
    assert history[0]["assessment_id"] == assess_id

    # Create prescription
    rx_payload = {
        "assessment_id": assess_id,
        "patient_id": "PAT-MANASA-API-01",
        "include_daivavyapashraya": True,
        "include_yukti_medhya": True,
        "include_sattvavajaya_cbt": True,
        "prescribed_by_arn": "AY-DL-2024-998811",
    }
    resp_rx = client_with_db.post("/api/v1/manasa-roga/prescriptions", json=rx_payload, headers=headers)
    assert resp_rx.status_code == 201
    rx_data = resp_rx.json()
    assert rx_data["assessment_id"] == assess_id
    assert len(rx_data["daivavyapashraya_therapies"]) > 0
    assert len(rx_data["yukti_medhya_rasayanas"]) > 0
    assert len(rx_data["sattvavajaya_cbt_interventions"]) > 0
