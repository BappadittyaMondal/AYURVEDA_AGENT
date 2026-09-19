"""
Phase 38: Tele-AYUSH Remote Consultation & Digital e-Prescription Models
========================================================================
Defines schemas for:
1. MoHFW Telemedicine Practice Guidelines compliant remote consultations
2. Tamper-evident cryptographic QR-code verified e-prescriptions
3. Statutory practitioner ARN verification and pharmacy dispensation tracking
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TeleConsultationType(str, Enum):
    AUDIO_ONLY = "AUDIO_ONLY"
    VIDEO_CONFERENCE = "VIDEO_CONFERENCE"


class TeleSessionStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class DispensationStatus(str, Enum):
    ISSUED = "ISSUED"
    DISPENSED = "DISPENSED"
    EXPIRED = "EXPIRED"


class PrescribedItem(BaseModel):
    formulation_name: str
    dosage: str
    timing: str
    anupana: str
    duration_days: int = 14


class TeleConsultationCreate(BaseModel):
    patient_id: str
    hospital_id: str
    physician_arn: str
    scheduled_timestamp: int
    call_type: TeleConsultationType = TeleConsultationType.VIDEO_CONFERENCE
    clinical_notes: Optional[str] = None


class TeleConsultationResponse(BaseModel):
    session_id: str
    patient_id: str
    hospital_id: str
    physician_arn: str
    scheduled_timestamp: int
    started_timestamp: Optional[int] = None
    ended_timestamp: Optional[int] = None
    session_status: TeleSessionStatus
    call_type: TeleConsultationType
    clinical_notes: Optional[str]
    created_at: int


class DigitalPrescriptionCreate(BaseModel):
    session_id: str
    patient_id: str
    hospital_id: str
    physician_arn: str
    formulations: List[PrescribedItem] = Field(..., min_length=1)
    pathya_diet_instructions: str


class DigitalPrescriptionResponse(BaseModel):
    prescription_id: str
    session_id: str
    patient_id: str
    hospital_id: str
    physician_arn: str
    formulations: List[PrescribedItem]
    pathya_diet_instructions: str
    verification_hash: str
    qr_code_payload: str
    dispensation_status: DispensationStatus
    issued_at: int


class PrescriptionVerificationResponse(BaseModel):
    is_authentic: bool
    prescription_id: str
    physician_arn: str
    patient_id: str
    issued_at: int
    dispensation_status: DispensationStatus
