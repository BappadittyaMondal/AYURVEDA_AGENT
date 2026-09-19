"""Authentication, Token Issuance, and User Management Router."""
import sqlite3
import time
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from config.settings import Settings, get_settings
from api.dependencies import get_current_user, get_db_session, require_role
from core.database import append_audit_log
from core.security import (
    ClinicalRole,
    create_access_token,
    hash_password,
    verify_password,
)
from models.schemas import (
    TokenResponse,
    UserCreateRequest,
    UserLoginRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])


@router.post("/login", response_model=TokenResponse)
def login_for_access_token(
    credentials: UserLoginRequest,
    conn: sqlite3.Connection = Depends(get_db_session),
    settings: Settings = Depends(get_settings)
) -> TokenResponse:
    """Authenticate institutional staff credentials and issue a zero-trust bearer token."""
    cursor = conn.cursor()
    hospital_id = credentials.hospital_id or settings.default_hospital_id

    cursor.execute(
        "SELECT user_id, hospital_id, username, password_hash, full_name, arn, role, is_active "
        "FROM users WHERE username = ? AND hospital_id = ?;",
        (credentials.username, hospital_id)
    )
    user = cursor.fetchone()
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username, password, or hospital tenant"
        )
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    role = ClinicalRole(user["role"])
    token = create_access_token(
        user_id=user["user_id"],
        hospital_id=user["hospital_id"],
        role=role,
        arn=user["arn"],
        expires_in_minutes=settings.access_token_expire_minutes
    )

    append_audit_log(
        conn,
        hospital_id=user["hospital_id"],
        actor_id=user["user_id"],
        action="USER_LOGIN_SUCCESS",
        entity_type="AUTH",
        entity_id=user["user_id"],
        details={"username": user["username"], "role": user["role"]}
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        hospital_id=user["hospital_id"],
        user_id=user["user_id"],
        role=role,
        arn=user["arn"]
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """Retrieve profile of currently authenticated actor."""
    return current_user


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_staff_account(
    request: UserCreateRequest,
    current_user: UserResponse = Depends(require_role(ClinicalRole.SUPERINTENDENT)),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> UserResponse:
    """Create a new staff user account (Requires SUPERINTENDENT role)."""
    # Enforce tenant match: Superintendent cannot create user for another hospital unless explicitly super-authorized
    if current_user.hospital_id != request.hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create staff for another hospital tenant"
        )

    # Physician RMP must have ARN
    if request.role == ClinicalRole.PHYSICIAN_RMP and not request.arn:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Mandatory requirement: PHYSICIAN_RMP must have an active NCISM Ayush Registration Number (ARN)"
        )

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE username = ?;", (request.username,))
    if cursor.fetchone()["cnt"] > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{request.username}' already registered"
        )

    user_id = f"user-{uuid.uuid4().hex[:12]}"
    pw_hash = hash_password(request.password)
    now = int(time.time())

    cursor.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute(
            """
            INSERT INTO users (user_id, hospital_id, username, password_hash, full_name, arn, role, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?);
            """,
            (user_id, request.hospital_id, request.username, pw_hash, request.full_name, request.arn, request.role.value, now)
        )
        append_audit_log(
            conn,
            hospital_id=request.hospital_id,
            actor_id=current_user.user_id,
            action="CREATE_STAFF_USER",
            entity_type="USER",
            entity_id=user_id,
            details={"username": request.username, "role": request.role.value, "arn": request.arn}
        )
        cursor.execute("COMMIT;")
    except Exception:
        cursor.execute("ROLLBACK;")
        raise

    return UserResponse(
        user_id=user_id,
        hospital_id=request.hospital_id,
        username=request.username,
        full_name=request.full_name,
        arn=request.arn,
        role=request.role,
        is_active=True,
        created_at=now
    )
