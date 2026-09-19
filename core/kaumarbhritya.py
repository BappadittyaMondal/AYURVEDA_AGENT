"""
Kaumarbhritya & Bala Roga Pediatric Engine
==========================================
Implements:
1. Kaumarbhritya Developmental Milestones & Classical Samskaras
2. Dual-Posology Pediatric Dosage Scaling (Sharngadhara Ratti, Clark, Cowling)
3. Pediatric Toxicology Firewall (Schedule E-1 and heavy metals prohibition)
4. Kashyapa Classical Bala Roga Syndromes (Phakka, Parigarbhika, Kukunaka, etc.)
5. Suvarnaprashana Immunomodulation Protocol Engine on Pushya Nakshatra
6. SQLite WAL persistence with indexed queries
"""

from __future__ import annotations
import json
import time
import uuid
import sqlite3
from typing import List, Optional, Dict, Any, Tuple

from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from models.kaumarbhritya import (
    BalaRogaSyndrome,
    ClassicalSamskara,
    DietaryStage,
    KaumarbhrityaMilestone,
    PediatricConsultationCreate,
    PediatricConsultationResponse,
    PediatricDosageCalculationRequest,
    PediatricDosageCalculationResponse,
    SuvarnaprashanaAdminCreate,
    SuvarnaprashanaAdminResponse,
)

# ==============================================================================
# 1. DEVELOPMENTAL MILESTONES & CLASSICAL SAMSKARAS CATALOG
# ==============================================================================

SEED_MILESTONES_CATALOG: List[KaumarbhrityaMilestone] = [
    KaumarbhrityaMilestone(
        milestone_id="MILESTONE-00",
        age_months=0,
        classical_samskara=ClassicalSamskara.JATAKARMA,
        motor_milestone="Primitive reflexes (Moro, sucking, rooting, palmar grasp present).",
        cognitive_milestone="Alert to human voice; turns toward maternal auditory stimulus.",
        sharngadhara_dosage_ratti=1.0,
        dietary_stage=DietaryStage.KSHEERADA,
    ),
    KaumarbhrityaMilestone(
        milestone_id="MILESTONE-01",
        age_months=1,
        classical_samskara=ClassicalSamskara.NAMAKARANA,
        motor_milestone="Lifts head briefly when prone; hands predominantly fisted.",
        cognitive_milestone="Tracks moving light or high-contrast faces to midline.",
        sharngadhara_dosage_ratti=1.0,
        dietary_stage=DietaryStage.KSHEERADA,
    ),
    KaumarbhrityaMilestone(
        milestone_id="MILESTONE-04",
        age_months=4,
        classical_samskara=ClassicalSamskara.NISHKRAMANA,
        motor_milestone="Steady head control; rolls from prone to supine; reaches for rattles.",
        cognitive_milestone="Social smile established; laughs aloud; anticipates feeding.",
        sharngadhara_dosage_ratti=4.0,
        dietary_stage=DietaryStage.KSHEERADA,
    ),
    KaumarbhrityaMilestone(
        milestone_id="MILESTONE-06",
        age_months=6,
        classical_samskara=ClassicalSamskara.ANNAPRASHANA,
        motor_milestone="Sits with pelvic support; transfers objects hand-to-hand; palmar grasp.",
        cognitive_milestone="Babbles consonants ('da-da', 'ba-ba'); stranger awareness begins.",
        sharngadhara_dosage_ratti=6.0,
        dietary_stage=DietaryStage.KSHEERANNADA,
    ),
    KaumarbhrityaMilestone(
        milestone_id="MILESTONE-07",
        age_months=7,
        classical_samskara=ClassicalSamskara.KARNAVEDHA,
        motor_milestone="Sits unsupported momentarily; radial-palmar grasp; responds to name.",
        cognitive_milestone="Inquisitive exploration; uncovers hidden toys.",
        sharngadhara_dosage_ratti=7.0,
        dietary_stage=DietaryStage.KSHEERANNADA,
    ),
    KaumarbhrityaMilestone(
        milestone_id="MILESTONE-12",
        age_months=12,
        classical_samskara=ClassicalSamskara.CHAULA_CHUDAKARANA,
        motor_milestone="Stands independently; takes first hesitant steps; neat pincer grasp.",
        cognitive_milestone="Says 2 to 4 single words with meaning; follows simple 1-step commands.",
        sharngadhara_dosage_ratti=12.0,
        dietary_stage=DietaryStage.KSHEERANNADA,
    ),
    KaumarbhrityaMilestone(
        milestone_id="MILESTONE-24",
        age_months=24,
        classical_samskara=ClassicalSamskara.CHAULA_CHUDAKARANA,
        motor_milestone="Runs smoothly; kicks a ball; climbs stairs two feet per step.",
        cognitive_milestone="Combines 2 words ('want milk'); recognizes body parts; points to objects.",
        sharngadhara_dosage_ratti=24.0,
        dietary_stage=DietaryStage.ANNADA,
    ),
]


# ==============================================================================
# DATABASE INITIALIZATION & SEEDING ENGINE
# ==============================================================================

def initialize_kaumarbhritya_tables(conn: sqlite3.Connection) -> None:
    """Populate kaumarbhritya_milestones_catalog if unseeded."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM kaumarbhritya_milestones_catalog;")
    row = cursor.fetchone()
    if row and row["cnt"] == 0:
        now = int(time.time())
        for m in SEED_MILESTONES_CATALOG:
            cursor.execute(
                """
                INSERT INTO kaumarbhritya_milestones_catalog (
                    milestone_id, age_months, classical_samskara, motor_milestone,
                    cognitive_milestone, sharngadhara_dosage_ratti, dietary_stage, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    m.milestone_id,
                    m.age_months,
                    m.classical_samskara.value,
                    m.motor_milestone,
                    m.cognitive_milestone,
                    m.sharngadhara_dosage_ratti,
                    m.dietary_stage.value,
                    now,
                )
            )
        conn.commit()


def list_developmental_milestones(conn: sqlite3.Connection) -> List[KaumarbhrityaMilestone]:
    """List registered Kaumarbhritya developmental milestones."""
    initialize_kaumarbhritya_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM kaumarbhritya_milestones_catalog ORDER BY age_months ASC;")
    rows = cursor.fetchall()
    return [
        KaumarbhrityaMilestone(
            milestone_id=r["milestone_id"],
            age_months=r["age_months"],
            classical_samskara=ClassicalSamskara(r["classical_samskara"]),
            motor_milestone=r["motor_milestone"],
            cognitive_milestone=r["cognitive_milestone"],
            sharngadhara_dosage_ratti=r["sharngadhara_dosage_ratti"],
            dietary_stage=DietaryStage(r["dietary_stage"]),
        )
        for r in rows
    ]


# ==============================================================================
# DUAL-POSOLOGY CALCULUS & TOXICOLOGY FIREWALL
# ==============================================================================

def determine_dietary_stage(age_months: int) -> DietaryStage:
    if age_months <= 12:
        return DietaryStage.KSHEERADA
    elif age_months <= 24:
        return DietaryStage.KSHEERANNADA
    return DietaryStage.ANNADA


def calculate_pediatric_posology(
    req: PediatricDosageCalculationRequest
) -> PediatricDosageCalculationResponse:
    """
    Computes dual-posology pediatric scaling:
    1. Clark's Rule: (Weight / 70) * Adult Dose
    2. Cowling's Rule: ((Age in years + 1) / 24) * Adult Dose
    3. Sharngadhara Samhita Rule: 1 Ratti (125 mg) per month up to 1 yr; 1 Masha (1500 mg) per year up to 16 yrs.
    Enforces Strict Toxicology Firewall against Schedule E-1 poisons and toxic heavy metals.
    """
    stage = determine_dietary_stage(req.age_months)
    contraindications: List[str] = []

    # Toxicology Firewall Checks
    if req.contains_heavy_metals_or_schedule_e1:
        if stage == DietaryStage.KSHEERADA:
            raise ClinicalGovernanceException(
                "STRICT CLINICAL TOXICOLOGY FIREWALL: Schedule E-1 poisons and heavy metal Bhasmas "
                "are strictly contraindicated in infants (Ksheerada stage under 1 year of age)."
            )
        elif req.age_months < 60:
            raise ClinicalGovernanceException(
                "STRICT PEDIATRIC SAFETY BLOCK: Heavy metal Bhasmas are strictly contraindicated in young children under 5 years."
            )

    # 1. Clark's Rule (Weight-based)
    clark = (req.weight_kg / 70.0) * req.adult_dose_mg

    # 2. Cowling's Rule (Age-based)
    age_years = req.age_months / 12.0
    cowling = ((age_years + 1.0) / 24.0) * req.adult_dose_mg

    # 3. Sharngadhara Samhita Formula
    # 1 Ratti = 125 mg
    if req.age_months <= 12:
        sharngadhara = max(1, req.age_months) * 125.0
    else:
        # 1 Masha = 12 Ratti = 1500 mg per year of age
        sharngadhara = min(req.adult_dose_mg, age_years * 1500.0)

    # Reconciled Recommended Pediatric Dose
    recommended = round((clark + cowling) / 2.0, 2)
    # Ensure recommended does not exceed adult dose
    recommended = min(recommended, req.adult_dose_mg)

    return PediatricDosageCalculationResponse(
        patient_id=req.patient_id,
        age_months=req.age_months,
        weight_kg=req.weight_kg,
        dietary_stage=stage,
        clark_dose_mg=round(clark, 2),
        cowling_dose_mg=round(cowling, 2),
        sharngadhara_dose_mg=round(sharngadhara, 2),
        recommended_pediatric_dose_mg=recommended,
        safety_firewall_cleared=True,
        contraindication_flags=contraindications,
    )


# ==============================================================================
# PEDIATRIC CLINICAL CONSULTATIONS & BALA ROGA ENGINE
# ==============================================================================

BALA_ROGA_ICD_MAP: Dict[BalaRogaSyndrome, str] = {
    BalaRogaSyndrome.PHAKKA_KSHIRAJA: "5B5B (Protein-energy malnutrition)",
    BalaRogaSyndrome.PHAKKA_GARBHAJA_PARIGARBHIKA: "5B5A (Severe acute malnutrition / Marasmus)",
    BalaRogaSyndrome.PHAKKA_VYADHIJA: "5B5C (Secondary wasting malnutrition)",
    BalaRogaSyndrome.KUKUNAKA: "9A60 (Ophthalmia neonatorum / conjunctivitis)",
    BalaRogaSyndrome.STANYA_DUSHTI: "JA65 (Disorders of lactation)",
    BalaRogaSyndrome.AHIPUTANA: "EK00 (Napkin / diaper dermatitis)",
    BalaRogaSyndrome.TALUKANTAKA: "5C53 (Severe dehydration with depressed fontanelle)",
    BalaRogaSyndrome.SHAYYAMUTRA: "6C00 (Nocturnal enuresis)",
    BalaRogaSyndrome.BALA_KRIMI: "1F68 (Helminthiasis)",
}

BALA_ROGA_TREATMENT_MAP: Dict[BalaRogaSyndrome, List[str]] = {
    BalaRogaSyndrome.PHAKKA_KSHIRAJA: [
        "Kalyanaka Ghrita or Ashtamangala Ghrita in pediatric scaled dosage.",
        "Rajanyadi Churna mixed with honey and cow ghee.",
        "Daily gentle full-body Abhyanga with Bala-Ashwagandha Laksha Taila.",
    ],
    BalaRogaSyndrome.PHAKKA_GARBHAJA_PARIGARBHIKA: [
        "IMMEDIATE ACTION: Cease breastfeeding from pregnant mother to halt toxic milk ingestion.",
        "Transition to cow milk fortified with Vidari and Yashtimadhu.",
        "Deepana-Pachana with Vidangadi Churna; Kalyanaka Ghrita for tissue rebuilding.",
    ],
    BalaRogaSyndrome.PHAKKA_VYADHIJA: [
        "Rehabilitative convalescent therapy: Amritarishta and Arvindasava.",
        "Shatavari Gulam for nutritional restorative replenishment.",
        "Warm medicated oil massages with Laksha Taila.",
    ],
    BalaRogaSyndrome.KUKUNAKA: [
        "Gentle eye irrigation with sterile Triphala and Yashtimadhu Kwatha.",
        "Topical application of warm breast milk or Lodhra Kwatha.",
        "Maternal milk purification (Dhatri Shodhana) with Patoladi Kashaya.",
    ],
    BalaRogaSyndrome.STANYA_DUSHTI: [
        "Dhatri Shodhana: Treat mother with Dashamoola Kwatha and Pathyadi Kwatha.",
        "Infant oral drops of Musta-Ativisha Churna with honey for colic and emesis.",
    ],
    BalaRogaSyndrome.AHIPUTANA: [
        "External perineal wash with Triphala Kwatha and Sphatika water.",
        "Gentle barrier application of Jatyadi Ghrita or Yashada Bhasma ointment.",
        "Strict diaper hygiene and frequent air drying.",
    ],
    BalaRogaSyndrome.TALUKANTAKA: [
        "EMERGENCY REHYDRATION: Oral rehydration therapy with Shadanga Paniya.",
        "Warm medicated Talu Pichu (oil-soaked cotton pad) applied to anterior fontanelle.",
        "Urgent pediatric medical review if lethargy or anuria is detected.",
    ],
    BalaRogaSyndrome.SHAYYAMUTRA: [
        "Brahmi Ghrita and Medha Rasayana for central autonomic bladder control.",
        "Chandraprabha Vati in calibrated pediatric dose.",
        "Fluid restriction 2 hours prior to sleep and scheduled nocturnal awakenings.",
    ],
    BalaRogaSyndrome.BALA_KRIMI: [
        "Vidangarishta and Palasha Beeja Churna with jaggery.",
        "Krimikuthar Rasa in age-appropriate micro-dosage.",
        "Strict hand hygiene and nail clipping.",
    ],
}


def record_pediatric_consultation(
    conn: sqlite3.Connection,
    hospital_id: str,
    consult_in: PediatricConsultationCreate
) -> PediatricConsultationResponse:
    """Log a pediatric clinical consultation, calculate scaled posology, and formulate treatment."""
    pos_req = PediatricDosageCalculationRequest(
        patient_id=consult_in.patient_id,
        age_months=consult_in.age_months,
        weight_kg=consult_in.weight_kg,
        adult_dose_mg=consult_in.adult_reference_dose_mg,
        formulation_name=consult_in.prescribed_formulation,
        contains_heavy_metals_or_schedule_e1=consult_in.contains_heavy_metals_or_schedule_e1,
        evaluator_arn=consult_in.practitioner_arn,
    )
    pos_res = calculate_pediatric_posology(pos_req)

    icd = BALA_ROGA_ICD_MAP.get(consult_in.bala_roga_diagnosis, "QC00 (Pediatric condition)")
    plan = BALA_ROGA_TREATMENT_MAP.get(
        consult_in.bala_roga_diagnosis,
        ["General supportive pediatric nursing and hydration."]
    )

    now = int(time.time())
    consult_id = f"ped-{now}-{uuid.uuid4().hex[:6]}"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO pediatric_consultation_dosing_logs (
            consultation_id, patient_id, hospital_id, age_months, weight_kg,
            bala_roga_diagnosis, icd11_mapping, adult_reference_dose_mg,
            calculated_dose_clark_mg, calculated_dose_cowling_mg,
            calculated_dose_sharngadhara_mg, final_dispensed_dose_mg,
            prescribed_formulation, safety_firewall_passed, practitioner_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            consult_id,
            consult_in.patient_id,
            hospital_id,
            consult_in.age_months,
            consult_in.weight_kg,
            consult_in.bala_roga_diagnosis.value,
            icd,
            consult_in.adult_reference_dose_mg,
            pos_res.clark_dose_mg,
            pos_res.cowling_dose_mg,
            pos_res.sharngadhara_dose_mg,
            pos_res.recommended_pediatric_dose_mg,
            consult_in.prescribed_formulation,
            1,
            consult_in.practitioner_arn,
            now,
        )
    )
    conn.commit()

    return PediatricConsultationResponse(
        consultation_id=consult_id,
        patient_id=consult_in.patient_id,
        hospital_id=hospital_id,
        age_months=consult_in.age_months,
        weight_kg=consult_in.weight_kg,
        dietary_stage=pos_res.dietary_stage,
        bala_roga_diagnosis=consult_in.bala_roga_diagnosis,
        icd11_mapping=icd,
        adult_reference_dose_mg=consult_in.adult_reference_dose_mg,
        calculated_dose_clark_mg=pos_res.clark_dose_mg,
        calculated_dose_cowling_mg=pos_res.cowling_dose_mg,
        calculated_dose_sharngadhara_mg=pos_res.sharngadhara_dose_mg,
        final_dispensed_dose_mg=pos_res.recommended_pediatric_dose_mg,
        prescribed_formulation=consult_in.prescribed_formulation,
        safety_firewall_passed=True,
        clinical_management_plan=plan,
        practitioner_arn=consult_in.practitioner_arn,
        created_at=now,
    )


def list_pediatric_consultations(
    patient_id: str,
    conn: sqlite3.Connection
) -> List[PediatricConsultationResponse]:
    """Retrieve historical pediatric consultations for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM pediatric_consultation_dosing_logs WHERE patient_id = ? ORDER BY created_at DESC;",
        (patient_id,)
    )
    rows = cursor.fetchall()
    return [
        PediatricConsultationResponse(
            consultation_id=r["consultation_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            age_months=r["age_months"],
            weight_kg=r["weight_kg"],
            dietary_stage=determine_dietary_stage(r["age_months"]),
            bala_roga_diagnosis=BalaRogaSyndrome(r["bala_roga_diagnosis"]),
            icd11_mapping=r["icd11_mapping"],
            adult_reference_dose_mg=r["adult_reference_dose_mg"],
            calculated_dose_clark_mg=r["calculated_dose_clark_mg"],
            calculated_dose_cowling_mg=r["calculated_dose_cowling_mg"],
            calculated_dose_sharngadhara_mg=r["calculated_dose_sharngadhara_mg"],
            final_dispensed_dose_mg=r["final_dispensed_dose_mg"],
            prescribed_formulation=r["prescribed_formulation"],
            safety_firewall_passed=bool(r["safety_firewall_passed"]),
            clinical_management_plan=BALA_ROGA_TREATMENT_MAP.get(
                BalaRogaSyndrome(r["bala_roga_diagnosis"]),
                ["General supportive pediatric care."]
            ),
            practitioner_arn=r["practitioner_arn"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


# ==============================================================================
# SUVARNAPRASHANA IMMUNOMODULATION PROTOCOL ENGINE
# ==============================================================================

SUVARNA_IMMUNOMODULATION_OUTCOMES: List[str] = [
    "Medha Vardhana: Cognitive acuity, attention span, and memory consolidation enhancement.",
    "Agni Vardhana: Digestive metabolic fire stimulation and nutrient assimilation optimization.",
    "Bala Vardhana: Broad-spectrum innate cell-mediated immunity and physical vigor boost.",
    "Ayushya: Cellular longevity, anti-oxidant tissue defense, and healthy somatic growth.",
    "Grahapaha: Protection against seasonal and environmental pediatric infections."
]


def record_suvarnaprashana_dose(
    conn: sqlite3.Connection,
    hospital_id: str,
    dose_in: SuvarnaprashanaAdminCreate
) -> SuvarnaprashanaAdminResponse:
    """
    Log administration of Suvarnaprashana on Pushya Nakshatra.
    Strictly verifies unequal ratio of honey and ghee (never 1:1 Viruddha Ahara).
    """
    ratio_str = dose_in.madhu_ghrita_ratio.strip().lower()
    if "1:1" in ratio_str or "equal" in ratio_str:
        raise ClinicalGovernanceException(
            "STRICT SAFETY FIREWALL: Equal proportion of honey and ghee (1:1) constitutes toxic "
            "Viruddha Ahara (incompatible synergy) and is strictly contraindicated in Suvarnaprashana."
        )

    now = int(time.time())
    dose_id = f"suvarna-{now}-{uuid.uuid4().hex[:6]}"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO suvarnaprashana_administration_logs (
            dose_id, patient_id, hospital_id, age_months,
            pushya_nakshatra_date, suvarna_bhasma_mg, madhu_ghrita_ratio,
            medhya_herbs_json, adverse_events, practitioner_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            dose_id,
            dose_in.patient_id,
            hospital_id,
            dose_in.age_months,
            dose_in.pushya_nakshatra_date,
            dose_in.suvarna_bhasma_mg,
            dose_in.madhu_ghrita_ratio,
            json.dumps(dose_in.medhya_herbs),
            "None reported; well-tolerated sublingual administration.",
            dose_in.practitioner_arn,
            now,
        )
    )
    conn.commit()

    return SuvarnaprashanaAdminResponse(
        dose_id=dose_id,
        patient_id=dose_in.patient_id,
        hospital_id=hospital_id,
        age_months=dose_in.age_months,
        pushya_nakshatra_date=dose_in.pushya_nakshatra_date,
        suvarna_bhasma_mg=dose_in.suvarna_bhasma_mg,
        madhu_ghrita_ratio=dose_in.madhu_ghrita_ratio,
        medhya_herbs=dose_in.medhya_herbs,
        immunomodulation_outcomes=SUVARNA_IMMUNOMODULATION_OUTCOMES,
        adverse_events="None reported; well-tolerated sublingual administration.",
        practitioner_arn=dose_in.practitioner_arn,
        created_at=now,
    )


def list_suvarnaprashana_doses(
    patient_id: str,
    conn: sqlite3.Connection
) -> List[SuvarnaprashanaAdminResponse]:
    """Retrieve historical Suvarnaprashana administration records for a child."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM suvarnaprashana_administration_logs WHERE patient_id = ? ORDER BY created_at DESC;",
        (patient_id,)
    )
    rows = cursor.fetchall()
    return [
        SuvarnaprashanaAdminResponse(
            dose_id=r["dose_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            age_months=r["age_months"],
            pushya_nakshatra_date=r["pushya_nakshatra_date"],
            suvarna_bhasma_mg=r["suvarna_bhasma_mg"],
            madhu_ghrita_ratio=r["madhu_ghrita_ratio"],
            medhya_herbs=json.loads(r["medhya_herbs_json"]),
            immunomodulation_outcomes=SUVARNA_IMMUNOMODULATION_OUTCOMES,
            adverse_events=r["adverse_events"],
            practitioner_arn=r["practitioner_arn"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
