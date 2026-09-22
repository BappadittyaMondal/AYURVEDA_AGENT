"""
models/prescription_parser.py - Pydantic models for Clinical Prescription Shorthand,
Dosage Form (Kalpana) Normalization, and Vernacular Herb/Tree Name Resolution.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from models.bhaishajya_kalpana import KalpanaForm


class ClinicalFrequency(str, Enum):
    """Standardized Clinical Administration Frequency."""
    OD = "OD"          # Once Daily (Ekakalam)
    BD = "BD"          # Twice Daily (Dvikalam)
    TDS = "TDS"        # Thrice Daily (Trikalam)
    QID = "QID"        # Four times Daily (Chaturthakalam)
    HS = "HS"          # At Bedtime / Night (Nishi / Shayana Kale)
    SOS = "SOS"        # As needed (Atyayika)
    STAT = "STAT"      # Immediately (Sadhya)
    MANE = "MANE"      # Morning (Pratah)
    VESPER = "VESPER"  # Evening (Sayam)


class AushadhaSevanaKala(str, Enum):
    """Classical 10 Administration Timings (Sharangadhara & Sushruta Samhita)."""
    ABHAKTA = "ABHAKTA"            # Empty stomach at dawn (pure metabolic action)
    PRAGBHAKTA = "PRAGBHAKTA"      # Ante Cibum (AC) - Immediately before food (Apana Vata)
    MADHYABHAKTA = "MADHYABHAKTA"  # Cum Cibo (CC) - Mid-meal (Samana Vata / Pachaka Pitta)
    ADHOBHAKTA = "ADHOBHAKTA"      # Post Cibum (PC) - After meals (Vyana & Udana Vata)
    SAMABHAKTA = "SAMABHAKTA"      # Cooked directly with food
    SAMUDGA = "SAMUDGA"            # Before and after light meal (Hikka, Shwasa, Kampa)
    MUHURMUHUH = "MUHURMUHUH"      # Frequently in micro-doses (Chhardi, Trishna, Visha)
    GRASA = "GRASA"                # With each morsel of food (Prana Vata / Deepana)
    GRASANTARA = "GRASANTARA"      # Between morsels (Hridroga / Prana-Vyana)
    NISHI = "NISHI"                # At bedtime / Night (Urdhva Jatrugata / Lekhana)


class VernacularHerbMatch(BaseModel):
    """Resolved medicinal plant or tree record from vernacular/trade name."""
    matched_query: str = Field(..., description="Query string supplied in prescription")
    canonical_sanskrit: str = Field(..., description="Canonical Sanskrit classical name")
    botanical_binomial: str = Field(..., description="Accepted botanical Latin binomial")
    botanical_family: str = Field(..., description="Botanical family")
    matched_vernacular_language: str = Field(..., description="Language or dialect detected (e.g. Hindi, Tamil, Bengali)")
    regional_common_name: str = Field(..., description="Regional local name matched")
    is_schedule_e1_poison: bool = Field(default=False, description="Flag for statutory poison registry")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Match confidence")


class ParsedPrescriptionItem(BaseModel):
    """Individual drug item extracted and normalized from clinical shorthand."""
    raw_line: str = Field(..., description="Original raw prescription line string")
    formulation_name: str = Field(..., description="Identified drug, herb, or compound name")
    matched_herb: Optional[VernacularHerbMatch] = Field(default=None, description="Resolved botanical/classical herb")
    dosage_form: Optional[KalpanaForm] = Field(default=None, description="Normalized Bhaishajya Kalpana form")
    dosage_form_raw: Optional[str] = Field(default=None, description="Raw form abbreviation (e.g. tab, kw, ch)")
    dose_amount: Optional[str] = Field(default=None, description="Extracted numerical quantity and unit (e.g. 2 tabs, 15 mL)")
    frequency: Optional[ClinicalFrequency] = Field(default=None, description="Standardized frequency (OD, BD, TDS, etc.)")
    administration_timing: Optional[AushadhaSevanaKala] = Field(default=None, description="Classical timing (AC, PC, etc.)")
    anupana_carrier: Optional[str] = Field(default=None, description="Prescribed carrier liquid (e.g. warm water, honey, milk)")
    duration: Optional[str] = Field(default=None, description="Prescribed course duration (e.g. 15 days, 1 month)")
    schedule_e1_alert: bool = Field(default=False, description="Whether item contains a statutory Schedule E-1 substance")
    special_instructions: List[str] = Field(default_factory=list, description="Extracted dietary or cautionary notes")


class PrescriptionTextParseRequest(BaseModel):
    """Request payload containing raw transcribed prescription text."""
    raw_prescription_text: str = Field(..., description="Doctor's unstructured or transcribed prescription text")
    prescriber_arn: Optional[str] = Field(default=None, description="NCISM ARN of attending physician if available")
    patient_id: Optional[str] = Field(default=None, description="Patient identifier")


class PrescriptionTextParseResponse(BaseModel):
    """Structured response containing all parsed items, safety alerts, and governance status."""
    total_lines_processed: int
    items_extracted: List[ParsedPrescriptionItem]
    schedule_e1_items_detected: List[str]
    unrecognized_tokens: List[str]
    requires_rmp_verification: bool = True
    governance_status: str = "DRAFT_PARSED_PRESCRIPTION"


class HandwrittenImageUploadRequest(BaseModel):
    """Payload for submitting photographic or scanned handwritten prescription images."""
    image_base64: str = Field(..., description="Base64 encoded JPEG, PNG, or WEBP image string")
    filename: Optional[str] = Field(default="prescription.jpg", description="Originating filename")
    prescriber_arn: Optional[str] = Field(default=None, description="Attending NCISM practitioner ARN")
    patient_id: Optional[str] = Field(default=None, description="Patient hospital registration identifier")

