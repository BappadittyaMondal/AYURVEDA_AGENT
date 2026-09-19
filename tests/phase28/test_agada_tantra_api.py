"""
Integration Tests for Agada Tantra, Visha Chikitsa & Toxicology API (Phase 28).
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
    """Fixture providing TestClient backed by an isolated temporary database with seeded toxic emergency patient."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "agada_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-TOX-API-01", "aiia-delhi-central-001", "Vikram", "Chauhan", "1990-07-18", "MALE", "+919876543009", 1700000000)
        )
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "agada_api_test.db")

        with TestClient(app) as client:
            yield client


def test_toxins_catalog_endpoints(client_with_db):
    """Verify listing toxins and retrieving single detail."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List all toxins
    resp = client_with_db.get("/api/v1/agada/toxins", headers=headers)
    assert resp.status_code == 200
    toxins = resp.json()
    assert len(toxins) >= 8

    # 2. Filter by JANGAMA category
    resp_jan = client_with_db.get("/api/v1/agada/toxins?category=JANGAMA", headers=headers)
    assert resp_jan.status_code == 200
    j_list = resp_jan.json()
    assert len(j_list) >= 4
    assert any(t["visha_code"] == "VISHA-JAN-01" for t in j_list)

    # 3. Retrieve single toxin detail
    resp_detail = client_with_db.get("/api/v1/agada/toxins/VISHA-STH-01", headers=headers)
    assert resp_detail.status_code == 200
    detail = resp_detail.json()
    assert "Vatsanabha" in detail["sanskrit_name"]

    # 4. 404 for invalid toxin
    resp_404 = client_with_db.get("/api/v1/agada/toxins/VISHA-INVALID-99", headers=headers)
    assert resp_404.status_code == 404


def test_envenomation_admission_endpoints(client_with_db):
    """Verify logging acute envenomation admission, ASV dosage, and patient history."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": "PAT-TOX-API-01",
        "suspected_visha_code": "VISHA-JAN-01",
        "envenomation_syndrome": "DARVIKARA_NEUROTOXIC",
        "bite_to_admission_minutes": 30,
        "twenty_minute_wbct_clotted": True,
        "neurotoxic_signs_present": True,
        "hemotoxic_signs_present": False,
        "practitioner_arn": "AY-DL-2024-998811",
    }
    resp = client_with_db.post("/api/v1/agada/envenomation-admissions", json=payload, headers=headers)
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["episode_id"].startswith("tox-")
    assert res_data["triage_level"] == "CRITICAL_TOXIC_EMERGENCY"
    assert res_data["asv_indicated_vials"] == 10
    assert "Anti-Snake Venom" in res_data["emergency_escalation_protocol"]

    # Fetch patient history
    hist_resp = client_with_db.get("/api/v1/agada/envenomation-admissions/patient/PAT-TOX-API-01", headers=headers)
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 1
    assert history[0]["episode_id"] == res_data["episode_id"]


def test_dushi_visha_assessment_endpoints(client_with_db):
    """Verify Dushi Visha assessment logging and history retrieval."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": "PAT-TOX-API-01",
        "suspected_toxin_source": "Chronic industrial solvent and heavy metal vapor exposure",
        "chronicity_months": 24,
        "reported_manifestations": ["Kitibha skin lesions", "Unexplained anemia", "Lethargy"],
        "aggravating_triggers": ["Cloudy monsoon season", "Cold wind"],
        "practitioner_arn": "AY-DL-2024-998811",
    }
    resp = client_with_db.post("/api/v1/agada/dushi-visha/assessments", json=payload, headers=headers)
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["log_id"].startswith("dushi-")
    assert res_data["dooshivishari_agada_prescribed"] is True

    # History retrieval
    hist_resp = client_with_db.get("/api/v1/agada/dushi-visha/assessments/patient/PAT-TOX-API-01", headers=headers)
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 1
    assert history[0]["log_id"] == res_data["log_id"]
