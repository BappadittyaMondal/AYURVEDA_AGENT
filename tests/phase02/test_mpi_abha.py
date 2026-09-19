"""Phase 02: Test Suite for Master Patient Index (MPI) and ABHA ID Binding."""
import tempfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from config.settings import get_settings
from core.database import init_database
from models.clinical import PatientCreateRequest
from main import app


@pytest.fixture
def client_with_db(monkeypatch):
    """Fixture providing TestClient backed by an isolated temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "mpi_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "mpi_test.db")

        with TestClient(app) as client:
            yield client


def test_abha_id_format_validation():
    """Verify standard 14-digit XX-XXXX-XXXX-XXXX format enforcement."""
    # Valid ABHA
    req = PatientCreateRequest(
        hospital_id="aiia-delhi-central-001",
        abha_id="91-4521-8890-3341",
        first_name="Ramesh",
        last_name="Patel",
        dob="1982-06-15",
        gender="MALE",
        contact_phone="9876543210"
    )
    assert req.abha_id == "91-4521-8890-3341"

    # Invalid ABHA format (missing dashes or incorrect digits)
    with pytest.raises(ValueError):
        PatientCreateRequest(
            hospital_id="aiia-delhi-central-001",
            abha_id="91452188903341",
            first_name="Ramesh",
            last_name="Patel",
            dob="1982-06-15",
            gender="MALE"
        )


def test_mpi_patient_registration_and_search(client_with_db):
    """Verify patient registration into MPI, retrieval, and search functionality."""
    # Login as physician RMP
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Register new patient with ABHA
    payload = {
        "hospital_id": "aiia-delhi-central-001",
        "abha_id": "14-9988-7766-5544",
        "first_name": "Savitri",
        "last_name": "Devi",
        "dob": "1975-11-20",
        "gender": "FEMALE",
        "contact_phone": "9811223344"
    }
    reg_resp = client_with_db.post("/api/v1/patients", json=payload, headers=headers)
    assert reg_resp.status_code == 201
    patient = reg_resp.json()
    patient_id = patient["patient_id"]
    assert patient_id.startswith("pat-")
    assert patient["first_name"] == "Savitri"
    assert patient["prakriti_vata"] == 0.3333

    # 2. Prevent duplicate ABHA registration
    dup_resp = client_with_db.post("/api/v1/patients", json=payload, headers=headers)
    assert dup_resp.status_code == 400

    # 3. Retrieve patient by ID
    get_resp = client_with_db.get(f"/api/v1/patients/{patient_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["abha_id"] == "14-9988-7766-5544"

    # 4. Search patient by name
    search_resp = client_with_db.get("/api/v1/patients?query=Savitri", headers=headers)
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert len(results) >= 1
    assert results[0]["patient_id"] == patient_id
