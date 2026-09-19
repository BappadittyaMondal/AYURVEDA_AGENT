"""
Integration Tests for Shalya Tantra Yantra-Shastra Microsurgical Instruments & Operative API (Phase 32).
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
    """Fixture providing TestClient backed by an isolated temporary database with seeded surgical patient."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "shalya_inst_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-SURG-API-01", "aiia-delhi-central-001", "Kailash", "Nath", "1983-04-20", "MALE", "+919876543016", 1700000000)
        )
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "shalya_inst_api_test.db")

        with TestClient(app) as client:
            yield client


def test_instruments_catalog_endpoints(client_with_db):
    """Verify listing instruments, filtering by type/category, and single lookup."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List all instruments
    resp = client_with_db.get("/api/v1/surgical/instruments", headers=headers)
    assert resp.status_code == 200
    all_inst = resp.json()
    assert len(all_inst) >= 12

    # 2. Filter by SHASTRA type
    resp_shastra = client_with_db.get("/api/v1/surgical/instruments?instrument_type=SHASTRA", headers=headers)
    assert resp_shastra.status_code == 200
    shastra_list = resp_shastra.json()
    assert len(shastra_list) >= 6
    assert any(s["instrument_code"] == "SHA-VRID-07" for s in shastra_list)

    # 3. Filter by SVASTIKA category
    resp_svastika = client_with_db.get("/api/v1/surgical/instruments?category=SVASTIKA", headers=headers)
    assert resp_svastika.status_code == 200
    svastika_list = resp_svastika.json()
    assert any(s["instrument_code"] == "YAN-SVA-01" for s in svastika_list)

    # 4. Lookup single instrument
    resp_one = client_with_db.get("/api/v1/surgical/instruments/SHA-VRID-07", headers=headers)
    assert resp_one.status_code == 200
    assert "वृद्धिपत्र" in resp_one.json()["sanskrit_name"]

    # 5. Non-existent returns 404
    resp_404 = client_with_db.get("/api/v1/surgical/instruments/INVALID-INSTRUMENT-99", headers=headers)
    assert resp_404.status_code == 404


def test_operative_procedure_endpoints(client_with_db):
    """Verify logging operative procedures, parasurgical firewalls, and patient history lookup."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Clean procedure
    clean_req = {
        "patient_id": "PAT-SURG-API-01",
        "operative_karma": "CHHEDANA",
        "surgical_instruments_used": ["SHA-VRID-07", "YAN-SAN-02"],
        "anesthesia_or_sangyaharana": "Local field block",
        "parasurgical_modality": "NONE",
        "operative_notes": "Excision of sebaceous cyst over scalp",
        "surgeon_arn": "ARN-NCISM-2015-8832"
    }
    resp1 = client_with_db.post("/api/v1/surgical/procedures", json=clean_req, headers=headers)
    assert resp1.status_code == 201
    res1 = resp1.json()
    assert res1["procedure_id"].startswith("op-")
    assert res1["safety_firewall_cleared"] is True
    assert len(res1["firewall_violations"]) == 0

    # 2. Kshara Karma with missing Amla neutralizer
    kshara_violation = {
        "patient_id": "PAT-SURG-API-01",
        "operative_karma": "LEKHANA",
        "surgical_instruments_used": ["SHA-MAND-08", "YAN-NAD-04"],
        "anesthesia_or_sangyaharana": "Local infiltration",
        "parasurgical_modality": "KSHARA_KARMA",
        "has_amla_neutralizer_ready": False,  # VIOLATION!
        "operative_notes": "Kshara application without acid wash on tray",
        "surgeon_arn": "ARN-NCISM-2015-8832"
    }
    resp2 = client_with_db.post("/api/v1/surgical/procedures", json=kshara_violation, headers=headers)
    assert resp2.status_code == 201
    res2 = resp2.json()
    assert res2["safety_firewall_cleared"] is False
    assert len(res2["firewall_violations"]) == 1
    assert "Amla neutralizing agent" in res2["firewall_violations"][0]

    # 3. Retrieve patient history
    hist_resp = client_with_db.get("/api/v1/surgical/procedures/patient/PAT-SURG-API-01", headers=headers)
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert len(hist) == 2


def test_yogya_assessment_endpoints(client_with_db):
    """Verify recording Yogya surgical simulation assessments and history lookup."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Yogya assessment
    req = {
        "practitioner_arn": "ARN-NCISM-2015-8832",
        "operative_karma_tested": "CHHEDANA",
        "simulation_model_used": "PUSHPAPHALA",
        "precision_score": 90.0,
        "tissue_handling_score": 85.0,
        "examiner_arn": "ARN-NCISM-1998-0421"
    }
    resp = client_with_db.post("/api/v1/surgical/yogya-assessments", json=req, headers=headers)
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["assessment_id"].startswith("yogya-")
    assert res_data["composite_score"] == 88.0
    assert res_data["overall_competency_certified"] is True
    assert "COMPETENCY CERTIFIED" in res_data["certification_verdict"]

    # 2. Retrieve practitioner history
    hist_resp = client_with_db.get("/api/v1/surgical/yogya-assessments/practitioner/ARN-NCISM-2015-8832", headers=headers)
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert len(hist) == 1
