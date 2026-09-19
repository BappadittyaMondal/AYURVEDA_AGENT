"""FastAPI dependency providers for authentication, authorization, and database access."""
import sqlite3
from typing import Callable, Generator
from fastapi import Depends, Header, HTTPException, status
from config.settings import Settings, get_settings
from core.database import get_db
from core.exceptions import AuthenticationFailedException, AuthorizationDeniedException
from core.security import (
    ClinicalAction,
    ClinicalRole,
    authorize_action,
    decode_and_verify_token,
)
from models.schemas import UserResponse


def get_db_session() -> Generator[sqlite3.Connection, None, None]:
    """Provide a scoped SQLite connection with WAL pragmas."""
    with get_db() as conn:
        yield conn


def get_current_user_token(
    authorization: str = Header(..., description="Bearer token in format: Bearer <token>")
) -> dict:
    """Extract and validate HS256 zero-trust bearer token from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must begin with 'Bearer '"
        )
    token = authorization.split(" ")[1]
    try:
        payload = decode_and_verify_token(token)
        return payload
    except AuthenticationFailedException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message
        ) from e


def get_current_user(
    token_claims: dict = Depends(get_current_user_token),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> UserResponse:
    """Load authenticated user record from database matching token subject."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, hospital_id, username, full_name, arn, role, is_active, created_at "
        "FROM users WHERE user_id = ? AND hospital_id = ?;",
        (token_claims["sub"], token_claims["hospital_id"])
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User identity no longer active or exists in this hospital"
        )
    if not row["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is suspended"
        )
    return UserResponse(
        user_id=row["user_id"],
        hospital_id=row["hospital_id"],
        username=row["username"],
        full_name=row["full_name"],
        arn=row["arn"],
        role=ClinicalRole(row["role"]),
        is_active=bool(row["is_active"]),
        created_at=row["created_at"]
    )


def require_role(*roles: ClinicalRole) -> Callable:
    """Enforce that current actor holds one of the specified ClinicalRoles."""
    def _role_checker(user: UserResponse = Depends(get_current_user)) -> UserResponse:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of roles {[r.value for r in roles]}. Current role is '{user.role.value}'"
            )
        return user
    return _role_checker


def require_action(action: ClinicalAction) -> Callable:
    """Enforce fine-grained Least-Privilege Action permissions."""
    def _action_checker(user: UserResponse = Depends(get_current_user)) -> UserResponse:
        try:
            authorize_action(user.role, action)
            return user
        except AuthorizationDeniedException as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=exc.message
            ) from exc
    return _action_checker
