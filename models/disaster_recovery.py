"""
models/disaster_recovery.py - Pydantic models for Phase 49 Disaster Recovery & Automated Backup Verifier.
Tables 104 & 105: backup_snapshots_catalog, recovery_drill_records.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from enum import Enum


class SnapshotType(str, Enum):
    WAL_CHECKPOINT = "WAL_CHECKPOINT"
    FULL_COLD_BACKUP = "FULL_COLD_BACKUP"
    INCREMENTAL_ARCHIVE = "INCREMENTAL_ARCHIVE"


class DrillType(str, Enum):
    SIMULATED_RECOVERY = "SIMULATED_RECOVERY"
    DR_FAILOVER_TEST = "DR_FAILOVER_TEST"
    PITR_INTEGRITY_CHECK = "PITR_INTEGRITY_CHECK"


class IntegrityStatus(str, Enum):
    VERIFIED_CORRECT = "VERIFIED_CORRECT"
    CORRUPTED = "CORRUPTED"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"


class BackupSnapshotCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hospital_id: str = Field(..., description="Hospital ID for backup scope")
    snapshot_type: SnapshotType = Field(default=SnapshotType.WAL_CHECKPOINT)
    custom_destination_dir: Optional[str] = Field(None, description="Optional custom directory for snapshot file")


class BackupSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: str
    hospital_id: str
    snapshot_type: SnapshotType
    file_path: str
    file_size_bytes: int
    sha256_checksum: str
    is_verified: bool
    created_at: int


class RecoveryDrillCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: str = Field(..., description="Target snapshot ID for drill")
    drill_type: DrillType = Field(default=DrillType.PITR_INTEGRITY_CHECK)


class RecoveryDrillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    drill_id: str
    snapshot_id: str
    drill_type: DrillType
    recovery_time_seconds: float
    data_integrity_status: IntegrityStatus
    simulated_by_user_id: str
    executed_at: int
