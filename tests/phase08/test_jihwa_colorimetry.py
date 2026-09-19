"""Unit tests for Jihwa Pariksha CIE-L*a*b* colorimetry, coating metrics, and Doshic vector formulation."""
import pytest
from core.jihwa_cv import (
    hex_to_rgb,
    rgb_to_cielab,
    classify_coating_thickness,
    classify_dominant_color,
    compute_ama_index,
    calculate_jihwa_doshic_vector,
    simulate_jihwa,
)
from models.jihwa import (
    CoatingThickness,
    DominantColor,
    TongueRegion,
    RegionColorimetry,
    JihwaInput,
)


def test_hex_to_rgb_and_cielab_conversion():
    """Verify sRGB to D65 CIE-L*a*b* conversion for standard calibration coordinates."""
    # Pure White #FFFFFF
    r, g, b = hex_to_rgb("#FFFFFF")
    l, a, b_val = rgb_to_cielab(r, g, b)
    assert l == pytest.approx(100.0, abs=1.0)
    assert abs(a) < 2.0
    assert abs(b_val) < 2.0

    # Pure Black #000000
    r, g, b = hex_to_rgb("#000000")
    l, a, b_val = rgb_to_cielab(r, g, b)
    assert l == pytest.approx(0.0, abs=0.5)

    # Pure Red #FF0000 -> positive a*
    r, g, b = hex_to_rgb("#FF0000")
    l, a, b_val = rgb_to_cielab(r, g, b)
    assert a > 70.0


def test_coating_thickness_boundaries():
    """Verify depth stratification across clinical percentage boundaries."""
    assert classify_coating_thickness(0.0) == CoatingThickness.NONE
    assert classify_coating_thickness(4.9) == CoatingThickness.NONE
    assert classify_coating_thickness(5.0) == CoatingThickness.THIN
    assert classify_coating_thickness(34.9) == CoatingThickness.THIN
    assert classify_coating_thickness(35.0) == CoatingThickness.MODERATE
    assert classify_coating_thickness(64.9) == CoatingThickness.MODERATE
    assert classify_coating_thickness(65.0) == CoatingThickness.THICK
    assert classify_coating_thickness(100.0) == CoatingThickness.THICK


def test_classify_dominant_color():
    """Test chromatic classification from CIE-L*a*b* features."""
    # Clean pink: low coating ratio, healthy pink coordinates
    pink = classify_dominant_color(cie_l=55.0, cie_a=20.0, cie_b=10.0, coating_ratio=2.0)
    assert pink == DominantColor.CLEAN_PINK

    # White: high L*, low saturation
    white = classify_dominant_color(cie_l=85.0, cie_a=0.0, cie_b=2.0, coating_ratio=70.0)
    assert white == DominantColor.WHITE

    # Yellow: high b*, moderate to high L*
    yellow = classify_dominant_color(cie_l=65.0, cie_a=15.0, cie_b=35.0, coating_ratio=50.0)
    assert yellow == DominantColor.YELLOW

    # Brown / Black: low L*
    dark = classify_dominant_color(cie_l=30.0, cie_a=5.0, cie_b=8.0, coating_ratio=20.0)
    assert dark == DominantColor.BROWN_BLACK


def test_ama_index_scoring():
    """Verify quantitative Ama scoring and binary Sama thresholding."""
    # High Ama: thick yellow/white coating, high moisture
    score_high, is_sama_high = compute_ama_index(
        coating_ratio=80.0,
        thickness=CoatingThickness.THICK,
        dominant_color=DominantColor.WHITE,
        moisture=0.8,
    )
    assert score_high >= 70.0
    assert is_sama_high is True

    # Low / Nirama: clear mucosa, no coating
    score_low, is_sama_low = compute_ama_index(
        coating_ratio=2.0,
        thickness=CoatingThickness.NONE,
        dominant_color=DominantColor.CLEAN_PINK,
        moisture=0.5,
    )
    assert score_low < 15.0
    assert is_sama_low is False


def test_jihwa_doshic_vector_simplex_properties():
    """Verify Doshic vector sums to 1.0 on Delta^2 with Dirichlet boundary."""
    regions = [
        RegionColorimetry(region=TongueRegion.ROOT, rgb_hex="#F0F0F0", cie_l=85.0, cie_a=1.0, cie_b=3.0),
        RegionColorimetry(region=TongueRegion.CENTER, rgb_hex="#E8E8E8", cie_l=82.0, cie_a=0.5, cie_b=2.0),
        RegionColorimetry(region=TongueRegion.TIP_MARGINS, rgb_hex="#E0E0E0", cie_l=80.0, cie_a=1.2, cie_b=4.0),
    ]
    inp = JihwaInput(
        patient_id="pat-test-01",
        coating_ratio_percent=75.0,
        fissure_density=0.0,
        papillary_roughness=0.1,
        regions=regions,
        observed_moisture=0.8,
    )

    w_v, w_p, w_k, primary = calculate_jihwa_doshic_vector(
        data=inp,
        avg_l=82.3,
        avg_a=0.9,
        avg_b=3.0,
        dominant_color=DominantColor.WHITE,
        thickness=CoatingThickness.THICK,
        ama_score=75.0,
    )

    assert w_v + w_p + w_k == pytest.approx(1.0, abs=1e-3)
    assert w_v >= 1e-4
    assert w_p >= 1e-4
    assert w_k >= 1e-4
    assert primary == "KAPHA"


def test_simulation_all_clinical_phenotypes():
    """Verify synthetic tongue biometric generation across classical conditions."""
    for cond in ["VATA_DRY", "PITTA_INFLAMED", "KAPHA_AMA", "HEALTHY_NIRAMA"]:
        sim = simulate_jihwa(cond)
        assert sim.target_condition == cond
        assert len(sim.regions) == 3
        assert len(sim.classical_reference) > 10
        assert sim.expected_dominant_color in list(DominantColor)
