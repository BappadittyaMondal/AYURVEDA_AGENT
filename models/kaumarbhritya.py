"""
Kaumarbhritya & Bala Roga Pediatric Models
==========================================
Defines schemas for:
1. Kaumarbhritya Developmental Milestones & Classical Samskaras (Jatakarma to Chaula)
2. Dual-Posology Pediatric Dosage Scaling (Sharngadhara Ratti Calculus & Clark / Cowling rules)
3. Pediatric Toxicology Firewall (Prohibition of Schedule E-1 poisons & toxic heavy metals)
4. Kashyapa Classical Bala Roga Syndromes (Phakka, Parigarbhika, Kukunaka, Stanya Dushti)
5. Suvarnaprashana Immunomodulation Protocol Engine on Pushya Nakshatra
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DietaryStage(str, Enum):
    KSHEERADA = "KSHEERADA"          # Milk-only diet (0 to 12 months)
    KSHEERANNADA = "KSHEERANNADA"    # Milk and semi-solid food transition (1 to 2 years)
    ANNADA = "ANNADA"                # Solid food established (> 2 years)


class ClassicalSamskara(str, Enum):
    JATAKARMA = "JATAKARMA"          # Neonatal resuscitation & gold-honey-ghee lick at birth
    NAMAKARANA = "NAMAKARANA"        # Naming ceremony (10th/12th day)
    NISHKRAMANA = "NISHKRAMANA"      # First outing for sun/moon exposure (4th month)
    ANNAPRASHANA = "ANNAPRASHANA"    # First fruit and grain feeding (6th month)
    KARNAVEDHA = "KARNAVEDHA"        # Earlobe piercing for immune/vital stimulation (6th/7th month)
    CHAULA_CHUDAKARANA = "CHAULA_CHUDAKARANA" # Tonsure / first haircut (1st to 3rd year)
    UPANAYANA = "UPANAYANA"          # Schooling initiation (5th to 8th year)


class BalaRogaSyndrome(str, Enum):
    PHAKKA_KSHIRAJA = "PHAKKA_KSHIRAJA"                        # Malnutrition from deficient/vitiated breast milk
    PHAKKA_GARBHAJA_PARIGARBHIKA = "PHAKKA_GARBHAJA_PARIGARBHIKA" # Emaciation from infant displacement by rapid subsequent pregnancy
    PHAKKA_VYADHIJA = "PHAKKA_VYADHIJA"                        # Secondary failure to thrive post-chronic fever/infection
    KUKUNAKA = "KUKUNAKA"                                      # Ophthalmia neonatorum / conjunctivitis during dentition
    STANYA_DUSHTI = "STANYA_DUSHTI"                            # Vitiated breast milk causing infantile colic/vomiting
    AHIPUTANA = "AHIPUTANA"                                    # Napkin/diaper dermatitis & perianal excoriation
    TALUKANTAKA = "TALUKANTAKA"                                # Depressed fontanelle from acute dehydration
    SHAYYAMUTRA = "SHAYYAMUTRA"                                # Nocturnal enuresis in children
    BALA_KRIMI = "BALA_KRIMI"                                  # Pediatric intestinal worm infestation


class KaumarbhrityaMilestone(BaseModel):
    """Developmental milestone and posology guide by age."""
    milestone_id: str
    age_months: int
    classical_samskara: ClassicalSamskara
    motor_milestone: str
    cognitive_milestone: str
    sharngadhara_dosage_ratti: float
    dietary_stage: DietaryStage


class PediatricDosageCalculationRequest(BaseModel):
    """Calculate pediatric scaled posology using dual Ayurvedic and Western formulas."""
    patient_id: str
    age_months: int = Field(..., ge=0, le=192, description="Age in months (0 to 16 years)")
    weight_kg: float = Field(..., ge=1.5, le=100.0, description="Current weight in kilograms")
    adult_dose_mg: float = Field(..., gt=0.0, description="Standard adult reference single dose in mg")
    formulation_name: str
    contains_heavy_metals_or_schedule_e1: bool = False
    evaluator_arn: str


class PediatricDosageCalculationResponse(BaseModel):
    """Calibrated pediatric dosage with toxicological firewall verification."""
    patient_id: str
    age_months: int
    weight_kg: float
    dietary_stage: DietaryStage
    clark_dose_mg: float
    cowling_dose_mg: float
    sharngadhara_dose_mg: float
    recommended_pediatric_dose_mg: float
    safety_firewall_cleared: bool
    contraindication_flags: List[str]


class PediatricConsultationCreate(BaseModel):
    """Log a pediatric clinical consultation, diagnosis, and prescription."""
    patient_id: str
    age_months: int = Field(..., ge=0, le=192)
    weight_kg: float = Field(..., ge=1.5, le=100.0)
    bala_roga_diagnosis: BalaRogaSyndrome
    presenting_symptoms: List[str]
    adult_reference_dose_mg: float = Field(..., gt=0.0)
    prescribed_formulation: str
    contains_heavy_metals_or_schedule_e1: bool = False
    practitioner_arn: str


class PediatricConsultationResponse(BaseModel):
    """Pediatric consultation record with dual posology and clinical management plan."""
    consultation_id: str
    patient_id: str
    hospital_id: str
    age_months: int
    weight_kg: float
    dietary_stage: DietaryStage
    bala_roga_diagnosis: BalaRogaSyndrome
    icd11_mapping: str
    adult_reference_dose_mg: float
    calculated_dose_clark_mg: float
    calculated_dose_cowling_mg: float
    calculated_dose_sharngadhara_mg: float
    final_dispensed_dose_mg: float
    prescribed_formulation: str
    safety_firewall_passed: bool
    clinical_management_plan: List[str]
    practitioner_arn: str
    created_at: int


class SuvarnaprashanaAdminCreate(BaseModel):
    """Log an administration of Suvarnaprashana on Pushya Nakshatra."""
    patient_id: str
    age_months: int = Field(..., ge=0, le=192)
    pushya_nakshatra_date: str = Field(..., description="Calendar date of Pushya Nakshatra (YYYY-MM-DD)")
    suvarna_bhasma_mg: float = Field(..., ge=0.5, le=15.0, description="Nano-purified Suvarna Bhasma in mg (typically 1.5 to 5 mg)")
    madhu_ghrita_ratio: str = Field(default="2:1 Madhu to Ghrita", description="Strictly unequal proportion (never 1:1)")
    medhya_herbs: List[str] = Field(default_factory=lambda: ["Brahmi", "Vacha", "Shankhapushpi"])
    practitioner_arn: str


class SuvarnaprashanaAdminResponse(BaseModel):
    """Suvarnaprashana administration record with documented immunomodulation outcomes."""
    dose_id: str
    patient_id: str
    hospital_id: str
    age_months: int
    pushya_nakshatra_date: str
    suvarna_bhasma_mg: float
    madhu_ghrita_ratio: str
    medhya_herbs: List[str]
    immunomodulation_outcomes: List[str]
    adverse_events: str
    practitioner_arn: str
    created_at: int
