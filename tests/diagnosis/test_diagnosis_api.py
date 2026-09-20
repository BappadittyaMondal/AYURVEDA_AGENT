"""Integration tests for Unified Clinical Diagnostic REST API."""
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
        test_db_path = Path(tmpdir) / "diagnosis_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-DIAG-API-01", "aiia-delhi-central-001", "Virendra", "Tripathi", "1975-06-12", "MALE", "+919876543099", 1700000000)
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "diagnosis_api_test.db")

        with TestClient(app) as client:
            yield client


def test_diagnosis_evaluation_endpoint(client_with_db):
    """Verify evaluating clinical intake via REST API returns complete dual-coded diagnosis."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    intake_payload = {
        "patient_id": "PAT-DIAG-API-01",
        "hospital_id": "aiia-delhi-central-001",
        "chief_complaints": [
            "Severe pain and morning stiffness in both knees",
            "Swelling in ankle joints and loss of appetite"
        ],
        "symptoms": ["joint pain", "morning stiffness", "sandhi-shula", "stambha", "shotha", "aruchi"],
        "duration_weeks": 4.0,
        "jihwa_coating": "THICK_WHITE_SLIMY",
        "appetite_and_digestion": "POOR_MANDAGNI",
        "rogi_bala": "MADHYAMA",
        "systolic_bp": 120,
        "diastolic_bp": 80,
        "hemoglobin_g_dl": 13.0,
        "is_pregnant": False,
        "age_years": 48
    }

    resp = client_with_db.post("/api/v1/diagnosis/evaluate", json=intake_payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["episode_id"].startswith("EPISODE-DIAG-")
    assert data["primary_diagnosis"]["sanskrit_name"] == "Amavata"
    assert data["primary_diagnosis"]["namaste_code"] == "AYU-ROGA-AMA-001"
    assert data["primary_diagnosis"]["icd11_tm2_code"] == "FA20.Z"
    assert data["ama_status"] == "SAMA"
    assert data["governance_status"] == "DRAFT_DECISION_SUPPORT"
    assert len(data["treatment_protocol"]["shamana_chikitsa"]) >= 2
    assert "Amavata" in data["patient_summary_report_markdown"]


def test_countersign_endpoint_lifecycle(client_with_db):
    """Verify NCISM physician can counter-sign an episode transitioning it to PHYSICIAN_COUNTERSIGNED."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create episode
    intake = {
        "patient_id": "PAT-DIAG-API-01",
        "hospital_id": "aiia-delhi-central-001",
        "chief_complaints": ["Sciatica radiating pain"],
        "symptoms": ["sciatica", "radiating leg pain", "suptata"],
        "duration_weeks": 3.0,
        "appetite_and_digestion": "VARIABLE_VISHAMAGNI",
        "rogi_bala": "MADHYAMA",
        "systolic_bp": 120,
        "diastolic_bp": 80,
        "hemoglobin_g_dl": 13.0,
        "is_pregnant": False,
        "age_years": 42
    }
    eval_resp = client_with_db.post("/api/v1/diagnosis/evaluate", json=intake, headers=headers)
    assert eval_resp.status_code == 201
    episode_id = eval_resp.json()["episode_id"]

    # 2. Countersign episode
    sign_payload = {
        "physician_arn": "ARN-NCISM-2015-8832",
        "action": "COUNTERSIGN",
        "clinical_notes": "Reviewed and approved for conservative management and Kati Basti."
    }
    sign_resp = client_with_db.post(f"/api/v1/diagnosis/episodes/{episode_id}/countersign", json=sign_payload, headers=headers)
    assert sign_resp.status_code == 200
    signed_data = sign_resp.json()
    assert signed_data["governance_status"] == "PHYSICIAN_COUNTERSIGNED"
    assert signed_data["attending_physician_arn"] == "ARN-NCISM-2015-8832"
    assert signed_data["countersigned_at"] is not None

    # 3. Retrieve patient history
    hist_resp = client_with_db.get("/api/v1/diagnosis/episodes/patient/PAT-DIAG-API-01", headers=headers)
    assert hist_resp.status_code == 200
    episodes = hist_resp.json()
    assert len(episodes) >= 1
    assert episodes[0]["episode_id"] == episode_id
    assert episodes[0]["governance_status"] == "PHYSICIAN_COUNTERSIGNED"


def test_disease_catalog_endpoint(client_with_db):
    """Verify querying morbidity catalog returns supported classical diseases with dual coding."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client_with_db.get("/api/v1/diagnosis/disease-catalog", headers=headers)
    assert resp.status_code == 200
    catalog = resp.json()
    assert len(catalog) >= 5
    names = {c["sanskrit_name"] for c in catalog}
    assert "Amavata" in names
    assert "Prameha (Madhumeha)" in names
    assert "Tamaka Shwasa" in names
    assert "Gridhrasi" in names
    assert "Sandhivata" in names


def test_incomplete_intake_rejected_by_api(client_with_db):
    """Verify missing mandatory parameters without override are rejected with 422 HTTP status."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    incomplete_payload = {
        "patient_id": "PAT-DIAG-API-01",
        "hospital_id": "aiia-delhi-central-001",
        "chief_complaints": ["Knee pain"],
        "symptoms": ["sandhi-shula"]
    }
    resp = client_with_db.post("/api/v1/diagnosis/evaluate", json=incomplete_payload, headers=headers)
    assert resp.status_code == 422
    assert "Mandatory parameters missing" in resp.json()["detail"]
