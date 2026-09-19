"""
Integration Tests for Vajikarana Tantra, Shukra Dushti & Reproductive Eugenics API (Phase 30).
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
    """Fixture providing TestClient backed by an isolated temporary database with seeded andrology patient."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "vajikarana_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-VAJI-API-01", "aiia-delhi-central-001", "Siddharth", "Mishra", "1989-11-20", "MALE", "+919876543012", 1700000000)
        )
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "vajikarana_api_test.db")

        with TestClient(app) as client:
            yield client


def test_dushti_catalog_endpoints(client_with_db):
    """Verify listing classical Shukra Dushtis and retrieving detail by code."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List all 8 Dushtis
    resp = client_with_db.get("/api/v1/vajikarana/dushti-registry", headers=headers)
    assert resp.status_code == 200
    dushtis = resp.json()
    assert len(dushtis) == 8

    # 2. Get single Dushti detail
    resp_one = client_with_db.get("/api/v1/vajikarana/dushti-registry/DUSHTI-VAT-01", headers=headers)
    assert resp_one.status_code == 200
    detail = resp_one.json()
    assert "वातज" in detail["sanskrit_name"]
    assert "Asthenozoospermia" in detail["who_semen_correlate"]

    # 3. 404 on invalid code
    resp_404 = client_with_db.get("/api/v1/vajikarana/dushti-registry/DUSHTI-INVALID-99", headers=headers)
    assert resp_404.status_code == 404


def test_semen_analysis_endpoints(client_with_db):
    """Verify WHO semen analysis evaluation, Shuddha Shukra, and patient history retrieval."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Normative sample (Shuddha Shukra)
    req1 = {
        "patient_id": "PAT-VAJI-API-01",
        "volume_ml": 3.0,
        "ph_level": 7.5,
        "liquefaction_time_min": 25,
        "viscosity_grade": "NORMAL",
        "sperm_concentration_million_ml": 55.0,
        "total_motility_percent": 60.0,
        "progressive_motility_percent": 48.0,
        "normal_morphology_percent": 6.5,
        "vitality_percent": 75.0,
        "pus_cells_per_hpf": 1,
        "erythrocytes_present": False,
        "practitioner_arn": "ARN-NCISM-2015-8832"
    }
    resp1 = client_with_db.post("/api/v1/vajikarana/semen-analysis", json=req1, headers=headers)
    assert resp1.status_code == 201
    res1_data = resp1.json()
    assert res1_data["analysis_id"].startswith("sem-")
    assert res1_data["primary_shukra_dushti"] == "SHUDDHA_SHUKRA"
    assert res1_data["shukra_shuddhi_score"] >= 90.0

    # 2. Leukocytospermic sample (Puti-Puya)
    req2 = {
        "patient_id": "PAT-VAJI-API-01",
        "volume_ml": 2.0,
        "ph_level": 8.1,
        "liquefaction_time_min": 35,
        "viscosity_grade": "NORMAL",
        "sperm_concentration_million_ml": 28.0,
        "total_motility_percent": 30.0,
        "progressive_motility_percent": 20.0,
        "normal_morphology_percent": 4.0,
        "vitality_percent": 52.0,
        "pus_cells_per_hpf": 15,
        "erythrocytes_present": False,
        "practitioner_arn": "ARN-NCISM-2015-8832"
    }
    resp2 = client_with_db.post("/api/v1/vajikarana/semen-analysis", json=req2, headers=headers)
    assert resp2.status_code == 201
    res2_data = resp2.json()
    assert res2_data["primary_shukra_dushti"] == "PUTI_PUYA"

    # 3. Retrieve patient history
    hist_resp = client_with_db.get("/api/v1/vajikarana/semen-analysis/patient/PAT-VAJI-API-01", headers=headers)
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert len(hist) == 2


def test_vajikarana_prescription_endpoints(client_with_db):
    """Verify Vajikarana prescription issuance, safety firewall gating, and history retrieval."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Cleared prescription
    rx_clear = {
        "patient_id": "PAT-VAJI-API-01",
        "klaibya_type": "JARASAMBHAVA",
        "target_action_class": "SHUKRA_JANANA_PRAVARTAKA",
        "pre_shodhana_completed": True,
        "has_active_ama": False,
        "partner_conception_intent": True,
        "practitioner_arn": "ARN-NCISM-2015-8832"
    }
    resp_clear = client_with_db.post("/api/v1/vajikarana/prescriptions", json=rx_clear, headers=headers)
    assert resp_clear.status_code == 201
    clear_data = resp_clear.json()
    assert clear_data["protocol_id"].startswith("vaji-")
    assert clear_data["safety_firewall_cleared"] is True
    assert len(clear_data["contraindication_warnings"]) == 0
    assert any("Vanari Kalpa" in f for f in clear_data["prescribed_classical_formulations"])

    # 2. Blocked prescription (Missing pre-Shodhana)
    rx_blocked = {
        "patient_id": "PAT-VAJI-API-01",
        "klaibya_type": "SHUKRAKSHAYAJA",
        "target_action_class": "SHUKRA_JANANA",
        "pre_shodhana_completed": False,  # Missing!
        "has_active_ama": True,           # Active Ama!
        "partner_conception_intent": True,
        "practitioner_arn": "ARN-NCISM-2015-8832"
    }
    resp_blocked = client_with_db.post("/api/v1/vajikarana/prescriptions", json=rx_blocked, headers=headers)
    assert resp_blocked.status_code == 201
    blocked_data = resp_blocked.json()
    assert blocked_data["safety_firewall_cleared"] is False
    assert len(blocked_data["contraindication_warnings"]) == 2

    # 3. Retrieve patient prescription history
    rx_hist_resp = client_with_db.get("/api/v1/vajikarana/prescriptions/patient/PAT-VAJI-API-01", headers=headers)
    assert rx_hist_resp.status_code == 200
    rx_hist = rx_hist_resp.json()
    assert len(rx_hist) == 2
