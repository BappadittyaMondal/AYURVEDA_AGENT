"""
Phase 34: Paschat Karma, Samsarjana Krama & Longitudinal EHR Persistence Engine
================================================================================
Implements core clinical algorithms, database operations, and trajectory analytics:
1. Graduated Annakala dietary ladder generation (Pravara, Madhyama, Avara)
2. Caloric and digestibility staircase calculations
3. Persistent episode lifecycle management (Table 74: paschat_karma_episodes)
4. Annakala-by-Annakala bedside intake logging (Table 75: samsarjana_krama_logs)
5. Dynamic Agni kindling trajectory modeling and complication interception
6. Ashta Mahadosha / Parihara Vishaya adherence auditing and classical remediation
7. Statutory Rasayana & Vajikarana readiness gating
"""

import json
import math
import sqlite3
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any

from core.database import get_sqlite_connection, append_audit_log
from models.panchakarma import ShuddhiGrade
from models.paschat_karma import (
    AnnakalaMealTime,
    DietaryLadderForm,
    AgniRestorationStatus,
    DigestionTolerance,
    PariharaProhibition,
    EpisodeStatus,
    SamsarjanaMealStep,
    PaschatKarmaEpisodeCreate,
    PaschatKarmaEpisodeResponse,
    SamsarjanaMealLogCreate,
    SamsarjanaMealLogResponse,
    AgniKindlingPoint,
    SamsarjanaTrajectorySummary,
    PariharaAdherenceAuditRequest,
    PariharaAdherenceAuditResponse,
    RasayanaReadinessResponse,
)


# -------------------------------------------------------------------------
# Classical Dietary Ladder Data & Culinary Specifications
# -------------------------------------------------------------------------

PREPARATION_SPECIFICATIONS: Dict[DietaryLadderForm, Dict[str, Any]] = {
    DietaryLadderForm.PEYA: {
        "description": "Thin warm rice gruel (Manda/Peya cooked with 1 part red shali rice to 14 parts water, liquid only)",
        "base_caloric_kcal": 120.0,
        "digestibility_index": 0.15,
        "doshic_action": "Deepana, Vatanulomana, Sroto-Shodhaka",
    },
    DietaryLadderForm.VILEPI: {
        "description": "Thick semi-solid boiled rice gruel (1 part rice to 4 parts water, soft gelatinous grains)",
        "base_caloric_kcal": 240.0,
        "digestibility_index": 0.35,
        "doshic_action": "Tarpanam, Hridya, Grahi, Balya",
    },
    DietaryLadderForm.AKRITA_YUSHA: {
        "description": "Green gram (Mudga) soup boiled without oil, ghee, salt, or pungent spices",
        "base_caloric_kcal": 380.0,
        "digestibility_index": 0.55,
        "doshic_action": "Kaphapittahara, Laghu, Dhatu-Posana",
    },
    DietaryLadderForm.KRITA_YUSHA: {
        "description": "Green gram soup seasoned with rock salt (Saindhava), cumin (Jeeraka), and pure cow's ghee (Go-Ghrita)",
        "base_caloric_kcal": 520.0,
        "digestibility_index": 0.70,
        "doshic_action": "Agni-Dipana, Ruchya, Balya, Vata-Shamaka",
    },
    DietaryLadderForm.MAMSA_RASA: {
        "description": "Light soup of Jangala meat (wild quail/goat) or rich nutritive mung-rice mash seasoned with ginger and ghee",
        "base_caloric_kcal": 680.0,
        "digestibility_index": 0.85,
        "doshic_action": "Sadyah-Pranadatri, Brimhana, Sarva-Dhatu-Poshaka",
    },
    DietaryLadderForm.NORMAL_DIET: {
        "description": "Balanced, easily digestible solid meal (Shali rice, Mudga dal, lightly cooked seasonal vegetables, Cow's milk)",
        "base_caloric_kcal": 850.0,
        "digestibility_index": 1.00,
        "doshic_action": "Prakriti-Equilibrating, Purna-Balya",
    }
}

CARDINAL_PARIHARA_RULES = [
    "Strict abstinence from excessive talking (Atibhashana) and shouting (Uchhairbhashana)",
    "Avoid motorized vehicular travel, rough terrain vibration, and sudden shocks (Ratha Kshobha)",
    "Avoid walking long distances, sun exposure, and strenuous exercise (Atichankramana)",
    "Refrain from prolonged sitting on hard or uneven surfaces (Atyasana)",
    "Do not consume food before previous meal is completely digested (Ajeerna Adhyashana)",
    "Avoid unwholesome, cold, heavy, or incompatible food items (Asatmya Bhojana)",
    "Strict avoidance of daytime sleeping (Divasvapna) and sexual intercourse (Maithuna)",
    "Maintain emotional equanimity; avoid anger, grief, anxiety, and loud arguments"
]


# -------------------------------------------------------------------------
# Core Algorithmic & Mathematical Functions
# -------------------------------------------------------------------------

def calculate_samsarjana_ladder(shuddhi_grade: ShuddhiGrade) -> List[SamsarjanaMealStep]:
    """
    Computes the canonical graduated Annakala meal sequence.
    - Pravara Shuddhi: 7 Days (14 Annakalas: 3 Peya, 3 Vilepi, 3 Akrita Yusha, 3 Krita Yusha, 2 Mamsa Rasa/Normal)
    - Madhyama Shuddhi: 5 Days (10 Annakalas: 2 Peya, 2 Vilepi, 2 Akrita Yusha, 2 Krita Yusha, 2 Mamsa Rasa/Normal)
    - Avara / Ayoga Shuddhi: 3 Days (6 Annakalas: 1 Peya, 1 Vilepi, 1 Akrita Yusha, 1 Krita Yusha, 2 Mamsa Rasa/Normal)
    """
    if shuddhi_grade == ShuddhiGrade.PRAVARA:
        sequence = [
            DietaryLadderForm.PEYA, DietaryLadderForm.PEYA, DietaryLadderForm.PEYA,
            DietaryLadderForm.VILEPI, DietaryLadderForm.VILEPI, DietaryLadderForm.VILEPI,
            DietaryLadderForm.AKRITA_YUSHA, DietaryLadderForm.AKRITA_YUSHA, DietaryLadderForm.AKRITA_YUSHA,
            DietaryLadderForm.KRITA_YUSHA, DietaryLadderForm.KRITA_YUSHA, DietaryLadderForm.KRITA_YUSHA,
            DietaryLadderForm.MAMSA_RASA,
            DietaryLadderForm.NORMAL_DIET
        ]
    elif shuddhi_grade == ShuddhiGrade.MADHYAMA:
        sequence = [
            DietaryLadderForm.PEYA, DietaryLadderForm.PEYA,
            DietaryLadderForm.VILEPI, DietaryLadderForm.VILEPI,
            DietaryLadderForm.AKRITA_YUSHA, DietaryLadderForm.AKRITA_YUSHA,
            DietaryLadderForm.KRITA_YUSHA, DietaryLadderForm.KRITA_YUSHA,
            DietaryLadderForm.MAMSA_RASA,
            DietaryLadderForm.NORMAL_DIET
        ]
    else:  # AVARA, AYOGA, or ATIYOGA
        sequence = [
            DietaryLadderForm.PEYA,
            DietaryLadderForm.VILEPI,
            DietaryLadderForm.AKRITA_YUSHA,
            DietaryLadderForm.KRITA_YUSHA,
            DietaryLadderForm.MAMSA_RASA,
            DietaryLadderForm.NORMAL_DIET
        ]

    total_annakalas = len(sequence)
    steps: List[SamsarjanaMealStep] = []

    for idx, diet_form in enumerate(sequence, start=1):
        day_num = ((idx - 1) // 2) + 1
        meal_time = AnnakalaMealTime.PRATAH_KALPA if (idx % 2 != 0) else AnnakalaMealTime.SAYAM_KALPA

        spec = PREPARATION_SPECIFICATIONS[diet_form]
        base_cal = spec["base_caloric_kcal"]
        base_dig = spec["digestibility_index"]

        # Non-linear progression multiplier: Calorie(k) = Base * (1 + 0.15 * (k/N)^1.2)
        progression_ratio = idx / total_annakalas
        dynamic_cal = round(base_cal * (0.95 + 0.10 * (progression_ratio ** 1.2)), 1)
        dynamic_dig = round(min(1.0, base_dig + 0.05 * progression_ratio), 2)

        steps.append(
            SamsarjanaMealStep(
                day_number=day_num,
                annakala_number=idx,
                meal_time_type=meal_time,
                prescribed_diet_form=diet_form,
                preparation_details=spec["description"],
                caloric_estimate_kcal=dynamic_cal,
                digestibility_index=dynamic_dig,
            )
        )

    return steps


# -------------------------------------------------------------------------
# Database Episode Operations (Table 74)
# -------------------------------------------------------------------------

def initiate_paschat_karma_episode(
    req: PaschatKarmaEpisodeCreate,
    conn: Optional[sqlite3.Connection] = None
) -> PaschatKarmaEpisodeResponse:
    """Initiate a post-Panchakarma Paschat Karma episode with a customized Samsarjana ladder."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        schedule = calculate_samsarjana_ladder(req.shuddhi_grade)
        total_annakalas = len(schedule)
        total_days = schedule[-1].day_number

        now = int(time.time())
        episode_id = f"EPISODE-PASCHAT-{now}-{uuid.uuid4().hex[:6].upper()}"

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO paschat_karma_episodes (
                episode_id, patient_id, hospital_id, plan_id, procedure_type,
                shuddhi_grade, total_annakalas, total_days, current_annakala,
                agni_restoration_status, parihara_restrictions_json, rasayana_readiness,
                status, attending_physician_arn, started_at, completed_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                episode_id,
                req.patient_id,
                req.hospital_id,
                req.plan_id,
                req.procedure_type,
                req.shuddhi_grade.value,
                total_annakalas,
                total_days,
                1,  # First Annakala active
                AgniRestorationStatus.MANDAGNI_POST_SHODHANA.value,
                json.dumps(CARDINAL_PARIHARA_RULES),
                0,  # Not yet ready for Rasayana
                EpisodeStatus.IN_PROGRESS.value,
                req.attending_physician_arn,
                now,
                None,
                now
            )
        )

        append_audit_log(
            conn,
            req.hospital_id,
            req.attending_physician_arn,
            "INITIATE_PASCHAT_KARMA",
            "PASCHAT_KARMA_EPISODE",
            episode_id,
            {
                "patient_id": req.patient_id,
                "shuddhi_grade": req.shuddhi_grade.value,
                "total_annakalas": total_annakalas,
                "total_days": total_days
            }
        )
        conn.commit()

        return PaschatKarmaEpisodeResponse(
            episode_id=episode_id,
            patient_id=req.patient_id,
            hospital_id=req.hospital_id,
            plan_id=req.plan_id,
            procedure_type=req.procedure_type,
            shuddhi_grade=req.shuddhi_grade,
            total_annakalas=total_annakalas,
            total_days=total_days,
            current_annakala=1,
            agni_restoration_status=AgniRestorationStatus.MANDAGNI_POST_SHODHANA,
            parihara_restrictions=CARDINAL_PARIHARA_RULES,
            rasayana_readiness=False,
            status=EpisodeStatus.IN_PROGRESS,
            attending_physician_arn=req.attending_physician_arn,
            schedule=schedule,
            started_at=now,
            completed_at=None,
            created_at=now
        )
    finally:
        if should_close:
            conn.close()


def get_paschat_karma_episode(
    episode_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> PaschatKarmaEpisodeResponse:
    """Retrieve an authoritative Paschat Karma episode with its complete schedule."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM paschat_karma_episodes WHERE episode_id = ?;", (episode_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Paschat Karma episode '{episode_id}' not found.")

        shuddhi = ShuddhiGrade(row["shuddhi_grade"])
        schedule = calculate_samsarjana_ladder(shuddhi)

        return PaschatKarmaEpisodeResponse(
            episode_id=row["episode_id"],
            patient_id=row["patient_id"],
            hospital_id=row["hospital_id"],
            plan_id=row["plan_id"],
            procedure_type=row["procedure_type"],
            shuddhi_grade=shuddhi,
            total_annakalas=row["total_annakalas"],
            total_days=row["total_days"],
            current_annakala=row["current_annakala"],
            agni_restoration_status=AgniRestorationStatus(row["agni_restoration_status"]),
            parihara_restrictions=json.loads(row["parihara_restrictions_json"]),
            rasayana_readiness=bool(row["rasayana_readiness"]),
            status=EpisodeStatus(row["status"]),
            attending_physician_arn=row["attending_physician_arn"],
            schedule=schedule,
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            created_at=row["created_at"]
        )
    finally:
        if should_close:
            conn.close()


def get_patient_paschat_episodes(
    patient_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> List[PaschatKarmaEpisodeResponse]:
    """List all Paschat Karma episodes for a patient."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT episode_id FROM paschat_karma_episodes WHERE patient_id = ? ORDER BY created_at DESC;",
            (patient_id,)
        )
        rows = cursor.fetchall()
        return [get_paschat_karma_episode(r["episode_id"], conn=conn) for r in rows]
    finally:
        if should_close:
            conn.close()


# -------------------------------------------------------------------------
# Longitudinal Meal Logging Operations (Table 75)
# -------------------------------------------------------------------------

def log_samsarjana_meal(
    episode_id: str,
    req: SamsarjanaMealLogCreate,
    conn: Optional[sqlite3.Connection] = None
) -> SamsarjanaMealLogResponse:
    """Record an Annakala meal intake, evaluate digestive outcome, and update episode progress."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        episode = get_paschat_karma_episode(episode_id, conn=conn)
        if episode.status not in (EpisodeStatus.ACTIVE, EpisodeStatus.IN_PROGRESS):
            raise ValueError(f"Cannot log meal for episode in status '{episode.status.value}'.")

        # Find the target schedule step
        matching_steps = [s for s in episode.schedule if s.annakala_number == req.annakala_number]
        if not matching_steps:
            raise ValueError(f"Annakala number {req.annakala_number} is out of bounds (1 to {episode.total_annakalas}).")
        step = matching_steps[0]

        now = int(time.time())
        log_id = f"LOG-MEAL-{now}-{uuid.uuid4().hex[:6].upper()}"

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO samsarjana_krama_logs (
                log_id, episode_id, patient_id, day_number, annakala_number,
                meal_time_type, prescribed_diet_form, preparation_details,
                caloric_estimate_kcal, digestibility_index, patient_appetite_observed,
                digestion_tolerance_noted, compliance_status, clinical_notes,
                nurse_or_practitioner_id, logged_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                log_id,
                episode_id,
                episode.patient_id,
                step.day_number,
                step.annakala_number,
                step.meal_time_type.value,
                step.prescribed_diet_form.value,
                step.preparation_details,
                step.caloric_estimate_kcal,
                step.digestibility_index,
                req.patient_appetite_observed,
                req.digestion_tolerance_noted.value,
                req.compliance_status,
                req.clinical_notes,
                req.nurse_or_practitioner_id,
                now
            )
        )

        # Update episode progress
        next_annakala = min(episode.total_annakalas, req.annakala_number + 1)
        
        # Agni Status Progression
        if req.annakala_number >= episode.total_annakalas and req.digestion_tolerance_noted == DigestionTolerance.SUKHA_PAKA:
            new_agni_status = AgniRestorationStatus.SAMAGNI_RESTORED
        elif req.annakala_number > 2:
            new_agni_status = AgniRestorationStatus.GRADUAL_KINDLING
        else:
            new_agni_status = AgniRestorationStatus.MANDAGNI_POST_SHODHANA

        cursor.execute(
            """
            UPDATE paschat_karma_episodes
            SET current_annakala = ?, agni_restoration_status = ?
            WHERE episode_id = ?;
            """,
            (next_annakala, new_agni_status.value, episode_id)
        )

        append_audit_log(
            conn,
            episode.hospital_id,
            req.nurse_or_practitioner_id,
            "LOG_SAMSARJANA_MEAL",
            "SAMSARJANA_MEAL_LOG",
            log_id,
            {
                "episode_id": episode_id,
                "annakala_number": req.annakala_number,
                "diet_form": step.prescribed_diet_form.value,
                "tolerance": req.digestion_tolerance_noted.value
            }
        )
        conn.commit()

        return SamsarjanaMealLogResponse(
            log_id=log_id,
            episode_id=episode_id,
            patient_id=episode.patient_id,
            day_number=step.day_number,
            annakala_number=step.annakala_number,
            meal_time_type=step.meal_time_type,
            prescribed_diet_form=step.prescribed_diet_form,
            preparation_details=step.preparation_details,
            caloric_estimate_kcal=step.caloric_estimate_kcal,
            digestibility_index=step.digestibility_index,
            patient_appetite_observed=req.patient_appetite_observed,
            digestion_tolerance_noted=req.digestion_tolerance_noted,
            compliance_status=req.compliance_status,
            clinical_notes=req.clinical_notes,
            nurse_or_practitioner_id=req.nurse_or_practitioner_id,
            logged_at=now
        )
    finally:
        if should_close:
            conn.close()


def list_samsarjana_meal_logs(
    episode_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> List[SamsarjanaMealLogResponse]:
    """Retrieve all logged meals for an episode ordered by Annakala number."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM samsarjana_krama_logs WHERE episode_id = ? ORDER BY annakala_number ASC;",
            (episode_id,)
        )
        rows = cursor.fetchall()
        return [
            SamsarjanaMealLogResponse(
                log_id=r["log_id"],
                episode_id=r["episode_id"],
                patient_id=r["patient_id"],
                day_number=r["day_number"],
                annakala_number=r["annakala_number"],
                meal_time_type=AnnakalaMealTime(r["meal_time_type"]),
                prescribed_diet_form=DietaryLadderForm(r["prescribed_diet_form"]),
                preparation_details=r["preparation_details"],
                caloric_estimate_kcal=r["caloric_estimate_kcal"],
                digestibility_index=r["digestibility_index"],
                patient_appetite_observed=r["patient_appetite_observed"],
                digestion_tolerance_noted=DigestionTolerance(r["digestion_tolerance_noted"]),
                compliance_status=r["compliance_status"],
                clinical_notes=r["clinical_notes"],
                nurse_or_practitioner_id=r["nurse_or_practitioner_id"],
                logged_at=r["logged_at"]
            )
            for r in rows
        ]
    finally:
        if should_close:
            conn.close()


# -------------------------------------------------------------------------
# Agni Kindling Trajectory & Analytics
# -------------------------------------------------------------------------

def compute_samsarjana_trajectory(
    episode_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> SamsarjanaTrajectorySummary:
    """
    Computes empirical Agni kindling curve and recovery trajectory based on logged meals.
    Mathematical model:
      Theoretical Agni: Agni_th(k) = 0.25 + 0.75 * (k / N)
      Clinical Tolerance Multiplier:
        SUKHA_PAKA   = 1.00
        VIDAHI       = 0.65
        VISHTAMBHI   = 0.55
        AJIRNA       = 0.35
    """
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        episode = get_paschat_karma_episode(episode_id, conn=conn)
        logs = list_samsarjana_meal_logs(episode_id, conn=conn)

        total_n = episode.total_annakalas
        logged_n = len(logs)
        completion_pct = round((logged_n / total_n) * 100.0, 1)

        tolerance_multipliers = {
            DigestionTolerance.SUKHA_PAKA: 1.00,
            DigestionTolerance.VIDAHI: 0.65,
            DigestionTolerance.VISHTAMBHI: 0.55,
            DigestionTolerance.AJIRNA: 0.35,
        }

        points: List[AgniKindlingPoint] = []
        intolerance_count = 0

        current_score = 0.25  # Baseline post-shodhana Agni
        for log in logs:
            k = log.annakala_number
            th_score = round(0.25 + 0.75 * (k / total_n), 3)
            tol_mult = tolerance_multipliers.get(log.digestion_tolerance_noted, 0.70)
            actual_score = round(th_score * tol_mult, 3)
            current_score = actual_score

            if log.digestion_tolerance_noted != DigestionTolerance.SUKHA_PAKA:
                intolerance_count += 1

            points.append(
                AgniKindlingPoint(
                    annakala_number=k,
                    day_number=log.day_number,
                    diet_form=log.prescribed_diet_form,
                    theoretical_agni_score=th_score,
                    clinical_tolerance_score=actual_score,
                    tolerance_status=log.digestion_tolerance_noted
                )
            )

        recommendations: List[str] = []
        if intolerance_count > 0:
            recommendations.append(
                "ADVERSE DIGESTIVE SIGNS DETECTED: Repeat previous dietary stage before stepping up to heavier solid food."
            )
            recommendations.append(
                "ADMINISTER DEEPANA-PACHANA: Prescribe Panchakola Churna (1g) with warm water or Shunthi Kwatha before next meal."
            )
        else:
            recommendations.append(
                "OPTIMAL AGNI RESTORATION: Digestion is smooth (Sukha Paka). Proceed to the next scheduled Annakala ladder step."
            )

        if completion_pct >= 100.0 and intolerance_count == 0:
            recommendations.append(
                "SAMSARJANA KRAMA COMPLETE: Patient's Agni is fully restored (Samagni). Cleared for Phase 30 Rasayana / Phase 31 Vajikarana."
            )

        return SamsarjanaTrajectorySummary(
            episode_id=episode_id,
            patient_id=episode.patient_id,
            shuddhi_grade=episode.shuddhi_grade,
            total_annakalas=total_n,
            logged_annakalas=logged_n,
            completion_percentage=completion_pct,
            current_agni_score=round(current_score, 2),
            agni_restoration_status=episode.agni_restoration_status,
            intolerance_events_count=intolerance_count,
            clinical_trajectory=points,
            recommendations=recommendations
        )
    finally:
        if should_close:
            conn.close()


# -------------------------------------------------------------------------
# Parihara Vishaya Audit & Remediation
# -------------------------------------------------------------------------

def audit_parihara_adherence(
    episode_id: str,
    req: PariharaAdherenceAuditRequest,
    conn: Optional[sqlite3.Connection] = None
) -> PariharaAdherenceAuditResponse:
    """Clinical audit for violations of Ashta Mahadosha post-purification prohibitions."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        episode = get_paschat_karma_episode(episode_id, conn=conn)
        violations = [v.value for v in req.reported_violations]
        is_compliant = len(violations) == 0

        remedial_measures: List[str] = []
        if is_compliant:
            risk = "NONE"
            remedial_measures.append("Continue strict adherence to peaceful rest, warm water intake, and prescribed diet.")
        else:
            risk = "MODERATE" if len(violations) <= 2 else "HIGH"
            for v in req.reported_violations:
                if v in (PariharaProhibition.ATIBHASHANA, PariharaProhibition.UCHHAIRBHASHANA):
                    remedial_measures.append("Vocal strain detected: Complete silence (Mauna) for 24 hours and gargle with warm salt water.")
                elif v == PariharaProhibition.RATHA_KSHOBHA:
                    remedial_measures.append("Vibration trauma: Immediate rest in supine posture with light Abhyanga using Mahanarayana Taila.")
                elif v == PariharaProhibition.AJEERNA_ADHYASHANA:
                    remedial_measures.append("Adhyashana detected: Fasting (Langhana) until previous food is fully digested, followed by hot water sipping.")
                elif v in (PariharaProhibition.DIVASVAPNA_MAITHUNA, PariharaProhibition.ASATMYA_BHOJANA):
                    remedial_measures.append("Doshic aggravation: Prescribe Shunthi Kwatha and strictly enforce nighttime sleep only.")

        append_audit_log(
            conn,
            episode.hospital_id,
            req.audited_by_staff_id,
            "AUDIT_PARIHARA_ADHERENCE",
            "PASCHAT_KARMA_EPISODE",
            episode_id,
            {"is_compliant": is_compliant, "violations": violations, "risk": risk}
        )
        conn.commit()

        return PariharaAdherenceAuditResponse(
            episode_id=episode_id,
            is_compliant=is_compliant,
            violations_detected=violations,
            risk_severity=risk,
            remedial_measures=remedial_measures
        )
    finally:
        if should_close:
            conn.close()


# -------------------------------------------------------------------------
# Rasayana & Vajikarana Readiness Evaluation
# -------------------------------------------------------------------------

def evaluate_rasayana_readiness(
    episode_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> RasayanaReadinessResponse:
    """Evaluate whether the patient has completed Samsarjana Krama and is eligible for Rasayana / Vajikarana."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        episode = get_paschat_karma_episode(episode_id, conn=conn)
        logs = list_samsarjana_meal_logs(episode_id, conn=conn)

        all_logged = len(logs) >= episode.total_annakalas
        last_log = logs[-1] if logs else None
        last_tolerance_good = last_log is not None and last_log.digestion_tolerance_noted == DigestionTolerance.SUKHA_PAKA
        intolerances = [l for l in logs if l.digestion_tolerance_noted != DigestionTolerance.SUKHA_PAKA]
        no_active_intolerance = len(intolerances) == 0 or (last_tolerance_good and len(logs) > episode.total_annakalas - 2)

        criteria = {
            "all_annakalas_completed": all_logged,
            "final_meal_well_tolerated": last_tolerance_good,
            "samagni_confirmed": episode.agni_restoration_status == AgniRestorationStatus.SAMAGNI_RESTORED or all_logged,
            "free_from_acute_complications": no_active_intolerance
        }

        is_ready = all(criteria.values())

        recommended_rasayanas = []
        if is_ready:
            now = int(time.time())
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE paschat_karma_episodes
                SET rasayana_readiness = 1, status = ?, completed_at = ?
                WHERE episode_id = ?;
                """,
                (EpisodeStatus.COMPLETED.value, now, episode_id)
            )

            append_audit_log(
                conn,
                episode.hospital_id,
                episode.attending_physician_arn,
                "CLEAR_RASAYANA_READINESS",
                "PASCHAT_KARMA_EPISODE",
                episode_id,
                {"patient_id": episode.patient_id, "is_ready": True}
            )
            conn.commit()

            clearance_notes = "Patient successfully completed graduated Samsarjana Krama. Agni is balanced (Samagni). Fully cleared for Rasayana and Vajikarana therapies."
            recommended_rasayanas = [
                "Brahma Rasayana (Cellular Rejuvenation & Cognition)",
                "Chyawanprash Avaleha (Immuno-Modulation & Respiratory Vitality)",
                "Amalaki Rasayana (Antioxidant & Tissue Longevity)",
                "Ashwagandha Avaleha (Brimhana & Neuromuscular Strength)"
            ]
        else:
            clearance_notes = "Patient has not yet completed all Annakalas or exhibits digestive intolerance. Continue Samsarjana Krama."

        return RasayanaReadinessResponse(
            episode_id=episode_id,
            patient_id=episode.patient_id,
            is_ready_for_rasayana=is_ready,
            readiness_criteria_met=criteria,
            clearance_notes=clearance_notes,
            recommended_rasayana_classes=recommended_rasayanas
        )
    finally:
        if should_close:
            conn.close()
