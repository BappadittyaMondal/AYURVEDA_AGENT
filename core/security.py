"""Zero-Trust Role-Based Access Control (RBAC) and Cryptographic Token Engine."""
import base64
import hashlib
import hmac
import json
import os
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from config.settings import get_settings
from core.exceptions import AuthenticationFailedException, AuthorizationDeniedException


class ClinicalRole(str, Enum):
    """Institutional Roles in accordance with NABH AYUSH Standards & NCISM Regulations."""
    SUPERINTENDENT = "SUPERINTENDENT"      # Medical Superintendent (All permissions + clinical governance)
    PHYSICIAN_RMP = "PHYSICIAN_RMP"        # Registered Ayurvedic Medical Practitioner (BAMS/MD) with ARN
    NURSE_AYUSH = "NURSE_AYUSH"            # Panchakarma Nurse / Therapist (Bedside telemetry, Vega logs)
    PHARMACIST = "PHARMACIST"              # Ayurvedic Pharmacist (Inventory, dispensing, CoA checks)
    AUDITOR = "AUDITOR"                    # Clinical & Financial Auditor (Read-only immutable logs)
    SYSTEM_KERNEL = "SYSTEM_KERNEL"        # Internal automated deterministic safety agent
    PATIENT = "PATIENT"                    # Patient Portal self-service access


class ClinicalAction(str, Enum):
    """Fine-grained atomic actions permitted within AYURVEDA_AGENT."""
    # Clinical Actions
    CREATE_PATIENT = "CREATE_PATIENT"
    VIEW_PATIENT_PHI = "VIEW_PATIENT_PHI"
    ASSESS_TRIDOSHA = "ASSESS_TRIDOSHA"
    DRAFT_PRESCRIPTION = "DRAFT_PRESCRIPTION"
    SIGN_PRESCRIPTION = "SIGN_PRESCRIPTION"    # Requires active NCISM ARN
    REQUISITION_PANCHAKARMA = "REQUISITION_PANCHAKARMA"
    RECORD_BEDSIDE_VEGA = "RECORD_BEDSIDE_VEGA"
    ALLOCATE_DRONI_BED = "ALLOCATE_DRONI_BED"

    # Pharmacy & Vault Actions
    DISPENSE_MEDICATION = "DISPENSE_MEDICATION"
    RECORD_SHODHANA_COA = "RECORD_SHODHANA_COA"
    TRANSACT_POISON_VAULT = "TRANSACT_POISON_VAULT"

    # Governance & Emergency Actions
    AUDIT_TRAIL_READ = "AUDIT_TRAIL_READ"
    EMERGENCY_BREAK_GLASS = "EMERGENCY_BREAK_GLASS"
    SYSTEM_MAINTENANCE = "SYSTEM_MAINTENANCE"


# Least-Privilege Role-to-Action Permission Matrix (Default: DENY ALL)
ROLE_PERMISSIONS: Dict[ClinicalRole, Set[ClinicalAction]] = {
    ClinicalRole.SUPERINTENDENT: {action for action in ClinicalAction},  # Full governance
    ClinicalRole.PHYSICIAN_RMP: {
        ClinicalAction.CREATE_PATIENT,
        ClinicalAction.VIEW_PATIENT_PHI,
        ClinicalAction.ASSESS_TRIDOSHA,
        ClinicalAction.DRAFT_PRESCRIPTION,
        ClinicalAction.SIGN_PRESCRIPTION,
        ClinicalAction.REQUISITION_PANCHAKARMA,
        ClinicalAction.ALLOCATE_DRONI_BED,
        ClinicalAction.RECORD_BEDSIDE_VEGA,
        ClinicalAction.EMERGENCY_BREAK_GLASS,
        ClinicalAction.AUDIT_TRAIL_READ,
    },
    ClinicalRole.NURSE_AYUSH: {
        ClinicalAction.VIEW_PATIENT_PHI,
        ClinicalAction.RECORD_BEDSIDE_VEGA,
        ClinicalAction.ALLOCATE_DRONI_BED,
        ClinicalAction.EMERGENCY_BREAK_GLASS,
    },
    ClinicalRole.PHARMACIST: {
        ClinicalAction.DISPENSE_MEDICATION,
        ClinicalAction.RECORD_SHODHANA_COA,
        ClinicalAction.TRANSACT_POISON_VAULT,
        ClinicalAction.VIEW_PATIENT_PHI,
    },
    ClinicalRole.AUDITOR: {
        ClinicalAction.AUDIT_TRAIL_READ,
    },
    ClinicalRole.SYSTEM_KERNEL: {
        ClinicalAction.ASSESS_TRIDOSHA,
        ClinicalAction.DRAFT_PRESCRIPTION,
        ClinicalAction.AUDIT_TRAIL_READ,
    },
    ClinicalRole.PATIENT: {
        ClinicalAction.VIEW_PATIENT_PHI,
    },
}


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """Generate salted PBKDF2-HMAC-SHA256 hash formatted as salt$hash."""
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify password against stored salt$hash string."""
    try:
        salt_hex, hash_hex = stored_hash.split("$")
        salt = bytes.fromhex(salt_hex)
        expected_hash = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100000).hex()
        return hmac.compare_digest(hash_hex, expected_hash)
    except Exception:
        return False


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(
    user_id: str,
    hospital_id: str,
    role: ClinicalRole,
    arn: Optional[str] = None,
    custom_claims: Optional[Dict[str, Any]] = None,
    expires_in_minutes: Optional[int] = None
) -> str:
    """Issue cryptographically signed HS256 zero-trust bearer token."""
    settings = get_settings()
    expire_minutes = expires_in_minutes or settings.access_token_expire_minutes
    now = int(time.time())
    payload = {
        "sub": user_id,
        "hospital_id": hospital_id,
        "role": role.value,
        "arn": arn,
        "iat": now,
        "exp": now + (expire_minutes * 60)
    }
    if custom_claims:
        payload.update(custom_claims)

    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256
    ).digest()
    sig_b64 = _base64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_and_verify_token(token: str) -> Dict[str, Any]:
    """Verify HS256 signature and expiration, returning decoded token claims."""
    settings = get_settings()
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthenticationFailedException("Malformed bearer token structure")

        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(
            settings.secret_key.encode("utf-8"),
            signing_input,
            hashlib.sha256
        ).digest()

        provided_sig = _base64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, provided_sig):
            raise AuthenticationFailedException("Invalid token signature")

        payload_bytes = _base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        now = int(time.time())
        if payload.get("exp", 0) < now:
            raise AuthenticationFailedException("Token has expired")

        return payload
    except AuthenticationFailedException:
        raise
    except Exception as exc:
        raise AuthenticationFailedException(f"Token verification error: {str(exc)}") from exc


def authorize_action(role: ClinicalRole, action: ClinicalAction) -> None:
    """Enforce Least-Privilege Role Permissions. Raises AuthorizationDeniedException on violation."""
    allowed_actions = ROLE_PERMISSIONS.get(role, set())
    if action not in allowed_actions:
        raise AuthorizationDeniedException(
            f"Role '{role.value}' is not authorized to perform action '{action.value}'"
        )


# ==============================================================================
# ED25519 ASYMMETRIC CRYPTOGRAPHIC DIGITAL SIGNATURE SUITE
# ==============================================================================

def generate_ed25519_keypair() -> Tuple[str, str]:
    """
    Generates a high-security Ed25519 (Edwards-curve Digital Signature Algorithm) keypair.
    Returns (private_key_hex, public_key_hex) as 64-character hex strings (32 raw bytes each).
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    return priv_bytes.hex(), pub_bytes.hex()


def sign_prescription_ed25519(
    prescription_payload: Dict[str, Any],
    private_key_hex: str
) -> str:
    """
    Cryptographically signs a clinical prescription or governance order using the practitioner's
    private Ed25519 key. Canonicalizes JSON with deterministic sorting to prevent malleability.
    """
    canonical_bytes = json.dumps(
        prescription_payload,
        sort_keys=True,
        separators=(",", ":")
    ).encode("utf-8")

    priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
    signature = priv_key.sign(canonical_bytes)
    return signature.hex()


def verify_prescription_signature_ed25519(
    prescription_payload: Dict[str, Any],
    signature_hex: str,
    public_key_hex: str
) -> bool:
    """
    Verifies an Ed25519 cryptographic signature against the canonical prescription payload
    and practitioner's registered public key.
    Returns True if valid; False if forged, corrupted, or signature verification fails.
    """
    try:
        canonical_bytes = json.dumps(
            prescription_payload,
            sort_keys=True,
            separators=(",", ":")
        ).encode("utf-8")

        pub_key = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        pub_key.verify(bytes.fromhex(signature_hex), canonical_bytes)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False

