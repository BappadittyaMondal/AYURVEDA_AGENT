"""
api/v1/iot_sensors.py - API Endpoints for Phase 39: Classical Pulse Sensor & Wearable IoT Interface.
"""

import sqlite3
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_current_user, get_db_session
from models.schemas import UserResponse
from models.iot_sensors import (
    SensorRegistrationRequest,
    SensorDeviceRecord,
    WaveformPacketIngestRequest,
    WaveformAnalysisResult,
)
from core.iot_sensors import (
    register_iot_sensor,
    get_registered_sensor,
    ingest_and_analyze_waveform,
    get_patient_waveform_packets,
    IoTSensorError,
)

router = APIRouter(prefix="/iot-sensors", tags=["Phase 39: IoT Pulse Sensors & Waveforms"])


@router.post(
    "/devices",
    response_model=SensorDeviceRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Register an IoT Nadi pulse acquisition sensor"
)
def register_device_endpoint(
    device_in: SensorRegistrationRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return register_iot_sensor(device_in, current_user=current_user, conn=conn)
    except IoTSensorError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/devices/{device_id}",
    response_model=SensorDeviceRecord,
    summary="Get registered IoT sensor details"
)
def get_device_endpoint(
    device_id: str,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    record = get_registered_sensor(device_id, conn=conn)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device '{device_id}' not found.")
    return record


@router.post(
    "/ingest",
    response_model=WaveformAnalysisResult,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest raw arterial waveform packet and analyze Doshic pulse metrics"
)
def ingest_waveform_endpoint(
    packet_in: WaveformPacketIngestRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
):
    try:
        return ingest_and_analyze_waveform(packet_in, current_user=current_user, conn=conn)
    except IoTSensorError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/patient/{patient_id}/packets",
    response_model=List[WaveformAnalysisResult],
    summary="Get recent arterial waveform packets for a patient"
)
def get_patient_packets_endpoint(
    patient_id: str,
    limit: int = 20,
    conn: sqlite3.Connection = Depends(get_db_session)
):
    return get_patient_waveform_packets(patient_id, limit=limit, conn=conn)
