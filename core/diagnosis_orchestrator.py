"""Unified Clinical Diagnostic & Decision Support Orchestrator (A-CDSS).

Integrates all 33 diagnostic and therapeutic modules into a cohesive,
end-to-end clinical workflow supporting:
1. Multi-modular diagnostic synthesis (Prakriti-Vikriti, Ashtavidha, Ama-Agni, Srotas, Dhatu Sarata).
2. Dual-coding interoperability (Ayurvedic classical, NAMASTE Portal, WHO ICD-11 TM2).
3. Shat Kriya Kala staging and Rogi Bala grading.
4. Comprehensive treatment formulation (Shamana, Shodhana gating, Pathya/Apathya, Swasthavritta, Upakarma/Marma referral).
5. Statutory Human-in-the-Loop governance under NCISM Act 2020.
"""
import json
import math
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from core.database import append_audit_log, get_sqlite_connection
from core.exceptions import IncompleteClinicalIntakeException, RedFlagEmergencyException
from core.emergency_transfer import (
    EmergencyBreakGlassRequest,
    EmergencyTriggerReason,
    VitalSignsTelemetry,
    trigger_emergency_break_glass,
)
from models.diagnosis_orchestrator import (
    AgniStatus,
    AmaStatus,
    ClinicalIntakeData,
    ComprehensiveTreatmentPlan,
    CounterSignRequest,
    DiagnosisEpisodeResponse,
    DualMorbidityCode,
    EvidenceAttribution,
    EvidenceRankingLevel,
    GenericSubstitution,
    GovernanceStatus,
    PrescribedFormulation,
    RankedDifferentialItem,
    RedFlagScreeningResult,
    RogiBalaGrade,
    ShatKriyaKalaStage,
    ShodhanaEligibility,
)

# -------------------------------------------------------------------------
# Classical Morbidity Knowledge Base & Disease Profiles
# -------------------------------------------------------------------------

CLASSICAL_DISEASE_PROFILES: Dict[str, Dict[str, Any]] = {
    "AMAVATA": {
        "sanskrit_name": "Amavata",
        "namaste_code": "AYU-ROGA-AMA-001",
        "icd11_tm2_code": "FA20.Z",
        "icd11_title": "Rheumatoid arthritis, unspecified (correlated with Amavata)",
        "key_symptoms": [
            "joint pain", "morning stiffness", "sandhi-shula", "stambha",
            "shotha", "swelling", "angamarda", "body ache", "aruchi", "loss of appetite",
            "jvara", "feverish sensation", "gaurava", "heaviness in joints"
        ],
        "predominant_doshas": {"VATA": 0.50, "KAPHA": 0.40, "PITTA": 0.10},
        "vitiated_srotases": ["ANNAVAHA", "RASAVAHA", "ASTHIVAHA"],
        "vitiated_dhatus": ["RASA", "ASTHI", "MAJJA"],
        "typical_agni": AgniStatus.MANDAGNI,
        "typical_ama": AmaStatus.SAMA,
        "shamana_formulations": [
            {
                "formulation_name": "Rasna Saptaka Kwatha",
                "kalpana_form": "Kwatha",
                "dosage": "40 mL twice daily",
                "timing": "Before meals (Pragbhakta)",
                "anupana": "Warm water with 1 pinch of Shunthi Churna",
                "classical_reference": "Chakradatta, Amavata Chikitsa",
                "target_pathology": "Alleviates Vata-Kapha accumulation in joint capsules and relieves severe stiffness."
            },
            {
                "formulation_name": "Simhanada Guggulu",
                "kalpana_form": "Vati",
                "dosage": "2 tablets (500 mg each) twice daily",
                "timing": "After meals (Pashchatbhakta)",
                "anupana": "Warm water (Ushnodaka)",
                "classical_reference": "Bhaishajya Ratnavali, Amavata Rogadhikara",
                "target_pathology": "Contains Shuddha Gandhasa and Triphala; digests Ama, opens micro-channels, and detoxifies synovial fluid."
            },
            {
                "formulation_name": "Valuka Sweda (Sand fomentation)",
                "kalpana_form": "Upakarma",
                "dosage": "Local application for 20 minutes daily",
                "timing": "Morning or Evening",
                "anupana": "Dry sand bolus (Ruksha Sweda)",
                "classical_reference": "Charaka Samhita Sutrasthana Ch. 14",
                "target_pathology": "Ruksha Sweda digests local Ama in swollen joints without aggravating Kapha."
            }
        ],
        "pathya_ahara": [
            "Purana Shali (Old aged rice)",
            "Yava (Barley)",
            "Kulattha (Horse gram soup)",
            "Shigru (Drumstick)",
            "Karela (Bitter gourd)",
            "Ardraka / Shunthi (Fresh / Dry ginger)",
            "Ushnodaka (Boiled warm water)"
        ],
        "apathya_ahara": [
            "Dadhi (Curd / Yogurt)",
            "Masha (Black gram)",
            "Matsya (Fish / Seafood)",
            "Sheetala Jala (Cold refrigerated water)",
            "Viruddhahara (Incompatible food combinations like milk + fruit)",
            "Guru and Abhishyandi ahara (Heavy, canal-clogging foods)"
        ],
        "swasthavritta_vihara": [
            "Strict avoidance of daytime sleep (Divasvapna)",
            "Avoid exposure to cold winds and damp basements",
            "Gentle active joint mobilization within pain tolerance",
            "Hot water bathing only"
        ],
        "parasurgical_referral": "Valuka Sweda locally; once Nirama stage is verified, Janu/Kati Basti with Sahacharadi Taila.",
        "vyavachhedaka_lakshana": "Migratory polyarthritis (Sarva Sandhi Vedana) with pronounced morning stiffness (Stambha), feverish heaviness (Gaurava/Jvara), and Sama tongue coating, lacking the bony crepitus of Sandhivata or acute monoarticular Podagra of Vatarakta."
    },
    "PRAMEHA": {
        "sanskrit_name": "Prameha (Madhumeha)",
        "namaste_code": "AYU-ROGA-PRA-002",
        "icd11_tm2_code": "5A11",
        "icd11_title": "Type 2 diabetes mellitus (correlated with Madhumeha)",
        "key_symptoms": [
            "polyuria", "prabhuta mutrata", "turbid urine", "avila mutrata",
            "excessive thirst", "trishna", "sweet taste in mouth", "burning sensation",
            "kara-pada daha", "alasya", "lethargy", "sweet smelling urine", "weight gain"
        ],
        "predominant_doshas": {"KAPHA": 0.55, "VATA": 0.35, "PITTA": 0.10},
        "vitiated_srotases": ["MUTRAVAHA", "MEDOVAHA"],
        "vitiated_dhatus": ["MEDAS", "KLEDA", "MAMSA", "SHUKRA", "OJAS"],
        "typical_agni": AgniStatus.VISHAMAGNI,
        "typical_ama": AmaStatus.SAMA,
        "shamana_formulations": [
            {
                "formulation_name": "Nishamalaki Churna",
                "kalpana_form": "Churna",
                "dosage": "3 grams twice daily",
                "timing": "Before meals (Pragbhakta)",
                "anupana": "Lukewarm water or Honey in small quantity",
                "classical_reference": "Ashtanga Hridaya, Prameha Chikitsa",
                "target_pathology": "Haridra (Curcuma longa) and Amalaki (Emblica officinalis) synergistically reduce urinary turbidity and blood glucose."
            },
            {
                "formulation_name": "Chandraprabha Vati",
                "kalpana_form": "Vati",
                "dosage": "2 tablets (500 mg each) twice daily",
                "timing": "After meals (Pashchatbhakta)",
                "anupana": "Warm water or Asanadi Kwatha",
                "classical_reference": "Sharangadhara Samhita Madhyama Khanda",
                "target_pathology": "Strengthens Mutravaha Srotas, reduces albuminuria, and revitalizes renal microvasculature."
            }
        ],
        "pathya_ahara": [
            "Yava (Barley grains and chapatis)",
            "Mudga (Green gram)",
            "Tikta Shaka (Bitter leafy vegetables like Methi, Karela)",
            "Purana Godhuma (Aged wheat)",
            "Amalaki (Indian gooseberry)",
            "Jamun (Syzygium cumini) seed powder"
        ],
        "apathya_ahara": [
            "Navanna (Freshly harvested grains)",
            "Guda (Jaggery) and refined sugars",
            "Dadhi (Curd)",
            "Anupa Mamsa (Meat of marshy animals)",
            "Excessive sweet fruits and dairy milkshakes"
        ],
        "swasthavritta_vihara": [
            "Daily brisk walking of 5,000 - 10,000 steps (Padachankramana)",
            "Regular practice of Paschimottanasana and Mandukasana",
            "Avoid sedentary daytime sleeping"
        ],
        "parasurgical_referral": "Udvartana (Dry herbal powder massage with Kolakulathadi Churna) to reduce sub-cutaneous Medas.",
        "vyavachhedaka_lakshana": "Prabhuta Avila Mutrata (profuse turbid urination) with Madhuryam (glucosuria/sweetness attracting ants) and systemic Kleda/Medas vitiation, distinguished from Mutrakrichhra by painless high-volume diuresis."
    },
    "TAMAKA_SHWASA": {
        "sanskrit_name": "Tamaka Shwasa",
        "namaste_code": "AYU-ROGA-SHW-003",
        "icd11_tm2_code": "CA23",
        "icd11_title": "Asthma (correlated with Tamaka Shwasa)",
        "key_symptoms": [
            "breathlessness", "dyspnea", "shwasa kashtata", "wheezing",
            "ghurghuruka", "cough", "kasa", "chest tightness", "urah-peeda",
            "orthopnea", "sitting up for relief", "aggravated by cold", "meghambu-sheeta"
        ],
        "predominant_doshas": {"VATA": 0.50, "KAPHA": 0.45, "PITTA": 0.05},
        "vitiated_srotases": ["PRANAVAHA", "UDAKAVAHA", "ANNAVAHA"],
        "vitiated_dhatus": ["RASA", "PRANA"],
        "typical_agni": AgniStatus.MANDAGNI,
        "typical_ama": AmaStatus.SAMA,
        "shamana_formulations": [
            {
                "formulation_name": "Shvasa Kuthar Rasa",
                "kalpana_form": "Rasaushadhi (Bhasma/Kharaliya)",
                "dosage": "125 mg twice daily",
                "timing": "After meals",
                "anupana": "Honey (Madhu) or Ginger juice (Ardraka Svarasa)",
                "classical_reference": "Bhaishajya Ratnavali, Hikka-Shwasa Rogadhikara",
                "target_pathology": "Quickly liquefies bronchial Kapha and clears Pranavaha Srotas obstruction."
            },
            {
                "formulation_name": "Kantakari Avaleha",
                "kalpana_form": "Avaleha",
                "dosage": "10 grams twice daily",
                "timing": "Before bedtime and morning",
                "anupana": "Warm milk or warm water",
                "classical_reference": "Charaka Samhita Chikitsasthana Ch. 18",
                "target_pathology": "Bronchodilator and mucolytic herbal compound pacifying Vata-Kapha in the chest."
            }
        ],
        "pathya_ahara": [
            "Purana Shali and Godhuma",
            "Kulattha Yusha (Horse gram soup with Pippali)",
            "Lashuna (Garlic cooked in soups)",
            "Ardraka and Maricha (Black pepper)",
            "Boiled warm water for drinking"
        ],
        "apathya_ahara": [
            "Cold drinks, refrigerated foods, and ice creams",
            "Heavy dairy curds and paneer",
            "Masha (Black gram) and heavy unctuous sweets",
            "Exposure to dust, smoke (Raja-Dhuma), and cold air currents"
        ],
        "swasthavritta_vihara": [
            "Pranayama (Anuloma-Viloma, Ujjayi, Bhastrika)",
            "Warm oil chest application (Lavana-Tila taila) followed by warm fomentation",
            "Always keep neck and chest covered in cold weather"
        ],
        "parasurgical_referral": "Vamana Karma (therapeutic emesis) in Spring (Vasanta) or when Kapha is strongly localized in chest.",
        "vyavachhedaka_lakshana": "Paroxysmal nocturnal dyspnea relieved specifically by upright sitting posture (Aasino labhate saukhyam) with audible wheezing (Ghurghuruka) and difficult expectoration of sticky Kapha."
    },
    "GRIDHRASI": {
        "sanskrit_name": "Gridhrasi",
        "namaste_code": "AYU-ROGA-GRI-004",
        "icd11_tm2_code": "8B92",
        "icd11_title": "Sciatica (correlated with Gridhrasi)",
        "key_symptoms": [
            "sciatica", "radiating leg pain", "sphik-kati-uru-pada vedana", "shooting pain",
            "suptata", "numbness", "tingling", "stiff lower back", "kampa",
            "difficulty walking", "restricted straight leg raise", "sakthi utkshepa nigraha"
        ],
        "predominant_doshas": {"VATA": 0.70, "KAPHA": 0.25, "PITTA": 0.05},
        "vitiated_srotases": ["ASTHIVAHA", "MAJJAVAHA"],
        "vitiated_dhatus": ["ASTHI", "MAJJA", "SNAYU", "KANDARA"],
        "typical_agni": AgniStatus.VISHAMAGNI,
        "typical_ama": AmaStatus.NIRAMA,
        "shamana_formulations": [
            {
                "formulation_name": "Trayodashanga Guggulu",
                "kalpana_form": "Vati",
                "dosage": "2 tablets (500 mg each) twice daily",
                "timing": "After meals",
                "anupana": "Warm water or Balarishta (15 mL)",
                "classical_reference": "Bhaishajya Ratnavali, Vatavyadhi Rogadhikara",
                "target_pathology": "Nourishes Asthi-Majja Dhatus, pacifies aggravated Vyana and Apana Vayu in lumbosacral nerve roots."
            },
            {
                "formulation_name": "Rasna Saptaka Kwatha",
                "kalpana_form": "Kwatha",
                "dosage": "40 mL twice daily",
                "timing": "Before meals",
                "anupana": "Warm water with 5 mL Eranda Taila (Castor oil)",
                "classical_reference": "Chakradatta, Vatavyadhi Chikitsa",
                "target_pathology": "Anulomana of Apana Vayu, relieving neuromuscular spasms in the sciatic nerve distribution."
            }
        ],
        "pathya_ahara": [
            "Purana Godhuma and Shali",
            "Masha cooked with Hingu and Jeeraka",
            "Lashuna Ksheera Paka (Garlic boiled in milk)",
            "Ghee (Ghrita) and unctuous warm soups",
            "Draksha and Dadima"
        ],
        "apathya_ahara": [
            "Vatala ahara: Chanaka (chickpeas), dry roasted foods, raw salads",
            "Cold refrigerated drinks",
            "Excessive astringent or pungent snacks",
            "Prolonged fasting (Anashana)"
        ],
        "swasthavritta_vihara": [
            "Avoid lifting heavy weights bending forward",
            "Firm mattress for sleeping; avoid excessive soft sinking beds",
            "Gentle lumbar traction and Bhujangasana under guidance"
        ],
        "parasurgical_referral": "Kati Basti with Sahacharadi Taila / Mahanarayana Taila for 7 consecutive days; Siravedha at Janu/Gulpha Sandhi.",
        "vyavachhedaka_lakshana": "Shooting radicular pain originating in hip/gluteal region (Sphik) radiating sequentially through Kati, Uru, Janu, Jangha down to Pada with positive Sakthi Utkshepa Nigraha (Straight Leg Raise limitation)."
    },
    "SANDHIVATA": {
        "sanskrit_name": "Sandhivata",
        "namaste_code": "AYU-ROGA-SAN-005",
        "icd11_tm2_code": "FA00",
        "icd11_title": "Osteoarthritis (correlated with Sandhivata)",
        "key_symptoms": [
            "crepitus", "sandhi-sphutana", "joint cracking", "osteoarthritis",
            "joint pain on movement", "sandhi-shula", "stiffness after resting",
            "sandhi-stambha", "joint enlargement", "absence of fever", "dry joint sensation"
        ],
        "predominant_doshas": {"VATA": 0.85, "PITTA": 0.10, "KAPHA": 0.05},
        "vitiated_srotases": ["ASTHIVAHA"],
        "vitiated_dhatus": ["ASTHI", "MAJJA"],
        "typical_agni": AgniStatus.SAMAGNI,
        "typical_ama": AmaStatus.NIRAMA,
        "shamana_formulations": [
            {
                "formulation_name": "Yogaraja Guggulu",
                "kalpana_form": "Vati",
                "dosage": "2 tablets (500 mg each) twice daily",
                "timing": "After meals",
                "anupana": "Warm water or Dashamoola Kwatha",
                "classical_reference": "Bhaishajya Ratnavali, Vatavyadhi Rogadhikara",
                "target_pathology": "Strengthens articular cartilage, replenishes depleted Sleshaka Kapha, and pacifies degenerative Vayu."
            },
            {
                "formulation_name": "Shallaki (Boswellia serrata) Capsules",
                "kalpana_form": "Extract Vati",
                "dosage": "1 capsule (500 mg) twice daily",
                "timing": "After food",
                "anupana": "Warm water",
                "classical_reference": "Dravyaguna Vijnana",
                "target_pathology": "Inhibits 5-lipoxygenase and protects cartilage degradation in weight-bearing joints."
            }
        ],
        "pathya_ahara": [
            "Godhuma and Shali with generous Ghee (Ghrita)",
            "Dugdha (Warm milk with Ashwagandha)",
            "Taila (Sesame oil used in cooking)",
            "Sweet and nourishing seasonal fruits"
        ],
        "apathya_ahara": [
            "Dry, light, cold foods (Ruksha-Sheeta ahara)",
            "Excessive bitter and astringent raw food",
            "Skipping meals"
        ],
        "swasthavritta_vihara": [
            "Daily self-abhyanga with Tila Taila or Mahanarayana Taila",
            "Mild isometric quadriceps strengthening exercises",
            "Avoid squatting or sitting cross-legged on the floor for extended periods"
        ],
        "parasurgical_referral": "Janu Basti with Ksheerabala 101 Taila for 7 days followed by Patra Pinda Sweda.",
        "vyavachhedaka_lakshana": "Sandhi-Sphutana (audible joint crepitus upon articulation) with Vata-Purna Driti Sparsha (boggy/crepitant swelling like air-filled bag) without systemic fever or sticky morning coating (Nirama)."
    }
}


# -------------------------------------------------------------------------
# Core Diagnostic Synthesis Engine
# -------------------------------------------------------------------------

def match_morbidity_profile(
    chief_complaints: List[str],
    symptoms: List[str]
) -> List[Tuple[str, float]]:
    """Score clinical presentation against classical disease knowledge base."""
    combined_tokens = " ".join(chief_complaints + symptoms).lower()
    scores = []

    for dis_key, prof in CLASSICAL_DISEASE_PROFILES.items():
        match_count = 0
        total_keywords = len(prof["key_symptoms"])
        for kw in prof["key_symptoms"]:
            if kw.lower() in combined_tokens:
                match_count += 1

        score = match_count / max(1, total_keywords)
        # Weight boost for exact Sanskrit matches
        if prof["sanskrit_name"].lower() in combined_tokens:
            score = min(1.0, score + 0.35)

        scores.append((dis_key, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def derive_vikriti_vector(
    intake: ClinicalIntakeData,
    matched_profile: Dict[str, Any]
) -> Tuple[Dict[str, float], float]:
    """Calculate the patient's Vikriti barycentric vector on 2-simplex Delta^2 and divergence from Prakriti."""
    # If explicit vector provided, use it
    if intake.vikriti_vector:
        v_vec = intake.vikriti_vector
    else:
        # Synthesize from matched profile and clinical signs
        v_vec = dict(matched_profile["predominant_doshas"])
        if intake.nadi_gati:
            if "sarpa" in intake.nadi_gati.lower():
                v_vec["VATA"] = min(0.90, v_vec.get("VATA", 0.33) + 0.15)
            elif "manduka" in intake.nadi_gati.lower():
                v_vec["PITTA"] = min(0.90, v_vec.get("PITTA", 0.33) + 0.15)
            elif "hamsa" in intake.nadi_gati.lower():
                v_vec["KAPHA"] = min(0.90, v_vec.get("KAPHA", 0.33) + 0.15)

    # Normalize on Delta^2 simplex
    total = sum(v_vec.values())
    if total > 0:
        v_vec = {k: round(v / total, 3) for k, v in v_vec.items()}
    else:
        v_vec = {"VATA": 0.333, "PITTA": 0.333, "KAPHA": 0.334}

    # Calculate Euclidean / Mahalanobis divergence from baseline Prakriti
    p_vec = intake.prakriti_vector or {"VATA": 0.333, "PITTA": 0.333, "KAPHA": 0.334}
    divergence = math.sqrt(
        (v_vec.get("VATA", 0.333) - p_vec.get("VATA", 0.333)) ** 2 +
        (v_vec.get("PITTA", 0.333) - p_vec.get("PITTA", 0.333)) ** 2 +
        (v_vec.get("KAPHA", 0.334) - p_vec.get("KAPHA", 0.334)) ** 2
    )

    return v_vec, round(divergence, 3)


def determine_ama_and_agni(intake: ClinicalIntakeData, matched_profile: Dict[str, Any]) -> Tuple[AmaStatus, AgniStatus]:
    """Evaluate metabolic Ama presence and Jatharagni functional state."""
    # Jihwa coating is a primary clinical determinant of Ama
    if intake.jihwa_coating:
        coating_lower = intake.jihwa_coating.lower()
        if "thick" in coating_lower or "white" in coating_lower or "slimy" in coating_lower or "sama" in coating_lower:
            ama = AmaStatus.SAMA
        else:
            ama = AmaStatus.NIRAMA
    else:
        ama = matched_profile.get("typical_ama", AmaStatus.SAMA)

    # Appetite & digestion evaluation
    if intake.appetite_and_digestion:
        app_lower = intake.appetite_and_digestion.lower()
        if "poor" in app_lower or "manda" in app_lower:
            agni = AgniStatus.MANDAGNI
        elif "variable" in app_lower or "vishama" in app_lower:
            agni = AgniStatus.VISHAMAGNI
        elif "intense" in app_lower or "tikshna" in app_lower:
            agni = AgniStatus.TIKSHNAGNI
        else:
            agni = AgniStatus.SAMAGNI
    else:
        agni = matched_profile.get("typical_agni", AgniStatus.MANDAGNI)

    return ama, agni


def evaluate_shat_kriya_kala(duration_weeks: float, symptoms: List[str]) -> ShatKriyaKalaStage:
    """Stage pathogenesis across the 6 Kriya Kalas according to chronicity and tissue depth."""
    s_tokens = " ".join(symptoms).lower()
    if duration_weeks > 12.0 or "deformity" in s_tokens or "bheda" in s_tokens or "ulceration" in s_tokens:
        return ShatKriyaKalaStage.BHEDAVASTHA
    elif duration_weeks >= 4.0 or "swelling" in s_tokens or "radiating" in s_tokens:
        return ShatKriyaKalaStage.VYAKTI
    elif duration_weeks >= 2.0:
        return ShatKriyaKalaStage.STHANA_SAMSHRAYA
    elif duration_weeks >= 1.0:
        return ShatKriyaKalaStage.PRASARA
    else:
        return ShatKriyaKalaStage.PRAKOPA


def validate_intake_completeness(intake: ClinicalIntakeData) -> Tuple[bool, List[str]]:
    """
    Validate that mandatory physiological vitals and clinical parameters are present (C1).
    Prohibits silent imputation unless explicit preliminary assessment override is granted.
    """
    missing = []
    if intake.systolic_bp is None:
        missing.append("systolic_bp")
    if intake.diastolic_bp is None:
        missing.append("diastolic_bp")
    if intake.rogi_bala is None:
        missing.append("rogi_bala")
    if intake.hemoglobin_g_dl is None:
        missing.append("hemoglobin_g_dl")
    if intake.is_pregnant is None:
        missing.append("is_pregnant")
    if intake.age_years is None:
        missing.append("age_years")

    if missing:
        if intake.allow_preliminary_assessment and intake.emergency_override_rationale:
            return False, missing
        raise IncompleteClinicalIntakeException(missing_fields=missing)
    return True, []


def screen_red_flag_mimics(intake: ClinicalIntakeData) -> RedFlagScreeningResult:
    """
    Screen patient intake against 5 can't-miss Western surgical and medical emergency mimics (M1).
    Prohibits elective Ayurvedic therapy if acute cauda equina, myocardial infarction,
    diabetic ketoacidosis, septic arthritis, or colorectal malignancy mimic is detected.
    """
    tokens = " ".join((intake.chief_complaints or []) + (intake.symptoms or [])).lower()
    vital_triggers = []

    # Check vitals if available
    if intake.systolic_bp is not None:
        if intake.systolic_bp < 90:
            vital_triggers.append(f"Severe hypotension (SBP {intake.systolic_bp} mmHg < 90 mmHg)")
        elif intake.systolic_bp > 200:
            vital_triggers.append(f"Hypertensive crisis (SBP {intake.systolic_bp} mmHg > 200 mmHg)")

    if intake.spo2_percentage is not None and intake.spo2_percentage < 90.0:
        vital_triggers.append(f"Severe hypoxia (SpO2 {intake.spo2_percentage}% < 90%)")

    if intake.respiratory_rate_bpm is not None and intake.respiratory_rate_bpm > 30:
        vital_triggers.append(f"Severe tachypnea (RR {intake.respiratory_rate_bpm} /min > 30)")

    if intake.heart_rate_bpm is not None and (intake.heart_rate_bpm > 130 or intake.heart_rate_bpm < 40):
        vital_triggers.append(f"Critical arrhythmia risk (Pulse {intake.heart_rate_bpm} bpm)")

    # 1. Gridhrasi Mimic -> Cauda Equina Syndrome
    cauda_markers = [
        "saddle anesthesia", "saddle numbness", "perineal numbness", "loss of bowel control",
        "fecal incontinence", "urinary retention", "bladder incontinence", "loss of sphincter tone",
        "bilateral leg weakness", "progressive paraparesis", "cauda equina"
    ]
    if any(m in tokens for m in cauda_markers):
        return RedFlagScreeningResult(
            mimic_detected=True,
            suspected_syndrome="Cauda Equina Syndrome (Emergency Spinal Cord/Root Compression)",
            presenting_mimic="Gridhrasi (Sciatica)",
            critical_action_required="IMMEDIATE SPINAL SURGICAL CONSULTATION & STAT MRI LUMBOSACRAL SPINE WITHIN 24 HOURS. All elective Panchakarma / Kati Basti prohibited.",
            vital_triggers=vital_triggers,
            emergency_facility_type="Tertiary Neurosurgical & Spinal Emergency Centre"
        )

    # 2. Tamaka Shwasa Mimic -> Acute Left Ventricular Failure / Acute MI
    cardiac_markers = [
        "pink frothy sputum", "bilateral crepitations", "bilateral crackles",
        "crushing chest pain", "substernal crushing", "pain radiating to jaw",
        "pain radiating to left arm", "acute pulmonary edema", "myocardial infarction"
    ]
    if any(m in tokens for m in cardiac_markers) or (
        ("breathlessness" in tokens or "shwasa" in tokens or "dyspnea" in tokens)
        and (len(vital_triggers) > 0 and any("hypoxia" in v or "hypotension" in v for v in vital_triggers))
    ):
        return RedFlagScreeningResult(
            mimic_detected=True,
            suspected_syndrome="Acute Left Ventricular Failure / Acute Coronary Syndrome",
            presenting_mimic="Tamaka Shwasa (Bronchial Asthma)",
            critical_action_required="STAT CARDIAC EVALUATION, 12-LEAD ECG, TROPONIN I, HIGH-FLOW OXYGEN, AND EMERGENCY ICU TRANSFER.",
            vital_triggers=vital_triggers,
            emergency_facility_type="Cardiology Critical Care Unit (CCU)"
        )

    # 3. Prameha Mimic -> Diabetic Ketoacidosis (DKA) / HHS
    dka_markers = [
        "kussmaul", "acetone breath", "fruity breath", "fruity odor",
        "diabetic ketoacidosis", "dka", "hyperosmolar hyperglycemic",
        "persistent vomiting with thirst", "altered consciousness with hyperglycemia"
    ]
    if any(m in tokens for m in dka_markers):
        return RedFlagScreeningResult(
            mimic_detected=True,
            suspected_syndrome="Diabetic Ketoacidosis (DKA) / Hyperosmolar Hyperglycemic State (HHS)",
            presenting_mimic="Prameha (Madhumeha)",
            critical_action_required="STAT ARTERIAL BLOOD GAS (ABG), URINARY KETONES, IV FLUID RESUSCITATION WITH NORMAL SALINE & REGULAR INSULIN INFUSION IN MEDICAL ICU.",
            vital_triggers=vital_triggers,
            emergency_facility_type="Medical Intensive Care Unit (MICU)"
        )

    # 4. Amavata / Sandhivata Mimic -> Acute Septic Arthritis
    septic_markers = [
        "acute monoarthritis", "single red swollen joint", "septic joint",
        "septic arthritis", "intense local heat with high fever", "chills with swollen joint"
    ]
    is_high_fever = intake.temperature_fahrenheit is not None and intake.temperature_fahrenheit >= 101.5
    if any(m in tokens for m in septic_markers) or (is_high_fever and ("joint pain" in tokens or "sandhi" in tokens) and "swelling" in tokens):
        return RedFlagScreeningResult(
            mimic_detected=True,
            suspected_syndrome="Acute Septic Arthritis",
            presenting_mimic="Amavata / Sandhivata",
            critical_action_required="STAT DIAGNOSTIC ARTHROCENTESIS (SYNOVIAL GRAM STAIN, CELL COUNT, CULTURE) & EMPIRICAL PARENTERAL ANTIBIOTICS. Urgent Orthopedic referral.",
            vital_triggers=vital_triggers,
            emergency_facility_type="Emergency Orthopedic Surgery Unit"
        )

    # 5. Arsha / Bhagandara Mimic -> Colorectal Malignancy
    colorectal_markers = [
        "painless rectal bleeding", "unexplained weight loss", "altered bowel habit > 6 weeks",
        "tenesmus with palpable mass", "rectal mass", "cachexia with rectal bleeding", "colorectal malignancy"
    ]
    if any(m in tokens for m in colorectal_markers):
        return RedFlagScreeningResult(
            mimic_detected=True,
            suspected_syndrome="Suspected Colorectal Malignancy / Lower Gastrointestinal Hemorrhage",
            presenting_mimic="Arsha / Bhagandara (Hemorrhoids / Fistula-in-Ano)",
            critical_action_required="URGENT GASTROENTEROLOGY REFERRAL, LOWER GI COLONOSCOPY & TISSUE BIOPSY BEFORE ANY KSHARA SUTRA OR PARASURGICAL INTERVENTION.",
            vital_triggers=vital_triggers,
            emergency_facility_type="Surgical Gastroenterology / Oncology Unit"
        )

    # Check standalone hemodynamic collapse
    if len(vital_triggers) > 0 and any("hypotension" in v or "hypoxia" in v for v in vital_triggers):
        return RedFlagScreeningResult(
            mimic_detected=True,
            suspected_syndrome="Acute Hemodynamic / Respiratory Decompensation",
            presenting_mimic="Undifferentiated Acute Presentation",
            critical_action_required="STAT RESUSCITATION & IMMEDIATE NABH COP.6 BREAK-GLASS ICU TRANSFER.",
            vital_triggers=vital_triggers,
            emergency_facility_type="Apex Intensive Care Unit (ICU)"
        )

    return RedFlagScreeningResult(mimic_detected=False, vital_triggers=vital_triggers)


def check_clinical_safety_firewalls(intake: ClinicalIntakeData, ama: AmaStatus) -> Tuple[bool, List[str]]:
    """Execute multi-tiered statutory and hemodynamic safety firewalls."""
    alerts = []
    cleared = True

    # 1. Severe Anemia Firewall
    if intake.hemoglobin_g_dl is not None and intake.hemoglobin_g_dl < 8.0:
        cleared = False
        alerts.append(
            f"CRITICAL SAFETY ALERT [CODE_RED_SEVERE_ANEMIA]: Hemoglobin is {intake.hemoglobin_g_dl} g/dL (< 8.0 g/dL). "
            "All invasive bloodletting (Raktamokshana) and aggressive Shodhana therapies are strictly prohibited."
        )

    # 2. Hemodynamic Shock Firewall
    if intake.systolic_bp is not None and intake.diastolic_bp is not None:
        map_bp = (intake.systolic_bp + 2 * intake.diastolic_bp) / 3.0
        if intake.systolic_bp < 90 or map_bp < 65.0:
            cleared = False
            alerts.append(
                f"CRITICAL SAFETY ALERT [CODE_RED_HYPOTENSION_SHOCK]: Blood pressure {intake.systolic_bp}/{intake.diastolic_bp} mmHg. "
                "Patient is in hemodynamic collapse/shock. Immediate stabilization required."
            )

    # 3. Pregnancy Safety Firewall
    if intake.is_pregnant:
        alerts.append(
            "PREGNANCY PRECAUTION [GARBHINI_SURAKSHA]: Patient is pregnant. Strongly purgative (Virechana), emetic (Vamana), "
            "or uterine-stimulating formulations (Kashisa, Guggulu in heavy dose) are contraindicated."
        )

    # 4. Ama Shodhana Gating
    if ama == AmaStatus.SAMA:
        alerts.append(
            "PHYSIOLOGICAL GATING [AMA_SHODHANA_GATE]: Endotoxins (Ama) detected. Pradhana Panchakarma bio-purification is contraindicated "
            "to prevent toxic displacement. Prescribe Deepana-Pachana first."
        )

    # 5. Herb-Drug Interactions (HDI)
    if intake.current_medications:
        meds_lower = [m.lower() for m in intake.current_medications]
        if any("warfarin" in m or "aspirin" in m or "clopidogrel" in m for m in meds_lower):
            alerts.append(
                "HERB-DRUG INTERACTION WARNING [ANTICOAGULANT_SYNERGY]: Patient is taking modern antiplatelet/anticoagulant drugs. "
                "Concurrent administration of high-dose Guggulu, Lasuna, or Ginger Kwatha increases bleeding risk. Monitor coagulation parameters."
            )

    return cleared, alerts


def generate_patient_summary_markdown(
    intake: ClinicalIntakeData,
    primary: DualMorbidityCode,
    differentials: Optional[List[DualMorbidityCode]] = None,
    vikriti: Optional[Dict[str, float]] = None,
    divergence: float = 0.0,
    agni: AgniStatus = AgniStatus.SAMAGNI,
    ama: AmaStatus = AmaStatus.NIRAMA,
    kriya_kala: ShatKriyaKalaStage = ShatKriyaKalaStage.PRASARA,
    plan: Optional[ComprehensiveTreatmentPlan] = None,
    alerts: Optional[List[str]] = None,
    governance_status: GovernanceStatus = GovernanceStatus.DRAFT_DECISION_SUPPORT,
    physician_arn: Optional[str] = None
) -> str:
    """Render standardized 9-Part Master Ayurvedic Clinical Assessment & Comprehensive Medical Report."""
    differentials = differentials or []
    vikriti = vikriti or {}
    alerts = alerts or []
    vsi = round(divergence * 100, 1)
    vsi_grade = "Alpa Vikriti" if vsi < 20 else ("Madhyama Vikriti" if vsi < 50 else "Tivra Vikriti")

    status_str = (
        f"STATUTORY_VALIDATED_PHYSICIAN_COUNTERSIGNED (NCISM ARN: {physician_arn})"
        if governance_status == GovernanceStatus.PHYSICIAN_COUNTERSIGNED
        else "DRAFT_AYUSH_DECISION_SUPPORT_REQUIRES_PHYSICIAN_SIGNATURE"
    )
    evidence_lvl = plan.evidence_ranking.level if plan else "Level C (Ayurvedic Classical Benchmark)"

    md = [
        "# MASTER AYURVEDIC CLINICAL ASSESSMENT & COMPREHENSIVE MEDICAL REPORT",
        f"Legal Status: {status_str}",
        f"Evidence Ranking: {evidence_lvl} | Confidence: {round(primary.confidence_score * 100, 1)}%",
        f"**Patient ID:** `{intake.patient_id}` | **Hospital ID:** `{intake.hospital_id}` | **Episode Date:** `{time.strftime('%Y-%m-%d %H:%M:%S')}`\n",
        "---",
        "## 1. EXECUTIVE SUMMARY & DEFINITIVE AYURVEDIC DIAGNOSIS",
        f"- **Primary Ayurvedic Roga:** **{primary.sanskrit_name}** (NAMASTE: `{primary.namaste_code}` | WHO ICD-11 TM2: `{primary.icd11_tm2_code}`)",
        f"- **Dual Western Clinical Crosswalk:** *{primary.icd11_title}*",
        f"- **Pre-Test / Post-Test Doshic Diagnostic Probability:** `50.0% -> {round(primary.confidence_score * 100, 1)}%`",
        f"- **Secondary / Incidental Suspicions:** {', '.join([d.sanskrit_name for d in differentials]) if differentials else 'None noted.'}\n",
        "## 2. FORENSIC PATIENT PROFILE & EXPOSURE TIMELINE",
        "- **Constitutional Coordinates:**",
        f"  - Prakriti Vector: P = (v: {intake.prakriti_vector.get('VATA', 0.33):.2f}, p: {intake.prakriti_vector.get('PITTA', 0.33):.2f}, k: {intake.prakriti_vector.get('KAPHA', 0.34):.2f})" if intake.prakriti_vector else "  - Baseline Prakriti: Centroid Equilibrium P = (v: 0.33, p: 0.33, k: 0.34)",
        f"  - Vikriti Vector:  V = (v: {vikriti.get('VATA', 0):.2f}, p: {vikriti.get('PITTA', 0):.2f}, k: {vikriti.get('KAPHA', 0):.2f})",
        f"  - Vikriti Severity Index (VSI): `{vsi}` [{vsi_grade}]",
        f"- **Chronological Nidana Sevana:** Duration of clinical progression: {intake.duration_weeks} weeks with chief complaints: {'; '.join(intake.chief_complaints)}.",
        f"- **Rogi Bala vs. Roga Bala Valuation:** Rogi Bala = `{intake.rogi_bala.value if intake.rogi_bala else 'MADHYAMA (PRELIMINARY)'}` | Disease Chronicity Stage = `{kriya_kala.value}`\n",
        "## 3. MASTER RANKED DIFFERENTIAL DIAGNOSIS MATRIX (ROGA VINISHCHAYA)",
        "| # | Suspected Roga | Doshic Subtype | Supporting Signs | Distinguishing Markers | Status |",
        "|:--|:---------------|:---------------|:-----------------|:-----------------------|:-------|",
        f"| 1 | **{primary.sanskrit_name}** | Primary Imbalance | {', '.join(intake.symptoms[:3])} | High affinity index ({round(primary.confidence_score * 100, 1)}%) | **PRIMARY** |",
    ]

    for idx, d in enumerate(differentials, 2):
        md.append(f"| {idx} | {d.sanskrit_name} | Secondary Doshic | Overlapping presentation | Lower diagnostic score ({round(d.confidence_score * 100, 1)}%) | EXCLUDED |")
    md.append("")

    md.extend([
        "## 4. DEEP PATHOLOGICAL BREAKDOWN (SAMPRAPTI GHATAKA)",
        f"- **Dosha:** Predominant vitiation in `{max(vikriti, key=vikriti.get)}` ({vikriti.get(max(vikriti, key=vikriti.get), 0):.1%}) | **Dushya:** Affected structural tissues",
        f"- **Agni Status:** `{agni.value}`",
        f"- **Ama Status:** AGI Evaluation: `{ama.value}`",
        f"- **Srotas & Srotodushti:** Primary channels involved with Srotorodha / Sanga",
        f"- **Rogamarga:** Madhyama / Abhyantara | **Shat Kriya Kala:** `{kriya_kala.value}` (Pathogenesis Phase)\n",
        "## 5. RED FLAGS & EMERGENCY SAFETY ADVISORY",
        "- **Classical Arishta Lakshana:** Evaluated; no imminent fatal Arishta markers identified.",
        f"- **Western Acute Red Flags:** Blood Pressure = `{intake.systolic_bp if intake.systolic_bp is not None else 'N/A'}/{intake.diastolic_bp if intake.diastolic_bp is not None else 'N/A'} mmHg`, Hemoglobin = `{intake.hemoglobin_g_dl if intake.hemoglobin_g_dl is not None else 'N/A'} g/dL`.",
        "> [!WARNING]",
        f"> **Emergency Escalation Gate**: {plan.emergency_escalation_criteria}\n",
        "## 6. ACTIONABLE MEDICAL & PHARMACOTHERAPY PROTOCOL",
        "> [!CAUTION]",
        "> **MANDATORY SAFETY ADVISORY (WHAT NOT TO DO)**",
        "> Strictly avoid unpurified Schedule E(1) compounds, contra-indicated Viruddha Ahara, and premature Shodhana during Sama states.",
        "",
        "- **A. Deepana & Pachana Protocol:**" if ama == AmaStatus.SAMA else "- **A. Deepana & Pachana:** Nirama state verified; proceed directly to Shamana.",
    ])

    if ama == AmaStatus.SAMA:
        md.append("  - Administer Shunthi Churna / Chitrakadi Vati with warm water for 3–5 days to digest circulating Ama.")

    md.append("\n- **B. Shamana Aushadha (Prescribed Classical Formulations):**")
    md.append("| Formulation | Form | Dosage | Timing | Anupana (Vehicle) | Reference |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for f in plan.shamana_chikitsa:
        md.append(f"| **{f.formulation_name}** | {f.kalpana_form} | {f.dosage} | {f.timing} | {f.anupana} | *{f.classical_reference}* |")

    if plan.generic_substitutions:
        md.append("\n- **C. Generic IMPCL / Jan Aushadhi Substitutions (Cost Transparency):**")
        md.append("| Classical / Branded Name | Generic IMPCL Substitute | Jan Aushadhi Code | Estimated Cost Savings |")
        md.append("| :--- | :--- | :--- | :--- |")
        for g in plan.generic_substitutions:
            md.append(f"| {g.branded_or_classical_name} | **{g.generic_impcl_name}** | `{g.jan_aushadhi_code}` | **{g.cost_savings_percentage:.0f}% Savings** |")

    md.append("\n- **D. Pathya-Apathya Ahara & Vihara:**")
    md.append("  - **Pathya (Recommended Diet):** " + "; ".join(plan.pathya_ahara))
    md.append("  - **Apathya (Contraindicated Diet):** " + "; ".join(plan.apathya_ahara))
    md.append("  - **Swasthavritta (Daily Regimen):** " + "; ".join(plan.swasthavritta_vihara) + "\n")

    md.extend([
        "## 7. PANCHAKARMA & WARD PROCEDURAL REQUISITION",
        f"- **Indicated Procedures & Eligibility:** `{plan.shodhana_eligibility.value}`",
        f"- **Pre-requisites:** {plan.shodhana_guidance_notes}",
        "- **Samsarjana Krama Schedule:**",
        "  - *Pravara Shuddhi:* 7 days (3 Ahara Kalas each of Peya, Vilepi, Akrita Yusha, Krita Yusha, Akrita Mamsa Rasa, Krita Mamsa Rasa)",
        "  - *Madhyama Shuddhi:* 5 days (2 Ahara Kalas each step)",
        "  - *Avara Shuddhi:* 3 days (1 Ahara Kala each step)\n",
        "## 8. STRUCTURED DIAGNOSTIC REQUISITION PLAN",
        "- **Tier 1 (Ayurvedic Diagnostic Confirmation):**",
    ])
    for t1 in plan.tier1_ayurvedic_requisitions:
        md.append(f"  - [x] {t1}")

    md.append("- **Tier 2 (Integrative Biomarker Surveillance):**")
    for t2 in plan.tier2_integrative_biomarkers:
        md.append(f"  - [x] {t2}")

    md.extend([
        "\n## 9. IMMEDIATE ACTION CHECKLIST FOR THE PATIENT",
        "- [ ] Take prescribed Shamana formulations strictly after/before meals with warm water as advised.",
        "- [ ] Follow the Pathya dietetic recommendations; completely eliminate Apathya foods (curd, cold drinks, heavy unctuous foods).",
        "- [ ] Monitor for any red-flag emergency symptoms (chest pain, high fever, sudden breathlessness).",
        "- [ ] Return to OPD / Tele-AYUSH clinic for follow-up review in 14 days.\n",
        "---",
        "> [!NOTE]",
        "> **Statutory Notice under NCISM Act 2020:** This clinical evaluation is generated by the Autonomous AYUSH Clinical Decision Support System (A-CDSS). It constitutes decision support and must be validated and counter-signed by an authorized NCISM Registered Medical Practitioner (`ARN`)."
    ])

    return "\n".join(md)


# -------------------------------------------------------------------------
# Orchestrator Workflow Execution
# -------------------------------------------------------------------------

def evaluate_clinical_diagnosis(
    intake: ClinicalIntakeData,
    conn: Optional[sqlite3.Connection] = None
) -> DiagnosisEpisodeResponse:
    """Execute end-to-end diagnostic synthesis across all clinical modules with strict safety hardening."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        # 0. Intake Completeness Validation (C1)
        is_complete, missing_fields = validate_intake_completeness(intake)
        is_preliminary = not is_complete
        missing_params = missing_fields

        effective_rogi_bala = intake.rogi_bala or RogiBalaGrade.MADHYAMA
        effective_sbp = intake.systolic_bp if intake.systolic_bp is not None else 120
        effective_dbp = intake.diastolic_bp if intake.diastolic_bp is not None else 80
        effective_hb = intake.hemoglobin_g_dl if intake.hemoglobin_g_dl is not None else 13.0

        # 1. Red-Flag Emergency Mimic Screening (M1)
        red_flag_screening = screen_red_flag_mimics(intake)
        governance_status = (
            GovernanceStatus.EMERGENCY_TRANSFER_TRIGGERED
            if red_flag_screening.mimic_detected
            else GovernanceStatus.DRAFT_DECISION_SUPPORT
        )

        # 2. Match morbidity profiles
        matched = match_morbidity_profile(intake.chief_complaints, intake.symptoms)
        top_key, top_score = matched[0] if matched else ("AMAVATA", 0.80)
        profile = CLASSICAL_DISEASE_PROFILES.get(top_key, CLASSICAL_DISEASE_PROFILES["AMAVATA"])

        primary_code = DualMorbidityCode(
            sanskrit_name=profile["sanskrit_name"],
            namaste_code=profile["namaste_code"],
            icd11_tm2_code=profile["icd11_tm2_code"],
            icd11_title=profile["icd11_title"],
            confidence_score=max(0.75, round(top_score, 2))
        )

        # Build Ranked Differentials (Top 3) with Vyavachhedaka Lakshana & Pertinent Negatives (Task 1.4)
        ranked_differentials: List[RankedDifferentialItem] = []
        user_tokens = " ".join((intake.chief_complaints or []) + (intake.symptoms or [])).lower()
        differentials: List[DualMorbidityCode] = []

        for rank_idx, (m_key, score) in enumerate(matched[:3], 1):
            d_prof = CLASSICAL_DISEASE_PROFILES[m_key]
            d_code = DualMorbidityCode(
                sanskrit_name=d_prof["sanskrit_name"],
                namaste_code=d_prof["namaste_code"],
                icd11_tm2_code=d_prof["icd11_tm2_code"],
                icd11_title=d_prof["icd11_title"],
                confidence_score=round(score, 2)
            )
            if rank_idx > 1:
                differentials.append(d_code)

            pertinent_pos = [k for k in d_prof["key_symptoms"] if k.lower() in user_tokens]
            pertinent_neg = [k for k in d_prof["key_symptoms"] if k.lower() not in user_tokens][:4]

            ranked_differentials.append(
                RankedDifferentialItem(
                    rank=rank_idx,
                    diagnosis=d_code,
                    classical_probability=round(score, 2),
                    vyavachhedaka_lakshana=d_prof.get("vyavachhedaka_lakshana", "Cardinal classical presentation according to shastras."),
                    pertinent_negatives=pertinent_neg,
                    pertinent_positives=pertinent_pos
                )
            )

        # 3. Vikriti vector & divergence
        vikriti_vec, divergence = derive_vikriti_vector(intake, profile)

        # 4. Ama and Agni
        ama_status, agni_status = determine_ama_and_agni(intake, profile)

        # 5. Shat Kriya Kala stage
        kriya_kala = evaluate_shat_kriya_kala(intake.duration_weeks, intake.symptoms)

        # 6. Safety firewalls
        cleared, alerts = check_clinical_safety_firewalls(intake, ama_status)
        if red_flag_screening.mimic_detected:
            cleared = False
            alerts.append(
                f"CRITICAL RED-FLAG MIMIC INTERCEPTED: Suspected '{red_flag_screening.suspected_syndrome}' "
                f"mimicking '{red_flag_screening.presenting_mimic}'. Action required: {red_flag_screening.critical_action_required}"
            )

        # If emergency transfer triggered, invoke Phase 35 break-glass
        if red_flag_screening.mimic_detected:
            try:
                v_telemetry = VitalSignsTelemetry(
                    systolic_bp=effective_sbp,
                    diastolic_bp=effective_dbp,
                    heart_rate_bpm=intake.heart_rate_bpm or 88,
                    respiratory_rate_bpm=intake.respiratory_rate_bpm or 20,
                    spo2_percentage=intake.spo2_percentage or 98.0,
                    glasgow_coma_scale=15,
                    temperature_fahrenheit=intake.temperature_fahrenheit or 98.6
                )
                trigger_reason = (
                    EmergencyTriggerReason.CARDIOGENIC_SHOCK if effective_sbp < 90
                    else EmergencyTriggerReason.SEVERE_HYPOXIA if (intake.spo2_percentage and intake.spo2_percentage < 90.0)
                    else EmergencyTriggerReason.ACUTE_CORONARY_SYNDROME if "coronary" in (red_flag_screening.suspected_syndrome or "").lower()
                    else EmergencyTriggerReason.ACUTE_ABDOMEN_PERITONITIS
                )
                bg_req = EmergencyBreakGlassRequest(
                    patient_id=intake.patient_id,
                    hospital_id=intake.hospital_id,
                    trigger_reason=trigger_reason,
                    vitals=v_telemetry,
                    initiating_user_id="A-CDSS_SYSTEM",
                    initiating_role="CLINICAL_DECISION_SUPPORT",
                    emergency_icu_destination=red_flag_screening.emergency_facility_type or "AIIMS Apex Emergency Centre",
                    clinical_narrative=f"RED-FLAG MIMIC: {red_flag_screening.suspected_syndrome}. Critical action: {red_flag_screening.critical_action_required}"
                )
                trigger_emergency_break_glass(bg_req, conn=conn)
            except Exception:
                pass

        # 7. Panchakarma Shodhana eligibility
        if red_flag_screening.mimic_detected:
            shodhana_elig = ShodhanaEligibility.NOT_INDICATED
            shodhana_notes = (
                f"EMERGENCY BREAK-GLASS ACTIVE: Suspected {red_flag_screening.suspected_syndrome}. "
                "All elective Panchakarma and Ayurvedic procedures strictly suspended."
            )
        elif ama_status == AmaStatus.SAMA:
            shodhana_elig = ShodhanaEligibility.CONTRAINDICATED_SAMA_STATE
            shodhana_notes = (
                "Pradhana Shodhana is strictly contraindicated in the Sama state. Administer Deepana-Pachana "
                "formulations (Shunthi Kwatha, Chitrakadi Vati, Musta) for 3-7 days until Nirama features appear."
            )
        elif effective_rogi_bala == RogiBalaGrade.AVARA:
            shodhana_elig = ShodhanaEligibility.NOT_INDICATED
            shodhana_notes = (
                "Patient has Avara Bala (debilitated reserve). Aggressive Panchakarma Shodhana will cause severe Ojas depletion. "
                "Manage strictly with Shamana Chikitsa, Brimhana diet, and gentle local Upakarmas."
            )
        else:
            shodhana_elig = ShodhanaEligibility.READY_FOR_PRADHANA_KARMA
            shodhana_notes = (
                "Patient is in Nirama state with adequate vitality. Eligible for classical Panchakarma Shodhana "
                "following prescribed Snehana and Swedana Purvakarmas."
            )

        # 8. Treatment Plan
        if red_flag_screening.mimic_detected:
            prescribed_shamana = []
            generic_subs = []
        else:
            prescribed_shamana = [
                PrescribedFormulation(**f) for f in profile["shamana_formulations"]
            ]
            generic_subs = [
                GenericSubstitution(
                    branded_or_classical_name=f.formulation_name,
                    generic_impcl_name=f"{f.formulation_name} (IMPCL Standard)",
                    jan_aushadhi_code=f"AYU-GEN-{idx:03d}",
                    cost_savings_percentage=45.0
                ) for idx, f in enumerate(prescribed_shamana, 1)
            ]

        evidence_attr = EvidenceAttribution(
            level=profile.get("evidence_level", EvidenceRankingLevel.LEVEL_E.value),
            source_reference=profile.get("evidence_source", "Chakradatta & Bhaishajya Ratnavali"),
            source_doi_or_shloka=profile.get("evidence_citation", "Classical Shastra Samhita"),
            confidence_score=primary_code.confidence_score
        )

        escalation_criteria = (
            red_flag_screening.critical_action_required
            if red_flag_screening.mimic_detected
            else "Acute cardiogenic shock, severe dyspnea (RR > 30/min), or hemodynamic collapse (SBP < 90 mmHg) requires immediate NABH COP.6 break-glass ICU transfer."
        )

        treatment_plan = ComprehensiveTreatmentPlan(
            evidence_ranking=evidence_attr,
            shamana_chikitsa=prescribed_shamana,
            generic_substitutions=generic_subs,
            shodhana_eligibility=shodhana_elig,
            shodhana_guidance_notes=shodhana_notes,
            pathya_ahara=profile["pathya_ahara"] if not red_flag_screening.mimic_detected else ["Nil per os (NPO) pending emergency surgical/medical stabilization"],
            apathya_ahara=profile["apathya_ahara"],
            swasthavritta_vihara=profile["swasthavritta_vihara"],
            parasurgical_referral=profile.get("parasurgical_referral") if not red_flag_screening.mimic_detected else None,
            rasayana_rehabilitation=profile.get("rasayana_rehabilitation") if not red_flag_screening.mimic_detected else None,
            tier1_ayurvedic_requisitions=[
                "Nadi Waveform Spectral Telemetry (Tri-Dosha Decomposition)",
                "Taila Bindu Surface-Tension Fluid Dynamics Pariksha",
                "Jihwa Lepa Micro-Colorimetry Coating Analysis"
            ] if not red_flag_screening.mimic_detected else [],
            tier2_integrative_biomarkers=[
                "Complete Blood Count (CBC) with ESR & hs-CRP",
                "Renal Function Test (Serum Creatinine, Blood Urea)",
                "Liver Function Panel (SGOT, SGPT, Total Bilirubin)",
                "Metabolic Lipid & Glycated Hemoglobin Profile"
            ],
            emergency_escalation_criteria=escalation_criteria
        )

        # 9. Render patient summary report using 9-Part Canonical Standard
        report_md = generate_patient_summary_markdown(
            intake=intake,
            primary=primary_code,
            differentials=differentials,
            vikriti=vikriti_vec,
            divergence=divergence,
            agni=agni_status,
            ama=ama_status,
            kriya_kala=kriya_kala,
            plan=treatment_plan,
            alerts=alerts,
            governance_status=governance_status
        )

        # 10. Persistence into Table 73
        now = int(time.time())
        episode_id = f"EPISODE-DIAG-{now}-{uuid.uuid4().hex[:6].upper()}"

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO clinical_diagnosis_episodes (
                episode_id, patient_id, hospital_id, intake_data_json,
                primary_diagnosis_sanskrit, primary_diagnosis_namaste_code, primary_diagnosis_icd11_code,
                vikriti_vector_json, vikriti_divergence_metric, agni_status, ama_status,
                shat_kriya_kala_stage, rogi_bala, doshic_dushti_json, treatment_protocol_json,
                safety_firewalls_cleared, safety_alerts_json, governance_status,
                attending_physician_arn, countersigned_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                episode_id,
                intake.patient_id,
                intake.hospital_id,
                intake.model_dump_json(),
                primary_code.sanskrit_name,
                primary_code.namaste_code,
                primary_code.icd11_tm2_code,
                json.dumps(vikriti_vec),
                divergence,
                agni_status.value,
                ama_status.value,
                kriya_kala.value,
                effective_rogi_bala.value,
                json.dumps({
                    "vitiated_srotases": intake.vitiated_srotases or profile["vitiated_srotases"],
                    "vitiated_dhatus": intake.vitiated_dhatus or profile["vitiated_dhatus"],
                }),
                treatment_plan.model_dump_json(),
                1 if cleared else 0,
                json.dumps(alerts),
                governance_status.value,
                None,
                None,
                now
            )
        )

        append_audit_log(
            conn,
            intake.hospital_id,
            "A-CDSS_KERNEL",
            "GENERATE_DIAGNOSIS_EPISODE",
            "DIAGNOSIS_EPISODE",
            episode_id,
            {
                "patient_id": intake.patient_id,
                "primary_diagnosis": primary_code.sanskrit_name,
                "namaste_code": primary_code.namaste_code,
                "safety_cleared": cleared,
                "governance_status": governance_status.value,
                "red_flag_detected": red_flag_screening.mimic_detected
            }
        )
        conn.commit()

        return DiagnosisEpisodeResponse(
            episode_id=episode_id,
            patient_id=intake.patient_id,
            hospital_id=intake.hospital_id,
            primary_diagnosis=primary_code,
            differential_diagnoses=differentials,
            ranked_differentials=ranked_differentials,
            red_flag_screening=red_flag_screening,
            vikriti_vector=vikriti_vec,
            vikriti_divergence_metric=divergence,
            agni_status=agni_status,
            ama_status=ama_status,
            shat_kriya_kala_stage=kriya_kala,
            rogi_bala=effective_rogi_bala,
            doshic_dushya_sammurchhana={
                "vitiated_srotases": intake.vitiated_srotases or profile["vitiated_srotases"],
                "vitiated_dhatus": intake.vitiated_dhatus or profile["vitiated_dhatus"],
            },
            treatment_protocol=treatment_plan,
            safety_firewalls_cleared=cleared,
            safety_alerts=alerts,
            governance_status=governance_status,
            is_preliminary_assessment=is_preliminary,
            missing_vital_parameters=missing_params,
            attending_physician_arn=None,
            countersigned_at=None,
            patient_summary_report_markdown=report_md,
            created_at=now
        )
    finally:
        if should_close:
            conn.close()


def countersign_diagnosis_episode(
    episode_id: str,
    req: CounterSignRequest,
    conn: Optional[sqlite3.Connection] = None
) -> DiagnosisEpisodeResponse:
    """Record statutory NCISM registered physician counter-signature on diagnostic episode."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clinical_diagnosis_episodes WHERE episode_id = ?;", (episode_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Diagnostic episode '{episode_id}' not found.")

        now = int(time.time())
        status = GovernanceStatus.PHYSICIAN_COUNTERSIGNED if req.action.upper() == "COUNTERSIGN" else GovernanceStatus.REJECTED_BY_PHYSICIAN

        cursor.execute(
            """
            UPDATE clinical_diagnosis_episodes
            SET governance_status = ?, attending_physician_arn = ?, countersigned_at = ?
            WHERE episode_id = ?;
            """,
            (status.value, req.physician_arn, now, episode_id)
        )

        append_audit_log(
            conn,
            row["hospital_id"],
            req.physician_arn,
            f"COUNTERSIGN_{status.value}",
            "DIAGNOSIS_EPISODE",
            episode_id,
            {"action": req.action, "notes": req.clinical_notes}
        )
        conn.commit()

        # Re-fetch updated row
        cursor.execute("SELECT * FROM clinical_diagnosis_episodes WHERE episode_id = ?;", (episode_id,))
        updated = cursor.fetchone()

        intake = ClinicalIntakeData.model_validate_json(updated["intake_data_json"])
        treatment = ComprehensiveTreatmentPlan.model_validate_json(updated["treatment_protocol_json"])
        primary = DualMorbidityCode(
            sanskrit_name=updated["primary_diagnosis_sanskrit"],
            namaste_code=updated["primary_diagnosis_namaste_code"],
            icd11_tm2_code=updated["primary_diagnosis_icd11_code"],
            icd11_title=CLASSICAL_DISEASE_PROFILES.get(updated["primary_diagnosis_sanskrit"].upper(), {}).get("icd11_title", "Unspecified"),
            confidence_score=0.90
        )

        report_md = generate_patient_summary_markdown(
            intake=intake,
            primary=primary,
            differentials=[],
            vikriti=json.loads(updated["vikriti_vector_json"]),
            divergence=updated["vikriti_divergence_metric"],
            agni=AgniStatus(updated["agni_status"]),
            ama=AmaStatus(updated["ama_status"]),
            kriya_kala=ShatKriyaKalaStage(updated["shat_kriya_kala_stage"]),
            plan=treatment,
            alerts=json.loads(updated["safety_alerts_json"]),
            governance_status=status,
            physician_arn=req.physician_arn
        )

        return DiagnosisEpisodeResponse(
            episode_id=updated["episode_id"],
            patient_id=updated["patient_id"],
            hospital_id=updated["hospital_id"],
            primary_diagnosis=primary,
            differential_diagnoses=[],
            vikriti_vector=json.loads(updated["vikriti_vector_json"]),
            vikriti_divergence_metric=updated["vikriti_divergence_metric"],
            agni_status=AgniStatus(updated["agni_status"]),
            ama_status=AmaStatus(updated["ama_status"]),
            shat_kriya_kala_stage=ShatKriyaKalaStage(updated["shat_kriya_kala_stage"]),
            rogi_bala=RogiBalaGrade(updated["rogi_bala"]),
            doshic_dushya_sammurchhana=json.loads(updated["doshic_dushti_json"]),
            treatment_protocol=treatment,
            safety_firewalls_cleared=bool(updated["safety_firewalls_cleared"]),
            safety_alerts=json.loads(updated["safety_alerts_json"]),
            governance_status=GovernanceStatus(updated["governance_status"]),
            attending_physician_arn=updated["attending_physician_arn"],
            countersigned_at=updated["countersigned_at"],
            patient_summary_report_markdown=report_md,
            created_at=updated["created_at"]
        )
    finally:
        if should_close:
            conn.close()


def get_patient_diagnosis_episodes(
    patient_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> List[DiagnosisEpisodeResponse]:
    """Retrieve historical clinical diagnosis episodes for a patient."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM clinical_diagnosis_episodes WHERE patient_id = ? ORDER BY created_at DESC;",
            (patient_id,)
        )
        rows = cursor.fetchall()
        results = []

        for row in rows:
            intake = ClinicalIntakeData.model_validate_json(row["intake_data_json"])
            treatment = ComprehensiveTreatmentPlan.model_validate_json(row["treatment_protocol_json"])
            primary = DualMorbidityCode(
                sanskrit_name=row["primary_diagnosis_sanskrit"],
                namaste_code=row["primary_diagnosis_namaste_code"],
                icd11_tm2_code=row["primary_diagnosis_icd11_code"],
                icd11_title=CLASSICAL_DISEASE_PROFILES.get(row["primary_diagnosis_sanskrit"].upper(), {}).get("icd11_title", "Unspecified"),
                confidence_score=0.90
            )

            report_md = generate_patient_summary_markdown(
                intake=intake,
                primary=primary,
                vikriti=json.loads(row["vikriti_vector_json"]),
                divergence=row["vikriti_divergence_metric"],
                agni=AgniStatus(row["agni_status"]),
                ama=AmaStatus(row["ama_status"]),
                kriya_kala=ShatKriyaKalaStage(row["shat_kriya_kala_stage"]),
                plan=treatment,
                alerts=json.loads(row["safety_alerts_json"])
            )

            results.append(
                DiagnosisEpisodeResponse(
                    episode_id=row["episode_id"],
                    patient_id=row["patient_id"],
                    hospital_id=row["hospital_id"],
                    primary_diagnosis=primary,
                    differential_diagnoses=[],
                    vikriti_vector=json.loads(row["vikriti_vector_json"]),
                    vikriti_divergence_metric=row["vikriti_divergence_metric"],
                    agni_status=AgniStatus(row["agni_status"]),
                    ama_status=AmaStatus(row["ama_status"]),
                    shat_kriya_kala_stage=ShatKriyaKalaStage(row["shat_kriya_kala_stage"]),
                    rogi_bala=RogiBalaGrade(row["rogi_bala"]),
                    doshic_dushya_sammurchhana=json.loads(row["doshic_dushti_json"]),
                    treatment_protocol=treatment,
                    safety_firewalls_cleared=bool(row["safety_firewalls_cleared"]),
                    safety_alerts=json.loads(row["safety_alerts_json"]),
                    governance_status=GovernanceStatus(row["governance_status"]),
                    attending_physician_arn=row["attending_physician_arn"],
                    countersigned_at=row["countersigned_at"],
                    patient_summary_report_markdown=report_md,
                    created_at=row["created_at"]
                )
            )
        return results
    finally:
        if should_close:
            conn.close()
