"""Phase 03: Test Suite for Vikriti Mathematical Vector Calculus, KL Divergence & VSI."""
import pytest
from core.vikriti import (
    VIKRITI_SYMPTOMS,
    compute_doshic_deltas,
    compute_kl_divergence,
    compute_mahalanobis_distance,
    compute_vikriti_vector,
    compute_vsi,
)
from models.vikriti import DoshicDeviationState, VikritiSeverityTier


def test_kl_divergence_properties():
    """Verify Kullback-Leibler divergence identity and non-negativity."""
    prakriti = (0.3333, 0.3333, 0.3334)

    # 1. Identity: D_KL(P || P) == 0.0
    kl_zero = compute_kl_divergence(prakriti, prakriti)
    assert kl_zero == 0.0, f"Expected 0.0, got {kl_zero}"

    # 2. Non-negativity: D_KL(V || P) >= 0.0
    vikriti_vata = (0.80, 0.10, 0.10)
    kl_vata = compute_kl_divergence(vikriti_vata, prakriti)
    assert kl_vata > 0.0, f"Expected positive KL divergence, got {kl_vata}"
    assert 0.45 <= kl_vata <= 0.47, f"Expected analytical KL divergence ~0.4597, got {kl_vata}"


def test_mahalanobis_distance_properties():
    """Verify Mahalanobis distance metric on 2D projected simplex subspace."""
    prakriti = (0.3333, 0.3333, 0.3334)

    # 1. Identity: D_M(P, P) == 0.0
    dm_zero = compute_mahalanobis_distance(prakriti, prakriti)
    assert dm_zero == 0.0, f"Expected 0.0, got {dm_zero}"

    # 2. Distance increases with constitutional perturbation
    vikriti_mild = (0.45, 0.30, 0.25)
    vikriti_severe = (0.85, 0.075, 0.075)

    dm_mild = compute_mahalanobis_distance(vikriti_mild, prakriti)
    dm_severe = compute_mahalanobis_distance(vikriti_severe, prakriti)

    assert dm_mild > 0.0
    assert dm_severe > dm_mild, f"Expected severe ({dm_severe}) > mild ({dm_mild})"


def test_vsi_stratification_and_bounds():
    """Verify that VSI scales appropriately from 0 to 100 and stratifies tiers."""
    # 1. Samadosha (identical)
    vsi_0, tier_0, _ = compute_vsi(0.0, 0.0)
    assert vsi_0 == 0.0
    assert tier_0 == VikritiSeverityTier.SAMADOSHA

    # 2. Alpa Vikriti (mild divergence)
    vsi_alpa, tier_alpa, _ = compute_vsi(0.20, 0.80)
    assert 15.0 <= vsi_alpa < 40.0
    assert tier_alpa == VikritiSeverityTier.ALPA_VIKRITI

    # 3. Madhyama Vikriti (moderate divergence)
    vsi_mod, tier_mod, _ = compute_vsi(0.60, 1.80)
    assert 40.0 <= vsi_mod < 75.0
    assert tier_mod == VikritiSeverityTier.MADHYAMA_VIKRITI

    # 4. Tivra Vikriti (severe divergence)
    vsi_tivra, tier_tivra, _ = compute_vsi(1.80, 3.50)
    assert vsi_tivra >= 75.0
    assert tier_tivra == VikritiSeverityTier.TIVRA_VIKRITI


def test_directional_doshic_deltas():
    """Verify calculation of Vriddhi, Kshaya, and Sama states."""
    prakriti = (0.30, 0.40, 0.30)
    # Vata increases significantly (+0.30), Pitta decreases (-0.25), Kapha mildly drops (-0.05)
    vikriti = (0.60, 0.15, 0.25)

    deltas = compute_doshic_deltas(vikriti, prakriti)

    assert deltas.vata.state == DoshicDeviationState.VRIDDHI
    assert deltas.vata.delta == 0.30
    assert deltas.dominant_vitiation == "VATA"

    assert deltas.pitta.state == DoshicDeviationState.KSHAYA
    assert deltas.pitta.delta == -0.25

    assert deltas.kapha.state == DoshicDeviationState.SAMA
    assert deltas.kapha.delta == -0.05


def test_vikriti_vector_symptom_mapping():
    """Verify symptom severity aggregation and normalization."""
    # Only Pitta symptoms severe (VS09 to VS16 all = 3)
    symptoms = {f"VS{i:02d}": 3 for i in range(9, 17)}
    v, p, k = compute_vikriti_vector(symptoms)

    assert abs((v + p + k) - 1.0) < 1e-4
    assert p > 0.95
    assert v < 0.05
    assert k < 0.05
