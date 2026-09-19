"""
tests/phase48/test_pharmacy_inventory_api.py - Integration API tests for Phase 48 Pharmacy Inventory & Dispensation endpoints.
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
        test_db_path = Path(tmpdir) / "pharma_api_test.db"
        init_database(test_db_path)

        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("pat-api-pharma-01", "aiia-delhi-central-001", "Geeta", "Tripathi", "1987-03-03", "FEMALE", "+919876541133", 1700000000)
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "pharma_api_test.db")

        with TestClient(app) as client:
            yield client


def test_pharmacy_inventory_api_lifecycle(client_with_db):
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Intake Lot
    intake_payload = {
        "hospital_id": "aiia-delhi-central-001",
        "formulation_name": "Ashwagandharishta",
        "batch_number": "API-BATCH-AR-01",
        "gs1_datamatrix_barcode": "(01)08901234567890(17)281231(10)AR01",
        "manufacturer_name": "Jan Aushadhi Ayush Pharmacy",
        "stock_quantity_units": 80,
        "unit_measure": "BOTTLE_450ML",
        "expiry_date": "2028-12-31",
        "is_quarantined": False
    }
    in_res = client_with_db.post("/api/v1/pharmacy-inventory/lots", json=intake_payload, headers=headers)
    assert in_res.status_code == 201
    lot_data = in_res.json()
    assert lot_data["lot_id"].startswith("lot-")
    assert lot_data["stock_quantity_units"] == 80

    # 2. Get Lot
    get_res = client_with_db.get(f"/api/v1/pharmacy-inventory/lots/{lot_data['lot_id']}")
    assert get_res.status_code == 200
    assert get_res.json()["formulation_name"] == "Ashwagandharishta"

    # 3. Dispense Medication
    disp_payload = {
        "prescription_id": "rx-api-test-01",
        "patient_id": "pat-api-pharma-01",
        "hospital_id": "aiia-delhi-central-001",
        "lot_id": lot_data["lot_id"],
        "quantity_dispensed": 2,
        "pharmacist_user_id": "user-pharmacist-001"
    }
    d_res = client_with_db.post("/api/v1/pharmacy-inventory/dispense", json=disp_payload, headers=headers)
    assert d_res.status_code == 201
    disp_data = d_res.json()
    assert disp_data["remaining_stock_units"] == 78

    # 4. Get Patient Dispensations
    hist_res = client_with_db.get("/api/v1/pharmacy-inventory/patient/pat-api-pharma-01/dispensations")
    assert hist_res.status_code == 200
    records = hist_res.json()
    assert len(records) >= 1
    assert records[0]["dispensation_id"] == disp_data["dispensation_id"]
