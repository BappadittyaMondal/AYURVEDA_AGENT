"""
api/v1/disaster_recovery.py - REST API endpoints for Phase 49 Disaster Recovery & Automated Backup Verifier.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, require_role
from core.security import ClinicalRole
from models.disaster_recovery import (
    BackupSnapshotCreate,
    BackupSnapshotResponse,
    RecoveryDrillCreate,
    RecoveryDrillResponse,
)
from core.disaster_recovery import (
    create_backup_snapshot,
    verify_snapshot_integrity,
    execute_recovery_drill,
    list_snapshots,
    list_drills,
    DisasterRecoveryError,
)

router = APIRouter(prefix="/disaster-recovery", tags=["Disaster Recovery & Backup Verifier"])


@router.post(
    "/snapshots",
    response_model=BackupSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create consistent SQLite WAL backup snapshot",
)
def create_snapshot_endpoint(
    payload: BackupSnapshotCreate,
    current_user: UserResponse = Depends(require_role(ClinicalRole.SUPERINTENDENT)),
):
    try:
        return create_backup_snapshot(payload, current_user)
    except DisasterRecoveryError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/snapshots",
    response_model=List[BackupSnapshotResponse],
    summary="List database backup snapshots",
)
def list_snapshots_endpoint(
    hospital_id: Optional[str] = Query(None, description="Filter by hospital ID"),
    current_user: UserResponse = Depends(get_current_user),
):
    return list_snapshots(hospital_id=hospital_id)


@router.post(
    "/snapshots/{snapshot_id}/verify",
    response_model=BackupSnapshotResponse,
    summary="Verify cryptographic SHA-256 integrity of snapshot on disk",
)
def verify_snapshot_endpoint(
    snapshot_id: str,
    current_user: UserResponse = Depends(require_role(ClinicalRole.SUPERINTENDENT)),
):
    try:
        return verify_snapshot_integrity(snapshot_id, current_user)
    except DisasterRecoveryError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/drills",
    response_model=RecoveryDrillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute automated disaster recovery / PITR integrity drill",
)
def execute_drill_endpoint(
    payload: RecoveryDrillCreate,
    current_user: UserResponse = Depends(require_role(ClinicalRole.SUPERINTENDENT)),
):
    try:
        return execute_recovery_drill(payload, current_user)
    except DisasterRecoveryError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/drills",
    response_model=List[RecoveryDrillResponse],
    summary="List recovery drill records",
)
def list_drills_endpoint(
    snapshot_id: Optional[str] = Query(None, description="Filter by target snapshot ID"),
    current_user: UserResponse = Depends(get_current_user),
):
    return list_drills(snapshot_id=snapshot_id)
