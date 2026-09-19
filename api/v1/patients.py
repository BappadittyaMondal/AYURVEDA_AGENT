"""Master Patient Index (MPI) and ABHA ID Binding Router."""
import sqlite3
import time
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from api.dependencies import get_current_user, get_db_session, require_action
from core.database import append_audit_log
from core.security import ClinicalAction
from models.clinical import Gender, PatientCreateRequest, PatientResponse
from models.schemas import UserResponse

router = APIRouter(prefix="/patients", tags=["Master Patient Index (MPI) & ABHA"])


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    request: PatientCreateRequest,
    current_user: UserResponse = Depends(require_action(ClinicalAction.CREATE_PATIENT)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> PatientResponse:
    """Register a new patient into the Master Patient Index with ABHA binding."""
    cursor = conn.cursor()

    if current_user.hospital_id != request.hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot register patient for another hospital tenant"
        )

    # Check for duplicate ABHA ID if provided
    if request.abha_id:
        cursor.execute("SELECT patient_id FROM patients WHERE abha_id = ?;", (request.abha_id,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Patient with ABHA ID '{request.abha_id}' is already registered in the National Index"
            )

    patient_id = f"pat-{uuid.uuid4().hex[:12]}"
    now = int(time.time())

    cursor.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute(
            """
            INSERT INTO patients (
                patient_id, hospital_id, abha_id, first_name, last_name, dob, gender,
                contact_phone, prakriti_vata, prakriti_pitta, prakriti_kapha, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.3333, 0.3333, 0.3334, ?);
            """,
            (
                patient_id,
                request.hospital_id,
                request.abha_id,
                request.first_name,
                request.last_name,
                request.dob,
                request.gender.value,
                request.contact_phone,
                now
            )
        )

        append_audit_log(
            conn,
            hospital_id=request.hospital_id,
            actor_id=current_user.user_id,
            action="CREATE_PATIENT_MPI",
            entity_type="PATIENT",
            entity_id=patient_id,
            details={"abha_id": request.abha_id, "name": f"{request.first_name} {request.last_name}"}
        )
        cursor.execute("COMMIT;")
    except Exception:
        cursor.execute("ROLLBACK;")
        raise

    return PatientResponse(
        patient_id=patient_id,
        hospital_id=request.hospital_id,
        abha_id=request.abha_id,
        first_name=request.first_name,
        last_name=request.last_name,
        dob=request.dob,
        gender=request.gender,
        contact_phone=request.contact_phone,
        prakriti_vata=0.3333,
        prakriti_pitta=0.3333,
        prakriti_kapha=0.3334,
        created_at=now
    )


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: str,
    current_user: UserResponse = Depends(require_action(ClinicalAction.VIEW_PATIENT_PHI)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> PatientResponse:
    """Retrieve patient demographic and clinical baseline profile by ID."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT patient_id, hospital_id, abha_id, first_name, last_name, dob, gender,
               contact_phone, prakriti_vata, prakriti_pitta, prakriti_kapha, created_at
        FROM patients WHERE patient_id = ? AND hospital_id = ?;
        """,
        (patient_id, current_user.hospital_id)
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found in current hospital tenant"
        )

    return PatientResponse(
        patient_id=row["patient_id"],
        hospital_id=row["hospital_id"],
        abha_id=row["abha_id"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        dob=row["dob"],
        gender=Gender(row["gender"]),
        contact_phone=row["contact_phone"],
        prakriti_vata=float(row["prakriti_vata"]),
        prakriti_pitta=float(row["prakriti_pitta"]),
        prakriti_kapha=float(row["prakriti_kapha"]),
        created_at=row["created_at"]
    )


@router.get("", response_model=List[PatientResponse])
def search_patients(
    query: Optional[str] = Query(None, description="Search by name or ABHA ID"),
    current_user: UserResponse = Depends(require_action(ClinicalAction.VIEW_PATIENT_PHI)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> List[PatientResponse]:
    """List or search patients within the current hospital tenant."""
    cursor = conn.cursor()
    if query:
        search_pattern = f"%{query}%"
        cursor.execute(
            """
            SELECT patient_id, hospital_id, abha_id, first_name, last_name, dob, gender,
                   contact_phone, prakriti_vata, prakriti_pitta, prakriti_kapha, created_at
            FROM patients
            WHERE hospital_id = ? AND (first_name LIKE ? OR last_name LIKE ? OR abha_id LIKE ?)
            ORDER BY created_at DESC LIMIT 50;
            """,
            (current_user.hospital_id, search_pattern, search_pattern, search_pattern)
        )
    else:
        cursor.execute(
            """
            SELECT patient_id, hospital_id, abha_id, first_name, last_name, dob, gender,
                   contact_phone, prakriti_vata, prakriti_pitta, prakriti_kapha, created_at
            FROM patients WHERE hospital_id = ? ORDER BY created_at DESC LIMIT 50;
            """,
            (current_user.hospital_id,)
        )

    rows = cursor.fetchall()
    return [
        PatientResponse(
            patient_id=row["patient_id"],
            hospital_id=row["hospital_id"],
            abha_id=row["abha_id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            dob=row["dob"],
            gender=Gender(row["gender"]),
            contact_phone=row["contact_phone"],
            prakriti_vata=float(row["prakriti_vata"]),
            prakriti_pitta=float(row["prakriti_pitta"]),
            prakriti_kapha=float(row["prakriti_kapha"]),
            created_at=row["created_at"]
        )
        for row in rows
    ]
