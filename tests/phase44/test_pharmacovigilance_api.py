"""
tests/phase44/test_pharmacovigilance_api.py - Integration API tests for Phase 44 Pharmacovigilance endpoints.
"""

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
        test_db_path = Path(tmpdir) / "pv_api_test.db"
        init_database(test_db_path)

        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("pat-api-pv-01", "aiia-delhi-central-001", "Meera", "Sen", "1983-04-10", "FEMALE", "+919876549900", 1700000000)
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "pv_api_test.db")

        with TestClient(app) as client:
            yield client


def test_pharmacovigilance_api_lifecycle(client_with_db):
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. File ADR Report
    report_payload = {
        "patient_id": "pat-api-pv-01",
        "hospital_id": "aiia-delhi-central-001",
        "suspected_formulation": "Chitrakadi Vati",
        "batch_number": "CHK-2026-01",
        "adverse_reaction_description": "Epigastric burning sensation after consumption",
        "onset_latency_hours": 2.0,
        "naranjo_questions": {
            "previous_conclusive_reports": True,
            "onset_after_drug": True,
            "dechallenge_improvement": True,
            "rechallenge_recurrence": False,
            "alternative_causes_absent": True,
            "toxic_concentration_or_heavy_metal": False,
            "dose_response_gradient": False,
            "past_history_similar": False,
            "objective_laboratory_evidence": False
        },
        "action_taken": "Dosage reduced to half and administered with milk",
        "reporting_rmp_arn": "ARN-NCISM-2015-8832"
    }
    create_res = client_with_db.post("/api/v1/pharmacovigilance/reports", json=report_payload, headers=headers)
    assert create_res.status_code == 201
    rep_data = create_res.json()
    assert rep_data["report_id"].startswith("adr-")
    assert rep_data["causality_category"] in ["PROBABLE", "CERTAIN", "POSSIBLE"]

    # 2. Export Yellow Card XML
    exp_res = client_with_db.post(f"/api/v1/pharmacovigilance/reports/{rep_data['report_id']}/export-yellow-card")
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    assert "<NPvCC_YellowCard_Form>" in exp_data["xml_payload_preview"]

    # 3. Get Patient ADR Reports
    hist_res = client_with_db.get("/api/v1/pharmacovigilance/patient/pat-api-pv-01/reports")
    assert hist_res.status_code == 200
    reports = hist_res.json()
    assert len(reports) >= 1
    assert reports[0]["report_id"] == rep_data["report_id"]
