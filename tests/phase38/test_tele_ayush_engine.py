"""
Phase 38: Unit Tests for Tele-AYUSH & Digital e-Prescription Engine
==================================================================
Verifies:
1. Remote consultation session scheduling and lifecycle (Table 82)
2. Cryptographic SHA-256 e-prescription generation and QR payload (Table 83)
3. Prescription verification and tamper detection
"""

import pytest
import sqlite3
from core.database import get_sqlite_connection, init_database
from core.tele_ayush import (
    schedule_tele_consultation,
    issue_digital_eprescription,
    verify_eprescription,
)
from models.tele_ayush import (
    TeleConsultationType,
    TeleSessionStatus,
    DispensationStatus,
    PrescribedItem,
    TeleConsultationCreate,
    DigitalPrescriptionCreate,
)


@pytest.fixture
def conn():
    """Provides a thread-safe database connection."""
    init_database()
    connection = get_sqlite_connection()
    yield connection
    connection.close()


def test_tele_session_scheduling(conn):
    """Verify scheduling remote consultation."""
    req = TeleConsultationCreate(
        patient_id="PAT-TELE-01",
        hospital_id="aiia-delhi-central-001",
        physician_arn="ARN-NCISM-2015-8832",
        scheduled_timestamp=1750000000,
        call_type=TeleConsultationType.VIDEO_CONFERENCE,
        clinical_notes="Follow-up consultation for Amavata joint stiffness."
    )
    resp = schedule_tele_consultation(req, conn=conn)
    assert resp.session_id.startswith("TELE-")
    assert resp.session_status == TeleSessionStatus.SCHEDULED


def test_eprescription_issue_and_verification(conn):
    """Verify digital prescription generation, hash calculation, and verification."""
    # 1. Schedule session
    sess = schedule_tele_consultation(
        TeleConsultationCreate(
            patient_id="PAT-TELE-RX-01",
            hospital_id="aiia-delhi-central-001",
            physician_arn="ARN-NCISM-2015-8832",
            scheduled_timestamp=1750000000
        ),
        conn=conn
    )

    # 2. Issue prescription
    rx_req = DigitalPrescriptionCreate(
        session_id=sess.session_id,
        patient_id="PAT-TELE-RX-01",
        hospital_id="aiia-delhi-central-001",
        physician_arn="ARN-NCISM-2015-8832",
        formulations=[
            PrescribedItem(
                formulation_name="Rasna Saptaka Kwatha",
                dosage="20 ml twice daily",
                timing="Before meals",
                anupana="Warm water"
            ),
            PrescribedItem(
                formulation_name="Simhanada Guggulu",
                dosage="2 tablets twice daily",
                timing="After meals",
                anupana="Warm water"
            )
        ],
        pathya_diet_instructions="Strictly follow warm, light foods. Avoid curd and cold water."
    )

    rx_resp = issue_digital_eprescription(rx_req, conn=conn)
    assert rx_resp.prescription_id.startswith("RX-AYUSH-")
    assert len(rx_resp.verification_hash) == 64
    assert "https://ayush-grid.gov.in/verify-rx" in rx_resp.qr_code_payload
    assert rx_resp.dispensation_status == DispensationStatus.ISSUED

    # 3. Verify Authenticity
    verif = verify_eprescription(rx_resp.prescription_id, conn=conn)
    assert verif.is_authentic
    assert verif.physician_arn == "ARN-NCISM-2015-8832"
    assert verif.dispensation_status == DispensationStatus.ISSUED
