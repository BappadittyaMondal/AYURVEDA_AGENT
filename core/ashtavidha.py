"""Ashtavidha Pariksha Clinical Diagnostics & Multi-Modal Doshic Evaluation Engine."""
from typing import Optional, Tuple
from core.prakriti import DIRICHLET_EPSILON
from models.ashtavidha import (
    AkritiPosture,
    AshtavidhaParikshaInput,
    DrikSclera,
    JalaNimajjanaResult,
    JihwaCoating,
    JihwaColor,
    MalaConsistency,
    MutraColor,
    NadiGati,
    NadiRhythm,
    NadiVolume,
    ShabdaTone,
    SparshaMoisture,
    SparshaTemp,
)


def evaluate_ashtavidha_pariksha(
    exam: AshtavidhaParikshaInput
) -> Tuple[float, float, float, str, Optional[str], bool, str]:
    """
    Evaluate the 8-fold classical examination modalities and compute normalized Doshic weights,
    primary/secondary Doshic manifestation, and Ama suspicion status.
    Returns: (vata_score, pitta_score, kapha_score, primary_dosha, secondary_dosha, ama_suspected, summary).
    """
    score_v = 0.0
    score_p = 0.0
    score_k = 0.0
    findings = []

    # 1. Nadi (Pulse)
    if exam.nadi.gati == NadiGati.SARPA:
        score_v += 3.0
        findings.append("Nadi: Sarpa Gati (Vataja)")
    elif exam.nadi.gati == NadiGati.MANDUKA:
        score_p += 3.0
        findings.append("Nadi: Manduka Gati (Pittaja)")
    elif exam.nadi.gati == NadiGati.HAMSA:
        score_k += 3.0
        findings.append("Nadi: Hamsa Gati (Kaphaja)")
    elif exam.nadi.gati == NadiGati.JALAUKA:
        score_p += 1.0
        score_k += 2.0
        findings.append("Nadi: Jalauka Gati (Kapha-Pitta)")
    elif exam.nadi.gati == NadiGati.KAKA:
        score_v += 2.0
        score_p += 1.0
        score_k += 1.0
        findings.append("Nadi: Kaka Gati (Sannipataja/Arrhythmic)")

    if exam.nadi.rhythm == NadiRhythm.IRREGULAR:
        score_v += 1.0
    if exam.nadi.volume == NadiVolume.FEEBLE:
        score_v += 1.0
    elif exam.nadi.volume == NadiVolume.BOUNDING:
        score_p += 1.0
    if exam.nadi.rate_bpm > 90:
        score_p += 1.0
    elif exam.nadi.rate_bpm < 60:
        score_k += 1.0

    # 2. Mutra (Urine)
    if exam.mutra.color in [MutraColor.DARK_YELLOW, MutraColor.REDDISH_BROWN]:
        score_p += 2.0
        findings.append("Mutra: Pitta varna (Dark/Reddish)")
    elif exam.mutra.color == MutraColor.PALE_CLEAR:
        score_v += 1.0
    elif exam.mutra.color == MutraColor.MILKY_TURBID:
        score_k += 2.0
        findings.append("Mutra: Kapha varna (Milky/Turbid)")

    if exam.mutra.dysuria:
        score_p += 1.0

    # 3. Mala (Stool)
    if exam.mala.consistency == MalaConsistency.HARD_DRY_SCYBALOUS:
        score_v += 2.0
        findings.append("Mala: Vibandha / Krura (Vataja)")
    elif exam.mala.consistency in [MalaConsistency.SOFT_LOOSE, MalaConsistency.WATERY]:
        score_p += 2.0
        findings.append("Mala: Mridu / Bhedana (Pittaja)")

    # 4. Jihwa (Tongue)
    if exam.jihwa.color == JihwaColor.RED:
        score_p += 2.0
    elif exam.jihwa.color == JihwaColor.BLUISH_CYANOTIC:
        score_v += 2.0
    elif exam.jihwa.color == JihwaColor.PALE:
        score_k += 1.0

    if exam.jihwa.coating == JihwaCoating.THICK_WHITE:
        score_k += 2.0
        findings.append("Jihwa: Thick white coating (Kapha-Ama)")
    elif exam.jihwa.coating == JihwaCoating.THICK_YELLOW:
        score_p += 2.0
        findings.append("Jihwa: Thick yellow coating (Pitta-Ama)")
    elif exam.jihwa.coating == JihwaCoating.THICK_BROWN_BLACK:
        score_v += 2.0
        findings.append("Jihwa: Dark coating (Vata-Ama)")

    if exam.jihwa.fissures:
        score_v += 1.0
    if exam.jihwa.tooth_indentations:
        score_k += 1.0

    # 5. Shabda (Voice)
    if exam.shabda.tone in [ShabdaTone.HIGH_PITCHED_FAST, ShabdaTone.HOARSE_HARSH]:
        score_v += 1.0
    elif exam.shabda.tone == ShabdaTone.LOW_DEEP:
        score_k += 1.0

    # 6. Sparsha (Touch/Skin)
    if exam.sparsha.temperature == SparshaTemp.BURNING_HOT:
        score_p += 2.0
        findings.append("Sparsha: Ushna (Pittaja)")
    elif exam.sparsha.temperature == SparshaTemp.COLD_CHILLY:
        score_v += 1.0
    elif exam.sparsha.temperature == SparshaTemp.COOL_DAMP:
        score_k += 1.0

    if exam.sparsha.moisture == SparshaMoisture.DRY_ROUGH:
        score_v += 1.0
    elif exam.sparsha.moisture == SparshaMoisture.PROFUSE_SWEAT:
        score_p += 1.0
    elif exam.sparsha.moisture == SparshaMoisture.CLAMMY:
        score_k += 1.0

    # 7. Drik (Eyes/Vision)
    if exam.drik.sclera in [DrikSclera.YELLOW_ICTERIC, DrikSclera.RED_CONGESTED]:
        score_p += 2.0
        findings.append("Drik: Haridra/Rakta sclera (Pittaja)")
    elif exam.drik.sclera == DrikSclera.MUDDY_DRY:
        score_v += 1.0
    elif exam.drik.sclera == DrikSclera.PALE:
        score_k += 1.0
    if exam.drik.photophobia:
        score_p += 1.0

    # 8. Akriti (Build/Gait)
    if exam.akriti.posture == AkritiPosture.EMACIATED_STOOPED:
        score_v += 1.0
    elif exam.akriti.posture == AkritiPosture.ATHLETIC_MODERATE:
        score_p += 1.0
    elif exam.akriti.posture == AkritiPosture.OBESE_HEAVY:
        score_k += 1.0

    # Ama Suspicion Criteria
    ama_suspected = False
    if exam.mala.jala_nimajjana == JalaNimajjanaResult.SINKS_SAMA:
        ama_suspected = True
        findings.append("Jala Nimajjana: Stool sinks immediately (Ama present)")
    elif exam.jihwa.coating in [JihwaCoating.THICK_WHITE, JihwaCoating.THICK_YELLOW, JihwaCoating.THICK_BROWN_BLACK]:
        ama_suspected = True
    elif exam.jihwa.tooth_indentations and exam.mala.jala_nimajjana != JalaNimajjanaResult.FLOATS_NIRAMA:
        ama_suspected = True

    # Normalize scores onto Simplex
    total = score_v + score_p + score_k
    if total == 0:
        return 0.3333, 0.3333, 0.3334, "TRIDOSHA", None, ama_suspected, "Sama Ashtavidha findings."

    eps = DIRICHLET_EPSILON
    raw_v = score_v / total
    raw_p = score_p / total
    raw_k = score_k / total

    v = (1.0 - 3.0 * eps) * raw_v + eps
    p = (1.0 - 3.0 * eps) * raw_p + eps
    k = (1.0 - 3.0 * eps) * raw_k + eps

    norm_sum = v + p + k
    v_norm = max(round(v / norm_sum, 4), eps)
    p_norm = max(round(p / norm_sum, 4), eps)
    k_norm = round(1.0 - (v_norm + p_norm), 4)

    scores = [("VATA", v_norm), ("PITTA", p_norm), ("KAPHA", k_norm)]
    scores.sort(key=lambda x: x[1], reverse=True)

    primary_dosha = scores[0][0]
    secondary_dosha = scores[1][0] if scores[1][1] > 0.25 else None

    summary = "; ".join(findings) if findings else f"Predominant {primary_dosha} clinical presentation."

    return v_norm, p_norm, k_norm, primary_dosha, secondary_dosha, ama_suspected, summary
