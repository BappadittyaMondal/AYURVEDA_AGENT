"""
tests/test_lab_telemetry.py - Unit tests for Structured Clinical Laboratory Telemetry.
Verifies threshold alerts, organ warnings, safety flags, and database persistence.
"""

import tempfile
from pathlib import Path
import pytest

from core.database import get_sqlite_connection, init_database
from models.lab_telemetry import (
    ComprehensiveLabTelemetry,
    LabAlertSeverity,
)
from core.lab_telemetry import (
    evaluate_lab_telemetry,
    save_lab_telemetry,
    get_latest_patient_lab_telemetry,
)


@pytest.fixture
def test_db():
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_lab_telemetry.db"
    init_database(db_path)
    conn = get_sqlite_connection(db_path)
    yield conn
    conn.close()
    tmpdir.cleanup()


def test_normal_lab_telemetry():
    """Verify healthy baseline laboratory telemetry triggers no clinical alerts."""
    telemetry = ComprehensiveLabTelemetry(
        patient_id="PAT-LAB-NORMAL",
        hospital_id="aiia-delhi-central-001",
        timestamp=1700000000,
        fasting_blood_glucose_mg_dl=88.0,
        hba1c_percent=5.2,
        serum_creatinine_mg_dl=0.9,
        egfr_ml_min_1_73m2=105.0,
        ast_sgot_u_l=22.0,
        alt_sgpt_u_l=24.0,
        total_bilirubin_mg_dl=0.8,
        hemoglobin_g_dl=14.2,
        platelet_count_per_ul=250000.0,
        hs_crp_mg_l=0.6,
    )
    result = evaluate_lab_telemetry(telemetry)
    assert len(result.alerts) == 0
    assert result.has_critical_alerts is False
    assert len(result.ayurvedic_organ_compromise_warnings) == 0
    assert len(result.clinical_governance_flags) == 0


def test_renal_failure_threshold_alerts():
    """Verify severe renal failure triggers critical alert and strict Bhasma contraindication."""
    telemetry = ComprehensiveLabTelemetry(
        patient_id="PAT-LAB-RENAL",
        hospital_id="aiia-delhi-central-001",
        timestamp=1700000000,
        egfr_ml_min_1_73m2=22.0,  # Critical (< 30)
        serum_creatinine_mg_dl=3.4,  # Critical (> 3.0)
    )
    result = evaluate_lab_telemetry(telemetry)
    assert result.has_critical_alerts is True
    assert len(result.alerts) == 2

    egfr_alert = next(a for a in result.alerts if a.analyte == "eGFR")
    assert egfr_alert.severity == LabAlertSeverity.CRITICAL

    cr_alert = next(a for a in result.alerts if a.analyte == "Serum Creatinine")
    assert cr_alert.severity == LabAlertSeverity.CRITICAL

    assert any("MUTRAVAHA_SROTAS_CRITICAL_FAILURE" in w for w in result.ayurvedic_organ_compromise_warnings)
    assert any("STRICT_CONTRAINDICATION_HEAVY_METAL_BHASMAS" in f for f in result.clinical_governance_flags)


def test_hepatic_crisis_alerts():
    """Verify acute hepatocellular transaminitis and hyperbilirubinemia triggers hepatic crisis alerts."""
    telemetry = ComprehensiveLabTelemetry(
        patient_id="PAT-LAB-HEPATIC",
        hospital_id="aiia-delhi-central-001",
        timestamp=1700000000,
        ast_sgot_u_l=240.0,  # Critical (> 200, > 5x ULN)
        alt_sgpt_u_l=280.0,
        total_bilirubin_mg_dl=6.5,  # Critical (> 5.0)
    )
    result = evaluate_lab_telemetry(telemetry)
    assert result.has_critical_alerts is True
    assert any("YAKRIT_ACUTE_HEPATOCELLULAR_INJURY" in w for w in result.ayurvedic_organ_compromise_warnings)
    assert any("KAMALA_SEVERE_CHOLESTASIS" in w for w in result.ayurvedic_organ_compromise_warnings)
    assert any("HALT_HEPATOTOXIC_MEDICATIONS" in f for f in result.clinical_governance_flags)


def test_hematologic_and_coagulopathy_alerts():
    """Verify severe thrombocytopenia and critical anemia halt all invasive procedures."""
    telemetry = ComprehensiveLabTelemetry(
        patient_id="PAT-LAB-HEMO",
        hospital_id="aiia-delhi-central-001",
        timestamp=1700000000,
        hemoglobin_g_dl=6.2,  # Critical (< 7.0)
        platelet_count_per_ul=42000.0,  # Critical (< 50,000)
    )
    result = evaluate_lab_telemetry(telemetry)
    assert result.has_critical_alerts is True
    assert any("ALL_INVASIVE_PROCEDURES_STRICTLY_PROHIBITED" in f for f in result.clinical_governance_flags)
    assert any("TRANSFUSION_TRIAGE_REQUIRED" in f for f in result.clinical_governance_flags)


def test_save_and_retrieve_lab_telemetry(test_db):
    """Verify persistence into clinical_lab_telemetry table and retrieval of latest telemetry."""
    telemetry = ComprehensiveLabTelemetry(
        patient_id="PAT-PERSIST-01",
        hospital_id="aiia-delhi-central-001",
        timestamp=1700000500,
        fasting_blood_glucose_mg_dl=145.0,
        hba1c_percent=7.8,
        serum_creatinine_mg_dl=1.1,
        egfr_ml_min_1_73m2=82.0,
    )
    eval_res = save_lab_telemetry(telemetry, conn=test_db)
    assert eval_res.patient_id == "PAT-PERSIST-01"

    retrieved = get_latest_patient_lab_telemetry("PAT-PERSIST-01", conn=test_db)
    assert retrieved is not None
    assert retrieved.patient_id == "PAT-PERSIST-01"
    assert retrieved.fasting_blood_glucose_mg_dl == 145.0
    assert retrieved.hba1c_percent == 7.8
