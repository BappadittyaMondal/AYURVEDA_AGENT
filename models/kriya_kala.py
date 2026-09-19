"""Pydantic schemas for Shat Kriya Kala Pathological Stage Tracker (6 Stages)."""
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class KriyaKalaStage(str, Enum):
    """The six classical stages of pathogenesis from Sushruta Samhita Sutrasthana 21."""
    SANCHAYA = "SANCHAYA"                  # Stage 1: Accumulation in native anatomical seats
    PRAKOPA = "PRAKOPA"                    # Stage 2: Excitation / provocation / liquefaction
    PRASARA = "PRASARA"                    # Stage 3: Systemic dissemination / overflow
    STHANASAMSHRAYA = "STHANASAMSHRAYA"    # Stage 4: Localization at Khavaigunya (Prodrome / Purvaroopa)
    VYAKTI = "VYAKTI"                      # Stage 5: Full clinical disease manifestation (Roopa)
    BHEDA = "BHEDA"                        # Stage 6: Complications / ulceration / chronicity (Upadrava)


class CurabilityPrognosis(str, Enum):
    """Classical prognosis according to stage of intervention."""
    SUKHASADHYA = "SUKHASADHYA"          # Easily curable
    KRICHRASADHYA = "KRICHRASADHYA"      # Curable with intensive effort
    YAPYA = "YAPYA"                      # Manageable / palliative chronic maintenance
    ASADHYA = "ASADHYA"                  # Incurable / irreversible tissue pathology


class StageObservationInput(BaseModel):
    """Semi-quantitative clinical observation scores (0-3 ordinal) and qualitative findings."""
    sanchaya_features: int = Field(default=0, ge=0, le=3, description="Aversion to like qualities, mild fullness")
    prakopa_features: int = Field(default=0, ge=0, le=3, description="Acid eructation, thirst, nausea, colicky pain")
    prasara_features: int = Field(default=0, ge=0, le=3, description="Systemic wandering aches, borborygmi, feverish heat")
    sthanasamshraya_features: int = Field(default=0, ge=0, le=3, description="Prodromal symptoms (Purvaroopa), organ localization")
    vyakti_features: int = Field(default=0, ge=0, le=3, description="Full disease signs & symptoms (Roopa)")
    bheda_features: int = Field(default=0, ge=0, le=3, description="Tissue breakdown, suppuration, ulceration, Upadrava")
    prodromal_symptoms: List[str] = Field(default_factory=list, description="Explicit prodromal indicators")
    manifest_symptoms: List[str] = Field(default_factory=list, description="Explicit manifest disease signs")
    complications: List[str] = Field(default_factory=list, description="Secondary complications / chronicity signs")


class KriyaKalaInput(BaseModel):
    """Diagnostic input payload for Shat Kriya Kala staging."""
    patient_id: str = Field(..., description="Target patient UUID")
    observations: StageObservationInput


class KriyaKalaOutput(BaseModel):
    """Complete Shat Kriya Kala stage attribution, progression index, and therapeutic window."""
    assessment_id: str
    patient_id: str
    hospital_id: str
    evaluator_arn: str
    current_stage: KriyaKalaStage
    pathological_progression_index: float
    stage_probabilities: Dict[str, float]
    prodromal_symptoms: List[str]
    manifest_symptoms: List[str]
    complications: List[str]
    reversibility_percentage: float
    curability_prognosis: CurabilityPrognosis
    therapeutic_window_directive: str
    timestamp: int
    model_config = ConfigDict(from_attributes=True)
