"""
Sattvavajaya Chikitsa, Manasa Roga, Triguna Dynamics & Mental Health CDSS Models
================================================================================
Defines schemas for:
1. Triguna dynamics (Sattva, Rajas, Tamas simplex vector)
2. Mental faculties assessment (Dhi, Dhriti, Smriti & Prajnaparadha Index)
3. Classical Manasa Roga classification (Unmada, Apasmara, Chittodvega, Avasada, Atattvabhinivesha)
4. Trividha Chikitsa prescription (Daivavyapashraya, Yuktivyapashraya Medhya Rasayana, Sattvavajaya)
5. Psychiatric emergency crisis firewall (Suicidal ideation, violent delirium, acute catatonia)
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ManasaDisorderCode(str, Enum):
    UNMADA_VATAJA = "UNMADA_VATAJA"                    # Psychosis with psychomotor agitation / incoherent speech
    UNMADA_PITTAJA = "UNMADA_PITTAJA"                  # Manic rage, violent aggression, hyperthermia
    UNMADA_KAPHAJA = "UNMADA_KAPHAJA"                  # Catatonia, depressive stupor, mutism, hypersomnia
    UNMADA_SANNIPATAJA = "UNMADA_SANNIPATAJA"          # Severe intractable chronic psychosis
    APASMARA = "APASMARA"                              # Seizure / Epilepsy / Dissociative convulsion
    CHITTODVEGA = "CHITTODVEGA"                        # Generalized Anxiety Disorder / Panic
    AVASADA = "AVASADA"                                # Major Depressive Disorder / Melancholia / Vishada
    ATATTVABHINIVESHA = "ATATTVABHINIVESHA"            # Delusional disorder / Obsessive fixed falsehood
    MADATYAYA = "MADATYAYA"                            # Substance / Alcohol withdrawal & dependence


class CrisisRiskLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MODERATE = "MODERATE"
    CRITICAL_EMERGENCY = "CRITICAL_EMERGENCY"


class TrigunaVector(BaseModel):
    """Normalized psychometric Triguna simplex vector where s + r + t = 1.0."""
    sattva: float = Field(..., ge=0.0, le=1.0, description="Purity, clarity, emotional equilibrium")
    rajas: float = Field(..., ge=0.0, le=1.0, description="Kinetic passion, anxiety, agitation, aggression")
    tamas: float = Field(..., ge=0.0, le=1.0, description="Inertia, darkness, depressive stupor, delusion")


class MentalFacultyScores(BaseModel):
    """Classical cognitive and emotional regulation faculty scores (0.0 - 10.0 scale)."""
    dhi_score: float = Field(..., ge=0.0, le=10.0, description="Intellect, discriminative reasoning, perception")
    dhriti_score: float = Field(..., ge=0.0, le=10.0, description="Willpower, impulse control, emotional retention")
    smriti_score: float = Field(..., ge=0.0, le=10.0, description="Memory, wholesome recollection, past wisdom")


class ManasaDisorderProfile(BaseModel):
    """Classical psychiatric disorder specifications and integrated ICD-11 mapping."""
    disorder_code: ManasaDisorderCode
    sanskrit_name: str
    english_name: str
    icd11_mapping: str
    manasa_dosha: str
    sharirika_dosha: str
    faculty_impairment: List[str]
    medhya_rasayana: List[str]
    sattvavajaya_modalities: List[str]
    emergency_escalation_criteria: List[str]


class ManasaAssessmentCreateRequest(BaseModel):
    """Clinical request to perform a Manasa Roga and Triguna assessment."""
    patient_id: str
    disorder_code: ManasaDisorderCode
    raw_sattva: float = Field(..., ge=0.0, description="Unnormalized psychometric score for Sattva")
    raw_rajas: float = Field(..., ge=0.0, description="Unnormalized psychometric score for Rajas")
    raw_tamas: float = Field(..., ge=0.0, description="Unnormalized psychometric score for Tamas")
    dhi_score: float = Field(..., ge=0.0, le=10.0, description="Dhi (Intellect/reasoning) score (0-10)")
    dhriti_score: float = Field(..., ge=0.0, le=10.0, description="Dhriti (Emotional control/willpower) score (0-10)")
    smriti_score: float = Field(..., ge=0.0, le=10.0, description="Smriti (Mindful memory) score (0-10)")
    has_suicidal_ideation: bool = Field(default=False, description="Presence of active suicidal thoughts or intent")
    has_violent_agitation: bool = Field(default=False, description="Physical violence, aggression, or homicidal intent")
    has_severe_delusion: bool = Field(default=False, description="Profound break from reality or unshakeable delusion")
    clinical_notes: Optional[str] = None
    assessed_by_arn: str = Field(..., description="NCISM ARN of evaluating practitioner")


class ManasaAssessmentResponse(BaseModel):
    """Evaluated Manasa Roga psychometric profile with Prajnaparadha index and crisis risk."""
    assessment_id: str
    patient_id: str
    triguna: TrigunaVector
    faculties: MentalFacultyScores
    prajnaparadha_index: float = Field(..., ge=0.0, le=100.0, description="Degree of cognitive/willpower failure (0-100%)")
    primary_manasa_disorder: ManasaDisorderCode
    crisis_risk_level: CrisisRiskLevel
    emergency_alert: Optional[str] = None
    clinical_summary: str
    assessed_by_arn: str
    created_at: int


class SattvavajayaPrescriptionCreateRequest(BaseModel):
    """Request to prescribe Trividha Chikitsa (Daiva, Yukti Medhya, Sattvavajaya)."""
    assessment_id: str
    patient_id: str
    include_daivavyapashraya: bool = Field(default=True, description="Mantra, spiritual mindfulness, Swastyayana")
    include_yukti_medhya: bool = Field(default=True, description="Medhya Rasayanas e.g. Shankhapushpi, Brahmi Ghrita")
    include_sattvavajaya_cbt: bool = Field(default=True, description="Cognitive-behavioral sensory withdrawal / Mano-nigraha")
    prescribed_by_arn: str = Field(..., description="NCISM ARN of prescribing physician")


class SattvavajayaPrescriptionResponse(BaseModel):
    """Comprehensive Trividha Chikitsa psychiatric prescription."""
    prescription_id: str
    assessment_id: str
    patient_id: str
    daivavyapashraya_therapies: List[str]
    yukti_medhya_rasayanas: List[str]
    sattvavajaya_cbt_interventions: List[str]
    contraindicated_factors: List[str]
    clinical_prognosis: str
    prescribed_by_arn: str
    created_at: int
