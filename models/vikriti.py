"""Pydantic schemas for Dynamic Vikriti Divergence Analytics and VSI Scoring."""
from enum import Enum
from typing import Dict
from pydantic import BaseModel, Field, ConfigDict


class VikritiSeverityTier(str, Enum):
    """Clinical severity grading based on Vikriti Severity Index (VSI)."""
    SAMADOSHA = "SAMADOSHA"                  # VSI < 15: Homeostatic equilibrium
    ALPA_VIKRITI = "ALPA_VIKRITI"            # 15 <= VSI < 40: Mild; Ahara & Vihara guidance
    MADHYAMA_VIKRITI = "MADHYAMA_VIKRITI"    # 40 <= VSI < 75: Moderate; Shamana Aushadha indicated
    TIVRA_VIKRITI = "TIVRA_VIKRITI"          # VSI >= 75: Severe; Shodhana / Panchakarma mandated


class DoshicDeviationState(str, Enum):
    """Directional Doshic pathogenetic vector change."""
    VRIDDHI = "VRIDDHI"    # Quantitative / qualitative increase (> +0.05)
    KSHAYA = "KSHAYA"      # Quantitative / qualitative decrease (< -0.05)
    SAMA = "SAMA"          # Physiological normal deviation (-0.05 to +0.05)


class DoshicDeltaDetail(BaseModel):
    """Individual doshic component deviation analysis."""
    delta: float = Field(..., description="V_curr - P_base")
    state: DoshicDeviationState
    percentage_change: float


class DoshicDeltaOutput(BaseModel):
    """Composite 3D doshic deviation vector."""
    vata: DoshicDeltaDetail
    pitta: DoshicDeltaDetail
    kapha: DoshicDeltaDetail
    dominant_vitiation: str


class VikritiAssessmentInput(BaseModel):
    """Dynamic acute presentation symptoms across 24 standard parameters (0: None, 1: Mild, 2: Moderate, 3: Severe)."""
    symptoms: Dict[str, int] = Field(
        ...,
        description="Map of Symptom IDs ('VS01' to 'VS24') to severity integer [0, 1, 2, 3]"
    )


class VikritiAssessmentOutput(BaseModel):
    """Comprehensive mathematical output of the Vikriti divergence engine."""
    assessment_id: str
    patient_id: str
    hospital_id: str
    evaluated_by_arn: str
    prakriti_baseline: Dict[str, float]
    vikriti_current: Dict[str, float]
    kl_divergence: float
    mahalanobis_distance: float
    vsi_score: float = Field(..., ge=0.0, le=100.0)
    severity_tier: VikritiSeverityTier
    doshic_deltas: DoshicDeltaOutput
    clinical_recommendation: str
    timestamp: int
    model_config = ConfigDict(from_attributes=True)
