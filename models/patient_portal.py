"""
models/patient_portal.py - Data models for Phase 41: Patient Portal & PWA Interface.
Tables 88 & 89: patient_portal_accounts, patient_daily_logs.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class BowelMovementType(str, Enum):
    SAMYAK_NORMAL = "SAMYAK_NORMAL_FORMED"
    VATA_CONSTIPATED = "VATA_CONSTIPATED_DRY_HARD"
    PITTA_LOOSE = "PITTA_LOOSE_BURNING_YELLOW"
    KAPHA_HEAVY_MUCOID = "KAPHA_HEAVY_MUCOID_SINKING"


class PatientPortalAccountCreate(BaseModel):
    patient_id: str = Field(..., description="Hospital Master Patient Index ID")
    hospital_id: str = Field(..., description="Hospital UUID")
    phone_number: str = Field(..., min_length=10, max_length=15, description="Patient mobile number")
    password: str = Field(..., min_length=6, description="Portal access password")
    abha_address: Optional[str] = Field(None, description="Ayushman Bharat Health Account (ABHA) address")


class PatientPortalAccountResponse(BaseModel):
    account_id: str
    patient_id: str
    hospital_id: str
    phone_number: str
    abha_address: Optional[str]
    is_active: bool
    created_at: int


class PatientPortalLoginRequest(BaseModel):
    phone_number: str
    password: str


class PatientPortalTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    account_id: str
    patient_id: str
    hospital_id: str
    first_name: str
    last_name: str


class PatientDailyLogCreate(BaseModel):
    patient_id: str
    hospital_id: str
    log_date: str = Field(..., description="Date YYYY-MM-DD")
    diet_adherence_score: int = Field(100, ge=0, le=100, description="Pathya adherence self-rating percentage")
    pathya_followed_notes: Optional[str] = Field(None, description="Meals and prescribed pathya followed")
    ahara_craving: Optional[str] = Field(None, description="Specific rasa or food craving")
    bowel_movement_type: BowelMovementType = Field(..., description="Morning bowel movement observation")
    sleep_duration_hours: float = Field(..., ge=0.0, le=24.0, description="Hours of night sleep")
    stress_level: int = Field(1, ge=1, le=10, description="Self-reported stress / Manasa tension (1-10)")


class PatientDailyLogRecord(BaseModel):
    log_id: str
    patient_id: str
    hospital_id: str
    log_date: str
    diet_adherence_score: int
    pathya_followed_notes: Optional[str]
    ahara_craving: Optional[str]
    bowel_movement_type: BowelMovementType
    sleep_duration_hours: float
    stress_level: int
    doshic_aggravation_warning: Optional[str]
    logged_at: int


class PatientHealthSummary(BaseModel):
    patient_id: str
    hospital_id: str
    full_name: str
    dob: str
    gender: str
    prakriti: Dict[str, float]
    total_logs: int
    average_diet_adherence: float
    active_prescriptions_count: int
    recent_logs: List[PatientDailyLogRecord]
