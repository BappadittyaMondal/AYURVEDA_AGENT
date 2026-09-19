"""Taila Bindu Pariksha Diagnostic Engine & Surface-Tension Fluid Dynamics.

Classical References:
- Yogaratnakara, Rogipariksha Adhyaya (Taila Bindu Pariksha)
- Vangasena Samhita, Mutra Pariksha Prakarana
"""
import math
import uuid
import time
from typing import Tuple, Optional

from models.taila_bindu import (
    TailaBinduInput,
    TailaBinduOutput,
    TailaBinduSimulationResponse,
    PrognosisVerdict,
    DoshicShape,
    CompassDirection,
)


def calculate_spreading_coefficient(
    gamma_urine: float,
    gamma_oil: float = 32.5,
    gamma_interface: float = 15.0,
) -> float:
    """Compute Harkins spreading coefficient: S = gamma_urine - gamma_oil - gamma_interface (mN/m)."""
    return float(gamma_urine - gamma_oil - gamma_interface)


def calculate_ellipse_geometry(
    semi_major_a: float,
    semi_minor_b: float,
) -> Tuple[float, float, float, float]:
    """Calculate geometric properties of droplet spreading boundary.

    Returns:
        (area_mm2, perimeter_mm, eccentricity, circularity)
    """
    a = float(max(semi_major_a, semi_minor_b))
    b = float(min(semi_major_a, semi_minor_b))

    # Area
    area = math.pi * a * b

    # Eccentricity: e = sqrt(1 - b^2 / a^2)
    if a > 0:
        ratio = (b / a) ** 2
        eccentricity = math.sqrt(max(0.0, 1.0 - ratio))
    else:
        eccentricity = 0.0

    # Ramanujan's formula for perimeter of ellipse
    # P approx pi * [3(a+b) - sqrt((3a+b)(a+3b))]
    term = math.sqrt((3.0 * a + b) * (a + 3.0 * b))
    perimeter = math.pi * (3.0 * (a + b) - term)

    # Circularity (Isoperimetric quotient) C = 4 * pi * A / P^2
    if perimeter > 0:
        circularity = (4.0 * math.pi * area) / (perimeter ** 2)
        circularity = min(1.0, max(0.0, circularity))
    else:
        circularity = 1.0

    return (area, perimeter, eccentricity, circularity)


def calculate_spreading_velocity(
    semi_major_a: float,
    observation_time_sec: float,
) -> float:
    """Calculate average radial spreading speed: v = a / t (mm/s)."""
    t = max(float(observation_time_sec), 0.1)
    return float(semi_major_a) / t


def infer_doshic_shape(
    semi_major_a: float,
    semi_minor_b: float,
    observation_time_sec: float,
    fragment_count: int,
    submerged: bool,
    manual_shape: Optional[DoshicShape] = None,
) -> DoshicShape:
    """Infer morphological Doshic droplet shape from physical kinematics."""
    if manual_shape is not None:
        return manual_shape

    if submerged:
        return DoshicShape.NIMAGNA

    if fragment_count > 4:
        return DoshicShape.CHURNA

    _, _, eccentricity, circularity = calculate_ellipse_geometry(semi_major_a, semi_minor_b)
    velocity = calculate_spreading_velocity(semi_major_a, observation_time_sec)

    if eccentricity > 0.70:
        return DoshicShape.SARPA
    elif circularity > 0.85 and velocity >= 1.2:
        return DoshicShape.CHHATRA
    elif circularity > 0.80 and velocity < 1.2:
        return DoshicShape.MUKTAKARA
    else:
        return DoshicShape.JALAVAT


def determine_prognosis(
    direction: CompassDirection,
    shape: DoshicShape,
    fragment_count: int,
    submerged: bool,
    circularity: float,
    spreading_coeff: float,
) -> Tuple[PrognosisVerdict, str]:
    """Determine classical prognosis verdict and Sanskrit textual rationale."""
    if submerged or shape == DoshicShape.NIMAGNA:
        return (
            PrognosisVerdict.ASADHYA,
            "Taila nimajjati (droplet sinks directly to vessel bed). Indicates terminal Ojas depletion and critical Asadhya prognosis.",
        )

    if direction in [CompassDirection.NORTHEAST, CompassDirection.SOUTHWEST, CompassDirection.NORTHWEST]:
        return (
            PrognosisVerdict.ASADHYA,
            f"Droplet trajectory towards Vidisha ({direction.value}) denotes severe systemic vitiation and Asadhya prognosis per Yogaratnakara.",
        )

    if fragment_count > 5 or shape == DoshicShape.CHURNA:
        return (
            PrognosisVerdict.ASADHYA,
            f"High fragmentation ({fragment_count} droplets) denotes Sannipataja dissolution and critical Asadhya prognosis.",
        )

    if direction in [CompassDirection.SOUTH, CompassDirection.SOUTHEAST]:
        return (
            PrognosisVerdict.KRICHRASADHYA,
            f"Spread towards Dakshina/Agneya ({direction.value}) indicates intense Pitta-associated thermal pathology; curable with intensive therapeutic effort (Krichrasadhya).",
        )

    if direction in [CompassDirection.NORTH, CompassDirection.EAST, CompassDirection.WEST]:
        if fragment_count <= 2 and circularity >= 0.45:
            return (
                PrognosisVerdict.SADHYA,
                f"Harmonious smooth spread towards auspicious cardinal direction ({direction.value}) indicates intact Bala and favorable Sadhya recovery.",
            )
        else:
            return (
                PrognosisVerdict.KRICHRASADHYA,
                f"Favorable direction ({direction.value}) but structural distortion/fragmentation indicates protracted Krichrasadhya recovery.",
            )

    return (
        PrognosisVerdict.KRICHRASADHYA,
        f"Intermediate fluid dynamic equilibrium ({direction.value}) indicates guarded Krichrasadhya prognosis.",
    )


def evaluate_taila_bindu(
    data: TailaBinduInput,
    evaluator_arn: str,
    hospital_id: str,
) -> TailaBinduOutput:
    """Execute complete Taila Bindu Pariksha fluid mechanics evaluation."""
    spreading_coeff = calculate_spreading_coefficient(
        gamma_urine=data.urine_surface_tension,
        gamma_oil=data.oil_surface_tension,
        gamma_interface=data.interfacial_tension,
    )

    _, _, eccentricity, circularity = calculate_ellipse_geometry(
        semi_major_a=data.semi_major_axis_mm,
        semi_minor_b=data.semi_minor_axis_mm,
    )

    spreading_velocity = calculate_spreading_velocity(
        semi_major_a=data.semi_major_axis_mm,
        observation_time_sec=data.observation_time_sec,
    )

    doshic_shape = infer_doshic_shape(
        semi_major_a=data.semi_major_axis_mm,
        semi_minor_b=data.semi_minor_axis_mm,
        observation_time_sec=data.observation_time_sec,
        fragment_count=data.fragment_count,
        submerged=data.submerged,
        manual_shape=data.observed_shape,
    )

    prognosis_verdict, commentary = determine_prognosis(
        direction=data.direction,
        shape=doshic_shape,
        fragment_count=data.fragment_count,
        submerged=data.submerged,
        circularity=circularity,
        spreading_coeff=spreading_coeff,
    )

    return TailaBinduOutput(
        session_id=str(uuid.uuid4()),
        patient_id=data.patient_id,
        hospital_id=hospital_id,
        evaluator_arn=evaluator_arn,
        urine_temp=data.urine_temperature_c,
        surface_tension=data.urine_surface_tension,
        spreading_coeff=round(spreading_coeff, 3),
        spreading_velocity=round(spreading_velocity, 3),
        eccentricity=round(eccentricity, 4),
        circularity=round(circularity, 4),
        direction=data.direction,
        fragment_count=data.fragment_count,
        submerged=data.submerged,
        doshic_shape=doshic_shape,
        prognosis_verdict=prognosis_verdict,
        commentary=commentary,
        timestamp=int(time.time()),
    )


def simulate_taila_bindu(
    doshic_condition: str,
    urine_temp: float = 25.0,
    drop_height_angula: float = 1.0,
) -> TailaBinduSimulationResponse:
    """Synthesize classical fluid dynamic parameters for specified doshic pathology."""
    cond = doshic_condition.strip().upper()

    if cond == "VATA":
        # Serpantine, high eccentricity, moderate surface tension, East/West
        surf_tension = 58.0
        a = 18.0
        b = 6.0
        direction = CompassDirection.EAST
        shape = DoshicShape.SARPA
        verdict = PrognosisVerdict.SADHYA
        ref = "Yogaratnakara: Vata tailam sarpavat sarpati (oil spreads like a snake with elongated zigzag morphology)."
    elif cond == "PITTA":
        # Rapid expanding circular parasol/rings, lower surface tension due to bile salts
        surf_tension = 65.0
        a = 24.0
        b = 23.0
        direction = CompassDirection.SOUTH
        shape = DoshicShape.CHHATRA
        verdict = PrognosisVerdict.KRICHRASADHYA
        ref = "Yogaratnakara: Pitta tailam chhatrakaram sheetalam prasarpati (oil spreads rapidly forming an umbrella ring)."
    elif cond == "KAPHA":
        # Slow cohesive pearl bead, higher surface tension, North
        surf_tension = 52.0
        a = 8.0
        b = 7.8
        direction = CompassDirection.NORTH
        shape = DoshicShape.MUKTAKARA
        verdict = PrognosisVerdict.SADHYA
        ref = "Yogaratnakara: Kapha tailam muktakaram mandam vishalyati (oil stays cohesive as a pearl bead expanding slowly)."
    else:  # SANNIPATA or other
        surf_tension = 48.0
        a = 15.0
        b = 7.0
        direction = CompassDirection.NORTHEAST
        shape = DoshicShape.CHURNA
        verdict = PrognosisVerdict.ASADHYA
        ref = "Yogaratnakara: Sannipata tailam churnavat prabhidyate (oil shatters into dispersed fragments or sinks, indicating grave prognosis)."

    s_coeff = calculate_spreading_coefficient(surf_tension)
    _, _, ecc, circ = calculate_ellipse_geometry(a, b)

    return TailaBinduSimulationResponse(
        doshic_condition=cond,
        simulated_surface_tension=surf_tension,
        simulated_spreading_coeff=round(s_coeff, 3),
        semi_major_axis_mm=a,
        semi_minor_axis_mm=b,
        eccentricity=round(ecc, 4),
        circularity=round(circ, 4),
        expected_direction=direction,
        doshic_shape=shape,
        prognosis_verdict=verdict,
        classical_reference=ref,
    )
