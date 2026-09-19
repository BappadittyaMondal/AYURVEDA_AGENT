"""
Clinical Dietetics, Ahara Varga, Pathya-Apathya & Viruddha Ahara Models
=======================================================================
Defines schemas for:
1. 12 Classical Ahara Varga food groups (Charaka Sutrasthana 27)
2. 18-fold Viruddha Ahara incompatibility matrix (Charaka Sutrasthana 26)
3. Disease-specific Pathya-Apathya clinical guideline registry
4. Caloric-Doshic meal composition and nutritional breakdown
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AharaVarga(str, Enum):
    SHUKA_DHANYA = "SHUKA_DHANYA"          # Corns/Grains with awns (Rice, Barley, Wheat)
    SHAMI_DHANYA = "SHAMI_DHANYA"          # Pulses/Legumes in pods (Green gram, Black gram, Horse gram)
    MAMSA_VARGA = "MAMSA_VARGA"            # Animal meats (Jangala, Anupa, Jalamchara, Matsya)
    SHAKA_VARGA = "SHAKA_VARGA"            # Leafy & pod vegetables
    PHALA_VARGA = "PHALA_VARGA"            # Fruits
    HARITA_VARGA = "HARITA_VARGA"          # Green herbs, salads, and aromatics (Ginger, Garlic, Radish)
    MADYA_VARGA = "MADYA_VARGA"            # Fermented alcoholic beverages
    JALA_VARGA = "JALA_VARGA"              # Waters (Rain, Spring, Boiled warm water)
    GORASA_VARGA = "GORASA_VARGA"          # Bovine dairy products (Milk, Curd, Buttermilk, Butter, Ghee)
    IKSHU_VARGA = "IKSHU_VARGA"            # Sugarcane products & Honey (Sugar, Jaggery, Honey)
    KRITANNA_VARGA = "KRITANNA_VARGA"      # Prepared foods (Gruel, Soups, Porridges)
    AHARAYOGI_VARGA = "AHARAYOGI_VARGA"    # Dietary adjuvants (Oils, Salts, Spices)


class ViruddhaType(str, Enum):
    DESHA_VIRUDDHA = "DESHA_VIRUDDHA"          # Habitat incompatibility (Dry foods in arid zones)
    KALA_VIRUDDHA = "KALA_VIRUDDHA"            # Seasonal incompatibility (Pungent in summer)
    AGNI_VIRUDDHA = "AGNI_VIRUDDHA"            # Digestive capacity mismatch
    MATRA_VIRUDDHA = "MATRA_VIRUDDHA"          # Quantitative ratio incompatibility (1:1 Honey & Ghee)
    SATMYA_VIRUDDHA = "SATMYA_VIRUDDHA"        # Habitual tolerance mismatch
    DOSHA_VIRUDDHA = "DOSHA_VIRUDDHA"          # Doshic provocation mismatch
    SAMSKARA_VIRUDDHA = "SAMSKARA_VIRUDDHA"    # Processing incompatibility (Heated honey, heated curd)
    VEERYA_VIRUDDHA = "VEERYA_VIRUDDHA"        # Potency clash (Fish + Milk)
    KOSHTHA_VIRUDDHA = "KOSHTHA_VIRUDDHA"      # Bowel motility mismatch
    AVASTHA_VIRUDDHA = "AVASTHA_VIRUDDHA"      # Health/Fatigue state mismatch
    KRAMA_VIRUDDHA = "KRAMA_VIRUDDHA"          # Incompatible meal sequence
    PARIHARA_VIRUDDHA = "PARIHARA_VIRUDDHA"    # Post-treatment violation
    UPACHAARA_VIRUDDHA = "UPACHAARA_VIRUDDHA"  # Treatment adjuvant conflict
    PAAKA_VIRUDDHA = "PAAKA_VIRUDDHA"          # Bad cooking / charred preparation
    SAMYOGA_VIRUDDHA = "SAMYOGA_VIRUDDHA"      # Direct chemical/toxic combination (Milk + Sour fruit)
    HRIDAYA_VIRUDDHA = "HRIDAYA_VIRUDDHA"      # Psychological unpalatability
    SAMPAT_VIRUDDHA = "SAMPAT_VIRUDDHA"        # Defective / decayed ingredient
    VIDHI_VIRUDDHA = "VIDHI_VIRUDDHA"          # Code of dining conduct violation


class DietIngredient(BaseModel):
    """Food ingredient nutrition and pharmacodynamic profile."""
    ingredient_id: str
    sanskrit_name: str
    english_name: str
    ahara_varga: AharaVarga
    rasa: str
    veerya: str
    vipaka: str
    guna: List[str]
    doshic_effect: Dict[str, str]
    calories_per_100g: float = Field(..., ge=0.0)
    protein_g: float = Field(..., ge=0.0)
    carbs_g: float = Field(..., ge=0.0)
    fat_g: float = Field(..., ge=0.0)


class DiseasePathyaApathya(BaseModel):
    """Disease-specific dietary and lifestyle guidelines."""
    registry_id: str
    disease_code: str
    disease_name: str
    pathya_ahara: List[str]
    apathya_ahara: List[str]
    pathya_vihara: List[str]
    apathya_vihara: List[str]


class MealItem(BaseModel):
    """Single food item and quantity in a meal."""
    ingredient_id: str = Field(..., description="Diet ingredient identifier")
    portion_grams: float = Field(..., gt=0.0, description="Portion quantity in grams")
    is_heated: bool = Field(default=False, description="Flag indicating if ingredient was cooked/heated")


class PlannedMeal(BaseModel):
    """Structured clinical meal."""
    meal_name: str = Field(..., description="PRATARASHA, MADHYAHNA, SAYAM, SNACK")
    time_of_day: str = Field(..., description="e.g. 08:00 AM, 01:00 PM, 07:30 PM")
    items: List[MealItem] = Field(..., min_length=1, description="Food items comprising the meal")


class ViruddhaViolation(BaseModel):
    """Documented incompatibility finding in a planned diet."""
    viruddha_type: ViruddhaType
    substances_involved: List[str]
    clinical_rationale: str
    severity: str = Field(..., description="WARNING or CRITICAL_BLOCKED")


class DietPlanCreateRequest(BaseModel):
    """Request to evaluate, audit, and prescribe a clinical Ayurvedic meal plan."""
    patient_id: str = Field(..., description="Patient identifier")
    diagnosis_code: str = Field(..., description="Principal diagnosis code (e.g. AYU-DIS-AMAVATA)")
    target_calories: float = Field(..., ge=500.0, le=5000.0, description="Target daily caloric intake")
    meals: List[PlannedMeal] = Field(..., min_length=1, description="Daily planned meals")
    prescribed_by_arn: str = Field(..., description="NCISM ARN of prescribing clinical dietician/physician")


class DietPlanResponse(BaseModel):
    """Evaluated clinical diet plan with Viruddha Ahara audit and nutritional breakdown."""
    diet_plan_id: str
    patient_id: str
    diagnosis_code: str
    target_calories: float
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    composite_doshic_vector: Dict[str, float]
    viruddha_check_passed: bool
    viruddha_violations: List[ViruddhaViolation]
    pathya_compliance_score: float = Field(..., ge=0.0, le=100.0, description="Percentage of foods matching Pathya")
    clinical_recommendation: str
    prescribed_by_arn: str
    created_at: int
