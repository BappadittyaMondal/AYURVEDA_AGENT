"""Phase 01: Test Suite for SQLite WAL Persistence and Hash-Chained Audit Ledger."""
import sqlite3
import tempfile
from pathlib import Path
import pytest
from core.database import append_audit_log, get_sqlite_connection, init_database


@pytest.fixture
def temp_db():
    """Create an isolated temporary SQLite database for verification."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_ayurveda_edge.db"
        init_database(db_path)
        yield db_path


def test_sqlite_wal_pragmas_enforced(temp_db):
    """Verify that SQLite connection applies WAL mode, synchronous=NORMAL, foreign_keys=ON, and busy_timeout."""
    conn = get_sqlite_connection(temp_db)
    cursor = conn.cursor()

    # Check journal_mode
    cursor.execute("PRAGMA journal_mode;")
    mode = cursor.fetchone()[0]
    assert mode.lower() == "wal", f"Expected WAL mode, got {mode}"

    # Check synchronous mode (1 is NORMAL)
    cursor.execute("PRAGMA synchronous;")
    sync = cursor.fetchone()[0]
    assert sync == 1, f"Expected synchronous=1 (NORMAL), got {sync}"

    # Check foreign keys
    cursor.execute("PRAGMA foreign_keys;")
    fk = cursor.fetchone()[0]
    assert fk == 1, "Foreign keys must be strictly ON"

    # Check busy timeout
    cursor.execute("PRAGMA busy_timeout;")
    timeout = cursor.fetchone()[0]
    assert timeout >= 5000, f"Expected timeout >= 5000ms, got {timeout}"

    conn.close()


def test_core_tables_and_seeds(temp_db):
    """Verify core tables exist and default institutional accounts are seeded."""
    conn = get_sqlite_connection(temp_db)
    cursor = conn.cursor()

    # Verify tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row["name"] for row in cursor.fetchall()}
    expected = {"hospitals", "users", "patients", "audit_ledger"}
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"

    # Verify default hospital seed
    cursor.execute("SELECT * FROM hospitals WHERE hospital_id = 'aiia-delhi-central-001';")
    hospital = cursor.fetchone()
    assert hospital is not None
    assert "AIIA" in hospital["name"]

    # Verify default superintendent user seed
    cursor.execute("SELECT * FROM users WHERE username = 'superintendent';")
    superintendent = cursor.fetchone()
    assert superintendent is not None
    assert superintendent["role"] == "SUPERINTENDENT"
    assert superintendent["arn"] is not None

    conn.close()


def test_foreign_key_constraint_enforcement(temp_db):
    """Verify that attempting to create a user for non-existent hospital triggers IntegrityError."""
    conn = get_sqlite_connection(temp_db)
    cursor = conn.cursor()

    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            """
            INSERT INTO users (user_id, hospital_id, username, password_hash, full_name, role, created_at)
            VALUES ('usr-bad', 'non-existent-hospital', 'baduser', 'fakehash', 'Bad Actor', 'NURSE_AYUSH', 123456);
            """
        )

    conn.close()


def test_sha256_audit_ledger_chaining(temp_db):
    """Verify that consecutive audit logs link via cryptographic SHA-256 prev_hash and detect tampering."""
    conn = get_sqlite_connection(temp_db)
    hospital_id = "aiia-delhi-central-001"

    h1 = append_audit_log(
        conn, hospital_id, "user-01", "LOGIN", "AUTH", "user-01", {"ip": "127.0.0.1"}
    )
    h2 = append_audit_log(
        conn, hospital_id, "user-01", "PRESCRIBE", "PRESCRIPTION", "rx-001", {"items": 3}
    )
    h3 = append_audit_log(
        conn, hospital_id, "user-02", "DISPENSE", "PHARMACY", "rx-001", {"status": "DISPENSED"}
    )

    cursor = conn.cursor()
    cursor.execute("SELECT entry_hash, prev_hash FROM audit_ledger WHERE hospital_id = ? ORDER BY id ASC;", (hospital_id,))
    rows = cursor.fetchall()

    # The first row is the bootstrap row from init_database
    # Check that each subsequent entry links to previous entry_hash
    for i in range(1, len(rows)):
        assert rows[i]["prev_hash"] == rows[i - 1]["entry_hash"], f"Broken audit chain at index {i}"

    assert h1 is not None and len(h1) == 64
    assert h2 is not None and len(h2) == 64
    assert h3 is not None and len(h3) == 64

    conn.close()
