"""Nadi Waveform Digital Signal Processing (DSP) & Telemetry Router."""
import json
import sqlite3
import time
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_current_user, get_db_session, require_action
from core.database import append_audit_log
from core.nadi_dsp import decompose_nadi_waveform, generate_synthetic_nadi
from core.security import ClinicalAction
from models.nadi import (
    NadiGatiType,
    NadiSimulationRequest,
    NadiSimulationResponse,
    NadiTelemetryIngestRequest,
    NadiTelemetryProcessResponse,
    SpectralBandPower,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/nadi", tags=["Nadi Waveform Telemetry DSP Engine"])


@router.post("/process", response_model=NadiTelemetryProcessResponse, status_code=status.HTTP_201_CREATED)
def process_nadi_telemetry(
    request: NadiTelemetryIngestRequest,
    current_user: UserResponse = Depends(require_action(ClinicalAction.ASSESS_TRIDOSHA)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> NadiTelemetryProcessResponse:
    """
    Ingest continuous radial artery pressure telemetry (fs >= 100 Hz), execute zero-phase
    Butterworth filtering, calculate FFT power spectrum, and decompose into Tri-doshic weights.
    """
    cursor = conn.cursor()

    cursor.execute(
        "SELECT patient_id, hospital_id FROM patients WHERE patient_id = ? AND hospital_id = ?;",
        (request.patient_id, current_user.hospital_id)
    )
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{request.patient_id}' not found in current hospital tenant"
        )

    # Execute DSP Pipeline
    dsp_results = decompose_nadi_waveform(
        request.raw_pressure_samples,
        fs=request.sampling_rate_hz
    )

    session_id = f"nad-{uuid.uuid4().hex[:12]}"
    now = int(time.time())

    hr = dsp_results["heart_rate_bpm"]
    max_dp = dsp_results["max_dp_dt"]
    spec: SpectralBandPower = dsp_results["spectral_power"]
    weights = dsp_results["doshic_weights"]
    gati: NadiGatiType = dsp_results["primary_gati"]

    cursor.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute(
            """
            INSERT INTO nadi_telemetry_sessions (
                session_id, patient_id, hospital_id, device_id, sampling_rate_hz,
                raw_samples_count, heart_rate_bpm, doshic_power_v, doshic_power_p,
                doshic_power_k, primary_gati, spectral_metrics_json, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                session_id,
                request.patient_id,
                current_user.hospital_id,
                request.device_id,
                request.sampling_rate_hz,
                len(request.raw_pressure_samples),
                hr,
                weights["vata"],
                weights["pitta"],
                weights["kapha"],
                gati.value,
                spec.model_dump_json(),
                now
            )
        )

        append_audit_log(
            conn,
            hospital_id=current_user.hospital_id,
            actor_id=current_user.user_id,
            action="PROCESS_NADI_TELEMETRY",
            entity_type="NADI_SESSION",
            entity_id=session_id,
            details={
                "patient_id": request.patient_id,
                "device_id": request.device_id,
                "heart_rate_bpm": hr,
                "primary_gati": gati.value
            }
        )
        cursor.execute("COMMIT;")
    except Exception:
        cursor.execute("ROLLBACK;")
        raise

    return NadiTelemetryProcessResponse(
        session_id=session_id,
        patient_id=request.patient_id,
        hospital_id=current_user.hospital_id,
        device_id=request.device_id,
        heart_rate_bpm=hr,
        max_dp_dt=max_dp,
        spectral_power=spec,
        doshic_weights=weights,
        primary_gati=gati,
        timestamp=now
    )


@router.post("/simulate", response_model=NadiSimulationResponse)
def simulate_nadi_waveform(
    request: NadiSimulationRequest,
    current_user: UserResponse = Depends(get_current_user)
) -> NadiSimulationResponse:
    """
    Generate calibrated synthetic Nadi pulse telemetry modeling classical Gati kinematics
    (Sarpa, Manduka, Hamsa) for device testing and telemedicine calibration.
    """
    samples = generate_synthetic_nadi(
        gati=request.gati,
        duration_sec=request.duration_seconds,
        fs=request.sampling_rate_hz,
        noise_level=request.noise_level
    )
    return NadiSimulationResponse(
        gati=request.gati,
        sampling_rate_hz=request.sampling_rate_hz,
        sample_count=len(samples),
        synthetic_samples=samples
    )


@router.get("/patients/{patient_id}/latest", response_model=NadiTelemetryProcessResponse)
def get_latest_nadi_session(
    patient_id: str,
    current_user: UserResponse = Depends(require_action(ClinicalAction.VIEW_PATIENT_PHI)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> NadiTelemetryProcessResponse:
    """Retrieve the most recent Nadi DSP telemetry session for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT session_id, patient_id, hospital_id, device_id, heart_rate_bpm,
               doshic_power_v, doshic_power_p, doshic_power_k, primary_gati,
               spectral_metrics_json, timestamp
        FROM nadi_telemetry_sessions
        WHERE patient_id = ? AND hospital_id = ?
        ORDER BY timestamp DESC LIMIT 1;
        """,
        (patient_id, current_user.hospital_id)
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Nadi telemetry sessions found for patient '{patient_id}'"
        )

    spec = SpectralBandPower.model_validate_json(row["spectral_metrics_json"])
    return NadiTelemetryProcessResponse(
        session_id=row["session_id"],
        patient_id=row["patient_id"],
        hospital_id=row["hospital_id"],
        device_id=row["device_id"],
        heart_rate_bpm=float(row["heart_rate_bpm"]),
        max_dp_dt=0.0,
        spectral_power=spec,
        doshic_weights={
            "vata": float(row["doshic_power_v"]),
            "pitta": float(row["doshic_power_p"]),
            "kapha": float(row["doshic_power_k"])
        },
        primary_gati=NadiGatiType(row["primary_gati"]),
        timestamp=row["timestamp"]
    )
