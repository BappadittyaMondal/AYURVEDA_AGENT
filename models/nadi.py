"""Pydantic schemas for Nadi Waveform Telemetry DSP and Signal Processing."""
from enum import Enum
from typing import Dict, List
from pydantic import BaseModel, Field, ConfigDict


class NadiGatiType(str, Enum):
    """Orthogonal classical Nadi Gati classifications."""
    SARPA = "SARPA"        # Vata: Serpentine, rapid, high-frequency [4.5 - 8.0 Hz]
    MANDUKA = "MANDUKA"    # Pitta: Frog-like, steep dP/dt systolic peak [2.0 - 4.5 Hz]
    HAMSA = "HAMSA"        # Kapha: Swan-like, slow sinusoidal rise [0.5 - 2.0 Hz]
    SAMANYA = "SAMANYA"    # Balanced homeostatic equilibrium


class SpectralBandPower(BaseModel):
    """Integrated spectral energy density across Tri-doshic frequency bands."""
    kapha_power_0_5_to_2_0_hz: float = Field(..., ge=0.0)
    pitta_power_2_0_to_4_5_hz: float = Field(..., ge=0.0)
    vata_power_4_5_to_8_0_hz: float = Field(..., ge=0.0)
    total_power: float = Field(..., ge=0.0)


class NadiTelemetryIngestRequest(BaseModel):
    """Raw pulse plethysmography / piezoelectric sensor telemetry ingestion."""
    patient_id: str
    device_id: str = Field(default="NADI_TARANGINI_V3")
    sampling_rate_hz: int = Field(default=250, ge=100, le=1000)
    raw_pressure_samples: List[float] = Field(..., min_length=250, description="Raw arterial pressure / voltage stream")


class NadiSimulationRequest(BaseModel):
    """Request to synthesize calibrated classical Nadi waveforms."""
    gati: NadiGatiType
    duration_seconds: float = Field(default=4.0, ge=1.0, le=30.0)
    sampling_rate_hz: int = Field(default=250, ge=100, le=1000)
    noise_level: float = Field(default=0.02, ge=0.0, le=0.5)


class NadiSimulationResponse(BaseModel):
    """Synthetic pulse telemetry output."""
    gati: NadiGatiType
    sampling_rate_hz: int
    sample_count: int
    synthetic_samples: List[float]


class NadiTelemetryProcessResponse(BaseModel):
    """Computed DSP pulse decomposition and Doshic classification."""
    session_id: str
    patient_id: str
    hospital_id: str
    device_id: str
    heart_rate_bpm: float
    max_dp_dt: float
    spectral_power: SpectralBandPower
    doshic_weights: Dict[str, float]
    primary_gati: NadiGatiType
    timestamp: int
    model_config = ConfigDict(from_attributes=True)
