"""
Unit Tests for Sattvavajaya Chikitsa, Manasa Roga & Mental Health CDSS Engine (Phase 23).
"""

import tempfile
from pathlib import Path
import pytest

from core.database import get_sqlite_connection, init_database
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.manasa_roga import (
    SEED_MANASA_ROGA_REGISTRY,
    create_sattvavajaya_prescription,
    get_disorder_profile,
    initialize_manasa_roga_tables,
    list_all_disorders,
    perform_manasa_assessment,
)
from models.manasa_roga import (
    CrisisRiskLevel,
    ManasaAssessmentCreateRequest,
    ManasaDisorderCode,
    SattvavajayaPrescriptionCreateRequest,
)


def get_fresh_db_with_patient():
    """Create isolated SQLite database with a seeded patient in a safe temp directory."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_manasa.db"
    init_database(db_path)
    conn = get_sqlite_connection(db_path)
    initialize_manasa_roga_tables(conn)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("PAT-MANASA-001", "aiia-delhi-central-001", "Rohit", "Deshmukh", "1991-03-12", "MALE", "+919876543111", 1700000000)
    )
    return tmpdir, conn


def test_manasa_roga_catalog_completeness():
    """Verify registry contains 9 classical psychiatric disorders with ICD-11 dual codes."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        disorders = list_all_disorders(conn)
        assert len(disorders) >= 9

        codes = {d.disorder_code for d in disorders}
        assert ManasaDisorderCode.UNMADA_VATAJA in codes
        assert ManasaDisorderCode.UNMADA_PITTAJA in codes
        assert ManasaDisorderCode.UNMADA_KAPHAJA in codes
        assert ManasaDisorderCode.APASMARA in codes
        assert ManasaDisorderCode.CHITTODVEGA in codes
        assert ManasaDisorderCode.AVASADA in codes
        assert ManasaDisorderCode.ATATTVABHINIVESHA in codes
        assert ManasaDisorderCode.MADATYAYA in codes

        chittodvega = get_disorder_profile("CHITTODVEGA", conn)
        assert "6B00" in chittodvega.icd11_mapping
        assert any("शङ्खपुष्पी" in m for m in chittodvega.medhya_rasayana)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_triguna_normalization_and_prajnaparadha_calculus():
    """Verify Triguna simplex normalization and Prajnaparadha Index (PPI) formula accuracy."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Raw scores: Sattva=20, Rajas=50, Tamas=30 (Total=100) -> s=0.2, r=0.5, t=0.3
        # Faculties: Dhi=4.0, Dhriti=3.0, Smriti=5.0 (Sum=12/30) -> Cognitive Deficit = 1 - 12/30 = 0.6
        # PPI = 100 * 0.6 * (0.5 + 0.3) = 100 * 0.6 * 0.8 = 48.0%
        req = ManasaAssessmentCreateRequest(
            patient_id="PAT-MANASA-001",
            disorder_code=ManasaDisorderCode.CHITTODVEGA,
            raw_sattva=20.0,
            raw_rajas=50.0,
            raw_tamas=30.0,
            dhi_score=4.0,
            dhriti_score=3.0,
            smriti_score=5.0,
            assessed_by_arn="AY-DL-2024-998811",
        )
        res = perform_manasa_assessment(req, "aiia-delhi-central-001", conn)
        assert res.triguna.sattva == 0.2
        assert res.triguna.rajas == 0.5
        assert res.triguna.tamas == 0.3
        assert res.prajnaparadha_index == 48.0
        assert res.crisis_risk_level == CrisisRiskLevel.LOW
    finally:
        conn.close()
        tmpdir.cleanup()


def test_suicidal_ideation_emergency_crisis_firewall():
    """Verify active suicidal ideation triggers CRITICAL_EMERGENCY and safety escalation."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = ManasaAssessmentCreateRequest(
            patient_id="PAT-MANASA-001",
            disorder_code=ManasaDisorderCode.AVASADA,
            raw_sattva=10.0,
            raw_rajas=20.0,
            raw_tamas=70.0,
            dhi_score=2.0,
            dhriti_score=1.0,
            smriti_score=3.0,
            has_suicidal_ideation=True,  # Severe crisis!
            assessed_by_arn="AY-DL-2024-998811",
        )
        res = perform_manasa_assessment(req, "aiia-delhi-central-001", conn)
        assert res.crisis_risk_level == CrisisRiskLevel.CRITICAL_EMERGENCY
        assert res.emergency_alert is not None
        assert "SUICIDE_FIREWALL" in res.emergency_alert
        assert "1-on-1 bedside surveillance" in res.emergency_alert
    finally:
        conn.close()
        tmpdir.cleanup()


def test_violent_mania_crisis_firewall():
    """Verify violent agitation in Pittaja Unmada triggers CRITICAL_EMERGENCY with safety restraint alert."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = ManasaAssessmentCreateRequest(
            patient_id="PAT-MANASA-001",
            disorder_code=ManasaDisorderCode.UNMADA_PITTAJA,
            raw_sattva=10.0,
            raw_rajas=80.0,
            raw_tamas=10.0,
            dhi_score=3.0,
            dhriti_score=1.0,
            smriti_score=4.0,
            has_violent_agitation=True,
            assessed_by_arn="AY-DL-2024-998811",
        )
        res = perform_manasa_assessment(req, "aiia-delhi-central-001", conn)
        assert res.crisis_risk_level == CrisisRiskLevel.CRITICAL_EMERGENCY
        assert res.emergency_alert is not None
        assert "VIOLENT_MANIA_FIREWALL" in res.emergency_alert
    finally:
        conn.close()
        tmpdir.cleanup()


def test_moderate_crisis_stratification():
    """Verify severe delusion or very high Prajnaparadha Index triggers MODERATE crisis."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = ManasaAssessmentCreateRequest(
            patient_id="PAT-MANASA-001",
            disorder_code=ManasaDisorderCode.ATATTVABHINIVESHA,
            raw_sattva=10.0,
            raw_rajas=50.0,
            raw_tamas=40.0,
            dhi_score=1.0,
            dhriti_score=1.0,
            smriti_score=2.0,  # Sum=4/30 -> Cog Deficit=0.867 -> PPI = 100 * 0.867 * 0.9 = 78.0%
            has_severe_delusion=True,
            assessed_by_arn="AY-DL-2024-998811",
        )
        res = perform_manasa_assessment(req, "aiia-delhi-central-001", conn)
        assert res.crisis_risk_level == CrisisRiskLevel.MODERATE
        assert res.prajnaparadha_index >= 70.0
    finally:
        conn.close()
        tmpdir.cleanup()


def test_trividha_sattvavajaya_prescription_synthesis():
    """Verify formulation of comprehensive Trividha Chikitsa (Daiva, Yukti Medhya, Sattvavajaya)."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # First create assessment
        assess_req = ManasaAssessmentCreateRequest(
            patient_id="PAT-MANASA-001",
            disorder_code=ManasaDisorderCode.CHITTODVEGA,
            raw_sattva=30.0,
            raw_rajas=50.0,
            raw_tamas=20.0,
            dhi_score=5.0,
            dhriti_score=4.0,
            smriti_score=6.0,
            assessed_by_arn="AY-DL-2024-998811",
        )
        assess_res = perform_manasa_assessment(assess_req, "aiia-delhi-central-001", conn)

        # Prescribe Trividha Chikitsa
        rx_req = SattvavajayaPrescriptionCreateRequest(
            assessment_id=assess_res.assessment_id,
            patient_id="PAT-MANASA-001",
            include_daivavyapashraya=True,
            include_yukti_medhya=True,
            include_sattvavajaya_cbt=True,
            prescribed_by_arn="AY-DL-2024-998811",
        )
        rx_res = create_sattvavajaya_prescription(rx_req, "aiia-delhi-central-001", conn)

        assert rx_res.prescription_id.startswith("RX-SATTVA-PAT-MANASA-001-")
        assert len(rx_res.daivavyapashraya_therapies) >= 3
        assert len(rx_res.yukti_medhya_rasayanas) >= 2
        assert any("शङ्खपुष्पी" in m for m in rx_res.yukti_medhya_rasayanas)
        assert len(rx_res.sattvavajaya_cbt_interventions) >= 4
        assert any("Mano-nigraha" in c for c in rx_res.sattvavajaya_cbt_interventions)
        assert len(rx_res.contraindicated_factors) >= 2

        # Verify persisted
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patient_sattvavajaya_prescriptions WHERE prescription_id = ?;", (rx_res.prescription_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["patient_id"] == "PAT-MANASA-001"
    finally:
        conn.close()
        tmpdir.cleanup()
