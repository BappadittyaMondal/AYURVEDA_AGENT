"""
tests/phase45/test_clinical_trials_engine.py - Unit tests for Phase 45 Clinical Trial Registry & Integrative Research engine.
"""

import pytest
from core.database import get_sqlite_connection, init_database
from models.schemas import UserResponse
from core.security import ClinicalRole
from models.clinical_trials import (
    ProtocolCreate,
    SubjectEnrollmentCreate,
    SubjectProgressUpdate,
    TrialStatus,
)
from core.clinical_trials import (
    register_trial_protocol,
    get_trial_protocol,
    enroll_trial_subject,
    update_subject_progress,
    compute_trial_analytics,
    ClinicalTrialError,
)


@pytest.fixture
def conn():
    init_database()
    connection = get_sqlite_connection()
    # Seed test patient for trial enrollment
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO patients (
            patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("pat-ctri-test-01", "aiia-delhi-central-001", "Girish", "Kulkarni", "1975-02-18", "MALE", "+919822334455", 1700000000)
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO patients (
            patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("pat-ctri-test-02", "aiia-delhi-central-001", "Radha", "Nair", "1980-07-22", "FEMALE", "+919822334466", 1700000000)
    )
    cursor.execute("DELETE FROM trial_cohort_subjects;")
    cursor.execute("DELETE FROM clinical_trial_protocols WHERE ctri_registration_number LIKE 'CTRI/2026/%';")
    connection.commit()
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


def test_protocol_registration_and_validation(conn, rmp_user):
    # Invalid CTRI number
    with pytest.raises(ClinicalTrialError):
        register_trial_protocol(
            ProtocolCreate(
                ctri_registration_number="INVALID_REG_123",
                trial_title="Randomized Trial of Shallaki in Knee Osteoarthritis",
                ayurvedic_intervention_arm="Shallaki Extract 500mg BD + Kshirabala Taila Matra Basti",
                control_arm="Standard Care NSAID (Aceclofenac 100mg BD)",
                sample_size_target=100,
                primary_outcome_measure="WOMAC Osteoarthritis Index at Week 12",
                principal_investigator_arn="ARN-NCISM-2015-8832"
            ),
            current_user=rmp_user,
            conn=conn
        )

    # Valid CTRI number
    req = ProtocolCreate(
        ctri_registration_number="CTRI/2026/04/098765",
        trial_title="Randomized Trial of Shallaki in Knee Osteoarthritis (Sandhigata Vata)",
        ayurvedic_intervention_arm="Shallaki Extract 500mg BD + Kshirabala Taila Matra Basti",
        control_arm="Standard Care NSAID (Aceclofenac 100mg BD)",
        sample_size_target=100,
        primary_outcome_measure="WOMAC Osteoarthritis Index at Week 12",
        principal_investigator_arn="ARN-NCISM-2015-8832"
    )
    rec = register_trial_protocol(req, current_user=rmp_user, conn=conn)
    assert rec.protocol_id.startswith("ctri-")
    assert rec.status == TrialStatus.RECRUITING

    fetched = get_trial_protocol(rec.protocol_id, conn=conn)
    assert fetched is not None
    assert fetched.trial_title == req.trial_title


def test_subject_enrollment_and_analytics(conn, rmp_user):
    req_proto = ProtocolCreate(
        ctri_registration_number="CTRI/2026/05/112233",
        trial_title="Evaluation of Nisha-Amalaki in Prediabetes (Prameha Purvarupa)",
        ayurvedic_intervention_arm="Nisha-Amalaki Granules 3g BD",
        control_arm="Diet and Lifestyle Counseling Alone",
        sample_size_target=50,
        primary_outcome_measure="HbA1c & Fasting Blood Glucose",
        principal_investigator_arn="ARN-NCISM-2015-8832"
    )
    proto = register_trial_protocol(req_proto, current_user=rmp_user, conn=conn)

    # Enroll intervention subject
    sub1 = enroll_trial_subject(
        SubjectEnrollmentCreate(
            protocol_id=proto.protocol_id,
            patient_id="pat-ctri-test-01",
            assigned_arm="INTERVENTION",
            baseline_prakriti="Kapha-Pitta",
            baseline_score=6.4
        ),
        current_user=rmp_user,
        conn=conn
    )
    # Enroll control subject
    sub2 = enroll_trial_subject(
        SubjectEnrollmentCreate(
            protocol_id=proto.protocol_id,
            patient_id="pat-ctri-test-02",
            assigned_arm="CONTROL",
            baseline_prakriti="Vata-Pitta",
            baseline_score=6.3
        ),
        current_user=rmp_user,
        conn=conn
    )

    # Update progress for intervention: HbA1c improved to 5.7
    update_subject_progress(sub1.subject_id, SubjectProgressUpdate(current_score=5.7, compliance_rate_pct=95.0), conn=conn)
    # Update progress for control: HbA1c changed to 6.2
    update_subject_progress(sub2.subject_id, SubjectProgressUpdate(current_score=6.2, compliance_rate_pct=90.0), conn=conn)

    analytics = compute_trial_analytics(proto.protocol_id, conn=conn)
    assert analytics.total_enrolled == 2
    assert analytics.intervention_count == 1
    assert analytics.control_count == 1
    assert analytics.mean_delta_improvement_intervention == 0.7  # 6.4 - 5.7
    assert analytics.mean_delta_improvement_control == 0.1      # 6.3 - 6.2
    assert analytics.overall_compliance_rate_pct == 92.5
