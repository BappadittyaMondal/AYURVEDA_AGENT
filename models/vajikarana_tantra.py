"""
Vajikarana Tantra, Shukra Dushti & Reproductive Eugenics Models
===============================================================
Defines schemas for:
1. The 8 Classical Shukra Dushtis (Ashta Shukra Dushtis per Charaka & Sushruta)
2. WHO 6th Edition Semen Analysis Dual-Mapping Diagnostic Engine
3. Classical Klaibya (Male Sexual Dysfunction) 4-Fold Stratification
4. Vajikarana Pharmacodynamic Dynamics (Shukra-Janana, Rechaka, Stambhana, Shodhaka)
5. Pre-Vajikarana Shodhana Safety Firewall & Eugenics Protocols
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ShukraDushtiType(str, Enum):
    VATIKA = "VATIKA"                      # Frothy, thin, rough, painful emission
    PAITTIKA = "PAITTIKA"                  # Yellowish/bluish, burning, fetid, acidic
    KAPHAJA = "KAPHAJA"                    # Dense, hyperviscous, delayed liquefaction, sinking
    RAKTAJA = "RAKTAJA"                    # Hematospermia, blood-tinged, failure of conception
    KUNAPA_GANDHI = "KUNAPA_GANDHI"        # Cadaveric / putrid necrotic odor
    GRANTHI_BHUTA = "GRANTHI_BHUTA"        # Clotted, clumped, obstructive asthenospermia
    PUTI_PUYA = "PUTI_PUYA"                # Purulent, leukocytospermia, accessory gland infection
    KSHINA = "KSHINA"                      # Severe oligospermia, count and volume depletion
    SHUDDHA_SHUKRA = "SHUDDHA_SHUKRA"      # Crystal-clear, unctuous, honey-sweet, fertile semen


class KlaibyaType(str, Enum):
    BEEJOPAGHATAJA = "BEEJOPAGHATAJA"      # Genetic / congenital / primary testicular failure
    DHVAJABHANGAJA = "DHVAJABHANGAJA"      # Neuro-vascular, local trauma, excessive coital strain
    JARASAMBHAVA = "JARASAMBHAVA"          # Age-related androgen decline / senile andropause
    SHUKRAKSHAYAJA = "SHUKRAKSHAYAJA"      # Depletion-induced secondary to extreme emaciation/loss
    MANASIKA = "MANASIKA"                  # Psychogenic performance anxiety, fear, and sorrow


class VajikaranaActionClass(str, Enum):
    SHUKRA_JANANA = "SHUKRA_JANANA"                     # Stimulates de novo spermatogenesis and volume
    SHUKRA_RECHAKA = "SHUKRA_RECHAKA"                   # Stimulates ejaculatory reflex and emission
    SHUKRA_JANANA_PRAVARTAKA = "SHUKRA_JANANA_PRAVARTAKA"# Both generates sperm and promotes expulsion
    SHUKRA_STAMBHANA = "SHUKRA_STAMBHANA"               # Enhances latency / delays premature ejaculation
    SHUKRA_SHODHAKA = "SHUKRA_SHODHAKA"                 # Purifies seminal Doshic Dushti and infections


class ViscosityGrade(str, Enum):
    NORMAL = "NORMAL"                                   # Normal thread length < 2 cm
    MODERATE_INCREASED = "MODERATE_INCREASED"           # Thread length 2 - 4 cm
    HIGH_PICCHILA = "HIGH_PICCHILA"                     # Thread length > 4 cm (Hyperviscous)


class ShukraDushtiProfile(BaseModel):
    """Classical specification of a seminal pathology."""
    dushti_code: str
    sanskrit_name: str
    doshic_etiology: str
    classical_characteristics: List[str]
    who_semen_correlate: str
    indicated_shodhana_protocol: str
    classical_herbal_remedies: List[str]


class SemenAnalysisCreate(BaseModel):
    """Clinical semen evaluation request mapped against WHO 6th edition reference limits."""
    patient_id: str
    volume_ml: float = Field(..., ge=0.1, le=15.0, description="Ejaculate volume in mL (WHO norm >= 1.5 mL)")
    ph_level: float = Field(..., ge=6.0, le=9.5, description="Semen pH (WHO norm 7.2 - 8.0)")
    liquefaction_time_min: int = Field(..., ge=5, le=180, description="Liquefaction time in minutes (WHO norm < 60 min)")
    viscosity_grade: ViscosityGrade
    sperm_concentration_million_ml: float = Field(..., ge=0.0, le=500.0, description="Sperm count in millions/mL (WHO norm >= 15 M/mL)")
    total_motility_percent: float = Field(..., ge=0.0, le=100.0, description="Total motility PR + NP (WHO norm >= 42%)")
    progressive_motility_percent: float = Field(..., ge=0.0, le=100.0, description="Progressive motility PR (WHO norm >= 30%)")
    normal_morphology_percent: float = Field(..., ge=0.0, le=100.0, description="Kruger strict normal morphology (WHO norm >= 4%)")
    vitality_percent: float = Field(..., ge=0.0, le=100.0, description="Eosin-nigrosin sperm viability (WHO norm >= 54%)")
    pus_cells_per_hpf: int = Field(default=0, ge=0, le=100, description="Leukocytes per HPF (Norm < 5/HPF or < 1M/mL)")
    erythrocytes_present: bool = Field(default=False, description="Presence of RBCs indicating hematospermia")
    practitioner_arn: str


class SemenAnalysisResponse(BaseModel):
    """Comprehensive diagnostic verdict integrating WHO 6th Ed. and Ayurvedic Ashta Shukra Dushtis."""
    analysis_id: str
    patient_id: str
    hospital_id: str
    volume_ml: float
    ph_level: float
    liquefaction_time_min: int
    viscosity_grade: ViscosityGrade
    sperm_concentration_million_ml: float
    total_motility_percent: float
    progressive_motility_percent: float
    normal_morphology_percent: float
    vitality_percent: float
    pus_cells_per_hpf: int
    erythrocytes_present: bool
    primary_shukra_dushti: ShukraDushtiType
    secondary_shukra_dushti: Optional[ShukraDushtiType] = None
    shukra_shuddhi_score: float = Field(..., ge=0.0, le=100.0)
    who_diagnostic_interpretation: List[str]
    fertility_prognosis: str
    practitioner_arn: str
    created_at: int


class VajikaranaPrescriptionCreate(BaseModel):
    """Clinical request for personalized Vajikarana regimen with safety gating."""
    patient_id: str
    klaibya_type: KlaibyaType
    target_action_class: VajikaranaActionClass
    pre_shodhana_completed: bool = Field(..., description="Prior Panchakarma or Kostha Shodhana completed")
    has_active_ama: bool = Field(default=False, description="Active Ama symptoms (coated tongue, lethargy, heaviness)")
    partner_conception_intent: bool = True
    practitioner_arn: str


class VajikaranaPrescriptionResponse(BaseModel):
    """Targeted Vajikarana prescription, dietary pathya, and safety firewall clearance."""
    protocol_id: str
    patient_id: str
    hospital_id: str
    klaibya_type: KlaibyaType
    shukra_action_class: VajikaranaActionClass
    pre_shodhana_verified: bool
    prescribed_classical_formulations: List[str]
    dietary_lifestyle_pathya: List[str]
    psychosexual_counseling_notes: str
    safety_firewall_cleared: bool
    contraindication_warnings: List[str]
    practitioner_arn: str
    created_at: int
