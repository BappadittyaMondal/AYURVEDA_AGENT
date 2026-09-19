"""Core infrastructure package for security, database, and exceptions."""
from core.database import append_audit_log, get_db, get_sqlite_connection, init_database
from core.exceptions import (
    AmaGatingException,
    AuthenticationFailedException,
    AuthorizationDeniedException,
    ClinicalGovernanceException,
    HeavyMetalExposureExceededException,
    HerbDrugInteractionViolation,
    RecordNotFoundException,
    ScheduleE1ShodhanaMissingException,
    TenantIsolationViolationException,
)
from core.security import (
    ClinicalAction,
    ClinicalRole,
    ROLE_PERMISSIONS,
    authorize_action,
    create_access_token,
    decode_and_verify_token,
    hash_password,
    verify_password,
)

__all__ = [
    "get_db",
    "get_sqlite_connection",
    "init_database",
    "append_audit_log",
    "ClinicalRole",
    "ClinicalAction",
    "ROLE_PERMISSIONS",
    "authorize_action",
    "create_access_token",
    "decode_and_verify_token",
    "hash_password",
    "verify_password",
    "ClinicalGovernanceException",
    "AuthenticationFailedException",
    "AuthorizationDeniedException",
    "TenantIsolationViolationException",
    "HerbDrugInteractionViolation",
    "ScheduleE1ShodhanaMissingException",
    "HeavyMetalExposureExceededException",
    "AmaGatingException",
    "RecordNotFoundException",
]
