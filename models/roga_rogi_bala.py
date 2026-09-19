"""Pydantic schemas for Roga Rogi Bala Ganan Yantra (Bi-Directional Balance Engine)."""
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TherapeuticCategory(str, Enum):
    """Clinical therapeutic intensity classification based on bi-directional Bala balance."""
    TIKSHNA_SHODHANA = "TIKSHNA_SHODHANA"
    MADHYAMA_SHODHANA_OR_SHAMANA = "MADHYAMA_SHODHANA_OR_SHAMANA"
    MADHYAMA_SHAMANA = "MADHYAMA_SHAMANA"
    MRIDU_SHAMANA_BRIMHANA = "MRIDU_SHAMANA_BRIMHANA"
    CONTRAINDICATED_SHODHANA_EMERGENCY_BRIMHANA = "CONTRAINDICATED_SHODHANA_EMERGENCY_BRIMHANA"


class ShodhanaEligibilityStatus(str, Enum):
    """Panchakarma bio-purification eligibility firewall state."""
    FULL_ELIGIBILITY = "FULL_ELIGIBILITY"
    CONDITIONAL_ELIGIBILITY = "CONDITIONAL_ELIGIBILITY"
    STRICTLY_CONTRAINDICATED = "STRICTLY_CONTRAINDICATED"
    NOT_INDICATED = "NOT_INDICATED"


class RogiBalaInput(BaseModel):
    """Host physiological vitality parameters (Charaka Vimanasthana 8)."""
    sahaja_bala: float = Field(default=0.7, ge=0.0, le=1.0, description="Constitutional/genetic vitality")
    kalaja_bala: float = Field(default=0.7, ge=0.0, le=1.0, description="Seasonal and age-appropriate vitality (Visarga vs Adana)")
    yuktikrita_bala: float = Field(default=0.7, ge=0.0, le=1.0, description="Acquired vitality: exercise, diet, sleep")
    dhatu_sarata_osi: float = Field(default=70.0, ge=0.0, le=100.0, description="Overall Sarata Index (OSI)")
    sattva_score: float = Field(default=0.7, ge=0.0, le=1.0, description="Psychological fortitude (0=Avara, 1=Pravara)")
    agni_strength: float = Field(default=0.7, ge=0.0, le=1.0, description="Functional digestive capacity (0-1)")


class RogaBalaInput(BaseModel):
    """Disease pathogenicity and virulence parameters."""
    vikriti_vsi: float = Field(default=40.0, ge=0.0, le=100.0, description="Vikriti Severity Index (VSI)")
    srotas_involvement_osi: float = Field(default=30.0, ge=0.0, le=100.0, description="Overall Srotas Index")
    vulnerable_channels_count: int = Field(default=2, ge=0, le=14, description="Count of channels with Khavaigunya")
    kriya_kala_ppi: float = Field(default=3.5, ge=1.0, le=6.0, description="Pathological Progression Index (1-6)")
    ama_agi_score: float = Field(default=30.0, ge=0.0, le=100.0, description="Ama Grading Index")
    chronicity_months: float = Field(default=1.0, ge=0.0, le=240.0, description="Disease duration in months")


class RogaRogiBalaInput(BaseModel):
    """Combined clinical payload for bi-directional host vs disease equilibrium."""
    patient_id: str = Field(..., description="Target patient UUID")
    rogi_bala: RogiBalaInput
    roga_bala: RogaBalaInput


class TherapeuticGovernorDirective(BaseModel):
    """Actionable therapeutic intensity protocol and procedure safety constraints."""
    protocol_name: str
    intensity_level: str
    dosage_multiplier: float
    permissible_panchakarma_procedures: List[str]
    forbidden_procedures: List[str]
    clinical_rationale: str


class RogaRogiBalaOutput(BaseModel):
    """Complete bi-directional balance valuation, dosage scalar, and therapeutic governor directives."""
    assessment_id: str
    patient_id: str
    hospital_id: str
    evaluator_arn: str
    rogi_bala_score: float
    roga_bala_score: float
    bala_ratio: float
    bala_differential: float
    therapeutic_category: TherapeuticCategory
    dosage_scalar: float
    shodhana_eligibility_status: ShodhanaEligibilityStatus
    governor_directives: List[TherapeuticGovernorDirective]
    timestamp: int
    model_config = ConfigDict(from_attributes=True)
