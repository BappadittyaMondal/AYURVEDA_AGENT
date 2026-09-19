"""
Unit Tests for Shalya Tantra Yantra-Shastra Microsurgical Instruments & Operative Suite (Phase 32).
"""

import tempfile
from pathlib import Path
import pytest

from core.database import get_sqlite_connection, init_database
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.shalya_instruments import (
    get_instrument_by_code,
    initialize_shalya_tables,
    list_all_instruments,
    list_patient_operative_procedures,
    list_practitioner_yogya_assessments,
    record_operative_procedure,
    record_yogya_assessment,
)
from models.shalya_instruments import (
    AshtavidhaKarma,
    InstrumentClass,
    OperativeProcedureCreate,
    ParasurgicalModality,
    YantraCategory,
    YogyaAssessmentCreate,
    YogyaSimulationModel,
)


def get_fresh_db_with_patient():
    """Create isolated SQLite database with a seeded surgical patient in a safe temp directory."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_shalya_inst.db"
    init_database(db_path)
    conn = get_sqlite_connection(db_path)
    initialize_shalya_tables(conn)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("PAT-SURG-001", "aiia-delhi-central-001", "Mahavir", "Gupta", "1985-09-12", "MALE", "+919876543015", 1700000000)
    )
    return tmpdir, conn


def test_instrument_catalog_completeness():
    """Verify registry contains both blunt Yantras across 6 groups and sharp Shastras."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        instruments = list_all_instruments(conn)
        assert len(instruments) >= 12

        classes = {i.instrument_type for i in instruments}
        assert InstrumentClass.YANTRA in classes
        assert InstrumentClass.SHASTRA in classes

        categories = {i.category_group for i in instruments}
        assert YantraCategory.SVASTIKA in categories
        assert YantraCategory.SANDAMSHA in categories
        assert YantraCategory.TALA in categories
        assert YantraCategory.NADI in categories
        assert YantraCategory.SHALAKA in categories
        assert YantraCategory.UPAYANTRA in categories
        assert YantraCategory.SHASTRA in categories

        # Lookup single instrument
        scalpel = get_instrument_by_code("SHA-VRID-07", conn)
        assert "वृद्धिपत्र" in scalpel.sanskrit_name
        assert scalpel.instrument_type == InstrumentClass.SHASTRA
        assert "Chhedana" in scalpel.primary_action

        with pytest.raises(RecordNotFoundException):
            get_instrument_by_code("NON-EXISTENT-CODE", conn)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_yogya_simulation_competency_certified():
    """Verify high precision on classical simulation model certifies surgical competency."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = YogyaAssessmentCreate(
            practitioner_arn="ARN-NCISM-2015-8832",
            operative_karma_tested=AshtavidhaKarma.CHHEDANA,
            simulation_model_used=YogyaSimulationModel.PUSHPAPHALA,
            precision_score=92.0,
            tissue_handling_score=88.0,
            examiner_arn="ARN-NCISM-1998-0421"
        )
        res = record_yogya_assessment(conn, "aiia-delhi-central-001", req)

        assert res.assessment_id.startswith("yogya-")
        assert res.composite_score == 90.4
        assert res.overall_competency_certified is True
        assert "COMPETENCY CERTIFIED" in res.certification_verdict
    finally:
        conn.close()
        tmpdir.cleanup()


def test_yogya_simulation_competency_rejected():
    """Verify sub-threshold precision score (< 80.0) denies surgical competency."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = YogyaAssessmentCreate(
            practitioner_arn="ARN-NCISM-2015-8832",
            operative_karma_tested=AshtavidhaKarma.LEKHANA,
            simulation_model_used=YogyaSimulationModel.LEATHER_WITH_HAIR,
            precision_score=68.0,
            tissue_handling_score=72.0,
            examiner_arn="ARN-NCISM-1998-0421"
        )
        res = record_yogya_assessment(conn, "aiia-delhi-central-001", req)

        assert res.composite_score == 69.6
        assert res.overall_competency_certified is False
        assert "COMPETENCY NOT CERTIFIED" in res.certification_verdict
    finally:
        conn.close()
        tmpdir.cleanup()


def test_ashtavidha_operative_procedure_clean():
    """Verify clean Ashtavidha surgical procedure clears safety firewall."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = OperativeProcedureCreate(
            patient_id="PAT-SURG-001",
            operative_karma=AshtavidhaKarma.CHHEDANA,
            surgical_instruments_used=["SHA-VRID-07", "YAN-SAN-02"],
            anesthesia_or_sangyaharana="Local field infiltration with 1% Lignocaine",
            parasurgical_modality=ParasurgicalModality.NONE,
            operative_notes="Elliptical excision of benign lipomatous subcutaneous swelling on back",
            surgeon_arn="ARN-NCISM-2015-8832"
        )
        res = record_operative_procedure(conn, "aiia-delhi-central-001", req)

        assert res.procedure_id.startswith("op-")
        assert res.safety_firewall_cleared is True
        assert len(res.firewall_violations) == 0
    finally:
        conn.close()
        tmpdir.cleanup()


def test_kshara_karma_firewall_rejection():
    """Verify missing Amla neutralizer triggers Kshara Karma safety firewall violation."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = OperativeProcedureCreate(
            patient_id="PAT-SURG-001",
            operative_karma=AshtavidhaKarma.CHHEDANA,
            surgical_instruments_used=["YAN-NAD-04", "YAN-SHA-05"],
            anesthesia_or_sangyaharana="Pudendal block & local infiltration",
            parasurgical_modality=ParasurgicalModality.KSHARA_KARMA,
            has_amla_neutralizer_ready=False,  # VIOLATION!
            operative_notes="Pratisaraniya Teekshna Kshara application to 3rd degree internal hemorrhoid",
            surgeon_arn="ARN-NCISM-2015-8832"
        )
        res = record_operative_procedure(conn, "aiia-delhi-central-001", req)

        assert res.safety_firewall_cleared is False
        assert len(res.firewall_violations) == 1
        assert "Amla neutralizing agent" in res.firewall_violations[0]
    finally:
        conn.close()
        tmpdir.cleanup()


def test_agni_karma_firewall_rejection():
    """Verify active bleeding diathesis triggers Agni Karma safety firewall violation."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = OperativeProcedureCreate(
            patient_id="PAT-SURG-001",
            operative_karma=AshtavidhaKarma.BHEDANA,
            surgical_instruments_used=["SHA-VRID-07"],
            anesthesia_or_sangyaharana="Topical cooling & local spray",
            parasurgical_modality=ParasurgicalModality.AGNI_KARMA,
            patient_has_active_bleeding_diathesis=True,  # VIOLATION!
            operative_notes="Direct thermal Agnikarma for chronic heel calcaneal spur pain",
            surgeon_arn="ARN-NCISM-2015-8832"
        )
        res = record_operative_procedure(conn, "aiia-delhi-central-001", req)

        assert res.safety_firewall_cleared is False
        assert len(res.firewall_violations) == 1
        assert "Active bleeding diathesis / Raktapitta" in res.firewall_violations[0]
    finally:
        conn.close()
        tmpdir.cleanup()


def test_patient_surgical_history_retrieval():
    """Verify historical operative procedures and Yogya assessments are retrievable."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Create procedure
        op_req = OperativeProcedureCreate(
            patient_id="PAT-SURG-001",
            operative_karma=AshtavidhaKarma.BHEDANA,
            surgical_instruments_used=["SHA-VRID-07", "SHA-KUSH-09"],
            anesthesia_or_sangyaharana="Local infiltration",
            parasurgical_modality=ParasurgicalModality.NONE,
            operative_notes="Incision and drainage of gluteal abscess",
            surgeon_arn="ARN-NCISM-2015-8832"
        )
        record_operative_procedure(conn, "aiia-delhi-central-001", op_req)

        op_hist = list_patient_operative_procedures("PAT-SURG-001", conn)
        assert len(op_hist) == 1

        # Create Yogya assessment
        yogya_req = YogyaAssessmentCreate(
            practitioner_arn="ARN-NCISM-2015-8832",
            operative_karma_tested=AshtavidhaKarma.SEEVANA,
            simulation_model_used=YogyaSimulationModel.THICK_LINEN_LEATHER,
            precision_score=88.0,
            tissue_handling_score=85.0,
            examiner_arn="ARN-NCISM-1998-0421"
        )
        record_yogya_assessment(conn, "aiia-delhi-central-001", yogya_req)

        yogya_hist = list_practitioner_yogya_assessments("ARN-NCISM-2015-8832", conn)
        assert len(yogya_hist) == 1
    finally:
        conn.close()
        tmpdir.cleanup()
