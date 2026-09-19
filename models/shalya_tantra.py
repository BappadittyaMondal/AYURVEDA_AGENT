"""
Shalya Tantra, Marma Sharira, Agnikarma & Ksharasutra Models
============================================================
Defines schemas for:
1. 107 Classical Marmas (Sadyo-Pranahara, Kalantara, Vishalyaghna, Vaikalyakara, Rujakara)
2. Surgical incision proximity screening and Sadyo-Pranahara shock firewall
3. Agnikarma thermal delivery dynamics (Panchadhatu Shalaka, operating temperature, contact duration)
4. Ksharasutra anorectal fistula management (Unit-Cutting Time UCT calculus & track healing)
5. Vrana surgical wound staging (Dusta, Shuddha, Ruhamana) & Shashti-Upakrama prescribing
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MarmaType(str, Enum):
    SADYO_PRANAHARA = "SADYO_PRANAHARA"              # Fatal within 1 to 7 days upon injury (19 Marmas)
    KALANTARA_PRANAHARA = "KALANTARA_PRANAHARA"      # Fatal within 15 to 30 days upon injury (33 Marmas)
    VISHALYAGHNA = "VISHALYAGHNA"                    # Fatal upon extraction of lodged foreign body (3 Marmas)
    VAIKALYAKARA = "VAIKALYAKARA"                    # Causes permanent anatomical/functional deformity (44 Marmas)
    RUJAKARA = "RUJAKARA"                            # Causes persistent intractable pain (8 Marmas)


class MarmaStructure(str, Enum):
    MAMSA = "MAMSA"                                  # Muscle tissue predominance (11 Marmas)
    SIRA = "SIRA"                                    # Blood vessels / vascular predominance (41 Marmas)
    SNAYU = "SNAYU"                                  # Ligaments / tendon / fascia predominance (27 Marmas)
    ASTHI = "ASTHI"                                  # Bone / osseous predominance (8 Marmas)
    SANDHI = "SANDHI"                                # Articulation / joint predominance (20 Marmas)


class MarmaRegion(str, Enum):
    SHAKHA = "SHAKHA"                                # Upper and lower extremities (44 Marmas)
    KOSHTHA = "KOSHTHA"                              # Thoraco-abdominal cavity (12 Marmas)
    PRISHTHA = "PRISHTHA"                            # Posterior back / vertebral spine (14 Marmas)
    URDHWAJATRUGATA = "URDHWAJATRUGATA"              # Head and neck / supraclavicular (37 Marmas)


class MarmaProfile(BaseModel):
    """Classical Marma anatomical specification and vulnerability profile."""
    marma_id: str
    sanskrit_name: str
    english_name: str
    marma_type: MarmaType
    structural_predominance: MarmaStructure
    anatomical_region: MarmaRegion
    dimension_angula: float = Field(..., gt=0.0, description="Classical dimension (Pramana) in Angulas")
    anatomical_landmarks: str
    trauma_manifestations: List[str]
    vulnerability_radius_cm: float = Field(..., gt=0.0, description="Minimum safe surgical distance in cm")


class MarmaProximityCheckRequest(BaseModel):
    """Surgical incision pre-operative screening request."""
    patient_id: str
    proposed_incision_site: str
    anatomical_region: MarmaRegion
    nearest_marma_id: str
    distance_from_marma_cm: float = Field(..., ge=0.0, description="Planned distance from Marma epicenter")
    surgeon_arn: str


class MarmaProximityCheckResponse(BaseModel):
    """Surgical proximity screening findings and shock firewall status."""
    patient_id: str
    nearest_marma_id: str
    marma_name: str
    marma_type: MarmaType
    is_safe_incision: bool
    vulnerability_radius_cm: float
    actual_distance_cm: float
    safety_tier: str = Field(..., description="CLEAR, CAUTION_REQUIRED, CRITICAL_BLOCKED")
    shock_resuscitation_protocol: Optional[str] = None
    surgical_recommendations: List[str]


class AgnikarmaDevice(str, Enum):
    PANCHADHATU_SHALAKA = "PANCHADHATU_SHALAKA"      # 5-metal alloy probe (Copper, Iron, Brass, Lead, Zinc)
    JAMBAVOSHTHA_LOHA = "JAMBAVOSHTHA_LOHA"          # Blunt iron probe for muscular cauterization
    PIPPALI = "PIPPALI"                              # Herbal cauterization for superficial cysts / warts
    SNEHA_TAILA_GHRITA = "SNEHA_TAILA_GHRITA"        # Boiling oil/ghee for deep joint/tendon cautery
    GODA_MADHU = "GODA_MADHU"                        # Boiling jaggery/honey for bleeding vessels


class AgnikarmaPattern(str, Enum):
    BINDU = "BINDU"                                  # Dot / Punctate cauterization
    VILEKHA = "VILEKHA"                              # Linear / Striated cauterization
    VALAYA = "VALAYA"                                # Circular / Ring cauterization
    PRATISARANA = "PRATISARANA"                      # Broad rubbing / Planar cauterization


class AgnikarmaSessionCreate(BaseModel):
    """Log an Agnikarma thermal cauterization procedure."""
    patient_id: str
    anatomical_site: str
    dahanopakarana: AgnikarmaDevice
    operating_temperature_c: float = Field(..., ge=80.0, le=300.0, description="Thermal probe temperature in Celsius")
    contact_time_seconds: float = Field(..., ge=0.2, le=5.0, description="Contact time in seconds")
    pattern: AgnikarmaPattern
    clinical_indication: str
    practitioner_arn: str


class AgnikarmaSessionResponse(BaseModel):
    """Evaluated and logged Agnikarma session record."""
    session_id: str
    patient_id: str
    anatomical_site: str
    dahanopakarana: AgnikarmaDevice
    operating_temperature_c: float
    contact_time_seconds: float
    burn_grade: str = Field(..., description="SAMYAK_DAGDHA, ATIDAGDHA, DURDAGDHA")
    post_care_dressing: str
    adverse_flags: List[str]
    practitioner_arn: str
    created_at: int


class KsharasutraFistulaType(str, Enum):
    INTERSPHINCTERIC = "INTERSPHINCTERIC"            # Low anal fistula (between internal & external sphincters)
    TRANSSPHINCTERIC = "TRANSSPHINCTERIC"            # Mid-to-high fistula crossing external sphincter
    SUPRASPHINCTERIC = "SUPRASPHINCTERIC"            # Complex high fistula coursing above puborectalis
    EXTRASPHINCTERIC = "EXTRASPHINCTERIC"            # Fistula originating above levator ani
    PILONIDAL_SINUS = "PILONIDAL_SINUS"              # Sacrococcygeal Nadi Vrana


class KsharasutraSessionCreate(BaseModel):
    """Log a Ksharasutra threading, changing, or measurement session."""
    patient_id: str
    fistula_type: KsharasutraFistulaType
    initial_track_length_cm: float = Field(..., gt=0.0)
    current_track_length_cm: float = Field(..., ge=0.0)
    sittings_count: int = Field(..., ge=1)
    total_days_elapsed: int = Field(..., ge=1)
    active_symptoms: List[str] = Field(default_factory=list)
    practitioner_arn: str


class KsharasutraSessionResponse(BaseModel):
    """Track assessment, Unit Cutting Time (UCT), and progress."""
    episode_id: str
    patient_id: str
    fistula_type: KsharasutraFistulaType
    initial_track_length_cm: float
    current_track_length_cm: float
    cut_length_cm: float
    percentage_cut: float
    unit_cutting_time_days_per_cm: float
    healing_status: str = Field(..., description="IN_PROGRESS, CUT_THROUGH_COMPLETE, SLOW_HEALING")
    clinical_advisory: str
    practitioner_arn: str
    created_at: int


class VranaStage(str, Enum):
    DUSTA_VRANA = "DUSTA_VRANA"                      # Septic / non-healing / slough-covered ulcer
    SHUDDHA_VRANA = "SHUDDHA_VRANA"                  # Clean, granulating, non-tender ulcer
    RUHAMANA_VRANA = "RUHAMANA_VRANA"                # Actively healing / contracting / marginalizing
    RUDHA_VRANA = "RUDHA_VRANA"                      # Fully healed / re-epithelialized cicatrix


class VranaAssessmentCreate(BaseModel):
    """Clinical surgical wound assessment."""
    patient_id: str
    location: str
    dimensions_cm: str = Field(..., description="e.g. 4.0 x 3.0 x 0.5 cm")
    is_foul_smelling: bool = False
    has_purulent_discharge: bool = False
    has_healthy_granulation: bool = True
    edge_character: str = Field(..., description="SLOPING, PUNCHED_OUT, UNDERMINED, EVERTED")
    practitioner_arn: str


class VranaAssessmentResponse(BaseModel):
    """Evaluated wound stage with Shashti-Upakrama treatment prescription."""
    evaluation_id: str
    patient_id: str
    wound_stage: VranaStage
    prescribed_shashti_upakramas: List[str]
    topical_formulation: str
    irrigation_solution: str
    dressing_frequency: str
    practitioner_arn: str
    created_at: int
