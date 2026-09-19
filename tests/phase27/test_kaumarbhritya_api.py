"""
Integration Tests for Kaumarbhritya, Bala Roga & Suvarnaprashana API (Phase 27).
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
    """Fixture providing TestClient backed by an isolated temporary database with seeded pediatric patient."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "kaumarbhritya_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-PEDIATRIC-API-01", "aiia-delhi-central-001", "Rohan", "Verma", "2025-01-10", "MALE", "+919876543007", 1700000000)
        )
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "kaumarbhritya_api_test.db")

        with TestClient(app) as client:
            yield client


def test_pediatric_milestones_endpoint(client_with_db):
    """Verify developmental milestones catalog listing."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client_with_db.get("/api/v1/kaumarbhritya/milestones", headers=headers)
    assert resp.status_code == 200
    milestones = resp.json()
    assert len(milestones) >= 7
    assert any(m["classical_samskara"] == "JATAKARMA" for m in milestones)
    assert any(m["classical_samskara"] == "ANNAPRASHANA" for m in milestones)


def test_posology_calculation_endpoint(client_with_db):
    """Verify dual posology calculation and toxicological firewall rejection."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Valid posology calculation for 8-month infant
    valid_payload = {
        "patient_id": "PAT-PEDIATRIC-API-01",
        "age_months": 8,
        "weight_kg": 8.2,
        "adult_dose_mg": 500.0,
        "formulation_name": "Arvindasava",
        "contains_heavy_metals_or_schedule_e1": False,
        "evaluator_arn": "AY-DL-2024-998811",
    }
    resp = client_with_db.post("/api/v1/kaumarbhritya/posology/calculate", json=valid_payload, headers=headers)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["dietary_stage"] == "KSHEERADA"
    assert res_data["recommended_pediatric_dose_mg"] > 0
    assert res_data["safety_firewall_cleared"] is True

    # 2. Rejection of heavy metals in infant -> 400 Bad Request
    toxic_payload = {
        "patient_id": "PAT-PEDIATRIC-API-01",
        "age_months": 8,
        "weight_kg": 8.2,
        "adult_dose_mg": 500.0,
        "formulation_name": "Tamra Rasayana",
        "contains_heavy_metals_or_schedule_e1": True,
        "evaluator_arn": "AY-DL-2024-998811",
    }
    resp_toxic = client_with_db.post("/api/v1/kaumarbhritya/posology/calculate", json=toxic_payload, headers=headers)
    assert resp_toxic.status_code == 400
    assert "Schedule E-1 poisons and heavy metal Bhasmas are strictly contraindicated" in resp_toxic.json()["detail"]


def test_pediatric_consultation_endpoints(client_with_db):
    """Verify logging pediatric consultation, Bala Roga diagnosis, and history retrieval."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": "PAT-PEDIATRIC-API-01",
        "age_months": 15,
        "weight_kg": 9.0,
        "bala_roga_diagnosis": "PHAKKA_KSHIRAJA",
        "presenting_symptoms": ["Delayed standing", "Muscle wasting", "Dry skin"],
        "adult_reference_dose_mg": 500.0,
        "prescribed_formulation": "Kalyanaka Ghrita with Rajanyadi Churna",
        "practitioner_arn": "AY-DL-2024-998811",
    }
    resp = client_with_db.post("/api/v1/kaumarbhritya/consultations", json=payload, headers=headers)
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["consultation_id"].startswith("ped-")
    assert res_data["dietary_stage"] == "KSHEERANNADA"
    assert "5B5B" in res_data["icd11_mapping"]

    # History retrieval
    hist_resp = client_with_db.get("/api/v1/kaumarbhritya/consultations/patient/PAT-PEDIATRIC-API-01", headers=headers)
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 1
    assert history[0]["consultation_id"] == res_data["consultation_id"]


def test_suvarnaprashana_endpoints(client_with_db):
    """Verify Suvarnaprashana administration, Viruddha Ahara rejection, and history retrieval."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Valid administration (2:1 Madhu to Ghrita)
    valid_payload = {
        "patient_id": "PAT-PEDIATRIC-API-01",
        "age_months": 14,
        "pushya_nakshatra_date": "2026-10-18",
        "suvarna_bhasma_mg": 2.5,
        "madhu_ghrita_ratio": "2:1 Madhu to Ghrita",
        "medhya_herbs": ["Brahmi", "Vacha", "Shankhapushpi"],
        "practitioner_arn": "AY-DL-2024-998811",
    }
    resp = client_with_db.post("/api/v1/kaumarbhritya/suvarnaprashana", json=valid_payload, headers=headers)
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["dose_id"].startswith("suvarna-")
    assert res_data["suvarna_bhasma_mg"] == 2.5
    assert len(res_data["immunomodulation_outcomes"]) >= 3

    # 2. Blocked 1:1 Viruddha Ahara ratio -> 400 Bad Request
    invalid_payload = {
        "patient_id": "PAT-PEDIATRIC-API-01",
        "age_months": 14,
        "pushya_nakshatra_date": "2026-10-18",
        "suvarna_bhasma_mg": 2.5,
        "madhu_ghrita_ratio": "1:1 Equal Honey and Ghee",
        "practitioner_arn": "AY-DL-2024-998811",
    }
    resp_inv = client_with_db.post("/api/v1/kaumarbhritya/suvarnaprashana", json=invalid_payload, headers=headers)
    assert resp_inv.status_code == 400
    assert "constitutes toxic Viruddha Ahara" in resp_inv.json()["detail"]

    # 3. Retrieve patient history
    hist_resp = client_with_db.get("/api/v1/kaumarbhritya/suvarnaprashana/patient/PAT-PEDIATRIC-API-01", headers=headers)
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 1
    assert history[0]["dose_id"] == res_data["dose_id"]
