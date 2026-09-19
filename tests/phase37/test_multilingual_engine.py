"""
Phase 37: Unit Tests for Multi-Lingual Regional Translation & Voice-to-EHR Audio Engine
========================================================================================
Verifies:
1. Lexicon cache initialization across all 12 Indian languages (Table 80)
2. Precise translation of vernacular complaints across Hindi, Bengali, Tamil, Telugu, Marathi, etc.
3. Audio intake transcription processing and entity extraction (Table 81)
"""

import pytest
import sqlite3
from core.database import get_sqlite_connection, init_database
from core.multilingual import (
    ensure_multilingual_lexicon_seeded,
    translate_vernacular_clinical_concept,
    process_and_save_audio_transcript,
)
from models.multilingual import (
    IndianLanguage,
    VernacularTranslationRequest,
    AudioIntakeTranscriptCreate,
)


@pytest.fixture
def conn():
    """Provides a thread-safe database connection."""
    init_database()
    connection = get_sqlite_connection()
    yield connection
    connection.close()


def test_multilingual_lexicon_seeding(conn):
    """Verify all 12 languages are seeded in Table 80."""
    ensure_multilingual_lexicon_seeded(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT language_code) as langs, COUNT(*) as count FROM multilingual_lexicon_cache;")
    row = cursor.fetchone()
    assert row["langs"] == 12
    assert row["count"] >= 48


def test_vernacular_translations_across_languages(conn):
    """Test clinical term mapping across different Indian language inputs."""
    # Test Hindi
    hi_resp = translate_vernacular_clinical_concept(
        VernacularTranslationRequest(source_language=IndianLanguage.HINDI, text="bhookh nahi lagti"),
        conn=conn
    )
    assert "aruchi" in hi_resp.standardized_ayurvedic_term.lower()
    assert hi_resp.confidence_score >= 0.90

    # Test Bengali
    bn_resp = translate_vernacular_clinical_concept(
        VernacularTranslationRequest(source_language=IndianLanguage.BENGALI, text="gite gite byatha"),
        conn=conn
    )
    assert "sandhishula" in bn_resp.standardized_ayurvedic_term.lower()

    # Test Tamil
    ta_resp = translate_vernacular_clinical_concept(
        VernacularTranslationRequest(source_language=IndianLanguage.TAMIL, text="nenjerichal"),
        conn=conn
    )
    assert "vidaha" in ta_resp.standardized_ayurvedic_term.lower()

    # Test Telugu
    te_resp = translate_vernacular_clinical_concept(
        VernacularTranslationRequest(source_language=IndianLanguage.TELUGU, text="aayasamu"),
        conn=conn
    )
    assert "shwasa" in te_resp.standardized_ayurvedic_term.lower()

    # Test Marathi
    mr_resp = translate_vernacular_clinical_concept(
        VernacularTranslationRequest(source_language=IndianLanguage.MARATHI, text="sandhidukhi"),
        conn=conn
    )
    assert "sandhishula" in mr_resp.standardized_ayurvedic_term.lower()


def test_audio_transcript_entity_extraction(conn):
    """Verify entity extraction and persistence into Table 81."""
    req = AudioIntakeTranscriptCreate(
        patient_id="PAT-AUDIO-01",
        hospital_id="aiia-delhi-central-001",
        audio_session_id="SESS-AUDIO-99",
        source_language=IndianLanguage.HINDI,
        raw_transcript_text="Rogi ko pichhle do hafte se bhookh nahi lagti aur chhati me jalan rehti hai."
    )

    resp = process_and_save_audio_transcript(req, conn=conn)
    assert resp.transcript_id.startswith("TR-AUDIO-")
    assert len(resp.extracted_entities) >= 2
    concepts = [e.ayurvedic_concept_sanskrit for e in resp.extracted_entities]
    assert any("Aruchi" in c for c in concepts)
    assert any("Vidaha" in c for c in concepts)
