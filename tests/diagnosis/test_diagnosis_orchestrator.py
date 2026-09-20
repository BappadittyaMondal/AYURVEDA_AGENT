"""Unit tests for Unified Clinical Diagnostic & Decision Support Orchestrator."""
import sqlite3
import pytest

from core.database import get_sqlite_connection, init_database
from core.diagnosis_orchestrator import (
    CLASSICAL_DISEASE_PROFILES,
    countersign_diagnosis_episode,
    determine_ama_and_agni,
    evaluate_clinical_diagnosis,
    evaluate_shat_kriya_kala,
    get_patient_diagnosis_episodes,
    match_morbidity_profile,
)
from models.diagnosis_orchestrator import (
    AgniStatus,
    AmaStatus,
    ClinicalIntakeData,
    CounterSignRequest,
    GovernanceStatus,
    RogiBalaGrade,
    ShatKriyaKalaStage,
    ShodhanaEligibility,
)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensure database is initialized before running tests."""
    init_database()


def test_disease_pattern_matching():
    """Verify morbidity pattern matching identifies classical diseases with appropriate confidence."""
    # Amavata presentation
    amavata_match = match_morbidity_profile(
        chief_complaints=["Severe joint pain and morning stiffness"],
        symptoms=["sandhi-shula", "stambha", "shotha", "aruchi"]
    )
    assert amavata_match[0][0] == "AMAVATA"
    assert amavata_match[0][1] > 0.3

    # Prameha presentation
    prameha_match = match_morbidity_profile(
        chief_complaints=["Excessive urination and sweet taste"],
        symptoms=["polyuria", "prabhuta mutrata", "avila mutrata", "trishna"]
    )
    assert prameha_match[0][0] == "PRAMEHA"

    # Gridhrasi presentation
    gridhrasi_match = match_morbidity_profile(
        chief_complaints=["Shooting pain radiating from buttock down to foot"],
        symptoms=["sciatica", "radiating leg pain", "suptata", "sakthi utkshepa nigraha"]
    )
    assert gridhrasi_match[0][0] == "GRIDHRASI"


def test_ama_and_agni_evaluation():
    """Verify Ama and Agni classification and physiological gating logic."""
    intake_sama = ClinicalIntakeData(
        patient_id="PAT-AMA-01",
        hospital_id="aiia-delhi-central-001",
        chief_complaints=["Indigestion"],
        symptoms=["loss of appetite", "heaviness"],
        jihwa_coating="THICK_WHITE_SLIMY",
        appetite_and_digestion="POOR_MANDAGNI"
    )
    ama, agni = determine_ama_and_agni(intake_sama, CLASSICAL_DISEASE_PROFILES["AMAVATA"])
    assert ama == AmaStatus.SAMA
    assert agni == AgniStatus.MANDAGNI

    intake_nirama = ClinicalIntakeData(
        patient_id="PAT-NIR-01",
        hospital_id="aiia-delhi-central-001",
        chief_complaints=["Joint stiffness"],
        symptoms=["pain"],
        jihwa_coating="CLEAN_PINK",
        appetite_and_digestion="SAMAGNI"
    )
    ama_n, agni_n = determine_ama_and_agni(intake_nirama, CLASSICAL_DISEASE_PROFILES["SANDHIVATA"])
    assert ama_n == AmaStatus.NIRAMA
    assert agni_n == AgniStatus.SAMAGNI


def test_shat_kriya_kala_staging():
    """Verify Shat Kriya Kala staging aligns with disease duration and tissue involvement."""
    stage_early = evaluate_shat_kriya_kala(0.5, ["mild heaviness"])
    assert stage_early == ShatKriyaKalaStage.PRAKOPA

    stage_prodromal = evaluate_shat_kriya_kala(2.5, ["joint stiffness"])
    assert stage_prodromal == ShatKriyaKalaStage.STHANA_SAMSHRAYA

    stage_overt = evaluate_shat_kriya_kala(5.0, ["swelling", "radiating pain"])
    assert stage_overt == ShatKriyaKalaStage.VYAKTI

    stage_chronic = evaluate_shat_kriya_kala(16.0, ["deformity", "ulceration"])
    assert stage_chronic == ShatKriyaKalaStage.BHEDAVASTHA


def test_amavata_end_to_end_synthesis():
    """Verify comprehensive end-to-end diagnostic synthesis for Amavata."""
    conn = get_sqlite_connection()
    intake = ClinicalIntakeData(
        patient_id="PAT-TEST-AMAVATA",
        hospital_id="aiia-delhi-central-001",
        chief_complaints=["Bilateral knee joint pain with severe morning stiffness"],
        symptoms=["sandhi-shula", "stambha", "shotha", "swelling", "aruchi"],
        duration_weeks=4.0,
        jihwa_coating="THICK_WHITE_SLIMY",
        appetite_and_digestion="POOR_MANDAGNI",
        rogi_bala=RogiBalaGrade.MADHYAMA,
        systolic_bp=120,
        diastolic_bp=80,
        hemoglobin_g_dl=13.0,
        is_pregnant=False,
        age_years=45
    )

    resp = evaluate_clinical_diagnosis(intake, conn=conn)
    conn.close()

    assert resp.primary_diagnosis.sanskrit_name == "Amavata"
    assert resp.primary_diagnosis.namaste_code == "AYU-ROGA-AMA-001"
    assert resp.primary_diagnosis.icd11_tm2_code == "FA20.Z"
    assert resp.ama_status == AmaStatus.SAMA
    assert resp.agni_status == AgniStatus.MANDAGNI
    assert resp.treatment_protocol.shodhana_eligibility == ShodhanaEligibility.CONTRAINDICATED_SAMA_STATE
    assert any("Rasna Saptaka Kwatha" in f.formulation_name for f in resp.treatment_protocol.shamana_chikitsa)
    assert any("Simhanada Guggulu" in f.formulation_name for f in resp.treatment_protocol.shamana_chikitsa)
    assert resp.governance_status == GovernanceStatus.DRAFT_DECISION_SUPPORT
    # Verify Ranked Differentials (Task 1.4)
    assert len(resp.ranked_differentials) == 3
    assert resp.ranked_differentials[0].rank == 1
    assert resp.ranked_differentials[0].diagnosis.sanskrit_name == "Amavata"
    assert "Migratory polyarthritis" in resp.ranked_differentials[0].vyavachhedaka_lakshana
    assert len(resp.ranked_differentials[0].pertinent_negatives) >= 1


def test_safety_firewall_interception():
    """Verify severe anemia triggers critical safety alert and blocks invasive therapies."""
    conn = get_sqlite_connection()
    intake_anemic = ClinicalIntakeData(
        patient_id="PAT-TEST-ANEMIA",
        hospital_id="aiia-delhi-central-001",
        chief_complaints=["Joint pain"],
        symptoms=["sandhi-shula", "fatigue"],
        hemoglobin_g_dl=6.8,  # Below 8.0 g/dL critical cutoff
        systolic_bp=110,
        diastolic_bp=70,
        rogi_bala=RogiBalaGrade.MADHYAMA,
        is_pregnant=False,
        age_years=52
    )

    resp = evaluate_clinical_diagnosis(intake_anemic, conn=conn)
    conn.close()

    assert resp.safety_firewalls_cleared is False
    assert any("CODE_RED_SEVERE_ANEMIA" in a for a in resp.safety_alerts)


def test_countersigning_lifecycle():
    """Verify statutory NCISM physician counter-signature transitions governance state."""
    conn = get_sqlite_connection()
    intake = ClinicalIntakeData(
        patient_id="PAT-TEST-SIGN",
        hospital_id="aiia-delhi-central-001",
        chief_complaints=["Polyuria and thirst"],
        symptoms=["polyuria", "prabhuta mutrata", "trishna"],
        duration_weeks=6.0,
        appetite_and_digestion="VARIABLE_VISHAMAGNI",
        rogi_bala=RogiBalaGrade.UTTAMA,
        systolic_bp=120,
        diastolic_bp=80,
        hemoglobin_g_dl=13.5,
        is_pregnant=False,
        age_years=40
    )

    resp = evaluate_clinical_diagnosis(intake, conn=conn)
    assert resp.governance_status == GovernanceStatus.DRAFT_DECISION_SUPPORT
    assert resp.attending_physician_arn is None

    sign_req = CounterSignRequest(
        physician_arn="ARN-NCISM-2015-8832",
        action="COUNTERSIGN",
        clinical_notes="Verified clinically. Prescriptions approved."
    )

    signed = countersign_diagnosis_episode(resp.episode_id, sign_req, conn=conn)
    assert signed.governance_status == GovernanceStatus.PHYSICIAN_COUNTERSIGNED
    assert signed.attending_physician_arn == "ARN-NCISM-2015-8832"
    assert signed.countersigned_at is not None

    history = get_patient_diagnosis_episodes("PAT-TEST-SIGN", conn=conn)
    conn.close()

    assert len(history) >= 1
    assert history[0].episode_id == resp.episode_id
    assert history[0].governance_status == GovernanceStatus.PHYSICIAN_COUNTERSIGNED


def test_incomplete_intake_rejection_and_override():
    """Verify missing mandatory parameters fail closed unless preliminary assessment override is given (C1)."""
    from core.exceptions import IncompleteClinicalIntakeException

    # Incomplete without override must fail closed
    intake_incomplete = ClinicalIntakeData(
        patient_id="PAT-TEST-INCOMPLETE",
        hospital_id="aiia-delhi-central-001",
        chief_complaints=["Joint pain"],
        symptoms=["sandhi-shula"]
    )
    with pytest.raises(IncompleteClinicalIntakeException) as exc_info:
        evaluate_clinical_diagnosis(intake_incomplete)
    assert "Mandatory parameters missing" in str(exc_info.value)

    # Incomplete with explicit preliminary override succeeds with warning flags
    intake_override = ClinicalIntakeData(
        patient_id="PAT-TEST-PRELIM",
        hospital_id="aiia-delhi-central-001",
        chief_complaints=["Joint pain and morning stiffness"],
        symptoms=["sandhi-shula", "stambha"],
        allow_preliminary_assessment=True,
        emergency_override_rationale="Outpatient rapid triage prior to nursing vital station"
    )
    resp = evaluate_clinical_diagnosis(intake_override)
    assert resp.is_preliminary_assessment is True
    assert len(resp.missing_vital_parameters) > 0


def test_red_flag_mimic_interception():
    """Verify 5 can't-miss Western emergency mimics trigger break-glass transfer and halt elective care (M1)."""
    # 1. Gridhrasi mimic with Cauda Equina Syndrome
    intake_cauda = ClinicalIntakeData(
        patient_id="PAT-MIMIC-CAUDA",
        hospital_id="aiia-delhi-central-001",
        chief_complaints=["Severe shooting sciatica down both legs", "Sudden urinary retention and saddle numbness"],
        symptoms=["sciatica", "saddle anesthesia", "urinary retention", "bilateral leg weakness"],
        duration_weeks=1.0,
        rogi_bala=RogiBalaGrade.AVARA,
        systolic_bp=130,
        diastolic_bp=85,
        hemoglobin_g_dl=13.0,
        is_pregnant=False,
        age_years=42
    )
    resp_cauda = evaluate_clinical_diagnosis(intake_cauda)
    assert resp_cauda.governance_status == GovernanceStatus.EMERGENCY_TRANSFER_TRIGGERED
    assert resp_cauda.red_flag_screening.mimic_detected is True
    assert "Cauda Equina" in resp_cauda.red_flag_screening.suspected_syndrome
    assert len(resp_cauda.treatment_protocol.shamana_chikitsa) == 0  # Blocked

    # 2. Tamaka Shwasa mimic with Left Ventricular Failure
    intake_lvf = ClinicalIntakeData(
        patient_id="PAT-MIMIC-LVF",
        hospital_id="aiia-delhi-central-001",
        chief_complaints=["Acute breathlessness", "Cough with pink frothy sputum and bilateral crackles"],
        symptoms=["breathlessness", "pink frothy sputum", "bilateral crepitations"],
        duration_weeks=0.5,
        rogi_bala=RogiBalaGrade.AVARA,
        systolic_bp=88,
        diastolic_bp=55,
        hemoglobin_g_dl=12.0,
        is_pregnant=False,
        age_years=68
    )
    resp_lvf = evaluate_clinical_diagnosis(intake_lvf)
    assert resp_lvf.governance_status == GovernanceStatus.EMERGENCY_TRANSFER_TRIGGERED
    assert resp_lvf.red_flag_screening.mimic_detected is True
    assert "Acute Left Ventricular Failure" in resp_lvf.red_flag_screening.suspected_syndrome

    # 3. Prameha mimic with Diabetic Ketoacidosis
    intake_dka = ClinicalIntakeData(
        patient_id="PAT-MIMIC-DKA",
        hospital_id="aiia-delhi-central-001",
        chief_complaints=["Excessive thirst and rapid deep breathing with fruity acetone odor"],
        symptoms=["polyuria", "trishna", "kussmaul", "acetone breath", "persistent vomiting with thirst"],
        duration_weeks=1.0,
        rogi_bala=RogiBalaGrade.AVARA,
        systolic_bp=100,
        diastolic_bp=60,
        hemoglobin_g_dl=14.0,
        is_pregnant=False,
        age_years=28
    )
    resp_dka = evaluate_clinical_diagnosis(intake_dka)
    assert resp_dka.governance_status == GovernanceStatus.EMERGENCY_TRANSFER_TRIGGERED
    assert resp_dka.red_flag_screening.mimic_detected is True
    assert "Diabetic Ketoacidosis" in resp_dka.red_flag_screening.suspected_syndrome

    # 4. Amavata mimic with Septic Arthritis
    intake_septic = ClinicalIntakeData(
        patient_id="PAT-MIMIC-SEPTIC",
        hospital_id="aiia-delhi-central-001",
        chief_complaints=["Single red swollen right knee with intense local heat and high fever"],
        symptoms=["acute monoarthritis", "single red swollen joint", "septic joint"],
        duration_weeks=0.5,
        temperature_fahrenheit=102.5,
        rogi_bala=RogiBalaGrade.AVARA,
        systolic_bp=115,
        diastolic_bp=75,
        hemoglobin_g_dl=11.5,
        is_pregnant=False,
        age_years=35
    )
    resp_septic = evaluate_clinical_diagnosis(intake_septic)
    assert resp_septic.governance_status == GovernanceStatus.EMERGENCY_TRANSFER_TRIGGERED
    assert resp_septic.red_flag_screening.mimic_detected is True
    assert "Septic Arthritis" in resp_septic.red_flag_screening.suspected_syndrome

    # 5. Malignancy mimic
    intake_cancer = ClinicalIntakeData(
        patient_id="PAT-MIMIC-CANCER",
        hospital_id="aiia-delhi-central-001",
        chief_complaints=["Painless rectal bleeding with severe unexplained weight loss"],
        symptoms=["painless rectal bleeding", "unexplained weight loss", "altered bowel habit > 6 weeks"],
        duration_weeks=8.0,
        rogi_bala=RogiBalaGrade.AVARA,
        systolic_bp=110,
        diastolic_bp=70,
        hemoglobin_g_dl=8.5,
        is_pregnant=False,
        age_years=58
    )
    resp_cancer = evaluate_clinical_diagnosis(intake_cancer)
    assert resp_cancer.governance_status == GovernanceStatus.EMERGENCY_TRANSFER_TRIGGERED
    assert resp_cancer.red_flag_screening.mimic_detected is True
    assert "Colorectal Malignancy" in resp_cancer.red_flag_screening.suspected_syndrome
