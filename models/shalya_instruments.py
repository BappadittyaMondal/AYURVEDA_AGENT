"""
Shalya Tantra Yantra-Shastra Microsurgical Instruments & Operative Suite Models
================================================================================
Defines schemas for:
1. The 101 Classical Yantras & 20 Shastras (Sushruta Samhita Sutrasthana Ch. 7 & 8)
2. Ashtavidha Shastra Karma (8 Classical Surgical Operations per Sushruta Sutra 25)
3. Yogya Sutriya Surgical Simulation Training & Competency Verification (Sushruta Sutra 9)
4. Kshara-Agni Karma Operative Safety Firewalls & Neutralization Protocols
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class InstrumentClass(str, Enum):
    YANTRA = "YANTRA"     # Blunt surgical instruments, forceps, specula, probes (101 types)
    SHASTRA = "SHASTRA"   # Sharp cutting instruments, lancets, scalpels, needles (20 types)


class YantraCategory(str, Enum):
    SVASTIKA = "SVASTIKA"       # Cruciform extraction forceps (24 types, 18 Angulas)
    SANDAMSHA = "SANDAMSHA"     # Grasping tweezers/pinchers (2 types, 16 Angulas)
    TALA = "TALA"               # Scoop/ear-pick instruments (2 types, 12 Angulas)
    NADI = "NADI"               # Tubular specula/cannulae (20 types, variable length)
    SHALAKA = "SHALAKA"         # Rods, probes, directors (28 types, variable length)
    UPAYANTRA = "UPAYANTRA"     # Accessory surgical appliances (25 types)
    SHASTRA = "SHASTRA"         # Sharp instruments group


class AshtavidhaKarma(str, Enum):
    CHHEDANA = "CHHEDANA"       # Excision of tissue/masses (Vriddhipatra, Mandalagra)
    BHEDANA = "BHEDANA"         # Incision / opening abscess (Vriddhipatra, Nakhashastra)
    LEKHANA = "LEKHANA"         # Scraping / curettage (Mandalagra, Karapatra)
    VYADHANA = "VYADHANA"       # Puncturing / venesection / paracentesis (Kutharika, Vrihimukha)
    ESHANA = "ESHANA"           # Probing / sinus exploration (Eshanika, Gandupada-Shalaka)
    AHARANA = "AHARANA"         # Extraction / retrieval of calculus/foreign bodies (Badisha, Svastika)
    VISRAVANA = "VISRAVANA"     # Drainage of pus/blood collections (Suchi, Kushapatra, Atimukha)
    SEEVANA = "SEEVANA"         # Suturing / wound approximation (Suchi / 4 needle types)


class ParasurgicalModality(str, Enum):
    NONE = "NONE"
    KSHARA_KARMA = "KSHARA_KARMA"   # Chemical alkaline cauterization (Pratisaraniya Kshara)
    AGNI_KARMA = "AGNI_KARMA"       # Thermal cauterization with metallic Shalaka / Pipali


class YogyaSimulationModel(str, Enum):
    PUSHPAPHALA = "PUSHPAPHALA"                     # Watermelon / ash gourd for Chhedana/Bhedana
    DRITHI_WATER_BAG = "DRITHI_WATER_BAG"           # Water/mud-filled bladder for Bhedana/Visravana
    LEATHER_WITH_HAIR = "LEATHER_WITH_HAIR"         # Tanned hide with fur for Lekhana scraping
    LOTUS_STALK_VEIN = "LOTUS_STALK_VEIN"           # Hollow lotus stem / animal jugular for Vyadhana
    BAMBOO_REED = "BAMBOO_REED"                     # Soft wood / tubular reed for Eshana probing
    JACKFRUIT_CORE = "JACKFRUIT_CORE"               # Panasa / jackfruit flesh for Aharana extraction
    BEESWAX_SLAB = "BEESWAX_SLAB"                   # Softened beeswax for Visravana drainage
    THICK_LINEN_LEATHER = "THICK_LINEN_LEATHER"     # Multi-layered linen/cloth for Seevana suturing


class SurgicalInstrumentProfile(BaseModel):
    """Catalog specification of a classical surgical instrument (Yantra or Shastra)."""
    instrument_code: str
    instrument_type: InstrumentClass
    sanskrit_name: str
    category_group: YantraCategory
    angula_dimension: float = Field(..., ge=0.5, le=30.0, description="Instrument dimension in Angulas")
    target_tissues: List[str]
    primary_action: str
    sterilization_protocol: str


class OperativeProcedureCreate(BaseModel):
    """Intra-operative log of an Ashtavidha surgical procedure with safety verification."""
    patient_id: str
    operative_karma: AshtavidhaKarma
    surgical_instruments_used: List[str] = Field(..., min_length=1, description="List of instrument codes used")
    anesthesia_or_sangyaharana: str
    parasurgical_modality: ParasurgicalModality = ParasurgicalModality.NONE
    has_amla_neutralizer_ready: bool = Field(default=True, description="Mandatory Amla Dravya (lemon/Kanji) on field for Kshara Karma")
    patient_has_active_bleeding_diathesis: bool = Field(default=False, description="Strict contraindication for Agni Karma")
    operative_notes: str
    surgeon_arn: str


class OperativeProcedureResponse(BaseModel):
    """Operative procedure audit verification and firewall clearance."""
    procedure_id: str
    patient_id: str
    hospital_id: str
    operative_karma: AshtavidhaKarma
    surgical_instruments_used: List[str]
    anesthesia_or_sangyaharana: str
    parasurgical_modality: ParasurgicalModality
    safety_firewall_cleared: bool
    firewall_violations: List[str]
    operative_notes: str
    surgeon_arn: str
    created_at: int


class YogyaAssessmentCreate(BaseModel):
    """Surgical simulation competency assessment per Sushruta Sutrasthana Ch. 9."""
    practitioner_arn: str
    operative_karma_tested: AshtavidhaKarma
    simulation_model_used: YogyaSimulationModel
    precision_score: float = Field(..., ge=0.0, le=100.0, description="Incidence, depth, and margin accuracy score")
    tissue_handling_score: float = Field(..., ge=0.0, le=100.0, description="Respect for tissue margins and instrument grip")
    examiner_arn: str


class YogyaAssessmentResponse(BaseModel):
    """Surgical competency certification on classical simulation models."""
    assessment_id: str
    practitioner_arn: str
    hospital_id: str
    operative_karma_tested: AshtavidhaKarma
    simulation_model_used: YogyaSimulationModel
    precision_score: float
    tissue_handling_score: float
    composite_score: float
    overall_competency_certified: bool
    certification_verdict: str
    examiner_arn: str
    created_at: int
