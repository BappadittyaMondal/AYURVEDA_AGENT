"""NCISM Practitioner Credentialing and Registration Router."""
import sqlite3
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_current_user, get_db_session, require_role
from core.database import append_audit_log
from core.security import ClinicalRole
from models.clinical import PractitionerRegistrationRequest, PractitionerResponse
from models.schemas import UserResponse

router = APIRouter(prefix="/practitioners", tags=["NCISM Practitioner Credentialing"])


@router.post("", response_model=PractitionerResponse, status_code=status.HTTP_201_CREATED)
def register_practitioner(
    request: PractitionerRegistrationRequest,
    current_user: UserResponse = Depends(require_role(ClinicalRole.SUPERINTENDENT, ClinicalRole.PHYSICIAN_RMP)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> PractitionerResponse:
    """Register and credential an Ayurvedic Practitioner under NCISM Act 2020."""
    cursor = conn.cursor()

    # Enforce tenant match
    if current_user.hospital_id != request.hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot register practitioner for a different hospital tenant"
        )

    # Check for duplicate ARN
    cursor.execute("SELECT COUNT(*) as count FROM practitioners WHERE arn = ?;", (request.arn,))
    if cursor.fetchone()["count"] > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Practitioner with ARN '{request.arn}' is already registered"
        )

    now = int(time.time())
    cursor.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute(
            """
            INSERT INTO practitioners (
                arn, hospital_id, full_name, qualification, university, registration_year, state_council, is_verified, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?);
            """,
            (
                request.arn,
                request.hospital_id,
                request.full_name,
                request.qualification.value,
                request.university,
                request.registration_year,
                request.state_council,
                now
            )
        )

        append_audit_log(
            conn,
            hospital_id=request.hospital_id,
            actor_id=current_user.user_id,
            action="CREDENTIAL_PRACTITIONER",
            entity_type="PRACTITIONER",
            entity_id=request.arn,
            details={
                "arn": request.arn,
                "qualification": request.qualification.value,
                "state_council": request.state_council
            }
        )
        cursor.execute("COMMIT;")
    except Exception:
        cursor.execute("ROLLBACK;")
        raise

    return PractitionerResponse(
        arn=request.arn,
        hospital_id=request.hospital_id,
        full_name=request.full_name,
        qualification=request.qualification,
        university=request.university,
        registration_year=request.registration_year,
        state_council=request.state_council,
        is_verified=True,
        created_at=now
    )


@router.get("/{arn}", response_model=PractitionerResponse)
def get_practitioner(
    arn: str,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> PractitionerResponse:
    """Fetch practitioner credentials by NCISM Ayush Registration Number (ARN)."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT arn, hospital_id, full_name, qualification, university, registration_year, state_council, is_verified, created_at "
        "FROM practitioners WHERE arn = ? AND hospital_id = ?;",
        (arn, current_user.hospital_id)
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Practitioner with ARN '{arn}' not found in this hospital"
        )

    return PractitionerResponse(
        arn=row["arn"],
        hospital_id=row["hospital_id"],
        full_name=row["full_name"],
        qualification=row["qualification"],
        university=row["university"],
        registration_year=row["registration_year"],
        state_council=row["state_council"],
        is_verified=bool(row["is_verified"]),
        created_at=row["created_at"]
    )


@router.get("", response_model=List[PractitionerResponse])
def list_practitioners(
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> List[PractitionerResponse]:
    """List all credentialed practitioners within current hospital tenant."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT arn, hospital_id, full_name, qualification, university, registration_year, state_council, is_verified, created_at "
        "FROM practitioners WHERE hospital_id = ? ORDER BY full_name ASC;",
        (current_user.hospital_id,)
    )
    rows = cursor.fetchall()
    return [
        PractitionerResponse(
            arn=row["arn"],
            hospital_id=row["hospital_id"],
            full_name=row["full_name"],
            qualification=row["qualification"],
            university=row["university"],
            registration_year=row["registration_year"],
            state_council=row["state_council"],
            is_verified=bool(row["is_verified"]),
            created_at=row["created_at"]
        )
        for row in rows
    ]
