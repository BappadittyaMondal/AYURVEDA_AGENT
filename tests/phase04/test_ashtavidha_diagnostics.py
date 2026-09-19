"""Phase 04: Test Suite for Ashtavidha Pariksha Clinical Diagnostics & Ama Detection."""
import pytest
from core.ashtavidha import evaluate_ashtavidha_pariksha
from models.ashtavidha import (
    AkritiExam,
    AkritiPosture,
    AshtavidhaParikshaInput,
    DrikExam,
    DrikSclera,
    JalaNimajjanaResult,
    JihwaCoating,
    JihwaColor,
    JihwaExam,
    MalaConsistency,
    MalaExam,
    MutraColor,
    MutraExam,
    NadiExam,
    NadiGati,
    NadiRhythm,
    NadiVolume,
    ShabdaExam,
    ShabdaTone,
    SparshaExam,
    SparshaMoisture,
    SparshaTemp,
    TailaBinduDirection,
)


def test_ashtavidha_vata_predominance():
    """Verify that classical Vata signs across all 8 modalities yield VATA primary diagnosis."""
    exam = AshtavidhaParikshaInput(
        nadi=NadiExam(gati=NadiGati.SARPA, rate_bpm=88, rhythm=NadiRhythm.IRREGULAR, volume=NadiVolume.FEEBLE),
        mutra=MutraExam(color=MutraColor.PALE_CLEAR, clarity="CLEAR", frequency_day=6, taila_bindu_direction=TailaBinduDirection.NORTH),
        mala=MalaExam(consistency=MalaConsistency.HARD_DRY_SCYBALOUS, jala_nimajjana=JalaNimajjanaResult.FLOATS_NIRAMA),
        jihwa=JihwaExam(color=JihwaColor.BLUISH_CYANOTIC, coating=JihwaCoating.CLEAN_NIRAMA, fissures=True),
        shabda=ShabdaExam(tone=ShabdaTone.HIGH_PITCHED_FAST),
        sparsha=SparshaExam(temperature=SparshaTemp.COLD_CHILLY, moisture=SparshaMoisture.DRY_ROUGH),
        drik=DrikExam(sclera=DrikSclera.MUDDY_DRY),
        akriti=AkritiExam(posture=AkritiPosture.EMACIATED_STOOPED)
    )
    v, p, k, primary, secondary, ama, summary = evaluate_ashtavidha_pariksha(exam)

    assert primary == "VATA"
    assert v > 0.65
    assert ama is False
    assert "Sarpa Gati" in summary


def test_ashtavidha_pitta_predominance():
    """Verify that classical Pitta signs across all 8 modalities yield PITTA primary diagnosis."""
    exam = AshtavidhaParikshaInput(
        nadi=NadiExam(gati=NadiGati.MANDUKA, rate_bpm=96, rhythm=NadiRhythm.REGULAR, volume=NadiVolume.BOUNDING),
        mutra=MutraExam(color=MutraColor.DARK_YELLOW, clarity="CLEAR", frequency_day=7, dysuria=True),
        mala=MalaExam(consistency=MalaConsistency.SOFT_LOOSE, jala_nimajjana=JalaNimajjanaResult.FLOATS_NIRAMA),
        jihwa=JihwaExam(color=JihwaColor.RED, coating=JihwaCoating.CLEAN_NIRAMA),
        shabda=ShabdaExam(tone=ShabdaTone.CLEAR_RESONANT),
        sparsha=SparshaExam(temperature=SparshaTemp.BURNING_HOT, moisture=SparshaMoisture.PROFUSE_SWEAT),
        drik=DrikExam(sclera=DrikSclera.YELLOW_ICTERIC, photophobia=True),
        akriti=AkritiExam(posture=AkritiPosture.ATHLETIC_MODERATE)
    )
    v, p, k, primary, secondary, ama, summary = evaluate_ashtavidha_pariksha(exam)

    assert primary == "PITTA"
    assert p > 0.65
    assert ama is False
    assert "Manduka Gati" in summary


def test_ashtavidha_kapha_ama_predominance():
    """Verify that Kapha signs with sinking stool and thick coating trigger Ama suspicion."""
    exam = AshtavidhaParikshaInput(
        nadi=NadiExam(gati=NadiGati.HAMSA, rate_bpm=58, rhythm=NadiRhythm.REGULAR, volume=NadiVolume.MODERATE),
        mutra=MutraExam(color=MutraColor.MILKY_TURBID, clarity="TURBID", frequency_day=4),
        mala=MalaExam(consistency=MalaConsistency.NORMAL_FORMED, jala_nimajjana=JalaNimajjanaResult.SINKS_SAMA),
        jihwa=JihwaExam(color=JihwaColor.PALE, coating=JihwaCoating.THICK_WHITE, tooth_indentations=True),
        shabda=ShabdaExam(tone=ShabdaTone.LOW_DEEP),
        sparsha=SparshaExam(temperature=SparshaTemp.COOL_DAMP, moisture=SparshaMoisture.CLAMMY),
        drik=DrikExam(sclera=DrikSclera.PALE),
        akriti=AkritiExam(posture=AkritiPosture.OBESE_HEAVY)
    )
    v, p, k, primary, secondary, ama, summary = evaluate_ashtavidha_pariksha(exam)

    assert primary == "KAPHA"
    assert k > 0.60
    assert ama is True  # Must trigger Ama flag
    assert "Jala Nimajjana: Stool sinks" in summary
