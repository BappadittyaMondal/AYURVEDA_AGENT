"""
Unit Tests for Kaumarbhritya, Bala Roga & Suvarnaprashana Engine (Phase 27).
"""

import tempfile
from pathlib import Path
import pytest

from core.database import get_sqlite_connection, init_database
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.kaumarbhritya import (
    calculate_pediatric_posology,
    initialize_kaumarbhritya_tables,
    list_developmental_milestones,
    list_pediatric_consultations,
    list_suvarnaprashana_doses,
    record_pediatric_consultation,
    record_suvarnaprashana_dose,
)
from models.kaumarbhritya import (
    BalaRogaSyndrome,
    ClassicalSamskara,
    DietaryStage,
    PediatricConsultationCreate,
    PediatricDosageCalculationRequest,
    SuvarnaprashanaAdminCreate,
)


def get_fresh_db_with_patient():
    """Create isolated SQLite database with a seeded pediatric patient in a safe temp directory."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_kaumarbhritya.db"
    init_database(db_path)
    conn = get_sqlite_connection(db_path)
    initialize_kaumarbhritya_tables(conn)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("PAT-PEDIATRIC-001", "aiia-delhi-central-001", "Aarav", "Sharma", "2025-06-15", "MALE", "+919876543006", 1700000000)
    )
    return tmpdir, conn


def test_developmental_milestones_catalog():
    """Verify developmental milestones, classical Samskaras, and dietary stages."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        milestones = list_developmental_milestones(conn)
        assert len(milestones) >= 7

        samskaras_found = {m.classical_samskara for m in milestones}
        assert ClassicalSamskara.JATAKARMA in samskaras_found
        assert ClassicalSamskara.NAMAKARANA in samskaras_found
        assert ClassicalSamskara.NISHKRAMANA in samskaras_found
        assert ClassicalSamskara.ANNAPRASHANA in samskaras_found
        assert ClassicalSamskara.KARNAVEDHA in samskaras_found
        assert ClassicalSamskara.CHAULA_CHUDAKARANA in samskaras_found

        m0 = [m for m in milestones if m.age_months == 0][0]
        assert m0.dietary_stage == DietaryStage.KSHEERADA
        assert m0.sharngadhara_dosage_ratti == 1.0

        m6 = [m for m in milestones if m.age_months == 6][0]
        assert m6.dietary_stage == DietaryStage.KSHEERANNADA
        assert m6.classical_samskara == ClassicalSamskara.ANNAPRASHANA
    finally:
        conn.close()
        tmpdir.cleanup()


def test_pediatric_posology_clark_cowling_sharngadhara():
    """Verify dual posology scaling for an infant (6 months) and toddler (36 months)."""
    # 1. 6-month infant (Weight 7.0 kg, Adult dose 500 mg)
    req_infant = PediatricDosageCalculationRequest(
        patient_id="PAT-PEDIATRIC-001",
        age_months=6,
        weight_kg=7.0,
        adult_dose_mg=500.0,
        formulation_name="Arvindasava",
        contains_heavy_metals_or_schedule_e1=False,
        evaluator_arn="AY-DL-2024-998811",
    )
    res_infant = calculate_pediatric_posology(req_infant)
    assert res_infant.dietary_stage == DietaryStage.KSHEERADA
    assert res_infant.clark_dose_mg == 50.0   # (7/70)*500
    assert res_infant.cowling_dose_mg == 31.25 # ((0.5+1)/24)*500
    assert res_infant.sharngadhara_dose_mg == 750.0 # 6 ratti * 125mg
    assert res_infant.recommended_pediatric_dose_mg == 40.62 # (50.0 + 31.25)/2
    assert res_infant.safety_firewall_cleared is True

    # 2. 36-month toddler (3 years, Weight 14.0 kg, Adult dose 500 mg)
    req_toddler = PediatricDosageCalculationRequest(
        patient_id="PAT-PEDIATRIC-001",
        age_months=36,
        weight_kg=14.0,
        adult_dose_mg=500.0,
        formulation_name="Shatavari Gulam",
        contains_heavy_metals_or_schedule_e1=False,
        evaluator_arn="AY-DL-2024-998811",
    )
    res_toddler = calculate_pediatric_posology(req_toddler)
    assert res_toddler.dietary_stage == DietaryStage.ANNADA
    assert res_toddler.clark_dose_mg == 100.0 # (14/70)*500
    assert res_toddler.cowling_dose_mg == 83.33 # ((3+1)/24)*500
    assert res_toddler.recommended_pediatric_dose_mg == 91.67


def test_pediatric_posology_underweight_malnourished_clamping():
    """Verify that an underweight/malnourished child's dosage is strictly clamped by Clark's rule."""
    # Underweight 3-year-old (36 months, but weight only 8.0 kg instead of normal 14 kg)
    # Clark = (8.0 / 70) * 500 = 57.14 mg
    # Cowling = ((3 + 1) / 24) * 500 = 83.33 mg
    # Without clamp, average would be 70.24 mg (overdose!)
    # With Clark clamp, dose must be strictly clamped to 57.14 mg
    req_malnourished = PediatricDosageCalculationRequest(
        patient_id="PAT-PEDIATRIC-MALNOURISHED",
        age_months=36,
        weight_kg=8.0,
        adult_dose_mg=500.0,
        formulation_name="Vidangadi Churna",
        contains_heavy_metals_or_schedule_e1=False,
        evaluator_arn="AY-DL-2024-998811",
    )
    res = calculate_pediatric_posology(req_malnourished)
    assert res.clark_dose_mg == 57.14
    assert res.cowling_dose_mg == 83.33
    assert res.recommended_pediatric_dose_mg == 57.14
    assert res.recommended_pediatric_dose_mg <= res.clark_dose_mg



def test_pediatric_toxicology_firewall_ksheerada_infant():
    """Verify Schedule E-1 or heavy metals in infant (< 12 months) triggers safety exception."""
    req_toxic = PediatricDosageCalculationRequest(
        patient_id="PAT-PEDIATRIC-001",
        age_months=8,
        weight_kg=8.5,
        adult_dose_mg=250.0,
        formulation_name="Kupipakwa Rasayana with Vatsanabha",
        contains_heavy_metals_or_schedule_e1=True,  # Prohibited!
        evaluator_arn="AY-DL-2024-998811",
    )
    with pytest.raises(ClinicalGovernanceException) as exc_info:
        calculate_pediatric_posology(req_toxic)
    assert "Schedule E-1 poisons and heavy metal Bhasmas are strictly contraindicated" in str(exc_info.value)


def test_pediatric_toxicology_firewall_under_five_years():
    """Verify heavy metal formulations in young children (< 5 years) are strictly blocked."""
    req_toxic_child = PediatricDosageCalculationRequest(
        patient_id="PAT-PEDIATRIC-001",
        age_months=36,
        weight_kg=14.0,
        adult_dose_mg=250.0,
        formulation_name="Tamra Bhasma Compound",
        contains_heavy_metals_or_schedule_e1=True,  # Prohibited under 5 years!
        evaluator_arn="AY-DL-2024-998811",
    )
    with pytest.raises(ClinicalGovernanceException) as exc_info:
        calculate_pediatric_posology(req_toxic_child)
    assert "Heavy metal Bhasmas are strictly contraindicated in young children under 5 years" in str(exc_info.value)


def test_pediatric_consultation_phakka_parigarbhika():
    """Verify diagnosis of Parigarbhika Phakka (maternal pregnancy displacement) and management plan."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        consult_data = PediatricConsultationCreate(
            patient_id="PAT-PEDIATRIC-001",
            age_months=14,
            weight_kg=7.2,
            bala_roga_diagnosis=BalaRogaSyndrome.PHAKKA_GARBHAJA_PARIGARBHIKA,
            presenting_symptoms=["Severe emaciation of limbs", "Protuberant abdomen (Kukshi Vriddhi)", "Loss of appetite"],
            adult_reference_dose_mg=500.0,
            prescribed_formulation="Kalyanaka Ghrita with Vidangadi Churna",
            practitioner_arn="AY-DL-2024-998811",
        )
        res = record_pediatric_consultation(conn, "aiia-delhi-central-001", consult_data)
        assert res.consultation_id.startswith("ped-")
        assert "5B5A" in res.icd11_mapping
        assert res.dietary_stage == DietaryStage.KSHEERANNADA
        assert any("Cease breastfeeding from pregnant mother" in p for p in res.clinical_management_plan)
        assert any("Kalyanaka Ghrita" in p for p in res.clinical_management_plan)

        # Retrieve history
        history = list_pediatric_consultations("PAT-PEDIATRIC-001", conn)
        assert len(history) == 1
        assert history[0].consultation_id == res.consultation_id
    finally:
        conn.close()
        tmpdir.cleanup()


def test_pediatric_consultation_kukunaka_ophthalmia():
    """Verify diagnosis of Kukunaka dentition-associated conjunctivitis and Dhatri Shodhana."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        consult_data = PediatricConsultationCreate(
            patient_id="PAT-PEDIATRIC-001",
            age_months=7,
            weight_kg=7.8,
            bala_roga_diagnosis=BalaRogaSyndrome.KUKUNAKA,
            presenting_symptoms=["Excessive eye rubbing", "Photophobia", "Copious purulent discharge during teething"],
            adult_reference_dose_mg=250.0,
            prescribed_formulation="Triphala-Yashtimadhu Aschyotana",
            practitioner_arn="AY-DL-2024-998811",
        )
        res = record_pediatric_consultation(conn, "aiia-delhi-central-001", consult_data)
        assert "9A60" in res.icd11_mapping
        assert any("Dhatri Shodhana" in p for p in res.clinical_management_plan)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_suvarnaprashana_administration_success():
    """Verify compliant Suvarnaprashana with unequal honey-ghee ratio logs successfully."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        dose_data = SuvarnaprashanaAdminCreate(
            patient_id="PAT-PEDIATRIC-001",
            age_months=24,
            pushya_nakshatra_date="2026-10-18",
            suvarna_bhasma_mg=3.0,
            madhu_ghrita_ratio="2:1 Madhu to Ghrita",  # Unequal ratio compliant
            medhya_herbs=["Brahmi", "Vacha", "Shankhapushpi"],
            practitioner_arn="AY-DL-2024-998811",
        )
        res = record_suvarnaprashana_dose(conn, "aiia-delhi-central-001", dose_data)
        assert res.dose_id.startswith("suvarna-")
        assert res.suvarna_bhasma_mg == 3.0
        assert any("Medha Vardhana" in o for o in res.immunomodulation_outcomes)
        assert any("Bala Vardhana" in o for o in res.immunomodulation_outcomes)

        # Retrieve history
        history = list_suvarnaprashana_doses("PAT-PEDIATRIC-001", conn)
        assert len(history) == 1
        assert history[0].dose_id == res.dose_id
    finally:
        conn.close()
        tmpdir.cleanup()


def test_suvarnaprashana_viruddha_ahara_equal_ratio_blocked():
    """Verify 1:1 equal ratio of honey and ghee triggers Viruddha Ahara rejection firewall."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        dose_data = SuvarnaprashanaAdminCreate(
            patient_id="PAT-PEDIATRIC-001",
            age_months=18,
            pushya_nakshatra_date="2026-10-18",
            suvarna_bhasma_mg=2.5,
            madhu_ghrita_ratio="1:1 Equal Madhu and Ghrita",  # Toxic Viruddha Ahara!
            practitioner_arn="AY-DL-2024-998811",
        )
        with pytest.raises(ClinicalGovernanceException) as exc_info:
            record_suvarnaprashana_dose(conn, "aiia-delhi-central-001", dose_data)
        assert "Equal proportion of honey and ghee (1:1) constitutes toxic Viruddha Ahara" in str(exc_info.value)
    finally:
        conn.close()
        tmpdir.cleanup()
