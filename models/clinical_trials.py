"""
models/clinical_trials.py - Data models for Phase 45: Clinical Trial Registry & Integrative Research (CTRI).
Tables 96 & 97: clinical_trial_protocols, trial_cohort_subjects.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class TrialStatus(str, Enum):
    PROPOSED = "PROPOSED"
    RECRUITING = "RECRUITING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    TERMINATED = "TERMINATED"


class ProtocolCreate(BaseModel):
    ctri_registration_number: str = Field(..., description="Official CTRI Identifier (e.g. CTRI/2026/03/089123)")
    trial_title: str = Field(..., min_length=5, description="Full scientific title of clinical study")
    ayurvedic_intervention_arm: str = Field(..., description="Details of Ayurvedic intervention formulation/protocol")
    control_arm: str = Field(..., description="Control intervention (Standard of Care, Placebo, or Active Comparator)")
    sample_size_target: int = Field(..., ge=10, le=50000, description="Target enrolled subject count")
    primary_outcome_measure: str = Field(..., description="Validated outcome scale (WOMAC, VAS, HbA1c, DAS28)")
    principal_investigator_arn: str = Field(..., description="NCISM ARN of Principal Investigator")


class ProtocolRecord(BaseModel):
    protocol_id: str
    ctri_registration_number: str
    trial_title: str
    ayurvedic_intervention_arm: str
    control_arm: str
    sample_size_target: int
    primary_outcome_measure: str
    principal_investigator_arn: str
    status: TrialStatus
    created_at: int


class SubjectEnrollmentCreate(BaseModel):
    protocol_id: str
    patient_id: str
    assigned_arm: str = Field(..., description="'INTERVENTION' or 'CONTROL'")
    baseline_prakriti: str = Field(..., description="Doshic constitution at baseline")
    baseline_score: float = Field(..., description="Initial primary outcome score")


class SubjectRecord(BaseModel):
    subject_id: str
    protocol_id: str
    patient_id: str
    assigned_arm: str
    baseline_prakriti: str
    baseline_score: float
    current_score: float
    compliance_rate_pct: float
    enrolled_at: int


class SubjectProgressUpdate(BaseModel):
    current_score: float
    compliance_rate_pct: float = Field(..., ge=0.0, le=100.0)


class TrialAnalyticsSummary(BaseModel):
    protocol_id: str
    trial_title: str
    status: TrialStatus
    total_enrolled: int
    intervention_count: int
    control_count: int
    mean_baseline_score_intervention: float
    mean_current_score_intervention: float
    mean_delta_improvement_intervention: float
    mean_delta_improvement_control: float
    cohens_d_effect_size: float
    overall_compliance_rate_pct: float
