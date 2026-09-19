"""
tests/phase42/test_ayush_grid_engine.py - Unit tests for Phase 42 AYUSH GRID Bridge & Zero-Knowledge Verification.
"""

import pytest
from core.database import get_sqlite_connection, init_database
from models.schemas import UserResponse
from core.security import ClinicalRole
from models.ayush_grid import (
    AbdmBundleType,
    AyushGridStatus,
    FhirBundleDispatchReq,
    ZkProofGenerateReq,
    ZkProofVerifyReq,
)
from core.ayush_grid import (
    build_fhir_r4_ayush_bundle,
    dispatch_fhir_bundle_to_ayush_grid,
    generate_zero_knowledge_proof,
    verify_zero_knowledge_proof,
    get_patient_ayush_grid_logs,
)


@pytest.fixture
def conn():
    init_database()
    connection = get_sqlite_connection()
    yield connection
    connection.close()


@pytest.fixture
def rmp_user():
    return UserResponse(
        user_id="user-physician-001",
        hospital_id="aiia-delhi-central-001",
        username="physician_rmp",
        full_name="Dr. Ananya Sen",
        arn="ARN-NCISM-2015-8832",
        role=ClinicalRole.PHYSICIAN_RMP,
        is_active=True,
        created_at=1700000000
    )


def test_build_fhir_r4_ayush_bundle():
    clinical_data = {
        "prakriti": "Vata-Pitta",
        "vikriti": "Pitta-Vata",
        "primary_disease_namaste": "AMAVATA-01",
        "formulations": ["Simhanada Guggulu", "Dashamoola Kwatha"]
    }
    bundle = build_fhir_r4_ayush_bundle(
        hospital_id="aiia-delhi-central-001",
        patient_id="pat-p42-001",
        bundle_type=AbdmBundleType.OP_CONSULTATION_NOTE,
        clinical_data=clinical_data
    )
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "document"
    assert len(bundle["entry"]) == 2
    assert bundle["entry"][0]["resource"]["resourceType"] == "Composition"


def test_dispatch_fhir_bundle(conn, rmp_user):
    req = FhirBundleDispatchReq(
        hospital_id="aiia-delhi-central-001",
        patient_id="pat-p42-001",
        abdm_bundle_type=AbdmBundleType.DIAGNOSTIC_REPORT,
        clinical_data={"diagnostic_summary": "Grid-certified diagnostic assessment completed."}
    )
    res = dispatch_fhir_bundle_to_ayush_grid(req, current_user=rmp_user, conn=conn)
    assert res.bridge_id.startswith("abdm-")
    assert res.status == AyushGridStatus.ACKNOWLEDGED
    assert res.ack_reference.startswith("ACK-AYUSH-GRID-")

    logs = get_patient_ayush_grid_logs("pat-p42-001", conn=conn)
    assert len(logs) >= 1
    assert logs[0].bridge_id == res.bridge_id


def test_zero_knowledge_proof_generation_and_verification(conn, rmp_user):
    # 1. Patient requests ZKP commitment for verified treatment without revealing underlying condition
    gen_req = ZkProofGenerateReq(
        hospital_id="aiia-delhi-central-001",
        patient_id="pat-p42-zk-01",
        clinical_attribute="AYUSH_PANCHAKARMA_COMPLETION_CERTIFIED",
        secret_salt="SecretPatientSalt9988",
        verifier_arn="ARN-NCISM-2015-8832"
    )
    zkp_rec = generate_zero_knowledge_proof(gen_req, current_user=rmp_user, conn=conn)
    assert zkp_rec.proof_id.startswith("zkp-")
    assert zkp_rec.is_verified is True

    # 2. Third-party verifier tests proof with correct credentials -> VALID
    verify_req_valid = ZkProofVerifyReq(
        proof_id=zkp_rec.proof_id,
        revealed_attribute="AYUSH_PANCHAKARMA_COMPLETION_CERTIFIED",
        revealed_secret_salt="SecretPatientSalt9988",
        patient_id="pat-p42-zk-01"
    )
    assert verify_zero_knowledge_proof(verify_req_valid, conn=conn) is True

    # 3. Third-party verifier tests proof with forged secret or attribute -> INVALID
    verify_req_invalid = ZkProofVerifyReq(
        proof_id=zkp_rec.proof_id,
        revealed_attribute="AYUSH_PANCHAKARMA_COMPLETION_CERTIFIED",
        revealed_secret_salt="WrongForgedSalt1234",
        patient_id="pat-p42-zk-01"
    )
    assert verify_zero_knowledge_proof(verify_req_invalid, conn=conn) is False
