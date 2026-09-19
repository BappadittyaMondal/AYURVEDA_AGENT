"""
models/ayush_grid.py - Data models for Phase 42: Ayush Grid Bridge & Zero-Knowledge Verification.
Tables 90 & 91: ayush_grid_bridge_logs, zero_knowledge_proof_records.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class AbdmBundleType(str, Enum):
    OP_CONSULTATION_NOTE = "OP_CONSULTATION_NOTE"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    DIAGNOSTIC_REPORT = "DIAGNOSTIC_REPORT"
    PRESCRIPTION = "PRESCRIPTION"


class AyushGridStatus(str, Enum):
    QUEUED = "QUEUED"
    DISPATCHED = "DISPATCHED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FAILED = "FAILED"


class FhirBundleDispatchReq(BaseModel):
    hospital_id: str
    patient_id: str
    abdm_bundle_type: AbdmBundleType
    clinical_data: Dict[str, Any] = Field(..., description="Ayurvedic clinical observations and diagnostic codes")


class FhirBundleRecord(BaseModel):
    bridge_id: str
    hospital_id: str
    patient_id: str
    abdm_bundle_type: AbdmBundleType
    fhir_bundle: Dict[str, Any]
    status: AyushGridStatus
    dispatch_timestamp: int
    ack_reference: Optional[str]


class ZkProofGenerateReq(BaseModel):
    hospital_id: str
    patient_id: str
    clinical_attribute: str = Field(..., description="Attribute to prove (e.g. PRAKRITI_VATA_PITTA, TREATMENT_COMPLETE)")
    secret_salt: str = Field(..., min_length=8, description="Client/Patient secret salt for blinding commitment")
    verifier_arn: str = Field(..., description="Attending NCISM practitioner ARN certifying the proof")


class ZkProofRecord(BaseModel):
    proof_id: str
    hospital_id: str
    patient_id: str
    clinical_attribute: str
    commitment_hash: str
    zk_proof_payload: str
    verifier_arn: str
    is_verified: bool
    generated_at: int


class ZkProofVerifyReq(BaseModel):
    proof_id: str
    revealed_attribute: str
    revealed_secret_salt: str
    patient_id: str
