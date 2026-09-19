"""
Unit Tests for Shalya Tantra, Marma Sharira, Agnikarma & Ksharasutra Engine (Phase 24).
"""

import tempfile
from pathlib import Path
import pytest

from core.database import get_sqlite_connection, init_database
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.shalya_tantra import (
    SEED_MARMA_CATALOG,
    assess_vrana_wound,
    evaluate_ksharasutra_session,
    execute_agnikarma_session,
    get_marma_profile,
    initialize_shalya_tables,
    list_all_marmas,
    screen_marma_incision_proximity,
)
from models.shalya_tantra import (
    AgnikarmaDevice,
    AgnikarmaPattern,
    AgnikarmaSessionCreate,
    KsharasutraFistulaType,
    KsharasutraSessionCreate,
    MarmaProximityCheckRequest,
    MarmaRegion,
    MarmaType,
    VranaAssessmentCreate,
    VranaStage,
)


def get_fresh_db_with_patient():
    """Create isolated SQLite database with a seeded patient in a safe temp directory."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_shalya.db"
    init_database(db_path)
    conn = get_sqlite_connection(db_path)
    initialize_shalya_tables(conn)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("PAT-SHALYA-001", "aiia-delhi-central-001", "Dinesh", "Kashyap", "1975-05-19", "MALE", "+919876543001", 1700000000)
    )
    return tmpdir, conn


def test_marma_catalog_completeness():
    """Verify registry contains 18+ prominent Marmas covering all 5 prognostic categories."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        marmas = list_all_marmas(conn)
        assert len(marmas) >= 18

        types_found = {m.marma_type for m in marmas}
        assert MarmaType.SADYO_PRANAHARA in types_found
        assert MarmaType.KALANTARA_PRANAHARA in types_found
        assert MarmaType.VISHALYAGHNA in types_found
        assert MarmaType.VAIKALYAKARA in types_found
        assert MarmaType.RUJAKARA in types_found

        hridaya = get_marma_profile("MARMA-HRIDAYA", conn)
        assert hridaya.marma_type == MarmaType.SADYO_PRANAHARA
        assert hridaya.vulnerability_radius_cm == 5.0

        sthapani = get_marma_profile("MARMA-STHAPANI", conn)
        assert sthapani.marma_type == MarmaType.VISHALYAGHNA
    finally:
        conn.close()
        tmpdir.cleanup()


def test_marma_proximity_screening_clear():
    """Verify incision outside Marma vulnerability radius is graded CLEAR."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Distance 8.0 cm from Hridaya (radius 5.0 cm)
        req = MarmaProximityCheckRequest(
            patient_id="PAT-SHALYA-001",
            proposed_incision_site="Right lower anterolateral chest wall",
            anatomical_region=MarmaRegion.KOSHTHA,
            nearest_marma_id="MARMA-HRIDAYA",
            distance_from_marma_cm=8.0,
            surgeon_arn="AY-DL-2024-998811",
        )
        res = screen_marma_incision_proximity(req, conn)
        assert res.is_safe_incision is True
        assert res.safety_tier == "CLEAR"
        assert res.shock_resuscitation_protocol is None
    finally:
        conn.close()
        tmpdir.cleanup()


def test_sadyo_pranahara_shock_firewall_blocked():
    """Verify incision within Sadyo-Pranahara radius triggers CRITICAL_BLOCKED and shock protocol."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Distance 1.5 cm from Hridaya (radius 5.0 cm) -> Severe shock hazard!
        req = MarmaProximityCheckRequest(
            patient_id="PAT-SHALYA-001",
            proposed_incision_site="Left sternal edge 4th intercostal space",
            anatomical_region=MarmaRegion.KOSHTHA,
            nearest_marma_id="MARMA-HRIDAYA",
            distance_from_marma_cm=1.5,
            surgeon_arn="AY-DL-2024-998811",
        )
        res = screen_marma_incision_proximity(req, conn)
        assert res.is_safe_incision is False
        assert res.safety_tier == "CRITICAL_BLOCKED"
        assert res.shock_resuscitation_protocol is not None
        assert "PRANA-PRATYAGAMANA" in res.shock_resuscitation_protocol
        assert any("RE-ROUTE INCISION" in r for r in res.surgical_recommendations)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_agnikarma_samyak_dagdha_success():
    """Verify compliant Agnikarma thermal parameters yield SAMYAK_DAGDHA and post-care dressing."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        session_data = AgnikarmaSessionCreate(
            patient_id="PAT-SHALYA-001",
            anatomical_site="Calcaneal spur / Vata-Kantaka",
            dahanopakarana=AgnikarmaDevice.PANCHADHATU_SHALAKA,
            operating_temperature_c=210.0,
            contact_time_seconds=1.5,
            pattern=AgnikarmaPattern.BINDU,
            clinical_indication="Severe plantar fasciitis / Vata-Kantaka",
            practitioner_arn="AY-DL-2024-998811",
        )
        res = execute_agnikarma_session(session_data, "aiia-delhi-central-001", conn)
        assert res.session_id.startswith("AGNI-PAT-SHALYA-001-")
        assert res.burn_grade == "SAMYAK_DAGDHA"
        assert len(res.adverse_flags) == 0
        assert "Ghrita-Kumari" in res.post_care_dressing

        # Verify persisted
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agnikarma_procedure_logs WHERE session_id = ?;", (res.session_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["samya_dagdha_verified"] == 1
    finally:
        conn.close()
        tmpdir.cleanup()


def test_agnikarma_atidagdha_burn_alert():
    """Verify excessive heat or contact time flags ATIDAGDHA alert."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        session_data = AgnikarmaSessionCreate(
            patient_id="PAT-SHALYA-001",
            anatomical_site="Lateral epicondyle / Tennis elbow",
            dahanopakarana=AgnikarmaDevice.PANCHADHATU_SHALAKA,
            operating_temperature_c=285.0,  # Excessive!
            contact_time_seconds=4.0,       # Too long!
            pattern=AgnikarmaPattern.BINDU,
            clinical_indication="Sandhigata Vata / Snayu Gata Vata",
            practitioner_arn="AY-DL-2024-998811",
        )
        res = execute_agnikarma_session(session_data, "aiia-delhi-central-001", conn)
        assert res.burn_grade == "ATIDAGDHA"
        assert any("Atidagdha Alert" in f for f in res.adverse_flags)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_ksharasutra_uct_and_healing_calculus():
    """Verify Ksharasutra tracking computes cut length, percentage, and UCT correctly."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Initial track 6.0 cm, current 2.0 cm, cut = 4.0 cm over 28 days -> UCT = 7.0 days/cm
        session_data = KsharasutraSessionCreate(
            patient_id="PAT-SHALYA-001",
            fistula_type=KsharasutraFistulaType.TRANSSPHINCTERIC,
            initial_track_length_cm=6.0,
            current_track_length_cm=2.0,
            sittings_count=4,
            total_days_elapsed=28,
            active_symptoms=["Mild serous discharge"],
            practitioner_arn="AY-DL-2024-998811",
        )
        res = evaluate_ksharasutra_session(session_data, "aiia-delhi-central-001", conn)
        assert res.cut_length_cm == 4.0
        assert res.percentage_cut == 66.7
        assert res.unit_cutting_time_days_per_cm == 7.0
        assert res.healing_status == "IN_PROGRESS"

        # Complete cut-through (current = 0.0 cm)
        comp_data = KsharasutraSessionCreate(
            patient_id="PAT-SHALYA-001",
            fistula_type=KsharasutraFistulaType.TRANSSPHINCTERIC,
            initial_track_length_cm=6.0,
            current_track_length_cm=0.0,
            sittings_count=6,
            total_days_elapsed=42,
            active_symptoms=[],
            practitioner_arn="AY-DL-2024-998811",
        )
        res_comp = evaluate_ksharasutra_session(comp_data, "aiia-delhi-central-001", conn)
        assert res_comp.healing_status == "CUT_THROUGH_COMPLETE"
    finally:
        conn.close()
        tmpdir.cleanup()


def test_vrana_staging_and_shashti_upakrama():
    """Verify Dusta Vrana vs. Ruhamana Vrana staging and Shashti-Upakrama prescriptions."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # 1. Dusta Vrana (Septic, foul smell, purulent)
        dusta_data = VranaAssessmentCreate(
            patient_id="PAT-SHALYA-001",
            location="Left pretibial ulcer",
            dimensions_cm="5.0 x 3.0 x 0.8 cm",
            is_foul_smelling=True,
            has_purulent_discharge=True,
            has_healthy_granulation=False,
            edge_character="UNDERMINED",
            practitioner_arn="AY-DL-2024-998811",
        )
        res_dusta = assess_vrana_wound(dusta_data, "aiia-delhi-central-001", conn)
        assert res_dusta.wound_stage == VranaStage.DUSTA_VRANA
        assert any("Kshalana" in u for u in res_dusta.prescribed_shashti_upakramas)
        assert any("Shodhana" in u for u in res_dusta.prescribed_shashti_upakramas)
        assert "Triphala" in res_dusta.irrigation_solution

        # 2. Ruhamana Vrana (Clean granulating, sloping edge)
        ruhamana_data = VranaAssessmentCreate(
            patient_id="PAT-SHALYA-001",
            location="Left pretibial ulcer (Follow up Week 3)",
            dimensions_cm="2.5 x 1.2 x 0.2 cm",
            is_foul_smelling=False,
            has_purulent_discharge=False,
            has_healthy_granulation=True,
            edge_character="SLOPING",
            practitioner_arn="AY-DL-2024-998811",
        )
        res_ruh = assess_vrana_wound(ruhamana_data, "aiia-delhi-central-001", conn)
        assert res_ruh.wound_stage == VranaStage.RUHAMANA_VRANA
        assert any("Ropana" in u for u in res_ruh.prescribed_shashti_upakramas)
        assert "Jatyadi" in res_ruh.topical_formulation
    finally:
        conn.close()
        tmpdir.cleanup()
