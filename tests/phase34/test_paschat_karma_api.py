"""
Phase 34: Integration Tests for Paschat Karma & Samsarjana Krama REST API
========================================================================
Verifies:
1. Episode initiation via POST /api/v1/paschat-karma/episodes
2. Episode retrieval via GET /api/v1/paschat-karma/episodes/{episode_id}
3. Patient episode listing via GET /api/v1/paschat-karma/patients/{patient_id}
4. Meal intake logging via POST /api/v1/paschat-karma/episodes/{episode_id}/meals
5. Meal history retrieval via GET /api/v1/paschat-karma/episodes/{episode_id}/meals
6. Trajectory calculation via GET /api/v1/paschat-karma/episodes/{episode_id}/trajectory
7. Parihara audit via POST /api/v1/paschat-karma/episodes/{episode_id}/parihara-audit
8. Rasayana readiness evaluation via POST /api/v1/paschat-karma/episodes/{episode_id}/rasayana-readiness
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
        test_db_path = Path(tmpdir) / "paschat_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-PASCHAT-API-01", "aiia-delhi-central-001", "Kavita", "Deshmukh", "1988-03-21", "FEMALE", "+919876543900", 1700000000)
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "paschat_api_test.db")

        with TestClient(app) as client:
            yield client


def test_paschat_karma_api_full_workflow(client_with_db):
    """Verify complete end-to-end Paschat Karma workflow via REST API."""
    # 1. Login as Physician
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Initiate Paschat Karma Episode (Madhyama Shuddhi -> 10 Annakalas)
    init_payload = {
        "patient_id": "PAT-PASCHAT-API-01",
        "hospital_id": "aiia-delhi-central-001",
        "plan_id": "PLAN-PK-API-001",
        "procedure_type": "VIRECHANA",
        "shuddhi_grade": "MADHYAMA",
        "attending_physician_arn": "ARN-NCISM-2015-8832"
    }
    create_resp = client_with_db.post("/api/v1/paschat-karma/episodes", json=init_payload, headers=headers)
    assert create_resp.status_code == 201
    ep_data = create_resp.json()
    episode_id = ep_data["episode_id"]
    assert ep_data["total_annakalas"] == 10
    assert ep_data["total_days"] == 5
    assert len(ep_data["schedule"]) == 10

    # 3. Retrieve Episode Details
    get_resp = client_with_db.get(f"/api/v1/paschat-karma/episodes/{episode_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["episode_id"] == episode_id

    # 4. Retrieve Episodes by Patient
    list_resp = client_with_db.get("/api/v1/paschat-karma/patients/PAT-PASCHAT-API-01", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # 5. Log Annakala 1 (Peya)
    meal_payload = {
        "annakala_number": 1,
        "patient_appetite_observed": "ALPA_KSHUDHA",
        "digestion_tolerance_noted": "SUKHA_PAKA",
        "compliance_status": "CONSUMED_AS_PRESCRIBED",
        "clinical_notes": "Warm Peya consumed smoothly without discomfort.",
        "nurse_or_practitioner_id": "nurse-ayush-001"
    }
    meal_resp = client_with_db.post(f"/api/v1/paschat-karma/episodes/{episode_id}/meals", json=meal_payload, headers=headers)
    assert meal_resp.status_code == 201
    meal_data = meal_resp.json()
    assert meal_data["annakala_number"] == 1
    assert meal_data["prescribed_diet_form"] == "PEYA"

    # 6. List Meal Logs
    meals_get_resp = client_with_db.get(f"/api/v1/paschat-karma/episodes/{episode_id}/meals", headers=headers)
    assert meals_get_resp.status_code == 200
    assert len(meals_get_resp.json()) == 1

    # 7. Check Trajectory Analytics
    traj_resp = client_with_db.get(f"/api/v1/paschat-karma/episodes/{episode_id}/trajectory", headers=headers)
    assert traj_resp.status_code == 200
    traj_data = traj_resp.json()
    assert traj_data["logged_annakalas"] == 1
    assert traj_data["total_annakalas"] == 10
    assert traj_data["intolerance_events_count"] == 0
    assert len(traj_data["recommendations"]) >= 1

    # 8. Audit Parihara Adherence
    audit_payload = {
        "reported_violations": ["DIVASVAPNA_MAITHUNA"],
        "audited_by_staff_id": "nurse-ayush-001",
        "notes": "Patient rested during afternoon."
    }
    audit_resp = client_with_db.post(f"/api/v1/paschat-karma/episodes/{episode_id}/parihara-audit", json=audit_payload, headers=headers)
    assert audit_resp.status_code == 200
    audit_data = audit_resp.json()
    assert not audit_data["is_compliant"]
    assert len(audit_data["remedial_measures"]) >= 1

    # 9. Evaluate Rasayana Readiness (Expect False initially since not all Annakalas logged)
    readiness_resp = client_with_db.post(f"/api/v1/paschat-karma/episodes/{episode_id}/rasayana-readiness", headers=headers)
    assert readiness_resp.status_code == 200
    assert not readiness_resp.json()["is_ready_for_rasayana"]
