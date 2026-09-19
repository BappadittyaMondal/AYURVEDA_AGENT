"""
models/ipd_management.py - Data models for Phase 46: IPD Inpatient Bed Management & Nursing Charting.
Tables 98 & 99: ipd_bed_allocations, panchakarma_daily_nursing_charts.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class IpdBedStatus(str, Enum):
    OCCUPIED = "OCCUPIED"
    DISCHARGED = "DISCHARGED"
    TRANSFERRED = "TRANSFERRED"


class BedAllocationCreate(BaseModel):
    patient_id: str = Field(..., description="Master Patient Index ID")
    hospital_id: str = Field(..., description="Hospital UUID")
    ward_name: str = Field(..., description="Inpatient ward name (e.g. KAYACHIKITSA_MALE_WARD, PANCHAKARMA_DELUXE)")
    bed_number: str = Field(..., description="Assigned bed identifier (e.g. BED-104)")
    attending_rmp_arn: str = Field(..., description="Attending NCISM Physician ARN")


class BedAllocationRecord(BaseModel):
    allocation_id: str
    patient_id: str
    hospital_id: str
    ward_name: str
    bed_number: str
    admission_timestamp: int
    discharge_timestamp: Optional[int]
    status: IpdBedStatus
    attending_rmp_arn: str


class NursingChartCreate(BaseModel):
    allocation_id: str = Field(..., description="Active IPD bed allocation ID")
    patient_id: str
    vital_bp_systolic: int = Field(..., ge=60, le=260, description="Systolic BP mmHg")
    vital_bp_diastolic: int = Field(..., ge=30, le=160, description="Diastolic BP mmHg")
    vital_pulse_bpm: int = Field(..., ge=30, le=220, description="Pulse rate bpm")
    panchakarma_therapy_administered: str = Field(..., description="Therapy administered during round (e.g. Abhyanga + Nadi Sweda, Virechana Vega)")
    vega_count: int = Field(0, ge=0, le=50, description="Number of therapeutic Vega (evacuations/bouts)")
    jeerna_ahara_lakshana: Optional[str] = Field(None, description="Signs of digestion: Udgara Shuddhi, Utsaha, Laghava, Kshut-pipasa")
    nursing_notes: Optional[str] = Field(None, description="Clinical observations and precautions")
    nurse_name: str = Field(..., min_length=2, description="Staff Nurse / Therapist Name")


class NursingChartRecord(BaseModel):
    chart_id: str
    allocation_id: str
    patient_id: str
    vital_bp_systolic: int
    vital_bp_diastolic: int
    vital_pulse_bpm: int
    panchakarma_therapy_administered: str
    vega_count: int
    jeerna_ahara_lakshana: Optional[str]
    nursing_notes: Optional[str]
    nurse_name: str
    charted_at: int
