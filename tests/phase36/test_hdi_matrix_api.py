"""
Phase 36: Integration Tests for Real-Time Herb-Drug Interaction REST API
========================================================================
Verifies:
1. POST /api/v1/hdi/cross-check
2. POST /api/v1/hdi/override
3. GET /api/v1/hdi/rules
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
        test_db_path = Path(tmpdir) / "hdi_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-HDI-API-01", "aiia-delhi-central-001", "Subhash", "Bose", "1972-01-23", "MALE", "+919876543222", 1700000000)
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "hdi_api_test.db")

        with TestClient(app) as client:
            yield client


def test_hdi_api_workflow(client_with_db):
    """Verify HDI cross-check, override, and rules list via REST API."""
    # 1. Login as Physician
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get 28-Point Rules Catalog
    rules_resp = client_with_db.get("/api/v1/hdi/rules", headers=headers)
    assert rules_resp.status_code == 200
    rules = rules_resp.json()
    assert len(rules) >= 28

    # 3. Cross-Check with Critical Conflict (Digoxin + Arjuna)
    check_payload = {
        "patient_id": "PAT-HDI-API-01",
        "hospital_id": "aiia-delhi-central-001",
        "prescribed_ayurvedic_herbs": ["Arjuna Ksheerapaka", "Prabhakar Vati"],
        "current_allopathic_medications": ["Digoxin 0.25mg"],
        "attending_physician_arn": "ARN-NCISM-2015-8832"
    }
    check_resp = client_with_db.post("/api/v1/hdi/cross-check", json=check_payload, headers=headers)
    assert check_resp.status_code == 200
    check_data = check_resp.json()
    assert not check_data["is_safe_to_prescribe"]
    assert len(check_data["critical_blocks"]) >= 1
    assert "arjuna" in check_data["critical_blocks"][0]["herb"].lower()

    # 4. Physician Override
    override_payload = {
        "patient_id": "PAT-HDI-API-01",
        "hospital_id": "aiia-delhi-central-001",
        "rule_id": "HDI-14",
        "prescribed_herb": "Arjuna",
        "concurrent_drug": "Digoxin",
        "physician_arn": "ARN-NCISM-2015-8832",
        "clinical_justification": "Digoxin discontinued 72 hours ago. Serum digitalis level is zero."
    }
    over_resp = client_with_db.post("/api/v1/hdi/override", json=override_payload, headers=headers)
    assert over_resp.status_code == 200
    over_data = over_resp.json()
    assert over_data["status"] == "OVERRIDE_RECORDED_AND_LOGGED"
