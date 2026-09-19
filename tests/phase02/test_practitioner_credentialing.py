"""Phase 02: Test Suite for NCISM Practitioner Credentialing & ARN Verification."""
import tempfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from config.settings import get_settings
from core.database import init_database
from models.clinical import PractitionerDegree, PractitionerRegistrationRequest
from main import app


@pytest.fixture
def client_with_db(monkeypatch):
    """Fixture providing TestClient backed by an isolated temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "practitioner_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "practitioner_test.db")

        with TestClient(app) as client:
            yield client


def test_arn_regex_format_validation():
    """Verify that ARN must conform strictly to ARN-NCISM-YYYY-XXXX format."""
    # Valid ARN
    req = PractitionerRegistrationRequest(
        arn="ARN-NCISM-2018-7721",
        hospital_id="aiia-delhi-central-001",
        full_name="Dr. Harish Kumar",
        qualification=PractitionerDegree.MD_AYU,
        university="National Institute of Ayurveda, Jaipur",
        registration_year=2018,
        state_council="Rajasthan Board of Indian Medicine"
    )
    assert req.arn == "ARN-NCISM-2018-7721"

    # Invalid ARNs
    with pytest.raises(ValueError):
        PractitionerRegistrationRequest(
            arn="INVALID-ARN-1234",
            hospital_id="aiia-delhi-central-001",
            full_name="Dr. Invalid",
            qualification=PractitionerDegree.BAMS,
            university="University",
            registration_year=2020,
            state_council="Delhi"
        )


def test_practitioner_registration_and_retrieval(client_with_db):
    """Verify practitioner registration lifecycle and duplicate prevention."""
    # 1. Login as superintendent
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "superintendent", "password": "Superintendent@AIIA2026"}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Register valid practitioner
    payload = {
        "arn": "ARN-NCISM-2016-5542",
        "hospital_id": "aiia-delhi-central-001",
        "full_name": "Dr. Meenakshi Sundaram, MD(Ayu)",
        "qualification": "MD_AYU",
        "university": "All India Institute of Ayurveda, New Delhi",
        "registration_year": 2016,
        "state_council": "Delhi Bharatiya Chikitsa Parishad"
    }
    reg_resp = client_with_db.post("/api/v1/practitioners", json=payload, headers=headers)
    assert reg_resp.status_code == 201
    data = reg_resp.json()
    assert data["arn"] == "ARN-NCISM-2016-5542"
    assert data["is_verified"] is True

    # 3. Prevent duplicate ARN registration
    dup_resp = client_with_db.post("/api/v1/practitioners", json=payload, headers=headers)
    assert dup_resp.status_code == 400

    # 4. Fetch practitioner by ARN
    get_resp = client_with_db.get(f"/api/v1/practitioners/{payload['arn']}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["full_name"] == payload["full_name"]


def test_practitioner_tenant_isolation(client_with_db):
    """Verify that practitioner registration is rejected if targeting another hospital."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "superintendent", "password": "Superintendent@AIIA2026"}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "arn": "ARN-NCISM-2021-9988",
        "hospital_id": "foreign-hospital-999",  # Cross-tenant mismatch
        "full_name": "Dr. Foreign Practitioner",
        "qualification": "BAMS",
        "university": "Government Ayurvedic College",
        "registration_year": 2021,
        "state_council": "Kerala"
    }
    resp = client_with_db.post("/api/v1/practitioners", json=payload, headers=headers)
    assert resp.status_code == 403
