"""Phase 13: Integration Test Suite for Roga Rogi Bala Ganan Yantra API."""
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
        test_db_path = Path(tmpdir) / "bala_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "bala_api_test.db")

        with TestClient(app) as client:
            yield client


def test_roga_rogi_bala_evaluation_and_retrieval_lifecycle(client_with_db):
    """Verify complete bi-directional evaluation lifecycle, latest retrieval, and history."""
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
        "first_name": "Madhavan",
        "last_name": "Acharya",
        "dob": "1965-08-14",
        "gender": "MALE",
        "contact_phone": "+919876543266",
        "abha_id": "14-1122-3344-5566",
    }
    reg_resp = client_with_db.post("/api/v1/patients", json=pat_payload, headers=headers)
    assert reg_resp.status_code == 201
    patient_id = reg_resp.json()["patient_id"]

    # 3. Evaluate first: Robust host, virulent disease (Tikshna Shodhana)
    eval_payload = {
        "patient_id": patient_id,
        "rogi_bala": {
            "sahaja_bala": 0.8,
            "kalaja_bala": 0.8,
            "yuktikrita_bala": 0.8,
            "dhatu_sarata_osi": 85.0,
            "sattva_score": 0.9,
            "agni_strength": 0.85,
        },
        "roga_bala": {
            "vikriti_vsi": 70.0,
            "srotas_involvement_osi": 60.0,
            "vulnerable_channels_count": 5,
            "kriya_kala_ppi": 4.8,
            "ama_agi_score": 50.0,
            "chronicity_months": 6.0,
        },
    }
    eval_resp = client_with_db.post("/api/v1/roga-rogi-bala/evaluate", json=eval_payload, headers=headers)
    assert eval_resp.status_code == 201
    data = eval_resp.json()
    assert data["patient_id"] == patient_id
    assert data["therapeutic_category"] == "TIKSHNA_SHODHANA"
    assert data["shodhana_eligibility_status"] == "FULL_ELIGIBILITY"
    assert data["dosage_scalar"] == 1.25
    assert len(data["governor_directives"]) > 0

    # 4. Evaluate second: Frail host, virulent disease (Contraindicated Shodhana)
    eval_payload_2 = {
        "patient_id": patient_id,
        "rogi_bala": {
            "sahaja_bala": 0.3,
            "kalaja_bala": 0.3,
            "yuktikrita_bala": 0.2,
            "dhatu_sarata_osi": 35.0,
            "sattva_score": 0.3,
            "agni_strength": 0.3,
        },
        "roga_bala": {
            "vikriti_vsi": 75.0,
            "srotas_involvement_osi": 65.0,
            "vulnerable_channels_count": 6,
            "kriya_kala_ppi": 5.2,
            "ama_agi_score": 60.0,
            "chronicity_months": 18.0,
        },
    }
    eval_resp_2 = client_with_db.post("/api/v1/roga-rogi-bala/evaluate", json=eval_payload_2, headers=headers)
    assert eval_resp_2.status_code == 201
    data2 = eval_resp_2.json()
    assert data2["therapeutic_category"] == "CONTRAINDICATED_SHODHANA_EMERGENCY_BRIMHANA"
    assert data2["shodhana_eligibility_status"] == "STRICTLY_CONTRAINDICATED"
    assert data2["dosage_scalar"] == 0.50

    # 5. Retrieve latest
    latest_resp = client_with_db.get(f"/api/v1/roga-rogi-bala/patients/{patient_id}/latest", headers=headers)
    assert latest_resp.status_code == 200
    assert latest_resp.json()["therapeutic_category"] == "CONTRAINDICATED_SHODHANA_EMERGENCY_BRIMHANA"

    # 6. Retrieve history
    hist_resp = client_with_db.get(f"/api/v1/roga-rogi-bala/patients/{patient_id}/history", headers=headers)
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()) == 2


def test_roga_rogi_bala_nonexistent_patient_returns_404(client_with_db):
    """Verify 404 response for non-existent patient."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "patient_id": "nonexistent-patient-uuid",
        "rogi_bala": {},
        "roga_bala": {},
    }
    resp = client_with_db.post("/api/v1/roga-rogi-bala/evaluate", json=payload, headers=headers)
    assert resp.status_code == 404
