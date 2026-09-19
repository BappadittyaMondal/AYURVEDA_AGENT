"""
Phase 37: REST API Router for Multi-Lingual Translation & Audio Intake
======================================================================
Provides clinical endpoints for:
1. Translating vernacular expressions across 12 Indian languages to Ayurvedic terminology
2. Processing transcribed audio intake and saving structured clinical entities
"""

import sqlite3
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_db_session
from core.multilingual import (
    translate_vernacular_clinical_concept,
    process_and_save_audio_transcript,
)
from models.multilingual import (
    VernacularTranslationRequest,
    VernacularTranslationResponse,
    AudioIntakeTranscriptCreate,
    AudioIntakeTranscriptResponse,
)
from models.schemas import UserResponse

router = APIRouter(prefix="/multilingual", tags=["Phase 37: Multi-Lingual Translation & Audio Intake"])


@router.post("/translate", response_model=VernacularTranslationResponse)
def translate_concept_endpoint(
    req: VernacularTranslationRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> VernacularTranslationResponse:
    """Translate patient's vernacular description to standardized classical Ayurvedic terminology."""
    return translate_vernacular_clinical_concept(req, conn=conn)


@router.post("/audio/transcripts", response_model=AudioIntakeTranscriptResponse, status_code=status.HTTP_201_CREATED)
def save_audio_transcript_endpoint(
    req: AudioIntakeTranscriptCreate,
    current_user: UserResponse = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_session)
) -> AudioIntakeTranscriptResponse:
    """Ingest transcribed patient speech narrative and extract standardized Ayurvedic entities."""
    return process_and_save_audio_transcript(req, conn=conn)
