"""
tests/phase39/test_iot_sensors_engine.py - Unit tests for Phase 39 IoT pulse sensor core DSP engine.
"""

import pytest
import math
from core.database import get_sqlite_connection, init_database
from models.schemas import UserResponse
from core.security import ClinicalRole
from models.iot_sensors import (
    SensorRegistrationRequest,
    SensorDeviceModel,
    WaveformPacketIngestRequest,
    DoshicWaveType,
)
from core.iot_sensors import (
    register_iot_sensor,
    get_registered_sensor,
    analyze_raw_waveform_samples,
    ingest_and_analyze_waveform,
    get_patient_waveform_packets,
    IoTSensorError,
)


@pytest.fixture
def conn():
    init_database()
    connection = get_sqlite_connection()
    yield connection
    connection.close()


@pytest.fixture
def rmp_user():
    return UserResponse(
        user_id="user-physician-001",
        hospital_id="aiia-delhi-central-001",
        username="physician_rmp",
        full_name="Dr. Ananya Sen",
        arn="ARN-NCISM-2015-8832",
        role=ClinicalRole.PHYSICIAN_RMP,
        is_active=True,
        created_at=1700000000
    )


def test_sensor_registration_and_retrieval(conn, rmp_user):
    req = SensorRegistrationRequest(
        device_id="NADI-PRO-T99",
        hospital_id="aiia-delhi-central-001",
        device_model=SensorDeviceModel.NADI_TARANGINI_PRO,
        sampling_rate_hz=500,
        calibration_factor=1.05,
        assigned_ward_or_clinic="OPD-KAYACHIKITSA-ROOM-1"
    )
    record = register_iot_sensor(req, current_user=rmp_user, conn=conn)
    assert record.device_id == "NADI-PRO-T99"
    assert record.sampling_rate_hz == 500
    assert record.is_active is True

    retrieved = get_registered_sensor("NADI-PRO-T99", conn=conn)
    assert retrieved is not None
    assert retrieved.assigned_ward_or_clinic == "OPD-KAYACHIKITSA-ROOM-1"


def test_waveform_dsp_vata_sarpa_detection():
    # Rapid rise time (< 0.05s at 500Hz = ~25 samples), low notch -> Vata Sarpa
    samples = []
    for i in range(200):
        if i < 15:
            samples.append(10.0 + (i / 15.0) * 80.0)
        elif i < 60:
            samples.append(90.0 - ((i - 15) / 45.0) * 50.0)
        else:
            samples.append(40.0 - ((i - 60) / 140.0) * 30.0)

    analysis = analyze_raw_waveform_samples(samples, sampling_rate_hz=500, calibration_factor=1.0)
    assert analysis["pwv"] >= 9.0
    assert analysis["doshic_wave"] == DoshicWaveType.VATA_SARPA
    assert analysis["systolic_peak"] == 90.0


def test_waveform_dsp_kapha_hamsa_detection():
    # Slow broad rise time (> 0.15s at 500Hz = 75 samples)
    samples = []
    for i in range(300):
        if i < 120:
            samples.append(20.0 + (i / 120.0) * 40.0)
        else:
            samples.append(60.0 - ((i - 120) / 180.0) * 35.0)

    analysis = analyze_raw_waveform_samples(samples, sampling_rate_hz=500, calibration_factor=1.0)
    assert analysis["pwv"] < 6.5
    assert analysis["doshic_wave"] == DoshicWaveType.KAPHA_HAMSA


def test_ingest_and_query_waveform_packet(conn, rmp_user):
    dev_req = SensorRegistrationRequest(
        device_id="AYUR-PIEZO-TEST-01",
        hospital_id="aiia-delhi-central-001",
        device_model=SensorDeviceModel.AYUR_PULSE_PIEZO,
        sampling_rate_hz=500,
        calibration_factor=1.0,
        assigned_ward_or_clinic="RESEARCH-LAB-2"
    )
    register_iot_sensor(dev_req, current_user=rmp_user, conn=conn)

    samples = [30.0 + 20.0 * math.sin(i * 0.1) for i in range(100)]
    pkt_req = WaveformPacketIngestRequest(
        device_id="AYUR-PIEZO-TEST-01",
        patient_id="pat-phase39-test-001",
        hospital_id="aiia-delhi-central-001",
        packet_index=1,
        pressure_samples=samples
    )

    result = ingest_and_analyze_waveform(pkt_req, current_user=rmp_user, conn=conn)
    assert result.packet_id.startswith("pkt-")
    assert result.patient_id == "pat-phase39-test-001"
    assert result.sample_count == 100
    assert result.pulse_wave_velocity_mps > 0

    history = get_patient_waveform_packets("pat-phase39-test-001", conn=conn)
    assert len(history) >= 1
    assert history[0].packet_id == result.packet_id
