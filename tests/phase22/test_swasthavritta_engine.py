"""
Unit Tests for Swasthavritta, Dinacharya, Ritucharya & Vega-Dharana Engine (Phase 22).
"""

from datetime import datetime
import tempfile
from pathlib import Path
import pytest

from core.database import get_sqlite_connection, init_database
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.swasthavritta import (
    ADHARANIYA_VEGAS_DATA,
    SEED_DINACHARYA_STEPS,
    SEED_RITUCHARYA_CATALOG,
    audit_patient_dinacharya_routine,
    evaluate_circadian_bio_rhythm,
    evaluate_current_ritucharya,
    get_seasonal_calendar,
    initialize_swasthavritta_tables,
    log_and_evaluate_vega_suppression,
)
from models.swasthavritta import (
    AdharaniyaVegaType,
    CircadianPeriod,
    DinacharyaRoutineAuditRequest,
    RituCode,
    VegaSuppressionLogRequest,
)


def get_fresh_db_with_patient():
    """Create isolated SQLite database with a seeded patient in a safe temp directory."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_swasthavritta.db"
    init_database(db_path)
    conn = get_sqlite_connection(db_path)
    initialize_swasthavritta_tables(conn)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("PAT-SWASTHA-001", "aiia-delhi-central-001", "Suresh", "Joshi", "1980-08-15", "MALE", "+919876543201", 1700000000)
    )
    return tmpdir, conn


def test_dinacharya_catalog_completeness():
    """Verify registry contains all 12 classical Dinacharya procedures."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        steps = SEED_DINACHARYA_STEPS
        assert len(steps) >= 12

        # Check key steps
        step_ids = [s.step_id for s in steps]
        assert "DINA-BRAHMA-MUHURTA" in step_ids
        assert "DINA-USHAPANA" in step_ids
        assert "DINA-DANTADHAVANA" in step_ids
        assert "DINA-JIHWA-NIRLEKHANA" in step_ids
        assert "DINA-PRATIMARSHA-NASYA" in step_ids
        assert "DINA-ABHYANGA" in step_ids
        assert "DINA-VYAYAMA" in step_ids
        assert "DINA-SNANA" in step_ids

        abhyanga = next(s for s in steps if s.step_id == "DINA-ABHYANGA")
        assert "Shirah" in abhyanga.description
        assert any("Taruna Jwara" in c for c in abhyanga.contraindications)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_circadian_bio_rhythm_clock_periods():
    """Verify 24-hour circadian clock partitions into 6 canonical Ayurvedic segments."""
    # 04:30 AM -> Brahma Muhurta (Vata)
    t_brahma = datetime(2026, 4, 15, 4, 30)
    res_brahma = evaluate_circadian_bio_rhythm(t_brahma)
    assert res_brahma.active_period == CircadianPeriod.BRAHMA_MUHURTA
    assert "Vata" in res_brahma.dominant_dosha

    # 08:00 AM -> Kapha Morning
    t_kapha_am = datetime(2026, 4, 15, 8, 0)
    res_kapha_am = evaluate_circadian_bio_rhythm(t_kapha_am)
    assert res_kapha_am.active_period == CircadianPeriod.KAPHA_MORNING
    assert "Kapha" in res_kapha_am.dominant_dosha

    # 12:30 PM -> Pitta Midday
    t_pitta_noon = datetime(2026, 4, 15, 12, 30)
    res_pitta_noon = evaluate_circadian_bio_rhythm(t_pitta_noon)
    assert res_pitta_noon.active_period == CircadianPeriod.PITTA_MIDDAY
    assert "Pitta" in res_pitta_noon.dominant_dosha

    # 04:00 PM -> Vata Afternoon
    t_vata_pm = datetime(2026, 4, 15, 16, 0)
    res_vata_pm = evaluate_circadian_bio_rhythm(t_vata_pm)
    assert res_vata_pm.active_period == CircadianPeriod.VATA_AFTERNOON

    # 08:00 PM -> Kapha Evening
    t_kapha_pm = datetime(2026, 4, 15, 20, 0)
    res_kapha_pm = evaluate_circadian_bio_rhythm(t_kapha_pm)
    assert res_kapha_pm.active_period == CircadianPeriod.KAPHA_EVENING

    # 11:30 PM -> Pitta Night
    t_pitta_night = datetime(2026, 4, 15, 23, 30)
    res_pitta_night = evaluate_circadian_bio_rhythm(t_pitta_night)
    assert res_pitta_night.active_period == CircadianPeriod.PITTA_NIGHT
    assert any("Night vigil" in c for c in res_pitta_night.contraindicated_activities)


def test_dinacharya_lifestyle_audit_optimal():
    """Verify high compliance lifestyle scores >= 80 (OPTIMAL)."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = DinacharyaRoutineAuditRequest(
            patient_id="PAT-SWASTHA-001",
            wake_up_time="05:15 AM",
            bed_time="10:00 PM",
            lunch_time="12:30 PM",
            dinner_time="07:30 PM",
            has_daytime_nap=False,
            exercise_habit="MODERATE",
            dinacharya_practices=["USHAPANA", "DANTADHAVANA", "JIHWA_NIRLEKHANA", "ABHYANGA", "PRATIMARSHA_NASYA"]
        )
        res = audit_patient_dinacharya_routine(req, "aiia-delhi-central-001", conn)
        assert res.compliance_score >= 80.0
        assert res.circadian_alignment == "OPTIMAL"
        assert len(res.doshic_vitiation_risks) == 0

        # Verify persisted
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patient_lifestyle_evaluations WHERE evaluation_id = ?;", (res.audit_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["patient_id"] == "PAT-SWASTHA-001"
    finally:
        conn.close()
        tmpdir.cleanup()


def test_dinacharya_lifestyle_audit_dysregulated():
    """Verify dysregulated lifestyle (late wake, late bed, day nap, no exercise) scores < 50."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        req = DinacharyaRoutineAuditRequest(
            patient_id="PAT-SWASTHA-001",
            wake_up_time="09:00 AM",
            bed_time="01:30 AM",
            has_daytime_nap=True,
            exercise_habit="NONE",
            dinacharya_practices=[]
        )
        res = audit_patient_dinacharya_routine(req, "aiia-delhi-central-001", conn)
        assert res.compliance_score < 50.0
        assert res.circadian_alignment == "DYSREGULATED"
        assert any("KAPHA_ACCUMULATION" in r for r in res.doshic_vitiation_risks)
        assert any("RATRI_JAGARANA" in r for r in res.doshic_vitiation_risks)
        assert any("DIVASWAPNA" in r for r in res.doshic_vitiation_risks)
        assert any("LACK_OF_VYAYAMA" in r for r in res.doshic_vitiation_risks)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_adharaniya_vegas_catalog_completeness():
    """Verify knowledge base contains all 13 non-suppressible natural urges."""
    vegas = list(AdharaniyaVegaType)
    assert len(vegas) == 13
    assert len(ADHARANIYA_VEGAS_DATA) == 13

    # Check key urges
    assert AdharaniyaVegaType.MUTRA in ADHARANIYA_VEGAS_DATA
    assert AdharaniyaVegaType.PURISHA in ADHARANIYA_VEGAS_DATA
    assert AdharaniyaVegaType.APANA_VATA in ADHARANIYA_VEGAS_DATA
    assert AdharaniyaVegaType.CHHARDI in ADHARANIYA_VEGAS_DATA
    assert AdharaniyaVegaType.NIDRA in ADHARANIYA_VEGAS_DATA


def test_vega_suppression_udavarta_pathology():
    """Verify urge suppression logs calculate secondary Udavarta risk and remediation."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Fecal suppression (Purisha Vega Dharana) for 8 months daily
        req = VegaSuppressionLogRequest(
            patient_id="PAT-SWASTHA-001",
            vega_type=AdharaniyaVegaType.PURISHA,
            frequency="DAILY",
            duration_months=8,
            presenting_symptoms=["Pakvashayashula", "Severe constipation"]
        )
        res = log_and_evaluate_vega_suppression(req, "aiia-delhi-central-001", conn)
        assert res.secondary_udavarta_risk == "CRITICAL"
        assert "Apana Vata" in res.primary_vitiated_dosha
        assert any("पक्वाशयशूल" in s for s in res.classical_manifestations)
        assert "Basti" in res.remediation_protocol

        # Check persisted
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patient_vega_suppression_logs WHERE log_id = ?;", (res.log_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["vega_type"] == "PURISHA"
    finally:
        conn.close()
        tmpdir.cleanup()


def test_ritucharya_6_seasons_catalog():
    """Verify 6 classical Ritus and seasonal Shodhana windows."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        calendar = get_seasonal_calendar(conn)
        assert len(calendar) == 6

        ritu_map = {r.ritu_code: r for r in calendar}
        # Vasanta -> Vamana
        assert "VAMANA" in ritu_map[RituCode.VASANTA].indicated_shodhana.upper()
        # Varsha -> Basti
        assert "BASTI" in ritu_map[RituCode.VARSHA].indicated_shodhana.upper()
        # Sharad -> Virechana
        assert "VIRECHANA" in ritu_map[RituCode.SHARAD].indicated_shodhana.upper()
    finally:
        conn.close()
        tmpdir.cleanup()


def test_ritusandhi_transition_detection_and_shodhana():
    """Verify evaluation of active Ritu, 14-day Ritusandhi vulnerability, and Padamshika Krama."""
    # Test date: April 10 (Vasanta, inside season, mid-month)
    d_vasanta = datetime(2026, 4, 10)
    res_vasanta = evaluate_current_ritucharya(d_vasanta)
    assert res_vasanta.active_ritu == RituCode.VASANTA
    assert "VAMANA" in res_vasanta.recommended_seasonal_shodhana.upper()
    assert res_vasanta.in_ritusandhi is False

    # Test date: March 28 (Vasanta boundary / Ritusandhi window)
    d_sandhi = datetime(2026, 3, 28)
    res_sandhi = evaluate_current_ritucharya(d_sandhi)
    assert res_sandhi.in_ritusandhi is True
    assert res_sandhi.transition_note is not None
    assert "PADAMSHIKA KRAMA" in res_sandhi.padamshika_krama_rule.upper()

    # Test date: October 10 (Sharad, mid-month)
    d_sharad = datetime(2026, 10, 10)
    res_sharad = evaluate_current_ritucharya(d_sharad)
    assert res_sharad.active_ritu == RituCode.SHARAD
    assert "VIRECHANA" in res_sharad.recommended_seasonal_shodhana.upper()
