"""
models/pharmacovigilance.py - Data models for Phase 44: Pharmacovigilance & NPvCC Gateway.
Tables 94 & 95: adr_pharmacovigilance_reports, suspected_formulation_lots.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class CausalityCategory(str, Enum):
    CERTAIN = "CERTAIN"
    PROBABLE = "PROBABLE"
    POSSIBLE = "POSSIBLE"
    UNLIKELY = "UNLIKELY"


class NpvccStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"


class NaranjoAsuQuestions(BaseModel):
    previous_conclusive_reports: bool = Field(False, description="Q1: Are there previous conclusive reports on this reaction?")
    onset_after_drug: bool = Field(True, description="Q2: Did adverse event appear after suspected formulation was administered?")
    dechallenge_improvement: bool = Field(False, description="Q3: Did adverse reaction improve when formulation was discontinued?")
    rechallenge_recurrence: bool = Field(False, description="Q4: Did adverse reaction reappear when formulation was readministered?")
    alternative_causes_absent: bool = Field(True, description="Q5: Were there no alternative causes (e.g. concurrent modern drug or disease progression)?")
    toxic_concentration_or_heavy_metal: bool = Field(False, description="Q6: Does formulation contain Schedule E1 minerals or heavy metals beyond Pharmacopoeial limits?")
    dose_response_gradient: bool = Field(False, description="Q7: Was reaction more severe when dose was increased?")
    past_history_similar: bool = Field(False, description="Q8: Did patient have similar reaction to identical/related herbal compound in the past?")
    objective_laboratory_evidence: bool = Field(False, description="Q9: Was the adverse event confirmed by objective diagnostic evidence (LFT/RFT/biopsy)?")


class SuspectedLotCreate(BaseModel):
    formulation_name: str
    manufacturer_name: str
    mfg_license_number: str
    expiry_date: Optional[str] = None
    chemical_heavy_metal_audit_notes: Optional[str] = None


class SuspectedLotRecord(BaseModel):
    lot_id: str
    report_id: str
    formulation_name: str
    manufacturer_name: str
    mfg_license_number: str
    expiry_date: Optional[str]
    chemical_heavy_metal_audit_notes: Optional[str]
    created_at: int


class AdrReportCreate(BaseModel):
    patient_id: str
    hospital_id: str
    suspected_formulation: str
    batch_number: Optional[str] = None
    adverse_reaction_description: str
    onset_latency_hours: Optional[float] = None
    naranjo_questions: NaranjoAsuQuestions
    action_taken: str
    reporting_rmp_arn: str
    suspected_lot_details: Optional[SuspectedLotCreate] = None


class AdrReportRecord(BaseModel):
    report_id: str
    patient_id: str
    hospital_id: str
    suspected_formulation: str
    batch_number: Optional[str]
    adverse_reaction_description: str
    onset_latency_hours: Optional[float]
    naranjo_asu_score: int
    causality_category: CausalityCategory
    action_taken: str
    reporting_rmp_arn: str
    npvcc_submission_status: NpvccStatus
    suspected_lot: Optional[SuspectedLotRecord]
    reported_at: int


class NpvccYellowCardExport(BaseModel):
    report_id: str
    reporting_centre: str
    patient_identifier_hash: str
    suspected_formulation: str
    reaction_terms: List[str]
    naranjo_score: int
    causality: CausalityCategory
    submission_timestamp_utc: str
    xml_payload_preview: str
