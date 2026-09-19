"""
Sattvavajaya Chikitsa, Manasa Roga & Mental Health CDSS Engine
==============================================================
Implements:
1. Classical psychiatric disorders registry (Unmada, Apasmara, Chittodvega, Avasada)
2. Triguna Simplex dynamics and Prajnaparadha Index (PPI) calculus
3. Psychiatric crisis triage firewall (suicidal ideation, acute psychosis, violent agitation)
4. Trividha Chikitsa prescription generator (Daiva, Yukti Medhya Rasayana, Sattvavajaya)
5. SQLite WAL persistence with indexed queries
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
from models.manasa_roga import (
    CrisisRiskLevel,
    ManasaAssessmentCreateRequest,
    ManasaAssessmentResponse,
    ManasaDisorderCode,
    ManasaDisorderProfile,
    MentalFacultyScores,
    SattvavajayaPrescriptionCreateRequest,
    SattvavajayaPrescriptionResponse,
    TrigunaVector,
)

# ==============================================================================
# CLASSICAL MANASA ROGA CLASSIFICATION & REGISTRY (8+ CONDITIONS)
# ==============================================================================

SEED_MANASA_ROGA_REGISTRY: List[ManasaDisorderProfile] = [
    ManasaDisorderProfile(
        disorder_code=ManasaDisorderCode.UNMADA_VATAJA,
        sanskrit_name="वातज उन्माद (Vataja Unmada)",
        english_name="Vata Psychosis / Acute Psychomotor Mania with Delusions",
        icd11_mapping="6A20 (Schizophrenia or other primary psychotic disorders)",
        manasa_dosha="Rajas (Hyperkinetic restlessness)",
        sharirika_dosha="Prana & Vyana Vata",
        faculty_impairment=["Dhi (Distorted perception)", "Dhriti (Loss of impulse control)", "Smriti (Fragmented recall)"],
        medhya_rasayana=["शङ्खपुष्पी कल्क (Shankhapushpi)", "कल्याणक घृत (Kalyanaka Ghrita)", "अश्वगन्धा चूर्ण (Ashwagandha with warm milk)", "ब्राह्मी तैल शिरोधारा (Brahmi Taila Shirodhara)"],
        sattvavajaya_modalities=["आश्वासन (Reassurance / supportive psychotherapy)", "धैर्य (Fortitude building)", "संवेगात्मक स्थिरता (Emotional grounding)"],
        emergency_escalation_criteria=["Violent impulsive wandering", "Inability to maintain self-care", "Auditory imperative hallucinations"]
    ),
    ManasaDisorderProfile(
        disorder_code=ManasaDisorderCode.UNMADA_PITTAJA,
        sanskrit_name="पित्तज उन्माद (Pittaja Unmada)",
        english_name="Pittaja Psychosis / Bipolar Manic Aggression",
        icd11_mapping="6A60 (Bipolar type I disorder, current episode manic)",
        manasa_dosha="Rajas (Aggressive irritability)",
        sharirika_dosha="Sadhaka Pitta & Alochaka Pitta",
        faculty_impairment=["Dhriti (Extreme anger / rage outburst)", "Dhi (Paranoid interpretation)"],
        medhya_rasayana=["ब्राह्मी घृत (Brahmi Ghrita)", "सारस्वतारिष्ट (Saraswatarishta)", "तक्रधारा (Sheetala Takradhara)", "चन्दन लेप (Cooling sandalwood on forehead)"],
        sattvavajaya_modalities=["ज्ञान (Cognitive understanding of triggers)", "शीतलोपचार (Cooling behavioral de-escalation)", "अक्रोध अभ्यास (Non-anger cognitive restructuring)"],
        emergency_escalation_criteria=["Physical violence against others", "Destructive rage episodes", "Severe hyperthermia"]
    ),
    ManasaDisorderProfile(
        disorder_code=ManasaDisorderCode.UNMADA_KAPHAJA,
        sanskrit_name="कफज उन्माद (Kaphaja Unmada)",
        english_name="Kaphaja Psychosis / Catatonic Stupor & Depressive Retardation",
        icd11_mapping="6A70 (Single episode depressive disorder with melancholic / catatonic features)",
        manasa_dosha="Tamas (Inertia, morbid lethargy, stupor)",
        sharirika_dosha="Tarpaka Kapha & Avalambaka Kapha",
        faculty_impairment=["Dhi (Profound psychomotor slowing)", "Dhriti (Total apathy)", "Smriti (Hypo-responsiveness)"],
        medhya_rasayana=["वचा चूर्ण (Vacha Churna)", "ज्योतिष्मती तैल (Jyotishmati Nasya)", "पिप्पली रसायन (Pippali Rasayana)", "कट्फल नस्य (Katphala Avapidana Nasya)"],
        sattvavajaya_modalities=["उद्दीपन (Sensory stimulation)", "प्रबोधन (Awakening / structured routine)", "सक्रिय कर्म (Behavioral activation)"],
        emergency_escalation_criteria=["Catatonic refusal to eat/drink", "Total mutism for > 48 hours", "Complete stupor"]
    ),
    ManasaDisorderProfile(
        disorder_code=ManasaDisorderCode.UNMADA_SANNIPATAJA,
        sanskrit_name="सन्निपातज उन्माद (Sannipataja Unmada)",
        english_name="Sannipataja Intractable Psychosis / Chronic Severe Schizophrenia",
        icd11_mapping="6A20.Z (Schizophrenia, continuous / chronic)",
        manasa_dosha="Rajas + Tamas (Severe mixed mental derangement)",
        sharirika_dosha="Tridosha (Vata-Pitta-Kapha vitiation)",
        faculty_impairment=["Complete breakdown of Dhi, Dhriti, and Smriti (Severe Prajnaparadha)"],
        medhya_rasayana=["महाकल्याणक घृत (Maha Kalyanaka Ghrita)", "स्मृतिसागर रस (Smritisagara Rasa)", "पञ्चगव्य घृत (Panchagavya Ghrita)"],
        sattvavajaya_modalities=["दैवव्यपाश्रय (Spiritual sanctuary & safety)", "सतत निरीक्षण (Continuous 24-hr psychiatric observation)"],
        emergency_escalation_criteria=["Active suicidal behaviour", "Homicidal aggression", "Severe self-mutilation"]
    ),
    ManasaDisorderProfile(
        disorder_code=ManasaDisorderCode.APASMARA,
        sanskrit_name="अपस्मार (Apasmara)",
        english_name="Epilepsy / Convulsive Seizure & Dissociative Episodes",
        icd11_mapping="8A60 (Epilepsy and seizures)",
        manasa_dosha="Rajas + Tamas (Paroxysmal clouding of consciousness)",
        sharirika_dosha="Prana Vata, Vyana Vata & Tarpaka Kapha",
        faculty_impairment=["Smriti (Paroxysmal total loss of recall and memory)"],
        medhya_rasayana=["सारस्वत घृत (Saraswata Ghrita)", "ब्राह्मी वटी (Brahmi Vati with Gold)", "शङ्खपुष्पी स्वरस (Shankhapushpi Juice)"],
        sattvavajaya_modalities=["धी-धैर्य-स्मृति पुनर्स्थापन (Cognitive seizure anticipation training)", "भय निवारण (De-stigmatization & panic abatement)"],
        emergency_escalation_criteria=["Status epilepticus (Continuous seizure > 5 min)", "Post-ictal respiratory arrest", "Secondary trauma"]
    ),
    ManasaDisorderProfile(
        disorder_code=ManasaDisorderCode.CHITTODVEGA,
        sanskrit_name="चित्तोद्वेग (Chittodvega)",
        english_name="Generalized Anxiety Disorder / Panic & Autonomic Hyperarousal",
        icd11_mapping="6B00 (Generalized anxiety disorder)",
        manasa_dosha="Rajas (Hyper-vigilance, racing thoughts, panic)",
        sharirika_dosha="Prana Vata & Sadhaka Pitta",
        faculty_impairment=["Dhriti (Loss of calm and emotional composure)", "Dhi (Catastrophic cognitive bias)"],
        medhya_rasayana=["शङ्खपुष्पी सिरप (Shankhapushpi)", "जटामांसी चूर्ण (Jatamansi Kwatha)", "अश्वगन्धारिष्ट (Ashwagandharishta)", "तैल शिरोधारा (Mahanarayana Taila Shirodhara)"],
        sattvavajaya_modalities=["प्राणायाम (Anuloma Viloma & Bhramari)", "योगनिद्रा (Systemic somatic relaxation)", "मनोनिग्रह (Mindfulness & cognitive reframing)"],
        emergency_escalation_criteria=["Acute intractable panic attack with severe chest tightness", "Agoraphobic incapacitation"]
    ),
    ManasaDisorderProfile(
        disorder_code=ManasaDisorderCode.AVASADA,
        sanskrit_name="अवसाद / विषाद (Avasada / Vishada)",
        english_name="Major Depressive Disorder / Anhedonia & Melancholia",
        icd11_mapping="6A71 (Single episode depressive disorder)",
        manasa_dosha="Tamas (Profound gloom, hopelessness, psychomotor inertia)",
        sharirika_dosha="Prana Vata & Tarpaka Kapha",
        faculty_impairment=["Dhi (Cognitive triad of helplessness)", "Dhriti (Avolition)", "Smriti (Ruminative negative recall)"],
        medhya_rasayana=["मण्डूकपर्णी स्वरस (Mandukaparni)", "ज्योतिष्मती बीज (Jyotishmati seeds)", "सुवर्ण वसन्त मालती (Suvarna Vasanta Malati)"],
        sattvavajaya_modalities=["विज्ञान (Analytical challenging of depressive cognitive distortions)", "सत्त्ववर्धन (Sattva amplification)", "उत्साह वर्धन (Motivational interview)"],
        emergency_escalation_criteria=["Active suicidal ideation or gesture", "Severe food refusal", "Psychotic depression"]
    ),
    ManasaDisorderProfile(
        disorder_code=ManasaDisorderCode.ATATTVABHINIVESHA,
        sanskrit_name="अतत्त्वाभिनिवेश (Atattvabhinivesha / Maha-Gada)",
        english_name="Delusional Disorder / Fixed False Obsessive Beliefs",
        icd11_mapping="6A24 (Delusional disorder)",
        manasa_dosha="Rajas + Tamas (Morbid distortion of intellect)",
        sharirika_dosha="Hridaya-ashrita Vata & Pitta",
        faculty_impairment=["Dhi (Perverted judgment: taking unwholesome as wholesome)", "Dhriti (Obstinate adherence to delusion)"],
        medhya_rasayana=["कल्याणक घृत (Kalyanaka Ghrita)", "ब्राह्मी घृत (Brahmi Ghrita)", "अभयारिष्ट (Abhayarishta)"],
        sattvavajaya_modalities=["शास्त्रार्थ संवादन (Gentle reality testing)", "ज्ञान-विज्ञान (Epistemological grounding)", "समाधि (Meditative self-observation)"],
        emergency_escalation_criteria=["Paranoid agitation threatening others", "Dangerous delusions of persecution"]
    ),
    ManasaDisorderProfile(
        disorder_code=ManasaDisorderCode.MADATYAYA,
        sanskrit_name="मदात्यय (Madatyaya)",
        english_name="Substance & Alcohol Dependence / Withdrawal Delirium",
        icd11_mapping="6C40 (Disorders due to use of alcohol)",
        manasa_dosha="Rajas + Tamas (Loss of moral inhibition and judgment)",
        sharirika_dosha="Ojakshaya & Pitta-Vata vitiation",
        faculty_impairment=["Dhriti (Addictive craving)", "Dhi (Impaired risk evaluation)", "Smriti (Blackouts)"],
        medhya_rasayana=["द्राक्षासव (Drakshasava)", "खर्जूर मन्थ (Kharjura Mantha)", "आमलकी रसायन (Amalaki)", "यष्टिमधु (Yashtimadhu)"],
        sattvavajaya_modalities=["आत्मसंयम (Self-regulation training)", "सद्वृत्त पालन (Moral and behavioral rehabilitation)", "सत्संग (Therapeutic supportive community)"],
        emergency_escalation_criteria=["Delirium tremens (Tremors, visual hallucinations, convulsions)", "Severe autonomic instability"]
    ),
]

# ==============================================================================
# DATABASE INITIALIZATION & SEEDING ENGINE
# ==============================================================================

def initialize_manasa_roga_tables(conn: sqlite3.Connection) -> None:
    """Populate manasa_roga_classification_registry if unseeded."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM manasa_roga_classification_registry;")
    row = cursor.fetchone()
    if row and row["cnt"] == 0:
        now = int(time.time())
        for dis in SEED_MANASA_ROGA_REGISTRY:
            cursor.execute(
                """
                INSERT INTO manasa_roga_classification_registry (
                    disorder_code, sanskrit_name, english_name, icd11_mapping,
                    manasa_dosha, sharirika_dosha, faculty_impairment_json,
                    medhya_rasayana_json, sattvavajaya_modalities_json,
                    emergency_escalation_criteria_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    dis.disorder_code.value,
                    dis.sanskrit_name,
                    dis.english_name,
                    dis.icd11_mapping,
                    dis.manasa_dosha,
                    dis.sharirika_dosha,
                    json.dumps(dis.faculty_impairment),
                    json.dumps(dis.medhya_rasayana),
                    json.dumps(dis.sattvavajaya_modalities),
                    json.dumps(dis.emergency_escalation_criteria),
                    now,
                )
            )
        conn.commit()


def get_disorder_profile(disorder_code: str, conn: sqlite3.Connection) -> ManasaDisorderProfile:
    """Retrieve psychiatric disorder profile by code."""
    initialize_manasa_roga_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM manasa_roga_classification_registry WHERE disorder_code = ?;", (disorder_code,))
    row = cursor.fetchone()
    if not row:
        raise RecordNotFoundException("ManasaDisorder", disorder_code)

    return ManasaDisorderProfile(
        disorder_code=ManasaDisorderCode(row["disorder_code"]),
        sanskrit_name=row["sanskrit_name"],
        english_name=row["english_name"],
        icd11_mapping=row["icd11_mapping"],
        manasa_dosha=row["manasa_dosha"],
        sharirika_dosha=row["sharirika_dosha"],
        faculty_impairment=json.loads(row["faculty_impairment_json"]),
        medhya_rasayana=json.loads(row["medhya_rasayana_json"]),
        sattvavajaya_modalities=json.loads(row["sattvavajaya_modalities_json"]),
        emergency_escalation_criteria=json.loads(row["emergency_escalation_criteria_json"]),
    )


def list_all_disorders(conn: sqlite3.Connection) -> List[ManasaDisorderProfile]:
    """List all registered Manasa Rogas."""
    initialize_manasa_roga_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM manasa_roga_classification_registry ORDER BY disorder_code ASC;")
    rows = cursor.fetchall()
    return [
        ManasaDisorderProfile(
            disorder_code=ManasaDisorderCode(r["disorder_code"]),
            sanskrit_name=r["sanskrit_name"],
            english_name=r["english_name"],
            icd11_mapping=r["icd11_mapping"],
            manasa_dosha=r["manasa_dosha"],
            sharirika_dosha=r["sharirika_dosha"],
            faculty_impairment=json.loads(r["faculty_impairment_json"]),
            medhya_rasayana=json.loads(r["medhya_rasayana_json"]),
            sattvavajaya_modalities=json.loads(r["sattvavajaya_modalities_json"]),
            emergency_escalation_criteria=json.loads(r["emergency_escalation_criteria_json"]),
        )
        for r in rows
    ]


# ==============================================================================
# PSYCHOMETRIC EVALUATION, TRIGUNA CALCULUS & CRISIS FIREWALL
# ==============================================================================

def perform_manasa_assessment(
    req: ManasaAssessmentCreateRequest,
    hospital_id: str,
    conn: sqlite3.Connection
) -> ManasaAssessmentResponse:
    """
    Evaluates Triguna simplex dynamics, computes Prajnaparadha Index (PPI),
    executes psychiatric emergency crisis triage, and records baseline in database.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM patients WHERE patient_id = ?;", (req.patient_id,))
    if not cursor.fetchone():
        raise RecordNotFoundException("Patient", req.patient_id)

    # 1. Triguna Normalization
    raw_tot = req.raw_sattva + req.raw_rajas + req.raw_tamas
    if raw_tot <= 0.0:
        norm_s, norm_r, norm_t = 0.34, 0.33, 0.33
    else:
        norm_s = round(req.raw_sattva / raw_tot, 3)
        norm_r = round(req.raw_rajas / raw_tot, 3)
        norm_t = round(req.raw_tamas / raw_tot, 3)

    triguna = TrigunaVector(sattva=norm_s, rajas=norm_r, tamas=norm_t)
    faculties = MentalFacultyScores(
        dhi_score=req.dhi_score,
        dhriti_score=req.dhriti_score,
        smriti_score=req.smriti_score
    )

    # 2. Prajnaparadha Index (PPI) Calculus (0.0 to 100.0%)
    # PPI = 100 * (1 - (Dhi + Dhriti + Smriti) / 30) * (Rajas + Tamas)
    faculties_sum = req.dhi_score + req.dhriti_score + req.smriti_score
    cognitive_deficit = max(0.0, min(1.0, 1.0 - (faculties_sum / 30.0)))
    pathogenic_doshas = norm_r + norm_t
    prajnaparadha_index = round(min(100.0, max(0.0, 100.0 * cognitive_deficit * pathogenic_doshas)), 1)

    # 3. Psychiatric Emergency Crisis Firewall
    crisis_level = CrisisRiskLevel.NONE
    emergency_alert = None

    if req.has_suicidal_ideation:
        crisis_level = CrisisRiskLevel.CRITICAL_EMERGENCY
        emergency_alert = (
            "PSYCHIATRIC EMERGENCY [SUICIDE_FIREWALL]: Active suicidal ideation detected. "
            "Mandatory immediate hospital admission, 1-on-1 bedside surveillance, removal of sharp objects, "
            "and activation of crisis intervention team."
        )
    elif req.has_violent_agitation and (req.has_severe_delusion or req.disorder_code in [ManasaDisorderCode.UNMADA_PITTAJA, ManasaDisorderCode.UNMADA_SANNIPATAJA]):
        crisis_level = CrisisRiskLevel.CRITICAL_EMERGENCY
        emergency_alert = (
            "PSYCHIATRIC EMERGENCY [VIOLENT_MANIA_FIREWALL]: Severe psychomotor aggression with reality loss detected. "
            "Physical safety protocols initiated; patient must be accommodated in a calming low-stimulus room with restraint standby."
        )
    elif req.has_violent_agitation or req.has_severe_delusion or prajnaparadha_index >= 70.0:
        crisis_level = CrisisRiskLevel.MODERATE
    elif prajnaparadha_index >= 40.0:
        crisis_level = CrisisRiskLevel.LOW

    # 4. Clinical Summary Synthesis
    disorder_prof = get_disorder_profile(req.disorder_code.value, conn)
    summary = (
        f"Psychiatric Assessment for {disorder_prof.sanskrit_name} ({disorder_prof.english_name}). "
        f"Triguna Vector: S={norm_s}, R={norm_r}, T={norm_t}. "
        f"Prajnaparadha Index: {prajnaparadha_index}%. Crisis Status: {crisis_level.value}."
    )

    now = int(time.time())
    assessment_id = f"MANASA-{req.patient_id}-{now}-{uuid.uuid4().hex[:6]}"

    # 5. Persist in patient_manasa_assessments
    cursor.execute(
        """
        INSERT INTO patient_manasa_assessments (
            assessment_id, patient_id, hospital_id, triguna_sattva,
            triguna_rajas, triguna_tamas, dhi_score, dhriti_score,
            smriti_score, prajnaparadha_index, primary_manasa_disorder,
            clinical_summary, crisis_risk_level, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            assessment_id,
            req.patient_id,
            hospital_id,
            norm_s,
            norm_r,
            norm_t,
            req.dhi_score,
            req.dhriti_score,
            req.smriti_score,
            prajnaparadha_index,
            req.disorder_code.value,
            summary,
            crisis_level.value,
            now,
        )
    )
    conn.commit()

    return ManasaAssessmentResponse(
        assessment_id=assessment_id,
        patient_id=req.patient_id,
        triguna=triguna,
        faculties=faculties,
        prajnaparadha_index=prajnaparadha_index,
        primary_manasa_disorder=req.disorder_code,
        crisis_risk_level=crisis_level,
        emergency_alert=emergency_alert,
        clinical_summary=summary,
        assessed_by_arn=req.assessed_by_arn,
        created_at=now,
    )


# ==============================================================================
# TRIVIDHA CHIKITSA PRESCRIPTION SYNTHESIS ENGINE
# ==============================================================================

def create_sattvavajaya_prescription(
    req: SattvavajayaPrescriptionCreateRequest,
    hospital_id: str,
    conn: sqlite3.Connection
) -> SattvavajayaPrescriptionResponse:
    """
    Formulates a comprehensive Trividha Chikitsa plan:
    1. Daivavyapashraya: Mantra, Swastyayana, Mani-dharana, Upavasa
    2. Yuktivyapashraya: Medhya Rasayanas (Shankhapushpi, Brahmi Ghrita, Saraswatarishta)
    3. Sattvavajaya: Mano-nigraha, Jnana-Vijnana, Dhairya, cognitive restructuring
    """
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patient_manasa_assessments WHERE assessment_id = ?;", (req.assessment_id,))
    assessment_row = cursor.fetchone()
    if not assessment_row:
        raise RecordNotFoundException("ManasaAssessment", req.assessment_id)

    disorder_code_str = assessment_row["primary_manasa_disorder"]
    disorder_prof = get_disorder_profile(disorder_code_str, conn)

    daiva_therapies: List[str] = []
    if req.include_daivavyapashraya:
        daiva_therapies = [
            "मन्त्र जप (Chanting of soothing Gayatree and Maha-Mrityunjaya mantras)",
            "स्वस्त्ययन एवं मङ्गल कर्म (Auspicious supportive affirmations and daily prayers)",
            "प्रणिधान (Surrender to higher conscious power / spiritual sanctuary)",
            "मणि-औषध धारण (Wearing sanctified Brahmi/Pearl gemstones for Pitta/Manas pacification)"
        ]

    yukti_medhya: List[str] = []
    if req.include_yukti_medhya:
        yukti_medhya = list(disorder_prof.medhya_rasayana)

    sattvavajaya_cbt: List[str] = []
    if req.include_sattvavajaya_cbt:
        sattvavajaya_cbt = [
            "अहितेभ्योऽर्थेभ्यो मनोनिग्रहः (Mano-nigraha: Deliberate cognitive withdrawal from unwholesome stimuli)",
            "ज्ञान एवं विज्ञान (Self-knowledge and analytical challenging of cognitive distortions)",
            "धैर्य (Cultivation of fortitude, resilience, and emotional impulse retention)",
            "स्मृति (Recollection of past wholesome victories and ethical consequences)",
            "समाधि (Daily 20-minute seated silent meditation / Pratyahara practice)"
        ]

    contraindications = [
        "Ratri Jagarana (Staying awake past 10 PM exacerbates Rajas & Vata)",
        "Tamasic Ahara (Stale, decomposed, excessively heavy, fermented foods strictly avoided)",
        "Sensory flooding (Overexposure to violent media, rapid flashing screens, abrasive sounds)"
    ]

    prognosis = (
        f"Sadhya (Manageable) with systematic Trividha Chikitsa adherence. "
        f"Target: Increase Sattva Guna by > 20% and reduce Prajnaparadha Index to < 30% over 8 weeks."
    )

    now = int(time.time())
    prescription_id = f"RX-SATTVA-{req.patient_id}-{now}-{uuid.uuid4().hex[:6]}"

    # Persist in patient_sattvavajaya_prescriptions
    cursor.execute(
        """
        INSERT INTO patient_sattvavajaya_prescriptions (
            prescription_id, assessment_id, patient_id, hospital_id,
            daivavyapashraya_json, yukti_medhya_rasayana_json,
            sattvavajaya_interventions_json, prescribed_by_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            prescription_id,
            req.assessment_id,
            req.patient_id,
            hospital_id,
            json.dumps(daiva_therapies),
            json.dumps(yukti_medhya),
            json.dumps(sattvavajaya_cbt),
            req.prescribed_by_arn,
            now,
        )
    )
    conn.commit()

    return SattvavajayaPrescriptionResponse(
        prescription_id=prescription_id,
        assessment_id=req.assessment_id,
        patient_id=req.patient_id,
        daivavyapashraya_therapies=daiva_therapies,
        yukti_medhya_rasayanas=yukti_medhya,
        sattvavajaya_cbt_interventions=sattvavajaya_cbt,
        contraindicated_factors=contraindications,
        clinical_prognosis=prognosis,
        prescribed_by_arn=req.prescribed_by_arn,
        created_at=now,
    )
