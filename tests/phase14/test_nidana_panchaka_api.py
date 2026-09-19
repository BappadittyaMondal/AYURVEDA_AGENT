"""
Phase 14: Integration Test Suite for Nidana Panchaka Differential Diagnostics API.
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
        test_db_path = Path(tmpdir) / "nidana_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "nidana_api_test.db")

        with TestClient(app) as client:
            yield client


def test_diseases_reference_endpoints(client_with_db):
    """Verify registry listing and specific disease queries."""
    # 1. Login
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. List all diseases
    resp = client_with_db.get("/api/v1/nidana-panchaka/diseases", headers=headers)
    assert resp.status_code == 200
    diseases = resp.json()
    assert len(diseases) == 10
    codes = [d["code"] for d in diseases]
    assert "AMAVATA" in codes
    assert "SANDHIGATA_VATA" in codes
    assert "TAMAKA_SHWASA" in codes

    # 3. Get specific disease
    resp_amavata = client_with_db.get("/api/v1/nidana-panchaka/diseases/AMAVATA", headers=headers)
    assert resp_amavata.status_code == 200
    data = resp_amavata.json()
    assert data["code"] == "AMAVATA"
    assert "scorpion" in " ".join(data["pratyatma_lingas"]).lower()
    assert data["samprapti_ghatakas"]["primary_dosha"] == "Vata"

    # 4. Non-existent disease returns 404
    resp_404 = client_with_db.get("/api/v1/nidana-panchaka/diseases/UNKNOWN_DISEASE", headers=headers)
    assert resp_404.status_code == 404


def test_nidana_panchaka_evaluation_and_retrieval_lifecycle(client_with_db):
    """Verify complete differential evaluation lifecycle, latest retrieval, and history."""
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
        "first_name": "Raghunath",
        "last_name": "Bhattacharya",
        "dob": "1972-03-21",
        "gender": "MALE",
        "contact_phone": "+919876543277",
        "abha_id": "14-2233-4455-6677",
    }
    reg_resp = client_with_db.post("/api/v1/patients", json=pat_payload, headers=headers)
    assert reg_resp.status_code == 201
    patient_id = reg_resp.json()["patient_id"]

    # 3. Evaluate first: Classic Amavata presentation
    eval_payload_1 = {
        "patient_id": patient_id,
        "presented_nidana": [
            "Viruddha Ahara (Incompatible foods)",
            "Mandagni (Impaired digestion)",
            "Divaswapna (Daytime sleep)"
        ],
        "presented_purvaroopa": [
            "Alasya (Lethargy)",
            "Gaurava (Generalized heaviness)",
            "Aruchi (Loss of appetite)"
        ],
        "presented_roopa": [
            "Sandhi Shula (Severe joint pain)",
            "Sandhi Shotha (Bilateral joint swelling)",
            "Stambha (Severe morning stiffness)",
            "Angamarda (Generalized body aches)",
            "Vrischika Damshavat Shula (Excruciating joint pain resembling scorpion sting)",
            "Agnimandya"
        ],
        "upashaya_trials": [
            {
                "description": "Langhana and dry Valuka Sweda",
                "category": "VYADHI_VIPARITA",
                "outcome": "UPASHAYA_RELIEVED",
                "modality": "Aushadha/Ahara"
            }
        ],
        "observed_doshas": ["Vata", "Kapha"]
    }

    resp_eval_1 = client_with_db.post(
        "/api/v1/nidana-panchaka/evaluate",
        json=eval_payload_1,
        headers=headers
    )
    assert resp_eval_1.status_code == 201
    data_1 = resp_eval_1.json()
    assert data_1["patient_id"] == patient_id
    assert data_1["primary_diagnosis"]["disease_code"] == "AMAVATA"
    assert data_1["primary_diagnosis"]["match_score"] >= 70.0
    assert len(data_1["differential_diagnoses"]) > 0
    assert len(data_1["clinical_recommendations"]) > 0

    # 4. Evaluate second: Bronchial asthma presentation
    eval_payload_2 = {
        "patient_id": patient_id,
        "presented_nidana": ["Raja-Dhooma Sevana", "Sheeta Vata"],
        "presented_purvaroopa": ["Parshva Shula", "Anaha"],
        "presented_roopa": [
            "Teevra Shwasa Krichrata (Acute paroxysmal respiratory distress)",
            "Ghurghuraka (Audible wheezing)",
            "Asino Labhate Saukhyam (Relief exclusively on sitting upright / orthopnea)",
            "Kasa with chest tightness"
        ],
        "upashaya_trials": [
            {
                "description": "Asino Avastha (Upright sitting posture) and warm fluid drinking",
                "category": "VYADHI_VIPARITA",
                "outcome": "UPASHAYA_RELIEVED",
                "modality": "Vihara"
            }
        ],
        "observed_doshas": ["Vata", "Kapha"]
    }

    resp_eval_2 = client_with_db.post(
        "/api/v1/nidana-panchaka/evaluate",
        json=eval_payload_2,
        headers=headers
    )
    assert resp_eval_2.status_code == 201
    data_2 = resp_eval_2.json()
    assert data_2["primary_diagnosis"]["disease_code"] == "TAMAKA_SHWASA"

    # 5. Query Latest (must return the second assessment: TAMAKA_SHWASA)
    resp_latest = client_with_db.get(
        f"/api/v1/nidana-panchaka/patients/{patient_id}/latest",
        headers=headers
    )
    assert resp_latest.status_code == 200
    latest_data = resp_latest.json()
    assert latest_data["primary_diagnosis"]["disease_code"] == "TAMAKA_SHWASA"

    # 6. Query History (must return 2 records in chronological order)
    resp_hist = client_with_db.get(
        f"/api/v1/nidana-panchaka/patients/{patient_id}/history",
        headers=headers
    )
    assert resp_hist.status_code == 200
    history = resp_hist.json()
    assert len(history) == 2
    assert history[0]["primary_diagnosis"]["disease_code"] == "AMAVATA"
    assert history[1]["primary_diagnosis"]["disease_code"] == "TAMAKA_SHWASA"


def test_nidana_panchaka_nonexistent_patient_returns_404(client_with_db):
    """Verify that operations on non-existent patients return 404."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    fake_id = "pat-nonexistent-999"

    # Evaluate for non-existent patient
    eval_resp = client_with_db.post(
        "/api/v1/nidana-panchaka/evaluate",
        json={"patient_id": fake_id, "presented_roopa": ["Fever", "Pain"]},
        headers=headers,
    )
    assert eval_resp.status_code == 404

    # Latest for non-existent patient
    latest_resp = client_with_db.get(
        f"/api/v1/nidana-panchaka/patients/{fake_id}/latest",
        headers=headers,
    )
    assert latest_resp.status_code == 404

    # History for non-existent patient
    hist_resp = client_with_db.get(
        f"/api/v1/nidana-panchaka/patients/{fake_id}/history",
        headers=headers,
    )
    assert hist_resp.status_code == 404
