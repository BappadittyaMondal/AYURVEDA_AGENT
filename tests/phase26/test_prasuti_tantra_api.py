"""
Integration Tests for Prasuti Tantra, Stri Roga & Garbhini Paricharya API (Phase 26).
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
        test_db_path = Path(tmpdir) / "prasuti_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-PRASUTI-API-01", "aiia-delhi-central-001", "Ananya", "Choudhury", "1996-11-25", "FEMALE", "+919876543005", 1700000000)
        )
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "prasuti_api_test.db")

        with TestClient(app) as client:
            yield client


def test_fertility_readiness_endpoint(client_with_db):
    """Verify Garbha Sambhava Samagri 4-factor fertility evaluation endpoint."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": "PAT-PRASUTI-API-01",
        "ritu_score": 85.0,
        "kshetra_score": 80.0,
        "ambu_score": 75.0,
        "beeja_score": 88.0,
        "evaluator_arn": "AY-DL-2024-998811",
        "clinical_notes": "Preconception assessment for 28-year-old nulligravida",
    }
    resp = client_with_db.post("/api/v1/prasuti/fertility-readiness", json=payload, headers=headers)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["composite_readiness_score"] == 82.0
    assert res_data["readiness_tier"] == "EXCELLENT"
    assert len(res_data["preconception_recommendations"]) >= 1


def test_garbhini_regimen_catalog_endpoints(client_with_db):
    """Verify listing all 9 months regimens and single month retrieval."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List all 9 months
    resp = client_with_db.get("/api/v1/prasuti/garbhini-regimen", headers=headers)
    assert resp.status_code == 200
    regimens = resp.json()
    assert len(regimens) == 9

    # 2. Get Month 4 (Dauhrida)
    resp_m4 = client_with_db.get("/api/v1/prasuti/garbhini-regimen/4", headers=headers)
    assert resp_m4.status_code == 200
    m4 = resp_m4.json()
    assert m4["month_number"] == 4
    assert "Navanita" in m4["dietary_regimen"]

    # 3. Invalid month (e.g. 10 -> 400 Bad Request)
    resp_bad = client_with_db.get("/api/v1/prasuti/garbhini-regimen/10", headers=headers)
    assert resp_bad.status_code == 400


def test_antenatal_consultation_endpoints(client_with_db):
    """Verify logging antenatal examination, Dauhrida fulfillment, and emergency triage firewall."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Normal antenatal consultation
    normal_payload = {
        "patient_id": "PAT-PRASUTI-API-01",
        "gestational_age_weeks": 20.0,
        "blood_pressure_systolic": 118,
        "blood_pressure_diastolic": 76,
        "fundal_height_cm": 20.0,
        "fetal_heart_rate_bpm": 144,
        "weight_kg": 60.0,
        "edema_present": False,
        "vaginal_bleeding_present": False,
        "dauhrida_desires": ["Warm vegetable soup", "Pomegranate juice"],
        "practitioner_arn": "AY-DL-2024-998811",
    }
    resp = client_with_db.post("/api/v1/prasuti/antenatal-consultations", json=normal_payload, headers=headers)
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["consultation_id"].startswith("anc-")
    assert res_data["gestational_month"] == 5
    assert res_data["obstetric_triage_level"] == "NORMAL"

    # 2. Emergency antenatal consultation (Severe Hemorrhage)
    emergency_payload = {
        "patient_id": "PAT-PRASUTI-API-01",
        "gestational_age_weeks": 30.0,
        "blood_pressure_systolic": 125,
        "blood_pressure_diastolic": 82,
        "fundal_height_cm": 29.0,
        "fetal_heart_rate_bpm": 136,
        "weight_kg": 67.0,
        "edema_present": False,
        "vaginal_bleeding_present": True,  # Critical emergency!
        "practitioner_arn": "AY-DL-2024-998811",
    }
    resp_em = client_with_db.post("/api/v1/prasuti/antenatal-consultations", json=emergency_payload, headers=headers)
    assert resp_em.status_code == 201
    em_data = resp_em.json()
    assert em_data["obstetric_triage_level"] == "CRITICAL_OBSTETRIC_EMERGENCY"
    assert em_data["emergency_escalation_notes"] is not None

    # 3. Fetch patient history
    hist_resp = client_with_db.get("/api/v1/prasuti/antenatal-consultations/patient/PAT-PRASUTI-API-01", headers=headers)
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 2


def test_yoni_vyapad_endpoints(client_with_db):
    """Verify Yoni Vyapad catalog, detail, assessment logging, and patient history."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List all 20 Yoni Vyapads
    resp = client_with_db.get("/api/v1/prasuti/yoni-vyapads", headers=headers)
    assert resp.status_code == 200
    vyapads = resp.json()
    assert len(vyapads) == 20

    # 2. Filter by PITTAJA doshic class
    resp_pit = client_with_db.get("/api/v1/prasuti/yoni-vyapads?doshic_class=PITTAJA", headers=headers)
    assert resp_pit.status_code == 200
    p_list = resp_pit.json()
    assert len(p_list) == 5
    assert any(v["vyapad_code"] == "YONI-PIT-02" for v in p_list)

    # 3. Retrieve detail for Udavartini
    resp_detail = client_with_db.get("/api/v1/prasuti/yoni-vyapads/YONI-VAT-02", headers=headers)
    assert resp_detail.status_code == 200
    detail = resp_detail.json()
    assert "Udavartini" in detail["sanskrit_name"]

    # 4. 404 for nonexistent code
    resp_404 = client_with_db.get("/api/v1/prasuti/yoni-vyapads/YONI-NONEXISTENT", headers=headers)
    assert resp_404.status_code == 404

    # 5. Log Yoni Vyapad assessment
    assess_payload = {
        "patient_id": "PAT-PRASUTI-API-01",
        "vyapad_code": "YONI-PIT-02",
        "reported_symptoms": ["Excessive heavy menstrual bleeding", "Clots and fatigue"],
        "pelvic_examination_findings": "Bleeding through external os, bulky uterus, no adnexal mass",
        "practitioner_arn": "AY-DL-2024-998811",
    }
    resp_assess = client_with_db.post("/api/v1/prasuti/yoni-vyapad/assessments", json=assess_payload, headers=headers)
    assert resp_assess.status_code == 201
    assess_data = resp_assess.json()
    assert assess_data["assessment_id"].startswith("yoni-")
    assert "Pushyanuga Churna" in "".join(assess_data["oral_formulations"])

    # 6. Retrieve patient assessment history
    hist_resp = client_with_db.get("/api/v1/prasuti/yoni-vyapad/assessments/patient/PAT-PRASUTI-API-01", headers=headers)
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 1
    assert history[0]["assessment_id"] == assess_data["assessment_id"]
