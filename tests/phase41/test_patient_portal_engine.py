"""
tests/phase41/test_patient_portal_engine.py - Unit tests for Phase 41 Patient Portal core engine.
"""

import pytest
from core.database import get_sqlite_connection, init_database
from models.patient_portal import (
    PatientPortalAccountCreate,
    PatientPortalLoginRequest,
    PatientDailyLogCreate,
    BowelMovementType,
)
from core.patient_portal import (
    register_patient_portal_account,
    authenticate_patient_portal,
    record_patient_daily_log,
    get_patient_daily_logs,
    get_patient_health_summary,
    PatientPortalError,
)


@pytest.fixture
def conn():
    init_database()
    connection = get_sqlite_connection()
    # Seed a test patient in MPI
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO patients (
            patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("pat-portal-test-01", "aiia-delhi-central-001", "Devendra", "Joshi", "1988-06-20", "MALE", "+919811223344", 1700000000)
    )
    cursor.execute("DELETE FROM patient_portal_accounts WHERE phone_number = '+919811223344';")
    connection.commit()
    yield connection
    connection.close()


def test_portal_registration_and_authentication(conn):
    req = PatientPortalAccountCreate(
        patient_id="pat-portal-test-01",
        hospital_id="aiia-delhi-central-001",
        phone_number="+919811223344",
        password="SecurePatient@2026",
        abha_address="devendra.joshi@abdm"
    )
    acc = register_patient_portal_account(req, conn=conn)
    assert acc.account_id.startswith("acc-")
    assert acc.phone_number == "+919811223344"

    # Authenticate
    login_req = PatientPortalLoginRequest(
        phone_number="+919811223344",
        password="SecurePatient@2026"
    )
    auth_resp = authenticate_patient_portal(login_req, conn=conn)
    assert auth_resp.access_token is not None
    assert auth_resp.first_name == "Devendra"


def test_daily_log_and_doshic_warning_evaluation(conn):
    log_req = PatientDailyLogCreate(
        patient_id="pat-portal-test-01",
        hospital_id="aiia-delhi-central-001",
        log_date="2026-09-20",
        diet_adherence_score=60,
        pathya_followed_notes="Ate spicy fried street food",
        ahara_craving="Tikshna & Amla",
        bowel_movement_type=BowelMovementType.PITTA_LOOSE,
        sleep_duration_hours=5.5,
        stress_level=8
    )
    rec = record_patient_daily_log(log_req, conn=conn)
    assert rec.log_id.startswith("log-")
    assert rec.doshic_aggravation_warning is not None
    assert "Pitta/Manasika" in rec.doshic_aggravation_warning

    logs = get_patient_daily_logs("pat-portal-test-01", limit=5, conn=conn)
    assert len(logs) >= 1
    assert logs[0].log_id == rec.log_id


def test_health_summary_aggregation(conn):
    summary = get_patient_health_summary("pat-portal-test-01", conn=conn)
    assert summary.patient_id == "pat-portal-test-01"
    assert summary.full_name == "Devendra Joshi"
    assert "vata" in summary.prakriti
    assert summary.total_logs >= 1
