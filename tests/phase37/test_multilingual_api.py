"""
Phase 37: Integration Tests for Multi-Lingual Translation & Audio Intake REST API
================================================================================
Verifies:
1. POST /api/v1/multilingual/translate
2. POST /api/v1/multilingual/audio/transcripts
"""

import tempfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from config.settings import get_settings
from core.database import get_sqlite_connection, init_database
from main import app


@pytest.fixture
def client_with_db(monkeypatch):
    """Fixture providing TestClient backed by an isolated temporary database with seeded patient."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "multilingual_api_test.db"
        init_database(test_db_path)

        # Seed test patient
        conn = get_sqlite_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("PAT-LANG-API-01", "aiia-delhi-central-001", "Aniruddha", "Chattopadhyay", "1980-08-15", "MALE", "+919876543333", 1700000000)
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        monkeypatch.setattr(settings, "database_dir", Path(tmpdir))
        monkeypatch.setattr(settings, "database_name", "multilingual_api_test.db")

        with TestClient(app) as client:
            yield client


def test_multilingual_api_endpoints(client_with_db):
    """Test translation and audio transcript ingestion via API."""
    login_resp = client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "physician_rmp", "password": "Physician@AIIA2026"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Translate Bengali phrase
    trans_payload = {
        "source_language": "bn",
        "text": "khide pai na"
    }
    trans_resp = client_with_db.post("/api/v1/multilingual/translate", json=trans_payload, headers=headers)
    assert trans_resp.status_code == 200
    data = trans_resp.json()
    assert "Aruchi" in data["standardized_ayurvedic_term"]

    # 2. Ingest Audio Transcript
    audio_payload = {
        "patient_id": "PAT-LANG-API-01",
        "hospital_id": "aiia-delhi-central-001",
        "audio_session_id": "AUDIO-SESS-001",
        "source_language": "hi",
        "raw_transcript_text": "Rogi ko jodo me dard hai."
    }
    audio_resp = client_with_db.post("/api/v1/multilingual/audio/transcripts", json=audio_payload, headers=headers)
    assert audio_resp.status_code == 201
    audio_data = audio_resp.json()
    assert len(audio_data["extracted_entities"]) >= 1
    assert "Sandhishula" in audio_data["extracted_entities"][0]["ayurvedic_concept_sanskrit"]
