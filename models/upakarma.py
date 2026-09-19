"""
Upakarma & Bahya Parimarjana Therapy Models
===========================================
Defines schemas for:
1. Bahya Parimarjana external therapy modalities (Abhyanga, Swedana, Shirodhara, Pinda Sweda, Takradhara, Lepa, Basti rings, Udvartana)
2. Thermodynamic temperature ranges and maximum safe burn limits
3. Hydrokinetic flow dynamics (suspension height, flow rate, stream continuity)
4. Lepa layer thickness and moisture retention criteria
5. Clinical pre-session screening and safety clearance
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class UpakarmaModality(str, Enum):
    ABHYANGA = "ABHYANGA"                              # Full-body rhythmic medicated oil application
    SWEDANA_BASHPA = "SWEDANA_BASHPA"                  # Full-body herbal steam cabin sudation
    SWEDANA_NADI = "SWEDANA_NADI"                      # Localized tube steam fomentation
    SHIRODHARA_TAILA = "SHIRODHARA_TAILA"              # Continuous warm herbal oil stream over forehead
    TAKRADHARA = "TAKRADHARA"                          # Continuous cool medicated buttermilk stream over forehead
    PATRA_PINDA_SWEDA = "PATRA_PINDA_SWEDA"            # Herbal leaf bolus fomentation (Elakizhi)
    SHASHTIKA_SHALI_PINDA_SWEDA = "SHASHTIKA_SHALI_PINDA_SWEDA"  # Rice-milk bolus fomentation (Navarakizhi)
    CHURNA_PINDA_SWEDA = "CHURNA_PINDA_SWEDA"          # Valuka/Powder dry bolus (Podi Kizhi)
    KATI_BASTI = "KATI_BASTI"                          # Lumbosacral medicated warm oil reservoir
    JANU_BASTI = "JANU_BASTI"                          # Knee joint medicated warm oil reservoir
    GREEVA_BASTI = "GREEVA_BASTI"                      # Cervical spine medicated warm oil reservoir
    LEPA_PRALEPA = "LEPA_PRALEPA"                      # Cool thin paste application
    LEPA_PRADEHA = "LEPA_PRADEHA"                      # Warm thick paste application
    UDVARTANA = "UDVARTANA"                            # Medicated dry powder upward friction rubbing


class UpakarmaTherapy(BaseModel):
    """Registered Bahya Parimarjana therapy catalog profile."""
    therapy_id: str = Field(..., description="Unique therapy identifier")
    sanskrit_name: str = Field(..., description="Classical Sanskrit nomenclature")
    modality_code: UpakarmaModality = Field(..., description="Standard modality enum code")
    target_temperature_min_c: float = Field(..., ge=15.0, le=60.0, description="Minimum therapeutic operating temperature Celsius")
    target_temperature_max_c: float = Field(..., ge=15.0, le=60.0, description="Maximum therapeutic operating temperature Celsius")
    max_safe_temperature_c: float = Field(..., ge=15.0, le=60.0, description="Absolute burn safety ceiling temperature Celsius")
    standard_duration_minutes: int = Field(..., ge=5, le=180, description="Standard protocol duration in minutes")
    recommended_media: List[str] = Field(..., description="Classical oils, decoctions, milks, or powders utilized")
    cardinal_indications: List[str] = Field(..., description="Key clinical conditions indicated")
    contraindications: List[str] = Field(..., description="Strict clinical contraindications")
    doshic_affinity: str = Field(..., description="Primary Doshic pacification action")


class UpakarmaSessionCreate(BaseModel):
    """Clinical request to log an administered Upakarma session."""
    patient_id: str = Field(..., description="Patient identifier")
    therapy_id: str = Field(..., description="Catalog therapy identifier")
    medium_used: str = Field(..., description="Specific oil, herbal decoction, or paste applied")
    operating_temperature_c: float = Field(..., ge=15.0, le=65.0, description="Measured application temperature Celsius")
    duration_minutes: int = Field(..., ge=5, le=180, description="Actual session duration in minutes")
    flow_rate_ml_sec: Optional[float] = Field(None, ge=0.0, le=100.0, description="Flow rate in mL/sec for Shirodhara/Takradhara")
    height_cm: Optional[float] = Field(None, ge=1.0, le=50.0, description="Stream suspension height above forehead in cm")
    lepa_thickness_mm: Optional[float] = Field(None, ge=0.5, le=20.0, description="Applied paste thickness in mm for Lepa")
    pre_vitals_bp: str = Field(..., description="Pre-treatment Blood Pressure (e.g. 120/80)")
    post_vitals_bp: str = Field(..., description="Post-treatment Blood Pressure (e.g. 118/78)")
    therapist_id: str = Field(..., description="Licensed Panchakarma technician / therapist ID")
    clinical_notes: Optional[str] = Field(None, description="Observations, skin response, relaxation grade")


class UpakarmaSessionRecord(BaseModel):
    """Persisted Upakarma clinical session log."""
    session_id: str
    patient_id: str
    hospital_id: str
    therapy_id: str
    medium_used: str
    operating_temperature_c: float
    duration_minutes: int
    flow_rate_ml_sec: Optional[float] = None
    height_cm: Optional[float] = None
    lepa_thickness_mm: Optional[float] = None
    pre_vitals_bp: str
    post_vitals_bp: str
    therapist_id: str
    adverse_events: List[str]
    clinical_notes: Optional[str] = None
    created_at: int


class PreSessionScreeningRequest(BaseModel):
    """Pre-treatment thermodynamic and clinical contraindication validation check."""
    patient_id: str = Field(..., description="Patient identifier")
    therapy_id: str = Field(..., description="Therapy ID to be validated")
    proposed_temperature_c: float = Field(..., description="Proposed delivery temperature Celsius")
    patient_conditions: List[str] = Field(default=[], description="Active patient diagnoses or states")
    pre_op_agi_score: Optional[float] = Field(None, ge=0.0, le=3.0, description="Current AGI score if available")


class PreSessionScreeningResponse(BaseModel):
    """Screening verdict and clinical guidance."""
    patient_id: str
    therapy_id: str
    is_safe_to_proceed: bool
    temperature_compliance: str = Field(..., description="COMPLIANT, SUB_THERAPEUTIC, or EXCESSIVE_RISK_OF_BURNS")
    contraindication_flags: List[str]
    clinical_recommendation: str
