"""
API Endpoints for Rasayana Tantra, Jara Chikitsa & Longevity Medicine Engine.
"""

import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, get_db_session
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.rasayana_tantra import (
    admit_kuti_praveshika_episode,
    calculate_ojas_and_biological_age,
    get_rasayana_protocol_by_id,
    initialize_rasayana_tables,
    list_all_rasayana_protocols,
    list_kuti_praveshika_episodes,
    list_patient_ojas_evaluations,
)
from models.rasayana_tantra import (
    KutiPraveshikaAdmissionRequest,
    KutiPraveshikaAdmissionResponse,
    OjasEvaluationRequest,
    OjasEvaluationResponse,
    RasayanaMode,
    RasayanaProtocol,
    RasayanaType,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/rasayana", tags=["Rasayana Tantra, Jara Chikitsa & Longevity Engine"])


@router.get("/protocols", response_model=List[RasayanaProtocol])
def list_protocols(
    rasayana_type: Optional[RasayanaType] = Query(default=None, description="Filter by Rasayana category (KAMYA, NAIMITTIKA, AJASRIKA, MEDHYA, ACHARA)"),
    mode: Optional[RasayanaMode] = Query(default=None, description="Filter by modality (VATATAPIKA, KUTI_PRAVESHIKA)"),
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[RasayanaProtocol]:
    """List classical Rasayana formulations and longevity protocols with optional filtering."""
    initialize_rasayana_tables(conn)
    return list_all_rasayana_protocols(conn, rasayana_type=rasayana_type, mode=mode)


@router.get("/protocols/{protocol_id}", response_model=RasayanaProtocol)
def get_protocol_detail(
    protocol_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> RasayanaProtocol:
    """Retrieve full classical protocol details, target Dhatus, and indications by ID."""
    initialize_rasayana_tables(conn)
    try:
        return get_rasayana_protocol_by_id(protocol_id, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/ojas-evaluation", response_model=OjasEvaluationResponse, status_code=status.HTTP_201_CREATED)
def evaluate_ojas_and_longevity(
    request: OjasEvaluationRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> OjasEvaluationResponse:
    """
    Evaluate Ojas reserve, Vyadhikshamatwa immune index, Decadal attribute decay,
    and objective biological age differential from physiological biomarkers.
    """
    initialize_rasayana_tables(conn)
    return calculate_ojas_and_biological_age(request, current_user.hospital_id, conn)


@router.get("/ojas-evaluation/patient/{patient_id}", response_model=List[OjasEvaluationResponse])
def get_patient_ojas_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[OjasEvaluationResponse]:
    """Retrieve historical Ojas reserve and biological age evaluations for a patient."""
    initialize_rasayana_tables(conn)
    return list_patient_ojas_evaluations(patient_id, conn)


@router.post("/kuti-praveshika/admissions", response_model=KutiPraveshikaAdmissionResponse, status_code=status.HTTP_201_CREATED)
def screen_and_admit_kuti_praveshika(
    request: KutiPraveshikaAdmissionRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> KutiPraveshikaAdmissionResponse:
    """
    Screen patient for intensive Kuti Praveshika cottage retreat, enforcing
    Panchakarma pre-Shodhana verification and cardiovascular/infection safety firewalls.
    """
    initialize_rasayana_tables(conn)
    return admit_kuti_praveshika_episode(conn, current_user.hospital_id, request)


@router.get("/kuti-praveshika/patient/{patient_id}", response_model=List[KutiPraveshikaAdmissionResponse])
def get_patient_kuti_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[KutiPraveshikaAdmissionResponse]:
    """Retrieve historical Kuti Praveshika admission screening episodes for a patient."""
    initialize_rasayana_tables(conn)
    return list_kuti_praveshika_episodes(patient_id, conn)
