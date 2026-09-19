"""
Morbidity Dual-Coding & Classical Taxonomy Models
================================================
Implements schemas for crosswalk mapping between:
1. Classical Ayurvedic Disease Nosology (Ashtodara Shata)
2. India Ministry of AYUSH NAMASTE Portal Morbidity Terminology
3. WHO ICD-11 Traditional Medicine Module 2 (Ayurveda)
4. WHO ICD-11 Biomedicine Classification
5. WHO ICD-10 Benchmark Mapping
6. ABDM / HL7 FHIR Condition Resource Schema
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    PROVISIONAL = "PROVISIONAL"
    DIFFERENTIAL_CONFIRMED = "DIFFERENTIAL_CONFIRMED"
    REFUTED = "REFUTED"
    ENTERED_IN_ERROR = "ENTERED_IN_ERROR"


class DoshicCategory(str, Enum):
    VATAJA = "VATAJA"
    PITTAJA = "PITTAJA"
    KAPHAJA = "KAPHAJA"
    SANNIPATAJA = "SANNIPATAJA"
    DVANDVAJA = "DVANDVAJA"
    AGANTUJA = "AGANTUJA"


class MorbidityCrosswalkEntry(BaseModel):
    """Complete multi-system classification crosswalk for a single clinical entity."""
    disease_code: str = Field(..., description="Internal canonical disease code")
    sanskrit_name: str = Field(..., description="Classical Sanskrit nomenclature in Devanagari")
    english_name: str = Field(..., description="Standardized English clinical nomenclature")
    namaste_code: str = Field(..., description="Ministry of AYUSH NAMASTE portal standardized code")
    icd11_tm2_code: str = Field(..., description="WHO ICD-11 Traditional Medicine Chapter Module 2 code")
    icd11_biomed_code: str = Field(..., description="WHO ICD-11 Biomedicine diagnostic code")
    icd10_code: str = Field(..., description="Legacy WHO ICD-10 diagnostic code")
    doshic_category: DoshicCategory = Field(..., description="Primary classical Doshic classification")
    classical_text_source: str = Field(..., description="Classical treatise reference (Samhita and Chapter)")


class PatientDiagnosisCodingInput(BaseModel):
    """Payload to assign a verified dual-coded diagnosis to an EHR patient."""
    patient_id: str
    disease_code: str = Field(..., description="Target disease code from registry")
    clinical_notes: Optional[str] = Field(default=None, description="Clinical reasoning and diagnostic observations")
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.DIFFERENTIAL_CONFIRMED,
        description="Clinical diagnostic certainty"
    )


class FHIRCoding(BaseModel):
    system: str
    code: str
    display: str


class FHIRCodeableConcept(BaseModel):
    coding: List[FHIRCoding]
    text: str


class FHIRConditionResource(BaseModel):
    """ABDM / HL7 FHIR R4 compliant Condition resource representation."""
    resourceType: str = "Condition"
    id: str
    clinicalStatus: Dict[str, Any]
    verificationStatus: Dict[str, Any]
    code: FHIRCodeableConcept
    subject: Dict[str, str]
    recordedDate: str
    recorder: Dict[str, str]
    note: Optional[List[Dict[str, str]]] = None


class PatientDiagnosisCodingOutput(BaseModel):
    """EHR recorded diagnosis with full crosswalk and generated FHIR resource."""
    coding_id: str
    patient_id: str
    hospital_id: str
    diagnosing_arn: str
    disease_crosswalk: MorbidityCrosswalkEntry
    verification_status: VerificationStatus
    clinical_notes: Optional[str] = None
    fhir_condition: Dict[str, Any]
    timestamp: int
