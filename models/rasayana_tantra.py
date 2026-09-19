"""
Rasayana Tantra, Jara Chikitsa & Longevity Medicine Models
==========================================================
Defines schemas for:
1. Classical Rasayana Modalities (Kuti Praveshika vs Vatatapika, Kamya, Naimittika, Medhya)
2. Ojas Reserve, Vyadhikshamatwa & Biological Ageing Calculus (Ojo Visramsa, Vyapat, Kshaya)
3. Decadal Bio-Functional Loss Attributes (Sharngadhara Samhita)
4. Kuti Praveshika Intensive Rejuvenation Screening & Safety Firewall
5. The 4 Medhya Rasayanas Cognitive Optimization Protocol
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RasayanaType(str, Enum):
    KAMYA = "KAMYA"              # General vitality, longevity & sensory acuity (Prana, Medha, Chakshu)
    NAIMITTIKA = "NAIMITTIKA"    # Disease-specific adjuvant rejuvenation (e.g., Shilajatu for Prameha)
    AJASRIKA = "AJASRIKA"        # Continuous daily dietary unction (Ksheera, Ghrita)
    MEDHYA = "MEDHYA"            # Specialized cognitive & neural rejuvenation (Brahmi, Shankhapushpi)
    ACHARA = "ACHARA"            # Behavioral & psychological non-pharmacological rejuvenation


class RasayanaMode(str, Enum):
    KUTI_PRAVESHIKA = "KUTI_PRAVESHIKA"  # Indoor trigarbha cottage intensive retreat
    VATATAPIKA = "VATATAPIKA"            # Outdoor / open-air ambulatory routine


class OjasStatus(str, Enum):
    PRAVARA_OJAS = "PRAVARA_OJAS"        # Ojas score >= 80.0 (Robust Vyadhikshamatwa / high immune reserve)
    MADHYAMA_OJAS = "MADHYAMA_OJAS"      # Ojas score 50.0 - 79.9 (Moderate immune reserve)
    AVARA_OJAS = "AVARA_OJAS"            # Ojas score < 50.0 (Severe Ojas depletion / opportunistic vulnerability)


class RasayanaProtocol(BaseModel):
    """Catalog specification of a classical Rasayana formulation or protocol."""
    protocol_id: str
    sanskrit_name: str
    rasayana_type: RasayanaType
    mode: RasayanaMode
    primary_ingredients: List[str]
    target_dhatu: str
    classical_reference: str
    indications: List[str]


class OjasEvaluationRequest(BaseModel):
    """Clinical assessment request for Ojas reserve, Vyadhikshamatwa, and biological age."""
    patient_id: str
    chronological_age: int = Field(..., ge=18, le=120, description="Chronological age in years")
    grip_strength_kg: float = Field(..., ge=5.0, le=100.0, description="Isometric handgrip strength in kg")
    vital_capacity_liters: float = Field(..., ge=0.5, le=8.0, description="Forced vital capacity in liters")
    joint_mobility_score: float = Field(..., ge=0.0, le=10.0, description="Functional range of motion (0-10)")
    skin_luster_score: float = Field(..., ge=0.0, le=10.0, description="Skin turgor and luster / Chhavi (0-10)")
    cognitive_memory_score: float = Field(..., ge=0.0, le=10.0, description="Cognitive recall / Smriti (0-10)")
    visramsa_symptoms: List[str] = Field(default_factory=list, description="Joint laxity, fatigue, doshic dislocation")
    vyapat_symptoms: List[str] = Field(default_factory=list, description="Stiffness, dropsy, heaviness, discoloration")
    kshaya_symptoms: List[str] = Field(default_factory=list, description="Fainting, confusion, severe wasting, delirium")
    evaluator_arn: str


class OjasEvaluationResponse(BaseModel):
    """Ojas reserve calculus, biological ageing differential, and prescribed Rasayana."""
    evaluation_id: str
    patient_id: str
    hospital_id: str
    chronological_age: int
    biological_age: float
    age_differential_years: float
    ojas_score: float = Field(..., ge=0.0, le=100.0)
    ojas_status: OjasStatus
    visramsa_score: float
    vyapat_score: float
    kshaya_score: float
    decadal_attribute_decay: str
    prescribed_rasayana_id: str
    recommended_rasayana_formulation: str
    lifestyle_achara_rasayana: List[str]
    practitioner_arn: str
    created_at: int


class KutiPraveshikaAdmissionRequest(BaseModel):
    """Screening and admission request for intensive Kuti Praveshika rejuvenation."""
    patient_id: str
    chronological_age: int = Field(..., ge=18, le=120)
    has_active_acute_infection: bool = False
    blood_pressure_systolic: int = Field(..., ge=80, le=220)
    blood_pressure_diastolic: int = Field(..., ge=50, le=140)
    has_severe_cardiac_or_psychiatric_instability: bool = False
    pre_shodhana_completed: bool = False
    planned_duration_days: int = Field(..., ge=7, le=90, description="Planned retreat duration in days (typically 21 to 60 days)")
    rasayana_formulation: str
    practitioner_arn: str


class KutiPraveshikaAdmissionResponse(BaseModel):
    """Kuti Praveshika admission verification and cottage architecture clearance."""
    episode_id: str
    patient_id: str
    hospital_id: str
    duration_days: int
    pre_shodhana_completed: bool
    rasayana_formulation: str
    eligibility_cleared: bool
    contraindication_flags: List[str]
    kuti_design_guidelines: List[str]
    practitioner_arn: str
    created_at: int
