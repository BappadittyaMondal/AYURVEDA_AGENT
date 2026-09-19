"""
tests/phase51/test_production_readiness_engine.py - Unit tests for Phase 51 Final Production Certification & Blueprint engine.
"""

import pytest
from core.database import get_sqlite_connection, init_database
from models.schemas import UserResponse
from core.security import ClinicalRole
from models.production_readiness import (
    DeploymentTier,
    DeploymentStatus,
    HostingerVPSSpecs,
    HospitalSiteConfigCreate,
    ProductionCertCreate,
)
from core.production_readiness import (
    audit_and_certify_production_readiness,
    configure_hospital_site,
    get_hospital_site_config,
    list_production_certifications,
    ProductionReadinessError,
)


@pytest.fixture
def superintendent_user():
    return UserResponse(
        user_id="user-superintendent-001",
        hospital_id="aiia-delhi-central-001",
        username="superintendent",
        full_name="Prof. Dr. V. Sharma",
        arn="ARN-NCISM-1998-0421",
        role=ClinicalRole.SUPERINTENDENT,
        is_active=True,
        created_at=1700000000
    )


@pytest.fixture
def conn():
    init_database()
    connection = get_sqlite_connection()
    yield connection
    connection.close()


def test_audit_and_certify_production_readiness(conn, superintendent_user):
    payload = ProductionCertCreate(
        release_version="v1.0.0-PROD-CERTIFIED",
        total_tests_executed=356,
    )
    cert = audit_and_certify_production_readiness(payload, superintendent_user)
    assert cert.cert_id.startswith("cert-prod-")
    assert cert.release_version == "v1.0.0-PROD-CERTIFIED"
    assert cert.all_51_phases_verified is True
    assert cert.zero_regression_passed is True
    assert len(cert.sha256_manifest_seal) == 64
    assert cert.certified_by_superintendent_arn == "ARN-NCISM-1998-0421"
    assert len(cert.audit_tranches_summary) == 6
    assert all(t.all_passing for t in cert.audit_tranches_summary)

    all_certs = list_production_certifications()
    assert len(all_certs) >= 1
    assert any(c.cert_id == cert.cert_id for c in all_certs)


def test_hospital_site_configuration(conn, superintendent_user):
    config_req = HospitalSiteConfigCreate(
        hospital_id="aiia-delhi-central-001",
        deployment_tier=DeploymentTier.APEX_HOSPITAL,
        hostinger_vps_specs=HostingerVPSSpecs(
            cpu_cores=8,
            ram_gb=32,
            disk_storage_gb=400,
            os_distribution="Ubuntu 24.04 LTS",
            wal_sync_mode="NORMAL_WAL_ASYNC",
            automated_backup_schedule="CRON_HOURLY_PITR",
        ),
        active_modules=[
            "PHASE_01_34_CANONICAL_CLINICAL",
            "PHASE_35_51_COMPREHENSIVE",
        ],
        status=DeploymentStatus.PRODUCTION_ACTIVE,
    )

    saved_cfg = configure_hospital_site(config_req, superintendent_user)
    assert saved_cfg.hospital_id == "aiia-delhi-central-001"
    assert saved_cfg.deployment_tier == DeploymentTier.APEX_HOSPITAL
    assert saved_cfg.hostinger_vps_specs.ram_gb == 32

    retrieved = get_hospital_site_config("aiia-delhi-central-001")
    assert retrieved.config_id == saved_cfg.config_id
    assert retrieved.status == DeploymentStatus.PRODUCTION_ACTIVE
    assert "PHASE_01_34_CANONICAL_CLINICAL" in retrieved.active_modules


def test_certify_without_arn_rejected(conn):
    no_arn_user = UserResponse(
        user_id="user-superintendent-999",
        hospital_id="aiia-delhi-central-001",
        username="super_no_arn",
        full_name="Dr. Anonymous",
        arn=None,
        role=ClinicalRole.SUPERINTENDENT,
        is_active=True,
        created_at=1700000000
    )
    with pytest.raises(ProductionReadinessError):
        audit_and_certify_production_readiness(
            ProductionCertCreate(release_version="v1.0.0-PROD-TEST", total_tests_executed=100),
            no_arn_user
        )
