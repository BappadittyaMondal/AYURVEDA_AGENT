"""
tests/phase44/test_pharmacovigilance_engine.py - Unit tests for Phase 44 Pharmacovigilance & NPvCC Gateway.
"""

import pytest
from core.database import get_sqlite_connection, init_database
from models.schemas import UserResponse
from core.security import ClinicalRole
from models.pharmacovigilance import (
    CausalityCategory,
    NaranjoAsuQuestions,
    SuspectedLotCreate,
    AdrReportCreate,
)
from core.pharmacovigilance import (
    calculate_naranjo_asu_score,
    create_adr_report,
    export_npvcc_yellow_card,
    get_patient_adr_reports,
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


def test_naranjo_asu_scoring_certain():
    q = NaranjoAsuQuestions(
        previous_conclusive_reports=True,         # +1
        onset_after_drug=True,                    # +2
        dechallenge_improvement=True,             # +1
        rechallenge_recurrence=True,              # +2
        alternative_causes_absent=True,           # +2
        toxic_concentration_or_heavy_metal=True,  # +1
        dose_response_gradient=True,              # +1
        past_history_similar=True,                # +1
        objective_laboratory_evidence=True        # +1
    )
    score, category = calculate_naranjo_asu_score(q)
    assert score >= 9
    assert category == CausalityCategory.CERTAIN


def test_naranjo_asu_scoring_probable():
    q = NaranjoAsuQuestions(
        previous_conclusive_reports=False,        # 0
        onset_after_drug=True,                    # +2
        dechallenge_improvement=True,             # +1
        rechallenge_recurrence=False,             # 0
        alternative_causes_absent=True,           # +2
        toxic_concentration_or_heavy_metal=False, # 0
        dose_response_gradient=True,              # +1
        past_history_similar=False,               # 0
        objective_laboratory_evidence=False       # 0
    )
    score, category = calculate_naranjo_asu_score(q)
    assert score == 6
    assert category == CausalityCategory.PROBABLE


def test_adr_report_and_yellow_card_export(conn, rmp_user):
    req = AdrReportCreate(
        patient_id="pat-pv-001",
        hospital_id="aiia-delhi-central-001",
        suspected_formulation="Arogyavardhini Vati",
        batch_number="BATCH-AV-9912",
        adverse_reaction_description="Transient maculopapular cutaneous rash with mild pruritus",
        onset_latency_hours=36.0,
        naranjo_questions=NaranjoAsuQuestions(
            onset_after_drug=True,
            dechallenge_improvement=True,
            alternative_causes_absent=True
        ),
        action_taken="Formulation discontinued; prescribed Sarivadyasava and Khadirarishta",
        reporting_rmp_arn="ARN-NCISM-2015-8832",
        suspected_lot_details=SuspectedLotCreate(
            formulation_name="Arogyavardhini Vati",
            manufacturer_name="Dhootapapeshwar Ltd.",
            mfg_license_number="GA/1422-A",
            expiry_date="2028-12-31",
            chemical_heavy_metal_audit_notes="Purified Parada and Gandhaka within Pharmacopoeial safety limits"
        )
    )
    report = create_adr_report(req, current_user=rmp_user, conn=conn)
    assert report.report_id.startswith("adr-")
    assert report.suspected_lot is not None
    assert report.suspected_lot.mfg_license_number == "GA/1422-A"

    export = export_npvcc_yellow_card(report.report_id, conn=conn)
    assert export.report_id == report.report_id
    assert "<NPvCC_YellowCard_Form>" in export.xml_payload_preview
    assert "Arogyavardhini Vati" in export.xml_payload_preview

    history = get_patient_adr_reports("pat-pv-001", conn=conn)
    assert len(history) >= 1
    assert history[0].report_id == report.report_id
