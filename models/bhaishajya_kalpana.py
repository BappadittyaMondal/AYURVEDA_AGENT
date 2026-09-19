"""
Classical Formulation Architecture (Bhaishajya Kalpana) & Polyherbal Synergy Models
=================================================================================
Defines Pydantic schemas for:
1. Panchavidha Kashaya Kalpana & Secondary Dosage Forms
2. Recipe formulation ingredients with botanical & classical mappings
3. Anupana Carrier & Vehicle Matrix
4. Polyherbal synergy vector calculus & Viruddha safety firewalls
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class KalpanaForm(str, Enum):
    # Primary Panchavidha Kashaya Kalpanas
    SVARASA = "SVARASA"              # Fresh expressed juice
    KALKA = "KALKA"                  # Paste / bolus
    KWATHA = "KWATHA"                # Decoction / boiling reduction (1/4th)
    HIMA = "HIMA"                    # Cold infusion (soaked overnight)
    PHANTA = "PHANTA"                # Hot water infusion

    # Secondary & Derived Forms
    CHURNA = "CHURNA"                # Micronized herbal powder
    VATI = "VATI"                    # Compressed tablet / pill
    AVALEHA = "AVALEHA"              # Electuary / medicated herbal jam
    GHRITA = "GHRITA"                # Medicated clarified butter
    TAILA = "TAILA"                  # Medicated sesame or botanical oil
    ASAVA_ARISHTA = "ASAVA_ARISHTA"  # Naturally fermented hydro-alcoholic beverage
    GUGGULU = "GUGGULU"              # Resin-bound therapeutic tablet


class SnehaPakaStage(str, Enum):
    MRIDU = "MRIDU"                  # Mild paka (for Nasya)
    MADHYAMA = "MADHYAMA"            # Moderate standard paka (for Pana and Basti)
    KHARA = "KHARA"                  # Hard paka (for Abhyanga)
    DAGDHA = "DAGDHA"                # Overcooked / charred (unusable)


class IngredientRole(str, Enum):
    MUKHYA_DRAVYA = "MUKHYA_DRAVYA"      # Chief active therapeutic agent
    SAHAKARI_DRAVYA = "SAHAKARI_DRAVYA"  # Synergistic / balancing agent
    PRAKSHEPA_DRAVYA = "PRAKSHEPA_DRAVYA"# Aromatic catalyst / bioavailability enhancer
    SNEHA_DRAVYA = "SNEHA_DRAVYA"        # Lipid solvent / base medium
    DRAVA_DRAVYA = "DRAVA_DRAVYA"        # Liquid boiling medium


class SafetyWarningLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL_CONTRAINDICATION = "CRITICAL_CONTRAINDICATION"


class FormulationIngredient(BaseModel):
    """Component ingredient within a compound formulation recipe."""
    herb_id: str = Field(..., description="Herb ID from Dravya Guna registry")
    herb_name: str = Field(..., description="Classical Sanskrit name")
    proportion_parts: float = Field(..., gt=0.0, description="Relative quantity parts")
    ingredient_role: IngredientRole = Field(default=IngredientRole.MUKHYA_DRAVYA)


class FormulationDosageStandard(BaseModel):
    """Classical posology guidelines for formulation."""
    min_dose_g: float
    max_dose_g: float
    recommended_timing: str
    instructions: str


class ClassicalFormulation(BaseModel):
    """Master classical compound formulation profile."""
    formulation_id: str
    sanskrit_name: str
    kalpana_form: KalpanaForm
    classical_reference: str
    ingredients: List[FormulationIngredient]
    composite_veerya: str
    composite_vipaka: str
    doshic_modulation: Dict[str, float] = Field(..., description="V-P-K deltas: -1.0 to +1.0")
    cardinal_indications: List[str]
    standard_anupana: str
    dosage_standard: FormulationDosageStandard


class AnupanaProfile(BaseModel):
    """Classical vehicle / carrier profile for bio-enhancement."""
    anupana_id: str
    sanskrit_name: str
    english_name: str
    doshic_affinity: str
    carrier_properties: List[str]
    contraindications: List[str]


class SafetyWarning(BaseModel):
    code: str
    level: SafetyWarningLevel
    message: str


class SynergyEvaluationRequest(BaseModel):
    """Payload to evaluate a custom polyherbal recipe and check carrier compatibility."""
    ingredients: List[FormulationIngredient] = Field(..., min_length=1)
    proposed_anupana_id: Optional[str] = None
    honey_ratio_parts: Optional[float] = Field(default=0.0, ge=0.0)
    ghee_ratio_parts: Optional[float] = Field(default=0.0, ge=0.0)
    is_heated_anupana: Optional[bool] = Field(default=False)


class SynergyEvaluationResponse(BaseModel):
    """Polyherbal synergy evaluation result with composite pharmacodynamics and warnings."""
    aggregate_doshic_vector: Dict[str, float] = Field(..., description="Computed composite V-P-K impact")
    composite_veerya: str
    composite_vipaka: str
    synergistic_karma: List[str]
    safety_warnings: List[SafetyWarning]
    rationale: str
