"""Integration tests for Phase 33 Raktamokshana REST API endpoints."""
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
        test_db_path = Path(tmpdir) / "raktamokshana_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-RAKTA-API-01", "aiia-delhi-central-001", "Dharmendra", "Shukla", "1978-08-15", "MALE", "+919876543088", 1700000000)
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "raktamokshana_api_test.db")

        with TestClient(app) as client:
            yield client


def test_jalauka_species_endpoints(client_with_db):
    """Verify retrieving leech catalog with NIRVISHA / SAVISHA classification filters."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Retrieve all species
    resp = client_with_db.get("/api/v1/raktamokshana/jalauka-species", headers=headers)
    assert resp.status_code == 200
    species_list = resp.json()
    assert len(species_list) == 12

    # 2. Filter NIRVISHA only
    resp_nir = client_with_db.get("/api/v1/raktamokshana/jalauka-species?species_type=NIRVISHA", headers=headers)
    assert resp_nir.status_code == 200
    nir_list = resp_nir.json()
    assert len(nir_list) == 6
    assert all(s["species_type"] == "NIRVISHA" for s in nir_list)

    # 3. Filter SAVISHA only
    resp_sav = client_with_db.get("/api/v1/raktamokshana/jalauka-species?species_type=SAVISHA", headers=headers)
    assert resp_sav.status_code == 200
    sav_list = resp_sav.json()
    assert len(sav_list) == 6
    assert all(s["species_type"] == "SAVISHA" for s in sav_list)


def test_siravedha_veins_matrix_endpoints(client_with_db):
    """Verify vein matrix retrieval and Avadhya / quadrant filtering."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Retrieve all veins
    resp = client_with_db.get("/api/v1/raktamokshana/siravedha-veins", headers=headers)
    assert resp.status_code == 200
    veins = resp.json()
    assert len(veins) >= 15

    # 2. Filter only Avadhya Siras
    resp_avadhya = client_with_db.get("/api/v1/raktamokshana/siravedha-veins?only_avadhya=true", headers=headers)
    assert resp_avadhya.status_code == 200
    avadhya_list = resp_avadhya.json()
    assert len(avadhya_list) >= 8
    assert all(v["is_avadhya"] is True for v in avadhya_list)

    # 3. Filter by Quadrant
    resp_shirah = client_with_db.get("/api/v1/raktamokshana/siravedha-veins?quadrant=SHIRAH", headers=headers)
    assert resp_shirah.status_code == 200
    shirah_list = resp_shirah.json()
    assert any(v["vein_code"] == "V-SHIROROGA-01" for v in shirah_list)


def test_safety_firewall_evaluation_api(client_with_db):
    """Verify pre-procedure safety firewall auditing via API."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Safe cleared request
    safe_payload = {
        "patient_id": "PAT-RAKTA-API-01",
        "hospital_id": "aiia-delhi-central-001",
        "modality": "JALAUKAVACHARANA",
        "rogi_bala": "MADHYAMA",
        "patient_age": 42,
        "patient_weight_kg": 65.0,
        "baseline_hemoglobin_g_dl": 12.8,
        "platelet_count": 220000,
        "inr": 1.05,
        "systolic_bp": 120,
        "diastolic_bp": 80,
        "species_id": "JAL-NIR-KAPILA",
        "proposed_volume_ml": 25.0,
        "current_season": "SHARAD"
    }
    resp_safe = client_with_db.post("/api/v1/raktamokshana/safety-evaluation", json=safe_payload, headers=headers)
    assert resp_safe.status_code == 200
    res_safe = resp_safe.json()
    assert res_safe["cleared"] is True
    assert res_safe["firewall_status"] == "CLEARED"
    assert res_safe["max_permissible_volume_ml"] > 0

    # 2. Avadhya Sira violation
    unsafe_vein_payload = {
        "patient_id": "PAT-RAKTA-API-01",
        "hospital_id": "aiia-delhi-central-001",
        "modality": "SIRAVEDHA",
        "rogi_bala": "UTTAMA",
        "patient_age": 30,
        "patient_weight_kg": 72.0,
        "baseline_hemoglobin_g_dl": 14.5,
        "vein_code": "AV-GREEVA-MATRIKA-01",  # Strictly Avadhya
        "proposed_volume_ml": 100.0
    }
    resp_unsafe = client_with_db.post("/api/v1/raktamokshana/safety-evaluation", json=unsafe_vein_payload, headers=headers)
    assert resp_unsafe.status_code == 200
    res_unsafe = resp_unsafe.json()
    assert res_unsafe["cleared"] is False
    assert res_unsafe["firewall_status"] == "AVADHYA_SIRA_VIOLATION_FATAL_RISK"


def test_procedure_logging_and_patient_history_api(client_with_db):
    """Verify logging procedure, firewall breach rejection (400), and history retrieval."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Valid compliant procedure
    valid_proc = {
        "patient_id": "PAT-RAKTA-API-01",
        "hospital_id": "aiia-delhi-central-001",
        "modality": "JALAUKAVACHARANA",
        "target_anatomical_site": "Left medial malleolus indurated ulcer",
        "species_id": "JAL-NIR-PINGALA",
        "jalauka_count": 2,
        "evacuated_volume_ml": 20.0,
        "pre_procedure_hb": 13.5,
        "blood_dosha_vitiation": "PAITTIKA",
        "hemostasis_method": "SANDHANA",
        "complications_observed": [],
        "practitioner_arn": "ARN-NCISM-2015-8832"
    }
    resp_proc = client_with_db.post("/api/v1/raktamokshana/procedure-logs", json=valid_proc, headers=headers)
    assert resp_proc.status_code == 201
    res_proc = resp_proc.json()
    assert res_proc["procedure_id"].startswith("PROC-RAKTA-")
    assert res_proc["safety_firewall_cleared"] is True

    # 2. Firewall breach attempt (severe anemia Hb 6.0 g/dL)
    breach_proc = {
        "patient_id": "PAT-RAKTA-API-01",
        "hospital_id": "aiia-delhi-central-001",
        "modality": "JALAUKAVACHARANA",
        "target_anatomical_site": "Left shin",
        "species_id": "JAL-NIR-KAPILA",
        "jalauka_count": 1,
        "evacuated_volume_ml": 15.0,
        "pre_procedure_hb": 6.0,  # Below 8.0 g/dL absolute firewall!
        "blood_dosha_vitiation": "PAITTIKA",
        "hemostasis_method": "SANDHANA",
        "complications_observed": [],
        "practitioner_arn": "ARN-NCISM-2015-8832"
    }
    resp_breach = client_with_db.post("/api/v1/raktamokshana/procedure-logs", json=breach_proc, headers=headers)
    assert resp_breach.status_code == 400
    assert "CODE_RED_SEVERE_ANEMIA" in resp_breach.json()["detail"]

    # 3. Retrieve patient history
    resp_hist = client_with_db.get("/api/v1/raktamokshana/procedure-logs/PAT-RAKTA-API-01", headers=headers)
    assert resp_hist.status_code == 200
    hist = resp_hist.json()
    assert len(hist) == 1
    assert hist[0]["procedure_id"] == res_proc["procedure_id"]
