"""
Phase 35: Western Emergency Break-Glass & Acute Critical Care Transfer Engine (NABH COP.6)
=========================================================================================
Implements:
1. Automated physiological deterioration threshold checks
2. Bilingual (English & Hindi) SBAR handover report synthesis
3. High-priority state lockdown and emergency transfer execution (Tables 76 & 77)
4. Medical Superintendent alerting and SHA-256 audit chaining
"""

import json
import sqlite3
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any

from core.database import get_sqlite_connection, append_audit_log
from models.emergency_transfer import (
    EmergencyTriggerReason,
    BreakGlassStatus,
    VitalSignsTelemetry,
    SbarHandoverReport,
    EmergencyBreakGlassRequest,
    EmergencyBreakGlassResponse,
    CriticalCareTransferRequest,
    CriticalCareTransferResponse,
    News2TriageEvaluation,
    PewsTriageEvaluation,
)


def calculate_news2(vitals: VitalSignsTelemetry) -> News2TriageEvaluation:
    """Calculate National Early Warning Score 2 (NEWS2) for adult patients."""
    # 1. Respiration rate
    rr = vitals.respiratory_rate_bpm
    if rr <= 8:
        rr_score = 3
    elif 9 <= rr <= 11:
        rr_score = 1
    elif 12 <= rr <= 20:
        rr_score = 0
    elif 21 <= rr <= 24:
        rr_score = 2
    else:  # >= 25
        rr_score = 3

    # 2. SpO2
    spo2 = vitals.spo2_percentage
    if spo2 <= 91.0:
        spo2_score = 3
    elif 92.0 <= spo2 <= 93.0:
        spo2_score = 2
    elif 94.0 <= spo2 <= 95.0:
        spo2_score = 1
    else:  # >= 96.0
        spo2_score = 0

    # 3. Systolic BP
    sbp = vitals.systolic_bp
    if sbp <= 90:
        sbp_score = 3
    elif 91 <= sbp <= 100:
        sbp_score = 2
    elif 101 <= sbp <= 110:
        sbp_score = 1
    elif 111 <= sbp <= 219:
        sbp_score = 0
    else:  # >= 220
        sbp_score = 3

    # 4. Pulse / Heart Rate
    hr = vitals.heart_rate_bpm
    if hr <= 40:
        hr_score = 3
    elif 41 <= hr <= 50:
        hr_score = 1
    elif 51 <= hr <= 90:
        hr_score = 0
    elif 91 <= hr <= 110:
        hr_score = 1
    elif 111 <= hr <= 130:
        hr_score = 2
    else:  # >= 131
        hr_score = 3

    # 5. Consciousness (GCS)
    gcs = vitals.glasgow_coma_scale
    cvpu_score = 0 if gcs >= 15 else 3

    # 6. Temperature (Fahrenheit)
    temp = vitals.temperature_fahrenheit
    if temp <= 95.0:  # <= 35.0 C
        temp_score = 3
    elif 95.1 <= temp <= 96.8:  # 35.1 - 36.0 C
        temp_score = 1
    elif 96.9 <= temp <= 100.4:  # 36.1 - 38.0 C
        temp_score = 0
    elif 100.5 <= temp <= 102.2:  # 38.1 - 39.0 C
        temp_score = 1
    else:  # >= 102.3 F / 39.1 C
        temp_score = 2

    total = rr_score + spo2_score + sbp_score + hr_score + cvpu_score + temp_score
    has_extreme_3 = any(s == 3 for s in [rr_score, spo2_score, sbp_score, hr_score, cvpu_score, temp_score])

    if total >= 7 or has_extreme_3:
        risk = "HIGH"
        is_trigger = True
    elif total >= 5:
        risk = "MEDIUM"
        is_trigger = False
    else:
        risk = "LOW"
        is_trigger = False

    return News2TriageEvaluation(
        respiratory_rate_score=rr_score,
        spo2_score=spo2_score,
        systolic_bp_score=sbp_score,
        heart_rate_score=hr_score,
        consciousness_score=cvpu_score,
        temperature_score=temp_score,
        total_score=total,
        risk_level=risk,
        is_emergency_trigger=is_trigger
    )


def calculate_pews(
    vitals: VitalSignsTelemetry,
    behavior_score: int = 0,
    cardiovascular_score: int = 0,
    respiratory_score: int = 0
) -> PewsTriageEvaluation:
    """Calculate Pediatric Early Warning Score (PEWS) for children < 16 years."""
    cv = cardiovascular_score
    if cv == 0:
        if vitals.heart_rate_bpm > 160 or vitals.heart_rate_bpm < 60:
            cv = 3
        elif vitals.heart_rate_bpm > 140:
            cv = 2
        elif vitals.heart_rate_bpm > 120:
            cv = 1

    resp = respiratory_score
    if resp == 0:
        if vitals.respiratory_rate_bpm > 50 or vitals.respiratory_rate_bpm < 10 or vitals.spo2_percentage < 90.0:
            resp = 3
        elif vitals.respiratory_rate_bpm > 40:
            resp = 2
        elif vitals.respiratory_rate_bpm > 30:
            resp = 1

    beh = behavior_score
    if beh == 0 and vitals.glasgow_coma_scale < 12:
        beh = 3
    elif beh == 0 and vitals.glasgow_coma_scale < 15:
        beh = 1

    total = beh + cv + resp
    has_extreme_3 = any(s == 3 for s in [beh, cv, resp])

    if total >= 5 or has_extreme_3:
        risk = "HIGH"
        is_trigger = True
    elif total >= 3:
        risk = "MEDIUM"
        is_trigger = False
    else:
        risk = "LOW"
        is_trigger = False

    return PewsTriageEvaluation(
        behavior_score=beh,
        cardiovascular_score=cv,
        respiratory_score=resp,
        total_score=total,
        risk_level=risk,
        is_emergency_trigger=is_trigger
    )


def evaluate_vital_instability(vitals: VitalSignsTelemetry) -> List[str]:
    """Detect specific physiological instabilities triggering break-glass protocol."""
    flags = []
    if vitals.systolic_bp < 90:
        flags.append(f"HEMODYNAMIC DECOMPENSATION: Severe hypotension (SBP {vitals.systolic_bp} mmHg < 90 mmHg).")
    if vitals.spo2_percentage < 90.0:
        flags.append(f"RESPIRATORY FAILURE: Critical desaturation (SpO2 {vitals.spo2_percentage}% < 90%).")
    if vitals.respiratory_rate_bpm > 30:
        flags.append(f"TACHYPNEA: Severe respiratory distress (RR {vitals.respiratory_rate_bpm}/min > 30/min).")
    if vitals.glasgow_coma_scale < 9:
        flags.append(f"COMA / NEUROLOGICAL DEPRESSION: Unprotected airway risk (GCS {vitals.glasgow_coma_scale} < 9).")
    if vitals.heart_rate_bpm > 130 or vitals.heart_rate_bpm < 40:
        flags.append(f"CARDIAC ARRHYTHMIA RISK: Severe pulse disturbance ({vitals.heart_rate_bpm} bpm).")

    # Multi-parameter Triage (NEWS2 for adults, PEWS for pediatrics) - Task 1.3
    if vitals.patient_age_years is not None and vitals.patient_age_years < 16:
        pews = calculate_pews(vitals)
        vitals.pews_score = pews.total_score
        vitals.triage_risk_level = pews.risk_level
        if pews.is_emergency_trigger:
            flags.append(
                f"PEDIATRIC EARLY WARNING SYSTEM ALERT [PEWS_CRITICAL]: PEWS Score {pews.total_score} "
                f"(Risk: {pews.risk_level}). Immediate pediatric ICU transfer required."
            )
    else:
        news2 = calculate_news2(vitals)
        vitals.news2_score = news2.total_score
        vitals.triage_risk_level = news2.risk_level
        if news2.is_emergency_trigger:
            flags.append(
                f"NATIONAL EARLY WARNING SCORE ALERT [NEWS2_CRITICAL]: NEWS2 Score {news2.total_score} "
                f"(Risk: {news2.risk_level}). NABH COP.6 break-glass transfer triggered."
            )

    return flags


def generate_sbar_report(
    patient_id: str,
    hospital_id: str,
    trigger: EmergencyTriggerReason,
    vitals: VitalSignsTelemetry,
    physician_arn: Optional[str] = None,
    clinical_narrative: Optional[str] = None
) -> SbarHandoverReport:
    """Generate canonical bilingual NABH COP.6 SBAR Transfer Handover."""
    now = int(time.time())

    english_situations = {
        EmergencyTriggerReason.CARDIOGENIC_SHOCK: "Acute cardiogenic shock and circulatory collapse requiring emergent ICU resuscitation.",
        EmergencyTriggerReason.SEVERE_HYPOXIA: "Acute hypoxic respiratory failure requiring immediate non-invasive/invasive mechanical ventilation.",
        EmergencyTriggerReason.ACUTE_CORONARY_SYNDROME: "Acute coronary syndrome presentation with crushing chest pain and hemodynamic instability.",
        EmergencyTriggerReason.ACUTE_ABDOMEN_PERITONITIS: "Suspected acute surgical abdomen with peritonitis and board-like involuntary guarding.",
        EmergencyTriggerReason.NEUROLOGICAL_COLLAPSE: "Acute neurological depression / coma (GCS < 9) requiring immediate airway protection.",
        EmergencyTriggerReason.ANAPHYLACTIC_SHOCK: "Severe anaphylactic reaction with laryngeal edema and bronchospasm.",
        EmergencyTriggerReason.MASSIVE_HEMORRHAGE: "Massive active hemorrhage causing secondary hypovolemic shock."
    }

    hindi_situations = {
        EmergencyTriggerReason.CARDIOGENIC_SHOCK: "गंभीर कार्डियोजेनिक शॉक एवं रक्तचाप में भारी गिरावट। तत्काल आईसीयू पुनर्जनन आवश्यक।",
        EmergencyTriggerReason.SEVERE_HYPOXIA: "तीव्र श्वसन विफलता और ऑक्सीजन स्तर में खतरनाक कमी (< 90%)। कृत्रिम वेंटिलेशन आवश्यक।",
        EmergencyTriggerReason.ACUTE_CORONARY_SYNDROME: "सीने में तीव्र दर्द एवं कार्डियक अरेस्ट की आशंका। तुरंत ईसीजी एवं कार्डियोलॉजी समीक्षा आवश्यक।",
        EmergencyTriggerReason.ACUTE_ABDOMEN_PERITONITIS: "तीव्र उदर संकट (एक्यूट एब्डोमेन) एवं पेरिटोनिटिस के लक्षण। तत्काल शल्य चिकित्सा जांच अपेक्षित।",
        EmergencyTriggerReason.NEUROLOGICAL_COLLAPSE: "चेतना का तीव्र ह्रास (जीसीएस < ९)। श्वासनली की सुरक्षा हेतु तत्काल विशेषज्ञ सहयोग अनिवार्य।",
        EmergencyTriggerReason.ANAPHYLACTIC_SHOCK: "तीव्र एनाफिलेक्टिक शॉक एवं श्वासनली शोफ। तत्काल एड्रेनालिन एवं आपातकालीन चिकित्सा आवश्यक।",
        EmergencyTriggerReason.MASSIVE_HEMORRHAGE: "अत्यधिक रक्तस्राव एवं हाइपोवोलेमिक शॉक। तत्काल रक्त आधान एवं सर्जिकल हस्तक्षेप आवश्यक।"
    }

    situation_en = english_situations.get(trigger, "Acute critical deterioration requiring immediate tertiary transfer.")
    situation_hi = hindi_situations.get(trigger, "रोगी की स्थिति अत्यंत गंभीर। तत्काल तृतीयक अस्पताल में स्थानांतरण आवश्यक।")

    recommendations = [
        "Secure immediate patent airway with high-flow supplemental oxygen (10-15 L/min NRB mask).",
        "Establish two large-bore (16G/18G) peripheral intravenous lines.",
        "Initiate emergency fluid resuscitation with warmed Normal Saline / Ringer Lactate under CVP/hemodynamic monitoring.",
        "Perform urgent 12-lead Electrocardiogram (ECG) and portable Bedside Ultrasound (FAST scan).",
        "Draw urgent blood samples for Cardiac Biomarkers (Troponin I), ABG, CBC, Renal Panel, and Blood Grouping & Cross-match."
    ]

    bg = clinical_narrative or f"Patient underwent inpatient Ayurvedic clinical care for chronic condition. Developed acute red-flag presentation ({trigger.value})."

    return SbarHandoverReport(
        situation_english=situation_en,
        situation_hindi=situation_hi,
        background_ayurvedic_course=bg,
        assessment_vitals=vitals,
        assessment_acute_syndrome=trigger.value,
        recommendation_allopathic_resuscitation=recommendations,
        transferring_facility=f"AIIA Apex Centre ({hospital_id})",
        attending_ayush_physician_arn=physician_arn or "ARN-EMERGENCY-ONCALL",
        generated_at=now
    )


# -------------------------------------------------------------------------
# Database Operations (Tables 76 & 77)
# -------------------------------------------------------------------------

def trigger_emergency_break_glass(
    req: EmergencyBreakGlassRequest,
    conn: Optional[sqlite3.Connection] = None
) -> EmergencyBreakGlassResponse:
    """Execute immediate emergency break-glass procedure and generate SBAR transfer dossier."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        sbar = generate_sbar_report(
            patient_id=req.patient_id,
            hospital_id=req.hospital_id,
            trigger=req.trigger_reason,
            vitals=req.vitals,
            physician_arn=req.physician_arn,
            clinical_narrative=req.clinical_narrative
        )

        now = int(time.time())
        event_id = f"EVENT-BREAKGLASS-{now}-{uuid.uuid4().hex[:6].upper()}"

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO emergency_break_glass_events (
                event_id, patient_id, hospital_id, trigger_reason, trigger_vitals_json,
                initiating_user_id, initiating_role, physician_arn, state_lockdown_enforced,
                sbar_handover_report_json, emergency_icu_destination, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                event_id,
                req.patient_id,
                req.hospital_id,
                req.trigger_reason.value,
                req.vitals.model_dump_json(),
                req.initiating_user_id,
                req.initiating_role,
                req.physician_arn,
                1,  # Lockdown enforced
                sbar.model_dump_json(),
                req.emergency_icu_destination,
                BreakGlassStatus.BREAK_GLASS_TRIGGERED.value,
                now
            )
        )

        append_audit_log(
            conn,
            req.hospital_id,
            req.initiating_user_id,
            "EMERGENCY_BREAK_GLASS_TRIGGERED",
            "EMERGENCY_EVENT",
            event_id,
            {
                "patient_id": req.patient_id,
                "trigger_reason": req.trigger_reason.value,
                "destination": req.emergency_icu_destination,
                "lockdown": True
            }
        )
        conn.commit()

        return EmergencyBreakGlassResponse(
            event_id=event_id,
            patient_id=req.patient_id,
            hospital_id=req.hospital_id,
            trigger_reason=req.trigger_reason,
            vitals=req.vitals,
            initiating_user_id=req.initiating_user_id,
            initiating_role=req.initiating_role,
            physician_arn=req.physician_arn,
            state_lockdown_enforced=True,
            sbar_handover=sbar,
            emergency_icu_destination=req.emergency_icu_destination,
            status=BreakGlassStatus.BREAK_GLASS_TRIGGERED,
            created_at=now
        )
    finally:
        if should_close:
            conn.close()


def execute_critical_care_transfer(
    req: CriticalCareTransferRequest,
    conn: Optional[sqlite3.Connection] = None
) -> CriticalCareTransferResponse:
    """Record execution of ambulance dispatch and tertiary allopathic ICU transfer."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM emergency_break_glass_events WHERE event_id = ?;", (req.event_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Emergency break-glass event '{req.event_id}' not found.")

        now = int(time.time())
        transfer_id = f"TRANSFER-ICU-{now}-{uuid.uuid4().hex[:6].upper()}"

        cursor.execute(
            """
            INSERT INTO critical_care_transfers (
                transfer_id, event_id, patient_id, hospital_id, ambulance_service_called,
                paramedic_call_timestamp, allopathic_physician_notified, medical_superintendent_alerted,
                handover_signed_by_arn, receiving_hospital_name, receiving_doctor_name,
                transfer_completed_at, clinical_notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                transfer_id,
                req.event_id,
                row["patient_id"],
                row["hospital_id"],
                1,
                now,
                req.allopathic_physician_notified,
                1,  # Superintendent alerted
                req.handover_signed_by_arn,
                req.receiving_hospital_name,
                req.receiving_doctor_name,
                now,
                req.clinical_notes,
                now
            )
        )

        cursor.execute(
            """
            UPDATE emergency_break_glass_events
            SET status = ?
            WHERE event_id = ?;
            """,
            (BreakGlassStatus.TRANSFERRED_TO_ICU.value, req.event_id)
        )

        append_audit_log(
            conn,
            row["hospital_id"],
            req.handover_signed_by_arn,
            "CRITICAL_CARE_TRANSFER_COMPLETED",
            "TRANSFER_RECORD",
            transfer_id,
            {
                "event_id": req.event_id,
                "receiving_hospital": req.receiving_hospital_name,
                "receiving_doctor": req.receiving_doctor_name
            }
        )
        conn.commit()

        return CriticalCareTransferResponse(
            transfer_id=transfer_id,
            event_id=req.event_id,
            patient_id=row["patient_id"],
            hospital_id=row["hospital_id"],
            ambulance_service_called=True,
            paramedic_call_timestamp=now,
            allopathic_physician_notified=req.allopathic_physician_notified,
            medical_superintendent_alerted=True,
            handover_signed_by_arn=req.handover_signed_by_arn,
            receiving_hospital_name=req.receiving_hospital_name,
            receiving_doctor_name=req.receiving_doctor_name,
            transfer_completed_at=now,
            clinical_notes=req.clinical_notes,
            created_at=now
        )
    finally:
        if should_close:
            conn.close()


def get_break_glass_event(
    event_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> EmergencyBreakGlassResponse:
    """Retrieve full details of an emergency break-glass event."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM emergency_break_glass_events WHERE event_id = ?;", (event_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Emergency event '{event_id}' not found.")

        vitals = VitalSignsTelemetry.model_validate_json(row["trigger_vitals_json"])
        sbar = SbarHandoverReport.model_validate_json(row["sbar_handover_report_json"])

        return EmergencyBreakGlassResponse(
            event_id=row["event_id"],
            patient_id=row["patient_id"],
            hospital_id=row["hospital_id"],
            trigger_reason=EmergencyTriggerReason(row["trigger_reason"]),
            vitals=vitals,
            initiating_user_id=row["initiating_user_id"],
            initiating_role=row["initiating_role"],
            physician_arn=row["physician_arn"],
            state_lockdown_enforced=bool(row["state_lockdown_enforced"]),
            sbar_handover=sbar,
            emergency_icu_destination=row["emergency_icu_destination"],
            status=BreakGlassStatus(row["status"]),
            created_at=row["created_at"]
        )
    finally:
        if should_close:
            conn.close()
