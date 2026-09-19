"""Pydantic schemas for Jalaukavacharana, Siravedha & Raktamokshana Biotherapy Suite."""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JalaukaType(str, Enum):
    """Classical categorization of leeches into therapeutic and toxic varieties."""
    NIRVISHA = "NIRVISHA"  # Therapeutic / Non-poisonous
    SAVISHA = "SAVISHA"    # Poisonous / Strictly contraindicated


class RaktamokshanaModality(str, Enum):
    """Classical modalities of bloodletting based on tissue depth and vitiation."""
    JALAUKAVACHARANA = "JALAUKAVACHARANA"  # Leech therapy for Pitta/deep-seated/sensitive patients
    SIRAVEDHA = "SIRAVEDHA"                # Venesection for generalized/Sarva-Sharira vitiation
    PRACHHANA = "PRACHHANA"                # Scarification for localized superficial vitiation
    SHRINGA = "SHRINGA"                    # Cow horn suction for Vata-dominant vitiation
    ALABU = "ALABU"                        # Pitcher gourd suction for Kapha-dominant vitiation
    GHATI_YANTRA = "GHATI_YANTRA"          # Cupping apparatus


class BodyQuadrant(str, Enum):
    """Anatomical regions for Siras according to Sushruta Samhita Sharirasthana Ch. 8."""
    SHAKHA_URDHVA = "SHAKHA_URDHVA"      # Upper extremities
    SHAKHA_ADHA = "SHAKHA_ADHA"          # Lower extremities
    KOSTHA = "KOSTHA"                    # Trunk / Thorax / Abdomen / Pelvis
    URO_GREEVA = "URO_GREEVA"            # Chest and Neck
    SHIRAH = "SHIRAH"                    # Cranium / Head


class BloodDoshaVitiation(str, Enum):
    """Dosha vitiation markers in extracted blood (Sushruta Sutrasthana Ch. 14)."""
    VATIKA = "VATIKA"                    # Frothy, dark, non-slimy, thin, rapid flow
    PAITTIKA = "PAITTIKA"                # Yellow/black, sour odor, hot, delayed clotting
    KAPHAJA = "KAPHAJA"                  # Slimy, whitish hue, thick, unctuous, slow flow
    RAKTA_PRADHAN = "RAKTA_PRADHAN"      # Crimson, warm, non-slimy, balanced
    SANNIPATAJA = "SANNIPATAJA"          # Turbid, multi-colored, foul odor
    SHUDDHA_RAKTA = "SHUDDHA_RAKTA"      # Cochineal / rabbit blood color, sweetish, non-hot


class HemostasisMethod(str, Enum):
    """Chaturvidha Rakta-Stambhana modalities (Sushruta Sutrasthana Ch. 14)."""
    SANDHANA = "SANDHANA"                # Astringent herbs (Lodhra, Priyangu, Madhuka) coaptation
    SKANDANA = "SKANDANA"                # Cold application / refrigeration to promote clot
    PACHANA = "PACHANA"                  # Ash / alkaline mineral drying of blood
    DAHANA = "DAHANA"                    # Thermal / chemical cauterization of bleeding vessel
    NATURAL_SPONTANEOUS = "NATURAL_SPONTANEOUS" # Normal physiological clot cascade


class RogiBala(str, Enum):
    """Patient constitutional and physical strength classification."""
    UTTAMA = "UTTAMA"                    # Superior strength
    MADHYAMA = "MADHYAMA"                # Moderate strength
    AVARA = "AVARA"                      # Inferior / debilitated strength


class AvadhyaComplicationRisk(str, Enum):
    """Clinical consequences of puncturing an Avadhya Sira (contraindicated vein)."""
    FATAL_HEMORRHAGE = "FATAL_HEMORRHAGE"
    BLINDNESS = "BLINDNESS"
    DEAFNESS = "DEAFNESS"
    PARALYSIS = "PARALYSIS"
    DEATH_ASPHYXIA = "DEATH_ASPHYXIA"
    ORGAN_FAILURE = "ORGAN_FAILURE"
    NONE = "NONE"


class ShastraUsed(str, Enum):
    """Sharp cutting surgical instrument utilized for venesection."""
    VRIHIMUKHA = "VRIHIMUKHA"            # Used for fleshier veins
    KUTHARIKA = "KUTHARIKA"              # Small axe-like instrument for veins over bones
    SUCHI = "SUCHI"                      # Needle for micro-venepuncture
    NONE = "NONE"


# -------------------------------------------------------------------------
# Entity Models
# -------------------------------------------------------------------------

class JalaukaSpecies(BaseModel):
    """Classical Jalauka species profile."""
    species_id: str
    sanskrit_name: str
    species_type: JalaukaType
    morphological_markers: List[str]
    salivary_enzymes_profile: Dict[str, Any]
    habitat_water_type: str
    clinical_suitability: str
    created_at: int


class SiravedhaVein(BaseModel):
    """Anatomical vein catalog entry with Avadhya status."""
    vein_code: str
    sanskrit_name: str
    anatomical_location: str
    body_quadrant: BodyQuadrant
    is_avadhya: bool
    avadhya_complication_risk: AvadhyaComplicationRisk
    indicated_diseases: List[str]
    puncture_depth_angula: float
    instrument_shastra: ShastraUsed
    created_at: int


class SafetyEvaluationRequest(BaseModel):
    """Pre-procedure safety firewall audit request."""
    patient_id: str
    hospital_id: str
    modality: RaktamokshanaModality
    rogi_bala: RogiBala
    patient_age: int
    patient_weight_kg: float
    baseline_hemoglobin_g_dl: float
    platelet_count: int = Field(default=250000, description="Platelet count per microliter")
    inr: float = Field(default=1.0, description="International Normalized Ratio")
    systolic_bp: int = Field(default=120, description="Systolic blood pressure in mmHg")
    diastolic_bp: int = Field(default=80, description="Diastolic blood pressure in mmHg")
    species_id: Optional[str] = None
    vein_code: Optional[str] = None
    proposed_volume_ml: float
    has_active_bleeding_diathesis: bool = False
    is_pregnant: bool = False
    current_season: str = "SHARAD"


class SafetyEvaluationResponse(BaseModel):
    """Pre-procedure safety firewall verdict and guidance."""
    cleared: bool
    firewall_status: str
    reason: str
    max_permissible_volume_ml: float
    recommended_modality: RaktamokshanaModality
    suggested_hemostasis: HemostasisMethod
    post_procedure_nutritional_replenishment: List[str]
    estimated_post_op_hb_g_dl: float


class RaktamokshanaProcedureLogCreate(BaseModel):
    """Request payload to log a completed Raktamokshana procedure."""
    patient_id: str
    hospital_id: str
    modality: RaktamokshanaModality
    target_anatomical_site: str
    vein_or_point_id: Optional[str] = None
    species_id: Optional[str] = None
    jalauka_count: Optional[int] = None
    evacuated_volume_ml: float
    pre_procedure_hb: float
    post_procedure_hb: Optional[float] = None
    blood_dosha_vitiation: BloodDoshaVitiation
    hemostasis_method: HemostasisMethod
    complications_observed: List[str] = Field(default_factory=list)
    practitioner_arn: str


class RaktamokshanaProcedureLogResponse(BaseModel):
    """Persisted Raktamokshana procedure response."""
    procedure_id: str
    patient_id: str
    hospital_id: str
    modality: RaktamokshanaModality
    target_anatomical_site: str
    vein_or_point_id: Optional[str]
    species_id: Optional[str]
    jalauka_count: Optional[int]
    evacuated_volume_ml: float
    pre_procedure_hb: float
    post_procedure_hb: float
    blood_dosha_vitiation: BloodDoshaVitiation
    hemostasis_method: HemostasisMethod
    safety_firewall_cleared: bool
    complications_observed: List[str]
    practitioner_arn: str
    created_at: int
