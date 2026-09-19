"""Pydantic schemas for Jihwa Pariksha Computer Vision & Micro-Colorimetry Tongue Coating Analysis."""
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class CoatingThickness(str, Enum):
    """Classical coating depth (Lepa) stratification."""
    NONE = "NONE"          # Nirlepa / Clean (0 - 5%)
    THIN = "THIN"          # Tanu Lepa (5 - 35%)
    MODERATE = "MODERATE"  # Madhyama Lepa (35 - 65%)
    THICK = "THICK"        # Bahula / Sandra Lepa (> 65%)


class DominantColor(str, Enum):
    """Micro-colorimetric tongue body & coating chromatic classification."""
    WHITE = "WHITE"                # Shweta: Kapha / Kaphaja Ama
    YELLOW = "YELLOW"              # Peeta / Haridra: Pitta / Pittaja Ama
    BROWN_BLACK = "BROWN_BLACK"    # Krishna / Shyama: Vata / Sannipata
    RED_CRIMSON = "RED_CRIMSON"    # Rakta: Pitta Vidagdha / Erythema
    CLEAN_PINK = "CLEAN_PINK"      # Prakrita: Healthy mucosal homeostatic vascularity


class TongueRegion(str, Enum):
    """Ayurvedic somatotopic lingual zones."""
    ROOT = "ROOT"                  # Mula: Adhobhaga / Pakvashaya / Vata-Kapha zone
    CENTER = "CENTER"              # Madhya: Samana / Pachaka Agni / Amashaya zone
    TIP_MARGINS = "TIP_MARGINS"    # Agra / Parshva: Prana / Hridaya / Yakrit zone


class RegionColorimetry(BaseModel):
    """Colorimetric values measured at a specific somatotopic lingual zone."""
    region: TongueRegion
    rgb_hex: str = Field(..., pattern=r"^#[0-9a-fA-F]{6}$", description="Hex RGB representation")
    cie_l: float = Field(..., ge=0.0, le=100.0, description="CIE-L* Lightness (0=Black, 100=White)")
    cie_a: float = Field(..., ge=-128.0, le=127.0, description="CIE-a* Green (-) to Red (+)")
    cie_b: float = Field(..., ge=-128.0, le=127.0, description="CIE-b* Blue (-) to Yellow (+)")


class JihwaInput(BaseModel):
    """Telemetry and computer vision extraction input for Jihwa Pariksha."""
    patient_id: str = Field(..., description="Target patient UUID")
    coating_ratio_percent: float = Field(..., ge=0.0, le=100.0, description="Coating area percentage (CAR)")
    fissure_density: float = Field(default=0.0, ge=0.0, le=1.0, description="Crack/fissure area density (Sphutita)")
    papillary_roughness: float = Field(default=0.0, ge=0.0, le=1.0, description="Gradient energy / papillae roughness")
    regions: List[RegionColorimetry] = Field(..., min_length=1, description="Colorimetric readings across lingual zones")
    observed_moisture: float = Field(default=0.5, ge=0.0, le=1.0, description="0=Arid/Ruksha, 1=Unctuous/Snigdha")
    image_hash: Optional[str] = Field(default=None, description="SHA-256 digest of clinical lingual photograph")


class JihwaOutput(BaseModel):
    """Comprehensive Jihwa diagnostic evaluation, Doshic vector, and Ama scoring."""
    exam_id: str
    patient_id: str
    hospital_id: str
    examiner_arn: str
    image_hash: Optional[str]
    coating_ratio: float
    coating_thickness: CoatingThickness
    dominant_color: DominantColor
    fissure_density: float
    cie_l: float
    cie_a: float
    cie_b: float
    ama_score: float
    vata_score: float
    pitta_score: float
    kapha_score: float
    primary_dosha: str
    is_sama: bool
    findings_summary: str
    somatotopic_mapping: Dict[str, str]
    timestamp: int
    model_config = ConfigDict(from_attributes=True)


class JihwaSimulationRequest(BaseModel):
    """Request to synthesize calibrated lingual biometric patterns."""
    target_condition: str = Field(
        ...,
        description="Target condition: VATA_DRY, PITTA_INFLAMED, KAPHA_AMA, or HEALTHY_NIRAMA",
    )


class JihwaSimulationResponse(BaseModel):
    """Synthesized lingual colorimetric profile for simulation testing."""
    target_condition: str
    coating_ratio_percent: float
    fissure_density: float
    papillary_roughness: float
    regions: List[RegionColorimetry]
    observed_moisture: float
    expected_dominant_color: DominantColor
    expected_dosha: str
    classical_reference: str
