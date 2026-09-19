"""
Unit Tests for Upakarma & Bahya Parimarjana Therapy Matrix Engine (Phase 20).
"""

import tempfile
from pathlib import Path
import pytest

from core.database import get_sqlite_connection, init_database
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.upakarma import (
    SEED_UPAKARMA_REGISTRY,
    get_therapy_profile,
    initialize_upakarma_tables,
    list_all_therapies,
    list_patient_upakarma_sessions,
    log_upakarma_session,
    screen_pre_session_safety,
)
from models.upakarma import (
    PreSessionScreeningRequest,
    UpakarmaModality,
    UpakarmaSessionCreate,
)


def get_fresh_db_with_patient():
    """Create isolated SQLite database with a seeded patient in a safe temp directory."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_upakarma.db"
    init_database(db_path)
    conn = get_sqlite_connection(db_path)
    initialize_upakarma_tables(conn)

    # Seed patient
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("PAT-UP-001", "aiia-delhi-central-001", "Meenakshi", "Pillai", "1985-09-12", "FEMALE", "+919876543222", 1700000000)
    )
    return tmpdir, conn


def test_upakarma_catalog_completeness():
    """Verify registry contains all 12 classical external therapy modalities."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        therapies = list_all_therapies(conn)
        assert len(therapies) >= 12

        # Check key therapies
        abhyanga = get_therapy_profile("UPAKARMA-ABHYANGA", conn)
        assert abhyanga.modality_code == UpakarmaModality.ABHYANGA
        assert abhyanga.target_temperature_min_c == 38.0
        assert abhyanga.max_safe_temperature_c == 42.0

        shirodhara = get_therapy_profile("UPAKARMA-SHIRODHARA-TAILA", conn)
        assert shirodhara.modality_code == UpakarmaModality.SHIRODHARA_TAILA
        assert shirodhara.max_safe_temperature_c == 40.0

        takradhara = get_therapy_profile("UPAKARMA-TAKRADHARA", conn)
        assert takradhara.modality_code == UpakarmaModality.TAKRADHARA
        assert takradhara.target_temperature_min_c == 25.0  # Ambient cool
    finally:
        conn.close()
        tmpdir.cleanup()


def test_pre_session_thermal_safety_burn_check():
    """Verify thermodynamic compliance blocks excessive temperatures with burn hazard alerts."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Bashpa Sweda max safe temp is 45.0°C. Test with 49.0°C (Burn risk!)
        req_burn = PreSessionScreeningRequest(
            patient_id="PAT-UP-001",
            therapy_id="UPAKARMA-BASHPA-SWEDA",
            proposed_temperature_c=49.0,
            patient_conditions=[],
        )
        res_burn = screen_pre_session_safety(req_burn, conn)
        assert res_burn.is_safe_to_proceed is False
        assert res_burn.temperature_compliance == "EXCESSIVE_RISK_OF_BURNS"
        assert any("Burn Hazard" in flag for flag in res_burn.contraindication_flags)

        # Test sub-therapeutic temperature (32°C for Bashpa Sweda min 40°C)
        req_sub = PreSessionScreeningRequest(
            patient_id="PAT-UP-001",
            therapy_id="UPAKARMA-BASHPA-SWEDA",
            proposed_temperature_c=32.0,
            patient_conditions=[],
        )
        res_sub = screen_pre_session_safety(req_sub, conn)
        assert res_sub.is_safe_to_proceed is False
        assert res_sub.temperature_compliance == "SUB_THERAPEUTIC"

        # Test compliant temperature (42.0°C)
        req_ok = PreSessionScreeningRequest(
            patient_id="PAT-UP-001",
            therapy_id="UPAKARMA-BASHPA-SWEDA",
            proposed_temperature_c=42.0,
            patient_conditions=[],
        )
        res_ok = screen_pre_session_safety(req_ok, conn)
        assert res_ok.is_safe_to_proceed is True
        assert res_ok.temperature_compliance == "COMPLIANT"
    finally:
        conn.close()
        tmpdir.cleanup()


def test_pre_session_contraindication_matching():
    """Verify screening cross-references patient active conditions against modality contraindications."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Pregnancy (Garbhini) contraindicated in Bashpa Sweda
        req = PreSessionScreeningRequest(
            patient_id="PAT-UP-001",
            therapy_id="UPAKARMA-BASHPA-SWEDA",
            proposed_temperature_c=41.5,
            patient_conditions=["Garbhini (24 weeks pregnancy)"],
        )
        res = screen_pre_session_safety(req, conn)
        assert res.is_safe_to_proceed is False
        assert any("Pregnancy" in flag for flag in res.contraindication_flags)

        # Acute Fever (Nava Jwara) contraindicated in Shirodhara
        req_jwara = PreSessionScreeningRequest(
            patient_id="PAT-UP-001",
            therapy_id="UPAKARMA-SHIRODHARA-TAILA",
            proposed_temperature_c=38.0,
            patient_conditions=["Acute viral Nava Jwara", "Headache"],
        )
        res_jwara = screen_pre_session_safety(req_jwara, conn)
        assert res_jwara.is_safe_to_proceed is False
        assert any("Jwara" in flag for flag in res_jwara.contraindication_flags)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_pre_session_ama_gating_snigdha_sweda_blocked():
    """Verify that AGI score >= 1.80 blocks Snigdha Sweda and recommends Ruksha Sweda."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = PreSessionScreeningRequest(
            patient_id="PAT-UP-001",
            therapy_id="UPAKARMA-PATRA-PINDA",  # Snigdha Sweda
            proposed_temperature_c=43.0,
            patient_conditions=["Amavata with severe joint stiffness"],
            pre_op_agi_score=1.90,  # High Ama!
        )
        res = screen_pre_session_safety(req, conn)
        assert res.is_safe_to_proceed is False
        assert any("Sama Avastha Firewall" in flag for flag in res.contraindication_flags)
        assert any("Ruksha Sweda" in flag for flag in res.contraindication_flags)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_log_upakarma_session_success():
    """Verify successful logging and retrieval of an Upakarma session."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        session_data = UpakarmaSessionCreate(
            patient_id="PAT-UP-001",
            therapy_id="UPAKARMA-ABHYANGA",
            medium_used="Mahanarayana Taila",
            operating_temperature_c=39.5,
            duration_minutes=45,
            pre_vitals_bp="122/82",
            post_vitals_bp="118/78",
            therapist_id="THERAPIST-001",
            clinical_notes="Excellent relaxation, muscle tone softened",
        )

        record = log_upakarma_session(session_data, "aiia-delhi-central-001", conn)
        assert record.session_id.startswith("SES-UP-ABHYANGA-")
        assert record.operating_temperature_c == 39.5
        assert len(record.adverse_events) == 0

        # Retrieve patient sessions
        history = list_patient_upakarma_sessions("PAT-UP-001", conn)
        assert len(history) == 1
        assert history[0].session_id == record.session_id
    finally:
        conn.close()
        tmpdir.cleanup()


def test_log_upakarma_session_severe_burn_violation():
    """Verify that extreme temperature (> max_safe + 2°C) triggers ThermalBurnViolation."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Shirodhara max safe is 40.0°C. Test with 45.0°C!
        dangerous_session = UpakarmaSessionCreate(
            patient_id="PAT-UP-001",
            therapy_id="UPAKARMA-SHIRODHARA-TAILA",
            medium_used="Ksheerabala Taila",
            operating_temperature_c=45.0,  # Scalding risk over head!
            duration_minutes=45,
            pre_vitals_bp="120/80",
            post_vitals_bp="120/80",
            therapist_id="THERAPIST-001",
        )

        with pytest.raises(ClinicalGovernanceException) as exc_info:
            log_upakarma_session(dangerous_session, "aiia-delhi-central-001", conn)
        assert "Severe Thermal Violation" in str(exc_info.value)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_shirodhara_hydrokinetics_validation():
    """Verify warning flags when Shirodhara stream height or flow rate deviates from canonical standards."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Standard height is 8-10 cm. Test with 32.0 cm (too high, causes cranial impact jarring)
        session_data = UpakarmaSessionCreate(
            patient_id="PAT-UP-001",
            therapy_id="UPAKARMA-SHIRODHARA-TAILA",
            medium_used="Ksheerabala Taila",
            operating_temperature_c=38.5,
            duration_minutes=45,
            flow_rate_ml_sec=20.0,
            height_cm=32.0,  # Extreme height!
            pre_vitals_bp="120/80",
            post_vitals_bp="118/78",
            therapist_id="THERAPIST-001",
        )

        record = log_upakarma_session(session_data, "aiia-delhi-central-001", conn)
        assert any("Hydrokinetic anomaly" in e for e in record.adverse_events)
    finally:
        conn.close()
        tmpdir.cleanup()
