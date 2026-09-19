"""Dashavidha Pariksha Clinical Evaluation Engine & Rogi-Roga Bala Valuation."""
from typing import Tuple
from models.dashavidha import (
    AgniType,
    DashavidhaParikshaInput,
    DehaDesha,
    DushyaDhatu,
    GradingScale,
    TherapeuticEligibility,
    VayasStage,
)

GRADE_SCORE = {
    GradingScale.PRAVARA: 3.0,
    GradingScale.MADHYAMA: 2.0,
    GradingScale.AVARA: 1.0,
}

DUSHYA_SEVERITY_WEIGHT = {
    DushyaDhatu.RASA: 1.0,
    DushyaDhatu.PURISHA: 1.0,
    DushyaDhatu.MUTRA: 1.0,
    DushyaDhatu.SVEDA: 1.0,
    DushyaDhatu.RAKTA: 2.0,
    DushyaDhatu.MAMSA: 2.0,
    DushyaDhatu.MEDA: 2.5,
    DushyaDhatu.ASTHI: 3.0,
    DushyaDhatu.MAJJA: 3.5,
    DushyaDhatu.SHUKRA: 4.0,
}


def compute_rogi_bala(exam: DashavidhaParikshaInput) -> float:
    """
    Calculate normalized patient host vitality score (Rogi Bala) [0 - 100].
    Incorporates constitutional Bala, mental Sattva, nutritional Satmya, Ahara-Shakti, and Vayas.
    """
    # 1. Bala (Sahaja + Kalaja + Yuktikrita) [Range 3 to 9]
    bala_sum = (
        GRADE_SCORE[exam.bala.sahaja] +
        GRADE_SCORE[exam.bala.kalaja] +
        GRADE_SCORE[exam.bala.yuktikrita]
    )
    bala_norm = (bala_sum - 3.0) / 6.0  # [0.0 - 1.0]

    # 2. Sattva (Mental Fortitude) [Range 1 to 3]
    sattva_norm = (GRADE_SCORE[exam.sattva] - 1.0) / 2.0

    # 3. Satmya (Habituation) [Range 1 to 3]
    satmya_norm = (GRADE_SCORE[exam.satmya] - 1.0) / 2.0

    # 4. Ahara-Shakti (Abhyavaharana + Jarana) [Range 2 to 6]
    ahara_sum = (
        GRADE_SCORE[exam.ahara_shakti.abhyavaharana] +
        GRADE_SCORE[exam.ahara_shakti.jarana]
    )
    ahara_norm = (ahara_sum - 2.0) / 4.0

    # 5. Vayas (Age Vitality)
    vayas_norm = 1.0 if exam.vayas_stage == VayasStage.MADHYAMA else (
        0.6 if exam.vayas_stage == VayasStage.BALYA else 0.3
    )

    weighted_score = (
        (0.25 * bala_norm) +
        (0.20 * sattva_norm) +
        (0.15 * satmya_norm) +
        (0.25 * ahara_norm) +
        (0.15 * vayas_norm)
    )
    return round(float(weighted_score * 100.0), 2)


def compute_roga_bala(exam: DashavidhaParikshaInput) -> float:
    """
    Calculate normalized disease virulence and tissue penetration score (Roga Bala) [0 - 100].
    Evaluates Dushya invasiveness, chronicity, Rogamarga depth, and Agni disruption.
    """
    # 1. Dushya Tissue Depth [Max ~12 pts]
    dushya_score = sum(DUSHYA_SEVERITY_WEIGHT.get(d, 1.0) for d in exam.dushya.primary_dushyas)
    dushya_norm = min(dushya_score / 10.0, 1.0) * 35.0  # Max 35%

    # 2. Chronicity
    days = exam.dushya.chronicity_days
    if days < 30:
        chronicity_score = 10.0
    elif days <= 180:
        chronicity_score = 20.0
    else:
        chronicity_score = 30.0  # Max 30% for chronic deep-seated disease

    # 3. Deha Desha (Rogamarga)
    if exam.desha.deha == DehaDesha.KOSHTHA:
        roamarga_score = 5.0
    elif exam.desha.deha == DehaDesha.SHAKHA:
        roamarga_score = 12.0
    else:  # MARMA_ASTHI_SANDHI
        roamarga_score = 20.0  # Max 20%

    # 4. Agni Impairment (Anala)
    if exam.anala.agni == AgniType.SAMAGNI:
        agni_score = 2.0
    elif exam.anala.agni == AgniType.VISHAMAGNI:
        agni_score = 10.0
    elif exam.anala.agni == AgniType.TIKSHNAGNI:
        agni_score = 12.0
    else:  # MANDAGNI
        agni_score = 15.0  # Max 15%

    total_roga = dushya_norm + chronicity_score + roamarga_score + agni_score
    return round(min(float(total_roga), 100.0), 2)


def evaluate_dashavidha_pariksha(
    exam: DashavidhaParikshaInput
) -> Tuple[float, float, float, TherapeuticEligibility, str]:
    """
    Evaluate 10-fold systemic clinical assessment, compute Rogi-Roga Bala valuation ratio,
    and determine therapeutic eligibility.
    Returns: (rogi_bala, roga_bala, rogi_roga_ratio, eligibility, clinical_rationale).
    """
    rogi_bala = compute_rogi_bala(exam)
    roga_bala = compute_roga_bala(exam)

    # Calculate ratio safely
    rogi_roga_ratio = round(rogi_bala / max(roga_bala, 5.0), 2)

    if rogi_roga_ratio > 1.20:
        eligibility = TherapeuticEligibility.SHODHANA_ELIGIBLE
        rationale = (
            f"Patient host vitality (Rogi Bala: {rogi_bala:.1f}) significantly exceeds disease burden "
            f"(Roga Bala: {roga_bala:.1f}; Ratio: {rogi_roga_ratio:.2f}). "
            "Patient possesses physiological reserve for radical Panchakarma Shodhana (Vamana/Virechana/Basti)."
        )
    elif rogi_roga_ratio >= 0.80:
        eligibility = TherapeuticEligibility.SHAMANA_INDICATED
        rationale = (
            f"Patient host vitality (Rogi Bala: {rogi_bala:.1f}) is commensurate with disease intensity "
            f"(Roga Bala: {roga_bala:.1f}; Ratio: {rogi_roga_ratio:.2f}). "
            "Moderate reserve indicates internal Shamana pharmacotherapy, gradual Deepana-Pachana, and mild purification."
        )
    else:
        eligibility = TherapeuticEligibility.BRIMHANA_SUPPORTIVE_ONLY
        rationale = (
            f"Patient host vitality (Rogi Bala: {rogi_bala:.1f}) is severely compromised relative to disease severity "
            f"(Roga Bala: {roga_bala:.1f}; Ratio: {rogi_roga_ratio:.2f}). "
            "Exhaustive Shodhana procedures are strictly contraindicated due to risk of collapse (Ojobhransha); "
            "nutritive Brimhana, Rasayana, and gentle supportive care mandated."
        )

    return rogi_bala, roga_bala, rogi_roga_ratio, eligibility, rationale
