"""
tests/phase43/test_edge_sync_engine.py - Unit tests for Phase 43 Offline-First Edge Node Sync engine.
"""

import pytest
from core.database import get_sqlite_connection, init_database
from models.schemas import UserResponse
from core.security import ClinicalRole
from models.edge_sync import (
    FacilityType,
    ReplicationOp,
    SyncStatus,
    EdgeNodeRegisterReq,
    QueueSyncItemReq,
    SyncBatchReconciliationReq,
)
from core.edge_sync import (
    register_edge_node,
    get_edge_node,
    queue_edge_replication_item,
    reconcile_edge_sync_batch,
    get_edge_node_queue,
)


@pytest.fixture
def conn():
    init_database()
    connection = get_sqlite_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM replication_sync_queue WHERE node_id LIKE 'NODE-TRIBAL-%' OR node_id LIKE 'NODE-RURAL-%';")
    cursor.execute("DELETE FROM edge_node_registries WHERE node_id LIKE 'NODE-TRIBAL-%' OR node_id LIKE 'NODE-RURAL-%';")
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def rmp_user():
    return UserResponse(
        user_id="user-physician-001",
        hospital_id="aiia-delhi-central-001",
        username="physician_rmp",
        full_name="Dr. Ananya Sen",
        arn="ARN-NCISM-2015-8832",
        role=ClinicalRole.PHYSICIAN_RMP,
        is_active=True,
        created_at=1700000000
    )


def test_edge_node_registration_and_retrieval(conn, rmp_user):
    req = EdgeNodeRegisterReq(
        node_id="NODE-RURAL-ALWAR-01",
        hospital_id="aiia-delhi-central-001",
        facility_name="Alwar Rural Ayush Health & Wellness Centre",
        facility_type=FacilityType.AYUSH_HW_CENTRE,
        sync_passkey="AlwarClinicSyncKey#2026"
    )
    node = register_edge_node(req, current_user=rmp_user, conn=conn)
    assert node.node_id == "NODE-RURAL-ALWAR-01"
    assert node.is_online is True

    fetched = get_edge_node("NODE-RURAL-ALWAR-01", conn=conn)
    assert fetched is not None
    assert fetched.facility_name == "Alwar Rural Ayush Health & Wellness Centre"


def test_queue_replication_and_batch_reconciliation(conn, rmp_user):
    # 1. Register Node
    node_req = EdgeNodeRegisterReq(
        node_id="NODE-TRIBAL-BASTAR-01",
        hospital_id="aiia-delhi-central-001",
        facility_name="Bastar Tribal Mobile Unit",
        facility_type=FacilityType.TRIBAL_OUTREACH_CLINIC,
        sync_passkey="BastarPassKey99@"
    )
    register_edge_node(node_req, current_user=rmp_user, conn=conn)

    # 2. Queue single mutation item
    q_req = QueueSyncItemReq(
        node_id="NODE-TRIBAL-BASTAR-01",
        entity_table="patients",
        record_id="pat-bastar-001",
        operation_type=ReplicationOp.INSERT,
        payload={"first_name": "Somaru", "gender": "MALE"},
        vector_clock_counter=1
    )
    q_rec = queue_edge_replication_item(q_req, conn=conn)
    assert q_rec.queue_id.startswith("sq-")
    assert q_rec.sync_status == SyncStatus.PENDING

    # 3. Batch Reconciliation
    batch_items = [
        QueueSyncItemReq(
            node_id="NODE-TRIBAL-BASTAR-01",
            entity_table="prakriti_assessments",
            record_id="prak-bastar-001",
            operation_type=ReplicationOp.INSERT,
            payload={"prakriti": "Vata-Kapha"},
            vector_clock_counter=1
        ),
        QueueSyncItemReq(
            node_id="NODE-TRIBAL-BASTAR-01",
            entity_table="patients",
            record_id="pat-bastar-001",
            operation_type=ReplicationOp.UPDATE,
            payload={"first_name": "Somaru", "contact_phone": "+919811000000"},
            vector_clock_counter=2
        )
    ]
    batch_req = SyncBatchReconciliationReq(
        node_id="NODE-TRIBAL-BASTAR-01",
        sync_passkey="BastarPassKey99@",
        items=batch_items
    )
    batch_resp = reconcile_edge_sync_batch(batch_req, conn=conn)
    assert batch_resp.total_received == 2
    assert batch_resp.applied_count >= 1

    history = get_edge_node_queue("NODE-TRIBAL-BASTAR-01", limit=10, conn=conn)
    assert len(history) >= 3
