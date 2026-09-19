"""
Unit Tests for Marma Sharira, Traumatological Interventions & Marma Chikitsa Engine (Phase 31).
"""

import tempfile
from pathlib import Path
import pytest

from core.database import get_sqlite_connection, init_database
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.marma_sharira import (
    get_marma_by_code,
    initialize_marma_tables,
    list_all_marmas,
    list_patient_marma_chikitsa_sessions,
    list_patient_marma_trauma_admissions,
    record_marma_chikitsa_session,
    triage_marma_trauma_admission,
)
from models.marma_sharira import (
    MarmaChikitsaSessionCreate,
    MarmaParinama,
    MarmaRachana,
    MarmaRegion,
    MarmaTraumaEmergencyCreate,
    MarmaTraumaTriage,
    StimulationModality,
)


def get_fresh_db_with_patient():
    """Create isolated SQLite database with a seeded patient in a safe temp directory."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_marma.db"
    init_database(db_path)
    conn = get_sqlite_connection(db_path)
    initialize_marma_tables(conn)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("PAT-MARMA-001", "aiia-delhi-central-001", "Bhimsen", "Verma", "1988-02-10", "MALE", "+919876543013", 1700000000)
    )
    return tmpdir, conn


def test_marma_catalog_completeness():
    """Verify registry contains representative Marmas across all Rachana and Parinama classes."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        marmas = list_all_marmas(conn)
        assert len(marmas) >= 12

        # Check all 5 Parinama classes
        parinamas = {m.parinama_prognosis for m in marmas}
        assert MarmaParinama.SADHYO_PRANAHARA in parinamas
        assert MarmaParinama.KALANTARA_PRANAHARA in parinamas
        assert MarmaParinama.VISHALYAGHNA in parinamas
        assert MarmaParinama.VAIKALYAKARA in parinamas
        assert MarmaParinama.RUJAKARA in parinamas

        # Check all 5 Rachana classes
        rachanas = {m.rachana_structure for m in marmas}
        assert MarmaRachana.MAMSA in rachanas
        assert MarmaRachana.SIRA in rachanas
        assert MarmaRachana.SNAYU in rachanas
        assert MarmaRachana.ASTHI in rachanas
        assert MarmaRachana.SANDHI in rachanas

        # Test single item lookup
        hridaya = get_marma_by_code("MARMA-HRID-01", conn)
        assert "हृदय" in hridaya.sanskrit_name
        assert hridaya.angula_dimension == 4.0
        assert "Mahamarma" in hridaya.cardinal_vulnerability

        sthapani = get_marma_by_code("MARMA-STHAP-04", conn)
        assert sthapani.parinama_prognosis == MarmaParinama.VISHALYAGHNA

        with pytest.raises(RecordNotFoundException):
            get_marma_by_code("MARMA-INVALID-99", conn)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_tri_marma_emergency_triage_firewall():
    """Verify acute trauma to Hridaya triggers CODE_RED_TRI_MARMA_CRITICAL."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        trauma_req = MarmaTraumaEmergencyCreate(
            patient_id="PAT-MARMA-001",
            injured_marma_code="MARMA-HRID-01",
            trauma_mechanism="Penetrating stab injury to anterior precordium",
            depth_penetration_mm=35.0,
            foreign_body_present=False,
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        res = triage_marma_trauma_admission(conn, "aiia-delhi-central-001", trauma_req)

        assert res.log_id.startswith("trauma-")
        assert res.tri_marma_involved is True
        assert res.triage_tier == MarmaTraumaTriage.CODE_RED_TRI_MARMA_CRITICAL
        assert "Level-1 ATLS" in res.emergency_resuscitation_protocol
        assert "Hridaya-Avarana" in res.emergency_resuscitation_protocol
    finally:
        conn.close()
        tmpdir.cleanup()


def test_vishalyaghna_extraction_firewall():
    """Verify lodged shrapnel in Sthapani triggers surgical extraction warning firewall."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        trauma_req = MarmaTraumaEmergencyCreate(
            patient_id="PAT-MARMA-001",
            injured_marma_code="MARMA-STHAP-04",
            trauma_mechanism="Penetrating shrapnel lodged in glabella",
            depth_penetration_mm=18.0,
            foreign_body_present=True,
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        res = triage_marma_trauma_admission(conn, "aiia-delhi-central-001", trauma_req)

        assert res.tri_marma_involved is False
        assert res.triage_tier == MarmaTraumaTriage.CODE_ORANGE_VISHALYAGHNA_SURGICAL
        assert res.surgical_extraction_warning is not None
        assert "DO NOT EXTRACT" in res.surgical_extraction_warning
        assert "Vayu to escape" in res.surgical_extraction_warning
    finally:
        conn.close()
        tmpdir.cleanup()


def test_vaikalyakara_trauma_triage():
    """Verify trauma to Janu knee joint triggers CODE_YELLOW_VAIKALYAKARA_URGENT."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        trauma_req = MarmaTraumaEmergencyCreate(
            patient_id="PAT-MARMA-001",
            injured_marma_code="MARMA-JANU-08",
            trauma_mechanism="Crush injury and hyperextension of knee in road accident",
            depth_penetration_mm=0.0,
            foreign_body_present=False,
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        res = triage_marma_trauma_admission(conn, "aiia-delhi-central-001", trauma_req)

        assert res.triage_tier == MarmaTraumaTriage.CODE_YELLOW_VAIKALYAKARA_URGENT
        assert "locomotor/anatomical disability" in res.emergency_resuscitation_protocol
    finally:
        conn.close()
        tmpdir.cleanup()


def test_rujakara_trauma_triage():
    """Verify injury to Gulpha ankle joint triggers CODE_GREEN_STABLE with pain management."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        trauma_req = MarmaTraumaEmergencyCreate(
            patient_id="PAT-MARMA-001",
            injured_marma_code="MARMA-GULP-10",
            trauma_mechanism="Severe ankle inversion sprain and ligamentous tear",
            depth_penetration_mm=0.0,
            foreign_body_present=False,
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        res = triage_marma_trauma_admission(conn, "aiia-delhi-central-001", trauma_req)

        assert res.triage_tier == MarmaTraumaTriage.CODE_GREEN_STABLE
        assert "Parisheka" in res.emergency_resuscitation_protocol
        assert "Bandhana" in res.emergency_resuscitation_protocol
    finally:
        conn.close()
        tmpdir.cleanup()


def test_marma_chikitsa_therapeutic_stimulation():
    """Verify therapeutic acupressure stimulation on Sthapani generates proper response."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = MarmaChikitsaSessionCreate(
            patient_id="PAT-MARMA-001",
            targeted_marma_code="MARMA-STHAP-04",
            stimulation_modality=StimulationModality.ANGULI_PIDANA,
            pressure_intensity_kg=1.0,
            cycles_count=18,
            clinical_objective="Alleviation of severe chronic insomnia and autonomic agitation",
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        res = record_marma_chikitsa_session(conn, "aiia-delhi-central-001", req)

        assert res.session_id.startswith("marmachik-")
        assert res.targeted_marma_code == "MARMA-STHAP-04"
        assert res.pressure_intensity_kg == 1.0
        assert "Pranic flow successfully stimulated" in res.immediate_response
        assert "Alleviation of Vata stagnation" in res.immediate_response
    finally:
        conn.close()
        tmpdir.cleanup()


def test_patient_marma_history_retrieval():
    """Verify historical Marma trauma admissions and Chikitsa sessions are retrievable."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Create trauma admission
        trauma_req = MarmaTraumaEmergencyCreate(
            patient_id="PAT-MARMA-001",
            injured_marma_code="MARMA-KURP-09",
            trauma_mechanism="Blunt contusion",
            depth_penetration_mm=0.0,
            foreign_body_present=False,
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        triage_marma_trauma_admission(conn, "aiia-delhi-central-001", trauma_req)

        trauma_hist = list_patient_marma_trauma_admissions("PAT-MARMA-001", conn)
        assert len(trauma_hist) == 1

        # Create Chikitsa session
        chik_req = MarmaChikitsaSessionCreate(
            patient_id="PAT-MARMA-001",
            targeted_marma_code="MARMA-JANU-08",
            stimulation_modality=StimulationModality.TAILA_ABHYANGA,
            pressure_intensity_kg=1.2,
            cycles_count=15,
            clinical_objective="Osteoarthritis knee pain relief",
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        record_marma_chikitsa_session(conn, "aiia-delhi-central-001", chik_req)

        chik_hist = list_patient_marma_chikitsa_sessions("PAT-MARMA-001", conn)
        assert len(chik_hist) == 1
    finally:
        conn.close()
        tmpdir.cleanup()
