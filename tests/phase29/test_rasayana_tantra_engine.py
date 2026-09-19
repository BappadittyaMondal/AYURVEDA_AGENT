"""
Unit Tests for Rasayana Tantra, Jara Chikitsa & Longevity Medicine Engine (Phase 29).
"""

import tempfile
from pathlib import Path
import pytest

from core.database import get_sqlite_connection, init_database
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.rasayana_tantra import (
    admit_kuti_praveshika_episode,
    calculate_ojas_and_biological_age,
    determine_decadal_attribute_decay,
    get_rasayana_protocol_by_id,
    initialize_rasayana_tables,
    list_all_rasayana_protocols,
    list_kuti_praveshika_episodes,
    list_patient_ojas_evaluations,
)
from models.rasayana_tantra import (
    KutiPraveshikaAdmissionRequest,
    OjasEvaluationRequest,
    OjasStatus,
    RasayanaMode,
    RasayanaType,
)


def get_fresh_db_with_patient():
    """Create isolated SQLite database with a seeded patient in a safe temp directory."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_rasayana.db"
    init_database(db_path)
    conn = get_sqlite_connection(db_path)
    initialize_rasayana_tables(conn)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("PAT-RAS-001", "aiia-delhi-central-001", "Devavrata", "Acharya", "1970-08-15", "MALE", "+919876543009", 1700000000)
    )
    return tmpdir, conn


def test_rasayana_catalog_completeness():
    """Verify registry contains classical formulations across all key modalities."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        protocols = list_all_rasayana_protocols(conn)
        assert len(protocols) >= 8

        types_found = {p.rasayana_type for p in protocols}
        assert RasayanaType.KAMYA in types_found
        assert RasayanaType.NAIMITTIKA in types_found
        assert RasayanaType.MEDHYA in types_found
        assert RasayanaType.ACHARA in types_found

        # Test specific protocol details
        chyavan = get_rasayana_protocol_by_id("RAS-CHYAVAN-01", conn)
        assert "Chyavanaprasha" in chyavan.sanskrit_name
        assert "Amalaki (Emblica officinalis)" in chyavan.primary_ingredients[0]
        assert "Abhayayamalakiya" in chyavan.classical_reference

        medhya = get_rasayana_protocol_by_id("RAS-MEDHYA-06", conn)
        assert medhya.rasayana_type == RasayanaType.MEDHYA
        assert len(medhya.primary_ingredients) == 4  # Mandukaparni, Yashtimadhu, Guduchi, Shankhapushpi

        with pytest.raises(RecordNotFoundException):
            get_rasayana_protocol_by_id("NON-EXISTENT-RASAYANA", conn)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_ojas_reserve_mathematics_pravara():
    """Verify high biomarker scores yield Pravara Ojas and lower biological age."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = OjasEvaluationRequest(
            patient_id="PAT-RAS-001",
            chronological_age=52,
            grip_strength_kg=48.0,          # High strength (> 40 kg baseline)
            vital_capacity_liters=4.4,      # High capacity (> 4.0 L baseline)
            joint_mobility_score=9.5,       # Excellent mobility
            skin_luster_score=9.0,          # Vibrant Chhavi
            cognitive_memory_score=9.0,     # Sharp Smriti
            visramsa_symptoms=[],           # Zero dislocation
            vyapat_symptoms=[],             # Zero pathology
            kshaya_symptoms=[],             # Zero wasting
            evaluator_arn="ARN-NCISM-2015-8832"
        )
        res = calculate_ojas_and_biological_age(req, "aiia-delhi-central-001", conn)

        assert res.ojas_score == 100.0
        assert res.ojas_status == OjasStatus.PRAVARA_OJAS
        assert res.visramsa_score == 0.0
        assert res.vyapat_score == 0.0
        assert res.kshaya_score == 0.0
        # Exceptionally fit biology yields biological age <= chronological age
        assert res.biological_age <= 52.0
        assert res.age_differential_years <= 0.0
        assert "Drishti" in res.decadal_attribute_decay  # Age 52 is Decade 6 (Drishti)
        assert len(res.lifestyle_achara_rasayana) >= 4
    finally:
        conn.close()
        tmpdir.cleanup()


def test_ojas_reserve_mathematics_avara_and_kshaya():
    """Verify severe multi-symptom Ojas depletion triggers Avara Ojas and Brahma Rasayana."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = OjasEvaluationRequest(
            patient_id="PAT-RAS-001",
            chronological_age=68,
            grip_strength_kg=16.0,          # Severely impaired strength
            vital_capacity_liters=1.4,      # Low capacity
            joint_mobility_score=3.0,       # Severe joint stiffness
            skin_luster_score=2.5,          # Pallor & dry skin
            cognitive_memory_score=6.5,     # Moderate cognitive retention
            visramsa_symptoms=["Sandhi-Vishlesha (Joint laxity)", "Gatra-Sadana (Profound fatigue)", "Dosha-Chyavana"],
            vyapat_symptoms=["Stambha (Stiffness)", "Guru-Gatrata (Heavy limbs)", "Varna-Bheda (Discoloration)"],
            kshaya_symptoms=["Murchha (Fainting)", "Moha (Stupor)", "Mamsa-Kshaya (Severe tissue wasting)"],
            evaluator_arn="ARN-NCISM-2015-8832"
        )
        res = calculate_ojas_and_biological_age(req, "aiia-delhi-central-001", conn)

        assert res.ojas_score < 50.0
        assert res.ojas_status == OjasStatus.AVARA_OJAS
        assert res.visramsa_score >= 75.0
        assert res.vyapat_score >= 75.0
        assert res.kshaya_score >= 90.0
        # Accelerated bio-functional decay
        assert res.biological_age > 68.0
        assert res.age_differential_years > 0.0
        # Severe Ojo Kshaya prescribes Brahma Rasayana
        assert res.prescribed_rasayana_id == "RAS-BRAHMA-02"
        assert "Brahma Rasayana" in res.recommended_rasayana_formulation
    finally:
        conn.close()
        tmpdir.cleanup()


def test_medhya_rasayana_cognitive_targeting():
    """Verify cognitive deficit or Medha decade selects Charakokta Chatush-Medhya Rasayana."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = OjasEvaluationRequest(
            patient_id="PAT-RAS-001",
            chronological_age=36,           # Decade 4: Medha
            grip_strength_kg=38.0,
            vital_capacity_liters=3.4,
            joint_mobility_score=8.0,
            skin_luster_score=8.0,
            cognitive_memory_score=4.8,     # Significant Smriti loss & mental fog
            visramsa_symptoms=[],
            vyapat_symptoms=[],
            kshaya_symptoms=[],
            evaluator_arn="ARN-NCISM-2015-8832"
        )
        res = calculate_ojas_and_biological_age(req, "aiia-delhi-central-001", conn)

        assert res.prescribed_rasayana_id == "RAS-MEDHYA-06"
        assert "Chatush-Medhya" in res.recommended_rasayana_formulation
        assert "Mandukaparni" in res.recommended_rasayana_formulation
        assert "Medha" in res.decadal_attribute_decay
    finally:
        conn.close()
        tmpdir.cleanup()


def test_decadal_loss_of_attributes_progression():
    """Verify Sharngadhara decadal loss attributes across all life decades (1 to 10)."""
    assert "Balya" in determine_decadal_attribute_decay(8)
    assert "Vriddhi" in determine_decadal_attribute_decay(17)
    assert "Chhavi" in determine_decadal_attribute_decay(25)
    assert "Medha" in determine_decadal_attribute_decay(35)
    assert "Twak" in determine_decadal_attribute_decay(45)
    assert "Drishti" in determine_decadal_attribute_decay(55)
    assert "Shukra" in determine_decadal_attribute_decay(65)
    assert "Vikrama" in determine_decadal_attribute_decay(75)
    assert "Buddhi" in determine_decadal_attribute_decay(85)
    assert "Karmendriya" in determine_decadal_attribute_decay(95)


def test_kuti_praveshika_firewall_all_clear():
    """Verify patient meeting all clinical criteria is cleared for Kuti retreat."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = KutiPraveshikaAdmissionRequest(
            patient_id="PAT-RAS-001",
            chronological_age=48,
            has_active_acute_infection=False,
            blood_pressure_systolic=124,
            blood_pressure_diastolic=82,
            has_severe_cardiac_or_psychiatric_instability=False,
            pre_shodhana_completed=True,    # Panchakarma bio-cleansing completed
            planned_duration_days=30,
            rasayana_formulation="Kuti Praveshika Chyavana Compound with Go-Ghrita",
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        res = admit_kuti_praveshika_episode(conn, "aiia-delhi-central-001", req)

        assert res.episode_id.startswith("kuti-")
        assert res.eligibility_cleared is True
        assert len(res.contraindication_flags) == 0
        assert any("Trigarbha" in g for g in res.kuti_design_guidelines)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_kuti_praveshika_firewall_rejections():
    """Verify safety firewall rejects candidates without prior Shodhana or with Stage-2 HTN."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Case A: Missing Shodhana
        req_no_shodhana = KutiPraveshikaAdmissionRequest(
            patient_id="PAT-RAS-001",
            chronological_age=48,
            has_active_acute_infection=False,
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80,
            has_severe_cardiac_or_psychiatric_instability=False,
            pre_shodhana_completed=False,   # VIOLATION!
            planned_duration_days=21,
            rasayana_formulation="Brahma Rasayana",
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        res_a = admit_kuti_praveshika_episode(conn, "aiia-delhi-central-001", req_no_shodhana)
        assert res_a.eligibility_cleared is False
        assert any("Prior Panchakarma bio-cleansing" in f for f in res_a.contraindication_flags)

        # Case B: Multi-factor violation (HTN + active infection + psychiatric crisis)
        req_multi_contra = KutiPraveshikaAdmissionRequest(
            patient_id="PAT-RAS-001",
            chronological_age=55,
            has_active_acute_infection=True,
            blood_pressure_systolic=175,
            blood_pressure_diastolic=105,
            has_severe_cardiac_or_psychiatric_instability=True,
            pre_shodhana_completed=True,
            planned_duration_days=45,
            rasayana_formulation="Shilajatu Compound",
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        res_b = admit_kuti_praveshika_episode(conn, "aiia-delhi-central-001", req_multi_contra)
        assert res_b.eligibility_cleared is False
        assert len(res_b.contraindication_flags) == 3
        flag_text = " ".join(res_b.contraindication_flags)
        assert "Active acute febrile" in flag_text
        assert "Stage-2 Hypertension" in flag_text
        assert "psychiatric instability" in flag_text
    finally:
        conn.close()
        tmpdir.cleanup()


def test_patient_history_retrieval():
    """Verify historical Ojas evaluations and Kuti screening episodes are retrievable."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Create 2 Ojas evaluations
        req1 = OjasEvaluationRequest(
            patient_id="PAT-RAS-001",
            chronological_age=50,
            grip_strength_kg=40.0,
            vital_capacity_liters=3.6,
            joint_mobility_score=8.5,
            skin_luster_score=8.0,
            cognitive_memory_score=8.0,
            visramsa_symptoms=[],
            vyapat_symptoms=[],
            kshaya_symptoms=[],
            evaluator_arn="ARN-NCISM-2015-8832"
        )
        calculate_ojas_and_biological_age(req1, "aiia-delhi-central-001", conn)

        req2 = OjasEvaluationRequest(
            patient_id="PAT-RAS-001",
            chronological_age=50,
            grip_strength_kg=35.0,
            vital_capacity_liters=3.0,
            joint_mobility_score=7.0,
            skin_luster_score=7.0,
            cognitive_memory_score=7.0,
            visramsa_symptoms=["Gatra-Sadana"],
            vyapat_symptoms=[],
            kshaya_symptoms=[],
            evaluator_arn="ARN-NCISM-2015-8832"
        )
        calculate_ojas_and_biological_age(req2, "aiia-delhi-central-001", conn)

        ojas_history = list_patient_ojas_evaluations("PAT-RAS-001", conn)
        assert len(ojas_history) == 2

        # Create 1 Kuti screening
        kuti_req = KutiPraveshikaAdmissionRequest(
            patient_id="PAT-RAS-001",
            chronological_age=50,
            has_active_acute_infection=False,
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80,
            has_severe_cardiac_or_psychiatric_instability=False,
            pre_shodhana_completed=True,
            planned_duration_days=21,
            rasayana_formulation="Chyavanaprasha",
            practitioner_arn="ARN-NCISM-2015-8832"
        )
        admit_kuti_praveshika_episode(conn, "aiia-delhi-central-001", kuti_req)

        kuti_history = list_kuti_praveshika_episodes("PAT-RAS-001", conn)
        assert len(kuti_history) == 1
        assert kuti_history[0].eligibility_cleared is True
    finally:
        conn.close()
        tmpdir.cleanup()
