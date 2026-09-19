"""
Phase 37: Multi-Lingual Regional Translation & Voice-to-EHR Audio Intake Models (12 Indian Languages)
=====================================================================================================
Defines schemas for:
1. 12 Indian Official Languages (Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati,
   Kannada, Malayalam, Odia, Punjabi, Assamese, Sanskrit)
2. Vernacular symptom to classical Ayurvedic clinical concept mapping
3. Speech/audio intake transcript recording and standardized entity extraction
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class IndianLanguage(str, Enum):
    """Supported 12 major Indian administrative & clinical languages."""
    HINDI = "hi"
    BENGALI = "bn"
    TAMIL = "ta"
    TELUGU = "te"
    MARATHI = "mr"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    ODIA = "or"
    PUNJABI = "pa"
    ASSAMESE = "as"
    SANSKRIT = "sa"


class ExtractedClinicalEntity(BaseModel):
    """Clinical concept extracted from vernacular patient narrative."""
    vernacular_mention: str
    ayurvedic_concept_sanskrit: str
    concept_domain: str  # LAKSHANA, NIDANA, UPATHRVA, PRAKRITI
    namaste_code: Optional[str] = None
    icd11_tm2_code: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0)


class VernacularTranslationRequest(BaseModel):
    """Translate and map patient vernacular phrase to standardized Ayurveda terminology."""
    source_language: IndianLanguage
    text: str = Field(..., min_length=1)


class VernacularTranslationResponse(BaseModel):
    """Standardized clinical concept translation."""
    source_language: IndianLanguage
    original_text: str
    phonetic_transcription: str
    standardized_ayurvedic_term: str
    english_clinical_crosswalk: str
    namaste_code: Optional[str]
    confidence_score: float


class AudioIntakeTranscriptCreate(BaseModel):
    """Record an audio transcription intake session."""
    patient_id: str
    hospital_id: str
    audio_session_id: str
    source_language: IndianLanguage
    raw_transcript_text: str = Field(..., min_length=1)


class AudioIntakeTranscriptResponse(BaseModel):
    """Processed audio intake with structured clinical entities."""
    transcript_id: str
    patient_id: str
    hospital_id: str
    audio_session_id: str
    source_language: IndianLanguage
    raw_transcript_text: str
    translated_clinical_text: str
    extracted_entities: List[ExtractedClinicalEntity]
    transcribed_at: int
