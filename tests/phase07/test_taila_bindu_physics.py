"""Unit tests for Taila Bindu Pariksha fluid mechanics, Ramanujan ellipse geometry, and prognosis."""
import math
import pytest
from core.taila_bindu import (
    calculate_spreading_coefficient,
    calculate_ellipse_geometry,
    calculate_spreading_velocity,
    infer_doshic_shape,
    determine_prognosis,
    simulate_taila_bindu,
)
from models.taila_bindu import CompassDirection, DoshicShape, PrognosisVerdict


def test_spreading_coefficient_harkins():
    """Verify S = gamma_urine - gamma_oil - gamma_interface."""
    # Standard normal urine
    s = calculate_spreading_coefficient(gamma_urine=65.0, gamma_oil=32.5, gamma_interface=15.0)
    assert s == pytest.approx(17.5, abs=1e-3)

    # Low surface tension urine (e.g., severe bile salts/proteinuria)
    s_low = calculate_spreading_coefficient(gamma_urine=45.0, gamma_oil=32.5, gamma_interface=15.0)
    assert s_low == pytest.approx(-2.5, abs=1e-3)


def test_ellipse_geometry_perfect_circle():
    """For a circle (a = b = 10mm), eccentricity must be 0 and circularity must be 1.0."""
    area, perimeter, eccentricity, circularity = calculate_ellipse_geometry(10.0, 10.0)

    expected_area = math.pi * 100.0
    expected_perimeter = 2.0 * math.pi * 10.0

    assert area == pytest.approx(expected_area, abs=1e-3)
    assert perimeter == pytest.approx(expected_perimeter, abs=1e-2)
    assert eccentricity == pytest.approx(0.0, abs=1e-4)
    assert circularity == pytest.approx(1.0, abs=1e-3)


def test_ellipse_geometry_elongated_serpentine():
    """For an elongated ellipse (a = 20mm, b = 5mm), check Ramanujan formula and metrics."""
    area, perimeter, eccentricity, circularity = calculate_ellipse_geometry(20.0, 5.0)

    # Area = pi * 20 * 5 = 100 * pi approx 314.159
    assert area == pytest.approx(100.0 * math.pi, abs=1e-2)

    # Eccentricity = sqrt(1 - 25/400) = sqrt(375/400) = sqrt(0.9375) approx 0.9682
    expected_ecc = math.sqrt(1.0 - (25.0 / 400.0))
    assert eccentricity == pytest.approx(expected_ecc, abs=1e-4)

    # Circularity must be significantly less than 1.0
    assert circularity < 0.65
    assert circularity > 0.0


def test_spreading_velocity():
    """Verify spreading velocity v = a / t."""
    v = calculate_spreading_velocity(semi_major_a=15.0, observation_time_sec=5.0)
    assert v == pytest.approx(3.0, abs=1e-3)

    # Minimum time safeguard
    v_zero = calculate_spreading_velocity(semi_major_a=15.0, observation_time_sec=0.0)
    assert v_zero == pytest.approx(150.0, abs=1e-2)


def test_doshic_shape_morphology_inference():
    """Verify morphological mapping from physical kinematics."""
    # Submerged -> NIMAGNA
    assert infer_doshic_shape(10, 10, 5, 1, submerged=True) == DoshicShape.NIMAGNA

    # High fragments -> CHURNA
    assert infer_doshic_shape(10, 10, 5, 6, submerged=False) == DoshicShape.CHURNA

    # Elongated (a=20, b=5) -> SARPA (eccentricity > 0.70)
    assert infer_doshic_shape(20, 5, 10, 1, submerged=False) == DoshicShape.SARPA

    # Rapid expanding circular (a=15, b=15, t=5 -> v=3.0, circ=1.0) -> CHHATRA
    assert infer_doshic_shape(15, 15, 5, 1, submerged=False) == DoshicShape.CHHATRA

    # Slow cohesive circular (a=6, b=6, t=10 -> v=0.6, circ=1.0) -> MUKTAKARA
    assert infer_doshic_shape(6, 6, 10, 1, submerged=False) == DoshicShape.MUKTAKARA


def test_classical_prognosis_verdicts():
    """Test Yogaratnakara classical prognostic rules."""
    # Favorable: North, single droplet, circular
    verdict, commentary = determine_prognosis(
        direction=CompassDirection.NORTH,
        shape=DoshicShape.MUKTAKARA,
        fragment_count=1,
        submerged=False,
        circularity=0.98,
        spreading_coeff=15.0,
    )
    assert verdict == PrognosisVerdict.SADHYA
    assert "Sadhya" in commentary

    # Sinking droplet: Asadhya
    v_sink, c_sink = determine_prognosis(
        direction=CompassDirection.NORTH,
        shape=DoshicShape.NIMAGNA,
        fragment_count=1,
        submerged=True,
        circularity=1.0,
        spreading_coeff=5.0,
    )
    assert v_sink == PrognosisVerdict.ASADHYA
    assert "nimajjati" in c_sink

    # Inauspicious direction: Northeast (Ishanya) -> Asadhya
    v_ne, c_ne = determine_prognosis(
        direction=CompassDirection.NORTHEAST,
        shape=DoshicShape.CHHATRA,
        fragment_count=1,
        submerged=False,
        circularity=0.9,
        spreading_coeff=12.0,
    )
    assert v_ne == PrognosisVerdict.ASADHYA

    # South (Dakshina) -> Krichrasadhya
    v_south, c_south = determine_prognosis(
        direction=CompassDirection.SOUTH,
        shape=DoshicShape.CHHATRA,
        fragment_count=1,
        submerged=False,
        circularity=0.95,
        spreading_coeff=16.0,
    )
    assert v_south == PrognosisVerdict.KRICHRASADHYA


def test_simulation_generation_all_doshas():
    """Verify physical synthetic parameter generation for classical Doshic conditions."""
    for dosha in ["VATA", "PITTA", "KAPHA", "SANNIPATA"]:
        res = simulate_taila_bindu(doshic_condition=dosha)
        assert res.doshic_condition == dosha
        assert res.simulated_surface_tension > 40.0
        assert res.circularity > 0.0
        assert res.semi_major_axis_mm >= res.semi_minor_axis_mm
        assert len(res.classical_reference) > 10
