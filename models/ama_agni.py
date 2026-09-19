"""Pydantic schemas for Quantitative Ama Grading Index (AGI) & Agni Vector Gating Engine."""
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class AgniType(str, Enum):
    """Classical quadruplicate functional digestive state (Charaka Chikitsasthana 15)."""
    SAMAGNI = "SAMAGNI"          # Equilibrium / homeostatic digestion
    VISHAMAGNI = "VISHAMAGNI"    # Irregular / erratic digestion (Vata)
    TIKSHNAGNI = "TIKSHNAGNI"    # Hyperactive / intense burning digestion (Pitta)
    MANDAGNI = "MANDAGNI"        # Sluggish / hypoactive digestion (Kapha)


class AmaGrade(str, Enum):
    """Clinical toxicity and metabolic endotoxin burden stratification."""
    NIRAMA = "NIRAMA"              # AGI < 20: No systemic Ama
    ALPA_AMA = "ALPA_AMA"          # 20 <= AGI < 45: Mild localized endotoxin
    MADHYAMA_AMA = "MADHYAMA_AMA"  # 45 <= AGI < 70: Moderate systemic endotoxin
    GURU_AMA = "GURU_AMA"          # AGI >= 70: Severe Amavisha / critical toxicity


class GatingStatus(str, Enum):
    """Panchakarma clinical safety firewall gating states."""
    CLEARED_FOR_SHODHANA = "CLEARED_FOR_SHODHANA"
    GATED_FOR_DEEPANA_PACHANA = "GATED_FOR_DEEPANA_PACHANA"
    GATED_EMERGENCY_LANGHANA = "GATED_EMERGENCY_LANGHANA"
    GATED_TIKSHNAGNI_PACIFICATION = "GATED_TIKSHNAGNI_PACIFICATION"


class AmaSymptomsInput(BaseModel):
    """10 Cardinal Classical Ama Lakshanas scored on 0-3 ordinal scale (0=None, 1=Mild, 2=Mod, 3=Severe)."""
    srotorodha: int = Field(default=0, ge=0, le=3, description="Channel obstruction / microcirculatory block")
    balabhramsha: int = Field(default=0, ge=0, le=3, description="Profound fatigue / loss of vitality")
    gaurava: int = Field(default=0, ge=0, le=3, description="Bodily heaviness / lethargy")
    anilamudhata: int = Field(default=0, ge=0, le=3, description="Obstructed / erratic downward peristalsis")
    alasya: int = Field(default=0, ge=0, le=3, description="Psychomotor slowing / inertia")
    apakti: int = Field(default=0, ge=0, le=3, description="Indigestion / dyspepsia")
    nishthiva: int = Field(default=0, ge=0, le=3, description="Excessive oral salivation / clamminess")
    malasanga: int = Field(default=0, ge=0, le=3, description="Retention of metabolic waste / constipation")
    aruchi: int = Field(default=0, ge=0, le=3, description="Anorexia / altered taste perception")
    klama: int = Field(default=0, ge=0, le=3, description="Exhaustion without muscular exertion")


class AgniParametersInput(BaseModel):
    """Physiological functional digestion telemetry and clinical indices."""
    appetite_regularity: float = Field(default=1.0, ge=0.0, le=1.0, description="1.0=predictable, 0.0=chaotic")
    digestion_speed_hours: float = Field(default=4.0, ge=1.0, le=12.0, description="Mean duration to digest meal")
    post_prandial_heaviness: float = Field(default=0.0, ge=0.0, le=1.0, description="Heaviness after food (0-1)")
    burning_sensation: float = Field(default=0.0, ge=0.0, le=1.0, description="Epigastric pyrosis / heat (0-1)")
    abdominal_distension: float = Field(default=0.0, ge=0.0, le=1.0, description="Tympanites / flatulence (0-1)")


class AmaAgniEvaluationRequest(BaseModel):
    """Comprehensive input for Ama Grading Index and Agni Vector analysis."""
    patient_id: str = Field(..., description="Target patient UUID")
    symptoms: AmaSymptomsInput
    agni_params: AgniParametersInput


class TherapeuticDirective(BaseModel):
    """Standardized Ayurvedic clinical pharmacology and dietary guidance."""
    phase: str
    action_type: str
    herbal_recommendations: List[str]
    dietary_guidelines: List[str]
    contraindications: List[str]


class AmaAgniOutput(BaseModel):
    """Complete AGI score, Agni Vector, Panchakarma gating flag, and therapeutic directives."""
    assessment_id: str
    patient_id: str
    hospital_id: str
    evaluator_arn: str
    agi_score: float
    ama_grade: AmaGrade
    agni_type: AgniType
    agni_vector: Dict[str, float]
    shodhana_permitted: bool
    gating_status: GatingStatus
    therapeutic_directives: List[TherapeuticDirective]
    timestamp: int
    model_config = ConfigDict(from_attributes=True)
