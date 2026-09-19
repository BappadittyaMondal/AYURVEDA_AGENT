"""
Unit Tests for Agada Tantra, Visha Chikitsa & Environmental Toxicology Engine (Phase 28).
"""

import tempfile
from pathlib import Path
import pytest

from core.database import get_sqlite_connection, init_database
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.agada_tantra import (
    get_visha_profile,
    initialize_agada_tables,
    list_all_vishas,
    list_dushi_visha_assessments,
    list_visha_emergency_admissions,
    record_dushi_visha_assessment,
    record_visha_emergency_admission,
)
from models.agada_tantra import (
    DushiVishaAssessmentCreate,
    EnvenomationSyndrome,
    ToxicEmergencyTriage,
    VishaCategory,
    VishaEmergencyAdmissionCreate,
)


def get_fresh_db_with_patient():
    """Create isolated SQLite database with a seeded emergency patient in a safe temp directory."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_agada.db"
    init_database(db_path)
    conn = get_sqlite_connection(db_path)
    initialize_agada_tables(conn)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("PAT-TOX-001", "aiia-delhi-central-001", "Ramesh", "Yadav", "1985-04-12", "MALE", "+919876543008", 1700000000)
    )
    return tmpdir, conn


def test_visha_catalog_completeness():
    """Verify registry contains toxins across all 4 categories with modern antidote mappings."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        vishas = list_all_vishas(conn)
        assert len(vishas) >= 8

        categories_found = {v.visha_category for v in vishas}
        assert VishaCategory.STHAVARA in categories_found
        assert VishaCategory.JANGAMA in categories_found
        assert VishaCategory.DUSHI_VISHA in categories_found
        assert VishaCategory.GARA_VISHA in categories_found

        # Verify specific profiles
        vatsanabha = get_visha_profile("VISHA-STH-01", conn)
        assert "Vatsanabha" in vatsanabha.sanskrit_name
        assert any("Hridaya-Avarana" in u for u in vatsanabha.upakrama_indications)
        assert "Atropine" in vatsanabha.modern_antidote_mapping

        darvikara = get_visha_profile("VISHA-JAN-01", conn)
        assert darvikara.visha_category == VishaCategory.JANGAMA
        assert "Anti-Snake Venom" in darvikara.modern_antidote_mapping
    finally:
        conn.close()
        tmpdir.cleanup()


def test_snakebite_darvikara_neurotoxic_emergency_triage():
    """Verify neurotoxic elapid bite triggers CRITICAL_TOXIC_EMERGENCY and 10 vials ASV."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        adm_data = VishaEmergencyAdmissionCreate(
            patient_id="PAT-TOX-001",
            suspected_visha_code="VISHA-JAN-01",
            envenomation_syndrome=EnvenomationSyndrome.DARVIKARA_NEUROTOXIC,
            bite_to_admission_minutes=45,
            twenty_minute_wbct_clotted=True,
            neurotoxic_signs_present=True,  # Ptosis & bulbar weakness!
            hemotoxic_signs_present=False,
            practitioner_arn="AY-DL-2024-998811",
        )
        res = record_visha_emergency_admission(conn, "aiia-delhi-central-001", adm_data)
        assert res.episode_id.startswith("tox-")
        assert res.triage_level == ToxicEmergencyTriage.CRITICAL_TOXIC_EMERGENCY
        assert res.asv_indicated_vials == 10
        assert "10 vials Polyvalent Anti-Snake Venom" in res.emergency_escalation_protocol
        assert any("Arishta-Bandhana" in u for u in res.upakramas_executed)
        assert "Maricha" in res.cardioprotective_hridaya_avarana
        assert "Bilvadi Agada" in "".join(res.adjunctive_ayurvedic_agadas)

        # Verify history retrieval
        history = list_visha_emergency_admissions("PAT-TOX-001", conn)
        assert len(history) == 1
        assert history[0].episode_id == res.episode_id
    finally:
        conn.close()
        tmpdir.cleanup()


def test_snakebite_mandala_hemotoxic_coagulopathy_triage():
    """Verify 20WBCT failure to clot triggers hemotoxic emergency and 10 vials ASV."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        adm_data = VishaEmergencyAdmissionCreate(
            patient_id="PAT-TOX-001",
            suspected_visha_code="VISHA-JAN-02",
            envenomation_syndrome=EnvenomationSyndrome.MANDALA_HEMOTOXIC,
            bite_to_admission_minutes=60,
            twenty_minute_wbct_clotted=False,  # Un-clotted blood / VICC!
            neurotoxic_signs_present=False,
            hemotoxic_signs_present=True,
            practitioner_arn="AY-DL-2024-998811",
        )
        res = record_visha_emergency_admission(conn, "aiia-delhi-central-001", adm_data)
        assert res.triage_level == ToxicEmergencyTriage.CRITICAL_TOXIC_EMERGENCY
        assert res.asv_indicated_vials == 10
        assert res.emergency_escalation_protocol is not None
    finally:
        conn.close()
        tmpdir.cleanup()


def test_non_venomous_dry_bite_observation():
    """Verify dry bite with normal 20WBCT is graded NON_ENCLOSING_DISCHARGED with 0 ASV vials."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        adm_data = VishaEmergencyAdmissionCreate(
            patient_id="PAT-TOX-001",
            suspected_visha_code="VISHA-JAN-01",
            envenomation_syndrome=EnvenomationSyndrome.NON_VENOMOUS,
            bite_to_admission_minutes=120,
            twenty_minute_wbct_clotted=True,
            neurotoxic_signs_present=False,
            hemotoxic_signs_present=False,
            practitioner_arn="AY-DL-2024-998811",
        )
        res = record_visha_emergency_admission(conn, "aiia-delhi-central-001", adm_data)
        assert res.triage_level == ToxicEmergencyTriage.NON_ENCLOSING_DISCHARGED
        assert res.asv_indicated_vials == 0
        assert res.emergency_escalation_protocol is None
    finally:
        conn.close()
        tmpdir.cleanup()


def test_dushi_visha_chronic_assessment():
    """Verify chronic Dushi Visha staging and Dooshivishari Agada prescription."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        dushi_data = DushiVishaAssessmentCreate(
            patient_id="PAT-TOX-001",
            suspected_toxin_source="Agricultural organophosphate and heavy metal groundwater residue",
            chronicity_months=18,
            reported_manifestations=["Recurrent urticarial rashes (Kotha)", "Chronic fatigue", "Anorexia"],
            aggravating_triggers=["Cloudy sky (Megha-Kala)", "Rainy weather (Varsha Ritu)"],
            practitioner_arn="AY-DL-2024-998811",
        )
        res = record_dushi_visha_assessment(conn, "aiia-delhi-central-001", dushi_data)
        assert res.log_id.startswith("dushi-")
        assert "Advanced Deep-Tissue Dushi Visha" in res.dushi_visha_stage
        assert res.dooshivishari_agada_prescribed is True
        assert any("Dooshivishari Agada" in p for p in res.clinical_management_plan)
        assert "Swedana" in res.shodhana_protocol

        # Retrieve history
        history = list_dushi_visha_assessments("PAT-TOX-001", conn)
        assert len(history) == 1
        assert history[0].log_id == res.log_id
    finally:
        conn.close()
        tmpdir.cleanup()
