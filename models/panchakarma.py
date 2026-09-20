"""
Clinical Panchakarma Protocol & Bedside Vega Tracking Models
===========================================================
Defines schemas for:
1. Panchakarma procedures (Vamana, Virechana, Basti, Nasya, Raktamokshana)
2. Purva Karma Snehapana & Swedana milestones
3. Bedside real-time Vega tracking (bout counts, volume, content, vitals)
4. Chaturvidha Shuddhi Pariksha (Vaigiki, Maniki, Antiki, Laingiki)
5. Antiki terminal milestones (Pittanta for Vamana, Kaphanta for Virechana)
6. Samsarjana Krama dietary rehabilitation schedule
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PanchakarmaProcedure(str, Enum):
    VAMANA = "VAMANA"                      # Therapeutic Emesis (Kapha Shodhana)
    VIRECHANA = "VIRECHANA"                # Therapeutic Purgation (Pitta Shodhana)
    BASTI = "BASTI"                        # Medicated Enema Therapy (Vata Shodhana)
    NASYA = "NASYA"                        # Nasal Errhine Therapy (Urdhva Jatrugata)
    RAKTAMOKSHANA = "RAKTAMOKSHANA"        # Therapeutic Bloodletting (Rakta-Pitta Shodhana)


class PanchakarmaStage(str, Enum):
    PURVA_KARMA = "PURVA_KARMA"            # Preparatory: Deepana-Pachana, Snehapana, Swedana
    PRADHANA_KARMA = "PRADHANA_KARMA"      # Active Elimination: Medication intake & Vega logging
    PASCHAT_KARMA = "PASCHAT_KARMA"        # Rehabilitation: Samsarjana Krama & Parihara
    COMPLETED = "COMPLETED"                # Successfully discharged
    ABORTED = "ABORTED"                    # Terminated due to complication or clinical veto


class ShuddhiGrade(str, Enum):
    PRAVARA = "PRAVARA"                    # Superior / Maximum Shuddhi
    MADHYAMA = "MADHYAMA"                  # Moderate / Standard Shuddhi
    AVARA = "AVARA"                        # Minimum acceptable / Low Shuddhi
    AYOGA = "AYOGA"                        # Inadequate / Under-elimination
    ATIYOGA = "ATIYOGA"                    # Excessive / Dangerous hyper-elimination


class VegaContent(str, Enum):
    ANNA = "ANNA"                          # Ingested stomach content / digested food
    KAPHA = "KAPHA"                        # Viscous, frothy, white mucoid discharge
    PITTA = "PITTA"                        # Yellow, greenish bilious fluid
    PURISHA = "PURISHA"                    # Fecal matter / stool
    ASRA_BLOOD = "ASRA_BLOOD"              # Frank blood (Pathological Atiyoga sign)
    JALA = "JALA"                          # Clear watery liquid


class AntikiMilestone(str, Enum):
    PITTANTA = "PITTANTA"                  # Terminal bile expulsion (signals Vamana completion)
    KAPHANTA = "KAPHANTA"                  # Terminal mucus expulsion (signals Virechana completion)
    ANILANTA = "ANILANTA"                  # Terminal flatus/gas expulsion (Basti completion)
    ASRANTA = "ASRANTA"                    # Terminal bright clear blood clotting (Raktamokshana)
    RAKTANTA = "RAKTANTA"                  # Terminal pure blood (Dangerous Atiyoga complication)
    INCOMPLETE = "INCOMPLETE"              # Not yet attained or interrupted


class BedsideVegaEntry(BaseModel):
    """Bedside bout observation submitted by clinical nurse or attending physician."""
    plan_id: str = Field(..., description="Active Panchakarma plan identifier")
    bout_number: int = Field(..., ge=1, description="Sequential bout index (1st, 2nd, ...)")
    output_volume_ml: float = Field(..., ge=0.0, description="Measured expulsion volume in mL")
    dominant_content: VegaContent = Field(..., description="Visual macroscopic dominant content")
    vitals_bp_systolic: int = Field(..., ge=60, le=240, description="Systolic blood pressure mmHg")
    vitals_bp_diastolic: int = Field(..., ge=30, le=160, description="Diastolic blood pressure mmHg")
    vitals_pulse_bpm: int = Field(..., ge=30, le=220, description="Pulse heart rate in bpm")
    attending_nurse_id: str = Field(..., description="Staff/Nurse identifier recording observation")
    clinical_notes: Optional[str] = Field(None, description="Patient posture, nausea, sweating notes")


class BedsideVegaRecord(BaseModel):
    """Persisted bedside Vega observation."""
    vega_id: str
    plan_id: str
    patient_id: str
    bout_number: int
    time_recorded: int
    output_volume_ml: float
    dominant_content: VegaContent
    vitals_bp_systolic: int
    vitals_bp_diastolic: int
    vitals_pulse_bpm: int
    attending_nurse_id: str
    clinical_notes: Optional[str] = None


class PurvaKarmaData(BaseModel):
    """Preparatory therapy data (Deepana-Pachana and Snehapana)."""
    deepana_pachana_days: int = Field(..., ge=1, le=14, description="Days of Deepana-Pachana completed")
    snehapana_daily_doses_ml: List[float] = Field(..., min_length=1, max_length=7, description="Daily graduated unctuous doses in mL")
    samyak_snigdha_lakshanas_present: bool = Field(..., description="Presence of canonical Snehana signs (soft skin, oily stool, flatus ease)")
    swedana_completed: bool = Field(..., description="Completion of Sarvanga Swedana (sudation)")
    pre_op_agi_score: float = Field(..., ge=0.0, le=3.0, description="AGI score from Phase 09 (< 1.80 mandatory)")

class DecoctionBatchPreparation(BaseModel):
    """
    Decoction (Kwatha/Kashaya) batch tracking for Panchakarma administration.
    Enforces classical Sharangadhara Samhita and NABH AYUSH 24-hour Saviryata Avadhi limit.
    """
    batch_id: str = Field(..., description="Unique batch identification number")
    formulation_name: str = Field(..., description="Ayurvedic classical formulation name")
    prepared_at_timestamp: int = Field(..., description="Epoch timestamp of preparation completion")
    prepared_by_staff_id: str = Field(..., description="Ayurvedic pharmacist or nursing staff ID")
    volume_prepared_ml: float = Field(..., ge=10.0, description="Volume of decoction prepared in mL")
    intended_procedure: PanchakarmaProcedure = Field(..., description="Target Panchakarma procedure")
    storage_temperature_celsius: Optional[float] = Field(default=None, description="Storage temperature in Celsius")
    administration_timestamp: Optional[int] = Field(default=None, description="Actual or planned administration timestamp")


class PanchakarmaPlanCreate(BaseModel):
    """Request to initiate a structured clinical Panchakarma procedure."""
    patient_id: str = Field(..., description="Patient identifier")
    procedure_type: PanchakarmaProcedure = Field(..., description="Panchakarma Pradhana Karma type")
    target_shuddhi_tier: ShuddhiGrade = Field(default=ShuddhiGrade.MADHYAMA, description="Targeted elimination intensity")
    purva_karma: PurvaKarmaData = Field(..., description="Preparatory clinical data")
    prescribed_by_arn: str = Field(..., description="NCISM ARN of prescribing Ayurvedic Physician")


class PanchakarmaPlanResponse(BaseModel):
    """Clinical Panchakarma treatment plan dossier."""
    plan_id: str
    patient_id: str
    hospital_id: str
    procedure_type: PanchakarmaProcedure
    target_shuddhi_tier: ShuddhiGrade
    current_stage: PanchakarmaStage
    purva_karma: PurvaKarmaData
    prescribed_by_arn: str
    created_at: int


class SamsarjanaMeal(BaseModel):
    """Specific meal stage in graduated post-elimination dietary recovery."""
    day_number: int
    annakala_number: int
    meal_type: str = Field(..., description="PEYA, VILEPI, AKRITA_YUSHA, KRITA_YUSHA, MAMSA_RASA, NORMAL_DIET")
    diet_description: str
    caloric_density_tier: str


class ShuddhiEvaluationRequest(BaseModel):
    """Request to compute final Chaturvidha Shuddhi Pariksha and generate Samsarjana Krama."""
    plan_id: str = Field(..., description="Panchakarma plan identifier")
    laingiki_symptoms: List[str] = Field(..., min_length=1, description="Observed subjective & objective recovery signs")
    assessed_by_arn: str = Field(..., description="NCISM ARN of evaluating physician")


class ShuddhiEvaluationResponse(BaseModel):
    """Full Chaturvidha Shuddhi Pariksha verdict, Atiyoga detection, and Samsarjana diet schedule."""
    assessment_id: str
    plan_id: str
    patient_id: str
    procedure_type: PanchakarmaProcedure
    vaigiki_vega_count: int
    vaigiki_grade: ShuddhiGrade
    maniki_total_volume_ml: float
    maniki_grade: ShuddhiGrade
    antiki_milestone: AntikiMilestone
    antiki_passed: bool
    overall_shuddhi_grade: ShuddhiGrade
    laingiki_symptoms: List[str]
    atiyoga_detected: bool
    atiyoga_complications: List[str]
    emergency_management_protocol: Optional[str] = None
    samsarjana_krama_schedule: List[SamsarjanaMeal]
    clinical_summary: str
    assessed_by_arn: str
    created_at: int
