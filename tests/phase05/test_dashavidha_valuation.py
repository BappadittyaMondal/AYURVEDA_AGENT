"""Phase 05: Test Suite for Dashavidha Pariksha & Rogi-Roga Bala Valuation."""
import pytest
from core.dashavidha import evaluate_dashavidha_pariksha
from models.dashavidha import (
    AgniType,
    AharaShaktiAssessment,
    AnalaAssessment,
    BalaAssessment,
    BhumiDesha,
    DashavidhaParikshaInput,
    DehaDesha,
    DeshaAssessment,
    DushyaAssessment,
    DushyaDhatu,
    GradingScale,
    TherapeuticEligibility,
    VayasStage,
)


def test_high_vitality_shodhana_eligibility():
    """Verify that robust patient with high Rogi Bala and mild Roga Bala qualifies for Shodhana."""
    exam = DashavidhaParikshaInput(
        dushya=DushyaAssessment(primary_dushyas=[DushyaDhatu.RASA], chronicity_days=10),
        desha=DeshaAssessment(bhumi=BhumiDesha.SADHARANA, deha=DehaDesha.KOSHTHA),
        bala=BalaAssessment(
            sahaja=GradingScale.PRAVARA,
            kalaja=GradingScale.PRAVARA,
            yuktikrita=GradingScale.PRAVARA
        ),
        kala_season="VASANTA",
        anala=AnalaAssessment(agni=AgniType.SAMAGNI),
        vayas_stage=VayasStage.MADHYAMA,
        sattva=GradingScale.PRAVARA,
        satmya=GradingScale.PRAVARA,
        ahara_shakti=AharaShaktiAssessment(
            abhyavaharana=GradingScale.PRAVARA,
            jarana=GradingScale.PRAVARA
        )
    )

    rogi_bala, roga_bala, ratio, eligibility, rationale = evaluate_dashavidha_pariksha(exam)

    assert rogi_bala > 90.0, f"Expected high Rogi Bala, got {rogi_bala}"
    assert roga_bala < 35.0, f"Expected low Roga Bala, got {roga_bala}"
    assert ratio > 2.0, f"Expected ratio > 2.0, got {ratio}"
    assert eligibility == TherapeuticEligibility.SHODHANA_ELIGIBLE
    assert "radical Panchakarma Shodhana" in rationale


def test_frail_patient_shodhana_contraindication():
    """Verify that elderly, frail patient facing deep chronic pathology is blocked from Shodhana."""
    exam = DashavidhaParikshaInput(
        dushya=DushyaAssessment(
            primary_dushyas=[DushyaDhatu.ASTHI, DushyaDhatu.MAJJA, DushyaDhatu.SHUKRA],
            chronicity_days=365
        ),
        desha=DeshaAssessment(bhumi=BhumiDesha.JANGALA, deha=DehaDesha.MARMA_ASTHI_SANDHI),
        bala=BalaAssessment(
            sahaja=GradingScale.AVARA,
            kalaja=GradingScale.AVARA,
            yuktikrita=GradingScale.AVARA
        ),
        kala_season="SHISHIRA",
        anala=AnalaAssessment(agni=AgniType.MANDAGNI),
        vayas_stage=VayasStage.VARDHAKYA,
        sattva=GradingScale.AVARA,
        satmya=GradingScale.AVARA,
        ahara_shakti=AharaShaktiAssessment(
            abhyavaharana=GradingScale.AVARA,
            jarana=GradingScale.AVARA
        )
    )

    rogi_bala, roga_bala, ratio, eligibility, rationale = evaluate_dashavidha_pariksha(exam)

    assert rogi_bala < 25.0, f"Expected low Rogi Bala, got {rogi_bala}"
    assert roga_bala > 75.0, f"Expected high Roga Bala, got {roga_bala}"
    assert ratio < 0.60, f"Expected ratio < 0.60, got {ratio}"
    assert eligibility == TherapeuticEligibility.BRIMHANA_SUPPORTIVE_ONLY
    assert "strictly contraindicated" in rationale


def test_moderate_vitality_shamana_indicated():
    """Verify that moderate host vitality and moderate disease burden qualifies for Shamana."""
    exam = DashavidhaParikshaInput(
        dushya=DushyaAssessment(primary_dushyas=[DushyaDhatu.RAKTA, DushyaDhatu.MAMSA], chronicity_days=60),
        desha=DeshaAssessment(bhumi=BhumiDesha.ANUPA, deha=DehaDesha.SHAKHA),
        bala=BalaAssessment(
            sahaja=GradingScale.MADHYAMA,
            kalaja=GradingScale.MADHYAMA,
            yuktikrita=GradingScale.MADHYAMA
        ),
        kala_season="GRISHMA",
        anala=AnalaAssessment(agni=AgniType.VISHAMAGNI),
        vayas_stage=VayasStage.MADHYAMA,
        sattva=GradingScale.MADHYAMA,
        satmya=GradingScale.MADHYAMA,
        ahara_shakti=AharaShaktiAssessment(
            abhyavaharana=GradingScale.MADHYAMA,
            jarana=GradingScale.MADHYAMA
        )
    )

    rogi_bala, roga_bala, ratio, eligibility, rationale = evaluate_dashavidha_pariksha(exam)

    assert 40.0 <= rogi_bala <= 75.0
    assert 35.0 <= roga_bala <= 70.0
    assert 0.80 <= ratio <= 1.50
    assert eligibility in [TherapeuticEligibility.SHAMANA_INDICATED, TherapeuticEligibility.SHODHANA_ELIGIBLE]
