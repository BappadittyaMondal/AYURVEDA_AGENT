"""
Integration Tests for Marma Sharira, Traumatological Interventions & Marma Chikitsa API (Phase 31).
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
    """Fixture providing TestClient backed by an isolated temporary database with seeded trauma patient."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "marma_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-MARMA-API-01", "aiia-delhi-central-001", "Raghav", "Trivedi", "1994-06-18", "MALE", "+919876543014", 1700000000)
        )
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "marma_api_test.db")

        with TestClient(app) as client:
            yield client


def test_marma_catalog_endpoints(client_with_db):
    """Verify listing Marmas, filtering by region/prognosis, and single item lookup."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List all Marmas
    resp = client_with_db.get("/api/v1/marmas", headers=headers)
    assert resp.status_code == 200
    marmas = resp.json()
    assert len(marmas) >= 12

    # 2. Filter by region URDHVAJATRU
    resp_head = client_with_db.get("/api/v1/marmas?region=URDHVAJATRU", headers=headers)
    assert resp_head.status_code == 200
    head_list = resp_head.json()
    assert len(head_list) >= 4
    assert any(m["marma_code"] == "MARMA-STHAP-04" for m in head_list)

    # 3. Filter by parinama SADHYO_PRANAHARA
    resp_sadhyo = client_with_db.get("/api/v1/marmas?parinama=SADHYO_PRANAHARA", headers=headers)
    assert resp_sadhyo.status_code == 200
    sadhyo_list = resp_sadhyo.json()
    assert any(m["marma_code"] == "MARMA-HRID-01" for m in sadhyo_list)

    # 4. Single item lookup
    resp_one = client_with_db.get("/api/v1/marmas/MARMA-HRID-01", headers=headers)
    assert resp_one.status_code == 200
    assert "हृदय" in resp_one.json()["sanskrit_name"]

    # 5. Non-existent returns 404
    resp_404 = client_with_db.get("/api/v1/marmas/MARMA-INVALID-99", headers=headers)
    assert resp_404.status_code == 404


def test_trauma_admission_endpoints(client_with_db):
    """Verify trauma intake, Tri-Marma emergency resuscitation, and foreign body warning."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Critical Tri-Marma intake
    tri_req = {
        "patient_id": "PAT-MARMA-API-01",
        "injured_marma_code": "MARMA-HRID-01",
        "trauma_mechanism": "Penetrating dagger injury to anterior chest",
        "depth_penetration_mm": 40.0,
        "foreign_body_present": False,
        "practitioner_arn": "ARN-NCISM-2015-8832"
    }
    resp1 = client_with_db.post("/api/v1/marmas/trauma-admissions", json=tri_req, headers=headers)
    assert resp1.status_code == 201
    res1 = resp1.json()
    assert res1["log_id"].startswith("trauma-")
    assert res1["tri_marma_involved"] is True
    assert res1["triage_tier"] == "CODE_RED_TRI_MARMA_CRITICAL"
    assert "Hridaya-Avarana" in res1["emergency_resuscitation_protocol"]

    # 2. Vishalyaghna shrapnel intake with extraction warning
    vish_req = {
        "patient_id": "PAT-MARMA-API-01",
        "injured_marma_code": "MARMA-STHAP-04",
        "trauma_mechanism": "Penetrating metallic shard in forehead",
        "depth_penetration_mm": 15.0,
        "foreign_body_present": True,
        "practitioner_arn": "ARN-NCISM-2015-8832"
    }
    resp2 = client_with_db.post("/api/v1/marmas/trauma-admissions", json=vish_req, headers=headers)
    assert resp2.status_code == 201
    res2 = resp2.json()
    assert res2["triage_tier"] == "CODE_ORANGE_VISHALYAGHNA_SURGICAL"
    assert "DO NOT EXTRACT" in res2["surgical_extraction_warning"]

    # 3. Retrieve patient trauma history
    hist_resp = client_with_db.get("/api/v1/marmas/trauma-admissions/patient/PAT-MARMA-API-01", headers=headers)
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert len(hist) == 2


def test_chikitsa_session_endpoints(client_with_db):
    """Verify recording therapeutic Marma stimulation session and history retrieval."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Chikitsa session
    chik_req = {
        "patient_id": "PAT-MARMA-API-01",
        "targeted_marma_code": "MARMA-STHAP-04",
        "stimulation_modality": "ANGULI_PIDANA",
        "pressure_intensity_kg": 0.8,
        "cycles_count": 21,
        "clinical_objective": "Relief of severe tension headache and nervous exhaustion",
        "practitioner_arn": "ARN-NCISM-2015-8832"
    }
    resp = client_with_db.post("/api/v1/marmas/chikitsa-sessions", json=chik_req, headers=headers)
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["session_id"].startswith("marmachik-")
    assert "Pranic flow successfully stimulated" in res_data["immediate_response"]

    # 2. Retrieve patient Chikitsa history
    hist_resp = client_with_db.get("/api/v1/marmas/chikitsa-sessions/patient/PAT-MARMA-API-01", headers=headers)
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert len(hist) == 1
