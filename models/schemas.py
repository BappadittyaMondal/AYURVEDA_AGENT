"""Pydantic v2 schemas for AYURVEDA_AGENT core entities and API transport."""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict
from core.security import ClinicalRole


class HospitalTenantBase(BaseModel):
    """Base schema for hospital tenant."""
    hospital_id: str = Field(..., description="Unique hospital / institutional tenant identifier")
    name: str = Field(..., description="Full accredited institutional name")
    nabh_accreditation_status: str = Field(default="ACCREDITED_LEVEL_2")
    state_council_code: str = Field(..., description="State AYUSH Council Registration Identifier")


class HospitalTenantCreate(HospitalTenantBase):
    """Schema for registering a new hospital tenant."""
    pass


class HospitalTenantOut(HospitalTenantBase):
    """Output schema for hospital tenant."""
    created_at: int
    model_config = ConfigDict(from_attributes=True)


class UserLoginRequest(BaseModel):
    """Authentication request credentials."""
    username: str = Field(..., description="Staff username")
    password: str = Field(..., description="Plaintext password")
    hospital_id: Optional[str] = Field(default=None, description="Target hospital tenant")


class UserCreateRequest(BaseModel):
    """Staff account creation request."""
    hospital_id: str
    username: str
    password: str
    full_name: str
    role: ClinicalRole
    arn: Optional[str] = Field(default=None, description="Ayush Registration Number (mandatory for PHYSICIAN_RMP)")


class UserResponse(BaseModel):
    """Staff account public representation."""
    user_id: str
    hospital_id: str
    username: str
    full_name: str
    arn: Optional[str] = None
    role: ClinicalRole
    is_active: bool
    created_at: int
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Cryptographic Bearer Token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    hospital_id: str
    user_id: str
    role: ClinicalRole
    arn: Optional[str] = None


class SystemHealthResponse(BaseModel):
    """System health, WAL mode verification, and telemetry response."""
    status: str
    app_name: str
    version: str
    environment: str
    database_connected: bool
    journal_mode: str
    synchronous_mode: str
    foreign_keys_enabled: bool
    busy_timeout_ms: int
    timestamp: int
