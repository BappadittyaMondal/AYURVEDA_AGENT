"""Phase 11: Integration Test Suite for Srotas Pathology Matrix & Khavaigunya Mapping API."""
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
        test_db_path = Path(tmpdir) / "srotas_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "srotas_api_test.db")

        with TestClient(app) as client:
            yield client


def test_srotas_reference_endpoint(client_with_db):
    """Verify listing of all 14 classical Srotamsi with Mula Sthana roots."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client_with_db.get("/api/v1/srotas/reference", headers=headers)
    assert resp.status_code == 200
    channels = resp.json()
    assert len(channels) == 14
    assert any(c["srotas"] == "PRANAVAHA" for c in channels)
    assert any(c["srotas"] == "MANOVAHA" for c in channels)


def test_srotas_evaluation_and_retrieval_lifecycle(client_with_db):
    """Verify complete Srotas diagnostic evaluation, latest lookup, and history retrieval."""
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
        "first_name": "Siddharth",
        "last_name": "Varma",
        "dob": "1988-06-15",
        "gender": "MALE",
        "contact_phone": "+919876543244",
        "abha_id": "14-7788-9900-1122",
    }
    reg_resp = client_with_db.post("/api/v1/patients", json=pat_payload, headers=headers)
    assert reg_resp.status_code == 201
    patient_id = reg_resp.json()["patient_id"]

    # 3. Evaluate first assessment (Severe Pranavaha and Annavaha involvement)
    eval_payload = {
        "patient_id": patient_id,
        "channels": [
            {
                "srotas": "PRANAVAHA",
                "ati_pravritti": 1,
                "sanga": 3,
                "sira_granthi": 0,
                "vimarga_gamana": 1,
                "pre_existing_defect": True,
            },
            {
                "srotas": "ANNAVAHA",
                "ati_pravritti": 0,
                "sanga": 2,
                "sira_granthi": 0,
                "vimarga_gamana": 2,
                "pre_existing_defect": False,
            },
            {
                "srotas": "PURISHAVAHA",
                "ati_pravritti": 0,
                "sanga": 3,
                "sira_granthi": 0,
                "vimarga_gamana": 0,
                "pre_existing_defect": True,
            },
        ],
    }
    eval_resp = client_with_db.post("/api/v1/srotas/evaluate", json=eval_payload, headers=headers)
    assert eval_resp.status_code == 201
    data = eval_resp.json()
    assert data["patient_id"] == patient_id
    assert data["vulnerable_channels_count"] == 3
    assert "PRANAVAHA" in data["khavaigunya_channels"]
    assert "PURISHAVAHA" in data["khavaigunya_channels"]
    assert len(data["srotoshodhana_directives"]) == 3

    # 4. Evaluate second assessment (Resolved / clear channels)
    eval_payload_2 = {
        "patient_id": patient_id,
        "channels": [
            {
                "srotas": "PRANAVAHA",
                "ati_pravritti": 0,
                "sanga": 0,
                "sira_granthi": 0,
                "vimarga_gamana": 0,
                "pre_existing_defect": False,
            }
        ],
    }
    eval_resp_2 = client_with_db.post("/api/v1/srotas/evaluate", json=eval_payload_2, headers=headers)
    assert eval_resp_2.status_code == 201
    data2 = eval_resp_2.json()
    assert data2["vulnerable_channels_count"] == 0
    assert data2["overall_srotas_index"] == 0.0

    # 5. Retrieve latest
    latest_resp = client_with_db.get(f"/api/v1/srotas/patients/{patient_id}/latest", headers=headers)
    assert latest_resp.status_code == 200
    assert latest_resp.json()["overall_srotas_index"] == 0.0

    # 6. Retrieve history
    hist_resp = client_with_db.get(f"/api/v1/srotas/patients/{patient_id}/history", headers=headers)
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()) == 2


def test_srotas_nonexistent_patient_returns_404(client_with_db):
    """Verify 404 response for unregistered patient."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": "nonexistent-patient-uuid",
        "channels": [{"srotas": "PRANAVAHA", "sanga": 2}],
    }
    resp = client_with_db.post("/api/v1/srotas/evaluate", json=payload, headers=headers)
    assert resp.status_code == 404
