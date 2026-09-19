"""Phase 01: Test Suite for Zero-Trust RBAC, Cryptographic Tokens, and Permission Gates."""
import time
import pytest
from core.exceptions import AuthenticationFailedException, AuthorizationDeniedException
from core.security import (
    ClinicalAction,
    ClinicalRole,
    authorize_action,
    create_access_token,
    decode_and_verify_token,
    hash_password,
    verify_password,
)


def test_password_hashing_and_verification():
    """Verify PBKDF2 salted hash generation and constant-time comparison."""
    password = "Secur3AyushPassword#2026"
    stored_hash = hash_password(password)

    assert stored_hash != password
    assert "$" in stored_hash
    assert verify_password(password, stored_hash) is True
    assert verify_password("WrongPassword", stored_hash) is False


def test_token_creation_and_decoding():
    """Verify cryptographically signed token creation, claim preservation, and decoding."""
    token = create_access_token(
        user_id="usr-physician-42",
        hospital_id="aiia-delhi-001",
        role=ClinicalRole.PHYSICIAN_RMP,
        arn="ARN-NCISM-2022-9901",
        expires_in_minutes=60
    )
    assert token is not None and len(token.split(".")) == 3

    claims = decode_and_verify_token(token)
    assert claims["sub"] == "usr-physician-42"
    assert claims["hospital_id"] == "aiia-delhi-001"
    assert claims["role"] == "PHYSICIAN_RMP"
    assert claims["arn"] == "ARN-NCISM-2022-9901"
    assert claims["exp"] > int(time.time())


def test_tampered_token_signature_rejected():
    """Verify that any modification of the token payload or signature is fail-closed rejected."""
    token = create_access_token(
        user_id="usr-01",
        hospital_id="hosp-01",
        role=ClinicalRole.NURSE_AYUSH
    )
    parts = token.split(".")
    # Tamper payload
    tampered_token = f"{parts[0]}.{parts[1][:-4]}AAAA.{parts[2]}"

    with pytest.raises(AuthenticationFailedException):
        decode_and_verify_token(tampered_token)


def test_expired_token_rejected():
    """Verify that expired tokens are immediately rejected."""
    token = create_access_token(
        user_id="usr-01",
        hospital_id="hosp-01",
        role=ClinicalRole.AUDITOR,
        expires_in_minutes=-10  # Expired in past
    )
    with pytest.raises(AuthenticationFailedException):
        decode_and_verify_token(token)


def test_role_based_action_authorization():
    """Verify fine-grained Least-Privilege Role Action Matrix."""
    # 1. Superintendent can perform all actions
    authorize_action(ClinicalRole.SUPERINTENDENT, ClinicalAction.SIGN_PRESCRIPTION)
    authorize_action(ClinicalRole.SUPERINTENDENT, ClinicalAction.EMERGENCY_BREAK_GLASS)
    authorize_action(ClinicalRole.SUPERINTENDENT, ClinicalAction.TRANSACT_POISON_VAULT)

    # 2. Physician RMP can sign prescriptions and draft
    authorize_action(ClinicalRole.PHYSICIAN_RMP, ClinicalAction.SIGN_PRESCRIPTION)
    authorize_action(ClinicalRole.PHYSICIAN_RMP, ClinicalAction.DRAFT_PRESCRIPTION)

    # 3. Nurse CANNOT sign prescriptions (Only RMP/Superintendent)
    with pytest.raises(AuthorizationDeniedException):
        authorize_action(ClinicalRole.NURSE_AYUSH, ClinicalAction.SIGN_PRESCRIPTION)

    # 4. Nurse CAN record bedside Vega telemetry
    authorize_action(ClinicalRole.NURSE_AYUSH, ClinicalAction.RECORD_BEDSIDE_VEGA)

    # 5. Auditor CANNOT dispense medications
    with pytest.raises(AuthorizationDeniedException):
        authorize_action(ClinicalRole.AUDITOR, ClinicalAction.DISPENSE_MEDICATION)

    # 6. Pharmacist can dispense and check CoA
    authorize_action(ClinicalRole.PHARMACIST, ClinicalAction.DISPENSE_MEDICATION)
    authorize_action(ClinicalRole.PHARMACIST, ClinicalAction.RECORD_SHODHANA_COA)

    # 7. Pharmacist CANNOT sign clinical prescriptions
    with pytest.raises(AuthorizationDeniedException):
        authorize_action(ClinicalRole.PHARMACIST, ClinicalAction.SIGN_PRESCRIPTION)
