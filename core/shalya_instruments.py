"""
Shalya Tantra Yantra-Shastra Microsurgical Instruments & Operative Suite Engine
================================================================================
Implements:
1. 101 Classical Yantras & 20 Shastras Structural Registry (Sushruta Sutrasthana Ch. 7 & 8)
2. Ashtavidha Shastra Karma Operative Procedures (Chhedana, Bhedana, Lekhana, etc.)
3. Yogya Sutriya Surgical Simulation Competency Certification (Sushruta Sutra 9)
4. Kshara-Agni Karma Operative Safety Firewalls & Neutralization Protocols
5. SQLite WAL Persistence with SHA-256 Hash-Chained Audit Ledger Logging
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
from models.shalya_instruments import (
    AshtavidhaKarma,
    InstrumentClass,
    OperativeProcedureCreate,
    OperativeProcedureResponse,
    ParasurgicalModality,
    SurgicalInstrumentProfile,
    YantraCategory,
    YogyaAssessmentCreate,
    YogyaAssessmentResponse,
    YogyaSimulationModel,
)

# ==============================================================================
# 1. CLASSICAL YANTRA & SHASTRA CATALOG SEED DATA
# ==============================================================================

SEED_INSTRUMENT_CATALOG: List[SurgicalInstrumentProfile] = [
    SurgicalInstrumentProfile(
        instrument_code="YAN-SVA-01",
        instrument_type=InstrumentClass.YANTRA,
        sanskrit_name="सिंहमुख स्वस्तिक यन्त्र (Simhamukha Svastika Yantra - Lion-Faced Forceps)",
        category_group=YantraCategory.SVASTIKA,
        angula_dimension=18.0,
        target_tissues=["Dense cortical bone fragments", "Deeply lodged metallic foreign bodies", "Fibrous masses"],
        primary_action="Powerful extraction and firm gripping of foreign bodies impacted in deep muscular or bony structures",
        sterilization_protocol="Agni-Taptam (Flaming/heat), ultrasonic wash, and steam autoclaving at 121°C"
    ),
    SurgicalInstrumentProfile(
        instrument_code="YAN-SAN-02",
        instrument_type=InstrumentClass.YANTRA,
        sanskrit_name="सन्दंश यन्त्र (Sandamsha Yantra - Non-Toothed Tissue Tweezers)",
        category_group=YantraCategory.SANDAMSHA,
        angula_dimension=16.0,
        target_tissues=["Dermal cut edges", "Delicate fascia", "Vascular adventitia"],
        primary_action="Atraumatic grasping of fine wound edges during dissection, excision, and suturing",
        sterilization_protocol="Boiling with Triphala-Nimba decoction, followed by autoclaving"
    ),
    SurgicalInstrumentProfile(
        instrument_code="YAN-TAL-03",
        instrument_type=InstrumentClass.YANTRA,
        sanskrit_name="एकताल यन्त्र (Ekatala Yantra - Single-Scoop Ear/Nose Pick)",
        category_group=YantraCategory.TALA,
        angula_dimension=12.0,
        target_tissues=["External auditory canal", "Nasal cavity", "Sinus apertures"],
        primary_action="Scooping and elevation of foreign bodies and hard cerumen from narrow orifices",
        sterilization_protocol="Chemical sterilization with alcoholic extract followed by steam autoclaving"
    ),
    SurgicalInstrumentProfile(
        instrument_code="YAN-NAD-04",
        instrument_type=InstrumentClass.YANTRA,
        sanskrit_name="अर्शो यन्त्र (Arsho Yantra - Two-Slit Proctoscope Speculum)",
        category_group=YantraCategory.NADI,
        angula_dimension=4.0,
        target_tissues=["Anal canal", "Internal hemorrhoidal cushions (Guda)"],
        primary_action="Tubular exposure and isolation of hemorrhoids for Ksharasutra or Pratisaraniya Kshara application",
        sterilization_protocol="High-level chemical disinfection and steam autoclaving at 134°C"
    ),
    SurgicalInstrumentProfile(
        instrument_code="YAN-SHA-05",
        instrument_type=InstrumentClass.YANTRA,
        sanskrit_name="गण्डूपदमुख शलाका यन्त्र (Gandupadamukha Shalaka - Sinus Exploration Probe)",
        category_group=YantraCategory.SHALAKA,
        angula_dimension=8.0,
        target_tissues=["Fistula-in-ano tracks (Bhagandara)", "Pilonidal sinus", "Deep blind ulcers"],
        primary_action="Eshana (atraumatic exploration and tracing of fistulous tracts with smooth earthworm-shaped head)",
        sterilization_protocol="Steam autoclaving and dry-heat sterilization"
    ),
    SurgicalInstrumentProfile(
        instrument_code="YAN-UPA-06",
        instrument_type=InstrumentClass.YANTRA,
        sanskrit_name="अयस्कान्त उपयन्त्र (Ayaskanta Upayantra - Surgical Magnetic Extractor)",
        category_group=YantraCategory.UPAYANTRA,
        angula_dimension=6.0,
        target_tissues=["Corneal surface", "Soft tissues with retained iron/steel shrapnel"],
        primary_action="Aharana (atraumatic magnetic extraction of loose ferromagnetic foreign bodies)",
        sterilization_protocol="Cold ethylene oxide (EtO) sterilization or UV-C irradiation"
    ),
    SurgicalInstrumentProfile(
        instrument_code="SHA-VRID-07",
        instrument_type=InstrumentClass.SHASTRA,
        sanskrit_name="वृद्धिपत्र शस्त्र (Vriddhipatra Shastra - Classical Surgical Scalpel)",
        category_group=YantraCategory.SHASTRA,
        angula_dimension=7.0,
        target_tissues=["Skin", "Subcutaneous fascia", "Fibroadenomas", "Abscess walls"],
        primary_action="Chhedana (clean linear/elliptical excision) and Bhedana (incision) with curved single-edged blade",
        sterilization_protocol="Oil-honing on stone (Taila-Dhauta), ultrasonic cleansing, autoclaving"
    ),
    SurgicalInstrumentProfile(
        instrument_code="SHA-MAND-08",
        instrument_type=InstrumentClass.SHASTRA,
        sanskrit_name="मण्डलाग्र शस्त्र (Mandalagra Shastra - Circular Excision & Scraping Blade)",
        category_group=YantraCategory.SHASTRA,
        angula_dimension=6.0,
        target_tissues=["Ulcer slough", "Hypertrophic granulation tissue", "Uvula & tonsil bases"],
        primary_action="Lekhana (precision scraping of necrotic slough) and circular tissue resection",
        sterilization_protocol="Micro-honing, immersion in Haridra extract, and autoclave sterilization"
    ),
    SurgicalInstrumentProfile(
        instrument_code="SHA-KUSH-09",
        instrument_type=InstrumentClass.SHASTRA,
        sanskrit_name="कुशपत्र शस्त्र (Kushapatra Shastra - Pointed Drainage Lancet)",
        category_group=YantraCategory.SHASTRA,
        angula_dimension=6.0,
        target_tissues=["Mature abscess cavities (Pakva Vrana)", "Hematomas", "Bursal effusions"],
        primary_action="Visravana (rapid stab entry and dependent drainage of purulent collections)",
        sterilization_protocol="Autoclaving at 121°C for 20 minutes"
    ),
    SurgicalInstrumentProfile(
        instrument_code="SHA-ESHA-10",
        instrument_type=InstrumentClass.SHASTRA,
        sanskrit_name="एषणी शस्त्र (Eshanika Shastra - Sharp Grooved Director & Probe)",
        category_group=YantraCategory.SHASTRA,
        angula_dimension=8.0,
        target_tissues=["Fistula tunnels", "Submucosal tracks", "Foreign body channels"],
        primary_action="Eshana and guiding Ksharasutra ligature threading through narrow fistulae",
        sterilization_protocol="Dry heat and steam autoclaving"
    ),
    SurgicalInstrumentProfile(
        instrument_code="SHA-BADI-11",
        instrument_type=InstrumentClass.SHASTRA,
        sanskrit_name="बडिश शस्त्र (Badisha Shastra - Sharp Retraction Hook)",
        category_group=YantraCategory.SHASTRA,
        angula_dimension=6.0,
        target_tissues=["Arman / Pterygium", "Uvula (Galashundika)", "Vascular pedicles"],
        primary_action="Aharana (traction, elevation, and steady holding of pathological tissue during excision)",
        sterilization_protocol="Ultrasonic wash and high-pressure steam autoclaving"
    ),
    SurgicalInstrumentProfile(
        instrument_code="SHA-SUCH-12",
        instrument_type=InstrumentClass.SHASTRA,
        sanskrit_name="सूची शस्त्र (Suchi Shastra - Quad-Type Precision Suturing Needles)",
        category_group=YantraCategory.SHASTRA,
        angula_dimension=3.0,
        target_tissues=["Skin", "Muscular layers", "Tendon sheaths", "Joint capsules"],
        primary_action="Seevana (wound closure using curved, triangular, straight, and circular needles)",
        sterilization_protocol="Individual sterile packaging and gamma-ray irradiation"
    )
]


# ==============================================================================
# 2. DATABASE INITIALIZATION & SEEDING
# ==============================================================================

def initialize_shalya_tables(conn: sqlite3.Connection) -> None:
    """Seed classical Yantra & Shastra catalog if empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM shalya_yantra_shastra_registry;")
    row = cursor.fetchone()
    if row and row["cnt"] == 0:
        now = int(time.time())
        for inst in SEED_INSTRUMENT_CATALOG:
            cursor.execute(
                """
                INSERT INTO shalya_yantra_shastra_registry (
                    instrument_code, instrument_type, sanskrit_name,
                    category_group, angula_dimension, target_tissues_json,
                    primary_action, sterilization_protocol, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    inst.instrument_code,
                    inst.instrument_type.value,
                    inst.sanskrit_name,
                    inst.category_group.value,
                    inst.angula_dimension,
                    json.dumps(inst.target_tissues),
                    inst.primary_action,
                    inst.sterilization_protocol,
                    now
                )
            )
        conn.commit()


# ==============================================================================
# 3. SURGICAL INSTRUMENTS QUERIES
# ==============================================================================

def list_all_instruments(
    conn: sqlite3.Connection,
    instrument_type: Optional[InstrumentClass] = None,
    category: Optional[YantraCategory] = None
) -> List[SurgicalInstrumentProfile]:
    """Retrieve catalog of surgical instruments with optional filtering."""
    cursor = conn.cursor()
    query = "SELECT * FROM shalya_yantra_shastra_registry WHERE 1=1"
    params: List[Any] = []

    if instrument_type:
        query += " AND instrument_type = ?"
        params.append(instrument_type.value)
    if category:
        query += " AND category_group = ?"
        params.append(category.value)

    query += " ORDER BY instrument_code ASC;"
    cursor.execute(query, params)
    rows = cursor.fetchall()

    return [
        SurgicalInstrumentProfile(
            instrument_code=r["instrument_code"],
            instrument_type=InstrumentClass(r["instrument_type"]),
            sanskrit_name=r["sanskrit_name"],
            category_group=YantraCategory(r["category_group"]),
            angula_dimension=r["angula_dimension"],
            target_tissues=json.loads(r["target_tissues_json"]),
            primary_action=r["primary_action"],
            sterilization_protocol=r["sterilization_protocol"],
        )
        for r in rows
    ]


def get_instrument_by_code(instrument_code: str, conn: sqlite3.Connection) -> SurgicalInstrumentProfile:
    """Retrieve single surgical instrument specification by code."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shalya_yantra_shastra_registry WHERE instrument_code = ?;", (instrument_code,))
    r = cursor.fetchone()
    if not r:
        raise RecordNotFoundException(entity="Surgical Instrument", identifier=instrument_code)

    return SurgicalInstrumentProfile(
        instrument_code=r["instrument_code"],
        instrument_type=InstrumentClass(r["instrument_type"]),
        sanskrit_name=r["sanskrit_name"],
        category_group=YantraCategory(r["category_group"]),
        angula_dimension=r["angula_dimension"],
        target_tissues=json.loads(r["target_tissues_json"]),
        primary_action=r["primary_action"],
        sterilization_protocol=r["sterilization_protocol"],
    )


# ==============================================================================
# 4. YOGYA SURGICAL SIMULATION TRAINING & COMPETENCY ENGINE
# ==============================================================================

def record_yogya_assessment(
    conn: sqlite3.Connection,
    hospital_id: str,
    data: YogyaAssessmentCreate
) -> YogyaAssessmentResponse:
    """
    Evaluates and certifies surgical simulation competency per Sushruta Sutrasthana Ch. 9.
    Composite threshold of 80.0 required to clear clinical surgical privileges.
    """
    composite_score = round((data.precision_score * 0.60) + (data.tissue_handling_score * 0.40), 1)
    certified = (composite_score >= 80.0)

    if certified:
        verdict = (
            f"COMPETENCY CERTIFIED: Practitioner meets Sushruta surgical precision standard (score {composite_score:.1f} >= 80.0) "
            f"on classical simulation model '{data.simulation_model_used.value}' for '{data.operative_karma_tested.value}'. "
            f"Eligible for supervised clinical operative procedures."
        )
    else:
        verdict = (
            f"COMPETENCY NOT CERTIFIED: Composite score {composite_score:.1f} is below the mandatory 80.0 threshold. "
            f"Mandates repeat simulation training on '{data.simulation_model_used.value}' before patient operating privileges."
        )

    now = int(time.time())
    assessment_id = f"yogya-{now}-{uuid.uuid4().hex[:6]}"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO surgical_simulation_yogya_assessments (
            assessment_id, practitioner_arn, hospital_id, operative_karma_tested,
            simulation_model_used, precision_score, tissue_handling_score,
            overall_competency_certified, examiner_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            assessment_id,
            data.practitioner_arn,
            hospital_id,
            data.operative_karma_tested.value,
            data.simulation_model_used.value,
            data.precision_score,
            data.tissue_handling_score,
            1 if certified else 0,
            data.examiner_arn,
            now
        )
    )
    conn.commit()

    append_audit_log(
        conn=conn,
        hospital_id=hospital_id,
        actor_id=data.examiner_arn,
        action="YOGYA_SIMULATION_ASSESSMENT",
        entity_type="YOGYA_ASSESSMENT",
        entity_id=assessment_id,
        details={
            "practitioner_arn": data.practitioner_arn,
            "operative_karma": data.operative_karma_tested.value,
            "composite_score": composite_score,
            "certified": certified
        }
    )

    return YogyaAssessmentResponse(
        assessment_id=assessment_id,
        practitioner_arn=data.practitioner_arn,
        hospital_id=hospital_id,
        operative_karma_tested=data.operative_karma_tested,
        simulation_model_used=data.simulation_model_used,
        precision_score=data.precision_score,
        tissue_handling_score=data.tissue_handling_score,
        composite_score=composite_score,
        overall_competency_certified=certified,
        certification_verdict=verdict,
        examiner_arn=data.examiner_arn,
        created_at=now
    )


def list_practitioner_yogya_assessments(
    practitioner_arn: str,
    conn: sqlite3.Connection
) -> List[YogyaAssessmentResponse]:
    """Retrieve historical Yogya simulation assessments for a practitioner."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM surgical_simulation_yogya_assessments
        WHERE practitioner_arn = ?
        ORDER BY created_at DESC;
        """,
        (practitioner_arn,)
    )
    rows = cursor.fetchall()
    return [
        YogyaAssessmentResponse(
            assessment_id=r["assessment_id"],
            practitioner_arn=r["practitioner_arn"],
            hospital_id=r["hospital_id"],
            operative_karma_tested=AshtavidhaKarma(r["operative_karma_tested"]),
            simulation_model_used=YogyaSimulationModel(r["simulation_model_used"]),
            precision_score=r["precision_score"],
            tissue_handling_score=r["tissue_handling_score"],
            composite_score=round((r["precision_score"] * 0.60) + (r["tissue_handling_score"] * 0.40), 1),
            overall_competency_certified=bool(r["overall_competency_certified"]),
            certification_verdict="Historical Assessment Record",
            examiner_arn=r["examiner_arn"],
            created_at=r["created_at"]
        )
        for r in rows
    ]


# ==============================================================================
# 5. ASHTAVIDHA OPERATIVE PROCEDURES & PARASURGICAL FIREWALL ENGINE
# ==============================================================================

def record_operative_procedure(
    conn: sqlite3.Connection,
    hospital_id: str,
    data: OperativeProcedureCreate
) -> OperativeProcedureResponse:
    """
    Logs an Ashtavidha surgical operation and enforces Kshara-Agni Karma safety firewalls:
    1. Kshara Karma: Requires Amla neutralizer (lemon juice / Kanji) on sterile field.
    2. Agni Karma: Prohibited in bleeding diathesis / internal hemorrhage (Raktapitta).
    """
    violations: List[str] = []

    # Parasurgical Firewall Rule 1: Kshara Neutralizer Readiness
    if data.parasurgical_modality == ParasurgicalModality.KSHARA_KARMA and not data.has_amla_neutralizer_ready:
        violations.append(
            "KSHARA KARMA FIREWALL VIOLATION: Amla neutralizing agent (Dhanyamla / fresh lemon juice) is missing from field. "
            "Unchecked caustic chemical dissolution of deep neurovascular planes will occur without immediate acid wash."
        )

    # Parasurgical Firewall Rule 2: Agni Karma Hemorrhage Contraindication
    if data.parasurgical_modality == ParasurgicalModality.AGNI_KARMA and data.patient_has_active_bleeding_diathesis:
        violations.append(
            "AGNI KARMA FIREWALL VIOLATION: Active bleeding diathesis / Raktapitta detected. "
            "Thermal cautery in coagulopathic states causes explosive vascular necrosis and uncontrolled hemorrhage."
        )

    safety_cleared = (len(violations) == 0)

    now = int(time.time())
    procedure_id = f"op-{now}-{uuid.uuid4().hex[:6]}"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO ashtavidha_operative_procedure_logs (
            procedure_id, patient_id, hospital_id, operative_karma,
            surgical_instruments_used_json, anesthesia_or_sangyaharana,
            parasurgical_modality, safety_firewall_cleared,
            operative_notes, surgeon_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            procedure_id,
            data.patient_id,
            hospital_id,
            data.operative_karma.value,
            json.dumps(data.surgical_instruments_used),
            data.anesthesia_or_sangyaharana,
            data.parasurgical_modality.value,
            1 if safety_cleared else 0,
            data.operative_notes,
            data.surgeon_arn,
            now
        )
    )
    conn.commit()

    append_audit_log(
        conn=conn,
        hospital_id=hospital_id,
        actor_id=data.surgeon_arn,
        action="ASHTAVIDHA_OPERATIVE_PROCEDURE",
        entity_type="SURGICAL_PROCEDURE",
        entity_id=procedure_id,
        details={
            "patient_id": data.patient_id,
            "operative_karma": data.operative_karma.value,
            "parasurgical_modality": data.parasurgical_modality.value,
            "safety_firewall_cleared": safety_cleared,
            "violation_count": len(violations)
        }
    )

    return OperativeProcedureResponse(
        procedure_id=procedure_id,
        patient_id=data.patient_id,
        hospital_id=hospital_id,
        operative_karma=data.operative_karma,
        surgical_instruments_used=data.surgical_instruments_used,
        anesthesia_or_sangyaharana=data.anesthesia_or_sangyaharana,
        parasurgical_modality=data.parasurgical_modality,
        safety_firewall_cleared=safety_cleared,
        firewall_violations=violations,
        operative_notes=data.operative_notes,
        surgeon_arn=data.surgeon_arn,
        created_at=now
    )


def list_patient_operative_procedures(
    patient_id: str,
    conn: sqlite3.Connection
) -> List[OperativeProcedureResponse]:
    """Retrieve historical Ashtavidha surgical procedures for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM ashtavidha_operative_procedure_logs
        WHERE patient_id = ?
        ORDER BY created_at DESC;
        """,
        (patient_id,)
    )
    rows = cursor.fetchall()
    return [
        OperativeProcedureResponse(
            procedure_id=r["procedure_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            operative_karma=AshtavidhaKarma(r["operative_karma"]),
            surgical_instruments_used=json.loads(r["surgical_instruments_used_json"]),
            anesthesia_or_sangyaharana=r["anesthesia_or_sangyaharana"],
            parasurgical_modality=ParasurgicalModality(r["parasurgical_modality"]),
            safety_firewall_cleared=bool(r["safety_firewall_cleared"]),
            firewall_violations=[],
            operative_notes=r["operative_notes"],
            surgeon_arn=r["surgeon_arn"],
            created_at=r["created_at"]
        )
        for r in rows
    ]
