"""
tests/phase41/test_patient_portal_api.py - Integration API tests for Phase 41 Patient Portal.
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
        test_db_path = Path(tmpdir) / "portal_api_test.db"
        init_database(test_db_path)

        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("pat-portal-api-01", "aiia-delhi-central-001", "Sunita", "Patil", "1994-09-15", "FEMALE", "+919876000000", 1700000000)
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "portal_api_test.db")

        with TestClient(app) as client:
            yield client


def test_patient_portal_api_lifecycle(client_with_db):
    # 1. Register Account
    reg_payload = {
        "patient_id": "pat-portal-api-01",
        "hospital_id": "aiia-delhi-central-001",
        "phone_number": "+919876000000",
        "password": "PatilSecurePassword2026",
        "abha_address": "sunita.patil@abdm"
    }
    reg_res = client_with_db.post("/api/v1/patient-portal/register", json=reg_payload)
    assert reg_res.status_code == 201
    assert reg_res.json()["account_id"].startswith("acc-")

    # 2. Login
    login_payload = {
        "phone_number": "+919876000000",
        "password": "PatilSecurePassword2026"
    }
    login_res = client_with_db.post("/api/v1/patient-portal/login", json=login_payload)
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    assert token is not None

    # 3. Submit Daily Log
    daily_payload = {
        "patient_id": "pat-portal-api-01",
        "hospital_id": "aiia-delhi-central-001",
        "log_date": "2026-09-20",
        "diet_adherence_score": 95,
        "pathya_followed_notes": "Warm mung dal soup, no curd at night",
        "ahara_craving": "None",
        "bowel_movement_type": "SAMYAK_NORMAL_FORMED",
        "sleep_duration_hours": 7.5,
        "stress_level": 2
    }
    log_res = client_with_db.post("/api/v1/patient-portal/daily-logs", json=daily_payload)
    assert log_res.status_code == 201
    assert log_res.json()["log_id"].startswith("log-")

    # 4. Get Summary
    summary_res = client_with_db.get("/api/v1/patient-portal/summary/pat-portal-api-01")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["full_name"] == "Sunita Patil"
    assert summary["total_logs"] == 1
