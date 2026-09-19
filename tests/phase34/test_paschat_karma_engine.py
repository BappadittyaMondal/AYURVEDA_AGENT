"""
Phase 34: Unit Tests for Paschat Karma & Samsarjana Krama Core Engine
====================================================================
Verifies:
1. Canonical Annakala graduated dietary ladder generation (Pravara, Madhyama, Avara)
2. Caloric and digestibility staircase progression
3. Persistent episode lifecycle management (Table 74)
4. Meal-by-meal logging and digestive tolerance evaluations (Table 75)
5. Agni kindling trajectory curve and adverse symptom handling
6. Ashta Mahadosha / Parihara Vishaya adherence audits
7. Statutory Rasayana & Vajikarana readiness certification
"""

import pytest
import sqlite3
from core.database import get_sqlite_connection, init_database
from core.paschat_karma import (
    calculate_samsarjana_ladder,
    initiate_paschat_karma_episode,
    get_paschat_karma_episode,
    get_patient_paschat_episodes,
    log_samsarjana_meal,
    list_samsarjana_meal_logs,
    compute_samsarjana_trajectory,
    audit_parihara_adherence,
    evaluate_rasayana_readiness,
)
from models.panchakarma import ShuddhiGrade
from models.paschat_karma import (
    DietaryLadderForm,
    AnnakalaMealTime,
    AgniRestorationStatus,
    DigestionTolerance,
    PariharaProhibition,
    EpisodeStatus,
    PaschatKarmaEpisodeCreate,
    SamsarjanaMealLogCreate,
    PariharaAdherenceAuditRequest,
)


@pytest.fixture
def conn():
    """Provides a thread-safe database connection."""
    init_database()
    connection = get_sqlite_connection()
    yield connection
    connection.close()


def test_samsarjana_ladder_generation():
    """Verify classical Annakala counts and sequence for all three Shuddhi grades."""
    # 1. Pravara Shuddhi (Superior): 14 Annakalas, 7 Days
    pravara_ladder = calculate_samsarjana_ladder(ShuddhiGrade.PRAVARA)
    assert len(pravara_ladder) == 14
    assert pravara_ladder[-1].day_number == 7
    # Verify sequence: 3 Peya, 3 Vilepi, 3 Akrita Yusha, 3 Krita Yusha, 1 Mamsa Rasa, 1 Normal Diet
    forms = [s.prescribed_diet_form for s in pravara_ladder]
    assert forms[0:3] == [DietaryLadderForm.PEYA] * 3
    assert forms[3:6] == [DietaryLadderForm.VILEPI] * 3
    assert forms[6:9] == [DietaryLadderForm.AKRITA_YUSHA] * 3
    assert forms[9:12] == [DietaryLadderForm.KRITA_YUSHA] * 3
    assert forms[12] == DietaryLadderForm.MAMSA_RASA
    assert forms[13] == DietaryLadderForm.NORMAL_DIET

    # 2. Madhyama Shuddhi (Moderate): 10 Annakalas, 5 Days
    madhyama_ladder = calculate_samsarjana_ladder(ShuddhiGrade.MADHYAMA)
    assert len(madhyama_ladder) == 10
    assert madhyama_ladder[-1].day_number == 5
    m_forms = [s.prescribed_diet_form for s in madhyama_ladder]
    assert m_forms[0:2] == [DietaryLadderForm.PEYA] * 2
    assert m_forms[2:4] == [DietaryLadderForm.VILEPI] * 2
    assert m_forms[4:6] == [DietaryLadderForm.AKRITA_YUSHA] * 2
    assert m_forms[6:8] == [DietaryLadderForm.KRITA_YUSHA] * 2
    assert m_forms[8] == DietaryLadderForm.MAMSA_RASA
    assert m_forms[9] == DietaryLadderForm.NORMAL_DIET

    # 3. Avara Shuddhi (Minimum): 6 Annakalas, 3 Days
    avara_ladder = calculate_samsarjana_ladder(ShuddhiGrade.AVARA)
    assert len(avara_ladder) == 6
    assert avara_ladder[-1].day_number == 3
    a_forms = [s.prescribed_diet_form for s in avara_ladder]
    assert a_forms == [
        DietaryLadderForm.PEYA,
        DietaryLadderForm.VILEPI,
        DietaryLadderForm.AKRITA_YUSHA,
        DietaryLadderForm.KRITA_YUSHA,
        DietaryLadderForm.MAMSA_RASA,
        DietaryLadderForm.NORMAL_DIET
    ]


def test_caloric_and_digestibility_staircase():
    """Verify that calories and digestibility progress strictly upward across Annakalas."""
    ladder = calculate_samsarjana_ladder(ShuddhiGrade.PRAVARA)
    
    first_step = ladder[0]
    last_step = ladder[-1]

    # First step (Peya) must be ultra-light
    assert first_step.caloric_estimate_kcal < 200.0
    assert first_step.digestibility_index <= 0.20
    assert first_step.meal_time_type == AnnakalaMealTime.PRATAH_KALPA

    # Last step (Normal Diet) must provide solid nutrition
    assert last_step.caloric_estimate_kcal > 800.0
    assert last_step.digestibility_index == 1.00
    assert last_step.meal_time_type == AnnakalaMealTime.SAYAM_KALPA

    # Monotonic progression check across stages
    peya_cals = [s.caloric_estimate_kcal for s in ladder if s.prescribed_diet_form == DietaryLadderForm.PEYA]
    vilepi_cals = [s.caloric_estimate_kcal for s in ladder if s.prescribed_diet_form == DietaryLadderForm.VILEPI]
    akrita_cals = [s.caloric_estimate_kcal for s in ladder if s.prescribed_diet_form == DietaryLadderForm.AKRITA_YUSHA]
    normal_cals = [s.caloric_estimate_kcal for s in ladder if s.prescribed_diet_form == DietaryLadderForm.NORMAL_DIET]

    assert max(peya_cals) < min(vilepi_cals)
    assert max(vilepi_cals) < min(akrita_cals)
    assert max(akrita_cals) < min(normal_cals)


def test_episode_lifecycle_and_persistence(conn):
    """Test full episode creation, database storage, and retrieval."""
    req = PaschatKarmaEpisodeCreate(
        patient_id="PAT-PASCHAT-TEST-001",
        hospital_id="aiia-delhi-central-001",
        plan_id="PLAN-PK-TEST-99",
        procedure_type="VIRECHANA",
        shuddhi_grade=ShuddhiGrade.MADHYAMA,
        attending_physician_arn="ARN-NCISM-2015-8832"
    )

    episode = initiate_paschat_karma_episode(req, conn=conn)
    assert episode.episode_id.startswith("EPISODE-PASCHAT-")
    assert episode.total_annakalas == 10
    assert episode.total_days == 5
    assert episode.current_annakala == 1
    assert episode.status == EpisodeStatus.IN_PROGRESS
    assert episode.agni_restoration_status == AgniRestorationStatus.MANDAGNI_POST_SHODHANA
    assert not episode.rasayana_readiness

    # Fetch from database
    fetched = get_paschat_karma_episode(episode.episode_id, conn=conn)
    assert fetched.episode_id == episode.episode_id
    assert fetched.patient_id == "PAT-PASCHAT-TEST-001"
    assert len(fetched.schedule) == 10

    # Test list for patient
    patient_episodes = get_patient_paschat_episodes("PAT-PASCHAT-TEST-001", conn=conn)
    assert len(patient_episodes) >= 1
    assert patient_episodes[0].episode_id == episode.episode_id


def test_meal_logging_and_agni_transition(conn):
    """Test Annakala meal logging, advancing current Annakala, and updating Agni status."""
    req = PaschatKarmaEpisodeCreate(
        patient_id="PAT-PASCHAT-MEAL-002",
        hospital_id="aiia-delhi-central-001",
        plan_id="PLAN-PK-TEST-100",
        procedure_type="VAMANA",
        shuddhi_grade=ShuddhiGrade.AVARA,  # 6 Annakalas
        attending_physician_arn="ARN-NCISM-2015-8832"
    )
    episode = initiate_paschat_karma_episode(req, conn=conn)

    # Log Meal 1: Peya (Sukha Paka)
    meal1_req = SamsarjanaMealLogCreate(
        annakala_number=1,
        patient_appetite_observed="ALPA_KSHUDHA",
        digestion_tolerance_noted=DigestionTolerance.SUKHA_PAKA,
        compliance_status="CONSUMED_AS_PRESCRIBED",
        clinical_notes="Tolerated 150ml Peya well without nausea.",
        nurse_or_practitioner_id="nurse-ayush-001"
    )
    meal1_resp = log_samsarjana_meal(episode.episode_id, meal1_req, conn=conn)
    assert meal1_resp.prescribed_diet_form == DietaryLadderForm.PEYA
    assert meal1_resp.annakala_number == 1
    assert meal1_resp.digestion_tolerance_noted == DigestionTolerance.SUKHA_PAKA

    # Check updated episode
    ep_after_1 = get_paschat_karma_episode(episode.episode_id, conn=conn)
    assert ep_after_1.current_annakala == 2

    # Log Meal 2: Vilepi (Sukha Paka)
    meal2_req = SamsarjanaMealLogCreate(
        annakala_number=2,
        patient_appetite_observed="MADHYAMA_KSHUDHA",
        digestion_tolerance_noted=DigestionTolerance.SUKHA_PAKA,
        nurse_or_practitioner_id="nurse-ayush-001"
    )
    log_samsarjana_meal(episode.episode_id, meal2_req, conn=conn)

    # Log Meal 3: Akrita Yusha
    meal3_req = SamsarjanaMealLogCreate(
        annakala_number=3,
        patient_appetite_observed="MADHYAMA_KSHUDHA",
        digestion_tolerance_noted=DigestionTolerance.SUKHA_PAKA,
        nurse_or_practitioner_id="nurse-ayush-001"
    )
    log_samsarjana_meal(episode.episode_id, meal3_req, conn=conn)

    ep_after_3 = get_paschat_karma_episode(episode.episode_id, conn=conn)
    # Beyond Annakala 2, Agni status transitions to GRADUAL_KINDLING
    assert ep_after_3.agni_restoration_status == AgniRestorationStatus.GRADUAL_KINDLING

    logs = list_samsarjana_meal_logs(episode.episode_id, conn=conn)
    assert len(logs) == 3


def test_trajectory_and_complication_handling(conn):
    """Test Agni kindling calculation and detection of digestive distress (Vidahi / Ajirna)."""
    req = PaschatKarmaEpisodeCreate(
        patient_id="PAT-PASCHAT-DISTRESS",
        hospital_id="aiia-delhi-central-001",
        plan_id="PLAN-PK-TEST-101",
        procedure_type="VIRECHANA",
        shuddhi_grade=ShuddhiGrade.AVARA,
        attending_physician_arn="ARN-NCISM-2015-8832"
    )
    episode = initiate_paschat_karma_episode(req, conn=conn)

    # Log Meal 1 with severe heartburn (Vidahi)
    log_samsarjana_meal(
        episode.episode_id,
        SamsarjanaMealLogCreate(
            annakala_number=1,
            patient_appetite_observed="ALPA_KSHUDHA",
            digestion_tolerance_noted=DigestionTolerance.VIDAHI,
            clinical_notes="Acid regurgitation observed 1 hr after Peya.",
            nurse_or_practitioner_id="nurse-ayush-001"
        ),
        conn=conn
    )

    trajectory = compute_samsarjana_trajectory(episode.episode_id, conn=conn)
    assert trajectory.intolerance_events_count == 1
    assert any("ADVERSE DIGESTIVE SIGNS DETECTED" in r for r in trajectory.recommendations)
    assert any("DEEPANA-PACHANA" in r for r in trajectory.recommendations)


def test_parihara_vishaya_auditing(conn):
    """Verify compliance checking against classical Ashta Mahadosha prohibitions."""
    req = PaschatKarmaEpisodeCreate(
        patient_id="PAT-PARIHARA-001",
        hospital_id="aiia-delhi-central-001",
        plan_id="PLAN-PK-TEST-102",
        procedure_type="VAMANA",
        shuddhi_grade=ShuddhiGrade.MADHYAMA,
        attending_physician_arn="ARN-NCISM-2015-8832"
    )
    episode = initiate_paschat_karma_episode(req, conn=conn)

    # Case A: Fully Compliant
    audit_clean = audit_parihara_adherence(
        episode.episode_id,
        PariharaAdherenceAuditRequest(reported_violations=[], audited_by_staff_id="nurse-001"),
        conn=conn
    )
    assert audit_clean.is_compliant
    assert audit_clean.risk_severity == "NONE"

    # Case B: Violations Reported (Day sleep + rough vehicle travel)
    audit_violation = audit_parihara_adherence(
        episode.episode_id,
        PariharaAdherenceAuditRequest(
            reported_violations=[PariharaProhibition.DIVASVAPNA_MAITHUNA, PariharaProhibition.RATHA_KSHOBHA],
            audited_by_staff_id="nurse-001",
            notes="Patient travelled by auto-rickshaw and slept in the afternoon."
        ),
        conn=conn
    )
    assert not audit_violation.is_compliant
    assert audit_violation.risk_severity in ("MODERATE", "HIGH")
    assert len(audit_violation.remedial_measures) >= 2


def test_rasayana_readiness_certification(conn):
    """Verify that Rasayana clearance requires 100% Annakala completion with Sukha Paka."""
    req = PaschatKarmaEpisodeCreate(
        patient_id="PAT-RASAYANA-READY-001",
        hospital_id="aiia-delhi-central-001",
        plan_id="PLAN-PK-TEST-103",
        procedure_type="VIRECHANA",
        shuddhi_grade=ShuddhiGrade.AVARA,  # 6 Annakalas
        attending_physician_arn="ARN-NCISM-2015-8832"
    )
    episode = initiate_paschat_karma_episode(req, conn=conn)

    # Incomplete: only 3 meals logged
    for k in range(1, 4):
        log_samsarjana_meal(
            episode.episode_id,
            SamsarjanaMealLogCreate(
                annakala_number=k,
                patient_appetite_observed="MADHYAMA_KSHUDHA",
                digestion_tolerance_noted=DigestionTolerance.SUKHA_PAKA,
                nurse_or_practitioner_id="nurse-ayush-001"
            ),
            conn=conn
        )

    readiness_incomplete = evaluate_rasayana_readiness(episode.episode_id, conn=conn)
    assert not readiness_incomplete.is_ready_for_rasayana

    # Complete remaining 3 meals (Meals 4, 5, 6)
    for k in range(4, 7):
        log_samsarjana_meal(
            episode.episode_id,
            SamsarjanaMealLogCreate(
                annakala_number=k,
                patient_appetite_observed="PRAVARA_KSHUDHA",
                digestion_tolerance_noted=DigestionTolerance.SUKHA_PAKA,
                nurse_or_practitioner_id="nurse-ayush-001"
            ),
            conn=conn
        )

    readiness_complete = evaluate_rasayana_readiness(episode.episode_id, conn=conn)
    assert readiness_complete.is_ready_for_rasayana
    assert len(readiness_complete.recommended_rasayana_classes) >= 3

    # Confirm episode updated to COMPLETED in database
    final_episode = get_paschat_karma_episode(episode.episode_id, conn=conn)
    assert final_episode.status == EpisodeStatus.COMPLETED
    assert final_episode.rasayana_readiness
    assert final_episode.completed_at is not None
