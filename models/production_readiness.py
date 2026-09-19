"""
models/production_readiness.py - Pydantic schemas for Phase 51 Final Production Certification & Blueprint.
Tables 108 & 109: production_release_certifications, hospital_site_configurations.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from enum import Enum


class DeploymentTier(str, Enum):
    APEX_HOSPITAL = "APEX_HOSPITAL"
    REGIONAL_CENTRE = "REGIONAL_CENTRE"
    PRIMARY_CLINIC = "PRIMARY_CLINIC"


class DeploymentStatus(str, Enum):
    PRODUCTION_ACTIVE = "PRODUCTION_ACTIVE"
    MAINTENANCE = "MAINTENANCE"
    DECOMMISSIONED = "DECOMMISSIONED"


class HostingerVPSSpecs(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cpu_cores: int = Field(default=8, description="Allocated vCPU cores")
    ram_gb: int = Field(default=32, description="Allocated RAM in GB")
    disk_storage_gb: int = Field(default=400, description="NVMe SSD storage in GB")
    os_distribution: str = Field(default="Ubuntu 24.04 LTS", description="Host OS")
    wal_sync_mode: str = Field(default="NORMAL_WAL_ASYNC", description="SQLite WAL synchronization tier")
    automated_backup_schedule: str = Field(default="CRON_HOURLY_PITR", description="Snapshot schedule")


class HospitalSiteConfigCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hospital_id: str = Field(..., description="Target Hospital ID")
    deployment_tier: DeploymentTier = Field(default=DeploymentTier.APEX_HOSPITAL)
    hostinger_vps_specs: HostingerVPSSpecs = Field(default_factory=HostingerVPSSpecs)
    active_modules: List[str] = Field(
        default_factory=lambda: [
            "PHASE_01_34_CANONICAL_CLINICAL",
            "PHASE_35_EMERGENCY_BREAKGLASS",
            "PHASE_36_HERB_DRUG_MATRIX",
            "PHASE_37_MULTILINGUAL_INTAKE",
            "PHASE_38_TELE_AYUSH_EPRESCRIPTION",
            "PHASE_39_IOT_PULSE_DSP",
            "PHASE_40_VISION_DIAGNOSTICS",
            "PHASE_41_PATIENT_PWA_PORTAL",
            "PHASE_42_AYUSH_GRID_ZKP",
            "PHASE_43_OFFLINE_EDGE_SYNC",
            "PHASE_44_PHARMACOVIGILANCE_NPVCC",
            "PHASE_45_CTRI_CLINICAL_TRIALS",
            "PHASE_46_IPD_NURSING_CARE",
            "PHASE_47_OPD_QUEUE_FLOW",
            "PHASE_48_PHARMACY_BARCODE_LOTS",
            "PHASE_49_DISASTER_RECOVERY_PITR",
            "PHASE_50_ZERO_TRUST_PEN_AUDIT",
            "PHASE_51_PRODUCTION_CERTIFICATION",
        ]
    )
    status: DeploymentStatus = Field(default=DeploymentStatus.PRODUCTION_ACTIVE)


class HospitalSiteConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    config_id: str
    hospital_id: str
    deployment_tier: DeploymentTier
    hostinger_vps_specs: HostingerVPSSpecs
    active_modules: List[str]
    status: DeploymentStatus
    updated_at: int


class PhaseAuditResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tranche_name: str
    phases_covered: str
    modules_verified: int
    tables_count: int
    all_passing: bool


class ProductionCertCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    release_version: str = Field(default="v1.0.0-PROD-CERTIFIED", description="Release semantic version tag")
    total_tests_executed: int = Field(default=356, description="Total automated test cases executed")


class ProductionCertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cert_id: str
    release_version: str
    all_51_phases_verified: bool
    zero_regression_passed: bool
    total_tests_executed: int
    sha256_manifest_seal: str
    certified_by_superintendent_arn: str
    certified_at: int
    audit_tranches_summary: List[PhaseAuditResult]
