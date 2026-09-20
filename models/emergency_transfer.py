"""
Phase 35: Western Emergency Break-Glass & Acute Critical Care Transfer Models (NABH COP.6)
=========================================================================================
Defines schemas for:
1. Acute physiological deterioration and emergency break-glass triggers
2. Standardized bilingual SBAR (Situation, Background, Assessment, Recommendation) handover
3. Critical care transfer logistics (Ambulance dispatch, allopathic ICU reception)
4. State lockdown enforcement and governance audit records
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EmergencyTriggerReason(str, Enum):
    """Cardinal physiological red flags mandating immediate NABH COP.6 break-glass transfer."""
    CARDIOGENIC_SHOCK = "CARDIOGENIC_SHOCK"            # SBP < 90 mmHg, pulse > 120 bpm, cold clammy extremities
    SEVERE_HYPOXIA = "SEVERE_HYPOXIA"                  # SpO2 < 90% on ambient air, RR > 30/min, central cyanosis
    ACUTE_CORONARY_SYNDROME = "ACUTE_CORONARY_SYNDROME" # Crushing chest pain, ST-deviation suspicion
    ACUTE_ABDOMEN_PERITONITIS = "ACUTE_ABDOMEN_PERITONITIS" # Board-like rigidity, rebound tenderness
    NEUROLOGICAL_COLLAPSE = "NEUROLOGICAL_COLLAPSE"    # GCS < 9, sudden acute hemiplegia, status epilepticus
    ANAPHYLACTIC_SHOCK = "ANAPHYLACTIC_SHOCK"          # Acute laryngeal stridor, angioedema, circulatory collapse
    MASSIVE_HEMORRHAGE = "MASSIVE_HEMORRHAGE"          # Uncontrolled severe hemorrhage / hemodynamic compromise


class BreakGlassStatus(str, Enum):
    """Lifecycle status of the emergency break-glass event."""
    BREAK_GLASS_TRIGGERED = "BREAK_GLASS_TRIGGERED"
    TRANSFER_IN_PROGRESS = "TRANSFER_IN_PROGRESS"
    TRANSFERRED_TO_ICU = "TRANSFERRED_TO_ICU"
    RESOLVED_STABILIZED = "RESOLVED_STABILIZED"
    CANCELLED = "CANCELLED"


class News2TriageEvaluation(BaseModel):
    """National Early Warning Score 2 (NEWS2) validation for adults >= 16 years."""
    respiratory_rate_score: int
    spo2_score: int
    systolic_bp_score: int
    heart_rate_score: int
    consciousness_score: int
    temperature_score: int
    total_score: int
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    is_emergency_trigger: bool  # Total >= 7 OR single parameter 3


class PewsTriageEvaluation(BaseModel):
    """Pediatric Early Warning Score (PEWS) validation for children < 16 years."""
    behavior_score: int
    cardiovascular_score: int
    respiratory_score: int
    total_score: int
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    is_emergency_trigger: bool  # Total >= 5 OR single parameter 3


class VitalSignsTelemetry(BaseModel):
    """Real-time physiological telemetry triggering break-glass threshold."""
    systolic_bp: int = Field(..., ge=40, le=260, description="Systolic Blood Pressure mmHg")
    diastolic_bp: int = Field(..., ge=20, le=160, description="Diastolic Blood Pressure mmHg")
    heart_rate_bpm: int = Field(..., ge=20, le=240, description="Heart rate / pulse in bpm")
    respiratory_rate_bpm: int = Field(..., ge=5, le=60, description="Respiratory rate in breaths/min")
    spo2_percentage: float = Field(..., ge=40.0, le=100.0, description="Pulse oximetry oxygen saturation")
    glasgow_coma_scale: int = Field(..., ge=3, le=15, description="Glasgow Coma Scale total score")
    temperature_fahrenheit: float = Field(default=98.6, ge=90.0, le=108.0)
    patient_age_years: Optional[int] = None
    news2_score: Optional[int] = None
    pews_score: Optional[int] = None
    triage_risk_level: Optional[str] = None


class SbarHandoverReport(BaseModel):
    """Standardized NABH COP.6 SBAR (Situation, Background, Assessment, Recommendation) Handover."""
    situation_english: str
    situation_hindi: str
    background_ayurvedic_course: str
    assessment_vitals: VitalSignsTelemetry
    assessment_acute_syndrome: str
    recommendation_allopathic_resuscitation: List[str]
    transferring_facility: str
    attending_ayush_physician_arn: str
    generated_at: int


class EmergencyBreakGlassRequest(BaseModel):
    """Request to initiate emergency break-glass protocol and trigger transfer."""
    patient_id: str
    hospital_id: str
    trigger_reason: EmergencyTriggerReason
    vitals: VitalSignsTelemetry
    initiating_user_id: str
    initiating_role: str
    physician_arn: Optional[str] = None
    emergency_icu_destination: str = "AIIMS New Delhi Critical Care Emergency Medicine Unit"
    clinical_narrative: Optional[str] = None


class EmergencyBreakGlassResponse(BaseModel):
    """Authoritative Emergency Break-Glass Record and Handover Dossier."""
    event_id: str
    patient_id: str
    hospital_id: str
    trigger_reason: EmergencyTriggerReason
    vitals: VitalSignsTelemetry
    initiating_user_id: str
    initiating_role: str
    physician_arn: Optional[str]
    state_lockdown_enforced: bool
    sbar_handover: SbarHandoverReport
    emergency_icu_destination: str
    status: BreakGlassStatus
    created_at: int


class CriticalCareTransferRequest(BaseModel):
    """Record dispatch of advanced cardiac life support ambulance and allopathic ICU reception."""
    event_id: str
    allopathic_physician_notified: str
    receiving_hospital_name: str
    receiving_doctor_name: str
    handover_signed_by_arn: str
    paramedic_unit_code: str = "ALS-AMBULANCE-DELHI-01"
    clinical_notes: Optional[str] = None


class CriticalCareTransferResponse(BaseModel):
    """Authoritative transfer execution record under NABH COP.6."""
    transfer_id: str
    event_id: str
    patient_id: str
    hospital_id: str
    ambulance_service_called: bool
    paramedic_call_timestamp: int
    allopathic_physician_notified: str
    medical_superintendent_alerted: bool
    handover_signed_by_arn: str
    receiving_hospital_name: str
    receiving_doctor_name: str
    transfer_completed_at: Optional[int]
    clinical_notes: Optional[str]
    created_at: int
