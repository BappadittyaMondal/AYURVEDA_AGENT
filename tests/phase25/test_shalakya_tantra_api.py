"""
Integration Tests for Shalakya Tantra, Netra Kriya Kalpa & ENT Micro-therapeutics API (Phase 25).
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
        test_db_path = Path(tmpdir) / "shalakya_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-SHALAKYA-API-01", "aiia-delhi-central-001", "Meenakshi", "Sundaram", "1988-03-21", "FEMALE", "+919876543003", 1700000000)
        )
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "shalakya_api_test.db")

        with TestClient(app) as client:
            yield client


def test_netra_rogas_catalog_endpoints(client_with_db):
    """Verify listing classical Netra Rogas and detail retrieval."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List all Netra Rogas
    resp = client_with_db.get("/api/v1/shalakya/netra-rogas", headers=headers)
    assert resp.status_code == 200
    rogas = resp.json()
    assert len(rogas) >= 20

    # 2. Filter by DRISHTI mandala
    resp_filtered = client_with_db.get("/api/v1/shalakya/netra-rogas?mandala=DRISHTI", headers=headers)
    assert resp_filtered.status_code == 200
    d_rogas = resp_filtered.json()
    assert len(d_rogas) >= 4
    assert any(r["roga_code"] == "NETRA-DRI-01" for r in d_rogas)

    # 3. Retrieve single detail
    resp_detail = client_with_db.get("/api/v1/shalakya/netra-rogas/NETRA-DRI-01", headers=headers)
    assert resp_detail.status_code == 200
    detail = resp_detail.json()
    assert detail["sanskrit_name"].startswith("तिमिर")
    assert "9D00" in detail["icd11_mapping"]

    # 4. 404 for invalid code
    resp_404 = client_with_db.get("/api/v1/shalakya/netra-rogas/NETRA-INVALID-99", headers=headers)
    assert resp_404.status_code == 404


def test_tarpana_kriya_kalpa_endpoints(client_with_db):
    """Verify logging Tarpana sessions and retrieving patient history."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": "PAT-SHALAKYA-API-01",
        "eye_side": "BILATERAL",
        "ghrita_used": "Mahatriphala Ghrita",
        "doshic_indication": "VATAJA",
        "clinical_indication": "Computer Vision Syndrome / Shushkakshipaka",
        "practitioner_arn": "AY-DL-2024-998811",
    }
    resp = client_with_db.post("/api/v1/shalakya/tarpana", json=payload, headers=headers)
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["session_id"].startswith("tarpana-")
    assert res_data["retention_matrakalas"] == 1000
    assert res_data["retention_duration_seconds"] == 200
    assert len(res_data["post_procedure_precautions"]) >= 4

    # Fetch patient history
    hist_resp = client_with_db.get("/api/v1/shalakya/tarpana/patient/PAT-SHALAKYA-API-01", headers=headers)
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 1
    assert history[0]["session_id"] == res_data["session_id"]


def test_ophthalmic_screening_emergency_firewall_endpoint(client_with_db):
    """Verify acute Adhimantha (glaucoma) crisis triggers emergency firewall via API."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    emergency_payload = {
        "patient_id": "PAT-SHALAKYA-API-01",
        "presenting_symptoms": ["Violent headache", "Steamy vision", "Vomiting", "Severe ocular pain"],
        "intraocular_pressure_mmhg": 48.0,
        "severe_ocular_pain": True,
        "hemicrania_headache": True,
        "halos_around_lights": True,
        "corneal_edema_steamy": True,
        "pupil_fixed_mid_dilated": True,
        "evaluator_arn": "AY-DL-2024-998811",
    }
    resp = client_with_db.post("/api/v1/shalakya/ophthalmic-screening", json=emergency_payload, headers=headers)
    assert resp.status_code == 200
    triage = resp.json()
    assert triage["triage_level"] == "CRITICAL_EMERGENCY"
    assert triage["adhimantha_glaucoma_firewall_triggered"] is True
    assert "TARPANA" in triage["contraindicated_kriya_kalpas"]
    assert "SEKA" in triage["contraindicated_kriya_kalpas"]
    assert triage["emergency_escalation_protocol"] is not None


def test_ent_procedures_and_perforation_firewall_endpoint(client_with_db):
    """Verify logging ENT procedures and HTTP 400 rejection for tympanic perforation."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Valid ENT Karna Purana
    valid_payload = {
        "patient_id": "PAT-SHALAKYA-API-01",
        "therapy_type": "KARNA_PURANA",
        "anatomical_site": "RIGHT_EAR",
        "medicated_oil_used": "Bilva Taila",
        "dosage_drops_or_ml": "10 drops",
        "eardrum_perforated": False,
        "observations": "Karnanada (tinnitus) with subjective high pitch whistling",
        "practitioner_arn": "AY-DL-2024-998811",
    }
    resp_valid = client_with_db.post("/api/v1/shalakya/ent-procedures", json=valid_payload, headers=headers)
    assert resp_valid.status_code == 201
    ent_data = resp_valid.json()
    assert ent_data["safety_cleared"] is True

    # 2. Blocked Karna Purana due to perforated eardrum -> 400 Bad Request
    invalid_payload = {
        "patient_id": "PAT-SHALAKYA-API-01",
        "therapy_type": "KARNA_PURANA",
        "anatomical_site": "LEFT_EAR",
        "medicated_oil_used": "Ksharatila Taila",
        "dosage_drops_or_ml": "10 drops",
        "eardrum_perforated": True,
        "observations": "Perforated tympanic membrane",
        "practitioner_arn": "AY-DL-2024-998811",
    }
    resp_invalid = client_with_db.post("/api/v1/shalakya/ent-procedures", json=invalid_payload, headers=headers)
    assert resp_invalid.status_code == 400
    assert "Perforated tympanic membrane" in resp_invalid.json()["detail"]

    # 3. Retrieve patient ENT history
    hist_resp = client_with_db.get("/api/v1/shalakya/ent-procedures/patient/PAT-SHALAKYA-API-01", headers=headers)
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 1
    assert history[0]["procedure_id"] == ent_data["procedure_id"]
