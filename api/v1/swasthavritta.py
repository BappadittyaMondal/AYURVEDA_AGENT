"""
API Endpoints for Swasthavritta, Dinacharya, Ritucharya & Vega-Dharana Pathology.
"""

from datetime import datetime
import json
import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, get_db_session
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.swasthavritta import (
    ADHARANIYA_VEGAS_DATA,
    SEED_DINACHARYA_STEPS,
    audit_patient_dinacharya_routine,
    evaluate_circadian_bio_rhythm,
    evaluate_current_ritucharya,
    get_seasonal_calendar,
    initialize_swasthavritta_tables,
    log_and_evaluate_vega_suppression,
)
from models.schemas import UserResponse
from models.swasthavritta import (
    AdharaniyaVegaType,
    CircadianClockStatus,
    DinacharyaRoutineAuditRequest,
    DinacharyaRoutineAuditResponse,
    DinacharyaStep,
    RitusandhiEvaluation,
    SeasonalRegimenProfile,
    VegaPathologyResponse,
    VegaSuppressionLogRequest,
)

router = APIRouter(prefix="/swasthavritta", tags=["Swasthavritta, Dinacharya & Ritucharya Lifestyle Optimization Engine"])


@router.get("/circadian-clock", response_model=CircadianClockStatus)
def get_circadian_clock(
    hour: Optional[int] = Query(default=None, ge=0, le=23, description="Hour of day (0-23) for simulation"),
    minute: Optional[int] = Query(default=None, ge=0, le=59, description="Minute of hour (0-59)"),
    current_user: UserResponse = Depends(get_current_user),
) -> CircadianClockStatus:
    """Retrieve real-time or designated Ayurvedic circadian bio-rhythm clock status."""
    dt = None
    if hour is not None:
        m = minute if minute is not None else 0
        now = datetime.now()
        dt = datetime(now.year, now.month, now.day, hour, m)

    return evaluate_circadian_bio_rhythm(dt)


@router.get("/dinacharya/steps", response_model=List[DinacharyaStep])
def list_dinacharya_steps(
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[DinacharyaStep]:
    """List all canonical classical Dinacharya daily regimen procedures."""
    initialize_swasthavritta_tables(conn)
    return SEED_DINACHARYA_STEPS


@router.post("/dinacharya/audit", response_model=DinacharyaRoutineAuditResponse, status_code=status.HTTP_201_CREATED)
def audit_dinacharya_routine(
    request: DinacharyaRoutineAuditRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> DinacharyaRoutineAuditResponse:
    """
    Audit patient's daily routine against canonical Dinacharya principles,
    calculating bio-rhythm alignment score (0-100) and actionable corrective prescriptions.
    """
    initialize_swasthavritta_tables(conn)
    try:
        return audit_patient_dinacharya_routine(request, current_user.hospital_id, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/adharaniya-vegas", response_model=List[dict])
def list_adharaniya_vegas(
    current_user: UserResponse = Depends(get_current_user),
) -> List[dict]:
    """List all 13 classical non-suppressible natural urges and their suppression pathologies."""
    results = []
    for vega, data in ADHARANIYA_VEGAS_DATA.items():
        results.append({
            "vega_type": vega.value,
            "sanskrit_name": data["sanskrit"],
            "classical_symptoms": data["classical_symptoms"],
            "vitiated_dosha": data["vitiated_dosha"],
            "secondary_udavarta_risk": data["secondary_udavarta_risk"],
            "remediation_protocol": data["remediation"]
        })
    return results


@router.post("/vegas/log-suppression", response_model=VegaPathologyResponse, status_code=status.HTTP_201_CREATED)
def log_vega_suppression(
    request: VegaSuppressionLogRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> VegaPathologyResponse:
    """
    Log and diagnose habitual suppression of a natural urge (Adharaniya Vega Dharana).
    Computes risk of secondary Udavarta and generates classical therapeutic relief plan.
    """
    initialize_swasthavritta_tables(conn)
    try:
        return log_and_evaluate_vega_suppression(request, current_user.hospital_id, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ClinicalGovernanceException as e:
        raise HTTPException(status_code=422, detail=f"[{e.error_code}] {e.message}")


@router.get("/ritucharya/calendar", response_model=List[SeasonalRegimenProfile])
def get_ritucharya_calendar(
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[SeasonalRegimenProfile]:
    """Retrieve the classical 6-season Ritucharya and seasonal Shodhana calendar."""
    return get_seasonal_calendar(conn)


@router.get("/ritucharya/current", response_model=RitusandhiEvaluation)
def get_current_ritucharya(
    date_str: Optional[str] = Query(default=None, description="Date in YYYY-MM-DD format (default: today)"),
    current_user: UserResponse = Depends(get_current_user),
) -> RitusandhiEvaluation:
    """
    Evaluate active Ayurvedic season, detect vulnerable 14-day Ritusandhi transition,
    and identify mandatory seasonal Shodhana windows.
    """
    eval_date = None
    if date_str:
        try:
            eval_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date_str format. Must be YYYY-MM-DD (e.g. 2026-03-25)."
            )

    return evaluate_current_ritucharya(eval_date)
