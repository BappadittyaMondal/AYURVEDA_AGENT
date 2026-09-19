"""
models/opd_queue.py - Data models for Phase 47: OPD Queue Optimization & Token Flow Management.
Tables 100 & 101: opd_token_queues, consultation_time_audits.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class PriorityTier(str, Enum):
    EMERGENCY_TIVRA = "EMERGENCY_TIVRA"
    SENIOR_CITIZEN_GERIATRIC = "SENIOR_CITIZEN_GERIATRIC"
    PEDIATRIC_BALA = "PEDIATRIC_BALA"
    ROUTINE_SAMANYA = "ROUTINE_SAMANYA"


class TokenStatus(str, Enum):
    WAITING = "WAITING"
    IN_CONSULTATION = "IN_CONSULTATION"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"


class OpdTokenCreate(BaseModel):
    hospital_id: str
    patient_id: str
    department: str = Field(..., description="Target OPD Department (KAYACHIKITSA, SHALYA, SHALAKYA, PRASUTI, KAUMARBHRITYA)")
    priority_tier: PriorityTier = Field(PriorityTier.ROUTINE_SAMANYA, description="Triage urgency level")


class OpdTokenRecord(BaseModel):
    token_id: str
    hospital_id: str
    patient_id: str
    department: str
    token_number: int
    priority_tier: PriorityTier
    status: TokenStatus
    estimated_wait_minutes: int
    issued_at: int


class ConsultationAuditRecord(BaseModel):
    audit_id: str
    token_id: str
    physician_arn: str
    consultation_start_timestamp: int
    consultation_end_timestamp: Optional[int]
    duration_seconds: Optional[int]
    efficiency_rating: Optional[float]


class OpdDepartmentQueueStatus(BaseModel):
    department: str
    total_waiting: int
    in_consultation_count: int
    current_token_being_served: Optional[int]
    average_wait_minutes: int
    active_tokens: List[OpdTokenRecord]
