"""
tests/phase43/test_edge_sync_api.py - Integration API tests for Phase 43 Offline-First Edge Node Sync endpoints.
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
        test_db_path = Path(tmpdir) / "edge_sync_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "edge_sync_api_test.db")

        with TestClient(app) as client:
            yield client


def test_edge_sync_api_lifecycle(client_with_db):
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Register Edge Node
    reg_payload = {
        "node_id": "NODE-API-EDGE-001",
        "hospital_id": "aiia-delhi-central-001",
        "facility_name": "Sunderbans Mobile Dispensary Boat",
        "facility_type": "MOBILE_TELEMEDICINE_VAN",
        "sync_passkey": "BoatPassKey#2026"
    }
    reg_res = client_with_db.post("/api/v1/edge-sync/nodes", json=reg_payload, headers=headers)
    assert reg_res.status_code == 201
    assert reg_res.json()["node_id"] == "NODE-API-EDGE-001"

    # 2. Get Node
    get_res = client_with_db.get("/api/v1/edge-sync/nodes/NODE-API-EDGE-001")
    assert get_res.status_code == 200
    assert get_res.json()["facility_name"] == "Sunderbans Mobile Dispensary Boat"

    # 3. Queue Single Mutation
    queue_payload = {
        "node_id": "NODE-API-EDGE-001",
        "entity_table": "patients",
        "record_id": "pat-boat-101",
        "operation_type": "INSERT",
        "payload": {"first_name": "Tapas", "gender": "MALE"},
        "vector_clock_counter": 1
    }
    q_res = client_with_db.post("/api/v1/edge-sync/queue", json=queue_payload)
    assert q_res.status_code == 201
    assert q_res.json()["sync_status"] == "PENDING"

    # 4. Reconcile Batch
    batch_payload = {
        "node_id": "NODE-API-EDGE-001",
        "sync_passkey": "BoatPassKey#2026",
        "items": [
            {
                "node_id": "NODE-API-EDGE-001",
                "entity_table": "patients",
                "record_id": "pat-boat-101",
                "operation_type": "UPDATE",
                "payload": {"first_name": "Tapas", "age": 42},
                "vector_clock_counter": 2
            }
        ]
    }
    rec_res = client_with_db.post("/api/v1/edge-sync/reconcile", json=batch_payload)
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["total_received"] == 1
    assert rec_data["applied_count"] == 1

    # 5. Fetch Node Queue
    hist_res = client_with_db.get("/api/v1/edge-sync/nodes/NODE-API-EDGE-001/queue")
    assert hist_res.status_code == 200
    items = hist_res.json()
    assert len(items) >= 2
