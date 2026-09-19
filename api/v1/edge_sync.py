"""
api/v1/edge_sync.py - API Endpoints for Phase 43: Offline-First Edge Node Sync & Rural PHC Resiliency.
"""

import sqlite3
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_current_user, get_db_session
from models.schemas import UserResponse
from models.edge_sync import (
    EdgeNodeRegisterReq,
    EdgeNodeRecord,
    QueueSyncItemReq,
    SyncQueueItemRecord,
    SyncBatchReconciliationReq,
    SyncBatchReconciliationResponse,
)
from core.edge_sync import (
    register_edge_node,
    get_edge_node,
    queue_edge_replication_item,
    reconcile_edge_sync_batch,
    get_edge_node_queue,
    EdgeSyncError,
)

router = APIRouter(prefix="/edge-sync", tags=["Phase 43: Offline-First Edge Node Sync & Rural PHC"])


@router.post(
    "/nodes",
    response_model=EdgeNodeRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Register a remote rural edge gateway node"
)
def register_node_endpoint(
    req: EdgeNodeRegisterReq,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
):
    return register_edge_node(req, current_user=current_user, conn=conn)


@router.get(
    "/nodes/{node_id}",
    response_model=EdgeNodeRecord,
    summary="Get registered edge node details"
)
def get_node_endpoint(
    node_id: str,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    node = get_edge_node(node_id, conn=conn)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found.")
    return node


@router.post(
    "/queue",
    response_model=SyncQueueItemRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Queue single mutation item for edge replication"
)
def queue_item_endpoint(
    req: QueueSyncItemReq,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return queue_edge_replication_item(req, conn=conn)
    except EdgeSyncError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/reconcile",
    response_model=SyncBatchReconciliationResponse,
    summary="Reconcile offline delta batch from rural edge node"
)
def reconcile_batch_endpoint(
    req: SyncBatchReconciliationReq,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return reconcile_edge_sync_batch(req, conn=conn)
    except EdgeSyncError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get(
    "/nodes/{node_id}/queue",
    response_model=List[SyncQueueItemRecord],
    summary="Get recent replication queue entries for an edge node"
)
def get_node_queue_endpoint(
    node_id: str,
    limit: int = 50,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    return get_edge_node_queue(node_id, limit=limit, conn=conn)
