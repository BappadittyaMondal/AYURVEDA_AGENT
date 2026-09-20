"""
tests/test_ed25519_signatures.py - Unit tests for Ed25519 PKI Digital Signatures & Database Adapter.
Verifies cryptographic non-repudiation, tamper detection, and dual-database adapter health.
"""

import tempfile
from pathlib import Path
import pytest

from core.security import (
    generate_ed25519_keypair,
    sign_prescription_ed25519,
    verify_prescription_signature_ed25519,
)
from core.database import (
    DatabaseEngineAdapter,
    DatabaseEngineType,
    init_database,
)


def test_ed25519_keypair_generation():
    """Verify Ed25519 keypair generation produces valid 32-byte (64 hex char) keys."""
    priv_hex, pub_hex = generate_ed25519_keypair()
    assert isinstance(priv_hex, str)
    assert isinstance(pub_hex, str)
    assert len(priv_hex) == 64
    assert len(pub_hex) == 64
    assert priv_hex != pub_hex


def test_ed25519_signature_and_verification():
    """Verify digital signature generation and verification for clinical prescriptions."""
    priv_hex, pub_hex = generate_ed25519_keypair()

    rx_payload = {
        "prescription_id": "RX-2026-DELHI-0099",
        "patient_id": "PAT-4401-KUMAR",
        "prescriber_arn": "ARN-NCISM-2015-8832",
        "date": "2026-09-20",
        "medications": [
            {"formulation": "Triphala Guggulu", "dosage": "2 tabs twice daily", "anupana": "Warm water"},
            {"formulation": "Dashamoolarishta", "dosage": "20 mL with equal water", "anupana": "Jala"},
        ],
    }

    sig_hex = sign_prescription_ed25519(rx_payload, priv_hex)
    assert isinstance(sig_hex, str)
    assert len(sig_hex) == 128  # 64 bytes in hex

    is_valid = verify_prescription_signature_ed25519(rx_payload, sig_hex, pub_hex)
    assert is_valid is True


def test_ed25519_tamper_detection():
    """Verify that tampering with prescription content fails cryptographic verification."""
    priv_hex, pub_hex = generate_ed25519_keypair()

    rx_payload = {
        "prescription_id": "RX-2026-TAMPER-TEST",
        "patient_id": "PAT-9912",
        "prescriber_arn": "ARN-NCISM-2015-8832",
        "dosage_mg": 250,
    }
    sig_hex = sign_prescription_ed25519(rx_payload, priv_hex)

    # Tampered dose (e.g. 250 -> 500)
    tampered_payload = dict(rx_payload)
    tampered_payload["dosage_mg"] = 500
    assert verify_prescription_signature_ed25519(tampered_payload, sig_hex, pub_hex) is False

    # Tampered prescriber
    tampered_prescriber = dict(rx_payload)
    tampered_prescriber["prescriber_arn"] = "ARN-IMPOSTER-0000"
    assert verify_prescription_signature_ed25519(tampered_prescriber, sig_hex, pub_hex) is False


def test_ed25519_wrong_key_and_corrupt_signature():
    """Verify verification fails with wrong key or corrupt signature string."""
    priv_hex_1, pub_hex_1 = generate_ed25519_keypair()
    _, pub_hex_2 = generate_ed25519_keypair()

    payload = {"test": "data"}
    sig_hex = sign_prescription_ed25519(payload, priv_hex_1)

    # Wrong public key
    assert verify_prescription_signature_ed25519(payload, sig_hex, pub_hex_2) is False

    # Corrupt signature
    corrupt_sig = "ab" * 64
    assert verify_prescription_signature_ed25519(payload, corrupt_sig, pub_hex_1) is False

    # Malformed signature string
    assert verify_prescription_signature_ed25519(payload, "not_a_hex", pub_hex_1) is False


def test_database_engine_adapter_sqlite_wal():
    """Verify DatabaseEngineAdapter operates in SQLite WAL mode and reports healthy status."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "adapter_test.db"
    init_database(db_path)

    adapter = DatabaseEngineAdapter(
        engine_type=DatabaseEngineType.SQLITE_WAL,
        sqlite_path=db_path,
    )
    assert adapter.engine_type == DatabaseEngineType.SQLITE_WAL

    # Check health telemetry
    health = adapter.verify_engine_health()
    assert health["status"] == "HEALTHY"
    assert health["engine_type"] == "SQLITE_WAL"
    assert health["wal_enabled"] is True
    assert health["latency_ms"] >= 0.0

    # Test session context manager
    with adapter.session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM hospitals;")
        row = cursor.fetchone()
        assert row["cnt"] >= 1

    tmpdir.cleanup()
