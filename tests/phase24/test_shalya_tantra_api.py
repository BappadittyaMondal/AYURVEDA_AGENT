"""
Integration Tests for Shalya Tantra, Marma Sharira, Agnikarma & Ksharasutra API (Phase 24).
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
        test_db_path = Path(tmpdir) / "shalya_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-SHALYA-API-01", "aiia-delhi-central-001", "Sanjay", "Mishra", "1983-09-02", "MALE", "+919876543002", 1700000000)
        )
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "shalya_api_test.db")

        with TestClient(app) as client:
            yield client


def test_marmas_listing_and_filtering_endpoints(client_with_db):
    """Verify listing all Marmas and filtering by anatomical region."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List all Marmas
    resp = client_with_db.get("/api/v1/shalya/marmas", headers=headers)
    assert resp.status_code == 200
    marmas = resp.json()
    assert len(marmas) >= 18

    # 2. Filter by KOSHTHA region
    resp_koshtha = client_with_db.get("/api/v1/shalya/marmas?region=KOSHTHA", headers=headers)
    assert resp_koshtha.status_code == 200
    k_list = resp_koshtha.json()
    assert len(k_list) >= 4
    assert any(m["marma_id"] == "MARMA-HRIDAYA" for m in k_list)


def test_marma_detail_and_404(client_with_db):
    """Verify single Marma retrieval and 404 response."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client_with_db.get("/api/v1/shalya/marmas/MARMA-BASTI", headers=headers)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["marma_id"] == "MARMA-BASTI"
    assert detail["marma_type"] == "SADYO_PRANAHARA"

    resp_404 = client_with_db.get("/api/v1/shalya/marmas/MARMA-NONEXISTENT", headers=headers)
    assert resp_404.status_code == 404


def test_marma_proximity_screening_endpoint(client_with_db):
    """Verify surgical incision screening against Sadyo-Pranahara Marma."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Close proximity to Nabhi (radius 4.0 cm, proposed 1.0 cm) -> CRITICAL_BLOCKED
    payload = {
        "patient_id": "PAT-SHALYA-API-01",
        "proposed_incision_site": "Periumbilical exploratory laparotomy",
        "anatomical_region": "KOSHTHA",
        "nearest_marma_id": "MARMA-NABHI",
        "distance_from_marma_cm": 1.0,
        "surgeon_arn": "AY-DL-2024-998811",
    }
    resp = client_with_db.post("/api/v1/shalya/marmas/screen-proximity", json=payload, headers=headers)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["is_safe_incision"] is False
    assert res_data["safety_tier"] == "CRITICAL_BLOCKED"
    assert res_data["shock_resuscitation_protocol"] is not None


def test_agnikarma_procedure_endpoint(client_with_db):
    """Verify logging an Agnikarma thermal cauterization procedure."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": "PAT-SHALYA-API-01",
        "anatomical_site": "Medial joint line of left knee / Janu Sandhigata Vata",
        "dahanopakarana": "PANCHADHATU_SHALAKA",
        "operating_temperature_c": 200.0,
        "contact_time_seconds": 1.0,
        "pattern": "BINDU",
        "clinical_indication": "Chronic degenerative osteoarthritis with sharp pain",
        "practitioner_arn": "AY-DL-2024-998811",
    }
    resp = client_with_db.post("/api/v1/shalya/agnikarma/sessions", json=payload, headers=headers)
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["burn_grade"] == "SAMYAK_DAGDHA"
    assert "Ghrita-Kumari" in res_data["post_care_dressing"]


def test_ksharasutra_episode_endpoint(client_with_db):
    """Verify logging Ksharasutra session and UCT calculation."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": "PAT-SHALYA-API-01",
        "fistula_type": "INTERSPHINCTERIC",
        "initial_track_length_cm": 4.0,
        "current_track_length_cm": 1.0,
        "sittings_count": 3,
        "total_days_elapsed": 21,
        "active_symptoms": [],
        "practitioner_arn": "AY-DL-2024-998811",
    }
    resp = client_with_db.post("/api/v1/shalya/ksharasutra/episodes", json=payload, headers=headers)
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["cut_length_cm"] == 3.0
    assert res_data["unit_cutting_time_days_per_cm"] == 7.0
    assert res_data["healing_status"] == "IN_PROGRESS"


def test_vrana_evaluation_endpoint(client_with_db):
    """Verify surgical wound evaluation and Shashti-Upakrama prescription."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": "PAT-SHALYA-API-01",
        "location": "Post-excisional sacral wound",
        "dimensions_cm": "3.0 x 2.0 x 0.5 cm",
        "is_foul_smelling": False,
        "has_purulent_discharge": False,
        "has_healthy_granulation": True,
        "edge_character": "SLOPING",
        "practitioner_arn": "AY-DL-2024-998811",
    }
    resp = client_with_db.post("/api/v1/shalya/vrana/evaluations", json=payload, headers=headers)
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["wound_stage"] == "RUHAMANA_VRANA"
    assert "Jatyadi Taila" in res_data["topical_formulation"]
