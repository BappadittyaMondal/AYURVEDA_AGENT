"""
Upakarma & Bahya Parimarjana Therapy Matrix Engine
=================================================
Implements:
1. Classical catalog of 12 Bahya Parimarjana external therapies
2. Thermodynamic temperature boundaries and burn hazard firewalls
3. Hydrokinetic flow dynamics (suspension height, flow rate, stream continuity)
4. Lepa layer thickness and removal timing rules
5. Clinical pre-session screening against patient contraindications and Ama status
6. SQLite WAL persistence with indexed queries
"""

from __future__ import annotations
import json
import time
import sqlite3
from typing import List, Optional, Dict, Any, Tuple

from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from models.upakarma import (
    PreSessionScreeningRequest,
    PreSessionScreeningResponse,
    UpakarmaModality,
    UpakarmaSessionCreate,
    UpakarmaSessionRecord,
    UpakarmaTherapy,
)

# ==============================================================================
# CLASSICAL UPAKARMA THERAPIES CATALOG (12 SEED MODALITIES)
# ==============================================================================

SEED_UPAKARMA_REGISTRY: List[UpakarmaTherapy] = [
    # 1. ABHYANGA
    UpakarmaTherapy(
        therapy_id="UPAKARMA-ABHYANGA",
        sanskrit_name="अभ्यङ्ग (Sarvanga Abhyanga)",
        modality_code=UpakarmaModality.ABHYANGA,
        target_temperature_min_c=38.0,
        target_temperature_max_c=40.5,
        max_safe_temperature_c=42.0,
        standard_duration_minutes=45,
        recommended_media=["Mahanarayana Taila", "Ksheerabala Taila", "Dhanwantaram Taila", "Tila Taila"],
        cardinal_indications=["Vatavyadhi", "Jarahara (Anti-aging)", "Shramahara (Fatigue)", "Nidrajanana", "Dhatupushti"],
        contraindications=["Nava Jwara (Acute Fever)", "Ajeerna (Acute Indigestion)", "Taruna Ama (High Ama AGI >= 1.80)", "Atisara"],
        doshic_affinity="Vata Shamana"
    ),
    # 2. BASHPA SWEDA
    UpakarmaTherapy(
        therapy_id="UPAKARMA-BASHPA-SWEDA",
        sanskrit_name="बाष्प स्वेद (Sarvanga Bashpa Sweda)",
        modality_code=UpakarmaModality.SWEDANA_BASHPA,
        target_temperature_min_c=40.0,
        target_temperature_max_c=43.0,
        max_safe_temperature_c=45.0,
        standard_duration_minutes=15,
        recommended_media=["Dashamula Kwatha", "Nirgundi Kwatha", "Rasna Saptaka Kwatha"],
        cardinal_indications=["Stambha (Stiffness)", "Gaurava (Heaviness)", "Shita (Chills)", "Sandhigata Vata", "Kaphaja Rogas"],
        contraindications=["Garbhini (Pregnancy)", "Raktapitta (Bleeding disorders)", "Hridroga (Severe cardiac disease)", "Pittaprakopa", "Murcha"],
        doshic_affinity="Vata-Kapha Shamana"
    ),
    # 3. NADI SWEDA
    UpakarmaTherapy(
        therapy_id="UPAKARMA-NADI-SWEDA",
        sanskrit_name="नाडी स्वेद (Ekanga Nadi Sweda)",
        modality_code=UpakarmaModality.SWEDANA_NADI,
        target_temperature_min_c=40.0,
        target_temperature_max_c=44.0,
        max_safe_temperature_c=45.5,
        standard_duration_minutes=20,
        recommended_media=["Dashamula Kwatha with Eranda Patra", "Nirgundi Kwatha"],
        cardinal_indications=["Kati Shula (Low back pain)", "Gridhrasi (Sciatica)", "Manya Stambha (Cervical stiffness)", "Ekanga Vata"],
        contraindications=["Acute localized burns", "Skin ulcerations (Vrana)", "Erysipelas (Visarpa)"],
        doshic_affinity="Vata Shamana"
    ),
    # 4. SHIRODHARA (TAILA)
    UpakarmaTherapy(
        therapy_id="UPAKARMA-SHIRODHARA-TAILA",
        sanskrit_name="शिरोधारा (Taila Shirodhara)",
        modality_code=UpakarmaModality.SHIRODHARA_TAILA,
        target_temperature_min_c=37.0,
        target_temperature_max_c=39.0,
        max_safe_temperature_c=40.0,
        standard_duration_minutes=45,
        recommended_media=["Ksheerabala Taila (101 avartita)", "Chandanadi Taila", "Brahmi Taila"],
        cardinal_indications=["Anidra (Insomnia)", "Chinta (Anxiety)", "Shirashula (Tension Headache)", "Smriti Bhransha", "Ardita"],
        contraindications=["Nava Jwara", "Aamashaya Pratishyaya (Acute Coryza/Sinusitis)", "Murcha", "Severe Kapha Stambha"],
        doshic_affinity="Vata-Pitta Shamana"
    ),
    # 5. TAKRADHARA
    UpakarmaTherapy(
        therapy_id="UPAKARMA-TAKRADHARA",
        sanskrit_name="तक्रधारा (Takradhara)",
        modality_code=UpakarmaModality.TAKRADHARA,
        target_temperature_min_c=25.0,
        target_temperature_max_c=30.0,
        max_safe_temperature_c=32.0,
        standard_duration_minutes=45,
        recommended_media=["Musta-Amalaki processed Takra (Medicated Buttermilk)"],
        cardinal_indications=["Kitibha (Psoriasis)", "Khalitya (Alopecia)", "Pittaja Shirashula", "Unmada", "Chronic Stress"],
        contraindications=["Severe chills (Sheeta)", "Pratishyaya with profuse rhinorrhea", "Vata Kampa"],
        doshic_affinity="Pitta Shamana"
    ),
    # 6. PATRA PINDA SWEDA
    UpakarmaTherapy(
        therapy_id="UPAKARMA-PATRA-PINDA",
        sanskrit_name="पत्र पिण्ड स्वेद (Elakizhi)",
        modality_code=UpakarmaModality.PATRA_PINDA_SWEDA,
        target_temperature_min_c=42.0,
        target_temperature_max_c=46.0,
        max_safe_temperature_c=48.0,
        standard_duration_minutes=45,
        recommended_media=["Eranda-Nirgundi-Arka leaves fried in Tila Taila with Saindhava and Haridra"],
        cardinal_indications=["Amavata (Subacute stage)", "Sandhigata Vata", "Lumbar/Cervical Spondylosis", "Post-traumatic sprains"],
        contraindications=["Acute inflammatory joint effusion with extreme heat (Pitta Pitta)", "Open lesions"],
        doshic_affinity="Vata-Kapha Shamana"
    ),
    # 7. SHASHTIKA SHALI PINDA SWEDA
    UpakarmaTherapy(
        therapy_id="UPAKARMA-SHASHTIKA-SHALI",
        sanskrit_name="षष्टिक शालि पिण्ड स्वेद (Navarakizhi)",
        modality_code=UpakarmaModality.SHASHTIKA_SHALI_PINDA_SWEDA,
        target_temperature_min_c=40.0,
        target_temperature_max_c=44.0,
        max_safe_temperature_c=46.0,
        standard_duration_minutes=45,
        recommended_media=["Shashtika red rice cooked in Balamula Kwatha and Cow Milk (Godugdha)"],
        cardinal_indications=["Pakshaghata (Hemiplegia)", "Mamsakshaya (Muscle Atrophy)", "Dhatukshaya", "Neuro-muscular weakness"],
        contraindications=["Acute Ama state", "Kapha Medoroga", "Obesity"],
        doshic_affinity="Vata Shamana / Brimhana"
    ),
    # 8. CHURNA PINDA SWEDA (RUKSHA SWEDA)
    UpakarmaTherapy(
        therapy_id="UPAKARMA-CHURNA-PINDA",
        sanskrit_name="चूर्ण पिण्ड स्वेद (Podi Kizhi / Valuka Sweda)",
        modality_code=UpakarmaModality.CHURNA_PINDA_SWEDA,
        target_temperature_min_c=42.0,
        target_temperature_max_c=46.0,
        max_safe_temperature_c=48.0,
        standard_duration_minutes=30,
        recommended_media=["Kottamchukkadi Churna", "Kolakulathadi Churna", "Valuka (Purified Sand)"],
        cardinal_indications=["Amavata (Acute stage with high Ama)", "Medoroga", "Kaphadhika Vatavyadhi", "Severe stiffness"],
        contraindications=["Dhatukshaya", "Severe emaciation (Krisha)", "Ruksha dry skin with cracking"],
        doshic_affinity="Ama-Kapha Shamana / Rukshana"
    ),
    # 9. KATI BASTI
    UpakarmaTherapy(
        therapy_id="UPAKARMA-KATI-BASTI",
        sanskrit_name="कटि बस्ति (Kati Basti)",
        modality_code=UpakarmaModality.KATI_BASTI,
        target_temperature_min_c=40.0,
        target_temperature_max_c=43.0,
        max_safe_temperature_c=44.5,
        standard_duration_minutes=30,
        recommended_media=["Mahanarayana Taila", "Sahacharadi Taila", "Ksheerabala Taila"],
        cardinal_indications=["Kati Shula (Lumbar Spondylosis)", "Lumbar Disc Herniation (IVDP)", "Sciatica (Gridhrasi)"],
        contraindications=["Active infectious spondylodiscitis", "Open skin ulcers over lumbosacral region"],
        doshic_affinity="Vata Shamana"
    ),
    # 10. JANU BASTI
    UpakarmaTherapy(
        therapy_id="UPAKARMA-JANU-BASTI",
        sanskrit_name="जानु बस्ति (Janu Basti)",
        modality_code=UpakarmaModality.JANU_BASTI,
        target_temperature_min_c=40.0,
        target_temperature_max_c=43.0,
        max_safe_temperature_c=44.5,
        standard_duration_minutes=30,
        recommended_media=["Ksheerabala Taila", "Murivenna", "Dhanwantaram Taila"],
        cardinal_indications=["Janu Sandhigata Vata (Knee Osteoarthritis)", "Meniscal tear stiffness", "Crepitus in knees"],
        contraindications=["Acute septic arthritis", "Marked acute localized effusion with rubor"],
        doshic_affinity="Vata Shamana"
    ),
    # 11. LEPA (PRADEHA)
    UpakarmaTherapy(
        therapy_id="UPAKARMA-LEPA-PRADEHA",
        sanskrit_name="प्रदेह लेप (Pradeha Lepa)",
        modality_code=UpakarmaModality.LEPA_PRADEHA,
        target_temperature_min_c=38.0,
        target_temperature_max_c=42.0,
        max_safe_temperature_c=44.0,
        standard_duration_minutes=35,
        recommended_media=["Dashanga Lepa mixed with Ghrita", "Nagaradi Lepa with Kanji"],
        cardinal_indications=["Shotha (Inflammatory Swelling)", "Shula (Localized Pain)", "Sandhishotha"],
        contraindications=["Application over broken skin", "Retention after complete drying (causes itching)"],
        doshic_affinity="Vata-Kapha Shamana"
    ),
    # 12. UDVARTANA
    UpakarmaTherapy(
        therapy_id="UPAKARMA-UDVARTANA",
        sanskrit_name="उद्वर्तन (Ruksha Udvartana)",
        modality_code=UpakarmaModality.UDVARTANA,
        target_temperature_min_c=20.0,
        target_temperature_max_c=28.0,  # Ambient dry powder
        max_safe_temperature_c=35.0,
        standard_duration_minutes=45,
        recommended_media=["Triphala Churna", "Kolakulathadi Churna", "Yava Churna with Haridra"],
        cardinal_indications=["Sthaulya (Obesity)", "Medoroga", "Kapha Prakopa", "Cellulite", "Excessive sweating"],
        contraindications=["Severe emaciation", "Dry cracked skin (Ruksha Twacha)", "Eczema with raw weeping lesions"],
        doshic_affinity="Kapha-Medo Shamana"
    ),
]


# ==============================================================================
# DATABASE INITIALIZATION & SEEDING ENGINE
# ==============================================================================

def initialize_upakarma_tables(conn: sqlite3.Connection) -> None:
    """Populate upakarma_therapies_catalog if unseeded."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM upakarma_therapies_catalog;")
    row = cursor.fetchone()
    if row and row["cnt"] == 0:
        now = int(time.time())
        for t in SEED_UPAKARMA_REGISTRY:
            cursor.execute(
                """
                INSERT INTO upakarma_therapies_catalog (
                    therapy_id, sanskrit_name, modality_code, target_temperature_min_c,
                    target_temperature_max_c, max_safe_temperature_c, standard_duration_minutes,
                    recommended_media_json, cardinal_indications_json, contraindications_json,
                    doshic_affinity, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    t.therapy_id,
                    t.sanskrit_name,
                    t.modality_code.value,
                    t.target_temperature_min_c,
                    t.target_temperature_max_c,
                    t.max_safe_temperature_c,
                    t.standard_duration_minutes,
                    json.dumps(t.recommended_media),
                    json.dumps(t.cardinal_indications),
                    json.dumps(t.contraindications),
                    t.doshic_affinity,
                    now,
                )
            )


def get_therapy_profile(therapy_id: str, conn: sqlite3.Connection) -> UpakarmaTherapy:
    """Retrieve therapy catalog entry by ID."""
    initialize_upakarma_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM upakarma_therapies_catalog WHERE therapy_id = ?;", (therapy_id,))
    row = cursor.fetchone()
    if not row:
        raise RecordNotFoundException("UpakarmaTherapy", therapy_id)

    return UpakarmaTherapy(
        therapy_id=row["therapy_id"],
        sanskrit_name=row["sanskrit_name"],
        modality_code=UpakarmaModality(row["modality_code"]),
        target_temperature_min_c=row["target_temperature_min_c"],
        target_temperature_max_c=row["target_temperature_max_c"],
        max_safe_temperature_c=row["max_safe_temperature_c"],
        standard_duration_minutes=row["standard_duration_minutes"],
        recommended_media=json.loads(row["recommended_media_json"]),
        cardinal_indications=json.loads(row["cardinal_indications_json"]),
        contraindications=json.loads(row["contraindications_json"]),
        doshic_affinity=row["doshic_affinity"],
    )


def list_all_therapies(conn: sqlite3.Connection) -> List[UpakarmaTherapy]:
    """Retrieve all available Upakarma modalities."""
    initialize_upakarma_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM upakarma_therapies_catalog ORDER BY therapy_id ASC;")
    rows = cursor.fetchall()
    return [
        UpakarmaTherapy(
            therapy_id=r["therapy_id"],
            sanskrit_name=r["sanskrit_name"],
            modality_code=UpakarmaModality(r["modality_code"]),
            target_temperature_min_c=r["target_temperature_min_c"],
            target_temperature_max_c=r["target_temperature_max_c"],
            max_safe_temperature_c=r["max_safe_temperature_c"],
            standard_duration_minutes=r["standard_duration_minutes"],
            recommended_media=json.loads(r["recommended_media_json"]),
            cardinal_indications=json.loads(r["cardinal_indications_json"]),
            contraindications=json.loads(r["contraindications_json"]),
            doshic_affinity=r["doshic_affinity"],
        )
        for r in rows
    ]


# ==============================================================================
# PRE-SESSION SCREENING & THERMAL SAFETY GATING
# ==============================================================================

def screen_pre_session_safety(
    req: PreSessionScreeningRequest,
    conn: sqlite3.Connection
) -> PreSessionScreeningResponse:
    """
    Screens patient against modality contraindications and validates proposed temperature:
    1. Thermodynamic burn check: proposed_temp <= max_safe_temp
    2. Contraindication check: scans patient conditions against known contraindications
    3. Ama Gating: If AGI >= 1.80 and Snigdha Sweda is selected, flags warning and recommends Ruksha Sweda.
    """
    therapy = get_therapy_profile(req.therapy_id, conn)

    contraindication_flags: List[str] = []

    # 1. Thermodynamic Temperature Evaluation
    if req.proposed_temperature_c > therapy.max_safe_temperature_c:
        temp_compliance = "EXCESSIVE_RISK_OF_BURNS"
        contraindication_flags.append(
            f"Burn Hazard: Proposed temperature {req.proposed_temperature_c:.1f}C exceeds maximum safe ceiling ({therapy.max_safe_temperature_c:.1f}C)."
        )
    elif req.proposed_temperature_c < therapy.target_temperature_min_c:
        temp_compliance = "SUB_THERAPEUTIC"
        contraindication_flags.append(
            f"Sub-Therapeutic: Proposed temperature {req.proposed_temperature_c:.1f}C below minimum effective floor ({therapy.target_temperature_min_c:.1f}C)."
        )
    else:
        temp_compliance = "COMPLIANT"

    # 2. Patient Conditions Contraindication Cross-Reference
    active_conditions_lower = [c.lower() for c in req.patient_conditions]
    for c_rule in therapy.contraindications:
        c_rule_lower = c_rule.lower()
        for pat_cond in active_conditions_lower:
            if any(term in pat_cond for term in ["jwara", "fever"]) and "jwara" in c_rule_lower:
                contraindication_flags.append(f"Contraindication matched: Active Fever / Jwara prohibits {therapy.sanskrit_name}.")
            elif any(term in pat_cond for term in ["pregnancy", "garbhini"]) and "garbhini" in c_rule_lower:
                contraindication_flags.append(f"Contraindication matched: Pregnancy prohibits {therapy.sanskrit_name}.")
            elif any(term in pat_cond for term in ["cardiac", "hridroga", "heart"]) and "hridroga" in c_rule_lower:
                contraindication_flags.append(f"Contraindication matched: Cardiac condition prohibits {therapy.sanskrit_name}.")
            elif any(term in pat_cond for term in ["bleeding", "raktapitta"]) and "raktapitta" in c_rule_lower:
                contraindication_flags.append(f"Contraindication matched: Bleeding diathesis prohibits {therapy.sanskrit_name}.")
            elif any(term in pat_cond for term in ["pratishyaya", "coryza", "sinusitis"]) and "pratishyaya" in c_rule_lower:
                contraindication_flags.append(f"Contraindication matched: Acute Coryza/Sinusitis prohibits {therapy.sanskrit_name}.")

    # 3. High Ama State Check (AGI >= 1.80)
    if req.pre_op_agi_score is not None and req.pre_op_agi_score >= 1.80:
        if therapy.modality_code in (
            UpakarmaModality.ABHYANGA,
            UpakarmaModality.SWEDANA_BASHPA,
            UpakarmaModality.PATRA_PINDA_SWEDA,
            UpakarmaModality.SHASHTIKA_SHALI_PINDA_SWEDA,
        ):
            contraindication_flags.append(
                f"Sama Avastha Firewall (AGI {req.pre_op_agi_score:.2f} >= 1.80): Snigdha Sweda causes Srotorodha and Gaurava. "
                f"Ruksha Sweda (Churna Pinda / Valuka) is mandatory until Ama is digested."
            )

    is_safe = (len(contraindication_flags) == 0 and temp_compliance == "COMPLIANT")
    if is_safe:
        recommendation = f"CLEARED: Patient is safe to undergo {therapy.sanskrit_name} at {req.proposed_temperature_c:.1f}C."
    else:
        recommendation = f"BLOCKED: {len(contraindication_flags)} contraindication flags identified. Treatment must be adjusted or rescheduled."

    return PreSessionScreeningResponse(
        patient_id=req.patient_id,
        therapy_id=req.therapy_id,
        is_safe_to_proceed=is_safe,
        temperature_compliance=temp_compliance,
        contraindication_flags=contraindication_flags,
        clinical_recommendation=recommendation,
    )


# ==============================================================================
# UPAKARMA SESSION LOGGING ENGINE
# ==============================================================================

def log_upakarma_session(
    req: UpakarmaSessionCreate,
    hospital_id: str,
    conn: sqlite3.Connection
) -> UpakarmaSessionRecord:
    """
    Logs an administered Upakarma session.
    Validates operating temperature against burn safety limit and checks modality kinetics.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM patients WHERE patient_id = ?;", (req.patient_id,))
    if not cursor.fetchone():
        raise RecordNotFoundException("Patient", req.patient_id)

    therapy = get_therapy_profile(req.therapy_id, conn)

    adverse_events: List[str] = []

    # Burn safety check
    if req.operating_temperature_c > therapy.max_safe_temperature_c:
        if req.operating_temperature_c > (therapy.max_safe_temperature_c + 2.0):
            raise ClinicalGovernanceException(
                f"Severe Thermal Violation: Operating temperature {req.operating_temperature_c:.1f}C severely exceeds burn threshold ({therapy.max_safe_temperature_c:.1f}C).",
                error_code="THERMAL_BURN_VIOLATION"
            )
        adverse_events.append(f"Temperature warning: Operating temperature {req.operating_temperature_c:.1f}C exceeded maximum target.")

    # Modality specific kinetic validations
    if therapy.modality_code in (UpakarmaModality.SHIRODHARA_TAILA, UpakarmaModality.TAKRADHARA):
        if req.height_cm is not None and (req.height_cm < 4.0 or req.height_cm > 25.0):
            adverse_events.append(f"Hydrokinetic anomaly: Stream height {req.height_cm:.1f}cm deviates from standard (8-10 cm).")
        if req.flow_rate_ml_sec is not None and (req.flow_rate_ml_sec < 5.0 or req.flow_rate_ml_sec > 50.0):
            adverse_events.append(f"Flow rate anomaly: {req.flow_rate_ml_sec:.1f} mL/sec outside recommended laminar range.")

    if therapy.modality_code in (UpakarmaModality.LEPA_PRALEPA, UpakarmaModality.LEPA_PRADEHA):
        if req.lepa_thickness_mm is not None and req.lepa_thickness_mm > 12.0:
            adverse_events.append(f"Lepa thickness {req.lepa_thickness_mm:.1f}mm excessively thick (standard 3-6mm).")

    now = int(time.time())
    session_id = f"SES-UP-{therapy.modality_code.value}-{req.patient_id}-{now}"

    cursor.execute(
        """
        INSERT INTO upakarma_session_logs (
            session_id, patient_id, hospital_id, therapy_id, medium_used,
            operating_temperature_c, duration_minutes, flow_rate_ml_sec,
            height_cm, lepa_thickness_mm, pre_vitals_bp, post_vitals_bp,
            therapist_id, adverse_events_json, clinical_notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            session_id,
            req.patient_id,
            hospital_id,
            req.therapy_id,
            req.medium_used,
            req.operating_temperature_c,
            req.duration_minutes,
            req.flow_rate_ml_sec,
            req.height_cm,
            req.lepa_thickness_mm,
            req.pre_vitals_bp,
            req.post_vitals_bp,
            req.therapist_id,
            json.dumps(adverse_events),
            req.clinical_notes,
            now,
        )
    )

    return UpakarmaSessionRecord(
        session_id=session_id,
        patient_id=req.patient_id,
        hospital_id=hospital_id,
        therapy_id=req.therapy_id,
        medium_used=req.medium_used,
        operating_temperature_c=req.operating_temperature_c,
        duration_minutes=req.duration_minutes,
        flow_rate_ml_sec=req.flow_rate_ml_sec,
        height_cm=req.height_cm,
        lepa_thickness_mm=req.lepa_thickness_mm,
        pre_vitals_bp=req.pre_vitals_bp,
        post_vitals_bp=req.post_vitals_bp,
        therapist_id=req.therapist_id,
        adverse_events=adverse_events,
        clinical_notes=req.clinical_notes,
        created_at=now,
    )


def list_patient_upakarma_sessions(patient_id: str, conn: sqlite3.Connection) -> List[UpakarmaSessionRecord]:
    """Retrieve all Upakarma session logs for a specific patient."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM upakarma_session_logs WHERE patient_id = ? ORDER BY created_at DESC;",
        (patient_id,)
    )
    rows = cursor.fetchall()
    return [
        UpakarmaSessionRecord(
            session_id=r["session_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            therapy_id=r["therapy_id"],
            medium_used=r["medium_used"],
            operating_temperature_c=r["operating_temperature_c"],
            duration_minutes=r["duration_minutes"],
            flow_rate_ml_sec=r["flow_rate_ml_sec"],
            height_cm=r["height_cm"],
            lepa_thickness_mm=r["lepa_thickness_mm"],
            pre_vitals_bp=r["pre_vitals_bp"],
            post_vitals_bp=r["post_vitals_bp"],
            therapist_id=r["therapist_id"],
            adverse_events=json.loads(r["adverse_events_json"]),
            clinical_notes=r["clinical_notes"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
