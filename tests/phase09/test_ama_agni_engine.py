"""Unit tests for Quantitative Ama Grading Index (AGI) and Agni Vector Gating Engine."""
import pytest
from core.ama_agni import (
    calculate_agi_score,
    classify_ama_grade,
    calculate_agni_vector,
    evaluate_gating_and_directives,
)
from models.ama_agni import (
    AgniType,
    AmaGrade,
    GatingStatus,
    AmaSymptomsInput,
    AgniParametersInput,
)


def test_agi_score_bounds_and_extremes():
    """Verify AGI boundaries: 0 for asymptomatic, 100 for maximum score."""
    # Zero symptoms
    no_sym = AmaSymptomsInput()
    assert calculate_agi_score(no_sym) == 0.0

    # Max symptoms (all 3)
    max_sym = AmaSymptomsInput(
        srotorodha=3,
        balabhramsha=3,
        gaurava=3,
        anilamudhata=3,
        alasya=3,
        apakti=3,
        nishthiva=3,
        malasanga=3,
        aruchi=3,
        klama=3,
    )
    assert calculate_agi_score(max_sym) == 100.0


def test_ama_grade_stratification():
    """Verify clinical grading boundaries."""
    assert classify_ama_grade(0.0) == AmaGrade.NIRAMA
    assert classify_ama_grade(19.9) == AmaGrade.NIRAMA
    assert classify_ama_grade(20.0) == AmaGrade.ALPA_AMA
    assert classify_ama_grade(44.9) == AmaGrade.ALPA_AMA
    assert classify_ama_grade(45.0) == AmaGrade.MADHYAMA_AMA
    assert classify_ama_grade(69.9) == AmaGrade.MADHYAMA_AMA
    assert classify_ama_grade(70.0) == AmaGrade.GURU_AMA
    assert classify_ama_grade(100.0) == AmaGrade.GURU_AMA


def test_agni_vector_simplex_properties():
    """Verify Agni Vector lies on Delta^3 simplex and reflects physiology."""
    # Balanced Samagni
    sama_params = AgniParametersInput(
        appetite_regularity=1.0,
        digestion_speed_hours=4.0,
        post_prandial_heaviness=0.0,
        burning_sensation=0.0,
        abdominal_distension=0.0,
    )
    vec_sama, primary_sama = calculate_agni_vector(sama_params)
    assert sum(vec_sama.values()) == pytest.approx(1.0, abs=1e-3)
    assert primary_sama == AgniType.SAMAGNI

    # Hypoactive Mandagni
    manda_params = AgniParametersInput(
        appetite_regularity=0.4,
        digestion_speed_hours=8.0,
        post_prandial_heaviness=0.9,
        burning_sensation=0.0,
        abdominal_distension=0.2,
    )
    vec_manda, primary_manda = calculate_agni_vector(manda_params)
    assert sum(vec_manda.values()) == pytest.approx(1.0, abs=1e-3)
    assert primary_manda == AgniType.MANDAGNI

    # Hyperactive Tikshnagni
    tikshna_params = AgniParametersInput(
        appetite_regularity=0.8,
        digestion_speed_hours=2.0,
        post_prandial_heaviness=0.0,
        burning_sensation=0.9,
        abdominal_distension=0.0,
    )
    vec_tikshna, primary_tikshna = calculate_agni_vector(tikshna_params)
    assert primary_tikshna == AgniType.TIKSHNAGNI

    # Erratic Vishamagni
    vishama_params = AgniParametersInput(
        appetite_regularity=0.1,
        digestion_speed_hours=3.0,
        post_prandial_heaviness=0.2,
        burning_sensation=0.1,
        abdominal_distension=0.9,
    )
    vec_vishama, primary_vishama = calculate_agni_vector(vishama_params)
    assert primary_vishama == AgniType.VISHAMAGNI


def test_shodhana_gating_firewall_rules():
    """Verify strict clinical safety firewall protecting against Apakva Dosha mobilization."""
    # 1. Guru Ama: Shodhana strictly forbidden, Emergency Langhana
    cleared_guru, status_guru, dir_guru = evaluate_gating_and_directives(
        ama_grade=AmaGrade.GURU_AMA,
        agni_type=AgniType.MANDAGNI,
        agi_score=85.0,
    )
    assert cleared_guru is False
    assert status_guru == GatingStatus.GATED_EMERGENCY_LANGHANA
    assert any("LANGHANA" in d.action_type for d in dir_guru)

    # 2. Madhyama Ama: Shodhana locked, Active Pachana
    cleared_mod, status_mod, dir_mod = evaluate_gating_and_directives(
        ama_grade=AmaGrade.MADHYAMA_AMA,
        agni_type=AgniType.MANDAGNI,
        agi_score=55.0,
    )
    assert cleared_mod is False
    assert status_mod == GatingStatus.GATED_FOR_DEEPANA_PACHANA

    # 3. Tikshnagni with Nirama: Shodhana gated until Pitta heat pacified
    cleared_tikshna, status_tikshna, dir_tikshna = evaluate_gating_and_directives(
        ama_grade=AmaGrade.NIRAMA,
        agni_type=AgniType.TIKSHNAGNI,
        agi_score=10.0,
    )
    assert cleared_tikshna is False
    assert status_tikshna == GatingStatus.GATED_TIKSHNAGNI_PACIFICATION

    # 4. Nirama with Samagni: Cleared for Shodhana Purvakarma
    cleared_ok, status_ok, dir_ok = evaluate_gating_and_directives(
        ama_grade=AmaGrade.NIRAMA,
        agni_type=AgniType.SAMAGNI,
        agi_score=8.0,
    )
    assert cleared_ok is True
    assert status_ok == GatingStatus.CLEARED_FOR_SHODHANA
    assert any("SNEHANA" in d.action_type for d in dir_ok)
