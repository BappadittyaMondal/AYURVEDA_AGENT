"""
Integration Tests for Swasthavritta, Dinacharya, Ritucharya & Vega-Dharana API (Phase 22).
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
        test_db_path = Path(tmpdir) / "swasthavritta_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-SWASTHA-API-01", "aiia-delhi-central-001", "Gaurav", "Pandey", "1992-06-18", "MALE", "+919876543202", 1700000000)
        )
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "swasthavritta_api_test.db")

        with TestClient(app) as client:
            yield client


def test_circadian_clock_endpoint(client_with_db):
    """Verify circadian clock status query with and without simulated hour."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Query current clock
    resp_now = client_with_db.get("/api/v1/swasthavritta/circadian-clock", headers=headers)
    assert resp_now.status_code == 200
    data_now = resp_now.json()
    assert "active_period" in data_now
    assert "dominant_dosha" in data_now

    # 2. Simulate 12:00 PM (Pitta Midday)
    resp_noon = client_with_db.get("/api/v1/swasthavritta/circadian-clock?hour=12&minute=0", headers=headers)
    assert resp_noon.status_code == 200
    data_noon = resp_noon.json()
    assert data_noon["active_period"] == "PITTA_MIDDAY"
    assert "Pitta" in data_noon["dominant_dosha"]


def test_dinacharya_steps_endpoint(client_with_db):
    """Verify listing all canonical Dinacharya steps."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client_with_db.get("/api/v1/swasthavritta/dinacharya/steps", headers=headers)
    assert resp.status_code == 200
    steps = resp.json()
    assert len(steps) >= 12
    assert any(s["step_id"] == "DINA-ABHYANGA" for s in steps)


def test_dinacharya_audit_endpoint(client_with_db):
    """Verify submitting a lifestyle routine for Dinacharya compliance audit."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    audit_payload = {
        "patient_id": "PAT-SWASTHA-API-01",
        "wake_up_time": "05:30 AM",
        "bed_time": "10:15 PM",
        "breakfast_time": "08:30 AM",
        "lunch_time": "12:45 PM",
        "dinner_time": "07:30 PM",
        "has_daytime_nap": False,
        "exercise_habit": "MODERATE",
        "dinacharya_practices": ["USHAPANA", "DANTADHAVANA", "JIHWA_NIRLEKHANA", "ABHYANGA", "PRATIMARSHA_NASYA"]
    }
    resp = client_with_db.post("/api/v1/swasthavritta/dinacharya/audit", json=audit_payload, headers=headers)
    assert resp.status_code == 201
    audit_data = resp.json()
    assert audit_data["compliance_score"] >= 80.0
    assert audit_data["circadian_alignment"] == "OPTIMAL"
    assert audit_data["patient_id"] == "PAT-SWASTHA-API-01"


def test_adharaniya_vegas_endpoint(client_with_db):
    """Verify listing all 13 non-suppressible natural urges and their pathologies."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client_with_db.get("/api/v1/swasthavritta/adharaniya-vegas", headers=headers)
    assert resp.status_code == 200
    vegas = resp.json()
    assert len(vegas) == 13
    assert any(v["vega_type"] == "MUTRA" for v in vegas)
    assert any(v["vega_type"] == "PURISHA" for v in vegas)


def test_vega_suppression_log_endpoint(client_with_db):
    """Verify logging a natural urge suppression habit and receiving pathology assessment."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    suppression_payload = {
        "patient_id": "PAT-SWASTHA-API-01",
        "vega_type": "APANA_VATA",
        "frequency": "DAILY",
        "duration_months": 6,
        "presenting_symptoms": ["Bloating", "Abdominal discomfort"]
    }
    resp = client_with_db.post("/api/v1/swasthavritta/vegas/log-suppression", json=suppression_payload, headers=headers)
    assert resp.status_code == 201
    pathology = resp.json()
    assert pathology["secondary_udavarta_risk"] == "CRITICAL"
    assert "Apana Vata" in pathology["primary_vitiated_dosha"]
    assert "Hingwashtaka" in pathology["remediation_protocol"] or "Basti" in pathology["remediation_protocol"]


def test_ritucharya_calendar_endpoint(client_with_db):
    """Verify retrieving full 6-season Ritucharya calendar."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client_with_db.get("/api/v1/swasthavritta/ritucharya/calendar", headers=headers)
    assert resp.status_code == 200
    calendar = resp.json()
    assert len(calendar) == 6
    assert any(r["ritu_code"] == "VASANTA" for r in calendar)
    assert any(r["ritu_code"] == "VARSHA" for r in calendar)


def test_current_ritucharya_endpoint(client_with_db):
    """Verify evaluating active Ritu and seasonal Shodhana for given dates."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Query Spring date (Vasanta)
    resp_spring = client_with_db.get("/api/v1/swasthavritta/ritucharya/current?date_str=2026-04-05", headers=headers)
    assert resp_spring.status_code == 200
    res_data = resp_spring.json()
    assert res_data["active_ritu"] == "VASANTA"
    assert "VAMANA" in res_data["recommended_seasonal_shodhana"].upper()

    # Invalid date format
    resp_bad = client_with_db.get("/api/v1/swasthavritta/ritucharya/current?date_str=invalid-date", headers=headers)
    assert resp_bad.status_code == 400
