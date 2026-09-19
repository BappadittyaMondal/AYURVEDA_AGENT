"""
Agada Tantra, Visha Chikitsa & Environmental Toxicology Models
==============================================================
Defines schemas for:
1. Classical Visha Taxonomy (Sthavara, Jangama, Dushi Visha, Gara Visha)
2. The 24 Classical Visha Upakramas & Emergency Resuscitation (Charaka Chikitsasthana 23)
3. Snakebite Syndromic Stratification (Darvikara, Mandala, Rajimanta) & 20WBCT
4. Modern Antidote Firewall (Polyvalent Anti-Snake Venom ASV & Cardioprotective Hridaya-Avarana)
5. Dushi Visha Chronic Bioaccumulation & Environmental Detoxification Engine
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class VishaCategory(str, Enum):
    STHAVARA = "STHAVARA"          # Plant & mineral poisons (Vatsanabha, Dhattura, Somala, Haratala)
    JANGAMA = "JANGAMA"            # Animal venoms (Sarpa, Vrishchika, Keeta, Luta, Alarka)
    DUSHI_VISHA = "DUSHI_VISHA"    # Latent, slow, cumulative bioaccumulative xenobiotics
    GARA_VISHA = "GARA_VISHA"      # Concocted / artificial slow chemical toxidromes & adulterants


class EnvenomationSyndrome(str, Enum):
    DARVIKARA_NEUROTOXIC = "DARVIKARA_NEUROTOXIC"        # Elapid (Cobra/Krait) - ptosis, respiratory paralysis
    MANDALA_HEMOTOXIC = "MANDALA_HEMOTOXIC"              # Viperid (Russell's/Saw-scaled) - coagulopathy, hemorrhage
    RAJIMANTA_MYOTOXIC = "RAJIMANTA_MYOTOXIC"            # Sea snake (Hydrophiinae) - myalgia, myoglobinuria
    VRISHCHIKA_AUTONOMIC = "VRISHCHIKA_AUTONOMIC"        # Scorpion sting - autonomic storm, pulmonary edema
    NON_VENOMOUS = "NON_VENOMOUS"                        # Dry bite or harmless species


class ToxicEmergencyTriage(str, Enum):
    CRITICAL_TOXIC_EMERGENCY = "CRITICAL_TOXIC_EMERGENCY"  # Immediate ASV, intubation, critical care resuscitation
    MODERATE_OBSERVATION = "MODERATE_OBSERVATION"          # Inconclusive signs; 2-hourly serial 20WBCT monitoring
    NON_ENCLOSING_DISCHARGED = "NON_ENCLOSING_DISCHARGED"  # No envenomation detected following 24-hr observation


class VishaProfile(BaseModel):
    """Toxicological registry entry for a classical or environmental toxin."""
    visha_code: str
    sanskrit_name: str
    english_name: str
    visha_category: VishaCategory
    source_origin: str
    cardinal_manifestations: List[str]
    upakrama_indications: List[str]
    specific_agada_formulations: List[str]
    modern_antidote_mapping: str


class VishaEmergencyAdmissionCreate(BaseModel):
    """Acute envenomation admission and emergency triage logging."""
    patient_id: str
    suspected_visha_code: str
    envenomation_syndrome: EnvenomationSyndrome
    bite_to_admission_minutes: int = Field(..., ge=0, description="Time elapsed from bite to hospital admission")
    twenty_minute_wbct_clotted: bool = Field(..., description="True if blood firmly clots in 20 min; False if non-clotting")
    neurotoxic_signs_present: bool = Field(False, description="Ptosis, diplopia, dysphagia, or respiratory depression")
    hemotoxic_signs_present: bool = Field(False, description="Spontaneous mucosal bleeding, rapid swelling, or hematuria")
    practitioner_arn: str


class VishaEmergencyAdmissionResponse(BaseModel):
    """Envenomation triage response with ASV dosage and 24-Upakrama protocols."""
    episode_id: str
    patient_id: str
    hospital_id: str
    suspected_visha_code: str
    envenomation_syndrome: EnvenomationSyndrome
    triage_level: ToxicEmergencyTriage
    asv_indicated_vials: int
    emergency_escalation_protocol: Optional[str] = None
    upakramas_executed: List[str]
    cardioprotective_hridaya_avarana: str
    adjunctive_ayurvedic_agadas: List[str]
    practitioner_arn: str
    created_at: int


class DushiVishaAssessmentCreate(BaseModel):
    """Log clinical evaluation for chronic latent toxic bioaccumulation (Dushi Visha)."""
    patient_id: str
    suspected_toxin_source: str = Field(..., description="E.g. Occupational heavy metals, pesticide residues, chemical exposure")
    chronicity_months: int = Field(..., ge=1, description="Duration of exposure/symptoms in months")
    reported_manifestations: List[str]
    aggravating_triggers: List[str] = Field(default_factory=list, description="E.g. Rainy season (Varsha), cloudy sky (Megha), cold wind")
    practitioner_arn: str


class DushiVishaAssessmentResponse(BaseModel):
    """Dushi Visha clinical assessment with Dooshivishari Agada and Shodhana regimen."""
    log_id: str
    patient_id: str
    hospital_id: str
    suspected_toxin_source: str
    chronicity_months: int
    manifestations: List[str]
    dushi_visha_stage: str
    dooshivishari_agada_prescribed: bool
    shodhana_protocol: str
    clinical_management_plan: List[str]
    practitioner_arn: str
    created_at: int
