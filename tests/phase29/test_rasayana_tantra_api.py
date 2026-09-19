"""
Integration Tests for Rasayana Tantra, Jara Chikitsa & Longevity Medicine API (Phase 29).
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
        test_db_path = Path(tmpdir) / "rasayana_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-RAS-API-01", "aiia-delhi-central-001", "Dharmendra", "Sharma", "1972-03-25", "MALE", "+919876543010", 1700000000)
        )
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "rasayana_api_test.db")

        with TestClient(app) as client:
            yield client


def test_rasayana_protocols_endpoints(client_with_db):
    """Verify listing protocols, filtering by type/mode, and single item lookup."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List all protocols
    resp = client_with_db.get("/api/v1/rasayana/protocols", headers=headers)
    assert resp.status_code == 200
    all_protos = resp.json()
    assert len(all_protos) >= 8

    # 2. Filter by MEDHYA type
    resp_medhya = client_with_db.get("/api/v1/rasayana/protocols?rasayana_type=MEDHYA", headers=headers)
    assert resp_medhya.status_code == 200
    medhya_list = resp_medhya.json()
    assert len(medhya_list) >= 1
    assert medhya_list[0]["protocol_id"] == "RAS-MEDHYA-06"

    # 3. Filter by KUTI_PRAVESHIKA mode
    resp_kuti = client_with_db.get("/api/v1/rasayana/protocols?mode=KUTI_PRAVESHIKA", headers=headers)
    assert resp_kuti.status_code == 200
    kuti_list = resp_kuti.json()
    assert len(kuti_list) >= 1
    assert kuti_list[0]["protocol_id"] == "RAS-KUTI-CHYAVAN-07"

    # 4. Single protocol lookup
    resp_one = client_with_db.get("/api/v1/rasayana/protocols/RAS-CHYAVAN-01", headers=headers)
    assert resp_one.status_code == 200
    assert "Chyavanaprasha" in resp_one.json()["sanskrit_name"]

    # 5. Non-existent protocol returns 404
    resp_404 = client_with_db.get("/api/v1/rasayana/protocols/INVALID-PROTO-99", headers=headers)
    assert resp_404.status_code == 404


def test_ojas_evaluation_endpoints(client_with_db):
    """Verify Ojas evaluation calculus, Pravara/Avara statuses, and patient history retrieval."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Robust health (Pravara Ojas)
    pravara_req = {
        "patient_id": "PAT-RAS-API-01",
        "chronological_age": 45,
        "grip_strength_kg": 46.0,
        "vital_capacity_liters": 4.2,
        "joint_mobility_score": 9.0,
        "skin_luster_score": 9.0,
        "cognitive_memory_score": 9.0,
        "visramsa_symptoms": [],
        "vyapat_symptoms": [],
        "kshaya_symptoms": [],
        "evaluator_arn": "ARN-NCISM-2015-8832"
    }
    resp1 = client_with_db.post("/api/v1/rasayana/ojas-evaluation", json=pravara_req, headers=headers)
    assert resp1.status_code == 201
    res1_data = resp1.json()
    assert res1_data["evaluation_id"].startswith("ojas-")
    assert res1_data["ojas_status"] == "PRAVARA_OJAS"
    assert res1_data["ojas_score"] == 100.0
    assert res1_data["biological_age"] <= 45.0
    assert "Twak" in res1_data["decadal_attribute_decay"]
    assert len(res1_data["lifestyle_achara_rasayana"]) >= 4

    # 2. Severe depletion (Avara Ojas & Brahma Rasayana)
    avara_req = {
        "patient_id": "PAT-RAS-API-01",
        "chronological_age": 72,
        "grip_strength_kg": 15.0,
        "vital_capacity_liters": 1.5,
        "joint_mobility_score": 3.0,
        "skin_luster_score": 3.0,
        "cognitive_memory_score": 6.0,
        "visramsa_symptoms": ["Sandhi-Vishlesha", "Gatra-Sadana"],
        "vyapat_symptoms": ["Stambha", "Guru-Gatrata"],
        "kshaya_symptoms": ["Murchha", "Mamsa-Kshaya", "Dhatu-Shosha"],
        "evaluator_arn": "ARN-NCISM-2015-8832"
    }
    resp2 = client_with_db.post("/api/v1/rasayana/ojas-evaluation", json=avara_req, headers=headers)
    assert resp2.status_code == 201
    res2_data = resp2.json()
    assert res2_data["ojas_status"] == "AVARA_OJAS"
    assert res2_data["ojas_score"] < 50.0
    assert res2_data["prescribed_rasayana_id"] == "RAS-BRAHMA-02"
    assert "Brahma Rasayana" in res2_data["recommended_rasayana_formulation"]
    assert "Vikrama" in res2_data["decadal_attribute_decay"]

    # 3. Retrieve patient history
    hist_resp = client_with_db.get("/api/v1/rasayana/ojas-evaluation/patient/PAT-RAS-API-01", headers=headers)
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert len(hist) == 2


def test_kuti_praveshika_admission_endpoints(client_with_db):
    """Verify Kuti Praveshika admission screening, firewall enforcement, and history lookup."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Eligible Admission
    clear_req = {
        "patient_id": "PAT-RAS-API-01",
        "chronological_age": 52,
        "has_active_acute_infection": False,
        "blood_pressure_systolic": 126,
        "blood_pressure_diastolic": 82,
        "has_severe_cardiac_or_psychiatric_instability": False,
        "pre_shodhana_completed": True,
        "planned_duration_days": 30,
        "rasayana_formulation": "Chyavanaprasha intensive retreat compound",
        "practitioner_arn": "ARN-NCISM-2015-8832"
    }
    resp_clear = client_with_db.post("/api/v1/rasayana/kuti-praveshika/admissions", json=clear_req, headers=headers)
    assert resp_clear.status_code == 201
    clear_data = resp_clear.json()
    assert clear_data["episode_id"].startswith("kuti-")
    assert clear_data["eligibility_cleared"] is True
    assert len(clear_data["contraindication_flags"]) == 0
    assert any("Trigarbha" in g for g in clear_data["kuti_design_guidelines"])

    # 2. Blocked Admission (Missing pre-Shodhana + Stage-2 HTN)
    blocked_req = {
        "patient_id": "PAT-RAS-API-01",
        "chronological_age": 52,
        "has_active_acute_infection": False,
        "blood_pressure_systolic": 168,
        "blood_pressure_diastolic": 102,
        "has_severe_cardiac_or_psychiatric_instability": False,
        "pre_shodhana_completed": False,  # Violation!
        "planned_duration_days": 21,
        "rasayana_formulation": "Brahma Rasayana",
        "practitioner_arn": "ARN-NCISM-2015-8832"
    }
    resp_blocked = client_with_db.post("/api/v1/rasayana/kuti-praveshika/admissions", json=blocked_req, headers=headers)
    assert resp_blocked.status_code == 201
    blocked_data = resp_blocked.json()
    assert blocked_data["eligibility_cleared"] is False
    assert len(blocked_data["contraindication_flags"]) == 2
    flag_str = " ".join(blocked_data["contraindication_flags"])
    assert "Prior Panchakarma bio-cleansing" in flag_str
    assert "Stage-2 Hypertension" in flag_str

    # 3. Retrieve patient Kuti episodes
    kuti_hist_resp = client_with_db.get("/api/v1/rasayana/kuti-praveshika/patient/PAT-RAS-API-01", headers=headers)
    assert kuti_hist_resp.status_code == 200
    kuti_hist = kuti_hist_resp.json()
    assert len(kuti_hist) == 2
