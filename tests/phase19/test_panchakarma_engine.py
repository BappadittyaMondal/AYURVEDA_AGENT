"""
Unit Tests for Clinical Panchakarma Protocol & Bedside Vega Tracking Engine (Phase 19).
"""

import tempfile
from pathlib import Path
import pytest

from core.database import get_sqlite_connection, init_database
from core.exceptions import (
    AmaGatingException,
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.panchakarma import (
    create_panchakarma_plan,
    evaluate_panchakarma_shuddhi,
    get_panchakarma_plan,
    list_plan_vegas,
    record_bedside_vega,
    verify_decoction_saviryata_avadhi,
)
from models.panchakarma import (
    AntikiMilestone,
    BedsideVegaEntry,
    PanchakarmaPlanCreate,
    PanchakarmaProcedure,
    PanchakarmaStage,
    PurvaKarmaData,
    ShuddhiEvaluationRequest,
    ShuddhiGrade,
    VegaContent,
)


def get_fresh_db_with_patient():
    """Create isolated SQLite database with a seeded patient in a safe temp directory."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_panchakarma.db"
    init_database(db_path)
    conn = get_sqlite_connection(db_path)

    # Seed patient
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("PAT-PK-001", "aiia-delhi-central-001", "Ramesh", "Sharma", "1978-04-15", "MALE", "+919876543210", 1700000000)
    )
    return tmpdir, conn


def test_panchakarma_plan_creation_success():
    """Verify successful initiation of Panchakarma plan when Purva Karma and AGI score comply."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        plan_create = PanchakarmaPlanCreate(
            patient_id="PAT-PK-001",
            procedure_type=PanchakarmaProcedure.VAMANA,
            target_shuddhi_tier=ShuddhiGrade.PRAVARA,
            purva_karma=PurvaKarmaData(
                deepana_pachana_days=3,
                snehapana_daily_doses_ml=[30.0, 60.0, 100.0, 150.0, 200.0],
                samyak_snigdha_lakshanas_present=True,
                swedana_completed=True,
                pre_op_agi_score=1.20,  # Safe (< 1.80)
            ),
            prescribed_by_arn="ARN-NCISM-2015-8832",
        )

        plan = create_panchakarma_plan(plan_create, "aiia-delhi-central-001", conn)
        assert plan.plan_id.startswith("PLAN-PK-VAMANA-")
        assert plan.current_stage == PanchakarmaStage.PURVA_KARMA
        assert plan.target_shuddhi_tier == ShuddhiGrade.PRAVARA

        # Retrieve and verify persistence
        fetched = get_panchakarma_plan(plan.plan_id, conn)
        assert fetched.plan_id == plan.plan_id
        assert fetched.purva_karma.pre_op_agi_score == 1.20
    finally:
        conn.close()
        tmpdir.cleanup()


def test_panchakarma_ama_gating_firewall_blocks_high_agi():
    """Verify Phase 09 Ama Gating Firewall strictly blocks Shodhana when AGI >= 1.80."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        plan_create = PanchakarmaPlanCreate(
            patient_id="PAT-PK-001",
            procedure_type=PanchakarmaProcedure.VIRECHANA,
            target_shuddhi_tier=ShuddhiGrade.MADHYAMA,
            purva_karma=PurvaKarmaData(
                deepana_pachana_days=2,
                snehapana_daily_doses_ml=[30.0, 60.0],
                samyak_snigdha_lakshanas_present=True,
                swedana_completed=True,
                pre_op_agi_score=1.95,  # Sama Avastha! (>= 1.80)
            ),
            prescribed_by_arn="ARN-NCISM-2015-8832",
        )

        with pytest.raises(AmaGatingException) as exc_info:
            create_panchakarma_plan(plan_create, "aiia-delhi-central-001", conn)
        assert "Sama Avastha" in str(exc_info.value)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_panchakarma_snehana_incomplete_firewall():
    """Ensure Shodhana is rejected if Samyak Snigdha Lakshanas are not confirmed."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        plan_create = PanchakarmaPlanCreate(
            patient_id="PAT-PK-001",
            procedure_type=PanchakarmaProcedure.VAMANA,
            target_shuddhi_tier=ShuddhiGrade.PRAVARA,
            purva_karma=PurvaKarmaData(
                deepana_pachana_days=3,
                snehapana_daily_doses_ml=[30.0, 60.0, 100.0],
                samyak_snigdha_lakshanas_present=False,  # Inadequate Snehana!
                swedana_completed=False,
                pre_op_agi_score=1.10,
            ),
            prescribed_by_arn="ARN-NCISM-2015-8832",
        )

        with pytest.raises(ClinicalGovernanceException) as exc_info:
            create_panchakarma_plan(plan_create, "aiia-delhi-central-001", conn)
        assert "Samyak Snigdha Lakshanas not attained" in str(exc_info.value)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_bedside_vega_logging_and_stage_advancement():
    """Verify bedside bout logging, vitals recording, and stage transition to PRADHANA_KARMA."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        plan = create_panchakarma_plan(
            PanchakarmaPlanCreate(
                patient_id="PAT-PK-001",
                procedure_type=PanchakarmaProcedure.VAMANA,
                target_shuddhi_tier=ShuddhiGrade.PRAVARA,
                purva_karma=PurvaKarmaData(
                    deepana_pachana_days=3,
                    snehapana_daily_doses_ml=[30.0, 60.0, 100.0, 150.0],
                    samyak_snigdha_lakshanas_present=True,
                    swedana_completed=True,
                    pre_op_agi_score=1.15,
                ),
                prescribed_by_arn="ARN-NCISM-2015-8832",
            ),
            "aiia-delhi-central-001",
            conn,
        )
        assert plan.current_stage == PanchakarmaStage.PURVA_KARMA

        # Record 1st Vega (Anna dominant)
        entry = BedsideVegaEntry(
            plan_id=plan.plan_id,
            bout_number=1,
            output_volume_ml=250.0,
            dominant_content=VegaContent.ANNA,
            vitals_bp_systolic=120,
            vitals_bp_diastolic=80,
            vitals_pulse_bpm=76,
            attending_nurse_id="NURSE-001",
            clinical_notes="1st emetic bout with stomach food remnants",
        )
        vega_rec = record_bedside_vega(entry, conn)
        assert vega_rec.bout_number == 1
        assert vega_rec.dominant_content == VegaContent.ANNA

        # Verify plan automatically transitioned to PRADHANA_KARMA
        updated_plan = get_panchakarma_plan(plan.plan_id, conn)
        assert updated_plan.current_stage == PanchakarmaStage.PRADHANA_KARMA

        # Record 2nd Vega
        record_bedside_vega(
            BedsideVegaEntry(
                plan_id=plan.plan_id,
                bout_number=2,
                output_volume_ml=300.0,
                dominant_content=VegaContent.KAPHA,
                vitals_bp_systolic=118,
                vitals_bp_diastolic=78,
                vitals_pulse_bpm=80,
                attending_nurse_id="NURSE-001",
            ),
            conn,
        )

        all_vegas = list_plan_vegas(plan.plan_id, conn)
        assert len(all_vegas) == 2
        assert all_vegas[0].bout_number == 1
        assert all_vegas[1].bout_number == 2
    finally:
        conn.close()
        tmpdir.cleanup()


def test_chaturvidha_shuddhi_vamana_pravara_pittanta():
    """
    Verify complete classical Vamana evaluation:
    8 bouts, 1600 mL volume, canonical sequence ending in Pitta (Pittanta),
    generating 14-meal Pravara Samsarjana Krama schedule.
    """
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        plan = create_panchakarma_plan(
            PanchakarmaPlanCreate(
                patient_id="PAT-PK-001",
                procedure_type=PanchakarmaProcedure.VAMANA,
                target_shuddhi_tier=ShuddhiGrade.PRAVARA,
                purva_karma=PurvaKarmaData(
                    deepana_pachana_days=3,
                    snehapana_daily_doses_ml=[30.0, 60.0, 100.0, 150.0],
                    samyak_snigdha_lakshanas_present=True,
                    swedana_completed=True,
                    pre_op_agi_score=1.05,
                ),
                prescribed_by_arn="ARN-NCISM-2015-8832",
            ),
            "aiia-delhi-central-001",
            conn,
        )

        # Log 8 bouts: 1-2 Anna, 3-6 Kapha, 7-8 Pitta
        contents = [
            VegaContent.ANNA, VegaContent.ANNA,
            VegaContent.KAPHA, VegaContent.KAPHA, VegaContent.KAPHA, VegaContent.KAPHA,
            VegaContent.PITTA, VegaContent.PITTA  # Pittanta!
        ]
        volumes = [250.0, 200.0, 200.0, 200.0, 200.0, 200.0, 180.0, 170.0]  # Total: 1600 mL (Pravara)

        for i, (cnt, vol) in enumerate(zip(contents, volumes), start=1):
            record_bedside_vega(
                BedsideVegaEntry(
                    plan_id=plan.plan_id,
                    bout_number=i,
                    output_volume_ml=vol,
                    dominant_content=cnt,
                    vitals_bp_systolic=118,
                    vitals_bp_diastolic=78,
                    vitals_pulse_bpm=82,
                    attending_nurse_id="NURSE-AYUSH-01",
                ),
                conn,
            )

        # Evaluate Shuddhi
        eval_req = ShuddhiEvaluationRequest(
            plan_id=plan.plan_id,
            laingiki_symptoms=[
                "Urolaghava (Chest lightness)",
                "Indriya Prasadana (Sensory clarity)",
                "Kaphapittashuddhi confirmed",
                "Vatanulomana present",
            ],
            assessed_by_arn="ARN-NCISM-2015-8832",
        )

        res = evaluate_panchakarma_shuddhi(eval_req, conn)
        assert res.vaigiki_vega_count == 8
        assert res.vaigiki_grade == ShuddhiGrade.PRAVARA
        assert res.maniki_total_volume_ml == 1600.0
        assert res.maniki_grade == ShuddhiGrade.PRAVARA
        assert res.antiki_milestone == AntikiMilestone.PITTANTA
        assert res.antiki_passed is True
        assert res.overall_shuddhi_grade == ShuddhiGrade.PRAVARA
        assert res.atiyoga_detected is False

        # Verify 14-meal (7-day) Pravara Samsarjana Krama
        assert len(res.samsarjana_krama_schedule) == 14
        assert res.samsarjana_krama_schedule[0].meal_type == "PEYA"
        assert res.samsarjana_krama_schedule[3].meal_type == "VILEPI"
        assert res.samsarjana_krama_schedule[6].meal_type == "AKRITA_YUSHA"
        assert res.samsarjana_krama_schedule[9].meal_type == "KRITA_YUSHA"

        # Plan stage updated to PASCHAT_KARMA
        updated_plan = get_panchakarma_plan(plan.plan_id, conn)
        assert updated_plan.current_stage == PanchakarmaStage.PASCHAT_KARMA
    finally:
        conn.close()
        tmpdir.cleanup()


def test_chaturvidha_shuddhi_virechana_madhyama_kaphanta():
    """
    Verify Virechana evaluation:
    22 bouts, 2400 mL volume, ending in Kapha (Kaphanta),
    generating 10-meal Madhyama Samsarjana Krama schedule.
    """
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        plan = create_panchakarma_plan(
            PanchakarmaPlanCreate(
                patient_id="PAT-PK-001",
                procedure_type=PanchakarmaProcedure.VIRECHANA,
                target_shuddhi_tier=ShuddhiGrade.MADHYAMA,
                purva_karma=PurvaKarmaData(
                    deepana_pachana_days=3,
                    snehapana_daily_doses_ml=[40.0, 80.0, 120.0, 160.0],
                    samyak_snigdha_lakshanas_present=True,
                    swedana_completed=True,
                    pre_op_agi_score=1.10,
                ),
                prescribed_by_arn="ARN-NCISM-2015-8832",
            ),
            "aiia-delhi-central-001",
            conn,
        )

        # Log 22 bouts (Madhyama): 1-5 Purisha, 6-18 Pitta, 19-22 Kapha (Kaphanta)
        for b in range(1, 23):
            if b <= 5:
                content = VegaContent.PURISHA
            elif b <= 18:
                content = VegaContent.PITTA
            else:
                content = VegaContent.KAPHA

            record_bedside_vega(
                BedsideVegaEntry(
                    plan_id=plan.plan_id,
                    bout_number=b,
                    output_volume_ml=110.0,  # Total ~2420 mL
                    dominant_content=content,
                    vitals_bp_systolic=115,
                    vitals_bp_diastolic=75,
                    vitals_pulse_bpm=78,
                    attending_nurse_id="NURSE-002",
                ),
                conn,
            )

        res = evaluate_panchakarma_shuddhi(
            ShuddhiEvaluationRequest(
                plan_id=plan.plan_id,
                laingiki_symptoms=["Sharira laghava", "Vatanulomana", "Pittashuddhi"],
                assessed_by_arn="ARN-NCISM-2015-8832",
            ),
            conn,
        )

        assert res.vaigiki_vega_count == 22
        assert res.vaigiki_grade == ShuddhiGrade.MADHYAMA
        assert res.maniki_grade == ShuddhiGrade.MADHYAMA
        assert res.antiki_milestone == AntikiMilestone.KAPHANTA
        assert res.antiki_passed is True
        assert res.overall_shuddhi_grade == ShuddhiGrade.MADHYAMA
        assert len(res.samsarjana_krama_schedule) == 10
    finally:
        conn.close()
        tmpdir.cleanup()


def test_atiyoga_detection_and_emergency_stambhana():
    """Verify that frank blood (Raktanta) and hypotension trigger Atiyoga and Emergency Stambhana."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        plan = create_panchakarma_plan(
            PanchakarmaPlanCreate(
                patient_id="PAT-PK-001",
                procedure_type=PanchakarmaProcedure.VAMANA,
                target_shuddhi_tier=ShuddhiGrade.MADHYAMA,
                purva_karma=PurvaKarmaData(
                    deepana_pachana_days=3,
                    snehapana_daily_doses_ml=[30.0, 60.0, 100.0],
                    samyak_snigdha_lakshanas_present=True,
                    swedana_completed=True,
                    pre_op_agi_score=1.20,
                ),
                prescribed_by_arn="ARN-NCISM-2015-8832",
            ),
            "aiia-delhi-central-001",
            conn,
        )

        # Bout 1-3 Normal
        for b in range(1, 4):
            record_bedside_vega(
                BedsideVegaEntry(
                    plan_id=plan.plan_id,
                    bout_number=b,
                    output_volume_ml=200.0,
                    dominant_content=VegaContent.KAPHA,
                    vitals_bp_systolic=110,
                    vitals_bp_diastolic=70,
                    vitals_pulse_bpm=80,
                    attending_nurse_id="NURSE-001",
                ),
                conn,
            )

        # Bout 4 Complication: Frank blood and BP drops to 80/50 mmHg
        record_bedside_vega(
            BedsideVegaEntry(
                plan_id=plan.plan_id,
                bout_number=4,
                output_volume_ml=350.0,
                dominant_content=VegaContent.ASRA_BLOOD,
                vitals_bp_systolic=80,  # Critical hypotension (<90)
                vitals_bp_diastolic=50,
                vitals_pulse_bpm=128,   # Severe tachycardia (>120)
                attending_nurse_id="NURSE-001",
                clinical_notes="Patient pale, profuse sweating, blood in vomitus",
            ),
            conn,
        )

        res = evaluate_panchakarma_shuddhi(
            ShuddhiEvaluationRequest(
                plan_id=plan.plan_id,
                laingiki_symptoms=["Trishna", "Moha", "Dhatukshaya", "Blood in emesis"],
                assessed_by_arn="ARN-NCISM-2015-8832",
            ),
            conn,
        )

        assert res.atiyoga_detected is True
        assert res.overall_shuddhi_grade == ShuddhiGrade.ATIYOGA
        assert res.antiki_milestone == AntikiMilestone.RAKTANTA
        assert res.emergency_management_protocol is not None
        assert "EMERGENCY STAMBHANA PROTOCOL" in res.emergency_management_protocol

        # Verify plan stage marked as ABORTED
        updated_plan = get_panchakarma_plan(plan.plan_id, conn)
        assert updated_plan.current_stage == PanchakarmaStage.ABORTED
    finally:
        conn.close()
        tmpdir.cleanup()


def test_saviryata_avadhi_microbial_countdown():
    """Verify Sharangadhara Samhita / NABH AYUSH 24-hour decoction stability enforcement."""
    base_time = 1700000000

    # 1. Fresh decoction administered 4 hours after preparation (valid)
    valid, elapsed, msg = verify_decoction_saviryata_avadhi(
        prepared_at_timestamp=base_time,
        administration_timestamp=base_time + (4 * 3600),
    )
    assert valid is True
    assert elapsed == 4.0
    assert "20.0h remaining" in msg

    # 2. Decoction administered 23.5 hours after preparation (valid, near limit)
    valid, elapsed, msg = verify_decoction_saviryata_avadhi(
        prepared_at_timestamp=base_time,
        administration_timestamp=base_time + int(23.5 * 3600),
    )
    assert valid is True
    assert elapsed == 23.5
    assert "0.5h remaining" in msg

    # 3. Decoction administered 24.5 hours after preparation (EXPIRED - raises exception)
    with pytest.raises(ClinicalGovernanceException) as exc_info:
        verify_decoction_saviryata_avadhi(
            prepared_at_timestamp=base_time,
            administration_timestamp=base_time + int(24.5 * 3600),
        )
    assert exc_info.value.error_code == "SAVIRYATA_AVADHI_EXPIRED"
    assert "exceeds the maximum permissible 24.0-hour" in str(exc_info.value)

    # 4. Decoction with invalid future prep timestamp
    with pytest.raises(ClinicalGovernanceException) as exc_info:
        verify_decoction_saviryata_avadhi(
            prepared_at_timestamp=base_time + 3600,
            administration_timestamp=base_time,
        )
    assert exc_info.value.error_code == "INVALID_PREPARATION_TIMESTAMP"

