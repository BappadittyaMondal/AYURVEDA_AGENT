"""
models/vision_diagnostics.py - Data models for Phase 40: Computer Vision Optical Diagnostics Pipeline.
Tables 86 & 87: vision_inference_records, optical_calibration_targets.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class AnatomicalTarget(str, Enum):
    JIHWA_TONGUE = "JIHWA_TONGUE"
    NETRA_SCLERA_EYE = "NETRA_SCLERA_EYE"
    NAKHA_NAIL = "NAKHA_NAIL"


class ColorCardStandard(str, Enum):
    X_RITE_COLORCHECKER = "X_RITE_COLORCHECKER_CLASSIC"
    HOSPITAL_NEUTRAL_GREY = "AYUR_CLINICAL_GREY_18PCT"
    CUSTOM_LAB_CARD = "CUSTOM_LAB_CALIBRATION_TARGET"


class CalibrationTargetCreate(BaseModel):
    target_id: str = Field(..., description="Unique calibration standard target identifier")
    color_card_standard: ColorCardStandard = Field(..., description="Color standard specification")
    reference_l: float = Field(..., ge=0.0, le=100.0, description="Reference CIELAB Lightness (L*)")
    reference_a: float = Field(..., ge=-128.0, le=127.0, description="Reference CIELAB a* axis")
    reference_b: float = Field(..., ge=-128.0, le=127.0, description="Reference CIELAB b* axis")
    tolerance_delta_e: float = Field(2.0, gt=0.0, le=10.0, description="Acceptable Delta E threshold")


class CalibrationTargetRecord(BaseModel):
    target_id: str
    color_card_standard: str
    reference_l: float
    reference_a: float
    reference_b: float
    tolerance_delta_e: float
    created_at: int


class OpticalInferenceRequest(BaseModel):
    patient_id: str = Field(..., description="Patient UUID")
    hospital_id: str = Field(..., description="Hospital UUID")
    anatomical_target: AnatomicalTarget = Field(..., description="Target anatomy for optical inference")
    image_base64_or_bytes_hash: str = Field(..., description="SHA-256 hash or representation of the captured image")
    raw_cielab_l: float = Field(..., ge=0.0, le=100.0, description="Measured raw L*")
    raw_cielab_a: float = Field(..., ge=-128.0, le=127.0, description="Measured raw a*")
    raw_cielab_b: float = Field(..., ge=-128.0, le=127.0, description="Measured raw b*")
    coating_coverage_pct: Optional[float] = Field(0.0, ge=0.0, le=100.0, description="Tongue coating area percentage")
    calibration_target_id: Optional[str] = Field(None, description="Optional calibration standard card used in acquisition")


class OpticalInferenceResult(BaseModel):
    inference_id: str
    patient_id: str
    hospital_id: str
    anatomical_target: AnatomicalTarget
    raw_image_hash: str
    calibrated_cielab_l: float
    calibrated_cielab_a: float
    calibrated_cielab_b: float
    coating_thickness_pct: float
    icterus_index: Optional[float]
    delta_e_calibration_shift: float
    clinical_interpretation: str
    analyzed_at: int
