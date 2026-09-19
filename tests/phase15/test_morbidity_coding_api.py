"""
Phase 15: Integration Test Suite for Morbidity Dual-Coding & ICD-11 Crosswalk API.
"""

import tempfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from config.settings import get_settings
from core.database import init_database
from main import app


@pytest.fixture
def client_with_db(monkeypatch):
    """Fixture providing TestClient backed by an isolated temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "morbidity_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "morbidity_api_test.db")

        with TestClient(app) as client:
            yield client


def test_registry_search_and_detail_endpoints(client_with_db):
    """Verify listing, searching, and detail retrieval of dual-coded entries."""
    # 1. Login
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. List all registry entries
    resp = client_with_db.get("/api/v1/morbidity-coding/registry", headers=headers)
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) >= 20

    # 3. Search by query 'Amavata'
    resp_q = client_with_db.get("/api/v1/morbidity-coding/registry?q=Amavata", headers=headers)
    assert resp_q.status_code == 200
    q_entries = resp_q.json()
    assert len(q_entries) == 1
    assert q_entries[0]["disease_code"] == "AYU-DIS-AMAVATA"
    assert q_entries[0]["namaste_code"] == "NAMASTE-AYU-014"
    assert q_entries[0]["icd11_biomed_code"] == "FA20.Z"

    # 4. Filter by Doshic category
    resp_pitta = client_with_db.get("/api/v1/morbidity-coding/registry?doshic_category=PITTAJA", headers=headers)
    assert resp_pitta.status_code == 200
    pitta_entries = resp_pitta.json()
    assert len(pitta_entries) >= 3
    for p in pitta_entries:
        assert p["doshic_category"] == "PITTAJA"

    # 5. Detail by disease code
    resp_det = client_with_db.get("/api/v1/morbidity-coding/registry/AYU-DIS-VATARAKTA", headers=headers)
    assert resp_det.status_code == 200
    assert resp_det.json()["disease_code"] == "AYU-DIS-VATARAKTA"

    # 6. Detail by NAMASTE code
    resp_nam = client_with_db.get("/api/v1/morbidity-coding/registry/NAMASTE-AYU-031", headers=headers)
    assert resp_nam.status_code == 200
    assert resp_nam.json()["disease_code"] == "AYU-DIS-VATARAKTA"

    # 7. Non-existent returns 404
    resp_404 = client_with_db.get("/api/v1/morbidity-coding/registry/NON-EXISTENT-CODE", headers=headers)
    assert resp_404.status_code == 404


def test_patient_diagnosis_assignment_and_fhir_bundle_lifecycle(client_with_db):
    """Verify patient diagnosis recording, EHR retrieval, and FHIR Bundle generation."""
    # 1. Login
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Register patient
    pat_payload = {
        "hospital_id": "aiia-delhi-central-001",
        "first_name": "Kavitha",
        "last_name": "Namboodiri",
        "dob": "1988-11-23",
        "gender": "FEMALE",
        "contact_phone": "+919876543288",
        "abha_id": "14-3344-5566-7788",
    }
    reg_resp = client_with_db.post("/api/v1/patients", json=pat_payload, headers=headers)
    assert reg_resp.status_code == 201
    patient_id = reg_resp.json()["patient_id"]

    # 3. Assign first diagnosis: AMAVATA
    diag_payload_1 = {
        "patient_id": patient_id,
        "disease_code": "AYU-DIS-AMAVATA",
        "clinical_notes": "Symmetric small and large joint inflammatory stiffness with positive morning gaurava",
        "verification_status": "DIFFERENTIAL_CONFIRMED"
    }
    assign_resp_1 = client_with_db.post(
        f"/api/v1/morbidity-coding/patients/{patient_id}/diagnose",
        json=diag_payload_1,
        headers=headers
    )
    assert assign_resp_1.status_code == 201
    data_1 = assign_resp_1.json()
    assert data_1["patient_id"] == patient_id
    assert data_1["disease_crosswalk"]["disease_code"] == "AYU-DIS-AMAVATA"
    assert data_1["disease_crosswalk"]["namaste_code"] == "NAMASTE-AYU-014"
    assert data_1["disease_crosswalk"]["icd11_tm2_code"] == "TM2-AYU-AMA"
    assert data_1["disease_crosswalk"]["icd11_biomed_code"] == "FA20.Z"
    assert data_1["fhir_condition"]["resourceType"] == "Condition"

    # 4. Assign second diagnosis: TAMAKA_SHWASA
    diag_payload_2 = {
        "patient_id": patient_id,
        "disease_code": "AYU-DIS-TAMAKA-SHWASA",
        "clinical_notes": "Secondary presentation of bronchial asthma during cold rainy periods",
        "verification_status": "DIFFERENTIAL_CONFIRMED"
    }
    assign_resp_2 = client_with_db.post(
        f"/api/v1/morbidity-coding/patients/{patient_id}/diagnose",
        json=diag_payload_2,
        headers=headers
    )
    assert assign_resp_2.status_code == 201

    # 5. Query patient diagnoses list
    list_resp = client_with_db.get(
        f"/api/v1/morbidity-coding/patients/{patient_id}/diagnoses",
        headers=headers
    )
    assert list_resp.status_code == 200
    diag_list = list_resp.json()
    assert len(diag_list) == 2
    codes = [d["disease_crosswalk"]["disease_code"] for d in diag_list]
    assert "AYU-DIS-AMAVATA" in codes
    assert "AYU-DIS-TAMAKA-SHWASA" in codes

    # 6. Query ABDM FHIR Condition Bundle
    bundle_resp = client_with_db.get(
        f"/api/v1/morbidity-coding/patients/{patient_id}/fhir-conditions",
        headers=headers
    )
    assert bundle_resp.status_code == 200
    bundle = bundle_resp.json()
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert bundle["total"] == 2
    assert len(bundle["entry"]) == 2
    assert bundle["entry"][0]["resource"]["resourceType"] == "Condition"


def test_patient_diagnosis_error_conditions(client_with_db):
    """Verify validation error responses for diagnosis assignment."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Non-existent patient returns 404
    resp_no_pat = client_with_db.post(
        "/api/v1/morbidity-coding/patients/pat-nonexistent-999/diagnose",
        json={"patient_id": "pat-nonexistent-999", "disease_code": "AYU-DIS-AMAVATA"},
        headers=headers
    )
    assert resp_no_pat.status_code == 404

    # Register real patient
    pat_payload = {
        "hospital_id": "aiia-delhi-central-001",
        "first_name": "Tara",
        "last_name": "Devi",
        "dob": "1992-06-15",
        "gender": "FEMALE",
        "contact_phone": "+919876543211",
        "abha_id": "14-7788-9900-1122",
    }
    reg_resp = client_with_db.post("/api/v1/patients", json=pat_payload, headers=headers)
    patient_id = reg_resp.json()["patient_id"]

    # 2. Path and body ID mismatch returns 400
    resp_mismatch = client_with_db.post(
        f"/api/v1/morbidity-coding/patients/{patient_id}/diagnose",
        json={"patient_id": "pat-different-id", "disease_code": "AYU-DIS-AMAVATA"},
        headers=headers
    )
    assert resp_mismatch.status_code == 400

    # 3. Invalid disease code returns 404
    resp_invalid_code = client_with_db.post(
        f"/api/v1/morbidity-coding/patients/{patient_id}/diagnose",
        json={"patient_id": patient_id, "disease_code": "AYU-INVALID-DISEASE-CODE"},
        headers=headers
    )
    assert resp_invalid_code.status_code == 404
