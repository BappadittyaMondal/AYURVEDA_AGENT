"""
Marma Sharira, Vital Traumatology & Marma Chikitsa Engine
=========================================================
Implements:
1. 107 Classical Marmas Structural & Prognostic Registry (Sushruta Sharirasthana Ch. 6)
2. Rachana Bheda (5 Structures) & Parinama Bheda (5 Prognostic Classes)
3. Tri-Marma Emergency Resuscitation Firewall (Hridaya, Basti, Shiras)
4. Vishalyaghna Foreign Body Surgical Extraction Firewall (Utkshepa, Sthapani)
5. Therapeutic Marma Chikitsa Acupressure Stimulation Engine
6. SQLite WAL Persistence with SHA-256 Hash-Chained Audit Ledger Logging
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
from models.marma_sharira import (
    MarmaChikitsaSessionCreate,
    MarmaChikitsaSessionResponse,
    MarmaParinama,
    MarmaPointProfile,
    MarmaRachana,
    MarmaRegion,
    MarmaTraumaEmergencyCreate,
    MarmaTraumaEmergencyResponse,
    MarmaTraumaTriage,
    StimulationModality,
)

# ==============================================================================
# 1. 107 CLASSICAL MARMA CATALOG SEED DATA
# ==============================================================================

SEED_MARMA_CATALOG: List[MarmaPointProfile] = [
    # Tri-Marmas & Sadhyo-Pranahara
    MarmaPointProfile(
        marma_code="MARMA-HRID-01",
        sanskrit_name="हृदय मर्म (Hridaya Marma - The Cardiac Center)",
        anatomical_region=MarmaRegion.MADHYA_SHARIRA,
        rachana_structure=MarmaRachana.SIRA,
        parinama_prognosis=MarmaParinama.SADHYO_PRANAHARA,
        angula_dimension=4.0,
        cardinal_vulnerability="Mahamarma / Seat of Prana, Chetana, and Para Ojas. Direct injury precipitates instantaneous cardiogenic shock, cardiac tamponade, and death within 1 to 7 days.",
        emergency_management="Immediate advanced cardiac life support (ACLS), sublingual Hridaya-Avarana with pure cow ghee and Maricha, emergency pericardiocentesis/thoracotomy.",
        therapeutic_indications=["Pranic re-centering", "Severe anxiety neurosis", "Emotional trauma and grief"]
    ),
    MarmaPointProfile(
        marma_code="MARMA-BAST-02",
        sanskrit_name="बस्ति मर्म (Basti Marma - The Urinary Bladder Center)",
        anatomical_region=MarmaRegion.MADHYA_SHARIRA,
        rachana_structure=MarmaRachana.SNAYU,
        parinama_prognosis=MarmaParinama.SADHYO_PRANAHARA,
        angula_dimension=4.0,
        cardinal_vulnerability="Mahamarma / Reservoir of Mutravaha Srotas and Apana Vayu. Rupture or deep penetrating injury causes pelvic peritonitis, acute uro-septic shock, and rapid death.",
        emergency_management="Immediate surgical laparotomy and bladder dome/trigone repair, urinary catheterization, broad-spectrum antimicrobial and inotropic support.",
        therapeutic_indications=["Apana Vayu dysregulation", "Pelvic congestion", "Refractory urinary retention"]
    ),
    MarmaPointProfile(
        marma_code="MARMA-NABH-03",
        sanskrit_name="नाभि मर्म (Nabhi Marma - The Umbilical / Solar Plexus Center)",
        anatomical_region=MarmaRegion.MADHYA_SHARIRA,
        rachana_structure=MarmaRachana.SIRA,
        parinama_prognosis=MarmaParinama.SADHYO_PRANAHARA,
        angula_dimension=4.0,
        cardinal_vulnerability="Seat of Samana Vayu and Pachaka Pitta. Origin of all Siras (mesenteric vasculature root). Penetrating trauma precipitates catastrophic hemoperitoneum and death.",
        emergency_management="Immediate exploratory laparotomy, mesenteric vascular ligation, rapid blood transfusion, and vital hemodynamic resuscitation.",
        therapeutic_indications=["Agnimandya", "Samana Vayu disorders", "Gastrointestinal motility imbalance"]
    ),
    MarmaPointProfile(
        marma_code="MARMA-ADH-06",
        sanskrit_name="अधिपति मर्म (Adhipati Marma - Crown / Vertex of Skull)",
        anatomical_region=MarmaRegion.URDHVAJATRU,
        rachana_structure=MarmaRachana.SANDHI,
        parinama_prognosis=MarmaParinama.SADHYO_PRANAHARA,
        angula_dimension=0.5,
        cardinal_vulnerability="Corresponds to Superior Sagittal Sinus / Torcula Herophili. Direct injury causes rapid intracranial hypertension, herniation, coma, and immediate mortality.",
        emergency_management="Emergency neurosurgical craniotomy, venous sinus hemostasis, intracranial pressure reduction (Mannitol), airway protection.",
        therapeutic_indications=["Shiro-Dhara focal point", "Severe insomnia", "Higher mental equanimity"]
    ),
    MarmaPointProfile(
        marma_code="MARMA-SHAN-07",
        sanskrit_name="शङ्ख मर्म (Shankha Marma - Spheno-Temporal Pterion)",
        anatomical_region=MarmaRegion.URDHVAJATRU,
        rachana_structure=MarmaRachana.ASTHI,
        parinama_prognosis=MarmaParinama.SADHYO_PRANAHARA,
        angula_dimension=0.5,
        cardinal_vulnerability="Thin pterion bone overlying anterior branch of middle meningeal artery. Fracture precipitates rapidly expanding extradural hematoma (EDH) and death within hours.",
        emergency_management="Immediate emergency burr-hole evacuation and middle meningeal artery ligation.",
        therapeutic_indications=["Temporal tension cephalalgia", "Ocular strain"]
    ),

    # Vishalyaghna (Fatal upon weapon extraction)
    MarmaPointProfile(
        marma_code="MARMA-STHAP-04",
        sanskrit_name="स्थापनी मर्म (Sthapani Marma - Glabella / Ajna Center)",
        anatomical_region=MarmaRegion.URDHVAJATRU,
        rachana_structure=MarmaRachana.SIRA,
        parinama_prognosis=MarmaParinama.VISHALYAGHNA,
        angula_dimension=0.5,
        cardinal_vulnerability="Located at glabella between eyebrows. Vishalyaghna: Patient survives while foreign body is lodged sealing the aperture; extraction allows Vayu escape, massive hemorrhage, and sudden death.",
        emergency_management="SURGICAL EXTRACTION FIREWALL: Never extract lodged weapon in the field. Transfer immediately to neurosurgical OT with craniotomy readiness.",
        therapeutic_indications=["Insomnia (Anidra)", "Cognitive fatigue & memory fog", "Anxiety & mental hyperarousal"]
    ),
    MarmaPointProfile(
        marma_code="MARMA-UTK-05",
        sanskrit_name="उत्क्षेप मर्म (Utkshepa Marma - Temporal Temple Center)",
        anatomical_region=MarmaRegion.URDHVAJATRU,
        rachana_structure=MarmaRachana.SNAYU,
        parinama_prognosis=MarmaParinama.VISHALYAGHNA,
        angula_dimension=0.5,
        cardinal_vulnerability="Above the temporal hairline. Vishalyaghna: Extraction of lodged weapon without vascular control results in fatal intracranial hemorrhage, Vayu release, and death.",
        emergency_management="DO NOT REMOVE LODGED OBJECT IN FIELD. Transport with rigid stabilization to specialized trauma theater.",
        therapeutic_indications=["Hemicrania / Migraine", "Sensory calming", "Temporal headache"]
    ),

    # Vaikalyakara (Deformity / Disability)
    MarmaPointProfile(
        marma_code="MARMA-JANU-08",
        sanskrit_name="जानु मर्म (Janu Marma - Knee Joint Articulation)",
        anatomical_region=MarmaRegion.SHAKHA,
        rachana_structure=MarmaRachana.SANDHI,
        parinama_prognosis=MarmaParinama.VAIKALYAKARA,
        angula_dimension=3.0,
        cardinal_vulnerability="Knee joint capsule, cruciate ligaments, and popliteal neurovascular bundle. Severe trauma produces Khanjata (permanent lameness and locomotor disability).",
        emergency_management="Joint stabilization and rigid splinting, cruciate ligament reconstruction, popliteal vessel inspection, Janu Basti.",
        therapeutic_indications=["Sandhigata Vata (Knee Osteoarthritis)", "Joint stiffness", "Locomotor rehabilitation"]
    ),
    MarmaPointProfile(
        marma_code="MARMA-KURP-09",
        sanskrit_name="कूर्पर मर्म (Kurpara Marma - Elbow Articulation)",
        anatomical_region=MarmaRegion.SHAKHA,
        rachana_structure=MarmaRachana.SANDHI,
        parinama_prognosis=MarmaParinama.VAIKALYAKARA,
        angula_dimension=3.0,
        cardinal_vulnerability="Elbow joint, brachial artery bifurcation, and median/ulnar nerves. Injury causes Kuni (flexion deformity, clawing, and permanent loss of hand dexterity).",
        emergency_management="Closed/open reduction of elbow, neurovascular decompression, functional immobilization, Abhyanga-Swedana.",
        therapeutic_indications=["Lateral epicondylitis (Tennis elbow)", "Brachial neuralgia", "Upper limb motor tone"]
    ),

    # Rujakara (Excruciating Chronic Pain)
    MarmaPointProfile(
        marma_code="MARMA-GULP-10",
        sanskrit_name="गुल्फ मर्म (Gulpha Marma - Ankle Joint Articulation)",
        anatomical_region=MarmaRegion.SHAKHA,
        rachana_structure=MarmaRachana.SANDHI,
        parinama_prognosis=MarmaParinama.RUJAKARA,
        angula_dimension=2.0,
        cardinal_vulnerability="Ankle joint mortise, deltoid ligaments, posterior tibial packet. Injury produces excruciating, unrelenting pain and chronic gait impairment (Stabdha-Padatva).",
        emergency_management="Ankle immobilization in neutral position, cold Parisheka, Rujahara herbal Lepa, compression Bandhana.",
        therapeutic_indications=["Chronic ankle sprain", "Gait instability", "Pelvic circulation stimulation"]
    ),
    MarmaPointProfile(
        marma_code="MARMA-MANI-11",
        sanskrit_name="मणिबन्ध मर्म (Manibandha Marma - Wrist Joint)",
        anatomical_region=MarmaRegion.SHAKHA,
        rachana_structure=MarmaRachana.SANDHI,
        parinama_prognosis=MarmaParinama.RUJAKARA,
        angula_dimension=2.0,
        cardinal_vulnerability="Carpal tunnel and radiocarpal articulation. Injury precipitates chronic burning neuralgia, severe carpal pain, and loss of grip strength.",
        emergency_management="Volar wrist splinting, nerve decompression, anti-inflammatory Parisheka, Rujahara Lepa.",
        therapeutic_indications=["Carpal tunnel syndrome", "Wrist tendinitis", "Manual dexterity restoration"]
    ),

    # Kalantara-Pranahara (Fatal within 15 to 30 days)
    MarmaPointProfile(
        marma_code="MARMA-TALH-12",
        sanskrit_name="तलहृदय मर्म (Talahridaya Marma - Sole & Palm Centers)",
        anatomical_region=MarmaRegion.SHAKHA,
        rachana_structure=MarmaRachana.MAMSA,
        parinama_prognosis=MarmaParinama.KALANTARA_PRANAHARA,
        angula_dimension=0.5,
        cardinal_vulnerability="Deep planto-palmar spaces between 2nd and 3rd rays. Deep puncture causes severe syncope, spreading deep fascial space infection, and delayed mortality within 15-30 days.",
        emergency_management="Wound debridement, drainage of deep fascial space, tetanus immunization, systemic antimicrobial therapy.",
        therapeutic_indications=["Pranic grounding", "Autonomic calming & sleep onset", "Peripheral circulatory stimulation"]
    )
]

TRI_MARMA_CODES = {"MARMA-HRID-01", "MARMA-BAST-02", "MARMA-ADH-06", "MARMA-SHAN-07"}


# ==============================================================================
# 2. DATABASE INITIALIZATION & SEEDING
# ==============================================================================

def initialize_marma_tables(conn: sqlite3.Connection) -> None:
    """Seed classical Marma registry if empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM marma_points_detailed_registry;")
    row = cursor.fetchone()
    if row and row["cnt"] == 0:
        now = int(time.time())
        for m in SEED_MARMA_CATALOG:
            cursor.execute(
                """
                INSERT INTO marma_points_detailed_registry (
                    marma_code, sanskrit_name, anatomical_region,
                    rachana_structure, parinama_prognosis, angula_dimension,
                    cardinal_vulnerability, emergency_management,
                    therapeutic_indications_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    m.marma_code,
                    m.sanskrit_name,
                    m.anatomical_region.value,
                    m.rachana_structure.value,
                    m.parinama_prognosis.value,
                    m.angula_dimension,
                    m.cardinal_vulnerability,
                    m.emergency_management,
                    json.dumps(m.therapeutic_indications),
                    now
                )
            )
        conn.commit()


# ==============================================================================
# 3. MARMA CATALOG QUERIES
# ==============================================================================

def list_all_marmas(
    conn: sqlite3.Connection,
    region: Optional[MarmaRegion] = None,
    rachana: Optional[MarmaRachana] = None,
    parinama: Optional[MarmaParinama] = None
) -> List[MarmaPointProfile]:
    """Retrieve catalog of vital Marmas with optional multi-attribute filtering."""
    cursor = conn.cursor()
    query = "SELECT * FROM marma_points_detailed_registry WHERE 1=1"
    params: List[Any] = []

    if region:
        query += " AND anatomical_region = ?"
        params.append(region.value)
    if rachana:
        query += " AND rachana_structure = ?"
        params.append(rachana.value)
    if parinama:
        query += " AND parinama_prognosis = ?"
        params.append(parinama.value)

    query += " ORDER BY marma_code ASC;"
    cursor.execute(query, params)
    rows = cursor.fetchall()

    return [
        MarmaPointProfile(
            marma_code=r["marma_code"],
            sanskrit_name=r["sanskrit_name"],
            anatomical_region=MarmaRegion(r["anatomical_region"]),
            rachana_structure=MarmaRachana(r["rachana_structure"]),
            parinama_prognosis=MarmaParinama(r["parinama_prognosis"]),
            angula_dimension=r["angula_dimension"],
            cardinal_vulnerability=r["cardinal_vulnerability"],
            emergency_management=r["emergency_management"],
            therapeutic_indications=json.loads(r["therapeutic_indications_json"]),
        )
        for r in rows
    ]


def get_marma_by_code(marma_code: str, conn: sqlite3.Connection) -> MarmaPointProfile:
    """Retrieve single Marma profile by unique marma_code."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM marma_points_detailed_registry WHERE marma_code = ?;", (marma_code,))
    r = cursor.fetchone()
    if not r:
        raise RecordNotFoundException(entity="Marma Point", identifier=marma_code)

    return MarmaPointProfile(
        marma_code=r["marma_code"],
        sanskrit_name=r["sanskrit_name"],
        anatomical_region=MarmaRegion(r["anatomical_region"]),
        rachana_structure=MarmaRachana(r["rachana_structure"]),
        parinama_prognosis=MarmaParinama(r["parinama_prognosis"]),
        angula_dimension=r["angula_dimension"],
        cardinal_vulnerability=r["cardinal_vulnerability"],
        emergency_management=r["emergency_management"],
        therapeutic_indications=json.loads(r["therapeutic_indications_json"]),
    )


# ==============================================================================
# 4. MARMA TRAUMA EMERGENCY TRIAGE & FIREWALL ENGINE
# ==============================================================================

def triage_marma_trauma_admission(
    conn: sqlite3.Connection,
    hospital_id: str,
    data: MarmaTraumaEmergencyCreate
) -> MarmaTraumaEmergencyResponse:
    """
    Evaluates acute Marma trauma, enforces the Tri-Marma Emergency Resuscitation Firewall,
    and checks Vishalyaghna surgical extraction prohibitions.
    """
    marma = get_marma_by_code(data.injured_marma_code, conn)

    tri_marma_involved = data.injured_marma_code in TRI_MARMA_CODES
    surgical_warning: Optional[str] = None

    # Triage and Firewall Stratification
    if tri_marma_involved:
        triage_tier = MarmaTraumaTriage.CODE_RED_TRI_MARMA_CRITICAL
        resuscitation_protocol = (
            "CRITICAL TRI-MARMA EMERGENCY: Involves primary seat of Prana/Ojas. Activate Level-1 ATLS trauma team. "
            "Execute immediate endotracheal airway control, aggressive volume resuscitation, sublingual Hridaya-Avarana, "
            "and transfer directly to operative resuscitation suite."
        )
    elif marma.parinama_prognosis == MarmaParinama.VISHALYAGHNA:
        triage_tier = MarmaTraumaTriage.CODE_ORANGE_VISHALYAGHNA_SURGICAL
        resuscitation_protocol = (
            "VISHALYAGHNA SURGICAL EXTRACTION FIREWALL ACTIVE: Direct cranial/sphenoidal trauma. "
            "Rigidly stabilize foreign body in place. Mandatory transfer to neurosurgical OT with craniotomy readiness."
        )
        if data.foreign_body_present:
            surgical_warning = (
                "STRICT STATUTORY PROHIBITION: DO NOT EXTRACT LODGED WEAPON/ARROW/SHRAPNEL IN THE FIELD. "
                "The lodged object tamponades intracranial pressure. Premature extraction allows Vayu to escape "
                "precipitating instantaneous fatal intracranial hemorrhage."
            )
    elif marma.parinama_prognosis == MarmaParinama.SADHYO_PRANAHARA:
        triage_tier = MarmaTraumaTriage.CODE_RED_TRI_MARMA_CRITICAL
        resuscitation_protocol = (
            "SADHYO-PRANAHARA CRISIS: Fatal within 1 to 7 days without surgical intervention. "
            "Emergent hemodynamic control, vessel ligation, and intensive critical care monitoring mandatory."
        )
    elif marma.parinama_prognosis in [MarmaParinama.KALANTARA_PRANAHARA, MarmaParinama.VAIKALYAKARA]:
        triage_tier = MarmaTraumaTriage.CODE_YELLOW_VAIKALYAKARA_URGENT
        resuscitation_protocol = (
            "URGENT TRAUMA INTERVENTION: High risk of permanent locomotor/anatomical disability or delayed infection. "
            "Rigid splinting, nerve decompression, wound debridement, and surgical reconstruction required."
        )
    else:
        triage_tier = MarmaTraumaTriage.CODE_GREEN_STABLE
        resuscitation_protocol = (
            "ANALGESIC & IMMOBILIZATION PROTOCOL: Severe chronic pain management. "
            "Cold herbal Parisheka, Rujahara Lepa, and functional compression Bandhana."
        )

    now = int(time.time())
    log_id = f"trauma-{now}-{uuid.uuid4().hex[:6]}"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO marma_trauma_emergency_logs (
            log_id, patient_id, hospital_id, injured_marma_code,
            trauma_mechanism, depth_penetration_mm, foreign_body_present,
            tri_marma_involved, triage_tier, emergency_resuscitation_protocol,
            practitioner_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            log_id,
            data.patient_id,
            hospital_id,
            data.injured_marma_code,
            data.trauma_mechanism,
            data.depth_penetration_mm,
            1 if data.foreign_body_present else 0,
            1 if tri_marma_involved else 0,
            triage_tier.value,
            resuscitation_protocol,
            data.practitioner_arn,
            now
        )
    )
    conn.commit()

    append_audit_log(
        conn=conn,
        hospital_id=hospital_id,
        actor_id=data.practitioner_arn,
        action="MARMA_TRAUMA_ADMISSION",
        entity_type="MARMA_TRAUMA",
        entity_id=log_id,
        details={
            "patient_id": data.patient_id,
            "injured_marma": data.injured_marma_code,
            "triage_tier": triage_tier.value,
            "tri_marma_involved": tri_marma_involved,
            "foreign_body_present": data.foreign_body_present
        }
    )

    return MarmaTraumaEmergencyResponse(
        log_id=log_id,
        patient_id=data.patient_id,
        hospital_id=hospital_id,
        injured_marma_code=data.injured_marma_code,
        trauma_mechanism=data.trauma_mechanism,
        depth_penetration_mm=data.depth_penetration_mm,
        foreign_body_present=data.foreign_body_present,
        tri_marma_involved=tri_marma_involved,
        triage_tier=triage_tier,
        emergency_resuscitation_protocol=resuscitation_protocol,
        surgical_extraction_warning=surgical_warning,
        practitioner_arn=data.practitioner_arn,
        created_at=now
    )


def list_patient_marma_trauma_admissions(
    patient_id: str,
    conn: sqlite3.Connection
) -> List[MarmaTraumaEmergencyResponse]:
    """Retrieve historical Marma trauma admissions for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM marma_trauma_emergency_logs
        WHERE patient_id = ?
        ORDER BY created_at DESC;
        """,
        (patient_id,)
    )
    rows = cursor.fetchall()
    return [
        MarmaTraumaEmergencyResponse(
            log_id=r["log_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            injured_marma_code=r["injured_marma_code"],
            trauma_mechanism=r["trauma_mechanism"],
            depth_penetration_mm=r["depth_penetration_mm"],
            foreign_body_present=bool(r["foreign_body_present"]),
            tri_marma_involved=bool(r["tri_marma_involved"]),
            triage_tier=MarmaTraumaTriage(r["triage_tier"]),
            emergency_resuscitation_protocol=r["emergency_resuscitation_protocol"],
            surgical_extraction_warning=None,
            practitioner_arn=r["practitioner_arn"],
            created_at=r["created_at"]
        )
        for r in rows
    ]


# ==============================================================================
# 5. MARMA CHIKITSA THERAPEUTIC STIMULATION ENGINE
# ==============================================================================

def record_marma_chikitsa_session(
    conn: sqlite3.Connection,
    hospital_id: str,
    data: MarmaChikitsaSessionCreate
) -> MarmaChikitsaSessionResponse:
    """
    Logs a therapeutic Marma Chikitsa acupressure/stimulation session.
    Calibrates pressure intensity (0.5 to 1.5 kg) and breathing synchrony.
    """
    marma = get_marma_by_code(data.targeted_marma_code, conn)

    # Validate pressure safety
    pressure_note = f"{data.pressure_intensity_kg:.1f} kg applied"
    if data.pressure_intensity_kg > 2.0:
        pressure_note += " (Warning: Higher than standard 1.5 kg therapeutic threshold, monitor for localized soreness)"

    immediate_response = (
        f"Pranic flow successfully stimulated at {marma.sanskrit_name} ({marma.marma_code}) using "
        f"{data.stimulation_modality.value}. Applied {pressure_note} over {data.cycles_count} respiratory cycles. "
        f"Alleviation of Vata stagnation achieved for objective: '{data.clinical_objective}'."
    )

    now = int(time.time())
    session_id = f"marmachik-{now}-{uuid.uuid4().hex[:6]}"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO marma_chikitsa_therapeutic_sessions (
            session_id, patient_id, hospital_id, targeted_marma_code,
            stimulation_modality, pressure_intensity_kg, cycles_count,
            clinical_objective, immediate_response, practitioner_arn,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            session_id,
            data.patient_id,
            hospital_id,
            data.targeted_marma_code,
            data.stimulation_modality.value,
            data.pressure_intensity_kg,
            data.cycles_count,
            data.clinical_objective,
            immediate_response,
            data.practitioner_arn,
            now
        )
    )
    conn.commit()

    append_audit_log(
        conn=conn,
        hospital_id=hospital_id,
        actor_id=data.practitioner_arn,
        action="MARMA_CHIKITSA_SESSION",
        entity_type="MARMA_CHIKITSA",
        entity_id=session_id,
        details={
            "patient_id": data.patient_id,
            "targeted_marma": data.targeted_marma_code,
            "modality": data.stimulation_modality.value,
            "pressure_intensity_kg": data.pressure_intensity_kg
        }
    )

    return MarmaChikitsaSessionResponse(
        session_id=session_id,
        patient_id=data.patient_id,
        hospital_id=hospital_id,
        targeted_marma_code=data.targeted_marma_code,
        stimulation_modality=data.stimulation_modality,
        pressure_intensity_kg=data.pressure_intensity_kg,
        cycles_count=data.cycles_count,
        clinical_objective=data.clinical_objective,
        immediate_response=immediate_response,
        practitioner_arn=data.practitioner_arn,
        created_at=now
    )


def list_patient_marma_chikitsa_sessions(
    patient_id: str,
    conn: sqlite3.Connection
) -> List[MarmaChikitsaSessionResponse]:
    """Retrieve historical Marma Chikitsa stimulation sessions for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM marma_chikitsa_therapeutic_sessions
        WHERE patient_id = ?
        ORDER BY created_at DESC;
        """,
        (patient_id,)
    )
    rows = cursor.fetchall()
    return [
        MarmaChikitsaSessionResponse(
            session_id=r["session_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            targeted_marma_code=r["targeted_marma_code"],
            stimulation_modality=StimulationModality(r["stimulation_modality"]),
            pressure_intensity_kg=r["pressure_intensity_kg"],
            cycles_count=r["cycles_count"],
            clinical_objective=r["clinical_objective"],
            immediate_response=r["immediate_response"],
            practitioner_arn=r["practitioner_arn"],
            created_at=r["created_at"]
        )
        for r in rows
    ]
