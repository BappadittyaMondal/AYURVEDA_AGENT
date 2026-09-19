"""
Integration Tests for Clinical Dietetics & Pathya-Apathya API (Phase 21).
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
        test_db_path = Path(tmpdir) / "dietetics_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-DIET-API-01", "aiia-delhi-central-001", "Anand", "Vaidya", "1982-11-05", "MALE", "+919876543288", 1700000000)
        )
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "dietetics_api_test.db")

        with TestClient(app) as client:
            yield client


def test_ingredients_listing_and_filtering(client_with_db):
    """Verify catalog listing, Ahara Varga filtering, and text search."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List all ingredients
    resp = client_with_db.get("/api/v1/dietetics/ingredients", headers=headers)
    assert resp.status_code == 200
    ings = resp.json()
    assert len(ings) >= 24

    # 2. Filter by Ahara Varga 'GORASA_VARGA'
    resp_gorasa = client_with_db.get("/api/v1/dietetics/ingredients?varga=GORASA_VARGA", headers=headers)
    assert resp_gorasa.status_code == 200
    gorasa_list = resp_gorasa.json()
    assert len(gorasa_list) >= 4
    assert all(i["ahara_varga"] == "GORASA_VARGA" for i in gorasa_list)

    # 3. Search query 'Ginger'
    resp_q = client_with_db.get("/api/v1/dietetics/ingredients?q=Ginger", headers=headers)
    assert resp_q.status_code == 200
    found = resp_q.json()
    assert len(found) >= 1
    assert found[0]["ingredient_id"] == "ING-ARDRAKA"


def test_ingredient_detail_and_404(client_with_db):
    """Verify single ingredient detail retrieval and 404 response for unknown ID."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client_with_db.get("/api/v1/dietetics/ingredients/ING-RAKTASHALI", headers=headers)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["ingredient_id"] == "ING-RAKTASHALI"
    assert detail["veerya"] == "Sheeta"

    resp_404 = client_with_db.get("/api/v1/dietetics/ingredients/ING-NONEXISTENT", headers=headers)
    assert resp_404.status_code == 404


def test_disease_pathya_apathya_endpoint(client_with_db):
    """Verify disease Pathya and Apathya guidelines endpoint."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client_with_db.get("/api/v1/dietetics/pathya-apathya/AYU-DIS-AMAVATA", headers=headers)
    assert resp.status_code == 200
    guidelines = resp.json()
    assert guidelines["disease_code"] == "AYU-DIS-AMAVATA"
    assert len(guidelines["pathya_ahara"]) > 0

    resp_404 = client_with_db.get("/api/v1/dietetics/pathya-apathya/AYU-UNKNOWN", headers=headers)
    assert resp_404.status_code == 404


def test_audit_viruddha_fast_endpoint(client_with_db):
    """Verify fast 18-fold Viruddha Ahara audit endpoint."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Meal with heated honey
    bad_meals = [
        {
            "meal_name": "PRATARASHA",
            "time_of_day": "08:00 AM",
            "items": [
                {"ingredient_id": "ING-MADHU", "portion_grams": 25.0, "is_heated": True}
            ]
        }
    ]
    resp = client_with_db.post("/api/v1/dietetics/audit-viruddha", json=bad_meals, headers=headers)
    assert resp.status_code == 200
    violations = resp.json()
    assert len(violations) >= 1
    assert violations[0]["viruddha_type"] == "SAMSKARA_VIRUDDHA"
    assert violations[0]["severity"] == "CRITICAL_BLOCKED"


def test_prescribe_diet_plan_endpoint_success_and_blocked(client_with_db):
    """Verify diet plan prescription creation, compliance calculation, and critical rejection."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Valid balanced meal plan
    valid_payload = {
        "patient_id": "PAT-DIET-API-01",
        "diagnosis_code": "AYU-DIS-SANDHIGATA-VATA",
        "target_calories": 2100.0,
        "prescribed_by_arn": "AY-DL-2024-998811",
        "meals": [
            {
                "meal_name": "PRATARASHA",
                "time_of_day": "08:00 AM",
                "items": [
                    {"ingredient_id": "ING-GODHUMA", "portion_grams": 100.0, "is_heated": True},
                    {"ingredient_id": "ING-GODUGDHA", "portion_grams": 200.0, "is_heated": False},
                ]
            },
            {
                "meal_name": "MADHYAHNA",
                "time_of_day": "01:00 PM",
                "items": [
                    {"ingredient_id": "ING-RAKTASHALI", "portion_grams": 150.0, "is_heated": True},
                    {"ingredient_id": "ING-GHRITA", "portion_grams": 15.0, "is_heated": False},
                    {"ingredient_id": "ING-DADIMA", "portion_grams": 100.0, "is_heated": False},
                ]
            }
        ]
    }
    resp_valid = client_with_db.post("/api/v1/dietetics/prescriptions", json=valid_payload, headers=headers)
    assert resp_valid.status_code == 201
    plan_data = resp_valid.json()
    assert plan_data["viruddha_check_passed"] is True
    assert plan_data["total_calories"] > 500.0
    assert plan_data["patient_id"] == "PAT-DIET-API-01"

    # 2. Blocked meal plan (Fish + Milk Veerya Viruddha)
    blocked_payload = {
        "patient_id": "PAT-DIET-API-01",
        "diagnosis_code": "AYU-DIS-SANDHIGATA-VATA",
        "target_calories": 1800.0,
        "prescribed_by_arn": "AY-DL-2024-998811",
        "meals": [
            {
                "meal_name": "MADHYAHNA",
                "time_of_day": "01:00 PM",
                "items": [
                    {"ingredient_id": "ING-MATSYA", "portion_grams": 150.0, "is_heated": True},
                    {"ingredient_id": "ING-GODUGDHA", "portion_grams": 200.0, "is_heated": False},
                ]
            }
        ]
    }
    resp_blocked = client_with_db.post("/api/v1/dietetics/prescriptions", json=blocked_payload, headers=headers)
    assert resp_blocked.status_code == 422
    assert "CRITICAL_VIRUDDHA_AHARA_BLOCKED" in resp_blocked.json()["detail"]
