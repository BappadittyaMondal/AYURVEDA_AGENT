"""
Phase 36: Real-Time Herb-Drug & Herb-Herb Interaction (HDI/HHI) Models (28-Point Matrix)
========================================================================================
Defines schemas for:
1. 28-point pharmacological cross-reactive rules catalog
2. Severity classification (Contraindicated, Major, Moderate, Minor)
3. Real-time prescription interception and cross-checking requests
4. Registered Physician override governance with NCISM ARN
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class HdiSeverity(str, Enum):
    """Clinical severity grading for herb-drug interactions."""
    CONTRAINDICATED_CRITICAL = "CONTRAINDICATED_CRITICAL"   # Co-administration absolutely forbidden
    MAJOR_MONITORING_REQUIRED = "MAJOR_MONITORING_REQUIRED" # High risk; strict therapeutic drug monitoring mandatory
    MODERATE_CAUTION = "MODERATE_CAUTION"                   # Caution; timing separation or dose titration advised
    MINOR_INFORMATIONAL = "MINOR_INFORMATIONAL"             # Minimal clinical significance


class InteractionMechanism(str, Enum):
    """Pharmacokinetic and pharmacodynamic mechanism taxonomy."""
    CYP450_INHIBITION = "CYP450_INHIBITION"
    CYP450_INDUCTION = "CYP450_INDUCTION"
    P_GLYCOPROTEIN_MODULATION = "P_GLYCOPROTEIN_MODULATION"
    SYNERGISTIC_ANTICOAGULATION = "SYNERGISTIC_ANTICOAGULATION"
    SYNERGISTIC_HYPOGLYCEMIA = "SYNERGISTIC_HYPOGLYCEMIA"
    SYNERGISTIC_CNS_DEPRESSION = "SYNERGISTIC_CNS_DEPRESSION"
    SYNERGISTIC_HYPOTENSION = "SYNERGISTIC_HYPOTENSION"
    ELECTROLYTE_DEPLETION = "ELECTROLYTE_DEPLETION"
    IMMUNOMODULATORY_ANTAGONISM = "IMMUNOMODULATORY_ANTAGONISM"


class HdiRule(BaseModel):
    """Evidence-based cross-reactive rule definition."""
    rule_id: str
    ayurvedic_herb_or_formulation: str
    allopathic_drug_or_class: str
    mechanism_of_interaction: InteractionMechanism
    clinical_severity: HdiSeverity
    potential_adverse_effects: str
    evidence_grade: str
    recommended_clinical_action: str
    reference_citations: str


class HdiCrossCheckRequest(BaseModel):
    """Real-time payload to screen proposed Ayurvedic herbs against patient's active drug regimen."""
    patient_id: str
    hospital_id: str
    prescribed_ayurvedic_herbs: List[str] = Field(..., min_length=1)
    current_allopathic_medications: List[str] = Field(default_factory=list)
    attending_physician_arn: str


class InterceptedInteraction(BaseModel):
    """Detected clinical conflict between herb and drug."""
    rule_id: str
    herb: str
    drug: str
    severity: HdiSeverity
    mechanism: InteractionMechanism
    adverse_effects: str
    recommended_action: str
    reference_citations: str


class HdiCrossCheckResponse(BaseModel):
    """Real-time prescription safety evaluation verdict."""
    patient_id: str
    hospital_id: str
    is_safe_to_prescribe: bool
    total_conflicts_detected: int
    critical_blocks: List[InterceptedInteraction]
    warnings_for_monitoring: List[InterceptedInteraction]
    clinical_guidance: List[str]
    evaluated_at: int


class HdiOverrideRequest(BaseModel):
    """Statutory physician override for non-critical or critically justified combinations."""
    patient_id: str
    hospital_id: str
    rule_id: str
    prescribed_herb: str
    concurrent_drug: str
    physician_arn: str
    clinical_justification: str
