"""Unit tests for Phase 33 Raktamokshana biotherapy engine."""
import sqlite3
import pytest

from core.database import get_sqlite_connection, init_database
from core.raktamokshana import (
    calculate_max_permissible_blood_volume,
    estimate_post_op_hemoglobin,
    evaluate_raktamokshana_safety,
    get_patient_raktamokshana_history,
    list_jalauka_species,
    list_siravedha_veins,
    record_raktamokshana_procedure,
    seed_raktamokshana_catalogs,
)
from models.raktamokshana import (
    BloodDoshaVitiation,
    BodyQuadrant,
    HemostasisMethod,
    JalaukaType,
    RaktamokshanaModality,
    RaktamokshanaProcedureLogCreate,
    RogiBala,
    SafetyEvaluationRequest,
)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Initialize SQLite database and seed catalogs before each test."""
    init_database()
    conn = get_sqlite_connection()
    seed_raktamokshana_catalogs(conn)
    conn.close()


def test_classical_12_jalauka_taxonomy():
    """Verify classical 12 leeches: 6 Nirvisha and 6 Savisha with salivary pharmacology."""
    conn = get_sqlite_connection()
    species = list_jalauka_species(conn=conn)
    conn.close()

    assert len(species) == 12
    nirvisha = [s for s in species if s.species_type == JalaukaType.NIRVISHA]
    savisha = [s for s in species if s.species_type == JalaukaType.SAVISHA]

    assert len(nirvisha) == 6
    assert len(savisha) == 6

    # Verify key Nirvisha species
    names = {s.sanskrit_name for s in nirvisha}
    assert "Kapila" in names
    assert "Pingala" in names
    assert "Shankhamukhi" in names
    assert "Mushika" in names
    assert "Pundarikamukhi" in names
    assert "Savarika" in names

    # Verify Shankhamukhi superior salivary biochemistry
    shankhamukhi = next(s for s in nirvisha if s.sanskrit_name == "Shankhamukhi")
    assert shankhamukhi.salivary_enzymes_profile["hirudin_atu_per_ml"] >= 50.0
    assert shankhamukhi.salivary_enzymes_profile["destabilase_fibrinolytic"] is True

    # Verify Savisha toxicity profile
    krishna = next(s for s in savisha if s.sanskrit_name == "Krishna")
    assert krishna.salivary_enzymes_profile["toxic_neurotoxin"] is True
    assert krishna.salivary_enzymes_profile["therapeutic_value"] == "NONE"


def test_siravedha_vein_matrix_and_avadhya_siras():
    """Verify Vidhya and 98 Avadhya Siras representation with anatomical mapping."""
    conn = get_sqlite_connection()
    veins = list_siravedha_veins(conn=conn)
    conn.close()

    assert len(veins) >= 15
    avadhya_veins = [v for v in veins if v.is_avadhya]
    vidhya_veins = [v for v in veins if not v.is_avadhya]

    assert len(avadhya_veins) >= 8
    assert len(vidhya_veins) >= 6

    # Check Gridhrasi indicated vein
    gridhrasi_vein = next((v for v in vidhya_veins if "Gridhrasi (Sciatica)" in v.indicated_diseases), None)
    assert gridhrasi_vein is not None
    assert gridhrasi_vein.body_quadrant == BodyQuadrant.SHAKHA_ADHA

    # Check Avadhya Greeva Matrika fatal complication risk
    matrika_vein = next((v for v in avadhya_veins if v.vein_code == "AV-GREEVA-MATRIKA-01"), None)
    assert matrika_vein is not None
    assert matrika_vein.avadhya_complication_risk.value == "FATAL_HEMORRHAGE"


def test_max_permissible_blood_volume_calculation():
    """Test bloodletting volume limits based on Rogi Bala and seasonal factor."""
    # 70 kg adult in Sharad (factor 1.0)
    vol_uttama = calculate_max_permissible_blood_volume(RogiBala.UTTAMA, 70.0, current_season="SHARAD")
    vol_madhyama = calculate_max_permissible_blood_volume(RogiBala.MADHYAMA, 70.0, current_season="SHARAD")
    vol_avara = calculate_max_permissible_blood_volume(RogiBala.AVARA, 70.0, current_season="SHARAD")

    assert vol_uttama == 560.0  # 70 * 8.0 = 560 mL (under 640 cap)
    assert vol_madhyama == 315.0  # 70 * 4.5 = 315 mL (under 320 cap)
    assert vol_avara == 154.0  # 70 * 2.2 = 154 mL (under 160 cap)

    # Seasonal restriction in Grishma (Summer factor 0.70)
    vol_grishma = calculate_max_permissible_blood_volume(RogiBala.UTTAMA, 70.0, current_season="GRISHMA")
    assert vol_grishma == round(560.0 * 0.70, 1)


def test_severe_anemia_safety_firewall():
    """Baseline Hemoglobin < 8.0 g/dL must trigger CODE_RED_SEVERE_ANEMIA_CONTRAINDICATION."""
    req = SafetyEvaluationRequest(
        patient_id="PAT-ANEMIA-01",
        hospital_id="HOSP-TEST-001",
        modality=RaktamokshanaModality.JALAUKAVACHARANA,
        rogi_bala=RogiBala.AVARA,
        patient_age=40,
        patient_weight_kg=55.0,
        baseline_hemoglobin_g_dl=7.2,
        proposed_volume_ml=20.0
    )

    res = evaluate_raktamokshana_safety(req)
    assert res.cleared is False
    assert res.firewall_status == "CODE_RED_SEVERE_ANEMIA_CONTRAINDICATION"
    assert "critically low" in res.reason.lower()


def test_moderate_anemia_siravedha_restriction():
    """Baseline Hemoglobin < 10.0 g/dL restricts Siravedha while allowing micro-Jalauka."""
    req = SafetyEvaluationRequest(
        patient_id="PAT-ANEMIA-02",
        hospital_id="HOSP-TEST-001",
        modality=RaktamokshanaModality.SIRAVEDHA,
        rogi_bala=RogiBala.MADHYAMA,
        patient_age=30,
        patient_weight_kg=60.0,
        baseline_hemoglobin_g_dl=9.1,
        proposed_volume_ml=100.0,
        vein_code="V-GRIDHRASI-01"
    )

    res = evaluate_raktamokshana_safety(req)
    assert res.cleared is False
    assert res.firewall_status == "CODE_ORANGE_MODERATE_ANEMIA_SIRAVEDHA_RESTRICTION"
    assert res.recommended_modality == RaktamokshanaModality.JALAUKAVACHARANA


def test_coagulopathy_bleeding_diathesis_firewall():
    """Coagulopathy (elevated INR or thrombocytopenia) must trigger CODE_RED_COAGULOPATHY_FIREWALL."""
    req = SafetyEvaluationRequest(
        patient_id="PAT-COAG-01",
        hospital_id="HOSP-TEST-001",
        modality=RaktamokshanaModality.JALAUKAVACHARANA,
        rogi_bala=RogiBala.MADHYAMA,
        patient_age=45,
        patient_weight_kg=65.0,
        baseline_hemoglobin_g_dl=13.5,
        platelet_count=35000,  # Below 50,000 cutoff
        proposed_volume_ml=30.0
    )

    res = evaluate_raktamokshana_safety(req)
    assert res.cleared is False
    assert res.firewall_status == "CODE_RED_COAGULOPATHY_FIREWALL"


def test_hemodynamic_hypotension_firewall():
    """Hypotension (SBP < 90 or MAP < 65) must trigger CODE_RED_HYPOTENSION_SHOCK."""
    req = SafetyEvaluationRequest(
        patient_id="PAT-SHOCK-01",
        hospital_id="HOSP-TEST-001",
        modality=RaktamokshanaModality.JALAUKAVACHARANA,
        rogi_bala=RogiBala.MADHYAMA,
        patient_age=50,
        patient_weight_kg=60.0,
        baseline_hemoglobin_g_dl=12.0,
        systolic_bp=85,
        diastolic_bp=55,
        proposed_volume_ml=25.0
    )

    res = evaluate_raktamokshana_safety(req)
    assert res.cleared is False
    assert res.firewall_status == "CODE_RED_HYPOTENSION_SHOCK"


def test_savisha_leech_species_firewall():
    """Selection of Savisha leech species must trigger SAVISHA_SPECIES_TOXIC_HAZARD."""
    req = SafetyEvaluationRequest(
        patient_id="PAT-SAVISHA-01",
        hospital_id="HOSP-TEST-001",
        modality=RaktamokshanaModality.JALAUKAVACHARANA,
        rogi_bala=RogiBala.UTTAMA,
        patient_age=32,
        patient_weight_kg=70.0,
        baseline_hemoglobin_g_dl=14.0,
        species_id="JAL-SAV-INDRAYUDHA",
        proposed_volume_ml=30.0
    )

    res = evaluate_raktamokshana_safety(req)
    assert res.cleared is False
    assert res.firewall_status == "SAVISHA_SPECIES_TOXIC_HAZARD"
    assert "SAVISHA (poisonous)" in res.reason


def test_avadhya_sira_puncture_firewall():
    """Attempting venesection on an Avadhya Sira must trigger AVADHYA_SIRA_VIOLATION_FATAL_RISK."""
    req = SafetyEvaluationRequest(
        patient_id="PAT-AVADHYA-01",
        hospital_id="HOSP-TEST-001",
        modality=RaktamokshanaModality.SIRAVEDHA,
        rogi_bala=RogiBala.UTTAMA,
        patient_age=28,
        patient_weight_kg=75.0,
        baseline_hemoglobin_g_dl=15.0,
        vein_code="AV-SHIRAH-STHAPANI-01",
        proposed_volume_ml=100.0
    )

    res = evaluate_raktamokshana_safety(req)
    assert res.cleared is False
    assert res.firewall_status == "AVADHYA_SIRA_VIOLATION_FATAL_RISK"
    assert "AVADHYA SIRAS" in res.reason


def test_excessive_volume_firewall():
    """Exceeding permissible volume limit must trigger EXCESSIVE_BLOOD_VOLUME_RISK."""
    req = SafetyEvaluationRequest(
        patient_id="PAT-VOL-01",
        hospital_id="HOSP-TEST-001",
        modality=RaktamokshanaModality.SIRAVEDHA,
        rogi_bala=RogiBala.AVARA,
        patient_age=65,
        patient_weight_kg=50.0,
        baseline_hemoglobin_g_dl=12.5,
        vein_code="V-GRIDHRASI-01",
        proposed_volume_ml=250.0,  # Far above 50 * 2.2 = 110 mL
        current_season="SHARAD"
    )

    res = evaluate_raktamokshana_safety(req)
    assert res.cleared is False
    assert res.firewall_status == "EXCESSIVE_BLOOD_VOLUME_RISK"


def test_normal_cleared_evaluation_and_hemostasis_guidance():
    """Compliant patient and parameters must clear all firewalls and output post-op guidance."""
    req = SafetyEvaluationRequest(
        patient_id="PAT-SAFE-01",
        hospital_id="HOSP-TEST-001",
        modality=RaktamokshanaModality.JALAUKAVACHARANA,
        rogi_bala=RogiBala.MADHYAMA,
        patient_age=35,
        patient_weight_kg=68.0,
        baseline_hemoglobin_g_dl=13.0,
        species_id="JAL-NIR-KAPILA",
        proposed_volume_ml=30.0,
        current_season="SHARAD"
    )

    res = evaluate_raktamokshana_safety(req)
    assert res.cleared is True
    assert res.firewall_status == "CLEARED"
    assert res.suggested_hemostasis == HemostasisMethod.SANDHANA
    assert len(res.post_procedure_nutritional_replenishment) > 0
    assert res.estimated_post_op_hb_g_dl == estimate_post_op_hemoglobin(13.0, 30.0)


def test_procedure_logging_and_patient_history():
    """Record procedure log, enforce safety check, and retrieve patient procedure history."""
    conn = get_sqlite_connection()
    payload = RaktamokshanaProcedureLogCreate(
        patient_id="PAT-PROC-HIST-01",
        hospital_id="HOSP-TEST-001",
        modality=RaktamokshanaModality.JALAUKAVACHARANA,
        target_anatomical_site="Right lower malleolus local induration",
        species_id="JAL-NIR-SHANKHAMUKHI",
        jalauka_count=2,
        evacuated_volume_ml=25.0,
        pre_procedure_hb=13.2,
        blood_dosha_vitiation=BloodDoshaVitiation.PAITTIKA,
        hemostasis_method=HemostasisMethod.SANDHANA,
        complications_observed=[],
        practitioner_arn="ARN-NCISM-2015-8832"
    )

    log_res = record_raktamokshana_procedure(payload, conn=conn)
    assert log_res.procedure_id.startswith("PROC-RAKTA-")
    assert log_res.safety_firewall_cleared is True
    assert log_res.post_procedure_hb < log_res.pre_procedure_hb

    history = get_patient_raktamokshana_history("PAT-PROC-HIST-01", conn=conn)
    conn.close()

    assert len(history) >= 1
    assert history[0].procedure_id == log_res.procedure_id
