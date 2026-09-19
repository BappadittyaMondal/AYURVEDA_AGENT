"""Pydantic schemas for Dhatu Sarata Quantitative Tissue Vitality Index (7 Dhatus + Sattva)."""
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class SarataTier(str, Enum):
    """Classical three-fold tissue vitality gradation (Charaka Vimanasthana 8)."""
    PRAVARA = "PRAVARA"      # Superior vitality (OSI >= 75%)
    MADHYAMA = "MADHYAMA"    # Moderate vitality (50% <= OSI < 75%)
    AVARA = "AVARA"          # Inferior / deficient vitality (OSI < 50%)


class DhatuType(str, Enum):
    """The Ashta Sara Purusha bodily and psychological tissues."""
    RASA = "RASA"        # Plasma/lymph & Tvak Sara (dermal radiance, hydration)
    RAKTA = "RAKTA"      # Blood tissue (vascularity, lip/nail redness, brilliance)
    MAMSA = "MAMSA"      # Muscle tissue (muscular development, firmness, stability)
    MEDA = "MEDA"        # Adipose tissue (lubrication, voice timbre, unctuousness)
    ASTHI = "ASTHI"      # Skeletal tissue (bone density, teeth, stamina, longevity)
    MAJJA = "MAJJA"      # Bone marrow & nervous tissue (joint stability, intellect)
    SHUKRA = "SHUKRA"    # Reproductive & regenerative tissue (radiance, Ojas precursor)
    SATTVA = "SATTVA"    # Psychological vitality (fortitude, emotional stability)


class DhatuRating(BaseModel):
    """Clinical assessment rating for an individual tissue substrate."""
    dhatu: DhatuType
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized vitality rating (0.0=severely depleted to 1.0=optimal Pravara)")
    clinical_notes: Optional[str] = Field(default=None, description="Examiner observations")


class DhatuSarataInput(BaseModel):
    """Input payload providing ratings for all 8 tissue dimensions."""
    patient_id: str = Field(..., description="Target patient UUID")
    dhatu_ratings: List[DhatuRating] = Field(..., min_length=8, max_length=8, description="Ratings for all 8 tissues")


class DhatuRasayanaDirective(BaseModel):
    """Targeted tissue revitalization protocol."""
    dhatu: DhatuType
    vitality_tier: SarataTier
    vulnerability_risk: str
    indicated_rasayana_herbs: List[str]
    dietary_guidelines: List[str]


class DhatuSarataOutput(BaseModel):
    """Comprehensive tissue vitality profile, Overall Sarata Index, and Rasayana directives."""
    assessment_id: str
    patient_id: str
    hospital_id: str
    evaluator_arn: str
    overall_sarata_index: float
    sarata_tier: SarataTier
    dhatu_scores: Dict[str, float]
    vulnerable_dhatus: List[str]
    rasayana_directives: List[DhatuRasayanaDirective]
    timestamp: int
    model_config = ConfigDict(from_attributes=True)
