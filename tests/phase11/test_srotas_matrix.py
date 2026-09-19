"""Unit tests for Srotas Pathology Matrix & Khavaigunya Mapping Engine (14 Channels)."""
import pytest
from core.srotas import (
    evaluate_channel_pathology,
    evaluate_srotas_matrix,
    MULA_STHANA_REGISTRY,
    SROTOSHODHANA_REGISTRY,
)
from models.srotas import (
    SrotasType,
    DushtiType,
    ChannelObservation,
    SrotasInput,
)


def test_channel_pathology_prakrita_and_severities():
    """Verify pathological grading, dominant Dushti classification, and Khavaigunya mapping."""
    # 1. Normal patent channel (Prakrita)
    prakrita_obs = ChannelObservation(srotas=SrotasType.PRANAVAHA)
    score, dushti, khavaigunya, _ = evaluate_channel_pathology(prakrita_obs)
    assert score == 0.0
    assert dushti == DushtiType.PRAKRITA
    assert khavaigunya is False

    # 2. Prominent Sanga (Obstruction)
    sanga_obs = ChannelObservation(
        srotas=SrotasType.PRANAVAHA,
        sanga=3,
        ati_pravritti=1,
    )
    score_s, dushti_s, khavaigunya_s, man_s = evaluate_channel_pathology(sanga_obs)
    # (4 / 12) * 100 = 33.33%
    assert score_s == pytest.approx(33.33, abs=0.1)
    assert dushti_s == DushtiType.SANGA
    assert "Sanga" in man_s

    # 3. Severe Ati-pravritti exceeding Khavaigunya threshold (>= 35%)
    ati_obs = ChannelObservation(
        srotas=SrotasType.MUTRAVAHA,
        ati_pravritti=3,
        sanga=2,
    )
    score_a, dushti_a, khavaigunya_a, _ = evaluate_channel_pathology(ati_obs)
    # (5 / 12) * 100 = 41.67%
    assert score_a > 35.0
    assert dushti_a == DushtiType.ATI_PRAVRITTI
    assert khavaigunya_a is True

    # 4. Pre-existing defect triggers Khavaigunya even with low score
    defect_obs = ChannelObservation(
        srotas=SrotasType.PURISHAVAHA,
        sanga=1,
        pre_existing_defect=True,
    )
    _, _, khavaigunya_d, _ = evaluate_channel_pathology(defect_obs)
    assert khavaigunya_d is True


def test_evaluate_srotas_matrix_comprehensive():
    """Verify matrix evaluation across multiple channels and directive generation."""
    channels = [
        ChannelObservation(srotas=SrotasType.PRANAVAHA, sanga=3, ati_pravritti=1),
        ChannelObservation(srotas=SrotasType.ANNAVAHA, sanga=2, vimarga_gamana=2),
        ChannelObservation(srotas=SrotasType.PURISHAVAHA, sanga=3, pre_existing_defect=True),
        ChannelObservation(srotas=SrotasType.RASAVAHA, ati_pravritti=0, sanga=0),
    ]
    inp = SrotasInput(patient_id="pat-test-11", channels=channels)
    output = evaluate_srotas_matrix(inp, evaluator_arn="ARN-NCISM-2020-1111", hospital_id="hosp-01")

    assert output.patient_id == "pat-test-11"
    assert len(output.channel_details) == 4
    assert len(output.khavaigunya_channels) >= 2  # Purishavaha (defect) and Annavaha (score 33.33% or Pranavaha)
    assert output.overall_srotas_index > 0.0
    assert len(output.srotoshodhana_directives) == 3  # Pranavaha, Annavaha, Purishavaha


def test_registry_completeness():
    """Ensure all 14 classical channels are registered in Mula Sthana and Srotoshodhana databases."""
    assert len(MULA_STHANA_REGISTRY) == 14
    assert len(SROTOSHODHANA_REGISTRY) == 14
    for srotas in SrotasType:
        assert srotas in MULA_STHANA_REGISTRY
        assert srotas in SROTOSHODHANA_REGISTRY
