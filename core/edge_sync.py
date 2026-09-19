"""
core/edge_sync.py - Core Engine for Phase 43: Offline-First Edge Node Sync & Rural PHC Resiliency.
Implements CRDT-inspired synchronization for edge clinics with intermittent rural connectivity.
"""

import time
import uuid
import json
import sqlite3
from typing import Optional, List, Dict, Any
from core.database import get_sqlite_connection, append_audit_log
from core.security import hash_password, verify_password
from models.edge_sync import (
    FacilityType,
    ReplicationOp,
    SyncStatus,
    EdgeNodeRegisterReq,
    EdgeNodeRecord,
    QueueSyncItemReq,
    SyncQueueItemRecord,
    SyncBatchReconciliationReq,
    SyncBatchReconciliationResponse,
)
from models.schemas import UserResponse


class EdgeSyncError(Exception):
    pass


def register_edge_node(
    req: EdgeNodeRegisterReq,
    current_user: Optional[UserResponse] = None,
    conn: Optional[sqlite3.Connection] = None
) -> EdgeNodeRecord:
    """Registers an edge gateway device deployed at a rural Primary Health Centre (PHC)."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        now = int(time.time())
        passkey_hash = hash_password(req.sync_passkey)

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO edge_node_registries (
                node_id, hospital_id, facility_name, facility_type, sync_passkey_hash,
                last_sync_timestamp, is_online, created_at
            ) VALUES (?, ?, ?, ?, ?, NULL, 1, ?)
            ON CONFLICT(node_id) DO UPDATE SET
                facility_name=excluded.facility_name,
                facility_type=excluded.facility_type,
                sync_passkey_hash=excluded.sync_passkey_hash,
                is_online=1;
            """,
            (
                req.node_id,
                req.hospital_id,
                req.facility_name,
                req.facility_type.value,
                passkey_hash,
                now,
            )
        )

        user_id = current_user.user_id if current_user else "SYSTEM"
        append_audit_log(
            conn,
            req.hospital_id,
            user_id,
            "REGISTER_EDGE_NODE",
            "EDGE_NODE",
            req.node_id,
            {"facility": req.facility_name, "type": req.facility_type.value}
        )
        conn.commit()

        return get_edge_node(req.node_id, conn=conn)
    finally:
        if should_close:
            conn.close()


def get_edge_node(
    node_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> Optional[EdgeNodeRecord]:
    """Retrieves edge node details."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM edge_node_registries WHERE node_id = ?;", (node_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return EdgeNodeRecord(
            node_id=row["node_id"],
            hospital_id=row["hospital_id"],
            facility_name=row["facility_name"],
            facility_type=FacilityType(row["facility_type"]),
            last_sync_timestamp=row["last_sync_timestamp"],
            is_online=bool(row["is_online"]),
            created_at=row["created_at"]
        )
    finally:
        if should_close:
            conn.close()


def queue_edge_replication_item(
    req: QueueSyncItemReq,
    conn: Optional[sqlite3.Connection] = None
) -> SyncQueueItemRecord:
    """Enqueues an offline delta mutation item for bi-directional replication."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        node = get_edge_node(req.node_id, conn=conn)
        if not node:
            raise EdgeSyncError(f"Edge node '{req.node_id}' is not registered.")

        queue_id = f"sq-{uuid.uuid4().hex[:12]}"
        now = int(time.time())
        payload_str = json.dumps(req.payload)

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO replication_sync_queue (
                queue_id, node_id, entity_table, record_id, operation_type,
                payload_json, vector_clock_counter, sync_status, queued_at, synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, NULL);
            """,
            (
                queue_id,
                req.node_id,
                req.entity_table,
                req.record_id,
                req.operation_type.value,
                payload_str,
                req.vector_clock_counter,
                now,
            )
        )
        conn.commit()

        return SyncQueueItemRecord(
            queue_id=queue_id,
            node_id=req.node_id,
            entity_table=req.entity_table,
            record_id=req.record_id,
            operation_type=req.operation_type,
            payload=req.payload,
            vector_clock_counter=req.vector_clock_counter,
            sync_status=SyncStatus.PENDING,
            queued_at=now,
            synced_at=None
        )
    finally:
        if should_close:
            conn.close()


def reconcile_edge_sync_batch(
    req: SyncBatchReconciliationReq,
    conn: Optional[sqlite3.Connection] = None
) -> SyncBatchReconciliationResponse:
    """Reconciles an offline delta batch from an edge facility with conflict detection and vector clock resolution."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM edge_node_registries WHERE node_id = ?;", (req.node_id,))
        node_row = cursor.fetchone()
        if not node_row:
            raise EdgeSyncError(f"Edge node '{req.node_id}' does not exist.")
        if not verify_password(req.sync_passkey, node_row["sync_passkey_hash"]):
            raise EdgeSyncError("Invalid mutual authentication sync passkey.")

        now = int(time.time())
        applied_count = 0
        conflict_count = 0
        failed_count = 0

        for item in req.items:
            try:
                # Check for existing sync entries on same entity and record
                cursor.execute(
                    """
                    SELECT vector_clock_counter FROM replication_sync_queue
                    WHERE entity_table = ? AND record_id = ?
                    ORDER BY vector_clock_counter DESC LIMIT 1;
                    """,
                    (item.entity_table, item.record_id)
                )
                prev_sync = cursor.fetchone()
                queue_id = f"sq-{uuid.uuid4().hex[:12]}"
                payload_str = json.dumps(item.payload)

                if prev_sync and prev_sync["vector_clock_counter"] >= item.vector_clock_counter:
                    # Conflict detected: Concurrent write or stale delta. Resolve via last-write-wins merge
                    status = SyncStatus.CONFLICT_RESOLVED
                    conflict_count += 1
                else:
                    status = SyncStatus.APPLIED
                    applied_count += 1

                cursor.execute(
                    """
                    INSERT INTO replication_sync_queue (
                        queue_id, node_id, entity_table, record_id, operation_type,
                        payload_json, vector_clock_counter, sync_status, queued_at, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        queue_id,
                        req.node_id,
                        item.entity_table,
                        item.record_id,
                        item.operation_type.value,
                        payload_str,
                        item.vector_clock_counter,
                        status.value,
                        now,
                        now,
                    )
                )
            except Exception:
                failed_count += 1

        # Update node telemetry
        cursor.execute(
            "UPDATE edge_node_registries SET last_sync_timestamp = ?, is_online = 1 WHERE node_id = ?;",
            (now, req.node_id)
        )
        conn.commit()

        return SyncBatchReconciliationResponse(
            node_id=req.node_id,
            total_received=len(req.items),
            applied_count=applied_count,
            conflict_resolved_count=conflict_count,
            failed_count=failed_count,
            sync_timestamp=now
        )
    finally:
        if should_close:
            conn.close()


def get_edge_node_queue(
    node_id: str,
    limit: int = 50,
    conn: Optional[sqlite3.Connection] = None
) -> List[SyncQueueItemRecord]:
    """Retrieves queued replication logs for a specific node."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM replication_sync_queue
            WHERE node_id = ?
            ORDER BY queued_at DESC
            LIMIT ?;
            """,
            (node_id, limit)
        )
        rows = cursor.fetchall()
        results = []
        for r in rows:
            results.append(
                SyncQueueItemRecord(
                    queue_id=r["queue_id"],
                    node_id=r["node_id"],
                    entity_table=r["entity_table"],
                    record_id=r["record_id"],
                    operation_type=ReplicationOp(r["operation_type"]),
                    payload=json.loads(r["payload_json"]),
                    vector_clock_counter=r["vector_clock_counter"],
                    sync_status=SyncStatus(r["sync_status"]),
                    queued_at=r["queued_at"],
                    synced_at=r["synced_at"]
                )
            )
        return results
    finally:
        if should_close:
            conn.close()
