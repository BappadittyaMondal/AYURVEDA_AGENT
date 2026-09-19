"""
Unit Tests for Vajikarana Tantra, Shukra Dushti & Reproductive Eugenics Engine (Phase 30).
"""

import tempfile
from pathlib import Path
import pytest

from core.database import get_sqlite_connection, init_database
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.vajikarana_tantra import (
    evaluate_semen_analysis,
    get_shukra_dushti_by_code,
    initialize_vajikarana_tables,
    list_all_shukra_dushtis,
    list_patient_semen_analyses,
    list_patient_vajikarana_prescriptions,
    prescribe_vajikarana_protocol,
)
from models.vajikarana_tantra import (
    KlaibyaType,
    SemenAnalysisCreate,
    ShukraDushtiType,
    VajikaranaActionClass,
    VajikaranaPrescriptionCreate,
    ViscosityGrade,
)


def get_fresh_db_with_patient():
    """Create isolated SQLite database with a seeded patient in a safe temp directory."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_vajikarana.db"
    init_database(db_path)
    conn = get_sqlite_connection(db_path)
    initialize_vajikarana_tables(conn)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("PAT-VAJI-001", "aiia-delhi-central-001", "Arjun", "Pandey", "1992-05-14", "MALE", "+919876543011", 1700000000)
    )
    return tmpdir, conn


def test_shukra_dushti_catalog_completeness():
    """Verify registry contains all 8 classical Shukra Dushtis with WHO correlates."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        dushtis = list_all_shukra_dushtis(conn)
        assert len(dushtis) == 8

        codes = [d.dushti_code for d in dushtis]
        assert "DUSHTI-VAT-01" in codes
        assert "DUSHTI-PIT-02" in codes
        assert "DUSHTI-KAPH-03" in codes
        assert "DUSHTI-RAKT-04" in codes
        assert "DUSHTI-KUN-05" in codes
        assert "DUSHTI-GRAN-06" in codes
        assert "DUSHTI-PUTI-07" in codes
        assert "DUSHTI-KSHI-08" in codes

        # Test single item lookup
        vataja = get_shukra_dushti_by_code("DUSHTI-VAT-01", conn)
        assert "वातज" in vataja.sanskrit_name
        assert any("Phenila" in c for c in vataja.classical_characteristics)
        assert "Asthenozoospermia" in vataja.who_semen_correlate

        kaphaja = get_shukra_dushti_by_code("DUSHTI-KAPH-03", conn)
        assert any("Picchila" in c for c in kaphaja.classical_characteristics)
        assert "Hyperviscosity" in kaphaja.who_semen_correlate

        with pytest.raises(RecordNotFoundException):
            get_shukra_dushti_by_code("DUSHTI-INVALID-99", conn)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_semen_analysis_shuddha_shukra():
    """Verify normative semen parameters yield Shuddha Shukra and high fertility score."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        data = SemenAnalysisCreate(
            patient_id="PAT-VAJI-001",
            volume_ml=3.2,
            ph_level=7.6,
            liquefaction_time_min=25,
            viscosity_grade=ViscosityGrade.NORMAL,
            sperm_concentration_million_ml=68.0,
            total_motility_percent=65.0,
            progressive_motility_percent=52.0,
            normal_morphology_percent=7.5,
            vitality_percent=80.0,
            pus_cells_per_hpf=1,
            erythrocytes_present=False,
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        res = evaluate_semen_analysis(conn, "aiia-delhi-central-001", data)

        assert res.analysis_id.startswith("sem-")
        assert res.primary_shukra_dushti == ShukraDushtiType.SHUDDHA_SHUKRA
        assert res.shukra_shuddhi_score >= 90.0
        assert "Normozoospermia" in res.who_diagnostic_interpretation[0]
        assert "Shuddha Shukra Sampat" in res.fertility_prognosis
    finally:
        conn.close()
        tmpdir.cleanup()


def test_semen_analysis_kaphaja_picchila():
    """Verify delayed liquefaction and hyperviscosity trigger Kaphaja Shukra Dushti."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        data = SemenAnalysisCreate(
            patient_id="PAT-VAJI-001",
            volume_ml=2.8,
            ph_level=7.4,
            liquefaction_time_min=75,                  # > 60 min liquefaction failure!
            viscosity_grade=ViscosityGrade.HIGH_PICCHILA, # Hyperviscous!
            sperm_concentration_million_ml=42.0,
            total_motility_percent=38.0,
            progressive_motility_percent=26.0,
            normal_morphology_percent=5.0,
            vitality_percent=68.0,
            pus_cells_per_hpf=2,
            erythrocytes_present=False,
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        res = evaluate_semen_analysis(conn, "aiia-delhi-central-001", data)

        assert res.primary_shukra_dushti == ShukraDushtiType.KAPHAJA
        assert any("Hyperviscosity" in f or "Delayed Liquefaction" in f for f in res.who_diagnostic_interpretation)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_semen_analysis_puti_puya_leukocytospermia():
    """Verify pus cells >= 5 / HPF trigger Puti-Puya Shukra Dushti."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        data = SemenAnalysisCreate(
            patient_id="PAT-VAJI-001",
            volume_ml=2.2,
            ph_level=8.2,
            liquefaction_time_min=30,
            viscosity_grade=ViscosityGrade.NORMAL,
            sperm_concentration_million_ml=35.0,
            total_motility_percent=32.0,
            progressive_motility_percent=22.0,
            normal_morphology_percent=4.5,
            vitality_percent=55.0,
            pus_cells_per_hpf=12,                     # Pyospermia / infection!
            erythrocytes_present=False,
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        res = evaluate_semen_analysis(conn, "aiia-delhi-central-001", data)

        assert res.primary_shukra_dushti == ShukraDushtiType.PUTI_PUYA
        assert any("Leukocytospermia" in f for f in res.who_diagnostic_interpretation)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_semen_analysis_raktaja_hematospermia():
    """Verify presence of erythrocytes triggers Raktaja Shukra Dushti."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        data = SemenAnalysisCreate(
            patient_id="PAT-VAJI-001",
            volume_ml=1.8,
            ph_level=7.5,
            liquefaction_time_min=20,
            viscosity_grade=ViscosityGrade.NORMAL,
            sperm_concentration_million_ml=28.0,
            total_motility_percent=40.0,
            progressive_motility_percent=32.0,
            normal_morphology_percent=5.0,
            vitality_percent=60.0,
            pus_cells_per_hpf=3,
            erythrocytes_present=True,                # Hematospermia!
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        res = evaluate_semen_analysis(conn, "aiia-delhi-central-001", data)

        assert res.primary_shukra_dushti == ShukraDushtiType.RAKTAJA
        assert any("Hematospermia" in f for f in res.who_diagnostic_interpretation)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_semen_analysis_kshina_oligozoospermia():
    """Verify low concentration < 15 M/mL triggers Kshina Shukra Dushti."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        data = SemenAnalysisCreate(
            patient_id="PAT-VAJI-001",
            volume_ml=1.1,                             # Hypospermia
            ph_level=7.4,
            liquefaction_time_min=25,
            viscosity_grade=ViscosityGrade.NORMAL,
            sperm_concentration_million_ml=7.5,       # Oligozoospermia!
            total_motility_percent=25.0,
            progressive_motility_percent=18.0,
            normal_morphology_percent=3.0,
            vitality_percent=45.0,
            pus_cells_per_hpf=1,
            erythrocytes_present=False,
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        res = evaluate_semen_analysis(conn, "aiia-delhi-central-001", data)

        assert res.primary_shukra_dushti == ShukraDushtiType.KSHINA
        assert any("Oligozoospermia" in f for f in res.who_diagnostic_interpretation)
        assert res.shukra_shuddhi_score < 50.0
    finally:
        conn.close()
        tmpdir.cleanup()


def test_vajikarana_prescription_cleared():
    """Verify patient with completed Shodhana and no Ama receives cleared Vajikarana prescription."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = VajikaranaPrescriptionCreate(
            patient_id="PAT-VAJI-001",
            klaibya_type=KlaibyaType.JARASAMBHAVA,
            target_action_class=VajikaranaActionClass.SHUKRA_JANANA_PRAVARTAKA,
            pre_shodhana_completed=True,
            has_active_ama=False,
            partner_conception_intent=True,
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        res = prescribe_vajikarana_protocol(conn, "aiia-delhi-central-001", req)

        assert res.protocol_id.startswith("vaji-")
        assert res.safety_firewall_cleared is True
        assert len(res.contraindication_warnings) == 0
        assert any("Vanari Kalpa" in f for f in res.prescribed_classical_formulations)
        assert any("Go-Ksheera" in p for p in res.dietary_lifestyle_pathya)
        assert "Somanasya" in res.psychosexual_counseling_notes
    finally:
        conn.close()
        tmpdir.cleanup()


def test_vajikarana_prescription_firewall_rejection():
    """Verify missing Shodhana and active Ama trigger safety contraindication warnings."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = VajikaranaPrescriptionCreate(
            patient_id="PAT-VAJI-001",
            klaibya_type=KlaibyaType.SHUKRAKSHAYAJA,
            target_action_class=VajikaranaActionClass.SHUKRA_JANANA,
            pre_shodhana_completed=False,  # Violation!
            has_active_ama=True,           # Violation!
            partner_conception_intent=True,
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        res = prescribe_vajikarana_protocol(conn, "aiia-delhi-central-001", req)

        assert res.safety_firewall_cleared is False
        assert len(res.contraindication_warnings) == 2
        warn_str = " ".join(res.contraindication_warnings)
        assert "Prior Panchakarma bio-cleansing" in warn_str
        assert "Active Sama Avastha" in warn_str
    finally:
        conn.close()
        tmpdir.cleanup()


def test_patient_vajikarana_history_retrieval():
    """Verify historical semen analyses and prescriptions are retrieved per patient."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Create semen analysis
        data = SemenAnalysisCreate(
            patient_id="PAT-VAJI-001",
            volume_ml=2.5,
            ph_level=7.5,
            liquefaction_time_min=30,
            viscosity_grade=ViscosityGrade.NORMAL,
            sperm_concentration_million_ml=40.0,
            total_motility_percent=55.0,
            progressive_motility_percent=42.0,
            normal_morphology_percent=6.0,
            vitality_percent=72.0,
            pus_cells_per_hpf=1,
            erythrocytes_present=False,
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        evaluate_semen_analysis(conn, "aiia-delhi-central-001", data)

        semen_hist = list_patient_semen_analyses("PAT-VAJI-001", conn)
        assert len(semen_hist) == 1

        # Create prescription
        req = VajikaranaPrescriptionCreate(
            patient_id="PAT-VAJI-001",
            klaibya_type=KlaibyaType.DHVAJABHANGAJA,
            target_action_class=VajikaranaActionClass.SHUKRA_JANANA,
            pre_shodhana_completed=True,
            has_active_ama=False,
            partner_conception_intent=True,
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        prescribe_vajikarana_protocol(conn, "aiia-delhi-central-001", req)

        rx_hist = list_patient_vajikarana_prescriptions("PAT-VAJI-001", conn)
        assert len(rx_hist) == 1
    finally:
        conn.close()
        tmpdir.cleanup()
