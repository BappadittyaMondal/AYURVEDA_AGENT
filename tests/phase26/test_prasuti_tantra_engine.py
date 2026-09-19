"""
Unit Tests for Prasuti Tantra, Stri Roga & Garbhini Paricharya Engine (Phase 26).
"""

import tempfile
from pathlib import Path
import pytest

from core.database import get_sqlite_connection, init_database
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.prasuti_tantra import (
    evaluate_fertility_readiness,
    get_garbhini_month_regimen,
    get_yoni_vyapad_profile,
    initialize_prasuti_tables,
    list_all_month_regimens,
    list_all_yoni_vyapads,
    list_antenatal_consultations,
    list_yoni_vyapad_assessments,
    record_antenatal_consultation,
    record_yoni_vyapad_assessment,
)
from models.prasuti_tantra import (
    AntenatalConsultationCreate,
    DoshicClass,
    FertilityReadinessRequest,
    ObstetricTriageLevel,
    YoniVyapadAssessmentCreate,
)


def get_fresh_db_with_patient():
    """Create isolated SQLite database with a seeded female patient in a safe temp directory."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_prasuti.db"
    init_database(db_path)
    conn = get_sqlite_connection(db_path)
    initialize_prasuti_tables(conn)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("PAT-PRASUTI-001", "aiia-delhi-central-001", "Kavita", "Deshmukh", "1994-06-12", "FEMALE", "+919876543004", 1700000000)
    )
    return tmpdir, conn


def test_garbha_sambhava_samagri_calculus():
    """Verify 4-factor fertility readiness calculus and tiered recommendations."""
    # 1. Optimal Fertility Readiness
    req_optimal = FertilityReadinessRequest(
        patient_id="PAT-PRASUTI-001",
        ritu_score=90.0,
        kshetra_score=85.0,
        ambu_score=80.0,
        beeja_score=95.0,
        evaluator_arn="AY-DL-2024-998811",
    )
    res_optimal = evaluate_fertility_readiness(req_optimal)
    assert res_optimal.composite_readiness_score == 87.5
    assert res_optimal.readiness_tier == "EXCELLENT"
    assert res_optimal.beeja_status == "OPTIMAL"
    assert "Ready for Garbhadhana Samskara" in "".join(res_optimal.preconception_recommendations)

    # 2. Compromised Beeja & Kshetra
    req_compromised = FertilityReadinessRequest(
        patient_id="PAT-PRASUTI-001",
        ritu_score=75.0,
        kshetra_score=50.0,
        ambu_score=70.0,
        beeja_score=45.0,
        evaluator_arn="AY-DL-2024-998811",
    )
    res_compromised = evaluate_fertility_readiness(req_compromised)
    assert res_compromised.composite_readiness_score == 60.0
    assert res_compromised.readiness_tier == "ADEQUATE"
    assert res_compromised.beeja_status == "DEFICIENT"
    assert any("Phala Ghrita" in r for r in res_compromised.preconception_recommendations)
    assert any("Uttarabasti" in p for p in res_compromised.indicated_shodhana_or_rasayana)


def test_garbhini_month_by_month_regimen_catalog():
    """Verify 9-month Garbhini Paricharya catalog completeness and canonical milestones."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        regimens = list_all_month_regimens(conn)
        assert len(regimens) == 9

        # Month 1: Sheeta Madhura Dugdha & Garbha Sthapana
        m1 = get_garbhini_month_regimen(1, conn)
        assert "Sheeta Madhura Dugdha" in m1.dietary_regimen
        assert "Garbha Sthapana" in m1.fetal_development_milestone
        assert "Vamana" in m1.contraindicated_drugs

        # Month 4: Navanita & Dauhrida
        m4 = get_garbhini_month_regimen(4, conn)
        assert "Navanita" in m4.dietary_regimen
        assert "Dauhrida" in m4.fetal_development_milestone

        # Month 8: Asthapana & Anuvasana Basti, Ojas instability
        m8 = get_garbhini_month_regimen(8, conn)
        assert "Basti" in m8.therapeutic_procedures
        assert "Ojas" in m8.fetal_development_milestone

        # Month 9: Anuvasana Basti & Yoni Pichu with Bala Taila for Sukha Prasava
        m9 = get_garbhini_month_regimen(9, conn)
        assert "Yoni Pichu" in m9.therapeutic_procedures
        assert "Sukha Prasava" in m9.fetal_development_milestone
    finally:
        conn.close()
        tmpdir.cleanup()


def test_antenatal_consultation_normal_physiological():
    """Verify normal 16-week antenatal visit correctly maps to Month 4 and recognizes Dauhrida."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        consult_data = AntenatalConsultationCreate(
            patient_id="PAT-PRASUTI-001",
            gestational_age_weeks=16.0,
            blood_pressure_systolic=116,
            blood_pressure_diastolic=74,
            fundal_height_cm=16.0,
            fetal_heart_rate_bpm=142,
            weight_kg=58.5,
            edema_present=False,
            vaginal_bleeding_present=False,
            dauhrida_desires=["Sweet mangoes", "Cold pomegranate juice"],
            practitioner_arn="AY-DL-2024-998811",
        )
        res = record_antenatal_consultation(conn, "aiia-delhi-central-001", consult_data)
        assert res.gestational_month == 4
        assert res.obstetric_triage_level == ObstetricTriageLevel.NORMAL
        assert len(res.high_risk_flags) == 0
        assert "Navanita" in res.prescribed_regimen
        assert "Sweet mangoes" in res.prescribed_regimen

        # Verify history retrieval
        history = list_antenatal_consultations("PAT-PRASUTI-001", conn)
        assert len(history) == 1
        assert history[0].consultation_id == res.consultation_id
    finally:
        conn.close()
        tmpdir.cleanup()


def test_antenatal_consultation_high_risk_antepartum_hemorrhage_firewall():
    """Verify antepartum bleeding triggers CRITICAL_OBSTETRIC_EMERGENCY and blocks Panchakarma."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        consult_data = AntenatalConsultationCreate(
            patient_id="PAT-PRASUTI-001",
            gestational_age_weeks=28.0,
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80,
            fundal_height_cm=27.0,
            fetal_heart_rate_bpm=138,
            weight_kg=64.0,
            edema_present=False,
            vaginal_bleeding_present=True,  # Severe Hemorrhage Flag!
            practitioner_arn="AY-DL-2024-998811",
        )
        res = record_antenatal_consultation(conn, "aiia-delhi-central-001", consult_data)
        assert res.obstetric_triage_level == ObstetricTriageLevel.CRITICAL_OBSTETRIC_EMERGENCY
        assert any("Antepartum vaginal hemorrhage" in f for f in res.high_risk_flags)
        assert "Vamana" in res.contraindicated_ayurvedic_therapies
        assert "Virechana" in res.contraindicated_ayurvedic_therapies
        assert res.emergency_escalation_notes is not None
        assert "Tertiary Labor & Delivery ICU" in res.emergency_escalation_notes
    finally:
        conn.close()
        tmpdir.cleanup()


def test_antenatal_consultation_severe_preeclampsia_firewall():
    """Verify BP >= 160/110 with CNS headache triggers CRITICAL_OBSTETRIC_EMERGENCY."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        consult_data = AntenatalConsultationCreate(
            patient_id="PAT-PRASUTI-001",
            gestational_age_weeks=34.0,
            blood_pressure_systolic=168,
            blood_pressure_diastolic=112,
            fundal_height_cm=33.0,
            fetal_heart_rate_bpm=150,
            weight_kg=72.0,
            edema_present=True,
            vaginal_bleeding_present=False,
            severe_headache_or_scotoma=True,
            practitioner_arn="AY-DL-2024-998811",
        )
        res = record_antenatal_consultation(conn, "aiia-delhi-central-001", consult_data)
        assert res.obstetric_triage_level == ObstetricTriageLevel.CRITICAL_OBSTETRIC_EMERGENCY
        assert any("Severe Pre-eclampsia" in f for f in res.high_risk_flags)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_yoni_vyapad_catalog_and_classification():
    """Verify 20 classical Yoni Vyapad conditions covering all 4 Doshic categories with ICD-11."""
    vyapads = list_all_yoni_vyapads()
    assert len(vyapads) == 20

    v_vat = list_all_yoni_vyapads(doshic_class=DoshicClass.VATAJA)
    v_pit = list_all_yoni_vyapads(doshic_class=DoshicClass.PITTAJA)
    v_kap = list_all_yoni_vyapads(doshic_class=DoshicClass.KAPHAJA)
    v_san = list_all_yoni_vyapads(doshic_class=DoshicClass.SANNIPATAJA)

    assert len(v_vat) == 5
    assert len(v_pit) == 5
    assert len(v_kap) == 5
    assert len(v_san) == 5

    # Specific profile checks
    udavartini = get_yoni_vyapad_profile("YONI-VAT-02")
    assert "Udavartini" in udavartini.sanskrit_name
    assert "GA00.0" in udavartini.icd11_mapping

    asrigdara = get_yoni_vyapad_profile("YONI-PIT-02")
    assert "Asrigdara" in asrigdara.sanskrit_name
    assert "Pushyanuga Churna" in "".join(asrigdara.classical_formulations)

    karnini = get_yoni_vyapad_profile("YONI-KAP-02")
    assert "Karnini" in karnini.sanskrit_name
    assert "GA10.0" in karnini.icd11_mapping


def test_yoni_vyapad_assessment_and_therapy():
    """Verify logging Yoni Vyapad clinical assessment and generating localized and oral prescription."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        assess_data = YoniVyapadAssessmentCreate(
            patient_id="PAT-PRASUTI-001",
            vyapad_code="YONI-VAT-02",
            reported_symptoms=["Severe spasmodic pelvic pain prior to menses", "Immediate relief after bleeding starts"],
            pelvic_examination_findings="Normal pelvic anatomy, no structural mass, tender bilateral fornices",
            practitioner_arn="AY-DL-2024-998811",
        )
        res = record_yoni_vyapad_assessment(conn, "aiia-delhi-central-001", assess_data)
        assert res.assessment_id.startswith("yoni-")
        assert res.vyapad_code == "YONI-VAT-02"
        assert res.doshic_class == DoshicClass.VATAJA
        assert any("Dhanwantaram Taila" in t for t in res.local_therapies)
        assert any("Rajapravartini Vati" in f for f in res.oral_formulations)

        # Retrieve history
        history = list_yoni_vyapad_assessments("PAT-PRASUTI-001", conn)
        assert len(history) == 1
        assert history[0].assessment_id == res.assessment_id
    finally:
        conn.close()
        tmpdir.cleanup()
