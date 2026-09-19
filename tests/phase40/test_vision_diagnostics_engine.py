"""
tests/phase40/test_vision_diagnostics_engine.py - Unit tests for Phase 40 Computer Vision Optical Diagnostics engine.
"""

import pytest
from core.database import get_sqlite_connection, init_database
from models.schemas import UserResponse
from core.security import ClinicalRole
from models.vision_diagnostics import (
    AnatomicalTarget,
    ColorCardStandard,
    CalibrationTargetCreate,
    OpticalInferenceRequest,
)
from core.vision_diagnostics import (
    compute_cielab_delta_e,
    create_calibration_target,
    get_calibration_target,
    analyze_optical_image,
    get_patient_vision_inferences,
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


def test_compute_cielab_delta_e():
    delta = compute_cielab_delta_e(50.0, 0.0, 0.0, 50.0, 0.0, 0.0)
    assert delta == 0.0

    delta2 = compute_cielab_delta_e(50.0, 10.0, -10.0, 50.0, 13.0, -14.0)
    assert delta2 == 5.0


def test_calibration_target_lifecycle(conn):
    req = CalibrationTargetCreate(
        target_id="CARD-CUSTOM-101",
        color_card_standard=ColorCardStandard.CUSTOM_LAB_CARD,
        reference_l=48.5,
        reference_a=1.2,
        reference_b=-0.8,
        tolerance_delta_e=1.5
    )
    rec = create_calibration_target(req, conn=conn)
    assert rec.target_id == "CARD-CUSTOM-101"
    assert rec.tolerance_delta_e == 1.5

    fetched = get_calibration_target("CARD-CUSTOM-101", conn=conn)
    assert fetched is not None
    assert fetched.reference_l == 48.5


def test_tongue_coating_ama_analysis(conn, rmp_user):
    req = OpticalInferenceRequest(
        patient_id="pat-phase40-001",
        hospital_id="aiia-delhi-central-001",
        anatomical_target=AnatomicalTarget.JIHWA_TONGUE,
        image_base64_or_bytes_hash="hash-jihwa-ama-thick-sample",
        raw_cielab_l=62.0,
        raw_cielab_a=14.0,
        raw_cielab_b=12.0,
        coating_coverage_pct=48.5
    )
    res = analyze_optical_image(req, current_user=rmp_user, conn=conn)
    assert res.inference_id.startswith("inf-")
    assert "Sama Jihwa" in res.clinical_interpretation
    assert "Ama involvement" in res.clinical_interpretation
    assert res.coating_thickness_pct == 48.5


def test_scleral_icterus_analysis(conn, rmp_user):
    # Elevated b* axis (> 10) indicates jaundice / Kamala
    req = OpticalInferenceRequest(
        patient_id="pat-phase40-002",
        hospital_id="aiia-delhi-central-001",
        anatomical_target=AnatomicalTarget.NETRA_SCLERA_EYE,
        image_base64_or_bytes_hash="hash-netra-icterus-sample",
        raw_cielab_l=78.0,
        raw_cielab_a=2.0,
        raw_cielab_b=16.0,
        calibration_target_id="TARGET-GREY-18"
    )
    res = analyze_optical_image(req, current_user=rmp_user, conn=conn)
    assert res.icterus_index is not None
    assert res.icterus_index >= 15.0
    assert "Kamala" in res.clinical_interpretation
    assert "Netra Peetata" in res.clinical_interpretation

    history = get_patient_vision_inferences("pat-phase40-002", conn=conn)
    assert len(history) >= 1
    assert history[0].inference_id == res.inference_id
