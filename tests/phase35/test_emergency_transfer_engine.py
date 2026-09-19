"""
Phase 35: Unit Tests for Emergency Break-Glass & Acute Transfer Engine (NABH COP.6)
==================================================================================
Verifies:
1. Physiological deterioration threshold detection
2. Bilingual SBAR report generation
3. Break-glass event persistence and state lockdown (Table 76)
4. Critical care transfer execution and ICU handover (Table 77)
"""

import pytest
import sqlite3
from core.database import get_sqlite_connection, init_database
from core.emergency_transfer import (
    evaluate_vital_instability,
    generate_sbar_report,
    trigger_emergency_break_glass,
    execute_critical_care_transfer,
    get_break_glass_event,
)
from models.emergency_transfer import (
    EmergencyTriggerReason,
    BreakGlassStatus,
    VitalSignsTelemetry,
    EmergencyBreakGlassRequest,
    CriticalCareTransferRequest,
)


@pytest.fixture
def conn():
    """Provides a thread-safe database connection."""
    init_database()
    connection = get_sqlite_connection()
    yield connection
    connection.close()


def test_vital_instability_evaluation():
    """Verify detection of critical vital signs thresholds."""
    stable_vitals = VitalSignsTelemetry(
        systolic_bp=120,
        diastolic_bp=80,
        heart_rate_bpm=72,
        respiratory_rate_bpm=16,
        spo2_percentage=98.0,
        glasgow_coma_scale=15
    )
    assert len(evaluate_vital_instability(stable_vitals)) == 0

    critical_vitals = VitalSignsTelemetry(
        systolic_bp=80,      # Hypotension
        diastolic_bp=50,
        heart_rate_bpm=135,  # Tachycardia
        respiratory_rate_bpm=34, # Tachypnea
        spo2_percentage=86.0, # Hypoxia
        glasgow_coma_scale=8  # Coma / loss of airway
    )
    flags = evaluate_vital_instability(critical_vitals)
    assert len(flags) >= 4
    assert any("HEMODYNAMIC DECOMPENSATION" in f for f in flags)
    assert any("RESPIRATORY FAILURE" in f for f in flags)
    assert any("COMA" in f for f in flags)


def test_sbar_bilingual_report_generation():
    """Verify SBAR structure and English/Hindi bilingual narrative."""
    vitals = VitalSignsTelemetry(
        systolic_bp=75,
        diastolic_bp=45,
        heart_rate_bpm=128,
        respiratory_rate_bpm=28,
        spo2_percentage=88.0,
        glasgow_coma_scale=11
    )
    sbar = generate_sbar_report(
        patient_id="PAT-EMERG-001",
        hospital_id="aiia-delhi-central-001",
        trigger=EmergencyTriggerReason.CARDIOGENIC_SHOCK,
        vitals=vitals,
        physician_arn="ARN-NCISM-2015-8832"
    )
    assert "shock" in sbar.situation_english.lower()
    assert "शॉक" in sbar.situation_hindi
    assert len(sbar.recommendation_allopathic_resuscitation) >= 4
    assert sbar.assessment_acute_syndrome == "CARDIOGENIC_SHOCK"
    assert sbar.attending_ayush_physician_arn == "ARN-NCISM-2015-8832"


def test_break_glass_and_transfer_lifecycle(conn):
    """Verify full break-glass trigger, database persistence, and ICU transfer execution."""
    vitals = VitalSignsTelemetry(
        systolic_bp=82,
        diastolic_bp=50,
        heart_rate_bpm=125,
        respiratory_rate_bpm=32,
        spo2_percentage=89.0,
        glasgow_coma_scale=10
    )
    req = EmergencyBreakGlassRequest(
        patient_id="PAT-BREAKGLASS-TEST-01",
        hospital_id="aiia-delhi-central-001",
        trigger_reason=EmergencyTriggerReason.CARDIOGENIC_SHOCK,
        vitals=vitals,
        initiating_user_id="user-physician-001",
        initiating_role="PHYSICIAN_RMP",
        physician_arn="ARN-NCISM-2015-8832",
        emergency_icu_destination="AIIMS Critical Care Unit"
    )

    resp = trigger_emergency_break_glass(req, conn=conn)
    assert resp.event_id.startswith("EVENT-BREAKGLASS-")
    assert resp.state_lockdown_enforced
    assert resp.status == BreakGlassStatus.BREAK_GLASS_TRIGGERED
    assert resp.sbar_handover.situation_english != ""

    # Fetch event
    event = get_break_glass_event(resp.event_id, conn=conn)
    assert event.event_id == resp.event_id
    assert event.patient_id == "PAT-BREAKGLASS-TEST-01"

    # Execute ICU Transfer
    transfer_req = CriticalCareTransferRequest(
        event_id=resp.event_id,
        allopathic_physician_notified="Dr. Rajesh Kumar, MD, AIIMS Emergency",
        receiving_hospital_name="AIIMS New Delhi",
        receiving_doctor_name="Dr. Rajesh Kumar",
        handover_signed_by_arn="ARN-NCISM-2015-8832",
        clinical_notes="Ambulance dispatched. Patient intubated and stabilized en route."
    )
    transfer_resp = execute_critical_care_transfer(transfer_req, conn=conn)
    assert transfer_resp.transfer_id.startswith("TRANSFER-ICU-")
    assert transfer_resp.ambulance_service_called
    assert transfer_resp.medical_superintendent_alerted
    assert transfer_resp.receiving_hospital_name == "AIIMS New Delhi"

    # Confirm event status updated to TRANSFERRED_TO_ICU
    updated_event = get_break_glass_event(resp.event_id, conn=conn)
    assert updated_event.status == BreakGlassStatus.TRANSFERRED_TO_ICU
