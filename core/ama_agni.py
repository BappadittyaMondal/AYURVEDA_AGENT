"""Quantitative Ama Grading Index (AGI) & Agni Vector Gating Engine.

Classical References:
- Charaka Samhita, Chikitsasthana Ch. 15 (Grahani Dosha Chikitsa)
- Ashtanga Hridaya, Sutrasthana Ch. 13 (Doshabhediya Adhyaya - Ama Lakshana)
- Charaka Samhita, Siddhisthana Ch. 6 (Vamana-Virechana Vyapad Siddhi)
"""
import uuid
import time
from typing import Dict, List, Tuple

from models.ama_agni import (
    AgniType,
    AmaGrade,
    GatingStatus,
    AmaSymptomsInput,
    AgniParametersInput,
    AmaAgniEvaluationRequest,
    TherapeuticDirective,
    AmaAgniOutput,
)


def calculate_agi_score(symptoms: AmaSymptomsInput) -> float:
    """Calculate normalized Quantitative Ama Grading Index (0-100) using diagnostic weighting."""
    weights = {
        "srotorodha": 1.2,
        "balabhramsha": 1.0,
        "gaurava": 1.1,
        "anilamudhata": 1.0,
        "alasya": 0.9,
        "apakti": 1.2,
        "nishthiva": 0.9,
        "malasanga": 1.0,
        "aruchi": 0.9,
        "klama": 0.8,
    }

    # Sum of weights = 10.0, max ordinal rating = 3, max raw = 30.0
    weighted_sum = (
        symptoms.srotorodha * weights["srotorodha"] +
        symptoms.balabhramsha * weights["balabhramsha"] +
        symptoms.gaurava * weights["gaurava"] +
        symptoms.anilamudhata * weights["anilamudhata"] +
        symptoms.alasya * weights["alasya"] +
        symptoms.apakti * weights["apakti"] +
        symptoms.nishthiva * weights["nishthiva"] +
        symptoms.malasanga * weights["malasanga"] +
        symptoms.aruchi * weights["aruchi"] +
        symptoms.klama * weights["klama"]
    )

    agi = (weighted_sum / 30.0) * 100.0
    return round(min(100.0, max(0.0, agi)), 2)


def classify_ama_grade(agi_score: float) -> AmaGrade:
    """Stratify systemic metabolic endotoxin burden based on quantitative AGI score."""
    if agi_score < 20.0:
        return AmaGrade.NIRAMA
    elif agi_score < 45.0:
        return AmaGrade.ALPA_AMA
    elif agi_score < 70.0:
        return AmaGrade.MADHYAMA_AMA
    else:
        return AmaGrade.GURU_AMA


def calculate_agni_vector(params: AgniParametersInput) -> Tuple[Dict[str, float], AgniType]:
    """Calculate barycentric coordinates on Delta^3 simplex and primary functional Agni state."""
    # 1. Vishamagni (Erratic/Vata): Chaotic appetite, abdominal tympanites, erratic digestion
    s_vishama = (
        0.45 * (1.0 - params.appetite_regularity) +
        0.40 * params.abdominal_distension +
        0.15 * min(1.0, abs(params.digestion_speed_hours - 4.0) / 4.0)
    )

    # 2. Tikshnagni (Hyperactive/Pitta): Burning pyrosis, abnormally rapid gastric emptying (< 3 hrs)
    s_tikshna = (
        0.55 * params.burning_sensation +
        0.45 * max(0.0, (4.0 - params.digestion_speed_hours) / 3.0)
    )

    # 3. Mandagni (Sluggish/Kapha): Post-prandial heaviness, prolonged digestion (> 5 hrs)
    s_manda = (
        0.50 * params.post_prandial_heaviness +
        0.50 * max(0.0, (params.digestion_speed_hours - 4.0) / 6.0)
    )

    # 4. Samagni (Equilibrium): Predictable appetite, physiological 4-hr digestion, no burning/heaviness
    s_sama = (
        0.40 * params.appetite_regularity +
        0.30 * max(0.0, 1.0 - (abs(params.digestion_speed_hours - 4.0) / 2.0)) +
        0.30 * (1.0 - max(params.burning_sensation, params.post_prandial_heaviness, params.abdominal_distension))
    )

    # Ensure non-zero
    s_vishama = max(s_vishama, 0.01)
    s_tikshna = max(s_tikshna, 0.01)
    s_manda = max(s_manda, 0.01)
    s_sama = max(s_sama, 0.01)

    total = s_vishama + s_tikshna + s_manda + s_sama
    u_vishama = s_vishama / total
    u_tikshna = s_tikshna / total
    u_manda = s_manda / total
    u_sama = s_sama / total

    # Dirichlet boundary smoothing (epsilon = 1e-4)
    eps = 1e-4
    w_vishama = (1.0 - 4.0 * eps) * u_vishama + eps
    w_tikshna = (1.0 - 4.0 * eps) * u_tikshna + eps
    w_manda = (1.0 - 4.0 * eps) * u_manda + eps
    w_sama = (1.0 - 4.0 * eps) * u_sama + eps

    agni_vector = {
        "SAMAGNI": round(w_sama, 4),
        "VISHAMAGNI": round(w_vishama, 4),
        "TIKSHNAGNI": round(w_tikshna, 4),
        "MANDAGNI": round(w_manda, 4),
    }

    # Primary Agni
    primary = max(agni_vector.items(), key=lambda x: x[1])[0]
    return (agni_vector, AgniType(primary))


def evaluate_gating_and_directives(
    ama_grade: AmaGrade,
    agni_type: AgniType,
    agi_score: float,
) -> Tuple[bool, GatingStatus, List[TherapeuticDirective]]:
    """Determine Panchakarma Shodhana clearance, safety firewall gating, and clinical directives."""
    directives: List[TherapeuticDirective] = []

    # SAFETY FIREWALL RULE 1: GURU AMA (Critical Toxicity)
    if ama_grade == AmaGrade.GURU_AMA:
        shodhana_permitted = False
        gating_status = GatingStatus.GATED_EMERGENCY_LANGHANA
        directives.append(
            TherapeuticDirective(
                phase="EMERGENCY_AMAPACHANA",
                action_type="LANGHANA_UPAVASA",
                herbal_recommendations=["Shunthi-Dhanyaka Siddha Jala", "Musta-Parpataka Kwatha", "Panchakola Yavagu"],
                dietary_guidelines=["Complete solid food abstinence", "Sip warm boiled water intermittently", "No dairy, fats, or heavy grains"],
                contraindications=["Shodhana (Vamana/Virechana strictly prohibited)", "Snehana (Oil intake causes Amavisha)", "Brihmana/Nourishing therapies"],
            )
        )
        return (shodhana_permitted, gating_status, directives)

    # SAFETY FIREWALL RULE 2: MADHYAMA AMA (Moderate Systemic Endotoxin)
    if ama_grade == AmaGrade.MADHYAMA_AMA:
        shodhana_permitted = False
        gating_status = GatingStatus.GATED_FOR_DEEPANA_PACHANA
        directives.append(
            TherapeuticDirective(
                phase="ACTIVE_PACHANA",
                action_type="DEEPANA_PACHANA",
                herbal_recommendations=["Trikatu Churna (1-2g with warm water)", "Chitrakadi Vati (2 tabs before food)", "Hingwashtaka Churna"],
                dietary_guidelines=["Mudga Yusha (warm green gram soup)", "Laja Manda", "Warm ginger water"],
                contraindications=["Panchakarma Shodhana locked until AGI < 20", "Abhyanga / external oleation", "Cold and heavy foods"],
            )
        )
        return (shodhana_permitted, gating_status, directives)

    # SAFETY FIREWALL RULE 3: ALPA AMA (Mild Endotoxin)
    if ama_grade == AmaGrade.ALPA_AMA:
        shodhana_permitted = False
        gating_status = GatingStatus.GATED_FOR_DEEPANA_PACHANA
        directives.append(
            TherapeuticDirective(
                phase="PREPARATORY_DEEPANA",
                action_type="MILD_DEEPANA",
                herbal_recommendations=["Jeeraka-Shunthi Phanta", "Ajawain Arka", "Lashunadi Vati"],
                dietary_guidelines=["Light warm meals twice daily", "Kitchari with cumin and ghee in modest quantity"],
                contraindications=["Immediate Shodhana prohibited", "Over-eating / snacking between meals"],
            )
        )
        return (shodhana_permitted, gating_status, directives)

    # SAFETY FIREWALL RULE 4: NIRAMA (Clear of Ama, AGI < 20)
    if agni_type == AgniType.TIKSHNAGNI:
        shodhana_permitted = False
        gating_status = GatingStatus.GATED_TIKSHNAGNI_PACIFICATION
        directives.append(
            TherapeuticDirective(
                phase="PITTA_AGNI_PACIFICATION",
                action_type="SHITHALA_DEEPANA",
                herbal_recommendations=["Mahatiktaka Ghrita", "Amalaki Rasayana", "Shatavari Churna with milk"],
                dietary_guidelines=["Ghee, cooling sweet fruits, barley, milk preparations", "Avoid hot pungent spices and alcohol"],
                contraindications=["Hot pungent Deepana herbs", "Fasting / Langhana (exacerbates Tikshnagni)"],
            )
        )
        return (shodhana_permitted, gating_status, directives)

    # All safety firewalls satisfied -> Cleared for Shodhana
    shodhana_permitted = True
    gating_status = GatingStatus.CLEARED_FOR_SHODHANA
    directives.append(
        TherapeuticDirective(
            phase="PURVAKARMA_CLEARANCE",
            action_type="SNEHANA_SWEDANA_PERMITTED",
            herbal_recommendations=["Indicated medicated Ghrita for Snehapana (e.g. Sukumara Ghrita or Guggulutiktaka)", "Dashamula Kwatha for Bashpa Sweda"],
            dietary_guidelines=["Warm rice with liquid ghee during Snehapana period", "Strict boiled warm water regimen"],
            contraindications=["Cold exposure", "Suppression of natural urges (Vegadharana)", "Daytime sleeping (Divaswapna)"],
        )
    )
    return (shodhana_permitted, gating_status, directives)


def evaluate_ama_agni(
    req: AmaAgniEvaluationRequest,
    evaluator_arn: str,
    hospital_id: str,
) -> AmaAgniOutput:
    """Execute complete Ama Grading Index and Agni Vector clinical assessment."""
    agi_score = calculate_agi_score(req.symptoms)
    ama_grade = classify_ama_grade(agi_score)
    agni_vector, agni_type = calculate_agni_vector(req.agni_params)

    shodhana_permitted, gating_status, directives = evaluate_gating_and_directives(
        ama_grade=ama_grade,
        agni_type=agni_type,
        agi_score=agi_score,
    )

    return AmaAgniOutput(
        assessment_id=f"aag-{uuid.uuid4().hex[:12]}",
        patient_id=req.patient_id,
        hospital_id=hospital_id,
        evaluator_arn=evaluator_arn,
        agi_score=agi_score,
        ama_grade=ama_grade,
        agni_type=agni_type,
        agni_vector=agni_vector,
        shodhana_permitted=shodhana_permitted,
        gating_status=gating_status,
        therapeutic_directives=directives,
        timestamp=int(time.time()),
    )
