"""Unit tests for Roga Rogi Bala Ganan Yantra (Bi-Directional Balance Engine)."""
import pytest
from core.roga_rogi_bala import (
    calculate_rogi_bala,
    calculate_roga_bala,
    evaluate_therapeutic_governor,
)
from models.roga_rogi_bala import (
    RogiBalaInput,
    RogaBalaInput,
    TherapeuticCategory,
    ShodhanaEligibilityStatus,
)


def test_rogi_bala_calculation_extremes():
    """Verify Rogi Bala calculation boundaries (0 to 100)."""
    # Max vitality
    max_rogi = RogiBalaInput(
        sahaja_bala=1.0,
        kalaja_bala=1.0,
        yuktikrita_bala=1.0,
        dhatu_sarata_osi=100.0,
        sattva_score=1.0,
        agni_strength=1.0,
    )
    assert calculate_rogi_bala(max_rogi) == 100.0

    # Min vitality
    min_rogi = RogiBalaInput(
        sahaja_bala=0.0,
        kalaja_bala=0.0,
        yuktikrita_bala=0.0,
        dhatu_sarata_osi=0.0,
        sattva_score=0.0,
        agni_strength=0.0,
    )
    assert calculate_rogi_bala(min_rogi) == 0.0


def test_roga_bala_calculation_extremes():
    """Verify Roga Bala calculation boundaries (0 to 100)."""
    # Max virulence
    max_roga = RogaBalaInput(
        vikriti_vsi=100.0,
        srotas_involvement_osi=100.0,
        vulnerable_channels_count=14,
        kriya_kala_ppi=6.0,
        ama_agi_score=100.0,
        chronicity_months=36.0,
    )
    assert calculate_roga_bala(max_roga) == 100.0

    # Min virulence
    min_roga = RogaBalaInput(
        vikriti_vsi=0.0,
        srotas_involvement_osi=0.0,
        vulnerable_channels_count=0,
        kriya_kala_ppi=1.0,
        ama_agi_score=0.0,
        chronicity_months=0.0,
    )
    assert calculate_roga_bala(min_roga) == 0.0


def test_therapeutic_governor_case1_frail_host_strong_disease():
    """Case 1: Low host vitality against virulent disease -> STRICT SHODHANA CONTRAINDICATION."""
    ratio, diff, cat, scalar, elig, dirs = evaluate_therapeutic_governor(
        rogi_bala=35.0,
        roga_bala=75.0,
    )
    assert cat == TherapeuticCategory.CONTRAINDICATED_SHODHANA_EMERGENCY_BRIMHANA
    assert elig == ShodhanaEligibilityStatus.STRICTLY_CONTRAINDICATED
    assert scalar == 0.50
    assert diff < 0.0
    assert ratio < 1.0
    assert any("Vamana" in d.forbidden_procedures for d in dirs)


def test_therapeutic_governor_case2_robust_host_strong_disease():
    """Case 2: High host vitality and high disease virulence -> TIKSHNA SHODHANA ELIGIBILITY."""
    ratio, diff, cat, scalar, elig, dirs = evaluate_therapeutic_governor(
        rogi_bala=82.0,
        roga_bala=68.0,
    )
    assert cat == TherapeuticCategory.TIKSHNA_SHODHANA
    assert elig == ShodhanaEligibilityStatus.FULL_ELIGIBILITY
    assert scalar == 1.25
    assert any("Classical Vamana Karma" in d.permissible_panchakarma_procedures for d in dirs)


def test_therapeutic_governor_case3_robust_host_mild_disease():
    """Case 3: High host vitality with mild disease -> SHAMANA SUFFICIENT."""
    _, _, cat, scalar, elig, _ = evaluate_therapeutic_governor(
        rogi_bala=75.0,
        roga_bala=25.0,
    )
    assert cat == TherapeuticCategory.MADHYAMA_SHAMANA
    assert elig == ShodhanaEligibilityStatus.NOT_INDICATED
    assert scalar == 0.85


def test_therapeutic_governor_case4_frail_host_mild_disease():
    """Case 4: Low host vitality with mild disease -> MRIDU SHAMANA BRIMHANA."""
    _, _, cat, scalar, elig, _ = evaluate_therapeutic_governor(
        rogi_bala=30.0,
        roga_bala=25.0,
    )
    assert cat == TherapeuticCategory.MRIDU_SHAMANA_BRIMHANA
    assert elig == ShodhanaEligibilityStatus.NOT_INDICATED
    assert scalar == 0.60
