"""
Marma Sharira, Vital Traumatology & Marma Chikitsa Models
=========================================================
Defines schemas for:
1. The 107 Classical Marmas Structural & Prognostic Taxonomy (Sushruta Samhita Sharirasthana Ch. 6)
2. Rachana Bheda (Mamsa, Sira, Snayu, Asthi, Sandhi) & Parinama Bheda (Sadhyo-Pranahara to Rujakara)
3. Tri-Marma Emergency Resuscitation Firewall (Hridaya, Basti, Shiras)
4. Vishalyaghna Foreign Body Surgical Extraction Firewall (Utkshepa, Sthapani)
5. Therapeutic Marma Chikitsa Acupressure Stimulation Sessions
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MarmaRachana(str, Enum):
    MAMSA = "MAMSA"       # Muscular tissue vital points (10 points)
    SIRA = "SIRA"         # Vascular / hemodynamic vital points (41 points)
    SNAYU = "SNAYU"       # Tendinous / ligamentous vital points (27 points)
    ASTHI = "ASTHI"       # Osseous / skeletal vital points (8 points)
    SANDHI = "SANDHI"     # Articular / joint vital points (20 points)


class MarmaParinama(str, Enum):
    SADHYO_PRANAHARA = "SADHYO_PRANAHARA"           # Fatal within 1 to 7 days (19 points)
    KALANTARA_PRANAHARA = "KALANTARA_PRANAHARA"     # Fatal within 15 to 30 days (33 points)
    VISHALYAGHNA = "VISHALYAGHNA"                   # Fatal upon extraction of weapon/shrapnel (3 points)
    VAIKALYAKARA = "VAIKALYAKARA"                   # Permanent anatomical/functional disability (44 points)
    RUJAKARA = "RUJAKARA"                           # Severe chronic pain and debility (8 points)


class MarmaRegion(str, Enum):
    SHAKHA = "SHAKHA"                     # Extremities (44 points)
    MADHYA_SHARIRA = "MADHYA_SHARIRA"     # Thorax & Abdomen (12 points)
    PRISHTHA = "PRISHTHA"                 # Back & Posterior Trunk (14 points)
    URDHVAJATRU = "URDHVAJATRU"           # Head & Neck above Clavicle (37 points)


class MarmaTraumaTriage(str, Enum):
    CODE_RED_TRI_MARMA_CRITICAL = "CODE_RED_TRI_MARMA_CRITICAL"             # Immediate resuscitation mandatory
    CODE_ORANGE_VISHALYAGHNA_SURGICAL = "CODE_ORANGE_VISHALYAGHNA_SURGICAL" # Extraction firewall: Do not pull in field!
    CODE_YELLOW_VAIKALYAKARA_URGENT = "CODE_YELLOW_VAIKALYAKARA_URGENT"     # High risk of permanent deformity/loss of limb
    CODE_GREEN_STABLE = "CODE_GREEN_STABLE"                                 # Localized pain / minor contusion


class StimulationModality(str, Enum):
    ANGULI_PIDANA = "ANGULI_PIDANA"       # Digital thumb / finger rhythmic acupressure
    TAILA_ABHYANGA = "TAILA_ABHYANGA"     # Medicated warm herbal oil friction / massage
    LEPA = "LEPA"                         # Warm herbal paste application
    AGNIKARMA = "AGNIKARMA"               # Micro-thermal cautery stimulation


class MarmaPointProfile(BaseModel):
    """Classical specification of a vital Marma point."""
    marma_code: str
    sanskrit_name: str
    anatomical_region: MarmaRegion
    rachana_structure: MarmaRachana
    parinama_prognosis: MarmaParinama
    angula_dimension: float = Field(..., ge=0.5, le=4.0, description="Vulnerability radius in Angula units (0.5 to 4.0)")
    cardinal_vulnerability: str
    emergency_management: str
    therapeutic_indications: List[str]


class MarmaTraumaEmergencyCreate(BaseModel):
    """Emergency admission and intake for vital Marma trauma."""
    patient_id: str
    injured_marma_code: str
    trauma_mechanism: str = Field(..., description="Penetrating, blunt, crush, incised, or blast injury")
    depth_penetration_mm: float = Field(..., ge=0.0, le=300.0)
    foreign_body_present: bool = Field(default=False, description="Presence of lodged arrow, shrapnel, or weapon")
    practitioner_arn: str


class MarmaTraumaEmergencyResponse(BaseModel):
    """Emergency triage verdict, resuscitation protocol, and surgical extraction firewall."""
    log_id: str
    patient_id: str
    hospital_id: str
    injured_marma_code: str
    trauma_mechanism: str
    depth_penetration_mm: float
    foreign_body_present: bool
    tri_marma_involved: bool
    triage_tier: MarmaTraumaTriage
    emergency_resuscitation_protocol: str
    surgical_extraction_warning: Optional[str] = None
    practitioner_arn: str
    created_at: int


class MarmaChikitsaSessionCreate(BaseModel):
    """Clinical request for therapeutic Marma acupressure or stimulation."""
    patient_id: str
    targeted_marma_code: str
    stimulation_modality: StimulationModality = StimulationModality.ANGULI_PIDANA
    pressure_intensity_kg: float = Field(..., ge=0.1, le=5.0, description="Applied pressure in kg (therapeutic range 0.5 - 1.5 kg)")
    cycles_count: int = Field(..., ge=3, le=50, description="Compression/decompression breathing cycles")
    clinical_objective: str
    practitioner_arn: str


class MarmaChikitsaSessionResponse(BaseModel):
    """Clinical record of Marma Chikitsa stimulation session."""
    session_id: str
    patient_id: str
    hospital_id: str
    targeted_marma_code: str
    stimulation_modality: StimulationModality
    pressure_intensity_kg: float
    cycles_count: int
    clinical_objective: str
    immediate_response: str
    practitioner_arn: str
    created_at: int
