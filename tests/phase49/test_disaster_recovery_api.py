"""
tests/phase49/test_disaster_recovery_api.py - Integration API tests for Phase 49 Disaster Recovery endpoints.
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
    """Fixture providing TestClient backed by an isolated temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "dr_api_test.db"
        init_database(test_db_path)

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "dr_api_test.db")

        with TestClient(app) as client:
            yield client, tmpdir


def test_disaster_recovery_api_flow(client_with_db):
    client, tmpdir = client_with_db

    # Login as Superintendent
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "superintendent", "password": "Superintendent@AIIA2026"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create snapshot
    snapshot_payload = {
        "hospital_id": "aiia-delhi-central-001",
        "snapshot_type": "WAL_CHECKPOINT",
        "custom_destination_dir": str(Path(tmpdir) / "api_snapshots"),
    }
    resp = client.post("/api/v1/disaster-recovery/snapshots", json=snapshot_payload, headers=headers)
    assert resp.status_code == 201
    snap_data = resp.json()
    snap_id = snap_data["snapshot_id"]
    assert snap_data["is_verified"] is True

    # 2. List snapshots
    list_resp = client.get("/api/v1/disaster-recovery/snapshots?hospital_id=aiia-delhi-central-001", headers=headers)
    assert list_resp.status_code == 200
    assert any(s["snapshot_id"] == snap_id for s in list_resp.json())

    # 3. Verify snapshot
    verify_resp = client.post(f"/api/v1/disaster-recovery/snapshots/{snap_id}/verify", headers=headers)
    assert verify_resp.status_code == 200
    assert verify_resp.json()["is_verified"] is True

    # 4. Execute recovery drill
    drill_payload = {
        "snapshot_id": snap_id,
        "drill_type": "PITR_INTEGRITY_CHECK",
    }
    drill_resp = client.post("/api/v1/disaster-recovery/drills", json=drill_payload, headers=headers)
    assert drill_resp.status_code == 201
    drill_data = drill_resp.json()
    assert drill_data["snapshot_id"] == snap_id
    assert drill_data["data_integrity_status"] == "VERIFIED_CORRECT"

    # 5. List drills
    drills_list = client.get(f"/api/v1/disaster-recovery/drills?snapshot_id={snap_id}", headers=headers)
    assert drills_list.status_code == 200
    assert len(drills_list.json()) >= 1
