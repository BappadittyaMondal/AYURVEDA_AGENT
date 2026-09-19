"""
Prasuti Tantra, Stri Roga & Garbhini Paricharya Models
======================================================
Defines schemas for:
1. Garbha Sambhava Samagri (Ritu, Kshetra, Ambu, Beeja) Preconception Fertility Readiness
2. Month-by-Month Garbhini Paricharya Regimen (1st through 9th Month)
3. Antenatal Consultation with High-Risk Obstetric Triage & Emergency Firewall
4. Classical 20 Yoni Vyapad Gynecological Classification & Therapeutics
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DoshicClass(str, Enum):
    VATAJA = "VATAJA"
    PITTAJA = "PITTAJA"
    KAPHAJA = "KAPHAJA"
    SANNIPATAJA = "SANNIPATAJA"


class ObstetricTriageLevel(str, Enum):
    NORMAL = "NORMAL"                                      # Low-risk physiological pregnancy
    CAUTION = "CAUTION"                                    # Mild risk factors requiring close monitoring
    CRITICAL_OBSTETRIC_EMERGENCY = "CRITICAL_OBSTETRIC_EMERGENCY"  # Acute bleeding/pre-eclampsia/fetal distress


class FertilityReadinessRequest(BaseModel):
    """Garbha Sambhava Samagri 4-factor preconception assessment request."""
    patient_id: str
    ritu_score: float = Field(..., ge=0.0, le=100.0, description="Ritu: ovulatory timing & maternal biological window (0-100)")
    kshetra_score: float = Field(..., ge=0.0, le=100.0, description="Kshetra: uterine cavity & reproductive tract integrity (0-100)")
    ambu_score: float = Field(..., ge=0.0, le=100.0, description="Ambu: plasma volume, nutritional rasa & metabolic hydration (0-100)")
    beeja_score: float = Field(..., ge=0.0, le=100.0, description="Beeja: sperm and ovum viability & genetic vitality (0-100)")
    evaluator_arn: str
    clinical_notes: Optional[str] = None


class FertilityReadinessResponse(BaseModel):
    """Garbha Sambhava Samagri evaluation outcome and preconception protocol."""
    patient_id: str
    composite_readiness_score: float = Field(..., ge=0.0, le=100.0)
    readiness_tier: str = Field(..., description="EXCELLENT, ADEQUATE, COMPROMISED, POOR")
    ritu_status: str
    kshetra_status: str
    ambu_status: str
    beeja_status: str
    preconception_recommendations: List[str]
    indicated_shodhana_or_rasayana: List[str]


class GarbhiniMonthRegimen(BaseModel):
    """Month-by-month Garbhini Paricharya classical regimen specification."""
    month_number: int = Field(..., ge=1, le=9)
    sanskrit_name: str
    dietary_regimen: str
    medicated_milk_or_ghee: str
    therapeutic_procedures: str
    fetal_development_milestone: str
    contraindicated_drugs: List[str]


class AntenatalConsultationCreate(BaseModel):
    """Garbhini antenatal consultation and clinical examination logging."""
    patient_id: str
    gestational_age_weeks: float = Field(..., ge=1.0, le=44.0, description="Gestational age in weeks")
    blood_pressure_systolic: int = Field(..., ge=60, le=240, description="Systolic BP in mmHg")
    blood_pressure_diastolic: int = Field(..., ge=30, le=160, description="Diastolic BP in mmHg")
    fundal_height_cm: float = Field(..., ge=0.0, le=50.0, description="Symphysis-fundal height in cm")
    fetal_heart_rate_bpm: int = Field(..., ge=0, le=220, description="Fetal heart rate in BPM")
    weight_kg: float = Field(..., ge=30.0, le=180.0, description="Current maternal weight in kg")
    edema_present: bool = False
    vaginal_bleeding_present: bool = False
    severe_headache_or_scotoma: bool = False
    dauhrida_desires: List[str] = Field(default_factory=list, description="Dauhrida cravings (Months 4-5)")
    practitioner_arn: str


class AntenatalConsultationResponse(BaseModel):
    """Antenatal clinical evaluation with high-risk obstetric triage."""
    consultation_id: str
    patient_id: str
    hospital_id: str
    gestational_age_weeks: float
    gestational_month: int
    blood_pressure_systolic: int
    blood_pressure_diastolic: int
    fundal_height_cm: float
    fetal_heart_rate_bpm: int
    weight_kg: float
    edema_present: bool
    vaginal_bleeding_present: bool
    dauhrida_desires: List[str]
    high_risk_flags: List[str]
    obstetric_triage_level: ObstetricTriageLevel
    contraindicated_ayurvedic_therapies: List[str]
    prescribed_regimen: str
    emergency_escalation_notes: Optional[str] = None
    practitioner_arn: str
    created_at: int


class YoniVyapadProfile(BaseModel):
    """Classical specification of a Yoni Vyapad gynecological condition."""
    vyapad_code: str
    sanskrit_name: str
    english_name: str
    doshic_class: DoshicClass
    icd11_mapping: str
    pathogenesis_summary: str
    cardinal_symptoms: List[str]
    local_therapies: List[str]
    classical_formulations: List[str]


class YoniVyapadAssessmentCreate(BaseModel):
    """Log clinical evaluation for a Yoni Vyapad gynecological condition."""
    patient_id: str
    vyapad_code: str
    reported_symptoms: List[str]
    pelvic_examination_findings: str
    practitioner_arn: str


class YoniVyapadAssessmentResponse(BaseModel):
    """Diagnosed Yoni Vyapad record with localized and systemic treatment plan."""
    assessment_id: str
    patient_id: str
    hospital_id: str
    vyapad_code: str
    vyapad_name: str
    doshic_class: DoshicClass
    icd11_mapping: str
    symptoms: List[str]
    local_therapies: List[str]
    oral_formulations: List[str]
    treatment_protocol: str
    practitioner_arn: str
    created_at: int
