"""
Agada Tantra, Visha Chikitsa & Environmental Toxicology Engine
==============================================================
Implements:
1. Classical Visha Registry (Sthavara, Jangama, Dushi Visha, Gara Visha)
2. Envenomation Syndromic Stratification (Darvikara, Mandala, Rajimanta)
3. 20-Minute Whole Blood Clotting Test (20WBCT) & Modern Antidote Firewall
4. Polyvalent Anti-Snake Venom (ASV) & Cardioprotective Hridaya-Avarana Protocols
5. Dushi Visha Chronic Latent Bioaccumulation & Dooshivishari Agada Management
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
from models.agada_tantra import (
    DushiVishaAssessmentCreate,
    DushiVishaAssessmentResponse,
    EnvenomationSyndrome,
    ToxicEmergencyTriage,
    VishaCategory,
    VishaEmergencyAdmissionCreate,
    VishaEmergencyAdmissionResponse,
    VishaProfile,
)

# ==============================================================================
# 1. CLASSICAL TOXICOLOGY & ENVENOMATION REGISTRY
# ==============================================================================

SEED_VISHA_CATALOG: List[VishaProfile] = [
    # Sthavara Visha (Plant & Mineral Toxins)
    VishaProfile(
        visha_code="VISHA-STH-01",
        sanskrit_name="वत्सनाभ विष (Vatsanabha Visha)",
        english_name="Monkshood / Aconite Poisoning (Aconitum ferox)",
        visha_category=VishaCategory.STHAVARA,
        source_origin="Tuberous root containing neurotoxic & cardiotoxic aconitine alkaloids",
        cardinal_manifestations=[
            "Severe perioral tingling and numbness (Harsha)",
            "Ventricular tachycardia / fatal cardiac arrhythmias",
            "Profound hypotension and hypothermia",
            "Terminal respiratory depression"
        ],
        upakrama_indications=[
            "Vamana (Emesis with Alabu/Saindhava)",
            "Hridaya-Avarana (Cardioprotection with ghee, honey, and Maricha)",
            "Tankana Bhasma (Specific mineral counteractant)"
        ],
        specific_agada_formulations=["Bilvadi Agada", "Sanjivani Vati", "Tankana Bhasma with cow ghee"],
        modern_antidote_mapping="Atropine (for bradycardia) + inotropic & antiarrhythmic intensive support"
    ),
    VishaProfile(
        visha_code="VISHA-STH-02",
        sanskrit_name="धत्तूर विष (Dhattura Visha)",
        english_name="Datura / Thorn Apple Intoxication (Datura stramonium)",
        visha_category=VishaCategory.STHAVARA,
        source_origin="Seeds containing tropane alkaloids (hyoscyamine, scopolamine, atropine)",
        cardinal_manifestations=[
            "Extreme dryness of mouth and throat (Mukhashosha)",
            "Fixed dilated pupils / cycloplegia (Vistrita Drishti)",
            "Delirium, visual hallucinations, and agitation (Pralapa)",
            "Flushed skin and hyperthermia"
        ],
        upakrama_indications=[
            "Vamana with Karanja and Nimba decoction",
            "Sheeta Parisheka (Cold water sprinkling)",
            "Ksheera and Draksha juice administration"
        ],
        specific_agada_formulations=["Drakshasava", "Chandanadi Kwatha", "Kalyanaka Ghrita"],
        modern_antidote_mapping="Physostigmine salicylate + active gastric lavage with activated charcoal"
    ),
    VishaProfile(
        visha_code="VISHA-STH-03",
        sanskrit_name="सोमल / शङ्खिया विष (Somala / White Arsenic)",
        english_name="Arsenic Trioxide Poisoning",
        visha_category=VishaCategory.STHAVARA,
        source_origin="Inorganic mineral arsenic salt (As2O3)",
        cardinal_manifestations=[
            "Rice-water cholera-like severe gastrointestinal purging",
            "Excruciating burning in throat and abdomen (Udaradaha)",
            "Metallic taste and garlic odor of breath",
            "Cardiovascular collapse and hypovolemic shock"
        ],
        upakrama_indications=[
            "Immediate Vamana with warm saltwater",
            "Gairika (red ochre) water and fresh cow ghee administration",
            "Hridaya-Avarana"
        ],
        specific_agada_formulations=["Gairika Kashaya with Ghrita", "Bilvadi Agada"],
        modern_antidote_mapping="Dimercaprol (BAL) / Succimer (DMSA) chelation therapy"
    ),

    # Jangama Visha (Animal Venoms)
    VishaProfile(
        visha_code="VISHA-JAN-01",
        sanskrit_name="दवकिर सर्पदंश (Darvikara Sarpa / Elapid Envenomation)",
        english_name="Neurotoxic Snakebite (Spectacled Cobra & Common Krait)",
        visha_category=VishaCategory.JANGAMA,
        source_origin="Venom apparatus of Naja naja and Bungarus caeruleus (Post- and pre-synaptic neurotoxins)",
        cardinal_manifestations=[
            "Bilateral ptosis (drooping eyelids) and ophthalmoplegia",
            "Dysphagia (inability to swallow saliva) and broken speech",
            "Ascending flaccid skeletal muscle paralysis",
            "Asphyxia from diaphragmatic and intercostal muscle paralysis"
        ],
        upakrama_indications=[
            "Arishta-Bandhana (Broad pressure immobilization without arterial strangulation)",
            "Hridaya-Avarana (Cardiac and neural protection)",
            "Nasya with Tikshna herbs for comatose states",
            "Aushadha (Bilvadi Agada)"
        ],
        specific_agada_formulations=["Bilvadi Agada", "Dashanga Agada", "Kalyanaka Kshara"],
        modern_antidote_mapping="Polyvalent Anti-Snake Venom (ASV) 10 vials IV + Neostigmine & Atropine"
    ),
    VishaProfile(
        visha_code="VISHA-JAN-02",
        sanskrit_name="मण्डल सर्पदंश (Mandala Sarpa / Viperid Envenomation)",
        english_name="Hemotoxic Snakebite (Russell's Viper & Saw-scaled Viper)",
        visha_category=VishaCategory.JANGAMA,
        source_origin="Venom apparatus of Daboia russelii and Echis carinatus (Procoagulant, hemorrhagin, metalloproteinase toxins)",
        cardinal_manifestations=[
            "Rapid massive progressive limb edema and hemorrhagic bullae",
            "Incoagulable blood (20WBCT > 20 minutes / complete failure to clot)",
            "Spontaneous mucosal hemorrhage (gingival, hematuria, hemoptysis)",
            "Acute Kidney Injury (oliguria / anuria) and DIC"
        ],
        upakrama_indications=[
            "Parisheka (Cool decoction irrigation; strictly avoid warm incisions)",
            "Hridaya-Avarana",
            "Aushadha (Chandanadi and Lodhradi cooling Agadas)"
        ],
        specific_agada_formulations=["Chandanadi Agada", "Lodhrasava", "Gopachandanadi Agada"],
        modern_antidote_mapping="Polyvalent Anti-Snake Venom (ASV) 10 vials IV + Fresh Frozen Plasma (FFP)"
    ),
    VishaProfile(
        visha_code="VISHA-JAN-03",
        sanskrit_name="वृश्चिक दंश (Vrishchika Damsha)",
        english_name="Scorpion Sting Envenomation (Mesobuthus tamulus)",
        visha_category=VishaCategory.JANGAMA,
        source_origin="Telson stinger of Red Indian Scorpion (Autonomic storm neurotoxin)",
        cardinal_manifestations=[
            "Excruciating burning pain radiating proximally from sting site",
            "Autonomic storm: profuse sweating, salivation, priapism",
            "Hypertension transitioning to acute myocarditis",
            "Fulminant acute pulmonary edema and pink frothy sputum"
        ],
        upakrama_indications=[
            "Swedana with warm rock salt (Saindhava Lavana)",
            "Matulunga swarasa application",
            "Aushadha (Bilvadi Agada with honey)"
        ],
        specific_agada_formulations=["Bilvadi Agada", "Hingu-Matulunga Lepa", "Dashanga Agada"],
        modern_antidote_mapping="Prazosin (alpha-1 adrenergic antagonist) + scorpion antivenom"
    ),
    VishaProfile(
        visha_code="VISHA-JAN-04",
        sanskrit_name="अलर्क विष (Alarka Visha)",
        english_name="Rabid Animal Bite / Rabies Viral Envenomation",
        visha_category=VishaCategory.JANGAMA,
        source_origin="Saliva of rabid dog/jackal carrying Lyssavirus",
        cardinal_manifestations=[
            "Extreme hydrophobia (Jalatrasha) and aerophobia",
            "Intense paroxysmal laryngeal spasm upon water exposure",
            "Agitation, hyper-salivation, and terminal encephalitis"
        ],
        upakrama_indications=[
            "Immediate vigorous wound washing with soap and running water",
            "Agnikarma (Cauterization of bite wound with boiling ghee / classical protocol)",
            "Aushadha (Jalatrashahara formulations)"
        ],
        specific_agada_formulations=["Bilvadi Agada", "Palasha Kashaya", "Sarivadyasava"],
        modern_antidote_mapping="Rabies Post-Exposure Prophylaxis: Rabies Vaccine + Human Rabies Immunoglobulin (RIG)"
    ),

    # Dushi Visha (Latent Chronic Toxins)
    VishaProfile(
        visha_code="VISHA-DUS-01",
        sanskrit_name="दूषीविष (Dushi Visha)",
        english_name="Chronic Latent Xenobiotic Bioaccumulation (Heavy Metals, Pesticides)",
        visha_category=VishaCategory.DUSHI_VISHA,
        source_origin="Low-grade persistent environmental toxins coated in Kapha and lodged in deep Dhatus",
        cardinal_manifestations=[
            "Looseness of stools, pallor, and altered complexion (Panduta)",
            "Recurrent urticarial eruptions (Kotha / Kitibha) triggered by cloudy weather (Megha-Kala)",
            "Hair fall, generalized fatigue, and chronic joint stiffness",
            "Suppression of digestive fire (Agnimandya) and sleep disturbances"
        ],
        upakrama_indications=[
            "Swedana (Sudation to liquefy sticky latent toxin)",
            "Mridu Vamana / Virechana",
            "Dooshivishari Agada with honey"
        ],
        specific_agada_formulations=["Dooshivishari Agada", "Amritarishta", "Patoladi Kwatha"],
        modern_antidote_mapping="Chelation therapy (DMSA / EDTA) + organ protection and antioxidant therapy"
    ),

    # Gara Visha (Concocted Slow Chemical Toxins)
    VishaProfile(
        visha_code="VISHA-GAR-01",
        sanskrit_name="गरविष (Gara Visha)",
        english_name="Concocted Slow Toxins & Food Adulteration Toxidrome",
        visha_category=VishaCategory.GARA_VISHA,
        source_origin="Artificial mixture of non-toxic substances or toxic adulterants producing slow visceral decline",
        cardinal_manifestations=[
            "Progressive splenic and liver enlargement (Yakrit-Pleehodara)",
            "Dry hacking cough, emaciation (Shosha), and intermittent pyrexia",
            "Drop in hemopoiesis, severe edema, and metabolic toxemia"
        ],
        upakrama_indications=[
            "Vamana with fine copper powder / Suvarna Bhasma and honey",
            "Murva Agada",
            "Deepana-Pachana"
        ],
        specific_agada_formulations=["Murva Agada", "Kalyanaka Ghrita", "Suvarna Bhasma with Madhu"],
        modern_antidote_mapping="Gastric lavage, oral activated charcoal, and targeted organ-specific antidote"
    )
]


# ==============================================================================
# DATABASE INITIALIZATION & SEEDING ENGINE
# ==============================================================================

def initialize_agada_tables(conn: sqlite3.Connection) -> None:
    """Populate agada_toxicology_registry if unseeded."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM agada_toxicology_registry;")
    row = cursor.fetchone()
    if row and row["cnt"] == 0:
        now = int(time.time())
        for v in SEED_VISHA_CATALOG:
            cursor.execute(
                """
                INSERT INTO agada_toxicology_registry (
                    visha_code, sanskrit_name, english_name, visha_category,
                    source_origin, cardinal_manifestations_json, upakrama_indications_json,
                    specific_agada_formulations_json, modern_antidote_mapping, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    v.visha_code,
                    v.sanskrit_name,
                    v.english_name,
                    v.visha_category.value,
                    v.source_origin,
                    json.dumps(v.cardinal_manifestations),
                    json.dumps(v.upakrama_indications),
                    json.dumps(v.specific_agada_formulations),
                    v.modern_antidote_mapping,
                    now,
                )
            )
        conn.commit()


def get_visha_profile(visha_code: str, conn: sqlite3.Connection) -> VishaProfile:
    """Retrieve full toxicological specification of a Visha by code."""
    initialize_agada_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agada_toxicology_registry WHERE visha_code = ?;", (visha_code,))
    row = cursor.fetchone()
    if not row:
        raise RecordNotFoundException("VishaProfile", visha_code)

    return VishaProfile(
        visha_code=row["visha_code"],
        sanskrit_name=row["sanskrit_name"],
        english_name=row["english_name"],
        visha_category=VishaCategory(row["visha_category"]),
        source_origin=row["source_origin"],
        cardinal_manifestations=json.loads(row["cardinal_manifestations_json"]),
        upakrama_indications=json.loads(row["upakrama_indications_json"]),
        specific_agada_formulations=json.loads(row["specific_agada_formulations_json"]),
        modern_antidote_mapping=row["modern_antidote_mapping"],
    )


def list_all_vishas(
    conn: sqlite3.Connection,
    category: Optional[VishaCategory] = None
) -> List[VishaProfile]:
    """List registered poisons and venoms with optional category filter."""
    initialize_agada_tables(conn)
    cursor = conn.cursor()
    if category:
        cursor.execute("SELECT * FROM agada_toxicology_registry WHERE visha_category = ? ORDER BY visha_code ASC;", (category.value,))
    else:
        cursor.execute("SELECT * FROM agada_toxicology_registry ORDER BY visha_code ASC;")
    rows = cursor.fetchall()
    return [
        VishaProfile(
            visha_code=r["visha_code"],
            sanskrit_name=r["sanskrit_name"],
            english_name=r["english_name"],
            visha_category=VishaCategory(r["visha_category"]),
            source_origin=r["source_origin"],
            cardinal_manifestations=json.loads(r["cardinal_manifestations_json"]),
            upakrama_indications=json.loads(r["upakrama_indications_json"]),
            specific_agada_formulations=json.loads(r["specific_agada_formulations_json"]),
            modern_antidote_mapping=r["modern_antidote_mapping"],
        )
        for r in rows
    ]


# ==============================================================================
# ENVENOMATION TRIAGE & MODERN ANTIDOTE FIREWALL
# ==============================================================================

def record_visha_emergency_admission(
    conn: sqlite3.Connection,
    hospital_id: str,
    adm_in: VishaEmergencyAdmissionCreate
) -> VishaEmergencyAdmissionResponse:
    """
    Execute acute envenomation triage with strict Anti-Snake Venom (ASV) firewall
    and classical 24-Upakrama cardioprotective Hridaya-Avarana coordination.
    """
    initialize_agada_tables(conn)

    # Coagulopathy & Neurotoxic Emergency Criteria:
    # 1. 20WBCT failure to clot (twenty_minute_wbct_clotted == False) indicates profound venom-induced consumption coagulopathy (VICC).
    # 2. Neurotoxic signs (ptosis, bulbar weakness, dyspnea) indicate impending respiratory collapse.
    # 3. Severe hemotoxic signs (spontaneous mucosal bleeding or rapidly progressing edema).
    is_neurotoxic_crisis = adm_in.neurotoxic_signs_present
    is_hemotoxic_crisis = (not adm_in.twenty_minute_wbct_clotted) or adm_in.hemotoxic_signs_present

    is_critical = (
        is_neurotoxic_crisis or
        is_hemotoxic_crisis or
        adm_in.envenomation_syndrome in (
            EnvenomationSyndrome.DARVIKARA_NEUROTOXIC,
            EnvenomationSyndrome.MANDALA_HEMOTOXIC
        ) and (adm_in.neurotoxic_signs_present or not adm_in.twenty_minute_wbct_clotted)
    )

    if is_critical:
        triage_level = ToxicEmergencyTriage.CRITICAL_TOXIC_EMERGENCY
        asv_vials = 10
        escalation_protocol = (
            "CRITICAL ENVENOMATION PROTOCOL ACTIVATED: Immediate intravenous infusion of 10 vials "
            "Polyvalent Anti-Snake Venom (ASV) reconstituted in 200 ml normal saline infused over 1 hour. "
            "Maintain emergency airway protection and anaphylaxis readiness (Adrenaline 1:1000 IM, Atropine, Hydrocortisone). "
            "STRICT CLINICAL FIREWALL: Modern ASV infusion is legally and clinically mandatory; under no circumstances "
            "may ASV be delayed or replaced by oral herbal formulations alone."
        )
        upakramas = [
            "Arishta-Bandhana (Broad pressure immobilization without arterial occlusion)",
            "Hridaya-Avarana (Cardioprotective unction)",
            "Aushadha (Adjunctive Bilvadi Agada)",
            "Prashamana (Aggravated Dosha-Dhatu stabilization)"
        ]
        hridaya_avarana = (
            "Classical Cardioprotection: Sublingual cow ghee mixed with fine Maricha churna and honey "
            "(strictly unequal ratio) to preserve myocardial tissue perfusion during systemic toxin circulation."
        )
        agadas = ["Bilvadi Agada (tablets/decoction)", "Dashanga Agada", "Chandanadi Agada"]
    elif adm_in.hemotoxic_signs_present or adm_in.neurotoxic_signs_present:
        triage_level = ToxicEmergencyTriage.MODERATE_OBSERVATION
        asv_vials = 0
        escalation_protocol = (
            "Inconclusive systemic envenomation. Perform 20WBCT every 2 hours. If blood fails to clot or "
            "neurotoxic signs progress, immediately escalate to 10 vials Polyvalent ASV."
        )
        upakramas = ["Parisheka (Cooling herbal irrigation)", "Aushadha (Bilvadi Agada)"]
        hridaya_avarana = "Cow ghee administration with warm water."
        agadas = ["Bilvadi Agada"]
    else:
        triage_level = ToxicEmergencyTriage.NON_ENCLOSING_DISCHARGED
        asv_vials = 0
        escalation_protocol = None
        upakramas = ["Parisheka (Local wound cleansing)"]
        hridaya_avarana = "Routine reassurance and vital observation."
        agadas = []

    now = int(time.time())
    episode_id = f"tox-{now}-{uuid.uuid4().hex[:6]}"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO visha_emergency_admissions_logs (
            episode_id, patient_id, hospital_id, suspected_visha_code,
            envenomation_syndrome, bite_to_admission_minutes,
            twenty_minute_wbct_clotted, neurotoxic_signs_present,
            hemotoxic_signs_present, triage_level, asv_indicated_vials,
            upakramas_executed_json, cardioprotective_hridaya_avarana,
            practitioner_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            episode_id,
            adm_in.patient_id,
            hospital_id,
            adm_in.suspected_visha_code,
            adm_in.envenomation_syndrome.value,
            adm_in.bite_to_admission_minutes,
            1 if adm_in.twenty_minute_wbct_clotted else 0,
            1 if adm_in.neurotoxic_signs_present else 0,
            1 if adm_in.hemotoxic_signs_present else 0,
            triage_level.value,
            asv_vials,
            json.dumps(upakramas),
            hridaya_avarana,
            adm_in.practitioner_arn,
            now,
        )
    )
    conn.commit()

    return VishaEmergencyAdmissionResponse(
        episode_id=episode_id,
        patient_id=adm_in.patient_id,
        hospital_id=hospital_id,
        suspected_visha_code=adm_in.suspected_visha_code,
        envenomation_syndrome=adm_in.envenomation_syndrome,
        triage_level=triage_level,
        asv_indicated_vials=asv_vials,
        emergency_escalation_protocol=escalation_protocol,
        upakramas_executed=upakramas,
        cardioprotective_hridaya_avarana=hridaya_avarana,
        adjunctive_ayurvedic_agadas=agadas,
        practitioner_arn=adm_in.practitioner_arn,
        created_at=now,
    )


def list_visha_emergency_admissions(
    patient_id: str,
    conn: sqlite3.Connection
) -> List[VishaEmergencyAdmissionResponse]:
    """Retrieve historical envenomation admission episodes for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM visha_emergency_admissions_logs WHERE patient_id = ? ORDER BY created_at DESC;",
        (patient_id,)
    )
    rows = cursor.fetchall()
    return [
        VishaEmergencyAdmissionResponse(
            episode_id=r["episode_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            suspected_visha_code=r["suspected_visha_code"],
            envenomation_syndrome=EnvenomationSyndrome(r["envenomation_syndrome"]),
            triage_level=ToxicEmergencyTriage(r["triage_level"]),
            asv_indicated_vials=r["asv_indicated_vials"],
            emergency_escalation_protocol=None,
            upakramas_executed=json.loads(r["upakramas_executed_json"]),
            cardioprotective_hridaya_avarana=r["cardioprotective_hridaya_avarana"],
            adjunctive_ayurvedic_agadas=["Bilvadi Agada"],
            practitioner_arn=r["practitioner_arn"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


# ==============================================================================
# DUSHI VISHA CHRONIC DETOXIFICATION ENGINE
# ==============================================================================

def record_dushi_visha_assessment(
    conn: sqlite3.Connection,
    hospital_id: str,
    dushi_in: DushiVishaAssessmentCreate
) -> DushiVishaAssessmentResponse:
    """Record clinical assessment for chronic latent Dushi Visha and prescribe Dooshivishari Agada."""
    if dushi_in.chronicity_months >= 12:
        stage = "Advanced Deep-Tissue Dushi Visha (Dhatu-Gata Latent Intoxication)"
    else:
        stage = "Subacute Dushi Visha (Rasa-Rakta Gata)"

    shodhana = (
        "Mridu Snehana with Kalyanaka Ghrita followed by Swedana to liquefy the sticky "
        "Kaphavrita latent toxin, followed by mild Vamana or Virechana."
    )

    plan = [
        "Gold Standard Antidote: Dooshivishari Agada (1 to 2 grams) mixed with pure honey twice daily.",
        "Dietary Safeguards: Strictly avoid cold wind, fermented sour foods, and exposure during cloudy weather (Megha-Kala).",
        "Rasa-Dhatu Rejuvenation: Guduchi Rasayana and Suvarna Bhasma micro-dosing for immune restoration.",
        "Environmental Remediation: Identification and elimination of ongoing toxic exposure source."
    ]

    now = int(time.time())
    log_id = f"dushi-{now}-{uuid.uuid4().hex[:6]}"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO dushi_visha_chronic_treatment_logs (
            log_id, patient_id, hospital_id, suspected_toxin_source,
            chronicity_months, manifestations_json, dooshivishari_agada_prescribed,
            shodhana_protocol, practitioner_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            log_id,
            dushi_in.patient_id,
            hospital_id,
            dushi_in.suspected_toxin_source,
            dushi_in.chronicity_months,
            json.dumps(dushi_in.reported_manifestations),
            1,
            shodhana,
            dushi_in.practitioner_arn,
            now,
        )
    )
    conn.commit()

    return DushiVishaAssessmentResponse(
        log_id=log_id,
        patient_id=dushi_in.patient_id,
        hospital_id=hospital_id,
        suspected_toxin_source=dushi_in.suspected_toxin_source,
        chronicity_months=dushi_in.chronicity_months,
        manifestations=dushi_in.reported_manifestations,
        dushi_visha_stage=stage,
        dooshivishari_agada_prescribed=True,
        shodhana_protocol=shodhana,
        clinical_management_plan=plan,
        practitioner_arn=dushi_in.practitioner_arn,
        created_at=now,
    )


def list_dushi_visha_assessments(
    patient_id: str,
    conn: sqlite3.Connection
) -> List[DushiVishaAssessmentResponse]:
    """Retrieve historical Dushi Visha assessments for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM dushi_visha_chronic_treatment_logs WHERE patient_id = ? ORDER BY created_at DESC;",
        (patient_id,)
    )
    rows = cursor.fetchall()
    return [
        DushiVishaAssessmentResponse(
            log_id=r["log_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            suspected_toxin_source=r["suspected_toxin_source"],
            chronicity_months=r["chronicity_months"],
            manifestations=json.loads(r["manifestations_json"]),
            dushi_visha_stage="Historical Assessment",
            dooshivishari_agada_prescribed=bool(r["dooshivishari_agada_prescribed"]),
            shodhana_protocol=r["shodhana_protocol"],
            clinical_management_plan=["Continue Dooshivishari Agada with honey."],
            practitioner_arn=r["practitioner_arn"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
