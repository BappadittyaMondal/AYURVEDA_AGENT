"""
models/iot_sensors.py - Data models for Phase 39: Classical Pulse Sensor & Wearable IoT Interface.
Tables 84 & 85: iot_sensor_registrations, raw_nadi_waveform_packets.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class SensorDeviceModel(str, Enum):
    NADI_TARANGINI_PRO = "NADI_TARANGINI_PRO_V3"
    AYUR_PULSE_PIEZO = "AYUR_PULSE_PIEZO_500HZ"
    OPTICAL_PPG_ARRAY = "OPTICAL_PPG_TRISENSOR"
    BIO_IMPEDANCE_RADIAL = "BIO_IMPEDANCE_RADIAL_EXACT"


class DoshicWaveType(str, Enum):
    VATA_SARPA = "VATA_SARPA_FAST_ERRATIC"
    PITTA_MANDUKA = "PITTA_MANDUKA_HIGH_AMPLITUDE_BOUNDING"
    KAPHA_HAMSA = "KAPHA_HAMSA_SLOW_WAVE_BROAD"
    TRIDOSHIC_BALANCED = "TRIDOSHIC_EQUILIBRIUM"


class SensorRegistrationRequest(BaseModel):
    device_id: str = Field(..., description="Unique hardware identifier/MAC/Serial")
    hospital_id: str = Field(..., description="Hospital UUID")
    device_model: SensorDeviceModel = Field(..., description="Certified IoT sensor hardware model")
    sampling_rate_hz: int = Field(500, ge=100, le=2000, description="Acquisition rate in Hz")
    calibration_factor: float = Field(1.0, gt=0.0, le=10.0, description="Factory/clinic calibration factor")
    assigned_ward_or_clinic: str = Field(..., min_length=2, description="Assigned clinical ward or OPD room")


class SensorDeviceRecord(BaseModel):
    device_id: str
    hospital_id: str
    device_model: str
    sampling_rate_hz: int
    calibration_factor: float
    assigned_ward_or_clinic: str
    is_active: bool
    registered_at: int


class WaveformPacketIngestRequest(BaseModel):
    device_id: str = Field(..., description="Source hardware device ID")
    patient_id: str = Field(..., description="Patient UUID")
    hospital_id: str = Field(..., description="Hospital UUID")
    packet_index: int = Field(..., ge=0, description="Sequential packet counter")
    pressure_samples: List[float] = Field(..., min_length=20, max_length=5000, description="Raw radial artery pressure/PPG time-series amplitudes")


class WaveformAnalysisResult(BaseModel):
    packet_id: str
    device_id: str
    patient_id: str
    hospital_id: str
    packet_index: int
    sample_count: int
    pulse_wave_velocity_mps: float
    radial_reflection_index: float
    doshic_dominant_wave: DoshicWaveType
    systolic_peak_amplitude: float
    diastolic_notch_amplitude: float
    estimated_heart_rate_bpm: float
    captured_at: int
