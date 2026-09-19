"""Dhatu Sarata Quantitative Tissue Vitality Index (7 Dhatus + Sattva).

Classical References:
- Charaka Samhita, Vimanasthana Ch. 8 (Ashta Sara Purusha Pariksha)
- Sushruta Samhita, Sutrasthana Ch. 35 (Aturalambana Pariksha)
- Ashtanga Hridaya, Sharirasthana Ch. 3 (Angavibhaga Adhyaya)
"""
import uuid
import time
from typing import Dict, List, Tuple

from models.dhatu_sarata import (
    DhatuType,
    SarataTier,
    DhatuRating,
    DhatuSarataInput,
    DhatuRasayanaDirective,
    DhatuSarataOutput,
)


DHATU_WEIGHTS: Dict[DhatuType, float] = {
    DhatuType.RASA: 1.0,
    DhatuType.RAKTA: 1.1,
    DhatuType.MAMSA: 1.2,
    DhatuType.MEDA: 1.0,
    DhatuType.ASTHI: 1.1,
    DhatuType.MAJJA: 1.2,
    DhatuType.SHUKRA: 1.3,
    DhatuType.SATTVA: 1.4,
}

RASAYANA_KNOWLEDGE_BASE: Dict[DhatuType, Dict[str, List[str]]] = {
    DhatuType.RASA: {
        "herbs": ["Shatavari", "Draksha", "Kharjura", "Yashtimadhu"],
        "diet": ["Fresh warm milk with cardamom", "Sweet seasonal fruits", "Coconut water", "Light Yavagu"],
        "risk": "Depletion causes dehydration, dry skin, fatigue, and impaired lymphatic microcirculation.",
    },
    DhatuType.RAKTA: {
        "herbs": ["Amalaki", "Sariva", "Manjistha", "Lohasava"],
        "diet": ["Pomegranate", "Black raisins", "Beetroot", "Red rice (Raktashali)"],
        "risk": "Depletion causes pallor, vascular weakness, cold extremities, and anemia.",
    },
    DhatuType.MAMSA: {
        "herbs": ["Ashwagandha", "Bala", "Atibala", "Vidari"],
        "diet": ["Masha (Black gram)", "Almonds soaked in water", "Warm nourishing vegetable soups", "Ghee"],
        "risk": "Depletion causes muscle wasting, loss of structural stamina, and joint instability.",
    },
    DhatuType.MEDA: {
        "herbs": ["Guggulu", "Shilajit", "Musta", "Triphala"],
        "diet": ["Barley (Yava)", "Horse gram (Kulatta)", "Honey with lukewarm water", "Steamed leafy greens"],
        "risk": "Imbalance causes either joint crackling, dry skin (Kshaya) or metabolic heaviness, dyslipidemia (Vriddhi).",
    },
    DhatuType.ASTHI: {
        "herbs": ["Pravala Pishti", "Mukta Shukti Bhasma", "Laksha", "Asthisamharaka (Hadjod)"],
        "diet": ["Sesame seeds (Tila)", "Moringa / Drumstick leaves", "A2 cow's milk", "Finger millet (Ragi)"],
        "risk": "Depletion causes osteopenia, bone pain, brittle nails, and dental degradation.",
    },
    DhatuType.MAJJA: {
        "herbs": ["Guduchi", "Brahmi", "Shankhapushpi", "Jyotishmati"],
        "diet": ["Cow's ghee", "Walnuts", "Bone marrow broths (where indicated)", "Warm spiced milk"],
        "risk": "Depletion causes neuro-motor weakness, sleep disturbances, cognitive decline, and joint hollowness.",
    },
    DhatuType.SHUKRA: {
        "herbs": ["Kapikacchu", "Gokshura", "Safed Musli", "Ashwagandha"],
        "diet": ["A2 Cow's milk with saffron", "Ghee", "Dates", "Almonds"],
        "risk": "Depletion causes loss of Ojas, chronic lethargy, reduced regenerative vigor, and reproductive dysfunction.",
    },
    DhatuType.SATTVA: {
        "herbs": ["Brahmi Rasayana", "Mandukaparni", "Kushmanda Avaleha", "Jatamansi"],
        "diet": ["Freshly cooked Satvik vegetarian meals", "Ghee", "Almonds", "Cardamom infusion"],
        "risk": "Depletion causes low stress tolerance, anxiety, mood instability, and loss of psychological fortitude.",
    },
}


def classify_tier_from_score(score: float) -> SarataTier:
    """Classify 0.0-1.0 or percentage score into Pravara, Madhyama, or Avara."""
    if score >= 0.75:
        return SarataTier.PRAVARA
    elif score >= 0.50:
        return SarataTier.MADHYAMA
    else:
        return SarataTier.AVARA


def calculate_overall_sarata_index(ratings: List[DhatuRating]) -> Tuple[float, SarataTier, Dict[str, float]]:
    """Compute weighted Overall Sarata Index (0-100%) and individual Dhatu scores."""
    rating_map = {r.dhatu: r.score for r in ratings}

    total_weighted_score = 0.0
    total_weights = 0.0
    dhatu_scores: Dict[str, float] = {}

    for dhatu, weight in DHATU_WEIGHTS.items():
        score = rating_map.get(dhatu, 0.5)
        dhatu_scores[dhatu.value] = round(score, 3)
        total_weighted_score += score * weight
        total_weights += weight

    osi = (total_weighted_score / total_weights) * 100.0
    overall_tier = classify_tier_from_score(osi / 100.0)

    return (round(osi, 2), overall_tier, dhatu_scores)


def generate_dhatu_directives(ratings: List[DhatuRating]) -> Tuple[List[str], List[DhatuRasayanaDirective]]:
    """Identify vulnerable tissues and generate targeted Rasayana directives."""
    vulnerable_dhatus: List[str] = []
    directives: List[DhatuRasayanaDirective] = []

    for r in ratings:
        tier = classify_tier_from_score(r.score)
        if r.score < 0.60:
            vulnerable_dhatus.append(r.dhatu.value)

        kb = RASAYANA_KNOWLEDGE_BASE.get(r.dhatu, {"herbs": [], "diet": [], "risk": ""})

        directives.append(
            DhatuRasayanaDirective(
                dhatu=r.dhatu,
                vitality_tier=tier,
                vulnerability_risk=kb["risk"],
                indicated_rasayana_herbs=kb["herbs"],
                dietary_guidelines=kb["diet"],
            )
        )

    return (vulnerable_dhatus, directives)


def evaluate_dhatu_sarata(
    input_data: DhatuSarataInput,
    evaluator_arn: str,
    hospital_id: str,
) -> DhatuSarataOutput:
    """Execute complete 8-tissue Sarata evaluation, OSI quantification, and Rasayana guidance."""
    osi, overall_tier, dhatu_scores = calculate_overall_sarata_index(input_data.dhatu_ratings)
    vulnerable, directives = generate_dhatu_directives(input_data.dhatu_ratings)

    return DhatuSarataOutput(
        assessment_id=f"sar-{uuid.uuid4().hex[:12]}",
        patient_id=input_data.patient_id,
        hospital_id=hospital_id,
        evaluator_arn=evaluator_arn,
        overall_sarata_index=osi,
        sarata_tier=overall_tier,
        dhatu_scores=dhatu_scores,
        vulnerable_dhatus=vulnerable,
        rasayana_directives=directives,
        timestamp=int(time.time()),
    )
