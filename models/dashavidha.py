"""Pydantic schemas for Dashavidha Pariksha (10-Fold Systemic Clinical Evaluation)."""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DushyaDhatu(str, Enum):
    """Pathological tissue and excretory substrates (Dhatus & Malas)."""
    RASA = "RASA"          # Chyle / Plasma / Interstitial fluid (Superficial)
    RAKTA = "RAKTA"        # Blood / Hemoglobin / Microcirculation
    MAMSA = "MAMSA"        # Muscle tissue
    MEDA = "MEDA"          # Adipose tissue / Lipids
    ASTHI = "ASTHI"        # Bone tissue (Deep)
    MAJJA = "MAJJA"        # Bone marrow / Neuro-tissue (Deep)
    SHUKRA = "SHUKRA"      # Reproductive semen / Ojas substrate (Deepest)
    PURISHA = "PURISHA"    # Fecal matter
    MUTRA = "MUTRA"        # Urine
    SVEDA = "SVEDA"        # Perspiration


class BhumiDesha(str, Enum):
    """Geographical habitat and climatic terrain."""
    ANUPA = "ANUPA"            # Marshy, humid, wetlands (Kapha predominance)
    JANGALA = "JANGALA"        # Arid, dry, thorny savanna (Vata predominance)
    SADHARANA = "SADHARANA"    # Temperate, moderate flora/climate (Equilibrium)


class DehaDesha(str, Enum):
    """Bodily locus of pathological manifestation (Rogamarga)."""
    KOSHTHA = "KOSHTHA"                          # Internal GI tract (Antah Rogamarga)
    SHAKHA = "SHAKHA"                            # External peripheral tissues (Bahir Rogamarga)
    MARMA_ASTHI_SANDHI = "MARMA_ASTHI_SANDHI"    # Vital centers, bones, and joints (Madhyama Rogamarga)


class GradingScale(str, Enum):
    """Three-tier classical qualitative grading (Charaka Vimana 8)."""
    PRAVARA = "PRAVARA"      # Superior / High / Excellent (Score = 3)
    MADHYAMA = "MADHYAMA"    # Medium / Moderate (Score = 2)
    AVARA = "AVARA"          # Inferior / Low / Deficient (Score = 1)


class AgniType(str, Enum):
    """Digestive & metabolic fire state."""
    SAMAGNI = "SAMAGNI"          # Balanced homeostatic metabolism
    VISHAMAGNI = "VISHAMAGNI"    # Irregular / fluctuating (Vata)
    TIKSHNAGNI = "TIKSHNAGNI"    # Hypermetabolic / ravenous (Pitta)
    MANDAGNI = "MANDAGNI"        # Sluggish / hypometabolic (Kapha)


class VayasStage(str, Enum):
    """Chronological life stage."""
    BALYA = "BALYA"              # Childhood (< 16 years; Kapha natural dominance)
    MADHYAMA = "MADHYAMA"        # Youth / Adult (16-60 years; Pitta natural dominance)
    VARDHAKYA = "VARDHAKYA"      # Old age (> 60 years; Vata natural dominance)


class TherapeuticEligibility(str, Enum):
    """Clinical determination of therapeutic intensity based on Rogi-Roga Bala."""
    SHODHANA_ELIGIBLE = "SHODHANA_ELIGIBLE"                # High reserve (R_BR > 1.2): Radical Panchakarma permitted
    SHAMANA_INDICATED = "SHAMANA_INDICATED"                # Moderate reserve (0.8 <= R_BR <= 1.2): Internal pacification
    BRIMHANA_SUPPORTIVE_ONLY = "BRIMHANA_SUPPORTIVE_ONLY"  # Low reserve (R_BR < 0.8): Shodhana strictly contraindicated


class DushyaAssessment(BaseModel):
    primary_dushyas: List[DushyaDhatu] = Field(..., min_length=1)
    chronicity_days: int = Field(default=14, ge=0)


class DeshaAssessment(BaseModel):
    bhumi: BhumiDesha
    deha: DehaDesha


class BalaAssessment(BaseModel):
    sahaja: GradingScale       # Innate / Genetic constitutional strength
    kalaja: GradingScale       # Seasonal & chronological age vitality
    yuktikrita: GradingScale   # Acquired lifestyle, diet, and physical training


class AnalaAssessment(BaseModel):
    agni: AgniType
    postprandial_heaviness: bool = False


class AharaShaktiAssessment(BaseModel):
    abhyavaharana: GradingScale  # Food ingestion volume capacity
    jarana: GradingScale         # Digestive transformation speed and comfort


class DashavidhaParikshaInput(BaseModel):
    """10-fold clinical systemic input model."""
    dushya: DushyaAssessment
    desha: DeshaAssessment
    bala: BalaAssessment
    kala_season: str = Field(default="VASANTA", description="Current Ritu (Season)")
    anala: AnalaAssessment
    vayas_stage: VayasStage
    sattva: GradingScale       # Mental fortitude & pain tolerance
    satmya: GradingScale       # Dietary tolerance & habituation
    ahara_shakti: AharaShaktiAssessment


class DashavidhaParikshaOutput(BaseModel):
    """Output evaluation of Dashavidha Pariksha and Rogi-Roga Bala."""
    assessment_id: str
    patient_id: str
    hospital_id: str
    evaluator_arn: str
    rogi_bala_score: float = Field(..., ge=0.0, le=100.0)
    roga_bala_score: float = Field(..., ge=0.0, le=100.0)
    rogi_roga_ratio: float = Field(..., ge=0.0)
    therapeutic_eligibility: TherapeuticEligibility
    clinical_rationale: str
    timestamp: int
    model_config = ConfigDict(from_attributes=True)
