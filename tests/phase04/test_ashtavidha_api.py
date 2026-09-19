"""Phase 04: Integration Test Suite for Ashtavidha Pariksha API Endpoints."""
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
        test_db_path = Path(tmpdir) / "ashtavidha_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "ashtavidha_api_test.db")

        with TestClient(app) as client:
            yield client


def test_ashtavidha_api_lifecycle(client_with_db):
    """Verify end-to-end clinical workflow: create patient, submit 8-fold examination, retrieve latest & history."""
    # 1. Login as physician RMP
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Register patient
    pat_payload = {
        "hospital_id": "aiia-delhi-central-001",
        "abha_id": "55-3344-7788-1122",
        "first_name": "Gopal",
        "last_name": "Krishnan",
        "dob": "1968-03-25",
        "gender": "MALE"
    }
    pat_resp = client_with_db.post("/api/v1/patients", json=pat_payload, headers=headers)
    assert pat_resp.status_code == 201
    patient_id = pat_resp.json()["patient_id"]

    # 3. Submit 8-fold examination (Pitta presentation)
    exam_payload = {
        "nadi": {"gati": "MANDUKA", "rate_bpm": 88, "rhythm": "REGULAR", "volume": "BOUNDING"},
        "mutra": {"color": "DARK_YELLOW", "clarity": "CLEAR", "frequency_day": 6, "taila_bindu_direction": "EAST", "dysuria": True},
        "mala": {"consistency": "SOFT_LOOSE", "jala_nimajjana": "FLOATS_NIRAMA", "frequency_per_day": 2, "color": "YELLOWISH"},
        "jihwa": {"color": "RED", "coating": "THIN_WHITE", "fissures": False, "tooth_indentations": False},
        "shabda": {"tone": "CLEAR_RESONANT", "clarity": True},
        "sparsha": {"temperature": "BURNING_HOT", "moisture": "PROFUSE_SWEAT"},
        "drik": {"sclera": "YELLOW_ICTERIC", "lacrimation": True, "photophobia": True},
        "akriti": {"posture": "ATHLETIC_MODERATE", "gait_stability": "STEADY"}
    }

    exam_resp = client_with_db.post(
        f"/api/v1/ashtavidha/patients/{patient_id}",
        json=exam_payload,
        headers=headers
    )
    assert exam_resp.status_code == 201
    data = exam_resp.json()

    assert data["exam_id"].startswith("ash-")
    assert data["primary_dosha"] == "PITTA"
    assert data["pitta_score"] > 0.60
    assert data["examiner_arn"] == "ARN-NCISM-2015-8832"
    assert data["ama_suspected"] is False

    # 4. Query latest examination
    latest_resp = client_with_db.get(f"/api/v1/ashtavidha/patients/{patient_id}/latest", headers=headers)
    assert latest_resp.status_code == 200
    latest_data = latest_resp.json()
    assert latest_data["exam_id"] == data["exam_id"]
    assert latest_data["primary_dosha"] == "PITTA"

    # 5. Query examination history
    hist_resp = client_with_db.get(f"/api/v1/ashtavidha/patients/{patient_id}/history", headers=headers)
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()) == 1
    assert hist_resp.json()[0]["exam_id"] == data["exam_id"]
