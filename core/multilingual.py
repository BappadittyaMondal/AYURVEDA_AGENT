"""
Phase 37: Multi-Lingual Regional Translation & Voice-to-EHR Audio Intake Engine
==============================================================================
Implements:
1. Lexicon cache covering 12 official Indian languages (Table 80)
2. Semantic mapping of vernacular expressions to canonical Sanskrit clinical concepts
3. Audio transcript ingestion and clinical entity extraction (Table 81)
"""

import json
import sqlite3
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any

from core.database import get_sqlite_connection, append_audit_log
from models.multilingual import (
    IndianLanguage,
    ExtractedClinicalEntity,
    VernacularTranslationRequest,
    VernacularTranslationResponse,
    AudioIntakeTranscriptCreate,
    AudioIntakeTranscriptResponse,
)

CANONICAL_MULTILINGUAL_LEXICON: List[Dict[str, Any]] = [
    # 1. Hindi (hi)
    {"lang": "hi", "phrase": "bhookh nahi lagti", "phonetic": "bhūkh nahīṁ lagtī", "sanskrit": "Aruchi (Mandagni)", "crosswalk": "Anorexia / Dyspepsia", "namaste": "AYU-SYM-ARU-01", "score": 0.95},
    {"lang": "hi", "phrase": "jodo me dard", "phonetic": "joṛōṁ mēṁ dard", "sanskrit": "Sandhishula (Amavata)", "crosswalk": "Arthralgia / Joint Pain", "namaste": "AYU-SYM-SAN-02", "score": 0.94},
    {"lang": "hi", "phrase": "chhati me jalan", "phonetic": "chātī mēṁ jalan", "sanskrit": "Vidaha (Amlapitta)", "crosswalk": "Heartburn / Acid Peptic", "namaste": "AYU-SYM-AML-03", "score": 0.95},
    {"lang": "hi", "phrase": "saans lene me takleef", "phonetic": "sā̃s lēnē mēṁ taklīf", "sanskrit": "Shwasa Kashtata", "crosswalk": "Dyspnea / Breathlessness", "namaste": "AYU-SYM-SHW-04", "score": 0.96},
    
    # 2. Bengali (bn)
    {"lang": "bn", "phrase": "khide pai na", "phonetic": "khidē pāi nā", "sanskrit": "Aruchi (Mandagni)", "crosswalk": "Anorexia / Loss of Appetite", "namaste": "AYU-SYM-ARU-01", "score": 0.95},
    {"lang": "bn", "phrase": "gite gite byatha", "phonetic": "gā̃ṭhē gā̃ṭhē byathā", "sanskrit": "Sandhishula (Amavata)", "crosswalk": "Polyarthralgia", "namaste": "AYU-SYM-SAN-02", "score": 0.94},
    {"lang": "bn", "phrase": "buke jala", "phonetic": "bukē jvālā", "sanskrit": "Vidaha (Amlapitta)", "crosswalk": "Retrosternal Burning", "namaste": "AYU-SYM-AML-03", "score": 0.93},
    {"lang": "bn", "phrase": "haphani", "phonetic": "hā̃phāni", "sanskrit": "Shwasa Kashtata", "crosswalk": "Bronchospasm / Wheezing", "namaste": "AYU-SYM-SHW-04", "score": 0.95},

    # 3. Tamil (ta)
    {"lang": "ta", "phrase": "pasi edukavillai", "phonetic": "paci eṭukkavillai", "sanskrit": "Aruchi (Mandagni)", "crosswalk": "Loss of Appetite", "namaste": "AYU-SYM-ARU-01", "score": 0.95},
    {"lang": "ta", "phrase": "mootu vali", "phonetic": "mūṭṭu vali", "sanskrit": "Sandhishula (Amavata)", "crosswalk": "Joint Pain / Arthralgia", "namaste": "AYU-SYM-SAN-02", "score": 0.94},
    {"lang": "ta", "phrase": "nenjerichal", "phonetic": "neñcericcal", "sanskrit": "Vidaha (Amlapitta)", "crosswalk": "Heartburn", "namaste": "AYU-SYM-AML-03", "score": 0.94},
    {"lang": "ta", "phrase": "moochu thinaral", "phonetic": "mūccu tiṇaral", "sanskrit": "Shwasa Kashtata", "crosswalk": "Shortness of Breath", "namaste": "AYU-SYM-SHW-04", "score": 0.95},

    # 4. Telugu (te)
    {"lang": "te", "phrase": "aakali veyadam ledu", "phonetic": "ākali vēyaḍaṁ lēdu", "sanskrit": "Aruchi (Mandagni)", "crosswalk": "Loss of Appetite", "namaste": "AYU-SYM-ARU-01", "score": 0.95},
    {"lang": "te", "phrase": "keella noppulu", "phonetic": "kīḷḷa noppulu", "sanskrit": "Sandhishula (Amavata)", "crosswalk": "Joint Pains", "namaste": "AYU-SYM-SAN-02", "score": 0.94},
    {"lang": "te", "phrase": "gundelo manta", "phonetic": "gundelō maṇṭa", "sanskrit": "Vidaha (Amlapitta)", "crosswalk": "Chest Burning / Pyrosis", "namaste": "AYU-SYM-AML-03", "score": 0.94},
    {"lang": "te", "phrase": "aayasamu", "phonetic": "āyāsamu", "sanskrit": "Shwasa Kashtata", "crosswalk": "Exertional Dyspnea", "namaste": "AYU-SYM-SHW-04", "score": 0.94},

    # 5. Marathi (mr)
    {"lang": "mr", "phrase": "bhook lagat nahi", "phonetic": "bhūka lāgata nāhī", "sanskrit": "Aruchi (Mandagni)", "crosswalk": "Anorexia", "namaste": "AYU-SYM-ARU-01", "score": 0.95},
    {"lang": "mr", "phrase": "sandhidukhi", "phonetic": "sandhidukhī", "sanskrit": "Sandhishula (Amavata)", "crosswalk": "Arthritis / Joint Pains", "namaste": "AYU-SYM-SAN-02", "score": 0.96},
    {"lang": "mr", "phrase": "chhatit jall", "phonetic": "chātīta jaḷajaḷa", "sanskrit": "Vidaha (Amlapitta)", "crosswalk": "Acidity / Burning Chest", "namaste": "AYU-SYM-AML-03", "score": 0.95},
    {"lang": "mr", "phrase": "shvasacha tras", "phonetic": "śvāsācā trāsa", "sanskrit": "Shwasa Kashtata", "crosswalk": "Breathing Difficulty", "namaste": "AYU-SYM-SHW-04", "score": 0.95},

    # 6. Gujarati (gu)
    {"lang": "gu", "phrase": "bhookh nathi lagti", "phonetic": "bhūkha nathī lāgatī", "sanskrit": "Aruchi (Mandagni)", "crosswalk": "Dyspepsia", "namaste": "AYU-SYM-ARU-01", "score": 0.95},
    {"lang": "gu", "phrase": "sandhivao", "phonetic": "sandhivā", "sanskrit": "Sandhishula (Amavata)", "crosswalk": "Rheumatoid Arthritis Presentation", "namaste": "AYU-SYM-SAN-02", "score": 0.95},
    {"lang": "gu", "phrase": "chhati ma balan", "phonetic": "chātī māṁ baḷatara", "sanskrit": "Vidaha (Amlapitta)", "crosswalk": "Heartburn", "namaste": "AYU-SYM-AML-03", "score": 0.94},
    {"lang": "gu", "phrase": "shwas charhvo", "phonetic": "śvāsa caḍhavō", "sanskrit": "Shwasa Kashtata", "crosswalk": "Breathlessness", "namaste": "AYU-SYM-SHW-04", "score": 0.95},

    # 7. Kannada (kn)
    {"lang": "kn", "phrase": "hasivu aagutilla", "phonetic": "hasivu āgutilla", "sanskrit": "Aruchi (Mandagni)", "crosswalk": "Lack of Appetite", "namaste": "AYU-SYM-ARU-01", "score": 0.95},
    {"lang": "kn", "phrase": "keelu novu", "phonetic": "kīlu nōvu", "sanskrit": "Sandhishula (Amavata)", "crosswalk": "Joint Ache", "namaste": "AYU-SYM-SAN-02", "score": 0.94},
    {"lang": "kn", "phrase": "edeuri", "phonetic": "ede uri", "sanskrit": "Vidaha (Amlapitta)", "crosswalk": "Chest Burn", "namaste": "AYU-SYM-AML-03", "score": 0.94},
    {"lang": "kn", "phrase": "usirata tondare", "phonetic": "usirāṭa tondare", "sanskrit": "Shwasa Kashtata", "crosswalk": "Breathing Trouble", "namaste": "AYU-SYM-SHW-04", "score": 0.95},

    # 8. Malayalam (ml)
    {"lang": "ml", "phrase": "vishappilla", "phonetic": "viśappilla", "sanskrit": "Aruchi (Mandagni)", "crosswalk": "Poor Appetite", "namaste": "AYU-SYM-ARU-01", "score": 0.95},
    {"lang": "ml", "phrase": "muttu vedana", "phonetic": "muṭṭu vēdana", "sanskrit": "Sandhishula (Amavata)", "crosswalk": "Joint Ache", "namaste": "AYU-SYM-SAN-02", "score": 0.94},
    {"lang": "ml", "phrase": "nencherichil", "phonetic": "neñcericcal", "sanskrit": "Vidaha (Amlapitta)", "crosswalk": "Gastric Acidity", "namaste": "AYU-SYM-AML-03", "score": 0.94},
    {"lang": "ml", "phrase": "shwasamuttal", "phonetic": "śvāsamuṭṭal", "sanskrit": "Shwasa Kashtata", "crosswalk": "Asthma / Dyspnea", "namaste": "AYU-SYM-SHW-04", "score": 0.95},

    # 9. Odia (or)
    {"lang": "or", "phrase": "bhoka laguni", "phonetic": "bhōka lāguni", "sanskrit": "Aruchi (Mandagni)", "crosswalk": "Loss of Hunger", "namaste": "AYU-SYM-ARU-01", "score": 0.95},
    {"lang": "or", "phrase": "ganthi bitha", "phonetic": "gāṇṭhi bitha", "sanskrit": "Sandhishula (Amavata)", "crosswalk": "Joint Pain", "namaste": "AYU-SYM-SAN-02", "score": 0.94},
    {"lang": "or", "phrase": "chhati poda", "phonetic": "chātī pōḍā", "sanskrit": "Vidaha (Amlapitta)", "crosswalk": "Chest Burn", "namaste": "AYU-SYM-AML-03", "score": 0.93},
    {"lang": "or", "phrase": "nisswasare kasta", "phonetic": "niḥśvāsare kaṣṭa", "sanskrit": "Shwasa Kashtata", "crosswalk": "Respiratory Distress", "namaste": "AYU-SYM-SHW-04", "score": 0.94},

    # 10. Punjabi (pa)
    {"lang": "pa", "phrase": "bhukh nahi lagdi", "phonetic": "bhukkha nahīṁ lagdī", "sanskrit": "Aruchi (Mandagni)", "crosswalk": "No Appetite", "namaste": "AYU-SYM-ARU-01", "score": 0.95},
    {"lang": "pa", "phrase": "jodan da dard", "phonetic": "jōṛāṁ dā dard", "sanskrit": "Sandhishula (Amavata)", "crosswalk": "Joint Pain", "namaste": "AYU-SYM-SAN-02", "score": 0.94},
    {"lang": "pa", "phrase": "kalje ch jalan", "phonetic": "kāljē 'ch jalan", "sanskrit": "Vidaha (Amlapitta)", "crosswalk": "Heartburn", "namaste": "AYU-SYM-AML-03", "score": 0.94},
    {"lang": "pa", "phrase": "saah charhna", "phonetic": "sāh caṛhnā", "sanskrit": "Shwasa Kashtata", "crosswalk": "Shortness of Breath", "namaste": "AYU-SYM-SHW-04", "score": 0.95},

    # 11. Assamese (as)
    {"lang": "as", "phrase": "bhuk laga nai", "phonetic": "bhuk lāgā nāi", "sanskrit": "Aruchi (Mandagni)", "crosswalk": "Anorexia", "namaste": "AYU-SYM-ARU-01", "score": 0.95},
    {"lang": "as", "phrase": "gathi bikh", "phonetic": "gāthi bikh", "sanskrit": "Sandhishula (Amavata)", "crosswalk": "Joint Pain", "namaste": "AYU-SYM-SAN-02", "score": 0.94},
    {"lang": "as", "phrase": "buk jola", "phonetic": "buk jvalā", "sanskrit": "Vidaha (Amlapitta)", "crosswalk": "Chest Burn", "namaste": "AYU-SYM-AML-03", "score": 0.93},
    {"lang": "as", "phrase": "uhah lout kosto", "phonetic": "uhāh l'ot kaṣṭa", "sanskrit": "Shwasa Kashtata", "crosswalk": "Breathing Problem", "namaste": "AYU-SYM-SHW-04", "score": 0.94},

    # 12. Sanskrit (sa)
    {"lang": "sa", "phrase": "aruchi", "phonetic": "aruciḥ", "sanskrit": "Aruchi (Mandagni)", "crosswalk": "Anorexia / Agnimandya", "namaste": "AYU-SYM-ARU-01", "score": 1.00},
    {"lang": "sa", "phrase": "sandhishula", "phonetic": "sandhiśūlam", "sanskrit": "Sandhishula (Amavata)", "crosswalk": "Arthralgia", "namaste": "AYU-SYM-SAN-02", "score": 1.00},
    {"lang": "sa", "phrase": "vidaha", "phonetic": "vidāhaḥ", "sanskrit": "Vidaha (Amlapitta)", "crosswalk": "Pyrosis / Internal Heat", "namaste": "AYU-SYM-AML-03", "score": 1.00},
    {"lang": "sa", "phrase": "shwasa", "phonetic": "śvāsaḥ", "sanskrit": "Shwasa Kashtata", "crosswalk": "Dyspnea", "namaste": "AYU-SYM-SHW-04", "score": 1.00},
]


def ensure_multilingual_lexicon_seeded(conn: sqlite3.Connection) -> None:
    """Populate Table 80 with the 12-language clinical lexicon cache."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM multilingual_lexicon_cache;")
    if cursor.fetchone()["count"] < 48:
        now = int(time.time())
        for item in CANONICAL_MULTILINGUAL_LEXICON:
            entry_id = f"LEX-{item['lang'].upper()}-{uuid.uuid4().hex[:6].upper()}"
            cursor.execute(
                """
                INSERT INTO multilingual_lexicon_cache (
                    entry_id, language_code, vernacular_phrase, phonetic_transcription,
                    ayurvedic_concept_sanskrit, namaste_code, confidence_score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    entry_id,
                    item["lang"],
                    item["phrase"],
                    item["phonetic"],
                    item["sanskrit"],
                    item["namaste"],
                    item["score"],
                    now
                )
            )
        conn.commit()


def translate_vernacular_clinical_concept(
    req: VernacularTranslationRequest,
    conn: Optional[sqlite3.Connection] = None
) -> VernacularTranslationResponse:
    """Map patient's vernacular input string to standardized classical Ayurvedic terminology."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        ensure_multilingual_lexicon_seeded(conn)
        cursor = conn.cursor()

        input_clean = req.text.lower().strip()
        cursor.execute(
            """
            SELECT * FROM multilingual_lexicon_cache
            WHERE language_code = ? AND vernacular_phrase = ?;
            """,
            (req.source_language.value, input_clean)
        )
        row = cursor.fetchone()

        if not row:
            # Fallback substring matching
            cursor.execute(
                """
                SELECT * FROM multilingual_lexicon_cache
                WHERE language_code = ? AND ? LIKE '%' || vernacular_phrase || '%';
                """,
                (req.source_language.value, input_clean)
            )
            row = cursor.fetchone()

        if row:
            # Match crosswalk
            crosswalk_dict = {
                "Aruchi (Mandagni)": "Anorexia / Dyspepsia",
                "Sandhishula (Amavata)": "Polyarthralgia / Joint Pain",
                "Vidaha (Amlapitta)": "Pyrosis / Heartburn",
                "Shwasa Kashtata": "Dyspnea / Shortness of Breath"
            }
            crosswalk = crosswalk_dict.get(row["ayurvedic_concept_sanskrit"], "Clinical Sign")

            return VernacularTranslationResponse(
                source_language=req.source_language,
                original_text=req.text,
                phonetic_transcription=row["phonetic_transcription"],
                standardized_ayurvedic_term=row["ayurvedic_concept_sanskrit"],
                english_clinical_crosswalk=crosswalk,
                namaste_code=row["namaste_code"],
                confidence_score=row["confidence_score"]
            )
        else:
            return VernacularTranslationResponse(
                source_language=req.source_language,
                original_text=req.text,
                phonetic_transcription="Unmatched phonetic",
                standardized_ayurvedic_term="Asiddha Lakshana (Unclassified)",
                english_clinical_crosswalk="General Malaise",
                namaste_code="AYU-SYM-GEN-99",
                confidence_score=0.45
            )
    finally:
        if should_close:
            conn.close()


def process_and_save_audio_transcript(
    req: AudioIntakeTranscriptCreate,
    conn: Optional[sqlite3.Connection] = None
) -> AudioIntakeTranscriptResponse:
    """Ingest transcribed speech audio, extract clinical entities, and persist into Table 81."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        ensure_multilingual_lexicon_seeded(conn)
        cursor = conn.cursor()

        # Query all lexicon phrases for source language
        cursor.execute(
            "SELECT * FROM multilingual_lexicon_cache WHERE language_code = ?;",
            (req.source_language.value,)
        )
        lexicon = cursor.fetchall()

        extracted: List[ExtractedClinicalEntity] = []
        text_lower = req.raw_transcript_text.lower()

        for item in lexicon:
            if item["vernacular_phrase"].lower() in text_lower:
                extracted.append(
                    ExtractedClinicalEntity(
                        vernacular_mention=item["vernacular_phrase"],
                        ayurvedic_concept_sanskrit=item["ayurvedic_concept_sanskrit"],
                        concept_domain="LAKSHANA",
                        namaste_code=item["namaste_code"],
                        icd11_tm2_code="TM2-UNSPECIFIED",
                        confidence_score=item["confidence_score"]
                    )
                )

        translated_text = "; ".join([e.ayurvedic_concept_sanskrit for e in extracted]) if extracted else "No definitive Ayurvedic symptoms detected."

        now = int(time.time())
        transcript_id = f"TR-AUDIO-{now}-{uuid.uuid4().hex[:6].upper()}"

        cursor.execute(
            """
            INSERT INTO audio_intake_transcripts (
                transcript_id, patient_id, hospital_id, audio_session_id,
                source_language, raw_transcript_text, translated_clinical_text,
                extracted_entities_json, transcribed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                transcript_id,
                req.patient_id,
                req.hospital_id,
                req.audio_session_id,
                req.source_language.value,
                req.raw_transcript_text,
                translated_text,
                json.dumps([e.model_dump() for e in extracted]),
                now
            )
        )

        append_audit_log(
            conn,
            req.hospital_id,
            "AUDIO_INTAKE_MODULE",
            "INGEST_AUDIO_TRANSCRIPT",
            "AUDIO_TRANSCRIPT",
            transcript_id,
            {"patient_id": req.patient_id, "entities_count": len(extracted), "lang": req.source_language.value}
        )
        conn.commit()

        return AudioIntakeTranscriptResponse(
            transcript_id=transcript_id,
            patient_id=req.patient_id,
            hospital_id=req.hospital_id,
            audio_session_id=req.audio_session_id,
            source_language=req.source_language,
            raw_transcript_text=req.raw_transcript_text,
            translated_clinical_text=translated_text,
            extracted_entities=extracted,
            transcribed_at=now
        )
    finally:
        if should_close:
            conn.close()
