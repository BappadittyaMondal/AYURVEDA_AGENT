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
        rogi_bala=RogiBalaGrade.MADHYAMA
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
        diastolic_bp=70
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
        appetite_and_digestion="VARIABLE_VISHAMAGNI"
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
