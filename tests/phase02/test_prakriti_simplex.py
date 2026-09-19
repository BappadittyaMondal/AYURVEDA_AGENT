"""Phase 02: Test Suite for Tridosha Simplex Calculus & Prakriti Diagnostic Engine."""
import tempfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from config.settings import get_settings
from core.database import init_database
from core.prakriti import DIRICHLET_EPSILON, PRAKRITI_QUESTIONS, compute_prakriti_simplex
from main import app


def test_simplex_closure_and_dirichlet_boundary():
    """Verify that any combination of answers produces valid coordinates on the Delta^2 simplex."""
    # Scenario 1: Extreme Vata (all 'A')
    answers_vata = {q["id"]: "A" for q in PRAKRITI_QUESTIONS}
    v, p, k, primary, classification = compute_prakriti_simplex(answers_vata)

    assert abs((v + p + k) - 1.0) < 1e-4, f"Simplex sum violation: {v + p + k}"
    assert min(v, p, k) >= DIRICHLET_EPSILON, "Dirichlet epsilon boundary violation"
    assert primary == "VATA"
    assert classification == "VATA_PRADHAN"
    assert v > 0.95

    # Scenario 2: Extreme Pitta (all 'B')
    answers_pitta = {q["id"]: "B" for q in PRAKRITI_QUESTIONS}
    v, p, k, primary, classification = compute_prakriti_simplex(answers_pitta)
    assert abs((v + p + k) - 1.0) < 1e-4
    assert primary == "PITTA"
    assert classification == "PITTA_PRADHAN"
    assert p > 0.95

    # Scenario 3: Extreme Kapha (all 'C')
    answers_kapha = {q["id"]: "C" for q in PRAKRITI_QUESTIONS}
    v, p, k, primary, classification = compute_prakriti_simplex(answers_kapha)
    assert abs((v + p + k) - 1.0) < 1e-4
    assert primary == "KAPHA"
    assert classification == "KAPHA_PRADHAN"
    assert k > 0.95


def test_balanced_sama_tridosha_classification():
    """Verify that equal distribution across all three doshas yields SAMA_TRIDOSHA."""
    # 10 'A', 10 'B', 10 'C'
    answers = {}
    for i, q in enumerate(PRAKRITI_QUESTIONS):
        if i < 10:
            answers[q["id"]] = "A"
        elif i < 20:
            answers[q["id"]] = "B"
        else:
            answers[q["id"]] = "C"

    v, p, k, primary, classification = compute_prakriti_simplex(answers)
    assert abs((v + p + k) - 1.0) < 1e-4
    assert classification == "SAMA_TRIDOSHA"
    assert abs(v - 0.3333) < 0.02
    assert abs(p - 0.3333) < 0.02
    assert abs(k - 0.3333) < 0.02


def test_dvandvaja_prakriti_classification():
    """Verify that dual dosha predominance (e.g. Vata-Pitta) is correctly identified."""
    # 15 'A' (Vata), 15 'B' (Pitta), 0 'C' (Kapha)
    answers = {}
    for i, q in enumerate(PRAKRITI_QUESTIONS):
        answers[q["id"]] = "A" if i < 15 else "B"

    v, p, k, primary, classification = compute_prakriti_simplex(answers)
    assert abs((v + p + k) - 1.0) < 1e-4
    assert classification == "VATA_PITTA"
    assert v > 0.45 and p > 0.45
    assert k < 0.01


@pytest.fixture
def client_with_db(monkeypatch):
    """Fixture providing TestClient backed by an isolated temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "prakriti_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "prakriti_test.db")

        with TestClient(app) as client:
            yield client


def test_prakriti_assessment_api_workflow(client_with_db):
    """Verify end-to-end clinical workflow: create patient, submit Prakriti assessment, update baseline."""
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
        "abha_id": "88-1122-3344-5566",
        "first_name": "Arjun",
        "last_name": "Nair",
        "dob": "1990-04-12",
        "gender": "MALE"
    }
    pat_resp = client_with_db.post("/api/v1/patients", json=pat_payload, headers=headers)
    assert pat_resp.status_code == 201
    patient_id = pat_resp.json()["patient_id"]

    # 3. Retrieve questionnaire
    q_resp = client_with_db.get("/api/v1/prakriti/questions", headers=headers)
    assert q_resp.status_code == 200
    assert len(q_resp.json()) == 30

    # 4. Submit assessment for patient (Pitta dominant)
    answers = {q["id"]: "B" for q in q_resp.json()}
    assess_resp = client_with_db.post(
        f"/api/v1/prakriti/patients/{patient_id}/assess",
        json={"answers": answers},
        headers=headers
    )
    assert assess_resp.status_code == 201
    assess_data = assess_resp.json()
    assert assess_data["primary_dosha"] == "PITTA"
    assert assess_data["classification"] == "PITTA_PRADHAN"

    # 5. Verify patient's updated baseline in MPI
    pat_get = client_with_db.get(f"/api/v1/patients/{patient_id}", headers=headers)
    assert pat_get.status_code == 200
    assert pat_get.json()["prakriti_pitta"] > 0.90

    # 6. Verify assessment history
    hist_resp = client_with_db.get(f"/api/v1/prakriti/patients/{patient_id}/history", headers=headers)
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()) == 1
    assert hist_resp.json()[0]["assessment_id"] == assess_data["assessment_id"]
