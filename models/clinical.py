"""Pydantic schemas for NCISM Practitioner Credentialing, Master Patient Index, and Prakriti Calculus."""
import re
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class PractitionerDegree(str, Enum):
    """Recognized qualifications under NCISM Act 2020."""
    BAMS = "BAMS"                                      # Bachelor of Ayurvedic Medicine and Surgery
    MD_AYU = "MD_AYU"                                  # Doctor of Medicine in Ayurveda
    MS_AYU = "MS_AYU"                                  # Master of Surgery in Ayurveda
    PHD_AYU = "PHD_AYU"                                # Doctorate in Ayurveda
    POST_GRAD_DIPLOMA_AYU = "POST_GRAD_DIPLOMA_AYU"    # PG Diploma recognized by NCISM


class Gender(str, Enum):
    """Gender categorization."""
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class PractitionerRegistrationRequest(BaseModel):
    """Registration request for NCISM-registered Ayurvedic practitioner."""
    arn: str = Field(..., description="NCISM Ayush Registration Number (ARN-NCISM-YYYY-XXXX)")
    hospital_id: str = Field(..., description="Associated hospital tenant identifier")
    full_name: str = Field(..., min_length=3, max_length=150)
    qualification: PractitionerDegree
    university: str = Field(..., min_length=2, max_length=200)
    registration_year: int = Field(..., ge=1950, le=2030)
    state_council: str = Field(..., description="State AYUSH Council (e.g., Delhi, Maharashtra, Kerala)")

    @field_validator("arn")
    @classmethod
    def validate_arn_format(cls, v: str) -> str:
        pattern = r"^ARN-NCISM-\d{4}-\d{4}$"
        if not re.match(pattern, v):
            raise ValueError("ARN must strictly follow the format: ARN-NCISM-YYYY-XXXX (e.g. ARN-NCISM-2015-8832)")
        return v


class PractitionerResponse(BaseModel):
    """Public practitioner credential representation."""
    arn: str
    hospital_id: str
    full_name: str
    qualification: PractitionerDegree
    university: str
    registration_year: int
    state_council: str
    is_verified: bool
    created_at: int
    model_config = ConfigDict(from_attributes=True)


class PatientCreateRequest(BaseModel):
    """Master Patient Index (MPI) registration schema."""
    hospital_id: str
    abha_id: Optional[str] = Field(None, description="14-digit Ayushman Bharat Health Account (XX-XXXX-XXXX-XXXX)")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    dob: str = Field(..., description="Date of birth in YYYY-MM-DD")
    gender: Gender
    contact_phone: Optional[str] = Field(None, description="10-digit mobile number")

    @field_validator("abha_id")
    @classmethod
    def validate_abha_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            pattern = r"^\d{2}-\d{4}-\d{4}-\d{4}$"
            if not re.match(pattern, v):
                raise ValueError("ABHA ID must follow the standard 14-digit format: XX-XXXX-XXXX-XXXX")
        return v

    @field_validator("dob")
    @classmethod
    def validate_dob_format(cls, v: str) -> str:
        pattern = r"^\d{4}-\d{2}-\d{2}$"
        if not re.match(pattern, v):
            raise ValueError("Date of birth must be formatted as YYYY-MM-DD")
        return v


class PatientResponse(BaseModel):
    """Patient record representation."""
    patient_id: str
    hospital_id: str
    abha_id: Optional[str] = None
    first_name: str
    last_name: str
    dob: str
    gender: Gender
    contact_phone: Optional[str] = None
    prakriti_vata: float
    prakriti_pitta: float
    prakriti_kapha: float
    created_at: int
    model_config = ConfigDict(from_attributes=True)


class PrakritiAssessmentInput(BaseModel):
    """30-parameter classical Sharirika and Manasika questionnaire responses."""
    answers: Dict[str, str] = Field(
        ...,
        description="Map of Question IDs ('Q01' to 'Q30') to chosen option ('A', 'B', 'C')"
    )


class PrakritiVectorOutput(BaseModel):
    """Computed constitutional vector coordinates on the 2-simplex."""
    assessment_id: str
    patient_id: str
    hospital_id: str
    evaluated_by_arn: str
    vata: float = Field(..., ge=0.0, le=1.0)
    pitta: float = Field(..., ge=0.0, le=1.0)
    kapha: float = Field(..., ge=0.0, le=1.0)
    primary_dosha: str
    secondary_dosha: Optional[str] = None
    classification: str
    timestamp: int
