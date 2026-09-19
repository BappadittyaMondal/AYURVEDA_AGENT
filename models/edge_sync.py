"""
models/edge_sync.py - Data models for Phase 43: Offline-First Edge Node Sync & Rural PHC Resiliency.
Tables 92 & 93: edge_node_registries, replication_sync_queue.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class FacilityType(str, Enum):
    RURAL_PHC = "RURAL_PRIMARY_HEALTH_CENTRE"
    AYUSH_HW_CENTRE = "AYUSH_HEALTH_WELLNESS_CENTRE"
    MOBILE_TELEMEDICINE_VAN = "MOBILE_TELEMEDICINE_VAN"
    TRIBAL_OUTREACH_CLINIC = "TRIBAL_OUTREACH_CLINIC"


class ReplicationOp(str, Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class SyncStatus(str, Enum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    CONFLICT_RESOLVED = "CONFLICT_RESOLVED"
    FAILED = "FAILED"


class EdgeNodeRegisterReq(BaseModel):
    node_id: str = Field(..., description="Unique hardware/node ID of rural clinic appliance")
    hospital_id: str = Field(..., description="Parent hospital tenant ID")
    facility_name: str = Field(..., description="Name of rural facility")
    facility_type: FacilityType = Field(..., description="Institutional facility classification")
    sync_passkey: str = Field(..., min_length=8, description="Cryptographic mutual authentication passkey")


class EdgeNodeRecord(BaseModel):
    node_id: str
    hospital_id: str
    facility_name: str
    facility_type: FacilityType
    last_sync_timestamp: Optional[int]
    is_online: bool
    created_at: int


class QueueSyncItemReq(BaseModel):
    node_id: str
    entity_table: str
    record_id: str
    operation_type: ReplicationOp
    payload: Dict[str, Any]
    vector_clock_counter: int = Field(1, ge=1)


class SyncQueueItemRecord(BaseModel):
    queue_id: str
    node_id: str
    entity_table: str
    record_id: str
    operation_type: ReplicationOp
    payload: Dict[str, Any]
    vector_clock_counter: int
    sync_status: SyncStatus
    queued_at: int
    synced_at: Optional[int]


class SyncBatchReconciliationReq(BaseModel):
    node_id: str
    sync_passkey: str
    items: List[QueueSyncItemReq]


class SyncBatchReconciliationResponse(BaseModel):
    node_id: str
    total_received: int
    applied_count: int
    conflict_resolved_count: int
    failed_count: int
    sync_timestamp: int
