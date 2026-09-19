"""Pydantic schemas for Taila Bindu Pariksha Diagnostic & Surface-Tension Fluid Dynamics."""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class PrognosisVerdict(str, Enum):
    """Classical prognostic verdict from Yogaratnakara & Vangasena."""
    SADHYA = "SADHYA"                  # Curable / favorable prognosis
    KRICHRASADHYA = "KRICHRASADHYA"    # Difficult to cure / guarded prognosis
    ASADHYA = "ASADHYA"                # Incurable / grave / fatal prognosis


class DoshicShape(str, Enum):
    """Morphological droplet classification reflecting doshic qualities."""
    SARPA = "SARPA"          # Vata: Serpentine, irregular, zigzag, elongated
    CHHATRA = "CHHATRA"      # Pitta: Umbrella-like, rapid expanding circular ring
    MUKTAKARA = "MUKTAKARA"  # Kapha: Pearl-like, slow cohesive sphere
    JALAVAT = "JALAVAT"      # Sieve-like / net-like / porous spread
    CHURNA = "CHURNA"        # Sannipata: Highly fragmented, multi-droplet dispersal
    NIMAGNA = "NIMAGNA"      # Sinking to bottom (grave asadhya)


class CompassDirection(str, Enum):
    """Eight classical cardinal directions (Ashta Dishah) for droplet movement."""
    NORTH = "NORTH"          # Uttara: Arogyam / Longevity (Sadhya)
    EAST = "EAST"            # Purva: Recovery / Rogamuktam (Sadhya)
    WEST = "WEST"            # Pashchima: Peace / Sukhasadhya
    SOUTH = "SOUTH"          # Dakshina: Jvara / decline (Krichrasadhya)
    NORTHEAST = "NORTHEAST"  # Ishanya: Critical / Asadhya
    SOUTHEAST = "SOUTHEAST"  # Agneya: Severe crisis (Krichrasadhya)
    SOUTHWEST = "SOUTHWEST"  # Nairutya: Incurable (Asadhya)
    NORTHWEST = "NORTHWEST"  # Vayavya: Chronic decline (Asadhya)
    STATIONARY = "STATIONARY"# Sthira: Droplet stationary


class TailaBinduInput(BaseModel):
    """Clinical droplet observation and fluid mechanics telemetry input."""
    patient_id: str = Field(..., description="Target patient UUID")
    urine_temperature_c: float = Field(default=25.0, ge=10.0, le=45.0, description="Urine temperature in Celsius")
    urine_surface_tension: float = Field(..., ge=20.0, le=85.0, description="Measured urine surface tension in mN/m")
    oil_surface_tension: float = Field(default=32.5, ge=25.0, le=40.0, description="Tila taila surface tension in mN/m")
    interfacial_tension: float = Field(default=15.0, ge=5.0, le=25.0, description="Oil-urine interfacial tension in mN/m")
    semi_major_axis_mm: float = Field(..., ge=0.5, le=100.0, description="Major axis extent 'a' in mm")
    semi_minor_axis_mm: float = Field(..., ge=0.5, le=100.0, description="Minor axis extent 'b' in mm")
    observation_time_sec: float = Field(default=10.0, ge=0.1, le=300.0, description="Elapsed observation duration in seconds")
    direction: CompassDirection = Field(default=CompassDirection.NORTH, description="Cardinal direction of spread")
    fragment_count: int = Field(default=1, ge=1, le=50, description="Number of dispersed oil droplets")
    submerged: bool = Field(default=False, description="True if droplet sank to the bottom")
    observed_shape: Optional[DoshicShape] = Field(default=None, description="Optional manual morphology classification")


class TailaBinduOutput(BaseModel):
    """Complete diagnostic evaluation and fluid dynamics metrics."""
    session_id: str
    patient_id: str
    hospital_id: str
    evaluator_arn: str
    urine_temp: float
    surface_tension: float
    spreading_coeff: float
    spreading_velocity: float
    eccentricity: float
    circularity: float
    direction: CompassDirection
    fragment_count: int
    submerged: bool
    doshic_shape: DoshicShape
    prognosis_verdict: PrognosisVerdict
    commentary: str
    timestamp: int
    model_config = ConfigDict(from_attributes=True)


class TailaBinduSimulationRequest(BaseModel):
    """Request to synthesize classical Taila Bindu physical parameters."""
    doshic_condition: str = Field(..., description="VATA, PITTA, KAPHA, or SANNIPATA")
    urine_temp: float = Field(default=25.0, ge=15.0, le=40.0)
    drop_height_angula: float = Field(default=1.0, ge=0.5, le=3.0, description="Drop height in classical Angula (~1.5-2 cm)")


class TailaBinduSimulationResponse(BaseModel):
    """Synthesized fluid mechanics parameters for simulation testing."""
    doshic_condition: str
    simulated_surface_tension: float
    simulated_spreading_coeff: float
    semi_major_axis_mm: float
    semi_minor_axis_mm: float
    eccentricity: float
    circularity: float
    expected_direction: CompassDirection
    doshic_shape: DoshicShape
    prognosis_verdict: PrognosisVerdict
    classical_reference: str
