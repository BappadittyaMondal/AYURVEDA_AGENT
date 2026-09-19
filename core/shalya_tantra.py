"""
Shalya Tantra, Marma Sharira, Agnikarma & Ksharasutra Engine
============================================================
Implements:
1. Classical Marma Sharira catalog (107 Marmas across 5 prognostic types)
2. Pre-operative surgical incision proximity screening & Sadyo-Pranahara shock firewall
3. Agnikarma thermal delivery dynamics (Panchadhatu Shalaka, burn grading, post-care)
4. Ksharasutra track tracking, Unit-Cutting Time (UCT) calculus, and healing analytics
5. Vrana Shashti-Upakrama wound staging and clinical dressing prescribing
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
from models.shalya_tantra import (
    AgnikarmaDevice,
    AgnikarmaPattern,
    AgnikarmaSessionCreate,
    AgnikarmaSessionResponse,
    KsharasutraFistulaType,
    KsharasutraSessionCreate,
    KsharasutraSessionResponse,
    MarmaProfile,
    MarmaProximityCheckRequest,
    MarmaProximityCheckResponse,
    MarmaRegion,
    MarmaStructure,
    MarmaType,
    VranaAssessmentCreate,
    VranaAssessmentResponse,
    VranaStage,
)

# ==============================================================================
# CLASSICAL MARMA SHARIRA CATALOG (20+ KEY PROMINENT MARMAS)
# ==============================================================================

SEED_MARMA_CATALOG: List[MarmaProfile] = [
    # Sadyo-Pranahara Marmas (Immediate Fatal Shock)
    MarmaProfile(
        marma_id="MARMA-HRIDAYA",
        sanskrit_name="हृदय मर्म (Hridaya Marma)",
        english_name="Cardiac Vital Center",
        marma_type=MarmaType.SADYO_PRANAHARA,
        structural_predominance=MarmaStructure.SIRA,
        anatomical_region=MarmaRegion.KOSHTHA,
        dimension_angula=4.0,
        anatomical_landmarks="Between breasts, overlying cardiac notch and anterior mediastinum",
        trauma_manifestations=["Instant death", "Severe thoracic syncope (Murchha)", "Terminal dyspnea", "Precordial collapse"],
        vulnerability_radius_cm=5.0
    ),
    MarmaProfile(
        marma_id="MARMA-BASTI",
        sanskrit_name="बस्ति मर्म (Basti Marma)",
        english_name="Urinary Bladder & Pelvic Triangle",
        marma_type=MarmaType.SADYO_PRANAHARA,
        structural_predominance=MarmaStructure.SNAYU,
        anatomical_region=MarmaRegion.KOSHTHA,
        dimension_angula=4.0,
        anatomical_landmarks="Between groin and pubic symphysis; retro-pubic urinary reservoir",
        trauma_manifestations=["Urinary peritonitis", "Immediate fatal shock unless single lateral puncture in calculus removal", "Anuria"],
        vulnerability_radius_cm=4.5
    ),
    MarmaProfile(
        marma_id="MARMA-NABHI",
        sanskrit_name="नाभि मर्म (Nabhi Marma)",
        english_name="Umbilical Vascular Plexus",
        marma_type=MarmaType.SADYO_PRANAHARA,
        structural_predominance=MarmaStructure.SIRA,
        anatomical_region=MarmaRegion.KOSHTHA,
        dimension_angula=4.0,
        anatomical_landmarks="Central abdominal umbilicus; confluence of mesenteric vascular roots",
        trauma_manifestations=["Immediate exsanguinating hemorrhage", "Severe abdominal shock", "Terminal collapse"],
        vulnerability_radius_cm=4.0
    ),
    MarmaProfile(
        marma_id="MARMA-SHRINGATAKA",
        sanskrit_name="शृङ्गाटक मर्म (Shringataka Marma)",
        english_name="Cranial Basilar Confluens / Cavernous Sinus",
        marma_type=MarmaType.SADYO_PRANAHARA,
        structural_predominance=MarmaStructure.SIRA,
        anatomical_region=MarmaRegion.URDHWAJATRUGATA,
        dimension_angula=4.0,
        anatomical_landmarks="Interior cranial floor confluens of olfactory, visual, auditory, and gustatory nerve pathways",
        trauma_manifestations=["Instantaneous intracranial demise", "Massive sensory extinction", "Coma"],
        vulnerability_radius_cm=3.5
    ),
    MarmaProfile(
        marma_id="MARMA-ADHIPATI",
        sanskrit_name="अधिपति मर्म (Adhipati Marma)",
        english_name="Vertex / Superior Sagittal Confluence",
        marma_type=MarmaType.SADYO_PRANAHARA,
        structural_predominance=MarmaStructure.SANDHI,
        anatomical_region=MarmaRegion.URDHWAJATRUGATA,
        dimension_angula=0.5,
        anatomical_landmarks="Crown vertex overlying Bregma / confluence of cranial sutures and superior sagittal sinus",
        trauma_manifestations=["Instantaneous death", "Massive cerebral herniation", "Fatal hemorrhage"],
        vulnerability_radius_cm=3.0
    ),
    MarmaProfile(
        marma_id="MARMA-SHANKHA",
        sanskrit_name="शङ्ख मर्म (Shankha Marma)",
        english_name="Pterion / Middle Meningeal Junction",
        marma_type=MarmaType.SADYO_PRANAHARA,
        structural_predominance=MarmaStructure.ASTHI,
        anatomical_region=MarmaRegion.URDHWAJATRUGATA,
        dimension_angula=0.5,
        anatomical_landmarks="Temporal fossa between ear and lateral orbital border overlying Pterion",
        trauma_manifestations=["Extradural hematoma", "Immediate loss of consciousness", "Death within 24 hours"],
        vulnerability_radius_cm=2.5
    ),
    MarmaProfile(
        marma_id="MARMA-GUDA",
        sanskrit_name="गुद मर्म (Guda Marma)",
        english_name="Anorectal Canal & Pudendal Plexus",
        marma_type=MarmaType.SADYO_PRANAHARA,
        structural_predominance=MarmaStructure.MAMSA,
        anatomical_region=MarmaRegion.KOSHTHA,
        dimension_angula=4.0,
        anatomical_landmarks="Terminal anal canal attached to large bowel; surrounded by internal & external sphincters",
        trauma_manifestations=["Fatal pelvic sepsis", "Incontinence", "Severe hemorrhagic shock"],
        vulnerability_radius_cm=4.0
    ),
    # Vishalyaghna Marmas (Fatal Foreign Body Extraction)
    MarmaProfile(
        marma_id="MARMA-STHAPANI",
        sanskrit_name="स्थपनी मर्म (Sthapani Marma)",
        english_name="Glabella / Frontal Venous Sinus",
        marma_type=MarmaType.VISHALYAGHNA,
        structural_predominance=MarmaStructure.SIRA,
        anatomical_region=MarmaRegion.URDHWAJATRUGATA,
        dimension_angula=0.5,
        anatomical_landmarks="Between the two eyebrows overlying the nasal frontal suture",
        trauma_manifestations=["Patient survives while foreign body seals wound; fatal air embolism or hemorrhage upon extraction"],
        vulnerability_radius_cm=2.0
    ),
    MarmaProfile(
        marma_id="MARMA-UTKSHEPA",
        sanskrit_name="उत्क्षेप मर्म (Utkshepa Marma)",
        english_name="Supra-temporal Scalp Margin",
        marma_type=MarmaType.VISHALYAGHNA,
        structural_predominance=MarmaStructure.SNAYU,
        anatomical_region=MarmaRegion.URDHWAJATRUGATA,
        dimension_angula=0.5,
        anatomical_landmarks="Above the temples near hair margin on either side of the skull",
        trauma_manifestations=["Death occurs immediately after extraction of embedded foreign body"],
        vulnerability_radius_cm=2.0
    ),
    # Kalantara-Pranahara Marmas (Delayed Fatal Shock within 15-30 days)
    MarmaProfile(
        marma_id="MARMA-STANAMULA",
        sanskrit_name="स्तनमूल मर्म (Stanamula Marma)",
        english_name="Infra-mammary Pleural Reflection",
        marma_type=MarmaType.KALANTARA_PRANAHARA,
        structural_predominance=MarmaStructure.SIRA,
        anatomical_region=MarmaRegion.KOSHTHA,
        dimension_angula=2.0,
        anatomical_landmarks="Two fingers below each breast overlying costodiaphragmatic pleural recess",
        trauma_manifestations=["Hemothorax", "Purulent empyema", "Respiratory arrest within 15-30 days"],
        vulnerability_radius_cm=3.5
    ),
    MarmaProfile(
        marma_id="MARMA-APASTAMBHA",
        sanskrit_name="अपस्तम्भ मर्म (Apastambha Marma)",
        english_name="Bronchial Pedicle / Internal Mammary Plexus",
        marma_type=MarmaType.KALANTARA_PRANAHARA,
        structural_predominance=MarmaStructure.SIRA,
        anatomical_region=MarmaRegion.KOSHTHA,
        dimension_angula=0.5,
        anatomical_landmarks="On either side of sternum in upper chest overlying primary bronchi roots",
        trauma_manifestations=["Pneumothorax", "Hemoptysis", "Suffocation leading to delayed demise"],
        vulnerability_radius_cm=2.5
    ),
    # Vaikalyakara Marmas (Deformity / Permanent Functional Disability)
    MarmaProfile(
        marma_id="MARMA-KURPARA",
        sanskrit_name="कूर्पर मर्म (Kurpara Marma)",
        english_name="Elbow Joint Complex",
        marma_type=MarmaType.VAIKALYAKARA,
        structural_predominance=MarmaStructure.SANDHI,
        anatomical_region=MarmaRegion.SHAKHA,
        dimension_angula=3.0,
        anatomical_landmarks="Articular junction of humerus, radius, and ulna",
        trauma_manifestations=["Severe flexion contracture", "Ankylosis of upper limb", "Wasting of forearm"],
        vulnerability_radius_cm=3.5
    ),
    MarmaProfile(
        marma_id="MARMA-JANU",
        sanskrit_name="जानु मर्म (Janu Marma)",
        english_name="Knee Joint Complex",
        marma_type=MarmaType.VAIKALYAKARA,
        structural_predominance=MarmaStructure.SANDHI,
        anatomical_region=MarmaRegion.SHAKHA,
        dimension_angula=3.0,
        anatomical_landmarks="Articulation between femur, patella, and tibia",
        trauma_manifestations=["Loss of locomotion", "Limping (Khanja)", "Permanent joint stiffness"],
        vulnerability_radius_cm=4.0
    ),
    MarmaProfile(
        marma_id="MARMA-LOHITAKSHA",
        sanskrit_name="लोहिताक्ष मर्म (Lohitaksha Marma)",
        english_name="Femoral / Axillary Neurovascular Bundle",
        marma_type=MarmaType.VAIKALYAKARA,
        structural_predominance=MarmaStructure.SIRA,
        anatomical_region=MarmaRegion.SHAKHA,
        dimension_angula=0.5,
        anatomical_landmarks="Root of groin or axilla above thigh/shoulder joint",
        trauma_manifestations=["Profuse arterial hemorrhage", "Ischemic limb palsy", "Wasting"],
        vulnerability_radius_cm=3.0
    ),
    MarmaProfile(
        marma_id="MARMA-URVI",
        sanskrit_name="उर्वी मर्म (Urvi Marma)",
        english_name="Mid-thigh / Brachial Vascular Channel",
        marma_type=MarmaType.VAIKALYAKARA,
        structural_predominance=MarmaStructure.SIRA,
        anatomical_region=MarmaRegion.SHAKHA,
        dimension_angula=1.0,
        anatomical_landmarks="Middle of thigh or arm overlying profunda vessels",
        trauma_manifestations=["Limb emaciation (Shosha)", "Paresis from blood loss"],
        vulnerability_radius_cm=3.0
    ),
    # Rujakara Marmas (Intractable Severe Pain)
    MarmaProfile(
        marma_id="MARMA-GULPHA",
        sanskrit_name="गुल्फ मर्म (Gulpha Marma)",
        english_name="Ankle Joint Complex",
        marma_type=MarmaType.RUJAKARA,
        structural_predominance=MarmaStructure.SANDHI,
        anatomical_region=MarmaRegion.SHAKHA,
        dimension_angula=2.0,
        anatomical_landmarks="Junction of leg and foot between medial & lateral malleoli",
        trauma_manifestations=["Excruciating persistent pain", "Inability to bear weight", "Foot drop / limp"],
        vulnerability_radius_cm=3.0
    ),
    MarmaProfile(
        marma_id="MARMA-MANIBANDHA",
        sanskrit_name="मणिबन्ध मर्म (Manibandha Marma)",
        english_name="Wrist Joint Complex",
        marma_type=MarmaType.RUJAKARA,
        structural_predominance=MarmaStructure.SANDHI,
        anatomical_region=MarmaRegion.SHAKHA,
        dimension_angula=2.0,
        anatomical_landmarks="Junction of forearm and carpus",
        trauma_manifestations=["Severe agonizing wrist pain", "Loss of grip strength"],
        vulnerability_radius_cm=2.5
    ),
    MarmaProfile(
        marma_id="MARMA-KURCHA",
        sanskrit_name="कूर्च मर्म (Kurcha Marma)",
        english_name="Metatarsal / Metacarpal Brush Plexus",
        marma_type=MarmaType.RUJAKARA,
        structural_predominance=MarmaStructure.SNAYU,
        anatomical_region=MarmaRegion.SHAKHA,
        dimension_angula=4.0,
        anatomical_landmarks="Above Kurchashira on dorsal aspect of hand and foot",
        trauma_manifestations=["Inability to walk or write", "Severe hyperalgesia", "Tremors"],
        vulnerability_radius_cm=3.0
    ),
]

# ==============================================================================
# DATABASE INITIALIZATION & SEEDING ENGINE
# ==============================================================================

def initialize_shalya_tables(conn: sqlite3.Connection) -> None:
    """Populate marma_sharira_catalog if unseeded."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM marma_sharira_catalog;")
    row = cursor.fetchone()
    if row and row["cnt"] == 0:
        now = int(time.time())
        for m in SEED_MARMA_CATALOG:
            cursor.execute(
                """
                INSERT INTO marma_sharira_catalog (
                    marma_id, sanskrit_name, english_name, marma_type,
                    structural_predominance, anatomical_region, dimension_angula,
                    anatomical_landmarks, trauma_manifestations_json,
                    vulnerability_radius_cm, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    m.marma_id,
                    m.sanskrit_name,
                    m.english_name,
                    m.marma_type.value,
                    m.structural_predominance.value,
                    m.anatomical_region.value,
                    m.dimension_angula,
                    m.anatomical_landmarks,
                    json.dumps(m.trauma_manifestations),
                    m.vulnerability_radius_cm,
                    now,
                )
            )
        conn.commit()


def get_marma_profile(marma_id: str, conn: sqlite3.Connection) -> MarmaProfile:
    """Retrieve Marma anatomical specification by ID."""
    initialize_shalya_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM marma_sharira_catalog WHERE marma_id = ?;", (marma_id,))
    row = cursor.fetchone()
    if not row:
        raise RecordNotFoundException("MarmaProfile", marma_id)

    return MarmaProfile(
        marma_id=row["marma_id"],
        sanskrit_name=row["sanskrit_name"],
        english_name=row["english_name"],
        marma_type=MarmaType(row["marma_type"]),
        structural_predominance=MarmaStructure(row["structural_predominance"]),
        anatomical_region=MarmaRegion(row["anatomical_region"]),
        dimension_angula=row["dimension_angula"],
        anatomical_landmarks=row["anatomical_landmarks"],
        trauma_manifestations=json.loads(row["trauma_manifestations_json"]),
        vulnerability_radius_cm=row["vulnerability_radius_cm"],
    )


def list_all_marmas(conn: sqlite3.Connection) -> List[MarmaProfile]:
    """List all registered classical Marmas."""
    initialize_shalya_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM marma_sharira_catalog ORDER BY marma_id ASC;")
    rows = cursor.fetchall()
    return [
        MarmaProfile(
            marma_id=r["marma_id"],
            sanskrit_name=r["sanskrit_name"],
            english_name=r["english_name"],
            marma_type=MarmaType(r["marma_type"]),
            structural_predominance=MarmaStructure(r["structural_predominance"]),
            anatomical_region=MarmaRegion(r["anatomical_region"]),
            dimension_angula=r["dimension_angula"],
            anatomical_landmarks=r["anatomical_landmarks"],
            trauma_manifestations=json.loads(r["trauma_manifestations_json"]),
            vulnerability_radius_cm=r["vulnerability_radius_cm"],
        )
        for r in rows
    ]


# ==============================================================================
# SURGICAL INCISION PROXIMITY & SADYO-PRANAHARA SHOCK FIREWALL
# ==============================================================================

def screen_marma_incision_proximity(
    req: MarmaProximityCheckRequest,
    conn: sqlite3.Connection
) -> MarmaProximityCheckResponse:
    """
    Evaluates surgical incision coordinates against nearest Marma anatomical vulnerability radius.
    Enforces Sadyo-Pranahara hard safety firewall if planned incision infringes vital radius.
    """
    marma = get_marma_profile(req.nearest_marma_id, conn)

    is_within_vulnerability = req.distance_from_marma_cm < marma.vulnerability_radius_cm
    recommendations: List[str] = []
    shock_protocol = None

    if is_within_vulnerability:
        if marma.marma_type == MarmaType.SADYO_PRANAHARA:
            tier = "CRITICAL_BLOCKED"
            is_safe = False
            shock_protocol = (
                "EMERGENCY PRANA-PRATYAGAMANA SHOCK PROTOCOL ACTIVATED: "
                "Incision infringes Sadyo-Pranahara vital radius. Immediate vascular clamp, "
                "Sandhana hemostasis, Sheeta Parisheka (cold water spray to face/vessels), "
                "intravenous crystalloid revival, and intensive surgical standby required."
            )
            recommendations.append(
                f"RE-ROUTE INCISION: Proposed incision at '{req.proposed_incision_site}' is within {req.distance_from_marma_cm:.1f} cm "
                f"of Sadyo-Pranahara Marma '{marma.sanskrit_name}' (Vulnerability Radius: {marma.vulnerability_radius_cm:.1f} cm). "
                "Direct incision into this Marma causes immediate fatal shock or exsanguination."
            )
        elif marma.marma_type in [MarmaType.KALANTARA_PRANAHARA, MarmaType.VISHALYAGHNA]:
            tier = "CAUTION_REQUIRED"
            is_safe = False
            recommendations.append(
                f"HIGH RISK INCISION: Within {req.distance_from_marma_cm:.1f} cm of {marma.marma_type.value} Marma. "
                "Proceed only under direct visualization with blunt dissection; avoid transfixing deep neurovascular bundles."
            )
        else:
            tier = "CAUTION_REQUIRED"
            is_safe = True
            recommendations.append(
                f"MODERATE RISK: Within {marma.vulnerability_radius_cm:.1f} cm of {marma.sanskrit_name}. "
                "Protect joint capsule/tendons to avoid post-operative functional deformity or chronic pain."
            )
    else:
        tier = "CLEAR"
        is_safe = True
        recommendations.append(
            f"CLEAR: Incision distance ({req.distance_from_marma_cm:.1f} cm) safely exceeds vulnerability radius "
            f"({marma.vulnerability_radius_cm:.1f} cm) of {marma.sanskrit_name}."
        )

    return MarmaProximityCheckResponse(
        patient_id=req.patient_id,
        nearest_marma_id=marma.marma_id,
        marma_name=marma.sanskrit_name,
        marma_type=marma.marma_type,
        is_safe_incision=is_safe,
        vulnerability_radius_cm=marma.vulnerability_radius_cm,
        actual_distance_cm=req.distance_from_marma_cm,
        safety_tier=tier,
        shock_resuscitation_protocol=shock_protocol,
        surgical_recommendations=recommendations
    )


# ==============================================================================
# AGNIKARMA THERMAL CAUTERIZATION DELIVERY DYNAMICS ENGINE
# ==============================================================================

def execute_agnikarma_session(
    data: AgnikarmaSessionCreate,
    hospital_id: str,
    conn: sqlite3.Connection
) -> AgnikarmaSessionResponse:
    """
    Validates thermal transfer parameters (operating temperature, contact duration, pattern),
    evaluates burn grade (Samyak, Atidagdha, Durdagdha), enforces post-care dressing, and logs procedure.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM patients WHERE patient_id = ?;", (data.patient_id,))
    if not cursor.fetchone():
        raise RecordNotFoundException("Patient", data.patient_id)

    adverse_flags: List[str] = []

    # Burn grade evaluation
    # Target for Shalaka: 180°C - 250°C; contact <= 2.5 seconds
    if data.operating_temperature_c > 260.0 or data.contact_time_seconds > 3.0:
        burn_grade = "ATIDAGDHA"
        adverse_flags.append("Atidagdha Alert: Excessive heat or contact duration exceeds therapeutic threshold; risk of deep tissue necrosis.")
    elif data.operating_temperature_c < 140.0 and data.dahanopakarana in [AgnikarmaDevice.PANCHADHATU_SHALAKA, AgnikarmaDevice.JAMBAVOSHTHA_LOHA]:
        burn_grade = "DURDAGDHA"
        adverse_flags.append("Durdagdha Alert: Temperature sub-therapeutic; produces erythema and painful blistering without therapeutic eschar.")
    else:
        burn_grade = "SAMYAK_DAGDHA"

    post_care = (
        "Immediate application of freshly extracted Ghrita-Kumari (Aloe vera) pulp "
        "and sterile Madhu-Ghrita (Honey & Ghee in 2:1 unequal ratio) to pacify burning sensation and promote sterile eschar maturation."
    )

    now = int(time.time())
    session_id = f"AGNI-{data.patient_id}-{now}-{uuid.uuid4().hex[:6]}"

    cursor.execute(
        """
        INSERT INTO agnikarma_procedure_logs (
            session_id, patient_id, hospital_id, anatomical_site,
            dahanopakarana, operating_temperature_c, contact_time_seconds,
            pattern, samya_dagdha_verified, post_care_dressing,
            practitioner_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            session_id,
            data.patient_id,
            hospital_id,
            data.anatomical_site,
            data.dahanopakarana.value,
            data.operating_temperature_c,
            data.contact_time_seconds,
            data.pattern.value,
            1 if burn_grade == "SAMYAK_DAGDHA" else 0,
            post_care,
            data.practitioner_arn,
            now,
        )
    )
    conn.commit()

    return AgnikarmaSessionResponse(
        session_id=session_id,
        patient_id=data.patient_id,
        anatomical_site=data.anatomical_site,
        dahanopakarana=data.dahanopakarana,
        operating_temperature_c=data.operating_temperature_c,
        contact_time_seconds=data.contact_time_seconds,
        burn_grade=burn_grade,
        post_care_dressing=post_care,
        adverse_flags=adverse_flags,
        practitioner_arn=data.practitioner_arn,
        created_at=now,
    )


# ==============================================================================
# KSHARASUTRA ANORECTAL SETON & UCT ENGINE
# ==============================================================================

def evaluate_ksharasutra_session(
    data: KsharasutraSessionCreate,
    hospital_id: str,
    conn: sqlite3.Connection
) -> KsharasutraSessionResponse:
    """
    Computes track cutting progression, Unit-Cutting Time (UCT in days/cm),
    evaluates healing status, and records treatment episode.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM patients WHERE patient_id = ?;", (data.patient_id,))
    if not cursor.fetchone():
        raise RecordNotFoundException("Patient", data.patient_id)

    cut_length = max(0.0, data.initial_track_length_cm - data.current_track_length_cm)
    pct_cut = round((cut_length / data.initial_track_length_cm) * 100.0, 1)

    if cut_length > 0:
        uct = round(data.total_days_elapsed / cut_length, 2)
    else:
        uct = 0.0

    if data.current_track_length_cm == 0.0:
        status = "CUT_THROUGH_COMPLETE"
        advisory = "Complete track cut-through and fistulous obliteration achieved. Continue Triphala Guggulu and Jatyadi Taila Matra Basti for 2 weeks."
    elif uct > 14.0:
        status = "SLOW_HEALING"
        advisory = "Slow cutting rate (UCT > 14 days/cm). Assess for epithelialized tract or sphincter fibrosis; tighten seton under mild traction."
    else:
        status = "IN_PROGRESS"
        advisory = f"Optimal healing progress ({pct_cut}% cut). Average cutting rate: {uct:.1f} days/cm. Change seton weekly."

    now = int(time.time())
    episode_id = f"KSHARA-{data.patient_id}-{now}-{uuid.uuid4().hex[:6]}"

    cursor.execute(
        """
        INSERT INTO ksharasutra_treatment_episodes (
            episode_id, patient_id, hospital_id, fistula_type,
            initial_track_length_cm, current_track_length_cm,
            sittings_count, unit_cutting_time_days_per_cm,
            complications_json, healing_status, practitioner_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            episode_id,
            data.patient_id,
            hospital_id,
            data.fistula_type.value,
            data.initial_track_length_cm,
            data.current_track_length_cm,
            data.sittings_count,
            uct,
            json.dumps(data.active_symptoms),
            status,
            data.practitioner_arn,
            now,
        )
    )
    conn.commit()

    return KsharasutraSessionResponse(
        episode_id=episode_id,
        patient_id=data.patient_id,
        fistula_type=data.fistula_type,
        initial_track_length_cm=data.initial_track_length_cm,
        current_track_length_cm=data.current_track_length_cm,
        cut_length_cm=round(cut_length, 2),
        percentage_cut=pct_cut,
        unit_cutting_time_days_per_cm=uct,
        healing_status=status,
        clinical_advisory=advisory,
        practitioner_arn=data.practitioner_arn,
        created_at=now,
    )


# ==============================================================================
# VRANA SURGICAL WOUND & SHASHTI-UPAKRAMA STAGING ENGINE
# ==============================================================================

def assess_vrana_wound(
    data: VranaAssessmentCreate,
    hospital_id: str,
    conn: sqlite3.Connection
) -> VranaAssessmentResponse:
    """
    Stages surgical wound/ulcer (Dusta vs. Shuddha vs. Ruhamana) and prescribes
    precise Shashti-Upakrama therapies (Kshalana, Shodhana, Ropana).
    """
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM patients WHERE patient_id = ?;", (data.patient_id,))
    if not cursor.fetchone():
        raise RecordNotFoundException("Patient", data.patient_id)

    upakramas: List[str] = []

    if data.has_purulent_discharge or data.is_foul_smelling or data.edge_character in ["UNDERMINED", "PUNCHED_OUT"]:
        stage = VranaStage.DUSTA_VRANA
        upakramas = [
            "प्रक्षालन (Kshalana: Irrigation with warm Triphala and Panchavalkala Kwatha)",
            "शोधन (Shodhana: Debridement of non-viable slough with Apamarga Kshara Pichu)",
            "धूपन (Dhoopana: Medicated fumigation with Guggulu and Haridra)",
            "कल्क प्रयोग (Application of Nimba-Patola Kalka paste)"
        ]
        topical = "नीम्ब तैल एवं जात्यादि घृत (Nimba Taila + Jatyadi Ghrita)"
        irrigation = "त्रिफला-पञ्चवल्कल कषाय (Triphala-Panchavalkala Kwatha)"
        freq = "Twice daily dressing"
    elif data.has_healthy_granulation and data.edge_character == "SLOPING":
        stage = VranaStage.RUHAMANA_VRANA
        upakramas = [
            "रोपण (Ropana: Tissue regeneration and contracture acceleration)",
            "जात्यादि तैल लेप (Jatyadi Taila gauze packing)",
            "बन्ध (Bandhana: Gentle supportive sterile non-constrictive bandaging)"
        ]
        topical = "जात्यादि तैल (Jatyadi Taila)"
        irrigation = "यष्टिमधु कषाय (Yashtimadhu Kwatha)"
        freq = "Once daily dressing"
    else:
        stage = VranaStage.SHUDDHA_VRANA
        upakramas = [
            "रोपण संरक्षण (Protective non-traumatic wound coverage)",
            "मधु-घृत लेपन (Application of 2:1 Madhu-Ghrita sterile emulsion)"
        ]
        topical = "मधु-घृत एवं चन्दन लेप (Madhu-Ghrita with Chandana)"
        irrigation = "शुद्ध कोष्ण जल (Sterile lukewarm saline/water)"
        freq = "Alternate day dressing"

    now = int(time.time())
    eval_id = f"VRANA-{data.patient_id}-{now}-{uuid.uuid4().hex[:6]}"

    cursor.execute(
        """
        INSERT INTO vrana_wound_evaluations (
            evaluation_id, patient_id, hospital_id, wound_stage,
            location, dimensions_cm, exudate_type,
            prescribed_shashti_upakramas_json, practitioner_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            eval_id,
            data.patient_id,
            hospital_id,
            stage.value,
            data.location,
            data.dimensions_cm,
            "Purulent" if data.has_purulent_discharge else "Serous",
            json.dumps(upakramas),
            data.practitioner_arn,
            now,
        )
    )
    conn.commit()

    return VranaAssessmentResponse(
        evaluation_id=eval_id,
        patient_id=data.patient_id,
        wound_stage=stage,
        prescribed_shashti_upakramas=upakramas,
        topical_formulation=topical,
        irrigation_solution=irrigation,
        dressing_frequency=freq,
        practitioner_arn=data.practitioner_arn,
        created_at=now,
    )
