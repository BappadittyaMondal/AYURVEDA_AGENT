"""
core/lab_telemetry.py - Clinical Laboratory Telemetry Processing & Ayurvedic Correlative Engine.
Ingests standard metabolic, renal, hepatic, hematologic, and inflammatory panels.
Generates objective threshold alerts, flags organ compromise for Ayurvedic dosing,
and persists telemetry in hospital database.
"""

from __future__ import annotations
import json
import time
import uuid
import sqlite3
from typing import List, Optional, Tuple

from models.lab_telemetry import (
    ComprehensiveLabTelemetry,
    LabAlert,
    LabAlertSeverity,
    LabTelemetryEvaluationResult,
)
from core.database import get_sqlite_connection


def init_lab_telemetry_table(conn: sqlite3.Connection) -> None:
    """Ensures clinical_lab_telemetry table and indexes exist."""
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS clinical_lab_telemetry (
            telemetry_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            hospital_id TEXT NOT NULL,
            sample_timestamp INTEGER NOT NULL,
            raw_payload_json TEXT NOT NULL,
            alerts_json TEXT NOT NULL,
            has_critical_alerts INTEGER NOT NULL,
            organ_warnings_json TEXT NOT NULL,
            governance_flags_json TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_lab_telemetry_patient ON clinical_lab_telemetry(patient_id, sample_timestamp DESC);"
    )
    conn.commit()


def evaluate_lab_telemetry(telemetry: ComprehensiveLabTelemetry) -> LabTelemetryEvaluationResult:
    """
    Evaluates laboratory telemetry against evidence-based clinical thresholds and
    classical Ayurvedic organ/Srotas vulnerability principles.
    """
    alerts: List[LabAlert] = []
    organ_warnings: List[str] = []
    gov_flags: List[str] = []

    # -------------------------------------------------------------------------
    # 1. Renal Panel (Mutravaha Srotas / Vrikka)
    # -------------------------------------------------------------------------
    if telemetry.egfr_ml_min_1_73m2 is not None:
        egfr = telemetry.egfr_ml_min_1_73m2
        if egfr < 30.0:
            alerts.append(
                LabAlert(
                    analyte="eGFR",
                    measured_value=egfr,
                    unit="mL/min/1.73m2",
                    reference_range=">= 90.0",
                    severity=LabAlertSeverity.CRITICAL,
                    clinical_implication="Stage 4/5 Severe Chronic Kidney Disease. Excretion failure.",
                )
            )
            organ_warnings.append("MUTRAVAHA_SROTAS_CRITICAL_FAILURE: eGFR < 30 mL/min.")
            gov_flags.append("NEPHROLOGY_EMERGENCY_CONSULTATION_REQUIRED")
            gov_flags.append("STRICT_CONTRAINDICATION_HEAVY_METAL_BHASMAS")
        elif egfr < 60.0:
            alerts.append(
                LabAlert(
                    analyte="eGFR",
                    measured_value=egfr,
                    unit="mL/min/1.73m2",
                    reference_range=">= 90.0",
                    severity=LabAlertSeverity.HIGH,
                    clinical_implication="Stage 3 Moderate Chronic Kidney Disease. Renal clearance impaired.",
                )
            )
            organ_warnings.append("MUTRAVAHA_SROTAS_IMPAIRMENT: eGFR < 60 mL/min.")
            gov_flags.append("RENAL_DOSE_ADJUSTMENT_MANDATORY")

    if telemetry.serum_creatinine_mg_dl is not None:
        cr = telemetry.serum_creatinine_mg_dl
        if cr > 3.0:
            alerts.append(
                LabAlert(
                    analyte="Serum Creatinine",
                    measured_value=cr,
                    unit="mg/dL",
                    reference_range="0.6 - 1.2",
                    severity=LabAlertSeverity.CRITICAL,
                    clinical_implication="Severe azotemia / Acute Kidney Injury.",
                )
            )
            organ_warnings.append("VRIKKA_AZOTEMIA_CRITICAL: Serum Creatinine > 3.0 mg/dL.")
        elif cr > 1.5:
            alerts.append(
                LabAlert(
                    analyte="Serum Creatinine",
                    measured_value=cr,
                    unit="mg/dL",
                    reference_range="0.6 - 1.2",
                    severity=LabAlertSeverity.HIGH,
                    clinical_implication="Elevated creatinine indicating impaired glomerular filtration.",
                )
            )
            organ_warnings.append("VRIKKA_DYSFUNCTION: Serum Creatinine > 1.5 mg/dL.")

    # -------------------------------------------------------------------------
    # 2. Hepatic Panel (Raktavaha Srotas / Yakrit / Kamala)
    # -------------------------------------------------------------------------
    ast = telemetry.ast_sgot_u_l
    alt = telemetry.alt_sgpt_u_l
    if ast is not None or alt is not None:
        max_transaminase = max(ast or 0.0, alt or 0.0)
        if max_transaminase > 200.0:
            alerts.append(
                LabAlert(
                    analyte="Hepatic Transaminases (AST/ALT)",
                    measured_value=max_transaminase,
                    unit="U/L",
                    reference_range="10 - 40",
                    severity=LabAlertSeverity.CRITICAL,
                    clinical_implication="Severe acute hepatocellular injury (> 5x ULN).",
                )
            )
            organ_warnings.append("YAKRIT_ACUTE_HEPATOCELLULAR_INJURY: Transaminases > 5x ULN.")
            gov_flags.append("HALT_HEPATOTOXIC_MEDICATIONS")
        elif max_transaminase > 120.0:
            alerts.append(
                LabAlert(
                    analyte="Hepatic Transaminases (AST/ALT)",
                    measured_value=max_transaminase,
                    unit="U/L",
                    reference_range="10 - 40",
                    severity=LabAlertSeverity.HIGH,
                    clinical_implication="Moderate transaminitis (> 3x ULN). Hepatic metabolic compromise.",
                )
            )
            organ_warnings.append("YAKRIT_METABOLIC_COMPROMISE: Transaminases > 3x ULN.")

    if telemetry.total_bilirubin_mg_dl is not None:
        tb = telemetry.total_bilirubin_mg_dl
        if tb > 5.0:
            alerts.append(
                LabAlert(
                    analyte="Total Bilirubin",
                    measured_value=tb,
                    unit="mg/dL",
                    reference_range="0.2 - 1.2",
                    severity=LabAlertSeverity.CRITICAL,
                    clinical_implication="Severe hyperbilirubinemia / cholestasis or liver failure.",
                )
            )
            organ_warnings.append("KAMALA_SEVERE_CHOLESTASIS: Total Bilirubin > 5.0 mg/dL.")
            gov_flags.append("URGENT_HEPATOLOGY_EVALUATION")
        elif tb > 2.0:
            alerts.append(
                LabAlert(
                    analyte="Total Bilirubin",
                    measured_value=tb,
                    unit="mg/dL",
                    reference_range="0.2 - 1.2",
                    severity=LabAlertSeverity.HIGH,
                    clinical_implication="Clinical jaundice (Kamala). Hepatic / biliary stasis.",
                )
            )
            organ_warnings.append("KAMALA_ICTERUS: Total Bilirubin > 2.0 mg/dL.")

    # -------------------------------------------------------------------------
    # 3. Glycemic & Metabolic Panel (Medovaha Srotas / Prameha)
    # -------------------------------------------------------------------------
    if telemetry.fasting_blood_glucose_mg_dl is not None:
        fbg = telemetry.fasting_blood_glucose_mg_dl
        if fbg < 70.0:
            alerts.append(
                LabAlert(
                    analyte="Fasting Blood Glucose",
                    measured_value=fbg,
                    unit="mg/dL",
                    reference_range="70 - 100",
                    severity=LabAlertSeverity.CRITICAL,
                    clinical_implication="Hypoglycemia hazard. Immediate oral or IV glucose required.",
                )
            )
            gov_flags.append("ACUTE_HYPOGLYCEMIA_MANAGEMENT_TRIGGER")
        elif fbg > 250.0:
            alerts.append(
                LabAlert(
                    analyte="Fasting Blood Glucose",
                    measured_value=fbg,
                    unit="mg/dL",
                    reference_range="70 - 100",
                    severity=LabAlertSeverity.CRITICAL,
                    clinical_implication="Severe uncontrolled hyperglycemia. DKA / HHS risk.",
                )
            )
            organ_warnings.append("PRAMEHA_UPADRAVA_HYPERGLYCEMIC_CRISIS: FBG > 250 mg/dL.")
            gov_flags.append("KETONURIA_AND_ELECTROLYTE_ASSESSMENT_REQUIRED")
        elif fbg > 126.0:
            alerts.append(
                LabAlert(
                    analyte="Fasting Blood Glucose",
                    measured_value=fbg,
                    unit="mg/dL",
                    reference_range="70 - 100",
                    severity=LabAlertSeverity.HIGH,
                    clinical_implication="Fasting hyperglycemia diagnostic of Diabetes Mellitus / Prameha.",
                )
            )
            organ_warnings.append("PRAMEHA_DIABETES: Fasting glucose > 126 mg/dL.")

    if telemetry.hba1c_percent is not None:
        hba1c = telemetry.hba1c_percent
        if hba1c > 10.0:
            alerts.append(
                LabAlert(
                    analyte="HbA1c",
                    measured_value=hba1c,
                    unit="%",
                    reference_range="< 5.7",
                    severity=LabAlertSeverity.CRITICAL,
                    clinical_implication="Poor long-term glycemic control. Accelerated microvascular risk.",
                )
            )
            organ_warnings.append("MEDOVOHA_SROTAS_CHRONIC_GLYCATION: HbA1c > 10%.")
        elif hba1c > 8.0:
            alerts.append(
                LabAlert(
                    analyte="HbA1c",
                    measured_value=hba1c,
                    unit="%",
                    reference_range="< 5.7",
                    severity=LabAlertSeverity.HIGH,
                    clinical_implication="Suboptimal glycemic control.",
                )
            )

    # -------------------------------------------------------------------------
    # 4. Hematology & Coagulation (Rakta Dhatu)
    # -------------------------------------------------------------------------
    if telemetry.hemoglobin_g_dl is not None:
        hb = telemetry.hemoglobin_g_dl
        if hb < 7.0:
            alerts.append(
                LabAlert(
                    analyte="Hemoglobin",
                    measured_value=hb,
                    unit="g/dL",
                    reference_range="12.0 - 16.5",
                    severity=LabAlertSeverity.CRITICAL,
                    clinical_implication="Severe decompensated anemia. Transfusion consideration.",
                )
            )
            organ_warnings.append("RAKTA_DHATUKSHAYA_CRITICAL: Hb < 7.0 g/dL.")
            gov_flags.append("TRANSFUSION_TRIAGE_REQUIRED")
            gov_flags.append("ALL_SHODHANA_AND_RAKTAMOKSHANA_CONTRAINDICATED")
        elif hb < 8.0:
            alerts.append(
                LabAlert(
                    analyte="Hemoglobin",
                    measured_value=hb,
                    unit="g/dL",
                    reference_range="12.0 - 16.5",
                    severity=LabAlertSeverity.HIGH,
                    clinical_implication="Severe anemia (Pandu Roga). Bloodletting strictly contraindicated.",
                )
            )
            organ_warnings.append("PANDU_SEVERE_RAKTA_KSHAYA: Hb < 8.0 g/dL.")
            gov_flags.append("RAKTAMOKSHANA_FIREWALL_LOCKED")
        elif hb < 10.0:
            alerts.append(
                LabAlert(
                    analyte="Hemoglobin",
                    measured_value=hb,
                    unit="g/dL",
                    reference_range="12.0 - 16.5",
                    severity=LabAlertSeverity.LOW,
                    clinical_implication="Moderate anemia. Siravedha restricted; Jalauka restricted.",
                )
            )
            gov_flags.append("SIRAVEDHA_MODALITY_CONTRAINDICATED")

    if telemetry.platelet_count_per_ul is not None:
        plt = telemetry.platelet_count_per_ul
        if plt < 50000.0:
            alerts.append(
                LabAlert(
                    analyte="Platelet Count",
                    measured_value=plt,
                    unit="/uL",
                    reference_range="150,000 - 450,000",
                    severity=LabAlertSeverity.CRITICAL,
                    clinical_implication="Severe thrombocytopenia. High risk of spontaneous hemorrhage.",
                )
            )
            organ_warnings.append("RAKTA_PITTAPATTI_BLEEDING_DIATHESIS: Platelets < 50,000/uL.")
            gov_flags.append("ALL_INVASIVE_PROCEDURES_STRICTLY_PROHIBITED")
        elif plt < 100000.0:
            alerts.append(
                LabAlert(
                    analyte="Platelet Count",
                    measured_value=plt,
                    unit="/uL",
                    reference_range="150,000 - 450,000",
                    severity=LabAlertSeverity.HIGH,
                    clinical_implication="Moderate thrombocytopenia. Venesection (Siravedha) restricted.",
                )
            )
            gov_flags.append("SIRAVEDHA_HEMOSTASIS_RESTRICTION_ACTIVE")

    # -------------------------------------------------------------------------
    # 5. Inflammatory Biomarkers (Ama / Sama Avastha)
    # -------------------------------------------------------------------------
    if telemetry.hs_crp_mg_l is not None:
        crp = telemetry.hs_crp_mg_l
        if crp > 10.0:
            alerts.append(
                LabAlert(
                    analyte="hs-CRP",
                    measured_value=crp,
                    unit="mg/L",
                    reference_range="< 1.0",
                    severity=LabAlertSeverity.CRITICAL,
                    clinical_implication="Marked systemic inflammatory response.",
                )
            )
            organ_warnings.append("TIVRA_SAMA_AVASTHA_SYSTEMIC_INFLAMMATION: hs-CRP > 10 mg/L.")
            gov_flags.append("DEEPANA_PACHANA_MANDATORY_BEFORE_SNEHANA")
        elif crp > 3.0:
            alerts.append(
                LabAlert(
                    analyte="hs-CRP",
                    measured_value=crp,
                    unit="mg/L",
                    reference_range="< 1.0",
                    severity=LabAlertSeverity.HIGH,
                    clinical_implication="Active chronic systemic inflammation.",
                )
            )
            organ_warnings.append("SAMA_AVASTHA_ELEVATED_CRP: hs-CRP > 3 mg/L.")

    has_crit = any(a.severity == LabAlertSeverity.CRITICAL for a in alerts)
    tid = telemetry.telemetry_id or f"lab-{uuid.uuid4().hex[:12]}"

    return LabTelemetryEvaluationResult(
        telemetry_id=tid,
        patient_id=telemetry.patient_id,
        timestamp=telemetry.timestamp,
        alerts=alerts,
        has_critical_alerts=has_crit,
        ayurvedic_organ_compromise_warnings=organ_warnings,
        clinical_governance_flags=gov_flags,
    )


def save_lab_telemetry(
    telemetry: ComprehensiveLabTelemetry,
    conn: Optional[sqlite3.Connection] = None
) -> LabTelemetryEvaluationResult:
    """Evaluates and persists laboratory telemetry into the hospital database."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        init_lab_telemetry_table(conn)
        eval_result = evaluate_lab_telemetry(telemetry)
        now = int(time.time())
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO clinical_lab_telemetry (
                telemetry_id, patient_id, hospital_id, sample_timestamp,
                raw_payload_json, alerts_json, has_critical_alerts,
                organ_warnings_json, governance_flags_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                eval_result.telemetry_id,
                telemetry.patient_id,
                telemetry.hospital_id,
                telemetry.timestamp,
                json.dumps(telemetry.model_dump()),
                json.dumps([a.model_dump() for a in eval_result.alerts]),
                1 if eval_result.has_critical_alerts else 0,
                json.dumps(eval_result.ayurvedic_organ_compromise_warnings),
                json.dumps(eval_result.clinical_governance_flags),
                now,
            )
        )
        conn.commit()
        return eval_result
    finally:
        if should_close:
            conn.close()


def get_latest_patient_lab_telemetry(
    patient_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> Optional[ComprehensiveLabTelemetry]:
    """Retrieves the most recent laboratory telemetry record for a patient."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        init_lab_telemetry_table(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT raw_payload_json FROM clinical_lab_telemetry
            WHERE patient_id = ?
            ORDER BY sample_timestamp DESC LIMIT 1;
            """,
            (patient_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        data = json.loads(row["raw_payload_json"])
        return ComprehensiveLabTelemetry(**data)
    finally:
        if should_close:
            conn.close()
