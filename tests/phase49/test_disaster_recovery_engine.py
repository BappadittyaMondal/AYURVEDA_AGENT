"""
tests/phase49/test_disaster_recovery_engine.py - Unit tests for Phase 49 Disaster Recovery & Backup Verifier engine.
"""

import os
import pytest
from core.database import get_sqlite_connection, init_database
from models.schemas import UserResponse
from core.security import ClinicalRole
from models.disaster_recovery import (
    SnapshotType,
    DrillType,
    IntegrityStatus,
    BackupSnapshotCreate,
    RecoveryDrillCreate,
)
from core.disaster_recovery import (
    create_backup_snapshot,
    verify_snapshot_integrity,
    execute_recovery_drill,
    list_snapshots,
    list_drills,
    DisasterRecoveryError,
)


@pytest.fixture
def superintendent_user():
    return UserResponse(
        user_id="user-superintendent-001",
        hospital_id="aiia-delhi-central-001",
        username="superintendent",
        full_name="Prof. Dr. V. Sharma",
        arn="ARN-NCISM-1998-0421",
        role=ClinicalRole.SUPERINTENDENT,
        is_active=True,
        created_at=1700000000
    )


@pytest.fixture
def conn():
    init_database()
    connection = get_sqlite_connection()
    yield connection
    connection.close()


def test_backup_snapshot_creation_and_integrity_check(conn, superintendent_user):
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        custom_dir = os.path.join(tmp_dir, "backups")
        snapshot_req = BackupSnapshotCreate(
            hospital_id="aiia-delhi-central-001",
            snapshot_type=SnapshotType.WAL_CHECKPOINT,
            custom_destination_dir=custom_dir,
        )

        # 1. Create backup snapshot
        snapshot_resp = create_backup_snapshot(snapshot_req, superintendent_user)
        assert snapshot_resp.snapshot_id.startswith("snap-")
        assert snapshot_resp.hospital_id == "aiia-delhi-central-001"
        assert snapshot_resp.is_verified is True
        assert os.path.exists(snapshot_resp.file_path)
        assert snapshot_resp.file_size_bytes > 0
        assert len(snapshot_resp.sha256_checksum) == 64

        # 2. Verify snapshot integrity
        verified = verify_snapshot_integrity(snapshot_resp.snapshot_id, superintendent_user)
        assert verified.is_verified is True
        assert verified.sha256_checksum == snapshot_resp.sha256_checksum

        # 3. Listing snapshots
        snaps = list_snapshots("aiia-delhi-central-001")
        assert any(s.snapshot_id == snapshot_resp.snapshot_id for s in snaps)


def test_recovery_drill_execution(conn, superintendent_user):
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        custom_dir = os.path.join(tmp_dir, "drill_backups")
        snapshot_req = BackupSnapshotCreate(
            hospital_id="aiia-delhi-central-001",
            snapshot_type=SnapshotType.FULL_COLD_BACKUP,
            custom_destination_dir=custom_dir,
        )
        snapshot = create_backup_snapshot(snapshot_req, superintendent_user)

        drill_req = RecoveryDrillCreate(
            snapshot_id=snapshot.snapshot_id,
            drill_type=DrillType.PITR_INTEGRITY_CHECK,
        )

        drill = execute_recovery_drill(drill_req, superintendent_user)
    assert drill.drill_id.startswith("drill-")
    assert drill.snapshot_id == snapshot.snapshot_id
    assert drill.data_integrity_status == IntegrityStatus.VERIFIED_CORRECT
    assert drill.recovery_time_seconds >= 0.0

    drills = list_drills(snapshot.snapshot_id)
    assert len(drills) >= 1
    assert drills[0].drill_id == drill.drill_id


def test_recovery_drill_nonexistent_snapshot(conn, superintendent_user):
    with pytest.raises(DisasterRecoveryError):
        execute_recovery_drill(
            RecoveryDrillCreate(
                snapshot_id="snap-nonexistent-999",
                drill_type=DrillType.DR_FAILOVER_TEST,
            ),
            superintendent_user
        )
