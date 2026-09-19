"""
core/iot_sensors.py - Core Engine for Phase 39: Classical Pulse Sensor & Wearable IoT Interface.
Integrates 500 Hz radial arterial waveform ingestion with classical Ayurvedic Nadi pulse diagnostics.
"""

import time
import json
import uuid
import sqlite3
from typing import Optional, List
from core.database import get_sqlite_connection, append_audit_log
from models.iot_sensors import (
    SensorRegistrationRequest,
    SensorDeviceRecord,
    WaveformPacketIngestRequest,
    WaveformAnalysisResult,
    DoshicWaveType,
)
from models.schemas import UserResponse


class IoTSensorError(Exception):
    pass


def register_iot_sensor(
    device_in: SensorRegistrationRequest,
    current_user: Optional[UserResponse] = None,
    conn: Optional[sqlite3.Connection] = None
) -> SensorDeviceRecord:
    """Registers an IoT Nadi pulse acquisition device in the hospital network."""
    now = int(time.time())
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO iot_sensor_registrations (
                device_id, hospital_id, device_model, sampling_rate_hz,
                calibration_factor, assigned_ward_or_clinic, is_active, registered_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                device_model=excluded.device_model,
                sampling_rate_hz=excluded.sampling_rate_hz,
                calibration_factor=excluded.calibration_factor,
                assigned_ward_or_clinic=excluded.assigned_ward_or_clinic,
                is_active=1;
            """,
            (
                device_in.device_id,
                device_in.hospital_id,
                device_in.device_model.value,
                device_in.sampling_rate_hz,
                device_in.calibration_factor,
                device_in.assigned_ward_or_clinic,
                now,
            )
        )

        user_id = current_user.user_id if current_user else "SYSTEM"
        append_audit_log(
            conn,
            device_in.hospital_id,
            user_id,
            "REGISTER_DEVICE",
            "IOT_SENSOR",
            device_in.device_id,
            {
                "device_model": device_in.device_model.value,
                "sampling_rate_hz": device_in.sampling_rate_hz,
                "ward": device_in.assigned_ward_or_clinic
            }
        )
        conn.commit()
        return get_registered_sensor(device_in.device_id, conn=conn)
    finally:
        if should_close:
            conn.close()


def get_registered_sensor(
    device_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> Optional[SensorDeviceRecord]:
    """Retrieves a registered IoT sensor record."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM iot_sensor_registrations WHERE device_id = ?;", (device_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return SensorDeviceRecord(
            device_id=row["device_id"],
            hospital_id=row["hospital_id"],
            device_model=row["device_model"],
            sampling_rate_hz=row["sampling_rate_hz"],
            calibration_factor=row["calibration_factor"],
            assigned_ward_or_clinic=row["assigned_ward_or_clinic"],
            is_active=bool(row["is_active"]),
            registered_at=row["registered_at"]
        )
    finally:
        if should_close:
            conn.close()


def analyze_raw_waveform_samples(
    samples: List[float],
    sampling_rate_hz: int,
    calibration_factor: float
) -> dict:
    """
    DSP algorithm to compute arterial pulse features from radial pressure samples:
    - Calibrated amplitudes
    - Systolic peak & Diastolic notch
    - Rise time (foot to peak)
    - Pulse Wave Velocity (PWV) proxy
    - Radial Reflection Index (RI)
    - Doshic classification
    """
    calibrated = [s * calibration_factor for s in samples]
    n = len(calibrated)
    if n < 10:
        raise IoTSensorError("Insufficient samples for waveform analysis.")

    min_val = min(calibrated)
    max_val = max(calibrated)

    # Locate peak indices
    peak_idx = calibrated.index(max_val)
    # Estimate foot index before peak
    foot_idx = 0
    min_before = calibrated[0]
    for i in range(peak_idx):
        if calibrated[i] <= min_before:
            min_before = calibrated[i]
            foot_idx = i

    # Rise time in seconds
    dt = 1.0 / float(sampling_rate_hz)
    rise_time_s = max(0.01, (peak_idx - foot_idx) * dt)

    # Search for dicrotic notch after peak
    notch_val = max_val * 0.45
    notch_idx = min(n - 1, peak_idx + int(0.15 * sampling_rate_hz))
    if notch_idx < n:
        notch_val = calibrated[notch_idx]

    # Pulse Wave Velocity estimation (m/s) based on rise-time correlation
    pwv = round(max(3.5, min(14.0, 0.85 / rise_time_s)), 2)

    # Radial Reflection Index (RI)
    ri = round((notch_val / max(max_val, 0.001)) * 100.0, 2)
    ri = max(5.0, min(95.0, ri))

    # Heart rate estimation: find cycles via mean crossings
    mean_val = sum(calibrated) / n
    crossings = 0
    for i in range(1, n):
        if (calibrated[i - 1] < mean_val and calibrated[i] >= mean_val):
            crossings += 1
    total_duration_s = n * dt
    estimated_hr = round((crossings / max(total_duration_s, 0.1)) * 60.0, 1) if crossings > 0 else 72.0
    estimated_hr = max(40.0, min(180.0, estimated_hr))

    if pwv >= 9.0 and ri < 50.0:
        doshic_wave = DoshicWaveType.VATA_SARPA
    elif 6.5 <= pwv < 9.0 or (max_val - min_val > 50.0):
        doshic_wave = DoshicWaveType.PITTA_MANDUKA
    elif pwv < 6.5 or ri >= 55.0:
        doshic_wave = DoshicWaveType.KAPHA_HAMSA
    else:
        doshic_wave = DoshicWaveType.TRIDOSHIC_BALANCED

    return {
        "calibrated_samples": calibrated,
        "systolic_peak": round(max_val, 2),
        "diastolic_notch": round(notch_val, 2),
        "rise_time_s": round(rise_time_s, 4),
        "pwv": pwv,
        "ri": ri,
        "estimated_hr": estimated_hr,
        "doshic_wave": doshic_wave
    }


def ingest_and_analyze_waveform(
    packet_in: WaveformPacketIngestRequest,
    current_user: Optional[UserResponse] = None,
    conn: Optional[sqlite3.Connection] = None
) -> WaveformAnalysisResult:
    """Ingests raw Nadi waveform packet, processes DSP arterial metrics, and persists to DB."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        sensor = get_registered_sensor(packet_in.device_id, conn=conn)
        if not sensor:
            raise IoTSensorError(f"IoT sensor '{packet_in.device_id}' is not registered.")
        if not sensor.is_active:
            raise IoTSensorError(f"IoT sensor '{packet_in.device_id}' is currently marked inactive.")

        features = analyze_raw_waveform_samples(
            samples=packet_in.pressure_samples,
            sampling_rate_hz=sensor.sampling_rate_hz,
            calibration_factor=sensor.calibration_factor
        )

        packet_id = f"pkt-{uuid.uuid4().hex[:12]}"
        now = int(time.time())
        samples_json = json.dumps(packet_in.pressure_samples)

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO raw_nadi_waveform_packets (
                packet_id, device_id, patient_id, hospital_id, packet_index,
                pressure_samples_json, pulse_wave_velocity_mps,
                radial_reflection_index, doshic_dominant_wave, captured_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                packet_id,
                packet_in.device_id,
                packet_in.patient_id,
                packet_in.hospital_id,
                packet_in.packet_index,
                samples_json,
                features["pwv"],
                features["ri"],
                features["doshic_wave"].value,
                now,
            )
        )

        user_id = current_user.user_id if current_user else "SYSTEM"
        append_audit_log(
            conn,
            packet_in.hospital_id,
            user_id,
            "INGEST_NADI_PACKET",
            "IOT_SENSOR_PACKET",
            packet_id,
            {
                "patient_id": packet_in.patient_id,
                "pwv": features["pwv"],
                "doshic_dominant_wave": features["doshic_wave"].value
            }
        )
        conn.commit()

        return WaveformAnalysisResult(
            packet_id=packet_id,
            device_id=packet_in.device_id,
            patient_id=packet_in.patient_id,
            hospital_id=packet_in.hospital_id,
            packet_index=packet_in.packet_index,
            sample_count=len(packet_in.pressure_samples),
            pulse_wave_velocity_mps=features["pwv"],
            radial_reflection_index=features["ri"],
            doshic_dominant_wave=features["doshic_wave"],
            systolic_peak_amplitude=features["systolic_peak"],
            diastolic_notch_amplitude=features["diastolic_notch"],
            estimated_heart_rate_bpm=features["estimated_hr"],
            captured_at=now
        )
    finally:
        if should_close:
            conn.close()


def get_patient_waveform_packets(
    patient_id: str,
    limit: int = 20,
    conn: Optional[sqlite3.Connection] = None
) -> List[WaveformAnalysisResult]:
    """Fetches recently ingested arterial pulse packets for a patient."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM raw_nadi_waveform_packets
            WHERE patient_id = ?
            ORDER BY captured_at DESC
            LIMIT ?;
            """,
            (patient_id, limit)
        )
        rows = cursor.fetchall()
        results = []
        for r in rows:
            samples = json.loads(r["pressure_samples_json"])
            results.append(
                WaveformAnalysisResult(
                    packet_id=r["packet_id"],
                    device_id=r["device_id"],
                    patient_id=r["patient_id"],
                    hospital_id=r["hospital_id"],
                    packet_index=r["packet_index"],
                    sample_count=len(samples),
                    pulse_wave_velocity_mps=r["pulse_wave_velocity_mps"],
                    radial_reflection_index=r["radial_reflection_index"],
                    doshic_dominant_wave=DoshicWaveType(r["doshic_dominant_wave"]),
                    systolic_peak_amplitude=max(samples) if samples else 0.0,
                    diastolic_notch_amplitude=min(samples) if samples else 0.0,
                    estimated_heart_rate_bpm=72.0,
                    captured_at=r["captured_at"]
                )
            )
        return results
    finally:
        if should_close:
            conn.close()
