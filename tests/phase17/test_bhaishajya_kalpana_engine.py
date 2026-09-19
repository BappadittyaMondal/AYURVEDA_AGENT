"""
Unit Tests for Classical Formulation Architecture (Bhaishajya Kalpana) & Polyherbal Synergy Engine.
"""

import tempfile
from pathlib import Path
import sqlite3
import pytest
from core.database import init_database
from core.bhaishajya_kalpana import (
    SEED_ANUPANA_REGISTRY,
    SEED_FORMULATIONS_REGISTRY,
    evaluate_polyherbal_synergy,
    get_all_anupana,
    get_formulation_by_id,
    search_formulations,
    seed_formulations_and_anupana,
)
from models.bhaishajya_kalpana import (
    FormulationIngredient,
    IngredientRole,
    KalpanaForm,
    SafetyWarningLevel,
    SynergyEvaluationRequest,
)


def test_registries_completeness():
    """Verify that all 15 classical formulations and 8 Anupana vehicles are populated."""
    assert len(SEED_FORMULATIONS_REGISTRY) >= 15
    assert len(SEED_ANUPANA_REGISTRY) >= 8

    # Formulations validation
    for form in SEED_FORMULATIONS_REGISTRY:
        assert form.formulation_id.startswith("FORM-")
        assert len(form.sanskrit_name) > 0
        assert isinstance(form.kalpana_form, KalpanaForm)
        assert len(form.ingredients) >= 1
        assert "vata_delta" in form.doshic_modulation
        assert "pitta_delta" in form.doshic_modulation
        assert "kapha_delta" in form.doshic_modulation
        assert len(form.cardinal_indications) >= 1
        assert len(form.standard_anupana) > 0
        assert form.dosage_standard.min_dose_g > 0

    # Anupana validation
    for anupana in SEED_ANUPANA_REGISTRY:
        assert anupana.anupana_id.startswith("ANUPANA-")
        assert len(anupana.sanskrit_name) > 0
        assert len(anupana.carrier_properties) >= 1
        assert len(anupana.contraindications) >= 1


def test_classical_formulation_pharmacodynamics_accuracy():
    """Verify formulation recipes and composite Doshic actions."""
    form_map = {f.formulation_id: f for f in SEED_FORMULATIONS_REGISTRY}

    # 1. Trikatu Churna
    trikatu = form_map["FORM-TRIKATU"]
    assert trikatu.kalpana_form == KalpanaForm.CHURNA
    assert len(trikatu.ingredients) == 3
    assert trikatu.composite_veerya == "USHNA"
    assert trikatu.doshic_modulation["kapha_delta"] < -0.60
    assert trikatu.doshic_modulation["pitta_delta"] > 0.30

    # 2. Triphala Churna
    triphala = form_map["FORM-TRIPHALA"]
    assert triphala.kalpana_form == KalpanaForm.CHURNA
    assert triphala.composite_vipaka == "MADHURA"
    assert triphala.doshic_modulation["vata_delta"] < 0
    assert triphala.doshic_modulation["pitta_delta"] < 0
    assert triphala.doshic_modulation["kapha_delta"] < 0

    # 3. Chitrakadi Vati
    chitrakadi = form_map["FORM-CHITRAKADI-VATI"]
    assert chitrakadi.kalpana_form == KalpanaForm.VATI
    assert chitrakadi.standard_anupana == "ANUPANA-TAKRA"

    # 4. Shatavari Ghrita
    ghrita = form_map["FORM-SHATAVARI-GHRITA"]
    assert ghrita.kalpana_form == KalpanaForm.GHRITA
    assert ghrita.composite_veerya == "SHEETA"
    assert ghrita.doshic_modulation["pitta_delta"] < -0.70


def test_viruddha_ahara_honey_ghee_safety_firewall():
    """Verify strict prohibition of equal 1:1 ratio of Honey and Ghee."""
    ingredients = [
        FormulationIngredient(herb_id="HERB-ASHWAGANDHA", herb_name="Ashwagandha", proportion_parts=2.0)
    ]

    # Equal ratio: 5g Honey and 5g Ghee -> MUST TRIGGER CRITICAL WARNING
    equal_req = SynergyEvaluationRequest(
        ingredients=ingredients,
        honey_ratio_parts=5.0,
        ghee_ratio_parts=5.0,
        is_heated_anupana=False
    )
    equal_resp = evaluate_polyherbal_synergy(equal_req)
    warning_codes = [w.code for w in equal_resp.safety_warnings]
    assert "VIRUDDHA_SAMYOGA_MADHU_GHRITA" in warning_codes

    # Unequal ratio: 10g Honey and 2g Ghee -> Permitted, NO CRITICAL WARNING
    unequal_req = SynergyEvaluationRequest(
        ingredients=ingredients,
        honey_ratio_parts=10.0,
        ghee_ratio_parts=2.0,
        is_heated_anupana=False
    )
    unequal_resp = evaluate_polyherbal_synergy(unequal_req)
    unequal_codes = [w.code for w in unequal_resp.safety_warnings]
    assert "VIRUDDHA_SAMYOGA_MADHU_GHRITA" not in unequal_codes


def test_viruddha_ahara_heated_honey_safety_firewall():
    """Verify prohibition against heating honey."""
    ingredients = [
        FormulationIngredient(herb_id="HERB-TULSI", herb_name="Tulsi", proportion_parts=1.0)
    ]

    # Heated honey request
    heated_req = SynergyEvaluationRequest(
        ingredients=ingredients,
        proposed_anupana_id="ANUPANA-MADHU",
        is_heated_anupana=True
    )
    resp = evaluate_polyherbal_synergy(heated_req)
    warning_codes = [w.code for w in resp.safety_warnings]
    assert "VIRUDDHA_USHNA_MADHU" in warning_codes
    assert any(w.level == SafetyWarningLevel.CRITICAL_CONTRAINDICATION for w in resp.safety_warnings)


def test_polyherbal_synergy_vector_calculus():
    """Verify weighted composite Doshic impact vector calculation across custom ingredients."""
    # Combine Ashwagandha (Vata/Kapha pacifying) + Shunthi (Deepana/Vata-Kapha pacifying) + Haridra
    req = SynergyEvaluationRequest(
        ingredients=[
            FormulationIngredient(herb_id="HERB-ASHWAGANDHA", herb_name="Ashwagandha", proportion_parts=3.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-SHUNTHI", herb_name="Shunthi", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
            FormulationIngredient(herb_id="HERB-HARIDRA", herb_name="Haridra", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
        ],
        proposed_anupana_id="ANUPANA-KSHEERA"
    )

    resp = evaluate_polyherbal_synergy(req)
    vec = resp.aggregate_doshic_vector
    assert vec["vata_delta"] < -0.50
    assert vec["kapha_delta"] < -0.50
    assert resp.composite_veerya == "USHNA"
    assert len(resp.synergistic_karma) >= 3
    assert "Rasayana" in resp.synergistic_karma
