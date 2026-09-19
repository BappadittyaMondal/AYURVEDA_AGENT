"""Vikriti Dynamic Pathological Divergence Engine & VSI Vector Analytics."""
import math
from typing import Any, Dict, List, Tuple
import numpy as np
from core.prakriti import DIRICHLET_EPSILON
from models.vikriti import DoshicDeltaDetail, DoshicDeltaOutput, DoshicDeviationState, VikritiSeverityTier

VIKRITI_SYMPTOMS: List[Dict[str, Any]] = [
    # Vata Pathological Symptoms (VS01 - VS08)
    {"id": "VS01", "dosha": "V", "name": "Shoola / Asthi-Sandhi Toda", "desc": "Wandering aching pain, severe joint or body aches"},
    {"id": "VS02", "dosha": "V", "name": "Parushya / Rukshata", "desc": "Severe dryness and roughness of skin, mouth, or throat"},
    {"id": "VS03", "dosha": "V", "name": "Anidra / Chanchalata", "desc": "Insomnia, interrupted anxious sleep, nervous restlessness"},
    {"id": "VS04", "dosha": "V", "name": "Vepathu / Spandana", "desc": "Tremors, muscle twitching, involuntary spasms"},
    {"id": "VS05", "dosha": "V", "name": "Adhmana / Vibandha", "desc": "Abdominal distension, painful gas, dry hard constipation"},
    {"id": "VS06", "dosha": "V", "name": "Bhrama / Klama", "desc": "Giddiness, disorientation, fatigue without physical work"},
    {"id": "VS07", "dosha": "V", "name": "Suptata / Sankocha", "desc": "Numbness, pins-and-needles sensation, limb contractures"},
    {"id": "VS08", "dosha": "V", "name": "Chitta Vibhrama", "desc": "Acute anxiety, panic attacks, racing uncontrollable thoughts"},

    # Pitta Pathological Symptoms (VS09 - VS16)
    {"id": "VS09", "dosha": "P", "name": "Santapa / Vidaha", "desc": "Severe internal burning sensation in stomach, chest, or extremities"},
    {"id": "VS10", "dosha": "P", "name": "Jvara / Ushnata", "desc": "Elevated body temperature, hot flushes, inflammatory heat"},
    {"id": "VS11", "dosha": "P", "name": "Amlika / Katu Udgara", "desc": "Severe hyperacidity, sour regurgitation, bitter belching"},
    {"id": "VS12", "dosha": "P", "name": "Sweda Atipravritti", "desc": "Excessive perspiration with strong, unpleasant odor"},
    {"id": "VS13", "dosha": "P", "name": "Rakta Pitta / Pitata", "desc": "Redness of eyes, cutaneous petechiae, yellowish urine/sclera"},
    {"id": "VS14", "dosha": "P", "name": "Trishna Adhikya", "desc": "Unquenchable burning thirst, dry parched mouth with burning"},
    {"id": "VS15", "dosha": "P", "name": "Pravahika / Atisara", "desc": "Loose, burning yellow stools, rapid gastrointestinal transit"},
    {"id": "VS16", "dosha": "P", "name": "Krodha / Sammoha", "desc": "Severe irritability, unprovoked anger, emotional aggression"},

    # Kapha Pathological Symptoms (VS17 - VS24)
    {"id": "VS17", "dosha": "K", "name": "Gourava / Guruta", "desc": "Profound physical heaviness in head, chest, or whole body"},
    {"id": "VS18", "dosha": "K", "name": "Alasya / Tandra", "desc": "Persistent lethargy, daytime somnolence, inability to initiate tasks"},
    {"id": "VS19", "dosha": "K", "name": "Shopha / Sthaulya", "desc": "Water retention, puffy edema of face/extremities, fluid stagnation"},
    {"id": "VS20", "dosha": "K", "name": "Praseka / Shleshma", "desc": "Excessive mucoid salivation, chronic productive cough with thick phlegm"},
    {"id": "VS21", "dosha": "K", "name": "Agnimandya / Aruchi", "desc": "Total loss of appetite, sluggish digestion lasting over 6 hours"},
    {"id": "VS22", "dosha": "K", "name": "Madhuryasya / Mukhalepa", "desc": "Sweet taste in mouth, thick unctuous white coating on tongue"},
    {"id": "VS23", "dosha": "K", "name": "Srotorodha / Kanthopalepa", "desc": "Channel congestion, heavy feeling in chest, nasal obstruction"},
    {"id": "VS24", "dosha": "K", "name": "Utsaha Hani", "desc": "Complete loss of vitality, mental apathy, depressive inertia"}
]

# Population Covariance Matrix in the 2D projected simplex subspace [v, p]^T
# Determinant = 0.04 * 0.04 - (-0.02)^2 = 0.0012
COV_2D = np.array([
    [0.04, -0.02],
    [-0.02, 0.04]
])
INV_COV_2D = np.linalg.inv(COV_2D)
CHI2_2_99 = 9.21034  # Critical value for Chi-Square distribution (df=2, p=0.99)
CHI2_NORM_FACTOR = math.sqrt(CHI2_2_99)


def compute_vikriti_vector(symptoms: Dict[str, int]) -> Tuple[float, float, float]:
    """
    Transform acute symptom severity ratings [0-3] into a normalized Vikriti vector on Delta^2.
    """
    sum_v = 0.0
    sum_p = 0.0
    sum_k = 0.0

    for s in VIKRITI_SYMPTOMS:
        sid = s["id"]
        severity = float(symptoms.get(sid, 0))
        # Clamp severity between 0 and 3
        severity = max(0.0, min(3.0, severity))
        if s["dosha"] == "V":
            sum_v += severity
        elif s["dosha"] == "P":
            sum_p += severity
        elif s["dosha"] == "K":
            sum_k += severity

    total = sum_v + sum_p + sum_k
    if total == 0:
        # If asymptomatic, current Vikriti mirrors equal baseline
        return 0.3333, 0.3333, 0.3334

    # Apply convex mixture to enforce Dirichlet minimum boundary
    eps = DIRICHLET_EPSILON
    raw_v = sum_v / total
    raw_p = sum_p / total
    raw_k = sum_k / total

    v = (1.0 - 3.0 * eps) * raw_v + eps
    p = (1.0 - 3.0 * eps) * raw_p + eps
    k = (1.0 - 3.0 * eps) * raw_k + eps

    norm_sum = v + p + k
    v_norm = max(round(v / norm_sum, 4), eps)
    p_norm = max(round(p / norm_sum, 4), eps)
    k_norm = round(1.0 - (v_norm + p_norm), 4)

    return v_norm, p_norm, k_norm


def compute_kl_divergence(
    vikriti: Tuple[float, float, float],
    prakriti: Tuple[float, float, float]
) -> float:
    """
    Calculate the Kullback-Leibler (Information) Divergence D_KL(V || P).
    Strictly non-negative by Gibbs' inequality.
    """
    kl = 0.0
    for v_val, p_val in zip(vikriti, prakriti):
        # Guarantee minimum epsilon
        v_safe = max(v_val, DIRICHLET_EPSILON)
        p_safe = max(p_val, DIRICHLET_EPSILON)
        kl += v_safe * math.log(v_safe / p_safe)
    return max(0.0, float(round(kl, 4)))


def compute_mahalanobis_distance(
    vikriti: Tuple[float, float, float],
    prakriti: Tuple[float, float, float]
) -> float:
    """
    Calculate the Mahalanobis distance D_M(V, P) on the 2D projected simplex subspace.
    """
    diff_2d = np.array([
        vikriti[0] - prakriti[0],
        vikriti[1] - prakriti[1]
    ])
    dist_sq = float(diff_2d.T @ INV_COV_2D @ diff_2d)
    dist = math.sqrt(max(0.0, dist_sq))
    return float(round(dist, 4))


def compute_vsi(kl: float, mahalanobis: float) -> Tuple[float, VikritiSeverityTier, str]:
    """
    Calculate the composite Vikriti Severity Index (VSI) [0 - 100].
    Returns (vsi_score, severity_tier, clinical_recommendation).
    """
    # Normalize KL (typical max empirical range on simplex is ~1.5)
    norm_kl = min(kl / 1.5, 1.0)
    # Normalize Mahalanobis by 99% Chi-Square boundary
    norm_m = min(mahalanobis / CHI2_NORM_FACTOR, 1.0)

    composite = (0.5 * norm_kl) + (0.5 * norm_m)
    vsi = round(composite * 100.0, 2)

    if vsi < 15.0:
        tier = VikritiSeverityTier.SAMADOSHA
        rec = "Samadosha: Physiological equilibrium maintained. Continue Swastha Vritta and Ritucharya."
    elif vsi < 40.0:
        tier = VikritiSeverityTier.ALPA_VIKRITI
        rec = "Alpa Vikriti: Mild doshic perturbation detected. Pathya-Apathya Ahara and Dinacharya modification indicated."
    elif vsi < 75.0:
        tier = VikritiSeverityTier.MADHYAMA_VIKRITI
        rec = "Madhyama Vikriti: Moderate doshic vitiation. Shamana Aushadha (internal pacification pharmacotherapy) indicated."
    else:
        tier = VikritiSeverityTier.TIVRA_VIKRITI
        rec = "Tivra Vikriti: Severe multi-doshic vitiation. Shodhana / Panchakarma detoxification protocol strongly mandated."

    return vsi, tier, rec


def compute_doshic_deltas(
    vikriti: Tuple[float, float, float],
    prakriti: Tuple[float, float, float]
) -> DoshicDeltaOutput:
    """
    Compute directional deviation vector Delta D = V_curr - P_base.
    """
    d_v = round(vikriti[0] - prakriti[0], 4)
    d_p = round(vikriti[1] - prakriti[1], 4)
    d_k = round(vikriti[2] - prakriti[2], 4)

    def _get_state_and_pct(delta: float, base: float) -> DoshicDeltaDetail:
        pct = round((delta / max(base, 1e-4)) * 100.0, 1)
        if delta > 0.05:
            state = DoshicDeviationState.VRIDDHI
        elif delta < -0.05:
            state = DoshicDeviationState.KSHAYA
        else:
            state = DoshicDeviationState.SAMA
        return DoshicDeltaDetail(delta=delta, state=state, percentage_change=pct)

    detail_v = _get_state_and_pct(d_v, prakriti[0])
    detail_p = _get_state_and_pct(d_p, prakriti[1])
    detail_k = _get_state_and_pct(d_k, prakriti[2])

    deltas = [("VATA", d_v), ("PITTA", d_p), ("KAPHA", d_k)]
    deltas.sort(key=lambda x: x[1], reverse=True)
    dominant_vitiation = deltas[0][0] if deltas[0][1] > 0.05 else "NONE_SAMA"

    return DoshicDeltaOutput(
        vata=detail_v,
        pitta=detail_p,
        kapha=detail_k,
        dominant_vitiation=dominant_vitiation
    )
