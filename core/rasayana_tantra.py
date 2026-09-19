"""
Rasayana Tantra, Jara Chikitsa & Longevity Medicine Engine
==========================================================
Implements:
1. Classical Rasayana Protocols Catalog (Kamya, Naimittika, Ajasrika, Medhya, Achara)
2. Ojas Reserve, Vyadhikshamatwa & Biological Ageing Calculus (Ojo Visramsa, Vyapat, Kshaya)
3. Decadal Loss of Attributes Analysis (Sharngadhara Samhita Purva Khanda 6/19)
4. Charakokta Chatush-Medhya Rasayana Cognitive Protocol
5. Intensive Kuti Praveshika Screening & Safety Firewall (Trigarbha Cottage Architecture)
6. SQLite WAL Persistence with Hash-Chained Audit Ledger Logging
"""

from __future__ import annotations
import json
import time
import uuid
import sqlite3
from typing import List, Optional, Dict, Any, Tuple

from core.database import append_audit_log
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from models.rasayana_tantra import (
    KutiPraveshikaAdmissionRequest,
    KutiPraveshikaAdmissionResponse,
    OjasEvaluationRequest,
    OjasEvaluationResponse,
    OjasStatus,
    RasayanaMode,
    RasayanaProtocol,
    RasayanaType,
)

# ==============================================================================
# 1. CLASSICAL RASAYANA CATALOG SEED DATA
# ==============================================================================

SEED_RASAYANA_CATALOG: List[RasayanaProtocol] = [
    RasayanaProtocol(
        protocol_id="RAS-CHYAVAN-01",
        sanskrit_name="च्यवनप्राश रसायन (Chyavanaprasha Rasayana)",
        rasayana_type=RasayanaType.KAMYA,
        mode=RasayanaMode.VATATAPIKA,
        primary_ingredients=[
            "Amalaki (Emblica officinalis)",
            "Dashamoola (Ten Roots)",
            "Ashtavarga compounds",
            "Tugaksheeri (Bambusa bambos)",
            "Pippali (Piper longum)",
            "Go-Ghrita (Cow Ghee)",
            "Shuddha Madhu (Honey)"
        ],
        target_dhatu="Rasa, Rakta, Mamsa, Meda, Asthi, Majja, Shukra (Sarva Dhatu)",
        classical_reference="Charaka Samhita, Chikitsa Sthana 1/1 (Abhayayamalakiya Rasayana Pada, Verses 62-74)",
        indications=[
            "Tissue wasting (Kshaya)",
            "Chronic respiratory debility (Kasa-Shwasa)",
            "Immunosenescence & physical exhaustion",
            "Premature greying and loss of skin luster"
        ]
    ),
    RasayanaProtocol(
        protocol_id="RAS-BRAHMA-02",
        sanskrit_name="ब्रह्म रसायन (Brahma Rasayana)",
        rasayana_type=RasayanaType.KAMYA,
        mode=RasayanaMode.VATATAPIKA,
        primary_ingredients=[
            "Amalaki (1000 fruits)",
            "Haritaki (1000 fruits)",
            "Dashamoola",
            "Pippali",
            "Shankhapushpi",
            "Guduchi",
            "Go-Ghrita & Tilataila",
            "Shuddha Madhu"
        ],
        target_dhatu="Majja, Shukra, Ojas",
        classical_reference="Charaka Samhita, Chikitsa Sthana 1/1 (Verses 41-57)",
        indications=[
            "Severe Ojas depletion (Ojo Kshaya)",
            "Loss of cognitive stamina & analytical acumen",
            "Senile debility, wrinkles (Vali) and greying (Palitya)",
            "Profound neuromuscular exhaustion"
        ]
    ),
    RasayanaProtocol(
        protocol_id="RAS-TRIPHALA-03",
        sanskrit_name="त्रिफला रसायन (Triphala Rasayana)",
        rasayana_type=RasayanaType.KAMYA,
        mode=RasayanaMode.VATATAPIKA,
        primary_ingredients=[
            "Haritaki (with Honey & Ghee)",
            "Bibhitaki (with Honey & Ghee)",
            "Amalaki (with Honey & Ghee)",
            "Loha Bhasma (Micro-incinerated Iron)"
        ],
        target_dhatu="Rasa, Rakta, Drishti (Netra / Ophthalmic tissue)",
        classical_reference="Charaka Samhita, Chikitsa Sthana 1/3 (Karaprachitiya Rasayana Pada, Verses 41-47)",
        indications=[
            "Ophthalmic senescence and visual accommodation loss (Drishti Mandya)",
            "Sluggish digestion (Agnimandya) and metabolic sluggishness",
            "Microcirculatory stagnation and microvascular rigidity"
        ]
    ),
    RasayanaProtocol(
        protocol_id="RAS-SHILAJATU-04",
        sanskrit_name="शिलाजतु रसायन (Shilajatu Rasayana)",
        rasayana_type=RasayanaType.NAIMITTIKA,
        mode=RasayanaMode.VATATAPIKA,
        primary_ingredients=[
            "Shuddha Shilajatu (Purified Asphaltum punjabianum)",
            "Triphala Kwatha",
            "Loha Bhasma",
            "Ksheera (Warm Cow Milk)"
        ],
        target_dhatu="Meda, Mutravaha Srotas, Asthi, Shukra",
        classical_reference="Charaka Samhita, Chikitsa Sthana 1/3 (Verses 48-65)",
        indications=[
            "Prameha (Metabolic Syndrome & Type-2 Diabetes Mellitus)",
            "Medoroga (Metabolic adiposity & lipid dysfunction)",
            "Urinary tract weakness and pelvic tone loss",
            "Musculoskeletal debility and age-related osteopenia"
        ]
    ),
    RasayanaProtocol(
        protocol_id="RAS-AMALAKI-05",
        sanskrit_name="आमलकी रसायन (Amalaki Rasayana)",
        rasayana_type=RasayanaType.KAMYA,
        mode=RasayanaMode.VATATAPIKA,
        primary_ingredients=[
            "Amalaki Churna bhavita with fresh Amalaki Swarasa (21 cycles)",
            "Go-Ghrita",
            "Shuddha Madhu",
            "Sita (Rock Sugar)"
        ],
        target_dhatu="Rasa, Rakta, Twak, Shukra",
        classical_reference="Charaka Samhita, Chikitsa Sthana 1/2 (Pranakamiya Rasayana Pada, Verses 8-11)",
        indications=[
            "Cellular oxidative stress & lipid peroxidation",
            "Amlapitta (Hyperacidity and systemic Pitta flare-ups)",
            "Dermal thinning, dryness, and loss of Chhavi (luster)",
            "Immune deficiency and recurrent seasonal susceptibility"
        ]
    ),
    RasayanaProtocol(
        protocol_id="RAS-MEDHYA-06",
        sanskrit_name="चतुष्-मेध्य रसायन (Charakokta Chatush-Medhya Rasayana)",
        rasayana_type=RasayanaType.MEDHYA,
        mode=RasayanaMode.VATATAPIKA,
        primary_ingredients=[
            "Mandukaparni Swarasa (Fresh leaf juice of Centella asiatica)",
            "Yashtimadhu Churna (Glycyrrhiza glabra root powder with milk)",
            "Guduchi Swarasa (Fresh stem juice of Tinospora cordifolia)",
            "Shankhapushpi Kalka (Whole plant paste of Convolvulus pluricaulis)"
        ],
        target_dhatu="Majja Dhatu, Manovaha Srotas, Ojas",
        classical_reference="Charaka Samhita, Chikitsa Sthana 1/3 (Verses 30-31)",
        indications=[
            "Smriti Bhransha (Cognitive decline, memory deficit, and executive fog)",
            "Mental exhaustion and academic/workplace burnout",
            "Age-related neurodegeneration and synapse loss",
            "Chinta & Mano-Dourbalya (Anxiety and mental fragility)"
        ]
    ),
    RasayanaProtocol(
        protocol_id="RAS-KUTI-CHYAVAN-07",
        sanskrit_name="कुटीप्रावेशिक च्यवन रसायन (Kuti Praveshika Chyavana Rejuvenation)",
        rasayana_type=RasayanaType.KAMYA,
        mode=RasayanaMode.KUTI_PRAVESHIKA,
        primary_ingredients=[
            "Maharshi Chyavana Formulation Compound",
            "Go-Ghrita & Ksheera intensive regimen",
            "Fresh Amalaki Swarasa decoctions",
            "Brahmi and Shankhapushpi infusions"
        ],
        target_dhatu="Sarva Dhatu (Total Systemic Biological Age Reversal)",
        classical_reference="Charaka Samhita, Chikitsa Sthana 1/1 (Verses 16-24)",
        indications=[
            "Advanced biological senescence",
            "Intensive cellular regeneration and telomeric preservation retreat",
            "Total constitutional refurbishment following Panchakarma Shodhana"
        ]
    ),
    RasayanaProtocol(
        protocol_id="RAS-ACHARA-08",
        sanskrit_name="आचार रसायन (Achara Rasayana - Behavioral Longevity Protocol)",
        rasayana_type=RasayanaType.ACHARA,
        mode=RasayanaMode.VATATAPIKA,
        primary_ingredients=[
            "Satya-Vadi (Truthfulness & integrity)",
            "Akrodha (Freedom from anger & hostility)",
            "Madyamaithuna-Nivritti (Moderation and abstinence)",
            "Prashanta (Serenity and regular meditation)",
            "Jitendriya (Sensory mastery and equanimity)"
        ],
        target_dhatu="Sattva Guna, Ojas, Manovaha Srotas",
        classical_reference="Charaka Samhita, Chikitsa Sthana 1/4 (Verses 30-35)",
        indications=[
            "Psychosomatic stress and autonomic hyperarousal",
            "Chronic neuro-endocrine dysregulation",
            "Longevity optimization without pharmacological interventions"
        ]
    )
]


# ==============================================================================
# 2. DATABASE SEEDING & INITIALIZATION
# ==============================================================================

def initialize_rasayana_tables(conn: sqlite3.Connection) -> None:
    """Seed classical Rasayana catalog if empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM rasayana_protocols_catalog;")
    row = cursor.fetchone()
    if row and row["cnt"] == 0:
        now = int(time.time())
        for proto in SEED_RASAYANA_CATALOG:
            cursor.execute(
                """
                INSERT INTO rasayana_protocols_catalog (
                    protocol_id, sanskrit_name, rasayana_type, mode,
                    primary_ingredients_json, target_dhatu,
                    classical_reference, indications_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    proto.protocol_id,
                    proto.sanskrit_name,
                    proto.rasayana_type.value,
                    proto.mode.value,
                    json.dumps(proto.primary_ingredients),
                    proto.target_dhatu,
                    proto.classical_reference,
                    json.dumps(proto.indications),
                    now
                )
            )
        conn.commit()


# ==============================================================================
# 3. RASAYANA PROTOCOL CATALOG QUERIES
# ==============================================================================

def list_all_rasayana_protocols(
    conn: sqlite3.Connection,
    rasayana_type: Optional[RasayanaType] = None,
    mode: Optional[RasayanaMode] = None
) -> List[RasayanaProtocol]:
    """Retrieve catalog of classical Rasayana formulations with optional filtering."""
    cursor = conn.cursor()
    query = "SELECT * FROM rasayana_protocols_catalog WHERE 1=1"
    params: List[Any] = []

    if rasayana_type:
        query += " AND rasayana_type = ?"
        params.append(rasayana_type.value)
    if mode:
        query += " AND mode = ?"
        params.append(mode.value)

    query += " ORDER BY protocol_id ASC;"
    cursor.execute(query, params)
    rows = cursor.fetchall()

    return [
        RasayanaProtocol(
            protocol_id=r["protocol_id"],
            sanskrit_name=r["sanskrit_name"],
            rasayana_type=RasayanaType(r["rasayana_type"]),
            mode=RasayanaMode(r["mode"]),
            primary_ingredients=json.loads(r["primary_ingredients_json"]),
            target_dhatu=r["target_dhatu"],
            classical_reference=r["classical_reference"],
            indications=json.loads(r["indications_json"]),
        )
        for r in rows
    ]


def get_rasayana_protocol_by_id(protocol_id: str, conn: sqlite3.Connection) -> RasayanaProtocol:
    """Retrieve single Rasayana protocol specification by unique protocol_id."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rasayana_protocols_catalog WHERE protocol_id = ?;", (protocol_id,))
    r = cursor.fetchone()
    if not r:
        raise RecordNotFoundException(entity="Rasayana Protocol", identifier=protocol_id)

    return RasayanaProtocol(
        protocol_id=r["protocol_id"],
        sanskrit_name=r["sanskrit_name"],
        rasayana_type=RasayanaType(r["rasayana_type"]),
        mode=RasayanaMode(r["mode"]),
        primary_ingredients=json.loads(r["primary_ingredients_json"]),
        target_dhatu=r["target_dhatu"],
        classical_reference=r["classical_reference"],
        indications=json.loads(r["indications_json"]),
    )


# ==============================================================================
# 4. DECADAL LOSS OF ATTRIBUTES CALCULUS (Sharngadhara Samhita)
# ==============================================================================

def determine_decadal_attribute_decay(chronological_age: int) -> str:
    """
    Identifies the primary physiological attribute undergoing natural decadal decay
    according to Sharngadhara Samhita (Purva Khanda 6/19).
    """
    if chronological_age <= 10:
        return "Decade 1 (1-10 yrs): Balya (Childhood Innocence & Somatic Growth Rate)"
    elif chronological_age <= 20:
        return "Decade 2 (11-20 yrs): Vriddhi (Stature, Skeletal Morphometry & Tissue Accretion)"
    elif chronological_age <= 30:
        return "Decade 3 (21-30 yrs): Chhavi (Skin Radiance, Complexion & Physical Beauty)"
    elif chronological_age <= 40:
        return "Decade 4 (31-40 yrs): Medha (Intellect, Analytical Grasping & Memory Retention)"
    elif chronological_age <= 50:
        return "Decade 5 (41-50 yrs): Twak (Dermal Elasticity, Collagen Tone & Tactile Sensitivity)"
    elif chronological_age <= 60:
        return "Decade 6 (51-60 yrs): Drishti (Visual Acuity & Ophthalmic Ciliary Accommodation)"
    elif chronological_age <= 70:
        return "Decade 7 (61-70 yrs): Shukra (Reproductive Vitality, Libido & Deep Tissue Essence)"
    elif chronological_age <= 80:
        return "Decade 8 (71-80 yrs): Vikrama (Physical Valour, Muscle Strength, Stamina & Endurance)"
    elif chronological_age <= 90:
        return "Decade 9 (81-90 yrs): Buddhi (Higher Cognitive Discernment, Wisdom & Decision Clarity)"
    else:
        return "Decade 10 (91-100+ yrs): Karmendriya (Motor Organ Coordination, Dexterity & Autonomy)"


# ==============================================================================
# 5. OJAS RESERVE & BIOLOGICAL AGEING EVALUATION ENGINE
# ==============================================================================

def calculate_ojas_and_biological_age(
    request: OjasEvaluationRequest,
    hospital_id: str,
    conn: sqlite3.Connection
) -> OjasEvaluationResponse:
    """
    Calculates:
    1. Ojo Visramsa, Vyapat, and Kshaya pathology scores
    2. Composite Ojas Reserve Score & Vyadhikshamatwa Status
    3. Decadal attribute decay per Sharngadhara Samhita
    4. Biological Age Differential from objective bio-functional markers
    5. Prescribed targeted Rasayana protocol & Achara Rasayana lifestyle guidance
    """
    # 1. Pathology scores (0.0 to 100.0)
    visramsa_score = min(100.0, float(len(request.visramsa_symptoms)) * 25.0)
    vyapat_score = min(100.0, float(len(request.vyapat_symptoms)) * 25.0)
    kshaya_score = min(100.0, float(len(request.kshaya_symptoms)) * 33.34)

    # 2. Mathematical Ojas Reserve Formula
    raw_ojas = 100.0 - (visramsa_score * 0.30 + vyapat_score * 0.30 + kshaya_score * 0.40)
    ojas_score = max(0.0, min(100.0, round(raw_ojas, 2)))

    # Classification of immune reserve
    if ojas_score >= 80.0:
        ojas_status = OjasStatus.PRAVARA_OJAS
    elif ojas_score >= 50.0:
        ojas_status = OjasStatus.MADHYAMA_OJAS
    else:
        ojas_status = OjasStatus.AVARA_OJAS

    # 3. Decadal attribute
    decadal_attribute = determine_decadal_attribute_decay(request.chronological_age)

    # 4. Biological Age Calculus
    # Calculate functional deficit points
    grip_def = max(0.0, (35.0 - request.grip_strength_kg) / 35.0) * 10.0
    vc_def = max(0.0, (3.5 - request.vital_capacity_liters) / 3.5) * 10.0
    mobility_def = max(0.0, (8.0 - request.joint_mobility_score) / 8.0) * 8.0
    luster_def = max(0.0, (8.0 - request.skin_luster_score) / 8.0) * 8.0
    memory_def = max(0.0, (8.0 - request.cognitive_memory_score) / 8.0) * 10.0
    ojas_def = max(0.0, (80.0 - ojas_score) / 80.0) * 15.0

    total_deficit = grip_def + vc_def + mobility_def + luster_def + memory_def + ojas_def

    # Calculate functional surplus points (for exceptionally resilient individuals)
    grip_surplus = max(0.0, (request.grip_strength_kg - 40.0) / 40.0) * 5.0
    vc_surplus = max(0.0, (request.vital_capacity_liters - 4.0) / 4.0) * 5.0
    mobility_surplus = max(0.0, (request.joint_mobility_score - 8.0) / 2.0) * 3.0
    luster_surplus = max(0.0, (request.skin_luster_score - 8.0) / 2.0) * 3.0
    memory_surplus = max(0.0, (request.cognitive_memory_score - 8.0) / 2.0) * 3.0
    ojas_surplus = max(0.0, (ojas_score - 85.0) / 15.0) * 5.0

    total_surplus = grip_surplus + vc_surplus + mobility_surplus + luster_surplus + memory_surplus + ojas_surplus

    # Biological age differential
    net_age_adjustment = round((total_deficit - total_surplus) * 0.4, 1)
    biological_age = round(float(request.chronological_age) + net_age_adjustment, 1)
    age_differential = round(biological_age - float(request.chronological_age), 1)

    # 5. Targeted Rasayana Selection Logic
    if request.cognitive_memory_score < 6.0 or (31 <= request.chronological_age <= 40) or (81 <= request.chronological_age <= 90):
        prescribed_id = "RAS-MEDHYA-06"
        recommended_formulation = "Charakokta Chatush-Medhya Rasayana (Mandukaparni juice, Yashtimadhu with milk, Guduchi, Shankhapushpi)"
    elif ojas_score < 50.0 or len(request.kshaya_symptoms) > 0:
        prescribed_id = "RAS-BRAHMA-02"
        recommended_formulation = "Brahma Rasayana with warm Cow Milk & Pure Go-Ghrita (Twice Daily on empty stomach)"
    elif request.joint_mobility_score < 6.0 or request.chronological_age >= 60:
        prescribed_id = "RAS-SHILAJATU-04"
        recommended_formulation = "Shuddha Shilajatu Rasayana (500mg with Triphala Kwatha & Cow Milk)"
    elif request.skin_luster_score < 6.0 or (21 <= request.chronological_age <= 30) or (41 <= request.chronological_age <= 50):
        prescribed_id = "RAS-AMALAKI-05"
        recommended_formulation = "Amalaki Rasayana (Bhavita 21-times with Emblica juice, Honey, and Ghee)"
    else:
        prescribed_id = "RAS-CHYAVAN-01"
        recommended_formulation = "Chyavanaprasha Rasayana (10g twice daily with warm A2 Cow Milk)"

    achara_guidelines = [
        "Satya-Vadi (Truthfulness in speech) and absolute avoidance of anger (Akrodha).",
        "Sensory restraint, moderation in wakefulness, and complete abstinence from alcohol.",
        "Dhyana-Tatpara (Daily mindfulness, meditation, and serene mental balance).",
        "Priya-Vadi (Compassionate, non-injurious dialogue) and kindness to all living beings.",
        "Guru-Vridhan-Pujaka (Reverence for spiritual preceptors, elders, and clinical healers)."
    ]

    now = int(time.time())
    evaluation_id = f"ojas-{now}-{uuid.uuid4().hex[:6]}"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO ojas_biological_age_evaluations (
            evaluation_id, patient_id, hospital_id, chronological_age,
            biological_age, ojas_score, ojas_status, visramsa_score,
            vyapat_score, kshaya_score, decadal_attribute_decay,
            prescribed_rasayana_id, practitioner_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            evaluation_id,
            request.patient_id,
            hospital_id,
            request.chronological_age,
            biological_age,
            ojas_score,
            ojas_status.value,
            visramsa_score,
            vyapat_score,
            kshaya_score,
            decadal_attribute,
            prescribed_id,
            request.evaluator_arn,
            now
        )
    )
    conn.commit()

    append_audit_log(
        conn=conn,
        hospital_id=hospital_id,
        actor_id=request.evaluator_arn,
        action="EVALUATION_CREATE",
        entity_type="OJAS_BIOLOGICAL_AGE",
        entity_id=evaluation_id,
        details={
            "patient_id": request.patient_id,
            "chronological_age": request.chronological_age,
            "biological_age": biological_age,
            "age_differential": age_differential,
            "ojas_score": ojas_score,
            "ojas_status": ojas_status.value,
            "prescribed_rasayana_id": prescribed_id
        }
    )

    return OjasEvaluationResponse(
        evaluation_id=evaluation_id,
        patient_id=request.patient_id,
        hospital_id=hospital_id,
        chronological_age=request.chronological_age,
        biological_age=biological_age,
        age_differential_years=age_differential,
        ojas_score=ojas_score,
        ojas_status=ojas_status,
        visramsa_score=visramsa_score,
        vyapat_score=vyapat_score,
        kshaya_score=kshaya_score,
        decadal_attribute_decay=decadal_attribute,
        prescribed_rasayana_id=prescribed_id,
        recommended_rasayana_formulation=recommended_formulation,
        lifestyle_achara_rasayana=achara_guidelines,
        practitioner_arn=request.evaluator_arn,
        created_at=now
    )


def list_patient_ojas_evaluations(
    patient_id: str,
    conn: sqlite3.Connection
) -> List[OjasEvaluationResponse]:
    """Retrieve historical Ojas and biological age evaluations for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM ojas_biological_age_evaluations
        WHERE patient_id = ?
        ORDER BY created_at DESC;
        """,
        (patient_id,)
    )
    rows = cursor.fetchall()

    evaluations: List[OjasEvaluationResponse] = []
    for r in rows:
        chrono = r["chronological_age"]
        bio = r["biological_age"]
        diff = round(bio - chrono, 1)

        # Retrieve protocol name if possible
        rec_name = "Classical Rasayana Formulation"
        try:
            proto = get_rasayana_protocol_by_id(r["prescribed_rasayana_id"], conn)
            rec_name = proto.sanskrit_name
        except Exception:
            pass

        evaluations.append(
            OjasEvaluationResponse(
                evaluation_id=r["evaluation_id"],
                patient_id=r["patient_id"],
                hospital_id=r["hospital_id"],
                chronological_age=chrono,
                biological_age=bio,
                age_differential_years=diff,
                ojas_score=r["ojas_score"],
                ojas_status=OjasStatus(r["ojas_status"]),
                visramsa_score=r["visramsa_score"],
                vyapat_score=r["vyapat_score"],
                kshaya_score=r["kshaya_score"],
                decadal_attribute_decay=r["decadal_attribute_decay"],
                prescribed_rasayana_id=r["prescribed_rasayana_id"],
                recommended_rasayana_formulation=rec_name,
                lifestyle_achara_rasayana=[
                    "Satya-Vadi (Truthfulness) and Akrodha (Freedom from anger).",
                    "Dhyana-Tatpara (Daily meditation and spiritual balance).",
                    "Priya-Vadi (Benevolent, peaceful conduct)."
                ],
                practitioner_arn=r["practitioner_arn"],
                created_at=r["created_at"]
            )
        )
    return evaluations


# ==============================================================================
# 6. KUTI PRAVESHIKA SCREENING & SAFETY FIREWALL
# ==============================================================================

def admit_kuti_praveshika_episode(
    conn: sqlite3.Connection,
    hospital_id: str,
    request: KutiPraveshikaAdmissionRequest
) -> KutiPraveshikaAdmissionResponse:
    """
    Screens candidate for intensive indoor cottage retreat (Kuti Praveshika Rasayana).
    Enforces classical safety firewalls:
    1. Mandatory prior Panchakarma Shodhana (Bio-cleansing)
    2. Absence of acute systemic infection
    3. Blood pressure stability (Systolic < 160, Diastolic < 100)
    4. Absence of decompensated cardiac or psychiatric instability
    """
    flags: List[str] = []

    # Firewall Rule 1: Prior Shodhana Verification
    if not request.pre_shodhana_completed:
        flags.append(
            "CONTRAINDICATION: Prior Panchakarma bio-cleansing (Vamana / Virechana Shodhana) is mandatory. "
            "Administering potent Rasayana into uncleared Srotas precipitates toxic Ama obstruction."
        )

    # Firewall Rule 2: Active Acute Infection
    if request.has_active_acute_infection:
        flags.append(
            "CONTRAINDICATION: Active acute febrile or inflammatory infection detected. "
            "Rasayana Brimhana is strictly prohibited during active Taruna Jwara / toxic states."
        )

    # Firewall Rule 3: Cardiovascular Safety Limits
    if request.blood_pressure_systolic >= 160 or request.blood_pressure_diastolic >= 100:
        flags.append(
            f"CONTRAINDICATION: Stage-2 Hypertension ({request.blood_pressure_systolic}/{request.blood_pressure_diastolic} mmHg). "
            "Sensory isolation and unction therapies require pre-stabilization of vascular hemodynamics."
        )

    # Firewall Rule 4: Cardiac and Psychiatric Instability
    if request.has_severe_cardiac_or_psychiatric_instability:
        flags.append(
            "CONTRAINDICATION: Decompensated cardiac disease or acute psychiatric instability detected. "
            "Strict solitary sensory confinement within Trigarbha Kuti is unsafe."
        )

    eligibility_cleared = (len(flags) == 0)

    guidelines = [
        "Trigarbha Architectural Spec: Three concentric walls with solitary eastern/northern ventilation portal to eliminate drafts, direct sunlight, and external acoustic shock.",
        "Microclimatic Control: Dry, elevated topography free from smoke, predatory insects, and atmospheric pollutants.",
        "Clinical Escort: Strict solitary access limited exclusively to certified NCISM Vaidya and dedicated Paricharka.",
        "Post-Kuti Re-adaptation: Gradual stepwise daylight, wind, and dietary reintegration over a duration equal to cottage stay."
    ]

    now = int(time.time())
    episode_id = f"kuti-{now}-{uuid.uuid4().hex[:6]}"
    compliance_score = 100.0 if eligibility_cleared else 0.0

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO kuti_praveshika_treatment_episodes (
            episode_id, patient_id, hospital_id, duration_days,
            pre_shodhana_completed, rasayana_formulation,
            isolation_compliance_score, eligibility_cleared,
            observations, practitioner_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            episode_id,
            request.patient_id,
            hospital_id,
            request.planned_duration_days,
            1 if request.pre_shodhana_completed else 0,
            request.rasayana_formulation,
            compliance_score,
            1 if eligibility_cleared else 0,
            json.dumps({"contraindications": flags, "guidelines": guidelines}),
            request.practitioner_arn,
            now
        )
    )
    conn.commit()

    append_audit_log(
        conn=conn,
        hospital_id=hospital_id,
        actor_id=request.practitioner_arn,
        action="ADMISSION_SCREENING",
        entity_type="KUTI_PRAVESHIKA",
        entity_id=episode_id,
        details={
            "patient_id": request.patient_id,
            "duration_days": request.planned_duration_days,
            "eligibility_cleared": eligibility_cleared,
            "contraindication_count": len(flags)
        }
    )

    return KutiPraveshikaAdmissionResponse(
        episode_id=episode_id,
        patient_id=request.patient_id,
        hospital_id=hospital_id,
        duration_days=request.planned_duration_days,
        pre_shodhana_completed=request.pre_shodhana_completed,
        rasayana_formulation=request.rasayana_formulation,
        eligibility_cleared=eligibility_cleared,
        contraindication_flags=flags,
        kuti_design_guidelines=guidelines,
        practitioner_arn=request.practitioner_arn,
        created_at=now
    )


def list_kuti_praveshika_episodes(
    patient_id: str,
    conn: sqlite3.Connection
) -> List[KutiPraveshikaAdmissionResponse]:
    """Retrieve historical Kuti Praveshika admission screening episodes for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM kuti_praveshika_treatment_episodes
        WHERE patient_id = ?
        ORDER BY created_at DESC;
        """,
        (patient_id,)
    )
    rows = cursor.fetchall()

    episodes: List[KutiPraveshikaAdmissionResponse] = []
    for r in rows:
        obs = {}
        try:
            obs = json.loads(r["observations"])
        except Exception:
            pass

        episodes.append(
            KutiPraveshikaAdmissionResponse(
                episode_id=r["episode_id"],
                patient_id=r["patient_id"],
                hospital_id=r["hospital_id"],
                duration_days=r["duration_days"],
                pre_shodhana_completed=bool(r["pre_shodhana_completed"]),
                rasayana_formulation=r["rasayana_formulation"],
                eligibility_cleared=bool(r["eligibility_cleared"]),
                contraindication_flags=obs.get("contraindications", []),
                kuti_design_guidelines=obs.get("guidelines", [
                    "Trigarbha cottage architecture adherence verified."
                ]),
                practitioner_arn=r["practitioner_arn"],
                created_at=r["created_at"]
            )
        )
    return episodes
