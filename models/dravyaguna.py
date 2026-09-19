"""
Classical Herbology (Dravya Guna) & Phytochemical Models
======================================================
Defines Pydantic schemas for:
1. Classical Rasa-Panchaka (Rasa, Guna, Veerya, Vipaka, Prabhava, Karma)
2. Quantitative Doshic impact vector modeling
3. Modern botanical taxonomy and pharmacognosy
4. Validated bioactive phytochemical metabolite mapping
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Rasa(str, Enum):
    MADHURA = "MADHURA"    # Sweet
    AMLA = "AMLA"          # Sour
    LAVANA = "LAVANA"      # Salty
    KATU = "KATU"          # Pungent / Acrid
    TIKTA = "TIKTA"        # Bitter
    KASHAYA = "KASHAYA"    # Astringent


class Guna(str, Enum):
    GURU = "GURU"          # Heavy
    LAGHU = "LAGHU"        # Light
    SHEETA = "SHEETA"      # Cold
    USHNA = "USHNA"        # Hot
    SNIGDHA = "SNIGDHA"    # Unctuous / Oily
    RUKSHA = "RUKSHA"      # Dry / Rough
    MANDA = "MANDA"        # Dull / Slow
    TIKSHNA = "TIKSHNA"    # Sharp / Quick
    STHIRA = "STHIRA"      # Stable / Firm
    SARA = "SARA"          # Mobile / Fluid
    MRIDU = "MRIDU"        # Soft
    KATHINA = "KATHINA"    # Hard
    VISHADA = "VISHADA"    # Clear / Non-slimy
    PICCHILA = "PICCHILA"  # Slimy / Mucilaginous
    SHLAKSHNA = "SHLAKSHNA"# Smooth
    KHARA = "KHARA"        # Rough
    STHULA = "STHULA"      # Gross / Bulky
    SUKSHMA = "SUKSHMA"    # Subtle / Penetrating
    SANDRA = "SANDRA"      # Dense / Viscous
    DRAVA = "DRAVA"        # Liquid / Aqueous


class Veerya(str, Enum):
    USHNA = "USHNA"        # Thermogenic / Heating Potency
    SHEETA = "SHEETA"      # Refrigerant / Cooling Potency


class Vipaka(str, Enum):
    MADHURA = "MADHURA"    # Anabolic / Sweet post-digestive transformation
    AMLA = "AMLA"          # Acidic / Sour post-digestive transformation
    KATU = "KATU"          # Catabolic / Pungent post-digestive transformation


class DoshicEffect(str, Enum):
    SHAMANA = "SHAMANA"    # Pacifying / Alleviating
    KOPANA = "KOPANA"      # Aggravating / Provoking
    SAMA = "SAMA"          # Neutral / Balanced


class DoshicKarma(BaseModel):
    """Classical biological impact on the three governing Doshas."""
    vata: DoshicEffect
    pitta: DoshicEffect
    kapha: DoshicEffect


class PhytochemicalBioactive(BaseModel):
    """Validated molecular phytochemical constituent with action."""
    compound_name: str
    chemical_class: str
    pharmacological_action: str


class HerbTherapeuticDosage(BaseModel):
    """Standard classical posology."""
    form: str = Field(..., description="Churna, Kwatha, Svarasa, Taila, etc.")
    min_dose_g: float
    max_dose_g: float
    anupana: Optional[str] = Field(default=None, description="Carrier vehicle: warm milk, honey, warm water, etc.")


class HerbProfile(BaseModel):
    """Master classical Dravya Guna and phytochemical profile."""
    herb_id: str
    sanskrit_name: str
    botanical_name: str
    botanical_family: str
    classical_synonyms: List[str]
    rasa: List[Rasa]
    guna: List[Guna]
    veerya: Veerya
    vipaka: Vipaka
    prabhava: Optional[str] = Field(default=None, description="Specific idiosyncratic non-linear action")
    doshic_karma: DoshicKarma
    therapeutics_karma: List[str] = Field(..., description="Deepana, Pachana, Rasayana, Medhya, etc.")
    phytochemicals: List[PhytochemicalBioactive]
    parts_used: List[str]
    dosages: List[HerbTherapeuticDosage]
    contraindications: List[str]


class DoshicModulationScore(BaseModel):
    """Calculated quantitative net impact on the patient's Doshic axis."""
    herb_id: str
    herb_name: str
    vata_delta: float = Field(..., ge=-1.0, le=1.0, description="-1.0 (strong pacification) to +1.0 (strong provocation)")
    pitta_delta: float = Field(..., ge=-1.0, le=1.0)
    kapha_delta: float = Field(..., ge=-1.0, le=1.0)
    rationale: str
