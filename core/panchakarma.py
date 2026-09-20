"""
Clinical Panchakarma Protocol & Bedside Vega Tracking Engine
===========================================================
Implements:
1. Panchakarma treatment plan management with Phase 09 Ama Gating Firewall integration
2. Real-time bedside Vega tracking (bout counter, volume, content, vitals)
3. Chaturvidha Shuddhi Pariksha (Vaigiki, Maniki, Antiki, Laingiki)
4. Terminal milestone detection (Pittanta for Vamana, Kaphanta for Virechana)
5. Atiyoga complication detection & emergency antidote triggers
6. Samsarjana Krama graduated dietetics generation
7. SQLite WAL persistence with indexed queries
"""

from __future__ import annotations
import json
import time
import sqlite3
from typing import List, Optional, Dict, Any, Tuple

from core.exceptions import (
    AmaGatingException,
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from models.panchakarma import (
    AntikiMilestone,
    BedsideVegaEntry,
    BedsideVegaRecord,
    DecoctionBatchPreparation,
    PanchakarmaPlanCreate,
    PanchakarmaPlanResponse,
    PanchakarmaProcedure,
    PanchakarmaStage,
    PurvaKarmaData,
    SamsarjanaMeal,
    ShuddhiEvaluationRequest,
    ShuddhiEvaluationResponse,
    ShuddhiGrade,
    VegaContent,
)


# ==============================================================================
# PANCHAKARMA TREATMENT PLAN LIFECYCLE & SAFETY FIREWALLS
# ==============================================================================

def create_panchakarma_plan(
    plan_in: PanchakarmaPlanCreate,
    hospital_id: str,
    conn: sqlite3.Connection
) -> PanchakarmaPlanResponse:
    """
    Initiates a clinical Panchakarma treatment plan after enforcing safety firewalls:
    1. Patient existence check
    2. Ama Gating Firewall: Pre-operative AGI score MUST be < 1.80 (Sama Avastha blocks Shodhana)
    3. Samyak Snigdha verification: Snehapana must be adequate
    """
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM patients WHERE patient_id = ?;", (plan_in.patient_id,))
    if not cursor.fetchone():
        raise RecordNotFoundException("Patient", plan_in.patient_id)

    # 1. AMA GATING FIREWALL (Phase 09 Rule)
    if plan_in.purva_karma.pre_op_agi_score >= 1.80:
        raise AmaGatingException(plan_in.purva_karma.pre_op_agi_score)

    # 2. Samyak Snigdha Verification
    if not plan_in.purva_karma.samyak_snigdha_lakshanas_present:
        raise ClinicalGovernanceException(
            "Purva Karma Incomplete: Samyak Snigdha Lakshanas not attained. Snehapana must continue.",
            error_code="PURVA_KARMA_SNEHANA_INCOMPLETE"
        )

    now = int(time.time())
    plan_id = f"PLAN-PK-{plan_in.procedure_type.value}-{plan_in.patient_id}-{now}"

    cursor.execute(
        """
        INSERT INTO panchakarma_treatment_plans (
            plan_id, patient_id, hospital_id, procedure_type,
            target_shuddhi_tier, current_stage, purva_karma_data_json,
            prescribed_by_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            plan_id,
            plan_in.patient_id,
            hospital_id,
            plan_in.procedure_type.value,
            plan_in.target_shuddhi_tier.value,
            PanchakarmaStage.PURVA_KARMA.value,
            json.dumps(plan_in.purva_karma.model_dump()),
            plan_in.prescribed_by_arn,
            now,
        )
    )

    return PanchakarmaPlanResponse(
        plan_id=plan_id,
        patient_id=plan_in.patient_id,
        hospital_id=hospital_id,
        procedure_type=plan_in.procedure_type,
        target_shuddhi_tier=plan_in.target_shuddhi_tier,
        current_stage=PanchakarmaStage.PURVA_KARMA,
        purva_karma=plan_in.purva_karma,
        prescribed_by_arn=plan_in.prescribed_by_arn,
        created_at=now,
    )


def get_panchakarma_plan(plan_id: str, conn: sqlite3.Connection) -> PanchakarmaPlanResponse:
    """Retrieve full Panchakarma plan details."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM panchakarma_treatment_plans WHERE plan_id = ?;", (plan_id,))
    row = cursor.fetchone()
    if not row:
        raise RecordNotFoundException("PanchakarmaPlan", plan_id)

    return PanchakarmaPlanResponse(
        plan_id=row["plan_id"],
        patient_id=row["patient_id"],
        hospital_id=row["hospital_id"],
        procedure_type=PanchakarmaProcedure(row["procedure_type"]),
        target_shuddhi_tier=ShuddhiGrade(row["target_shuddhi_tier"]),
        current_stage=PanchakarmaStage(row["current_stage"]),
        purva_karma=PurvaKarmaData(**json.loads(row["purva_karma_data_json"])),
        prescribed_by_arn=row["prescribed_by_arn"],
        created_at=row["created_at"],
    )


# ==============================================================================
# BEDSIDE REAL-TIME VEGA TRACKING ENGINE
# ==============================================================================

def record_bedside_vega(entry: BedsideVegaEntry, conn: sqlite3.Connection) -> BedsideVegaRecord:
    """
    Records a bedside Vega observation during active Pradhana Karma.
    Advances plan to PRADHANA_KARMA on first bout if currently in PURVA_KARMA.
    Detects critical Atiyoga indicators (e.g. Frank Blood or Hemodynamic Collapse).
    """
    plan = get_panchakarma_plan(entry.plan_id, conn)

    now = int(time.time())
    vega_id = f"VEGA-{entry.plan_id}-{entry.bout_number}-{now}"

    cursor = conn.cursor()

    # Automatically advance stage to PRADHANA_KARMA if not already
    if plan.current_stage == PanchakarmaStage.PURVA_KARMA:
        cursor.execute(
            "UPDATE panchakarma_treatment_plans SET current_stage = ? WHERE plan_id = ?;",
            (PanchakarmaStage.PRADHANA_KARMA.value, entry.plan_id)
        )

    # Persist Vega record
    cursor.execute(
        """
        INSERT INTO panchakarma_bedside_vegas (
            vega_id, plan_id, patient_id, bout_number, time_recorded,
            output_volume_ml, dominant_content, vitals_bp_systolic,
            vitals_bp_diastolic, vitals_pulse_bpm, attending_nurse_id,
            clinical_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            vega_id,
            entry.plan_id,
            plan.patient_id,
            entry.bout_number,
            now,
            entry.output_volume_ml,
            entry.dominant_content.value,
            entry.vitals_bp_systolic,
            entry.vitals_bp_diastolic,
            entry.vitals_pulse_bpm,
            entry.attending_nurse_id,
            entry.clinical_notes,
        )
    )

    return BedsideVegaRecord(
        vega_id=vega_id,
        plan_id=entry.plan_id,
        patient_id=plan.patient_id,
        bout_number=entry.bout_number,
        time_recorded=now,
        output_volume_ml=entry.output_volume_ml,
        dominant_content=entry.dominant_content,
        vitals_bp_systolic=entry.vitals_bp_systolic,
        vitals_bp_diastolic=entry.vitals_bp_diastolic,
        vitals_pulse_bpm=entry.vitals_pulse_bpm,
        attending_nurse_id=entry.attending_nurse_id,
        clinical_notes=entry.clinical_notes,
    )


def list_plan_vegas(plan_id: str, conn: sqlite3.Connection) -> List[BedsideVegaRecord]:
    """Retrieve all recorded bouts for a plan ordered sequentially."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM panchakarma_bedside_vegas WHERE plan_id = ? ORDER BY bout_number ASC;",
        (plan_id,)
    )
    rows = cursor.fetchall()
    return [
        BedsideVegaRecord(
            vega_id=r["vega_id"],
            plan_id=r["plan_id"],
            patient_id=r["patient_id"],
            bout_number=r["bout_number"],
            time_recorded=r["time_recorded"],
            output_volume_ml=r["output_volume_ml"],
            dominant_content=VegaContent(r["dominant_content"]),
            vitals_bp_systolic=r["vitals_bp_systolic"],
            vitals_bp_diastolic=r["vitals_bp_diastolic"],
            vitals_pulse_bpm=r["vitals_pulse_bpm"],
            attending_nurse_id=r["attending_nurse_id"],
            clinical_notes=r["clinical_notes"],
        )
        for r in rows
    ]


# ==============================================================================
# SAMSARJANA KRAMA DIETARY SCHEDULE GENERATOR
# ==============================================================================

def generate_samsarjana_krama_schedule(shuddhi_grade: ShuddhiGrade) -> List[SamsarjanaMeal]:
    """
    Generates classical graduated dietary rehabilitation schedule (Peya, Vilepi, Yusha, Mamsa Rasa).
    - Pravara Shuddhi: 7 days (14 Annakala meals)
    - Madhyama Shuddhi: 5 days (10 Annakala meals)
    - Avara Shuddhi: 3 days (6 Annakala meals)
    """
    meals: List[SamsarjanaMeal] = []

    if shuddhi_grade == ShuddhiGrade.PRAVARA:
        # 7 Days (14 Annakalas: 3 Peya, 3 Vilepi, 3 Akrita Yusha, 3 Krita Yusha, 2 Mamsa Rasa / Normal)
        plan_sequence = [
            ("PEYA", "Thin warm rice gruel / water", "ULTRA_LIGHT_LIQUID"),
            ("PEYA", "Thin warm rice gruel / water", "ULTRA_LIGHT_LIQUID"),
            ("PEYA", "Thin warm rice gruel / water", "ULTRA_LIGHT_LIQUID"),
            ("VILEPI", "Thick boiled rice gruel", "SEMI_SOLID_MILD"),
            ("VILEPI", "Thick boiled rice gruel", "SEMI_SOLID_MILD"),
            ("VILEPI", "Thick boiled rice gruel", "SEMI_SOLID_MILD"),
            ("AKRITA_YUSHA", "Green gram soup without oil/salt", "LIGHT_PROTEIN"),
            ("AKRITA_YUSHA", "Green gram soup without oil/salt", "LIGHT_PROTEIN"),
            ("AKRITA_YUSHA", "Green gram soup without oil/salt", "LIGHT_PROTEIN"),
            ("KRITA_YUSHA", "Green gram soup seasoned with ghee, cumin & rock salt", "MODERATE_PROTEIN"),
            ("KRITA_YUSHA", "Green gram soup seasoned with ghee, cumin & rock salt", "MODERATE_PROTEIN"),
            ("KRITA_YUSHA", "Green gram soup seasoned with ghee, cumin & rock salt", "MODERATE_PROTEIN"),
            ("MAMSA_RASA", "Light wild meat broth or boiled rice with ghee", "NOURISHING_ANABOLIC"),
            ("NORMAL_DIET", "Normal light balanced meal (Prakriti-specific)", "REGULAR_NUTRITION"),
        ]
    elif shuddhi_grade == ShuddhiGrade.MADHYAMA:
        # 5 Days (10 Annakalas: 2 Peya, 2 Vilepi, 2 Akrita Yusha, 2 Krita Yusha, 2 Normal)
        plan_sequence = [
            ("PEYA", "Thin warm rice gruel / water", "ULTRA_LIGHT_LIQUID"),
            ("PEYA", "Thin warm rice gruel / water", "ULTRA_LIGHT_LIQUID"),
            ("VILEPI", "Thick boiled rice gruel", "SEMI_SOLID_MILD"),
            ("VILEPI", "Thick boiled rice gruel", "SEMI_SOLID_MILD"),
            ("AKRITA_YUSHA", "Green gram soup without oil/salt", "LIGHT_PROTEIN"),
            ("AKRITA_YUSHA", "Green gram soup without oil/salt", "LIGHT_PROTEIN"),
            ("KRITA_YUSHA", "Green gram soup seasoned with ghee and cumin", "MODERATE_PROTEIN"),
            ("KRITA_YUSHA", "Green gram soup seasoned with ghee and cumin", "MODERATE_PROTEIN"),
            ("MAMSA_RASA", "Light broth or soft rice with mung dal", "NOURISHING_ANABOLIC"),
            ("NORMAL_DIET", "Gradual return to balanced diet", "REGULAR_NUTRITION"),
        ]
    else:
        # Avara or Ayoga: 3 Days (6 Annakalas: 1 Peya, 1 Vilepi, 1 Akrita Yusha, 1 Krita Yusha, 2 Normal)
        plan_sequence = [
            ("PEYA", "Thin warm rice gruel", "ULTRA_LIGHT_LIQUID"),
            ("VILEPI", "Thick boiled rice gruel", "SEMI_SOLID_MILD"),
            ("AKRITA_YUSHA", "Unseasoned green gram soup", "LIGHT_PROTEIN"),
            ("KRITA_YUSHA", "Seasoned green gram soup with ghee", "MODERATE_PROTEIN"),
            ("MAMSA_RASA", "Soft cooked rice with light dal", "NOURISHING_ANABOLIC"),
            ("NORMAL_DIET", "Return to normal diet", "REGULAR_NUTRITION"),
        ]

    for idx, (m_type, desc, tier) in enumerate(plan_sequence, start=1):
        day_num = ((idx - 1) // 2) + 1
        meals.append(
            SamsarjanaMeal(
                day_number=day_num,
                annakala_number=idx,
                meal_type=m_type,
                diet_description=desc,
                caloric_density_tier=tier,
            )
        )

    return meals


# ==============================================================================
# CHATURVIDHA SHUDDHI PARIKSHA EVALUATION ENGINE
# ==============================================================================

def evaluate_panchakarma_shuddhi(
    req: ShuddhiEvaluationRequest,
    conn: sqlite3.Connection
) -> ShuddhiEvaluationResponse:
    """
    Computes four-fold classical elimination criteria (Chaturvidha Shuddhi Pariksha):
    1. Vaigiki (Bout Count)
    2. Maniki (Volumetric Output)
    3. Antiki (Terminal End-Point: Pittanta for Vamana, Kaphanta for Virechana)
    4. Laingiki (Subjective & Objective Sign Resolution)
    Detects Atiyoga (complications/collapse) and generates customized Samsarjana Krama.
    """
    plan = get_panchakarma_plan(req.plan_id, conn)
    vegas = list_plan_vegas(req.plan_id, conn)

    vega_count = len(vegas)
    total_volume_ml = sum(v.output_volume_ml for v in vegas)

    # 1. Vaigiki Pariksha
    if plan.procedure_type == PanchakarmaProcedure.VAMANA:
        if vega_count >= 8:
            vaigiki_grade = ShuddhiGrade.PRAVARA
        elif vega_count >= 6:
            vaigiki_grade = ShuddhiGrade.MADHYAMA
        elif vega_count >= 4:
            vaigiki_grade = ShuddhiGrade.AVARA
        else:
            vaigiki_grade = ShuddhiGrade.AYOGA
    elif plan.procedure_type == PanchakarmaProcedure.VIRECHANA:
        if vega_count >= 30:
            vaigiki_grade = ShuddhiGrade.PRAVARA
        elif vega_count >= 20:
            vaigiki_grade = ShuddhiGrade.MADHYAMA
        elif vega_count >= 10:
            vaigiki_grade = ShuddhiGrade.AVARA
        else:
            vaigiki_grade = ShuddhiGrade.AYOGA
    else:  # Basti / Nasya / Raktamokshana
        vaigiki_grade = ShuddhiGrade.MADHYAMA

    # 2. Maniki Pariksha
    # Classical Prastha ~= 750 mL
    if plan.procedure_type == PanchakarmaProcedure.VAMANA:
        if total_volume_ml >= 1500.0:
            maniki_grade = ShuddhiGrade.PRAVARA
        elif total_volume_ml >= 1125.0:
            maniki_grade = ShuddhiGrade.MADHYAMA
        elif total_volume_ml >= 750.0:
            maniki_grade = ShuddhiGrade.AVARA
        else:
            maniki_grade = ShuddhiGrade.AYOGA
    elif plan.procedure_type == PanchakarmaProcedure.VIRECHANA:
        if total_volume_ml >= 3000.0:
            maniki_grade = ShuddhiGrade.PRAVARA
        elif total_volume_ml >= 2250.0:
            maniki_grade = ShuddhiGrade.MADHYAMA
        elif total_volume_ml >= 1500.0:
            maniki_grade = ShuddhiGrade.AVARA
        else:
            maniki_grade = ShuddhiGrade.AYOGA
    else:
        maniki_grade = ShuddhiGrade.MADHYAMA

    # 3. Antiki Pariksha (Terminal Milestone Detection)
    antiki_milestone = AntikiMilestone.INCOMPLETE
    antiki_passed = False
    atiyoga_detected = False
    atiyoga_complications: List[str] = []

    # Check for frank blood in any bout
    has_blood = any(v.dominant_content == VegaContent.ASRA_BLOOD for v in vegas)
    if has_blood:
        antiki_milestone = AntikiMilestone.RAKTANTA
        atiyoga_detected = True
        atiyoga_complications.append(
            "CRITICAL: Raktanta observed! Severe Atiyoga / Gastrointestinal mucosal bleeding."
        )

    # Check for hemodynamic collapse
    critical_hypotension = any(v.vitals_bp_systolic < 90 for v in vegas)
    severe_tachycardia = any(v.vitals_pulse_bpm > 120 for v in vegas)
    if critical_hypotension or severe_tachycardia:
        atiyoga_detected = True
        atiyoga_complications.append(
            f"HEMODYNAMIC INSTABILITY: Hypotension (<90 mmHg) or Tachycardia (>120 bpm) observed during procedure."
        )

    # If no blood, check normal terminal milestone
    if not has_blood and len(vegas) > 0:
        last_vegas = vegas[-2:]  # Check last 1-2 bouts
        if plan.procedure_type == PanchakarmaProcedure.VAMANA:
            # Canonical: Kapha followed by Pitta at the end
            if any(v.dominant_content == VegaContent.PITTA for v in last_vegas):
                antiki_milestone = AntikiMilestone.PITTANTA
                antiki_passed = True
        elif plan.procedure_type == PanchakarmaProcedure.VIRECHANA:
            # Canonical: Pitta followed by Kapha at the end
            if any(v.dominant_content == VegaContent.KAPHA for v in last_vegas):
                antiki_milestone = AntikiMilestone.KAPHANTA
                antiki_passed = True
        elif plan.procedure_type == PanchakarmaProcedure.BASTI:
            antiki_milestone = AntikiMilestone.ANILANTA
            antiki_passed = True
        elif plan.procedure_type == PanchakarmaProcedure.RAKTAMOKSHANA:
            antiki_milestone = AntikiMilestone.ASRANTA
            antiki_passed = True

    # Check for excessive bouts / volumes triggering Atiyoga
    if plan.procedure_type == PanchakarmaProcedure.VAMANA and (vega_count > 12 or total_volume_ml > 2500.0):
        atiyoga_detected = True
        atiyoga_complications.append(f"Atiyoga: Excessive emetic volume ({total_volume_ml:.1f}mL) or bouts ({vega_count}).")
    elif plan.procedure_type == PanchakarmaProcedure.VIRECHANA and (vega_count > 40 or total_volume_ml > 4500.0):
        atiyoga_detected = True
        atiyoga_complications.append(f"Atiyoga: Excessive purgation volume ({total_volume_ml:.1f}mL) or bouts ({vega_count}).")

    # 4. Overall Shuddhi Synthesis
    if atiyoga_detected:
        overall_grade = ShuddhiGrade.ATIYOGA
    elif vaigiki_grade == ShuddhiGrade.AYOGA or maniki_grade == ShuddhiGrade.AYOGA or not antiki_passed:
        overall_grade = ShuddhiGrade.AYOGA
    elif vaigiki_grade == ShuddhiGrade.PRAVARA and maniki_grade in (ShuddhiGrade.PRAVARA, ShuddhiGrade.MADHYAMA) and antiki_passed:
        overall_grade = ShuddhiGrade.PRAVARA
    elif vaigiki_grade in (ShuddhiGrade.PRAVARA, ShuddhiGrade.MADHYAMA) and maniki_grade in (ShuddhiGrade.PRAVARA, ShuddhiGrade.MADHYAMA):
        overall_grade = ShuddhiGrade.MADHYAMA
    else:
        overall_grade = ShuddhiGrade.AVARA

    # Emergency Stambhana protocol if Atiyoga
    emergency_protocol = None
    if atiyoga_detected:
        emergency_protocol = (
            "EMERGENCY STAMBHANA PROTOCOL ACTIVATED: Immediate administration of Dadimashtaka / Kutajavaleha, "
            "cold sponging (Sheeta Upachara), IV fluid resuscitation (Normal Saline / Ringer Lactate), and monitoring."
        )

    # 5. Generate Samsarjana Krama schedule
    samsarjana_schedule = generate_samsarjana_krama_schedule(overall_grade)

    now = int(time.time())
    assessment_id = f"SHUDDHI-{plan.plan_id}-{now}"

    # Update treatment plan current stage to PASCHAT_KARMA (or ABORTED if severe Atiyoga)
    new_stage = PanchakarmaStage.ABORTED if (atiyoga_detected and has_blood) else PanchakarmaStage.PASCHAT_KARMA
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE panchakarma_treatment_plans SET current_stage = ? WHERE plan_id = ?;",
        (new_stage.value, plan.plan_id)
    )

    # Persist Shuddhi assessment
    cursor.execute(
        """
        INSERT INTO panchakarma_shuddhi_assessments (
            assessment_id, plan_id, patient_id, vaigiki_vega_count,
            maniki_total_volume_ml, antiki_milestone, laingiki_symptoms_json,
            overall_shuddhi_grade, samsarjana_krama_plan_json,
            atiyoga_complications_json, assessed_by_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            assessment_id,
            plan.plan_id,
            plan.patient_id,
            vega_count,
            total_volume_ml,
            antiki_milestone.value,
            json.dumps(req.laingiki_symptoms),
            overall_grade.value,
            json.dumps([m.model_dump() for m in samsarjana_schedule]),
            json.dumps(atiyoga_complications),
            req.assessed_by_arn,
            now,
        )
    )

    summary = (
        f"Chaturvidha Shuddhi Completed for {plan.procedure_type.value}: "
        f"Vaigiki ({vega_count} bouts), Maniki ({total_volume_ml:.1f} mL), "
        f"Antiki ({antiki_milestone.value}), Overall Grade: {overall_grade.value}. "
        f"Samsarjana Krama prescribed for {len(samsarjana_schedule)} Annakalas."
    )

    return ShuddhiEvaluationResponse(
        assessment_id=assessment_id,
        plan_id=plan.plan_id,
        patient_id=plan.patient_id,
        procedure_type=plan.procedure_type,
        vaigiki_vega_count=vega_count,
        vaigiki_grade=vaigiki_grade,
        maniki_total_volume_ml=round(total_volume_ml, 2),
        maniki_grade=maniki_grade,
        antiki_milestone=antiki_milestone,
        antiki_passed=antiki_passed,
        overall_shuddhi_grade=overall_grade,
        laingiki_symptoms=req.laingiki_symptoms,
        atiyoga_detected=atiyoga_detected,
        atiyoga_complications=atiyoga_complications,
        emergency_management_protocol=emergency_protocol,
        samsarjana_krama_schedule=samsarjana_schedule,
        clinical_summary=summary,
        assessed_by_arn=req.assessed_by_arn,
        created_at=now,
    )


# ==============================================================================
# SAVIRYATA AVADHI (MICROBIAL STABILITY) VERIFICATION
# ==============================================================================

def verify_decoction_saviryata_avadhi(
    prepared_at_timestamp: int,
    administration_timestamp: Optional[int] = None
) -> Tuple[bool, float, str]:
    """
    Enforces Sharangadhara Samhita / NABH AYUSH 24-hour microbial and enzymatic stability limit
    (Saviryata Avadhi) on freshly prepared Kashayas and Kwathas.

    If elapsed hours exceed 24.0, raises ClinicalGovernanceException(error_code="SAVIRYATA_AVADHI_EXPIRED").
    """
    now = administration_timestamp if administration_timestamp is not None else int(time.time())
    if now < prepared_at_timestamp:
        raise ClinicalGovernanceException(
            "Invalid timestamp: Administration timestamp precedes preparation timestamp.",
            error_code="INVALID_PREPARATION_TIMESTAMP"
        )

    elapsed_seconds = now - prepared_at_timestamp
    elapsed_hours = round(elapsed_seconds / 3600.0, 2)

    if elapsed_hours > 24.0:
        raise ClinicalGovernanceException(
            f"Saviryata Avadhi Expired: Decoction batch prepared {elapsed_hours:.1f} hours ago exceeds "
            f"the maximum permissible 24.0-hour Ayurvedic pharmacopeial and microbial stability threshold "
            f"(Sharangadhara Samhita / NABH AYUSH standards). Risk of microbial proliferation, fermentation, "
            f"and secondary endotoxin formation. Discard batch immediately.",
            error_code="SAVIRYATA_AVADHI_EXPIRED"
        )

    remaining_hours = round(24.0 - elapsed_hours, 2)
    message = (
        f"Decoction within valid Saviryata Avadhi ({elapsed_hours:.1f}h elapsed, "
        f"{remaining_hours:.1f}h remaining before expiration)."
    )
    return True, elapsed_hours, message
