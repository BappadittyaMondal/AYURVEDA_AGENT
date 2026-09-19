"""Pydantic schemas for Ashtavidha Pariksha (8-Fold Clinical Examination)."""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# 1. Nadi Enums
class NadiGati(str, Enum):
    SARPA = "SARPA"          # Vata: Serpentine, rapid, thin
    MANDUKA = "MANDUKA"      # Pitta: Frog-like, leaping, bounding
    HAMSA = "HAMSA"          # Kapha: Swan-like, slow, broad
    JALAUKA = "JALAUKA"      # Leech-like
    KAKA = "KAKA"            # Crow-like (arrhythmic / grave)


class NadiRhythm(str, Enum):
    REGULAR = "REGULAR"
    IRREGULAR = "IRREGULAR"


class NadiVolume(str, Enum):
    FEEBLE = "FEEBLE"
    MODERATE = "MODERATE"
    BOUNDING = "BOUNDING"


class NadiExam(BaseModel):
    gati: NadiGati
    rate_bpm: int = Field(..., ge=30, le=220)
    rhythm: NadiRhythm
    volume: NadiVolume


# 2. Mutra Enums
class MutraColor(str, Enum):
    PALE_CLEAR = "PALE_CLEAR"          # Vata / normal
    PALE_YELLOW = "PALE_YELLOW"        # Normal
    DARK_YELLOW = "DARK_YELLOW"        # Pitta
    REDDISH_BROWN = "REDDISH_BROWN"    # Pitta / Rakta
    MILKY_TURBID = "MILKY_TURBID"      # Kapha / Prameha


class TailaBinduDirection(str, Enum):
    EAST = "EAST"                          # Sadhya (favorable)
    NORTH = "NORTH"                        # Sadhya (favorable)
    WEST = "WEST"                          # Krichrasadhya (moderate)
    SOUTH = "SOUTH"                        # Krichrasadhya (difficult)
    CENTRAL_STATIONARY = "CENTRAL_STATIONARY"  # Sluggish / Ama
    SUBMERGED_IMMEDIATE = "SUBMERGED_IMMEDIATE" # Asadhya (grave prognosis)


class MutraExam(BaseModel):
    color: MutraColor
    clarity: str = Field(default="CLEAR")
    frequency_day: int = Field(default=5, ge=0, le=30)
    taila_bindu_direction: TailaBinduDirection = TailaBinduDirection.NORTH
    dysuria: bool = False


# 3. Mala Enums
class MalaConsistency(str, Enum):
    HARD_DRY_SCYBALOUS = "HARD_DRY_SCYBALOUS"  # Vata
    NORMAL_FORMED = "NORMAL_FORMED"            # Samadosha
    SOFT_LOOSE = "SOFT_LOOSE"                  # Pitta
    WATERY = "WATERY"                          # Pitta / Vata


class JalaNimajjanaResult(str, Enum):
    FLOATS_NIRAMA = "FLOATS_NIRAMA"          # Nirama (Free from Ama)
    SINKS_SAMA = "SINKS_SAMA"                # Sama (Contains Ama)
    PARTIALLY_FLOATS = "PARTIALLY_FLOATS"    # Moderate Ama


class MalaExam(BaseModel):
    consistency: MalaConsistency
    jala_nimajjana: JalaNimajjanaResult
    frequency_per_day: int = Field(default=1, ge=0, le=20)
    color: str = Field(default="BROWN")


# 4. Jihwa Enums
class JihwaColor(str, Enum):
    NORMAL_PINK = "NORMAL_PINK"
    PALE = "PALE"                          # Kapha / Pandu
    RED = "RED"                            # Pitta
    BLUISH_CYANOTIC = "BLUISH_CYANOTIC"    # Vata / Sannipata


class JihwaCoating(str, Enum):
    CLEAN_NIRAMA = "CLEAN_NIRAMA"          # Nirama
    THIN_WHITE = "THIN_WHITE"              # Mild Kapha/Ama
    THICK_WHITE = "THICK_WHITE"            # High Kapha-Ama
    THICK_YELLOW = "THICK_YELLOW"          # High Pitta-Ama
    THICK_BROWN_BLACK = "THICK_BROWN_BLACK"# Severe Vata-Ama


class JihwaExam(BaseModel):
    color: JihwaColor
    coating: JihwaCoating
    fissures: bool = False                 # Vata indicator
    tooth_indentations: bool = False       # Ama / Kapha indicator


# 5. Shabda Enums
class ShabdaTone(str, Enum):
    CLEAR_RESONANT = "CLEAR_RESONANT"      # Samadosha
    LOW_DEEP = "LOW_DEEP"                  # Kapha
    HIGH_PITCHED_FAST = "HIGH_PITCHED_FAST"# Vata
    HOARSE_HARSH = "HOARSE_HARSH"          # Vata / Pitta


class ShabdaExam(BaseModel):
    tone: ShabdaTone
    clarity: bool = True


# 6. Sparsha Enums
class SparshaTemp(str, Enum):
    NORMAL_WARM = "NORMAL_WARM"
    COLD_CHILLY = "COLD_CHILLY"            # Vata / Kapha
    BURNING_HOT = "BURNING_HOT"            # Pitta
    COOL_DAMP = "COOL_DAMP"                # Kapha


class SparshaMoisture(str, Enum):
    NORMAL = "NORMAL"
    DRY_ROUGH = "DRY_ROUGH"                # Vata
    PROFUSE_SWEAT = "PROFUSE_SWEAT"        # Pitta
    CLAMMY = "CLAMMY"                      # Kapha


class SparshaExam(BaseModel):
    temperature: SparshaTemp
    moisture: SparshaMoisture


# 7. Drik Enums
class DrikSclera(str, Enum):
    CLEAR_WHITE = "CLEAR_WHITE"
    PALE = "PALE"                          # Pandu / Kapha
    YELLOW_ICTERIC = "YELLOW_ICTERIC"      # Pitta / Kamala
    RED_CONGESTED = "RED_CONGESTED"        # Pitta / Abhisyanda
    MUDDY_DRY = "MUDDY_DRY"                # Vata


class DrikExam(BaseModel):
    sclera: DrikSclera
    lacrimation: bool = False
    photophobia: bool = False


# 8. Akriti Enums
class AkritiPosture(str, Enum):
    NORMAL_SYMMETRICAL = "NORMAL_SYMMETRICAL"
    EMACIATED_STOOPED = "EMACIATED_STOOPED"# Vata
    ATHLETIC_MODERATE = "ATHLETIC_MODERATE"# Pitta
    OBESE_HEAVY = "OBESE_HEAVY"            # Kapha


class AkritiExam(BaseModel):
    posture: AkritiPosture
    gait_stability: str = Field(default="STEADY")


# Full Examination Input & Output
class AshtavidhaParikshaInput(BaseModel):
    """Complete 8-fold clinical examination input."""
    nadi: NadiExam
    mutra: MutraExam
    mala: MalaExam
    jihwa: JihwaExam
    shabda: ShabdaExam
    sparsha: SparshaExam
    drik: DrikExam
    akriti: AkritiExam


class AshtavidhaParikshaOutput(BaseModel):
    """Diagnostic evaluation output of Ashtavidha Pariksha."""
    exam_id: str
    patient_id: str
    hospital_id: str
    examiner_arn: str
    vata_score: float = Field(..., ge=0.0, le=1.0)
    pitta_score: float = Field(..., ge=0.0, le=1.0)
    kapha_score: float = Field(..., ge=0.0, le=1.0)
    primary_dosha: str
    secondary_dosha: Optional[str] = None
    ama_suspected: bool
    summary_findings: str
    timestamp: int
    model_config = ConfigDict(from_attributes=True)
