"""
tests/phase47/test_opd_queue_engine.py - Unit tests for Phase 47 OPD Queue Optimization & Token Flow.
"""

import pytest
from core.database import get_sqlite_connection, init_database
from models.schemas import UserResponse
from core.security import ClinicalRole
from models.opd_queue import (
    PriorityTier,
    TokenStatus,
    OpdTokenCreate,
)
from core.opd_queue import (
    issue_opd_token,
    call_next_opd_token,
    complete_opd_consultation,
    get_department_queue_status,
)


@pytest.fixture
def conn():
    init_database()
    connection = get_sqlite_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO patients (
            patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("pat-opd-001", "aiia-delhi-central-001", "Dinesh", "Mishra", "1970-03-11", "MALE", "+919876540001", 1700000000)
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO patients (
            patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("pat-opd-002", "aiia-delhi-central-001", "Vidya", "Balan", "1995-12-05", "FEMALE", "+919876540002", 1700000000)
    )
    # Clean up test department
    cursor.execute("DELETE FROM consultation_time_audits WHERE token_id IN (SELECT token_id FROM opd_token_queues WHERE department = 'TEST_KAYACHIKITSA');")
    cursor.execute("DELETE FROM opd_token_queues WHERE department = 'TEST_KAYACHIKITSA';")
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


def test_priority_token_issuance_and_wait_time(conn, rmp_user):
    # Routine patient
    t1 = issue_opd_token(
        OpdTokenCreate(
            hospital_id="aiia-delhi-central-001",
            patient_id="pat-opd-001",
            department="TEST_KAYACHIKITSA",
            priority_tier=PriorityTier.ROUTINE_SAMANYA
        ),
        conn=conn
    )
    assert t1.token_number == 1
    assert t1.status == TokenStatus.WAITING

    # Emergency Tivra patient -> should have 0 wait time
    t2 = issue_opd_token(
        OpdTokenCreate(
            hospital_id="aiia-delhi-central-001",
            patient_id="pat-opd-002",
            department="TEST_KAYACHIKITSA",
            priority_tier=PriorityTier.EMERGENCY_TIVRA
        ),
        conn=conn
    )
    assert t2.token_number == 2
    assert t2.estimated_wait_minutes == 0


def test_triage_calling_order_and_consultation_completion(conn, rmp_user):
    # Routine patient issued first
    t1 = issue_opd_token(
        OpdTokenCreate(
            hospital_id="aiia-delhi-central-001",
            patient_id="pat-opd-001",
            department="TEST_KAYACHIKITSA",
            priority_tier=PriorityTier.ROUTINE_SAMANYA
        ),
        conn=conn
    )
    # Emergency Tivra patient issued second
    t2 = issue_opd_token(
        OpdTokenCreate(
            hospital_id="aiia-delhi-central-001",
            patient_id="pat-opd-002",
            department="TEST_KAYACHIKITSA",
            priority_tier=PriorityTier.EMERGENCY_TIVRA
        ),
        conn=conn
    )
    # Call next: Even though t1 was issued first, t2 is EMERGENCY_TIVRA and must be served FIRST!
    called_token = call_next_opd_token("TEST_KAYACHIKITSA", physician_arn="ARN-NCISM-2015-8832", conn=conn)
    assert called_token is not None
    assert called_token.token_number == 2  # The Emergency Tivra patient!
    assert called_token.status == TokenStatus.IN_CONSULTATION

    # Complete consultation
    audit = complete_opd_consultation(called_token.token_id, conn=conn)
    assert audit.token_id == called_token.token_id
    assert audit.duration_seconds is not None
    assert audit.efficiency_rating is not None
    assert audit.efficiency_rating > 0.0

    # Check status
    status = get_department_queue_status("TEST_KAYACHIKITSA", conn=conn)
    assert status.total_waiting == 1  # t1 is still waiting
    assert status.current_token_being_served is None  # t2 is completed
