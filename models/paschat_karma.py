"""
Phase 34: Paschat Karma, Samsarjana Krama & Longitudinal EHR Persistence Models
================================================================================
Defines schemas for:
1. Paschat Karma rehabilitation episodes following Panchakarma bio-purification
2. Graduated Samsarjana Krama dietary recovery ladder (Peya to Normal Diet)
3. Annakala-by-Annakala meal intake logging and caloric/digestibility staircases
4. Real-time Agni kindling trajectory modeling and digestive complication alerts
5. Ashta Mahadosha / Parihara Vishaya classical prohibition auditing
6. Rasayana & Vajikarana clinical readiness evaluation
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from models.panchakarma import ShuddhiGrade


class AnnakalaMealTime(str, Enum):
    """Meal time point within the diurnal digestive cycle."""
    PRATAH_KALPA = "PRATAH_KALPA"   # Morning / Mid-day Annakala (Pitta circadian peak)
    SAYAM_KALPA = "SAYAM_KALPA"     # Evening Annakala (Before sunset)


class DietaryLadderForm(str, Enum):
    """Classical graduated dietary ladder preparation forms."""
    PEYA = "PEYA"                   # Thin rice gruel (1 part rice : 14 parts water, liquid only)
    VILEPI = "VILEPI"               # Thick semi-solid rice gruel (1 part rice : 4 parts water)
    AKRITA_YUSHA = "AKRITA_YUSHA"   # Green gram soup without salt, ghee, or spices
    KRITA_YUSHA = "KRITA_YUSHA"     # Green gram soup seasoned with rock salt, cumin, and cow's ghee
    MAMSA_RASA = "MAMSA_RASA"       # Light Jangala meat soup or nutritious mung-rice mash
    NORMAL_DIET = "NORMAL_DIET"     # Balanced solid meal attuned to Prakriti and Agni


class AgniRestorationStatus(str, Enum):
    """Pathophysiological metabolic state during post-purification recovery."""
    MANDAGNI_POST_SHODHANA = "MANDAGNI_POST_SHODHANA"  # Depleted post-cleansing digestive fire
    GRADUAL_KINDLING = "GRADUAL_KINDLING"              # Active progressive metabolic stimulation
    SAMAGNI_RESTORED = "SAMAGNI_RESTORED"              # Fully restored, balanced digestive capacity


class DigestionTolerance(str, Enum):
    """Clinical assessment of digestion tolerance following an Annakala meal."""
    SUKHA_PAKA = "SUKHA_PAKA"         # Ideal, easy digestion without discomfort
    VIDAHI = "VIDAHI"                 # Heartburn, acid regurgitation, burning distress
    VISHTAMBHI = "VISHTAMBHI"         # Tympanites, abdominal distension, retention of flatus
    AJIRNA = "AJIRNA"                 # Heavy undigested fullness, nausea, malaise


class PariharaProhibition(str, Enum):
    """Classical Ashta Mahadosha (eight cardinal post-purification prohibitions)."""
    ATIBHASHANA = "ATIBHASHANA"               # Excessive speech / strain on vocal cords
    UCHHAIRBHASHANA = "UCHHAIRBHASHANA"       # Loud shouting
    RATHA_KSHOBHA = "RATHA_KSHOBHA"           # Vehicle travel, vibration, rough roads
    ATICHANKRAMANA = "ATICHANKRAMANA"         # Excessive walking or physical exertion
    ATYASANA = "ATYASANA"                     # Prolonged sitting on hard surfaces
    AJEERNA_ADHYASHANA = "AJEERNA_ADHYASHANA" # Eating when earlier food is undigested
    ASATMYA_BHOJANA = "ASATMYA_BHOJANA"       # Incompatible, unaccustomed, or cold foods
    DIVASVAPNA_MAITHUNA = "DIVASVAPNA_MAITHUNA" # Daytime sleeping and sexual indulgence


class EpisodeStatus(str, Enum):
    """Lifecycle status of the Paschat Karma rehabilitation episode."""
    ACTIVE = "ACTIVE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


# -------------------------------------------------------------------------
# Meal & Schedule Schemas
# -------------------------------------------------------------------------

class SamsarjanaMealStep(BaseModel):
    """Single Annakala step within the graduated dietary ladder."""
    day_number: int = Field(..., ge=1, description="Day of recovery (1 to 7)")
    annakala_number: int = Field(..., ge=1, description="Sequential Annakala index (1 to 14)")
    meal_time_type: AnnakalaMealTime = Field(..., description="Morning or Evening meal")
    prescribed_diet_form: DietaryLadderForm = Field(..., description="Form of food")
    preparation_details: str = Field(..., description="Culinary instructions and ingredients")
    caloric_estimate_kcal: float = Field(..., ge=50.0, description="Estimated energetic content in kcal")
    digestibility_index: float = Field(..., ge=0.0, le=1.0, description="Digestibility scale: 0.1 (liquid) to 1.0 (solid)")


class PaschatKarmaEpisodeCreate(BaseModel):
    """Initiate a post-Panchakarma rehabilitation episode."""
    patient_id: str = Field(..., description="Unique Patient Identifier")
    hospital_id: str = Field(..., description="Hospital Organization ID")
    plan_id: str = Field(..., description="Associated Panchakarma Plan Identifier")
    procedure_type: str = Field(..., description="Panchakarma Procedure: VAMANA, VIRECHANA, BASTI, etc.")
    shuddhi_grade: ShuddhiGrade = Field(..., description="Purification grade from Chaturvidha Shuddhi Pariksha")
    attending_physician_arn: str = Field(..., description="NCISM ARN of attending Ayurvedic Physician")


class PaschatKarmaEpisodeResponse(BaseModel):
    """Authoritative Paschat Karma rehabilitation episode dossier."""
    episode_id: str
    patient_id: str
    hospital_id: str
    plan_id: str
    procedure_type: str
    shuddhi_grade: ShuddhiGrade
    total_annakalas: int
    total_days: int
    current_annakala: int
    agni_restoration_status: AgniRestorationStatus
    parihara_restrictions: List[str]
    rasayana_readiness: bool
    status: EpisodeStatus
    attending_physician_arn: str
    schedule: List[SamsarjanaMealStep]
    started_at: int
    completed_at: Optional[int] = None
    created_at: int


class SamsarjanaMealLogCreate(BaseModel):
    """Bedside or patient log recording the consumption of an Annakala meal."""
    annakala_number: int = Field(..., ge=1, description="Annakala index being recorded")
    patient_appetite_observed: str = Field(..., description="ALPA_KSHUDHA, MADHYAMA_KSHUDHA, or PRAVARA_KSHUDHA")
    digestion_tolerance_noted: DigestionTolerance = Field(..., description="Observed digestive outcome")
    compliance_status: str = Field(default="CONSUMED_AS_PRESCRIBED", description="Compliance code")
    clinical_notes: Optional[str] = Field(None, description="Nurse or practitioner bedside notes")
    nurse_or_practitioner_id: str = Field(..., description="Identifier of staff recording entry")


class SamsarjanaMealLogResponse(BaseModel):
    """Persisted Annakala meal observation."""
    log_id: str
    episode_id: str
    patient_id: str
    day_number: int
    annakala_number: int
    meal_time_type: AnnakalaMealTime
    prescribed_diet_form: DietaryLadderForm
    preparation_details: str
    caloric_estimate_kcal: float
    digestibility_index: float
    patient_appetite_observed: str
    digestion_tolerance_noted: DigestionTolerance
    compliance_status: str
    clinical_notes: Optional[str] = None
    nurse_or_practitioner_id: str
    logged_at: int


# -------------------------------------------------------------------------
# Trajectory & Agni Restoration Analytics
# -------------------------------------------------------------------------

class AgniKindlingPoint(BaseModel):
    """Point assessment on the Agni recovery curve."""
    annakala_number: int
    day_number: int
    diet_form: DietaryLadderForm
    theoretical_agni_score: float = Field(ge=0.0, le=1.0)
    clinical_tolerance_score: float = Field(ge=0.0, le=1.0)
    tolerance_status: DigestionTolerance


class SamsarjanaTrajectorySummary(BaseModel):
    """Cumulative metabolic trajectory and Agni restoration summary."""
    episode_id: str
    patient_id: str
    shuddhi_grade: ShuddhiGrade
    total_annakalas: int
    logged_annakalas: int
    completion_percentage: float
    current_agni_score: float = Field(ge=0.0, le=1.0)
    agni_restoration_status: AgniRestorationStatus
    intolerance_events_count: int
    clinical_trajectory: List[AgniKindlingPoint]
    recommendations: List[str]


# -------------------------------------------------------------------------
# Governance, Prohibitions & Rasayana Readiness
# -------------------------------------------------------------------------

class PariharaAdherenceAuditRequest(BaseModel):
    """Clinical audit for violations of post-purification prohibitions."""
    reported_violations: List[PariharaProhibition] = Field(default_factory=list)
    audited_by_staff_id: str
    notes: Optional[str] = None


class PariharaAdherenceAuditResponse(BaseModel):
    """Parihara compliance audit result with corrective regimens."""
    episode_id: str
    is_compliant: bool
    violations_detected: List[str]
    risk_severity: str
    remedial_measures: List[str]


class RasayanaReadinessResponse(BaseModel):
    """Statutory readiness certification for Phase 30 Rasayana / Phase 31 Vajikarana."""
    episode_id: str
    patient_id: str
    is_ready_for_rasayana: bool
    readiness_criteria_met: Dict[str, bool]
    clearance_notes: str
    recommended_rasayana_classes: List[str]
