"""
Swasthavritta, Dinacharya, Ritucharya & Vega-Dharana Pathology Models
=====================================================================
Defines schemas for:
1. Circadian Doshic Bio-Rhythm Clock (Kapha, Pitta, Vata cycles)
2. Classical Dinacharya Daily Regimen steps (Ashtanga Hridaya Sutrasthana Ch. 2)
3. 13 Non-suppressible natural urges (Adharaniya Vegas - Charaka Sutrasthana Ch. 7)
4. Ritucharya Seasonal Calendar & Seasonal Shodhana Windows (Charaka Sutrasthana Ch. 6)
5. Ritusandhi 14-day transition firewall & Padamshika Krama
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CircadianPeriod(str, Enum):
    BRAHMA_MUHURTA = "BRAHMA_MUHURTA"    # 02:00 - 06:00 (Vata Predawn / Awakening & Evacuation)
    KAPHA_MORNING = "KAPHA_MORNING"      # 06:00 - 10:00 (Kapha Morning / Vyayama & Bath)
    PITTA_MIDDAY = "PITTA_MIDDAY"        # 10:00 - 14:00 (Pitta Midday / Principal Meal & Peak Agni)
    VATA_AFTERNOON = "VATA_AFTERNOON"    # 14:00 - 18:00 (Vata Afternoon / Intellectual Work)
    KAPHA_EVENING = "KAPHA_EVENING"      # 18:00 - 22:00 (Kapha Evening / Light Dinner & Relaxation)
    PITTA_NIGHT = "PITTA_NIGHT"          # 22:00 - 02:00 (Pitta Night / Metabolic Regeneration & Sleep)


class AdharaniyaVegaType(str, Enum):
    MUTRA = "MUTRA"                      # Urination
    PURISHA = "PURISHA"                  # Defecation
    SHUKRA = "SHUKRA"                    # Semen / Ejaculation
    APANA_VATA = "APANA_VATA"            # Flatus
    CHHARDI = "CHHARDI"                  # Vomiting
    KSHAVATHU = "KSHAVATHU"              # Sneezing
    UDGARA = "UDGARA"                    # Belching / Eructation
    JRIMBHA = "JRIMBHA"                  # Yawning
    KSHUDHA = "KSHUDHA"                  # Hunger
    PIPASA = "PIPASA"                    # Thirst
    BASHPA = "BASHPA"                    # Tears / Crying
    SHRAMA_SHWASA = "SHRAMA_SHWASA"      # Rapid breathing on exertion
    NIDRA = "NIDRA"                      # Sleep


class RituCode(str, Enum):
    SHISHIRA = "SHISHIRA"                # Late Winter (Mid Jan - Mid Mar)
    VASANTA = "VASANTA"                  # Spring (Mid Mar - Mid May)
    GRISHMA = "GRISHMA"                  # Summer (Mid May - Mid Jul)
    VARSHA = "VARSHA"                    # Monsoon (Mid Jul - Mid Sep)
    SHARAD = "SHARAD"                    # Autumn (Mid Sep - Mid Nov)
    HEMANTA = "HEMANTA"                  # Early Winter (Mid Nov - Mid Jan)


class Ayana(str, Enum):
    ADANA_KALA = "ADANA_KALA"            # Uttarayana (Sun moves north, absorbs bodily strength)
    VISARGA_KALA = "VISARGA_KALA"        # Dakshinayana (Sun moves south, releases coolness/strength)


class DinacharyaStep(BaseModel):
    """Canonical daily regimen procedure specification."""
    step_id: str
    step_name: str
    sanskrit_name: str
    ideal_time_window: str
    doshic_benefit: str
    description: str
    contraindications: List[str] = Field(default_factory=list)


class CircadianClockStatus(BaseModel):
    """Current Ayurvedic bio-rhythm state based on circadian clock."""
    current_time_str: str
    active_period: CircadianPeriod
    dominant_dosha: str
    recommended_activities: List[str]
    contraindicated_activities: List[str]
    clinical_advisory: str


class DinacharyaRoutineAuditRequest(BaseModel):
    """Patient daily lifestyle routine submission for audit against Dinacharya principles."""
    patient_id: str
    wake_up_time: str = Field(..., description="e.g. 05:30 AM or 08:30 AM")
    bed_time: str = Field(..., description="e.g. 10:30 PM or 01:00 AM")
    breakfast_time: Optional[str] = None
    lunch_time: Optional[str] = None
    dinner_time: Optional[str] = None
    has_daytime_nap: bool = Field(default=False, description="Sleep during day hours (Diva-swapna)")
    exercise_habit: str = Field(..., description="NONE, LIGHT, MODERATE, EXCESSIVE")
    dinacharya_practices: List[str] = Field(
        default_factory=list,
        description="Practices performed e.g. USHAPANA, DANTADHAVANA, JIHWA_NIRLEKHANA, ABHYANGA, NASYA, GANDUSHA"
    )


class DinacharyaRoutineAuditResponse(BaseModel):
    """Clinical lifestyle audit findings, score, and corrections."""
    audit_id: str
    patient_id: str
    compliance_score: float = Field(..., ge=0.0, le=100.0)
    circadian_alignment: str = Field(..., description="OPTIMAL, MODERATE, DYSREGULATED")
    doshic_vitiation_risks: List[str]
    corrective_recommendations: List[str]
    created_at: int


class VegaSuppressionLogRequest(BaseModel):
    """Log a pattern of non-suppressible urge inhibition."""
    patient_id: str
    vega_type: AdharaniyaVegaType
    frequency: str = Field(..., description="DAILY, FREQUENT, OCCASIONAL")
    duration_months: int = Field(..., ge=1, description="Duration of habit in months")
    presenting_symptoms: List[str] = Field(default_factory=list)


class VegaPathologyResponse(BaseModel):
    """Diagnostic evaluation of natural urge suppression consequences and treatment."""
    log_id: str
    patient_id: str
    vega_type: AdharaniyaVegaType
    classical_manifestations: List[str]
    secondary_udavarta_risk: str = Field(..., description="CRITICAL, HIGH, MODERATE, LOW")
    primary_vitiated_dosha: str
    remediation_protocol: str
    created_at: int


class SeasonalRegimenProfile(BaseModel):
    """Ritucharya clinical specifications for a single season."""
    ritu_code: RituCode
    ritu_name: str
    sanskrit_name: str
    ayana: Ayana
    english_months: str
    dominant_rasa: str
    dominant_mahabhuta: str
    doshic_sanchaya: str
    doshic_prakopa: str
    doshic_prashamana: str
    indicated_shodhana: str
    pathya_ahara: List[str]
    apathya_ahara: List[str]
    pathya_vihara: List[str]
    apathya_vihara: List[str]


class RitusandhiEvaluation(BaseModel):
    """Evaluation of seasonal transition period and seasonal Shodhana readiness."""
    evaluated_date: str
    active_ritu: RituCode
    in_ritusandhi: bool
    transition_note: Optional[str] = None
    padamshika_krama_rule: Optional[str] = None
    active_doshic_state: Dict[str, str]
    recommended_seasonal_shodhana: str
    seasonal_advisory: str
