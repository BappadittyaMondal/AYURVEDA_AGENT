"""Shat Kriya Kala Pathological Stage Tracker & Progression Engine (6 Stages).

Classical References:
- Sushruta Samhita, Sutrasthana Ch. 21 (Vranaprashna Adhyaya - Shat Kriya Kala)
- Ashtanga Hridaya, Sutrasthana Ch. 12 & 13
"""
import uuid
import time
from typing import Dict, List, Tuple

from models.kriya_kala import (
    KriyaKalaStage,
    CurabilityPrognosis,
    StageObservationInput,
    KriyaKalaInput,
    KriyaKalaOutput,
)


def calculate_kriya_kala_distribution(
    obs: StageObservationInput,
) -> Tuple[Dict[str, float], KriyaKalaStage, float]:
    """Compute smoothed probability distribution over Delta^5 simplex and Pathological Progression Index."""
    # Raw weight scores
    w1 = float(obs.sanchaya_features)
    w2 = float(obs.prakopa_features)
    w3 = float(obs.prasara_features)
    w4 = float(obs.sthanasamshraya_features) + (0.5 * len(obs.prodromal_symptoms))
    w5 = float(obs.vyakti_features) + (0.5 * len(obs.manifest_symptoms))
    w6 = float(obs.bheda_features) + (0.5 * len(obs.complications))

    # Add baseline 0.01 to ensure non-zero simplex coordinates
    scores = [
        max(w1, 0.01),
        max(w2, 0.01),
        max(w3, 0.01),
        max(w4, 0.01),
        max(w5, 0.01),
        max(w6, 0.01),
    ]

    total = sum(scores)
    raw_probs = [s / total for s in scores]

    # Dirichlet boundary smoothing (epsilon = 1e-4)
    eps = 1e-4
    smoothed_probs = [(1.0 - 6.0 * eps) * p + eps for p in raw_probs]

    stage_keys = [
        KriyaKalaStage.SANCHAYA,
        KriyaKalaStage.PRAKOPA,
        KriyaKalaStage.PRASARA,
        KriyaKalaStage.STHANASAMSHRAYA,
        KriyaKalaStage.VYAKTI,
        KriyaKalaStage.BHEDA,
    ]

    prob_dict = {
        stage.value: round(p, 4) for stage, p in zip(stage_keys, smoothed_probs)
    }

    # Primary Stage = argmax
    max_idx = max(range(6), key=lambda i: smoothed_probs[i])
    primary_stage = stage_keys[max_idx]

    # Pathological Progression Index (1.0 to 6.0)
    ppi = sum((i + 1) * p for i, p in enumerate(smoothed_probs))

    return (prob_dict, primary_stage, round(ppi, 2))


def evaluate_prognosis_and_directives(
    stage: KriyaKalaStage,
    ppi: float,
) -> Tuple[float, CurabilityPrognosis, str]:
    """Determine reversibility percentage, curability prognosis, and Kriyavidhi directive."""
    if ppi < 1.8:
        reversibility = round(100.0 - (ppi - 1.0) * 10.0, 1)
        prognosis = CurabilityPrognosis.SUKHASADHYA
        directive = (
            "Stage 1 (Sanchaya): Critical early window. Discontinue causative factors (Nidana Parivarjana), "
            "administer mild opposite-quality diet (Viparita Ahara) and mild Apatarpana to prevent provocation."
        )
    elif ppi < 2.8:
        reversibility = round(92.0 - (ppi - 1.8) * 12.0, 1)
        prognosis = CurabilityPrognosis.SUKHASADHYA
        directive = (
            "Stage 2 (Prakopa): Excitation stage. Administer targeted Shamana dravyas or mild Sthanika Shodhana "
            "(e.g. Koshtha Shodhana) before systemic dissemination."
        )
    elif ppi < 3.8:
        reversibility = round(80.0 - (ppi - 2.8) * 15.0, 1)
        prognosis = CurabilityPrognosis.KRICHRASADHYA
        directive = (
            "Stage 3 (Prasara): Overflow stage. Mobilize circulating Doshas toward the alimentary canal "
            "(Rogamarga Anulomana) using Deepana-Pachana and Snehana."
        )
    elif ppi < 4.8:
        reversibility = round(65.0 - (ppi - 3.8) * 15.0, 1)
        prognosis = CurabilityPrognosis.KRICHRASADHYA
        directive = (
            "Stage 4 (Sthanasamshraya): Crucial Prodromal window (Purvaroopa). Clear localized Khavaigunya, "
            "arrest Dosha-Dushya Sammurchhana before irreversible cellular localization."
        )
    elif ppi < 5.5:
        reversibility = round(50.0 - (ppi - 4.8) * 20.0, 1)
        prognosis = CurabilityPrognosis.KRICHRASADHYA
        directive = (
            "Stage 5 (Vyakti): Full clinical manifestation stage (Roopa). Implement comprehensive Vyadhi-pratyanika "
            "Chikitsa (disease-specific Shodhana and Shamana protocols)."
        )
    else:
        reversibility = round(max(10.0, 36.0 - (ppi - 5.5) * 30.0), 1)
        prognosis = CurabilityPrognosis.YAPYA if reversibility >= 20.0 else CurabilityPrognosis.ASADHYA
        directive = (
            "Stage 6 (Bheda): Chronic / complicated stage (Upadrava). Manage tissue breakdown, suppuration (Paka/Vrana), "
            "secondary complications, and establish palliative chronic Yapya maintenance."
        )

    return (reversibility, prognosis, directive)


def evaluate_kriya_kala(
    input_data: KriyaKalaInput,
    evaluator_arn: str,
    hospital_id: str,
) -> KriyaKalaOutput:
    """Execute complete Shat Kriya Kala staging, progression metrics, and therapeutic directive."""
    prob_dict, primary_stage, ppi = calculate_kriya_kala_distribution(input_data.observations)
    reversibility, prognosis, directive = evaluate_prognosis_and_directives(primary_stage, ppi)

    return KriyaKalaOutput(
        assessment_id=f"krk-{uuid.uuid4().hex[:12]}",
        patient_id=input_data.patient_id,
        hospital_id=hospital_id,
        evaluator_arn=evaluator_arn,
        current_stage=primary_stage,
        pathological_progression_index=ppi,
        stage_probabilities=prob_dict,
        prodromal_symptoms=input_data.observations.prodromal_symptoms,
        manifest_symptoms=input_data.observations.manifest_symptoms,
        complications=input_data.observations.complications,
        reversibility_percentage=reversibility,
        curability_prognosis=prognosis,
        therapeutic_window_directive=directive,
        timestamp=int(time.time()),
    )
