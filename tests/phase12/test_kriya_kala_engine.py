"""Unit tests for Shat Kriya Kala Pathological Stage Tracker & Progression Engine (6 Stages)."""
import pytest
from core.kriya_kala import (
    calculate_kriya_kala_distribution,
    evaluate_prognosis_and_directives,
)
from models.kriya_kala import (
    KriyaKalaStage,
    CurabilityPrognosis,
    StageObservationInput,
)


def test_sanchaya_early_accumulation():
    """Verify Stage 1 (Sanchaya) attribution, high reversibility, and Sukhasadhya prognosis."""
    obs = StageObservationInput(
        sanchaya_features=3,
        prakopa_features=0,
        prasara_features=0,
        sthanasamshraya_features=0,
        vyakti_features=0,
        bheda_features=0,
    )
    probs, primary_stage, ppi = calculate_kriya_kala_distribution(obs)

    assert primary_stage == KriyaKalaStage.SANCHAYA
    assert ppi < 1.8
    assert sum(probs.values()) == pytest.approx(1.0, abs=1e-3)
    assert probs["SANCHAYA"] > 0.8

    reversibility, prognosis, directive = evaluate_prognosis_and_directives(primary_stage, ppi)
    assert reversibility >= 90.0
    assert prognosis == CurabilityPrognosis.SUKHASADHYA
    assert "Sanchaya" in directive


def test_sthanasamshraya_prodromal_window():
    """Verify Stage 4 (Sthanasamshraya) localization with Purvaroopa prodrome."""
    obs = StageObservationInput(
        sanchaya_features=0,
        prakopa_features=0,
        prasara_features=1,
        sthanasamshraya_features=3,
        prodromal_symptoms=["Aruchi (Prodromal anorexia)", "Alasya (Profound languor)", "Angamarda (Vague body aches)"],
        vyakti_features=0,
        bheda_features=0,
    )
    probs, primary_stage, ppi = calculate_kriya_kala_distribution(obs)

    assert primary_stage == KriyaKalaStage.STHANASAMSHRAYA
    assert 3.5 <= ppi <= 4.8
    assert probs["STHANASAMSHRAYA"] > 0.6

    reversibility, prognosis, directive = evaluate_prognosis_and_directives(primary_stage, ppi)
    assert 55.0 <= reversibility <= 75.0
    assert prognosis == CurabilityPrognosis.KRICHRASADHYA
    assert "Purvaroopa" in directive


def test_vyakti_full_disease_manifestation():
    """Verify Stage 5 (Vyakti) full disease manifestation."""
    obs = StageObservationInput(
        sanchaya_features=0,
        prakopa_features=0,
        prasara_features=0,
        sthanasamshraya_features=1,
        vyakti_features=3,
        manifest_symptoms=["High fever (Santapa)", "Intense shivering (Sheeta)", "Sweating crisis (Sveda-pravritti)"],
        bheda_features=0,
    )
    _, primary_stage, ppi = calculate_kriya_kala_distribution(obs)

    assert primary_stage == KriyaKalaStage.VYAKTI
    assert 4.5 <= ppi <= 5.4

    reversibility, prognosis, directive = evaluate_prognosis_and_directives(primary_stage, ppi)
    assert reversibility <= 55.0
    assert prognosis == CurabilityPrognosis.KRICHRASADHYA
    assert "Vyadhi-pratyanika" in directive


def test_bheda_chronic_complicated_stage():
    """Verify Stage 6 (Bheda) chronicity, ulceration, and Yapya/Asadhya prognosis."""
    obs = StageObservationInput(
        sanchaya_features=0,
        prakopa_features=0,
        prasara_features=0,
        sthanasamshraya_features=0,
        vyakti_features=1,
        bheda_features=3,
        complications=["Tissue ulceration (Vrana)", "Severe emaciation (Kshaya)", "Secondary ascites (Udara)"],
    )
    _, primary_stage, ppi = calculate_kriya_kala_distribution(obs)

    assert primary_stage == KriyaKalaStage.BHEDA
    assert ppi >= 5.5

    reversibility, prognosis, _ = evaluate_prognosis_and_directives(primary_stage, ppi)
    assert reversibility <= 36.0
    assert prognosis in [CurabilityPrognosis.YAPYA, CurabilityPrognosis.ASADHYA]
