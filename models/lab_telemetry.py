"""
models/lab_telemetry.py - Structured Clinical Laboratory Telemetry Models.
Supports standard panels (Metabolic, Renal, Hepatic, Hematologic, Inflammatory)
with strict Ayurvedic physiological correlation and clinical governance alert severity.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LabAlertSeverity(str, Enum):
    NORMAL = "NORMAL"
    LOW = "LOW"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class LabAlert(BaseModel):
    """Clinical laboratory threshold violation alert."""
    analyte: str = Field(..., description="Analyte or laboratory parameter name")
    measured_value: float = Field(..., description="Quantified laboratory measurement")
    unit: str = Field(..., description="Measurement unit (e.g. mg/dL, mL/min/1.73m2, U/L)")
    reference_range: str = Field(..., description="Biological reference interval")
    severity: LabAlertSeverity = Field(..., description="Alert severity classification")
    clinical_implication: str = Field(..., description="Evidence-based clinical explanation")


class ComprehensiveLabTelemetry(BaseModel):
    """
    Structured laboratory telemetry payload across vital physiological panels.
    Correlated with Ayurvedic Srotas and Dhatvagni dynamics.
    """
    telemetry_id: Optional[str] = Field(default=None, description="Unique telemetry assessment identifier")
    patient_id: str = Field(..., description="Patient hospital registration identifier")
    hospital_id: str = Field(..., description="Originating hospital or diagnostic clinic ID")
    timestamp: int = Field(..., description="Epoch timestamp of sample acquisition")

    # Glycemic & Metabolic Panel (Medovaha Srotas / Prameha)
    fasting_blood_glucose_mg_dl: Optional[float] = Field(default=None, ge=10.0, le=1000.0)
    postprandial_blood_glucose_mg_dl: Optional[float] = Field(default=None, ge=10.0, le=1000.0)
    hba1c_percent: Optional[float] = Field(default=None, ge=3.0, le=20.0)

    # Renal Panel (Mutravaha Srotas / Vrikka)
    serum_creatinine_mg_dl: Optional[float] = Field(default=None, ge=0.1, le=25.0)
    egfr_ml_min_1_73m2: Optional[float] = Field(default=None, ge=1.0, le=200.0)
    blood_urea_nitrogen_mg_dl: Optional[float] = Field(default=None, ge=1.0, le=200.0)

    # Hepatic Panel (Raktavaha Srotas / Yakrit / Kamala)
    ast_sgot_u_l: Optional[float] = Field(default=None, ge=1.0, le=5000.0)
    alt_sgpt_u_l: Optional[float] = Field(default=None, ge=1.0, le=5000.0)
    alkaline_phosphatase_u_l: Optional[float] = Field(default=None, ge=5.0, le=3000.0)
    total_bilirubin_mg_dl: Optional[float] = Field(default=None, ge=0.1, le=50.0)
    serum_albumin_g_dl: Optional[float] = Field(default=None, ge=0.5, le=8.0)

    # Hematology & Coagulation (Rakta Dhatu / Srotas)
    hemoglobin_g_dl: Optional[float] = Field(default=None, ge=1.0, le=25.0)
    total_leukocyte_count_per_ul: Optional[float] = Field(default=None, ge=500.0, le=150000.0)
    platelet_count_per_ul: Optional[float] = Field(default=None, ge=5000.0, le=1500000.0)

    # Inflammatory Biomarkers (Ama / Sama Avastha / Vidaha)
    esr_mm_1st_hr: Optional[float] = Field(default=None, ge=0.0, le=150.0)
    hs_crp_mg_l: Optional[float] = Field(default=None, ge=0.0, le=200.0)
    serum_uric_acid_mg_dl: Optional[float] = Field(default=None, ge=0.5, le=25.0)


class LabTelemetryEvaluationResult(BaseModel):
    """Evaluation summary containing detected alerts, organ warnings, and safety flags."""
    telemetry_id: str
    patient_id: str
    timestamp: int
    alerts: List[LabAlert]
    has_critical_alerts: bool
    ayurvedic_organ_compromise_warnings: List[str]
    clinical_governance_flags: List[str]
