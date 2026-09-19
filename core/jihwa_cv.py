"""Jihwa Pariksha Computer Vision & Micro-Colorimetry Analytic Engine.

Classical References:
- Yogaratnakara, Rogipariksha Adhyaya (Jihwa Pariksha)
- Bhavaprakasha, Purvakhanda, Rogipariksha Prakarana
- Ashtanga Hridaya, Sutrasthana Ch. 1 & Sharirasthana Ch. 3
"""
import math
import uuid
import time
from typing import Dict, List, Tuple

from models.jihwa import (
    CoatingThickness,
    DominantColor,
    TongueRegion,
    RegionColorimetry,
    JihwaInput,
    JihwaOutput,
    JihwaSimulationResponse,
)


def hex_to_rgb(hex_code: str) -> Tuple[int, int, int]:
    """Parse hexadecimal color string into integer RGB components."""
    clean_hex = hex_code.strip().lstrip("#")
    if len(clean_hex) != 6:
        return (128, 128, 128)
    r = int(clean_hex[0:2], 16)
    g = int(clean_hex[2:4], 16)
    b = int(clean_hex[4:6], 16)
    return (r, g, b)


def rgb_to_cielab(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert standard sRGB (0-255) to CIE-L*a*b* under D65 standard illuminant."""
    # 1. Normalize to [0, 1]
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0

    # 2. Linearize sRGB gamma
    def gamma_inv(c: float) -> float:
        if c > 0.04045:
            return ((c + 0.055) / 1.055) ** 2.4
        else:
            return c / 12.92

    r_lin = gamma_inv(r_norm)
    g_lin = gamma_inv(g_norm)
    b_lin = gamma_inv(b_norm)

    # 3. Transform to CIE XYZ (D65 standard)
    x = (r_lin * 0.4124564 + g_lin * 0.3575761 + b_lin * 0.1804375) * 100.0
    y = (r_lin * 0.2126729 + g_lin * 0.7151522 + b_lin * 0.0721750) * 100.0
    z = (r_lin * 0.0193339 + g_lin * 0.1191920 + b_lin * 0.9503041) * 100.0

    # 4. Normalize to D65 reference white (Xn=95.047, Yn=100.000, Zn=108.883)
    xr = x / 95.047
    yr = y / 100.000
    zr = z / 108.883

    # 5. Nonlinear transformation function
    def f_lab(t: float) -> float:
        if t > 0.008856:
            return t ** (1.0 / 3.0)
        else:
            return (7.787 * t) + (16.0 / 116.0)

    fx = f_lab(xr)
    fy = f_lab(yr)
    fz = f_lab(zr)

    cie_l = max(0.0, min(100.0, (116.0 * fy) - 16.0))
    cie_a = max(-128.0, min(127.0, 500.0 * (fx - fy)))
    cie_b = max(-128.0, min(127.0, 200.0 * (fy - fz)))

    return (round(cie_l, 2), round(cie_a, 2), round(cie_b, 2))


def classify_coating_thickness(coating_ratio_percent: float) -> CoatingThickness:
    """Classify lingual coating coverage into classical depth categories."""
    if coating_ratio_percent < 5.0:
        return CoatingThickness.NONE
    elif coating_ratio_percent < 35.0:
        return CoatingThickness.THIN
    elif coating_ratio_percent < 65.0:
        return CoatingThickness.MODERATE
    else:
        return CoatingThickness.THICK


def classify_dominant_color(
    cie_l: float,
    cie_a: float,
    cie_b: float,
    coating_ratio: float,
) -> DominantColor:
    """Classify chromatic phenotype based on CIE-L*a*b* coordinates and coating depth."""
    if coating_ratio < 5.0 and 45.0 <= cie_l <= 68.0 and 10.0 <= cie_a <= 26.0 and cie_b < 16.0:
        return DominantColor.CLEAN_PINK

    if cie_l <= 40.0:
        return DominantColor.BROWN_BLACK

    if cie_b >= 16.0 and cie_l >= 45.0:
        return DominantColor.YELLOW

    if cie_a >= 22.0 and cie_b < 16.0:
        return DominantColor.RED_CRIMSON

    if cie_l >= 65.0 and abs(cie_a) <= 16.0 and abs(cie_b) <= 16.0:
        return DominantColor.WHITE

    if cie_a > 15.0 and cie_l >= 45.0:
        return DominantColor.CLEAN_PINK

    return DominantColor.WHITE


def compute_ama_index(
    coating_ratio: float,
    thickness: CoatingThickness,
    dominant_color: DominantColor,
    moisture: float,
) -> Tuple[float, bool]:
    """Calculate quantitative Ama Score (0-100) and Sama clinical state."""
    # 1. Base from coating area
    base = 0.5 * coating_ratio

    # 2. Thickness bonus
    thickness_weight = {
        CoatingThickness.NONE: 0.0,
        CoatingThickness.THIN: 10.0,
        CoatingThickness.MODERATE: 20.0,
        CoatingThickness.THICK: 30.0,
    }.get(thickness, 0.0)

    # 3. Color bonus
    color_weight = {
        DominantColor.WHITE: 15.0,        # Kaphaja Ama
        DominantColor.YELLOW: 20.0,       # Pittaja Ama
        DominantColor.BROWN_BLACK: 15.0,  # Vata-Sannipata Ama
        DominantColor.RED_CRIMSON: 5.0,
        DominantColor.CLEAN_PINK: 0.0,
    }.get(dominant_color, 0.0)

    # 4. Moisture unctuousness bonus
    moisture_weight = 10.0 if moisture >= 0.65 else 0.0

    raw_score = base + thickness_weight + color_weight + moisture_weight
    ama_score = min(100.0, max(0.0, raw_score))

    is_sama = ama_score >= 35.0 or (thickness in [CoatingThickness.MODERATE, CoatingThickness.THICK] and coating_ratio >= 35.0)

    return (round(ama_score, 2), is_sama)


def compute_somatotopic_mapping(regions: List[RegionColorimetry]) -> Dict[str, str]:
    """Correlate somatotopic lingual zones with internal organ systems and Agni status."""
    mapping = {}
    for r in regions:
        if r.region == TongueRegion.ROOT:
            status = "Dense coating indicative of Adhobhaga / Pakvashaya Mala stasis" if r.cie_l > 60 else "Adhobhaga clear"
            mapping["ROOT_MULA"] = f"Pakvashaya / Vata-Kapha zone: L*={r.cie_l}, a*={r.cie_a}, b*={r.cie_b}. {status}"
        elif r.region == TongueRegion.CENTER:
            status = "Elevated thermal or Sama activity at Pachaka Agni" if (r.cie_b > 16 or r.cie_a > 20) else "Moderate Agni balance"
            mapping["CENTER_MADHYA"] = f"Amashaya / Pachaka Pitta zone: L*={r.cie_l}, a*={r.cie_a}, b*={r.cie_b}. {status}"
        elif r.region == TongueRegion.TIP_MARGINS:
            status = "Marginal erythema indicative of Pitta / Ranjaka-Sadhaka excitation" if r.cie_a > 22 else "Peripheral vascularity stable"
            mapping["TIP_MARGINS_AGRA_PARSHVA"] = f"Prana / Hridaya / Yakrit zone: L*={r.cie_l}, a*={r.cie_a}, b*={r.cie_b}. {status}"
    return mapping


def calculate_jihwa_doshic_vector(
    data: JihwaInput,
    avg_l: float,
    avg_a: float,
    avg_b: float,
    dominant_color: DominantColor,
    thickness: CoatingThickness,
    ama_score: float,
) -> Tuple[float, float, float, str]:
    """Formulate normalized Tri-Doshic Simplex vector and primary Doshic vitiation."""
    # Vata: Fissures (Sphutita), Aridity (Ruksha), Roughness (Khara), Brown/Black (Krishna)
    s_v = (
        0.35 * data.fissure_density +
        0.35 * (1.0 - data.observed_moisture) +
        0.20 * data.papillary_roughness +
        (0.30 if dominant_color == DominantColor.BROWN_BLACK else 0.05)
    )

    # Pitta: Redness (Rakta), Yellowness (Peeta), Marginal Erythema, Clean pink with high a*
    s_p = (
        0.35 * max(0.0, (avg_a - 10.0) / 20.0) +
        0.35 * max(0.0, (avg_b - 5.0) / 20.0) +
        (0.30 if dominant_color in [DominantColor.RED_CRIMSON, DominantColor.YELLOW] else 0.05)
    )

    # Kapha: Coating coverage (Lepa), High lightness (Shweta), Unctuous moisture (Snigdha)
    s_k = (
        0.35 * (data.coating_ratio_percent / 100.0) +
        0.25 * max(0.0, (avg_l - 40.0) / 40.0) +
        0.25 * data.observed_moisture +
        (0.25 if dominant_color == DominantColor.WHITE else 0.05)
    )

    # Ensure strictly positive weights
    s_v = max(s_v, 0.01)
    s_p = max(s_p, 0.01)
    s_k = max(s_k, 0.01)

    total = s_v + s_p + s_k
    u_v = s_v / total
    u_p = s_p / total
    u_k = s_k / total

    # Dirichlet boundary smoothing (epsilon = 1e-4)
    eps = 1e-4
    w_v = (1.0 - 3.0 * eps) * u_v + eps
    w_p = (1.0 - 3.0 * eps) * u_p + eps
    w_k = (1.0 - 3.0 * eps) * u_k + eps

    # Determine primary dosha
    doshas = [("VATA", w_v), ("PITTA", w_p), ("KAPHA", w_k)]
    primary_dosha = max(doshas, key=lambda x: x[1])[0]

    return (round(w_v, 4), round(w_p, 4), round(w_k, 4), primary_dosha)


def evaluate_jihwa(
    data: JihwaInput,
    examiner_arn: str,
    hospital_id: str,
) -> JihwaOutput:
    """Execute complete Jihwa Pariksha computer vision extraction and clinical assessment."""
    # 1. Compute average colorimetry across regions
    avg_l = sum(r.cie_l for r in data.regions) / len(data.regions)
    avg_a = sum(r.cie_a for r in data.regions) / len(data.regions)
    avg_b = sum(r.cie_b for r in data.regions) / len(data.regions)

    # 2. Coating classification
    thickness = classify_coating_thickness(data.coating_ratio_percent)
    dominant_color = classify_dominant_color(avg_l, avg_a, avg_b, data.coating_ratio_percent)

    # 3. Ama scoring
    ama_score, is_sama = compute_ama_index(
        coating_ratio=data.coating_ratio_percent,
        thickness=thickness,
        dominant_color=dominant_color,
        moisture=data.observed_moisture,
    )

    # 4. Somatotopic organ mapping
    somatotopic = compute_somatotopic_mapping(data.regions)

    # 5. Doshic vector
    vata_score, pitta_score, kapha_score, primary_dosha = calculate_jihwa_doshic_vector(
        data=data,
        avg_l=avg_l,
        avg_a=avg_a,
        avg_b=avg_b,
        dominant_color=dominant_color,
        thickness=thickness,
        ama_score=ama_score,
    )

    # 6. Generate summary commentary
    ama_text = "SAMA (Ama accumulation confirmed)" if is_sama else "NIRAMA (Digestive fire clear)"
    findings = (
        f"Jihwa Pariksha indicates {primary_dosha} predominance with {dominant_color.value} coating "
        f"({thickness.value} thickness, {data.coating_ratio_percent:.1f}% CAR). "
        f"Clinical state: {ama_text} with Ama Score {ama_score:.1f}/100. "
        f"Fissure density: {data.fissure_density:.2f}."
    )

    return JihwaOutput(
        exam_id=f"jih-{uuid.uuid4().hex[:12]}",
        patient_id=data.patient_id,
        hospital_id=hospital_id,
        examiner_arn=examiner_arn,
        image_hash=data.image_hash,
        coating_ratio=data.coating_ratio_percent,
        coating_thickness=thickness,
        dominant_color=dominant_color,
        fissure_density=data.fissure_density,
        cie_l=round(avg_l, 2),
        cie_a=round(avg_a, 2),
        cie_b=round(avg_b, 2),
        ama_score=ama_score,
        vata_score=vata_score,
        pitta_score=pitta_score,
        kapha_score=kapha_score,
        primary_dosha=primary_dosha,
        is_sama=is_sama,
        findings_summary=findings,
        somatotopic_mapping=somatotopic,
        timestamp=int(time.time()),
    )


def simulate_jihwa(target_condition: str) -> JihwaSimulationResponse:
    """Synthesize lingual biometric and colorimetric values for specified clinical condition."""
    cond = target_condition.strip().upper()

    if cond == "VATA_DRY":
        # Rough, cracked, dusky dark-brownish hue, dry
        ratio = 12.0
        fissures = 0.65
        roughness = 0.70
        moisture = 0.15
        regions = [
            RegionColorimetry(region=TongueRegion.ROOT, rgb_hex="#5A4738", cie_l=32.0, cie_a=4.5, cie_b=11.2),
            RegionColorimetry(region=TongueRegion.CENTER, rgb_hex="#6D5545", cie_l=38.5, cie_a=5.8, cie_b=13.0),
            RegionColorimetry(region=TongueRegion.TIP_MARGINS, rgb_hex="#543C2E", cie_l=29.0, cie_a=6.2, cie_b=12.1),
        ]
        dom_color = DominantColor.BROWN_BLACK
        expected_dosha = "VATA"
        ref = "Yogaratnakara: Vatat sphutita ruksha cha krishnabha shitala bhavet (In Vata, tongue is cracked, dry, dark/blackish, cold)."

    elif cond == "PITTA_INFLAMED":
        # Crimson red body, yellowish tint in center, moist
        ratio = 42.0
        fissures = 0.05
        roughness = 0.40
        moisture = 0.60
        regions = [
            RegionColorimetry(region=TongueRegion.ROOT, rgb_hex="#D9822B", cie_l=62.0, cie_a=24.0, cie_b=48.0),
            RegionColorimetry(region=TongueRegion.CENTER, rgb_hex="#E59A32", cie_l=68.0, cie_a=18.5, cie_b=52.0),
            RegionColorimetry(region=TongueRegion.TIP_MARGINS, rgb_hex="#DC2626", cie_l=48.0, cie_a=55.0, cie_b=28.0),
        ]
        dom_color = DominantColor.YELLOW
        expected_dosha = "PITTA"
        ref = "Yogaratnakara: Pittena rakta peeta va shuna tikshna pradahyate (In Pitta, tongue is crimson/red, yellow, inflamed, burning)."

    elif cond == "KAPHA_AMA":
        # Thick white coating, high lightness, unctuous/slimy
        ratio = 78.0
        fissures = 0.0
        roughness = 0.15
        moisture = 0.85
        regions = [
            RegionColorimetry(region=TongueRegion.ROOT, rgb_hex="#F5F5F0", cie_l=92.0, cie_a=-1.2, cie_b=4.5),
            RegionColorimetry(region=TongueRegion.CENTER, rgb_hex="#EAEAEA", cie_l=88.5, cie_a=-0.8, cie_b=3.2),
            RegionColorimetry(region=TongueRegion.TIP_MARGINS, rgb_hex="#E0E0DB", cie_l=84.0, cie_a=0.5, cie_b=5.0),
        ]
        dom_color = DominantColor.WHITE
        expected_dosha = "KAPHA"
        ref = "Yogaratnakara: Kaphena shweta pichhila gurutva yukta (In Kapha, tongue is white, slimy/sticky, heavy with thick lepa)."

    else:  # HEALTHY_NIRAMA
        # Clean pink mucosal surface, no coating, optimal moisture
        ratio = 2.0
        fissures = 0.0
        roughness = 0.10
        moisture = 0.50
        regions = [
            RegionColorimetry(region=TongueRegion.ROOT, rgb_hex="#DB7093", cie_l=56.0, cie_a=22.0, cie_b=10.0),
            RegionColorimetry(region=TongueRegion.CENTER, rgb_hex="#E06D88", cie_l=54.5, cie_a=24.5, cie_b=9.5),
            RegionColorimetry(region=TongueRegion.TIP_MARGINS, rgb_hex="#DE6480", cie_l=53.0, cie_a=25.0, cie_b=11.0),
        ]
        dom_color = DominantColor.CLEAN_PINK
        expected_dosha = "PITTA"  # natural pink mucosa falls near Pitta-Rakta vascularity or balanced
        ref = "Bhavaprakasha: Nirama jihwa prakritastha snigdha rakta shubha bhavet (Healthy tongue is naturally unctuous, auspicious pink-red, clear)."

    return JihwaSimulationResponse(
        target_condition=cond,
        coating_ratio_percent=ratio,
        fissure_density=fissures,
        papillary_roughness=roughness,
        regions=regions,
        observed_moisture=moisture,
        expected_dominant_color=dom_color,
        expected_dosha=expected_dosha,
        classical_reference=ref,
    )
