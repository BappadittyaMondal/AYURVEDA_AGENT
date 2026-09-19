"""
API Endpoints for Shalakya Tantra, Netra Kriya Kalpa & ENT Microsurgical Therapeutics.
"""

import json
import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, get_db_session
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.shalakya_tantra import (
    evaluate_ophthalmic_screening,
    get_netra_roga_profile,
    initialize_shalakya_tables,
    list_all_netra_rogas,
    list_ent_procedures,
    list_tarpana_sessions,
    record_ent_procedure,
    record_tarpana_session,
)
from models.schemas import UserResponse
from models.shalakya_tantra import (
    EntProcedureCreate,
    EntProcedureResponse,
    EntTherapyType,
    KriyaKalpaType,
    NetraMandala,
    NetraPatala,
    NetraRogaProfile,
    OphthalmicScreeningRequest,
    OphthalmicScreeningResponse,
    TarpanaSessionCreate,
    TarpanaSessionResponse,
)

router = APIRouter(prefix="/shalakya", tags=["Shalakya Tantra, Netra Kriya Kalpa & ENT Engine"])


@router.get("/netra-rogas", response_model=List[NetraRogaProfile])
def list_netra_rogas(
    mandala: Optional[NetraMandala] = Query(default=None, description="Filter by anatomical Mandala (PAKSHMA, VARTMA, SHUKLA, KRISHNA, DRISHTI, SARVAGATA)"),
    patala: Optional[NetraPatala] = Query(default=None, description="Filter by anatomical Patala depth (BAHYA, PRATHAMA, DWITIYA, TRITIYA, CHATURTHA)"),
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[NetraRogaProfile]:
    """List registered classical Netra Rogas with ICD-11 dual-coding and Kriya Kalpa indications."""
    return list_all_netra_rogas(conn, mandala=mandala, patala=patala)


@router.get("/netra-rogas/{roga_code}", response_model=NetraRogaProfile)
def get_netra_roga_detail(
    roga_code: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> NetraRogaProfile:
    """Retrieve full clinical and anatomical specification of a Netra Roga by code."""
    try:
        return get_netra_roga_profile(roga_code, conn)
    except RecordNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/tarpana", response_model=TarpanaSessionResponse, status_code=status.HTTP_201_CREATED)
def log_tarpana_session(
    request: TarpanaSessionCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> TarpanaSessionResponse:
    """
    Log an ocular Tarpana Kriya Kalpa procedure session.
    Calculates exact Doshic Matrakala duration and prescribes post-care photoprotection regimen.
    """
    return record_tarpana_session(conn, current_user.hospital_id, request)


@router.get("/tarpana/patient/{patient_id}", response_model=List[TarpanaSessionResponse])
def get_patient_tarpana_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[TarpanaSessionResponse]:
    """Retrieve historical Tarpana Kriya Kalpa treatment logs for a patient."""
    return list_tarpana_sessions(patient_id, conn)


@router.post("/ophthalmic-screening", response_model=OphthalmicScreeningResponse)
def screen_ophthalmic_emergency(
    request: OphthalmicScreeningRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> OphthalmicScreeningResponse:
    """
    Ophthalmic screening triage with Acute Adhimantha (Glaucoma Crisis) Firewall.
    Triages patients presenting with severe eye pain, hemicrania, high IOP, corneal edema, or halos.
    Blocks contraindicated heating or unctuous ocular procedures (Tarpana, Seka).
    """
    return evaluate_ophthalmic_screening(request)


@router.post("/ent-procedures", response_model=EntProcedureResponse, status_code=status.HTTP_201_CREATED)
def log_ent_procedure(
    request: EntProcedureCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> EntProcedureResponse:
    """
    Execute and log an ENT micro-therapeutic procedure (Karna Purana, Karna Dhoopana, Nasya).
    Validates tympanic membrane integrity and blocks fluid instillation if perforation is detected.
    """
    try:
        return record_ent_procedure(conn, current_user.hospital_id, request)
    except ClinicalGovernanceException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("/ent-procedures/patient/{patient_id}", response_model=List[EntProcedureResponse])
def get_patient_ent_history(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session),
) -> List[EntProcedureResponse]:
    """Retrieve historical ENT micro-therapeutic procedures for a patient."""
    return list_ent_procedures(patient_id, conn)
