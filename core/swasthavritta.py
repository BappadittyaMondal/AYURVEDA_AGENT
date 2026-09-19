"""
Swasthavritta, Dinacharya, Ritucharya & Vega-Dharana Pathology Engine
=====================================================================
Implements:
1. Classical Dinacharya protocol catalog (Ashtanga Hridaya Sutrasthana Ch. 2)
2. Circadian Doshic Bio-Rhythm evaluation clock
3. Lifestyle routine compliance audit engine
4. 13 Non-suppressible natural urges (Adharaniya Vegas) & secondary Udavarta pathology
5. Ritucharya 6-season calendar, Ritusandhi 14-day transition firewall & seasonal Shodhana windows
6. SQLite WAL persistence with indexed queries
"""

from __future__ import annotations
import json
import time
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from models.swasthavritta import (
    AdharaniyaVegaType,
    Ayana,
    CircadianClockStatus,
    CircadianPeriod,
    DinacharyaRoutineAuditRequest,
    DinacharyaRoutineAuditResponse,
    DinacharyaStep,
    RituCode,
    RitusandhiEvaluation,
    SeasonalRegimenProfile,
    VegaPathologyResponse,
    VegaSuppressionLogRequest,
)

# ==============================================================================
# CLASSICAL DINACHARYA PROTOCOL STEPS CATALOG
# ==============================================================================

SEED_DINACHARYA_STEPS: List[DinacharyaStep] = [
    DinacharyaStep(
        step_id="DINA-BRAHMA-MUHURTA",
        step_name="Brahma Muhurta Jagrana",
        sanskrit_name="ब्राह्मे मुहूर्ते उत्तिष्ठेत् (Brahme Muhurte Uttishthet)",
        ideal_time_window="04:30 AM - 05:30 AM",
        doshic_benefit="Vata balance, Sattva Guna amplification, mental clarity",
        description="Awakening ~48-96 minutes prior to sunrise. Preserves longevity and synchronizes pineal-pituitary biological clock.",
        contraindications=["Severe exhaustion", "Acute high fever (Taruna Jwara)", "Post-operative surgical convalescence"]
    ),
    DinacharyaStep(
        step_id="DINA-USHAPANA",
        step_name="Ushapana",
        sanskrit_name="उषःपान (Ushapana)",
        ideal_time_window="05:30 AM - 06:00 AM",
        doshic_benefit="Stimulates Apana Vata peristalsis and flushes Pakvashaya",
        description="Drinking 200-400 mL lukewarm boiled water (or copper-vessel water) on an empty stomach.",
        contraindications=["Acute diarrhea (Atisara)", "Nausea/Vomiting (Chhardi)", "Ascites (Jalodara)"]
    ),
    DinacharyaStep(
        step_id="DINA-VEGA-UTSARGA",
        step_name="Mala-Mutra Utsarga",
        sanskrit_name="मल-मूत्र उत्सर्ग (Mala-Mutra Utsarga)",
        ideal_time_window="05:45 AM - 06:30 AM",
        doshic_benefit="Prevents Vega-Dharana, Apana Vata vitiation, and secondary Udavarta",
        description="Timely, unforced evacuation of bowel and bladder in squatting posture facing north/east.",
        contraindications=["Forceful straining (Pravahana is prohibited)"]
    ),
    DinacharyaStep(
        step_id="DINA-DANTADHAVANA",
        step_name="Dantadhavana",
        sanskrit_name="दन्तधावन (Dantadhavana)",
        ideal_time_window="06:15 AM - 06:45 AM",
        doshic_benefit="Liquefies Oral Kapha, eliminates Dantamala, enhances taste perception",
        description="Teeth brushing with herbal twigs (Khadira, Nimba, Karanja, Babool) endowed with Kashaya, Katu, or Tikta rasa.",
        contraindications=["Stomatitis (Mukha Paka)", "Facial paralysis (Ardita)", "Severe headache", "Eye diseases"]
    ),
    DinacharyaStep(
        step_id="DINA-JIHWA-NIRLEKHANA",
        step_name="Jihwa Nirlekhana",
        sanskrit_name="जिह्वा निर्लेखन (Jihwa Nirlekhana)",
        ideal_time_window="06:30 AM - 06:45 AM",
        doshic_benefit="Clears tongue Ama coating, stimulates digestive reflexes, removes halitosis",
        description="Tongue scraping using a curved gold, silver, or copper scraper from posterior root to anterior tip.",
        contraindications=["Oral mucosal ulcerations", "Glossitis"]
    ),
    DinacharyaStep(
        step_id="DINA-ANJANA",
        step_name="Netra Anjana",
        sanskrit_name="नेत्राञ्जन (Netranjana)",
        ideal_time_window="06:45 AM - 07:00 AM",
        doshic_benefit="Expels ocular Kapha secretions (Drishti-Prasadhana) and strengthens vision",
        description="Daily application of soothing Sauviranjana along the lid margin; weekly Rasanjana for Kapha clearance.",
        contraindications=["Acute conjunctivitis (Netra Abhisyanda)", "Immediately after head bath", "High fever"]
    ),
    DinacharyaStep(
        step_id="DINA-PRATIMARSHA-NASYA",
        step_name="Pratimarsha Nasya",
        sanskrit_name="प्रतिमर्श नस्य (Pratimarsha Nasya)",
        ideal_time_window="07:00 AM - 07:15 AM",
        doshic_benefit="Pacifies Urdhwajatrugata Vata, strengthens cervical spine, prevents premature graying",
        description="Instillation of 2 drops of lukewarm Anu Taila into each nostril followed by gentle aspiration and spitting.",
        contraindications=["Indigestion (Ajirna)", "Acute rhinitis (Nava Pratishyaya)", "Immediately post-meal"]
    ),
    DinacharyaStep(
        step_id="DINA-GANDUSHA",
        step_name="Gandusha / Kavala",
        sanskrit_name="गण्डूष एवं कवल (Gandusha & Kavala)",
        ideal_time_window="07:15 AM - 07:30 AM",
        doshic_benefit="Strengthens periodontal ligaments, jaw bone, and vocal resonance",
        description="Oil pulling: filling the oral cavity with warm Sesame Oil or Irimedadi Taila until lacrimation or nasal discharge appears.",
        contraindications=["Severe mouth ulcers", "Extreme thirst"]
    ),
    DinacharyaStep(
        step_id="DINA-ABHYANGA",
        step_name="Daily Abhyanga",
        sanskrit_name="नित्य अभ्यङ्ग (Nitya Abhyanga)",
        ideal_time_window="07:15 AM - 07:45 AM",
        doshic_benefit="Potently pacifies Vata, nourishes Dhatus, promotes sound sleep and longevity",
        description="Full body warm oil massage with particular focus on head (Shirah), ears (Karna), and feet (Pada).",
        contraindications=["High Ama (AGI >= 1.80)", "Taruna Jwara", "Indigestion", "Immediately after Shodhana"]
    ),
    DinacharyaStep(
        step_id="DINA-VYAYAMA",
        step_name="Ardha-Shakti Vyayama",
        sanskrit_name="अर्धशक्ति व्यायाम (Ardha-Shakti Vyayama)",
        ideal_time_window="07:30 AM - 08:15 AM",
        doshic_benefit="Alleviates Kapha, enhances Agni, burns excess Meda, tones body musculature",
        description="Physical exercise limited to 50% capacity (Ardha-Shakti) signified by sweating on forehead, nose, and axillae.",
        contraindications=["Severe Vata-Pitta disorders", "Raktapitta", "Children and elderly (> 70 yrs)", "Extreme debility"]
    ),
    DinacharyaStep(
        step_id="DINA-UDVARTANA",
        step_name="Udvartana / Kshoura",
        sanskrit_name="उद्वर्तन एवं क्षौर (Udvartana & Kshoura)",
        ideal_time_window="08:00 AM - 08:20 AM",
        doshic_benefit="Liquefies subcutaneous Kapha-Meda, firms flaccid skin, improves cutaneous microcirculation",
        description="Upward frictional rubbing with fragrant dry herbal powders (Triphala, Kolakulathadi) followed by grooming.",
        contraindications=["Dry eczema", "Severe dehydration", "Cachexia"]
    ),
    DinacharyaStep(
        step_id="DINA-SNANA",
        step_name="Snana",
        sanskrit_name="स्नान (Snana / Therapeutic Bath)",
        ideal_time_window="08:15 AM - 08:45 AM",
        doshic_benefit="Stimulates Ojas, removes fatigue, kindles digestive fire, purifies senses",
        description="Warm water bath below neck, and cool/ambient water over the head to preserve ocular and hair health.",
        contraindications=["Facial paralysis (Ardita)", "Tympanitis / Otalgia (Karnashula)", "Active diarrhea", "Ajirna"]
    ),
]

# ==============================================================================
# CLASSICAL RITUCHARYA (6-SEASON) & SEASONAL SHODHANA CATALOG
# ==============================================================================

SEED_RITUCHARYA_CATALOG: List[SeasonalRegimenProfile] = [
    SeasonalRegimenProfile(
        ritu_code=RituCode.SHISHIRA,
        ritu_name="Shishira (Late Winter)",
        sanskrit_name="शिशिर ऋतु (Shishira Ritu)",
        ayana=Ayana.ADANA_KALA,
        english_months="Mid January to Mid March",
        dominant_rasa="Tikta (Bitter)",
        dominant_mahabhuta="Vayu + Akasha",
        doshic_sanchaya="Vata Sanchaya begins in late Shishira",
        doshic_prakopa="None (Kapha accumulates in frozen state)",
        doshic_prashamana="Pitta Prashamana",
        indicated_shodhana="None required; Jatharagni is naturally powerful; heavy unctuous nourishing diet indicated",
        pathya_ahara=["गोधूम (Wheat)", "माष (Urad dal)", "गोधृत (Ghee)", "गुड (Old Jaggery)", "दुग्ध (Warm spiced milk)", "उष्ण जल (Warm water)"],
        apathya_ahara=["शीत जल (Cold water)", "रुक्ष आहार (Dry light foods)", "कटु रस (Excess pungent)", "लङ्घन (Fasting)"],
        pathya_vihara=["उष्ण गृहावास (Heated indoor dwelling)", "गुरु वस्त्र (Heavy warm woolens)", "अभ्यङ्ग (Daily warm oil massage)", "आतप सेवा (Sunbathing)"],
        apathya_vihara=["शीत वात सेवा (Exposure to cold dry drafts)", "अति व्यायाम (Over-exercise)", "दिवास्वप्न (Day sleep)"]
    ),
    SeasonalRegimenProfile(
        ritu_code=RituCode.VASANTA,
        ritu_name="Vasanta (Spring)",
        sanskrit_name="वसन्त ऋतु (Vasanta Ritu)",
        ayana=Ayana.ADANA_KALA,
        english_months="Mid March to Mid May",
        dominant_rasa="Kashaya (Astringent)",
        dominant_mahabhuta="Prithvi + Vayu",
        doshic_sanchaya="None",
        doshic_prakopa="KAPHA PRAKOPA (Sun liquefies winter-accumulated Kapha, extinguishing Agni)",
        doshic_prashamana="Vata remains neutral",
        indicated_shodhana="MANDATORY VAMANA KARMA (Therapeutic emesis) & Pratimarsha Nasya for Kapha evacuation",
        pathya_ahara=["यव (Barley)", "मुद्ग (Green gram)", "पुराण शालि (Old rice)", "आर्द्रक (Ginger)", "मधु (Honey)", "तक्र (Buttermilk)"],
        apathya_ahara=["दधि (Curd)", "गोधूम (Wheat in excess)", "मिष्टान्न (Heavy sweets)", "शीत स्निग्ध आहार (Cold unctuous food)", "नवान्न (Freshly harvested grains)"],
        pathya_vihara=["उद्वर्तन (Dry powder massage)", "व्यायाम (Brisk physical exercise)", "कवल-गण्डूष (Herbal gargling)", "वनेषु भ्रमण (Garden walks)"],
        apathya_vihara=["दिवास्वप्न (Daytime sleeping is strictly prohibited as it triggers acute Kapha rogas)", "अति स्निग्धाहार (Excess oil)"]
    ),
    SeasonalRegimenProfile(
        ritu_code=RituCode.GRISHMA,
        ritu_name="Grishma (Summer)",
        sanskrit_name="ग्रीष्म ऋतु (Grishma Ritu)",
        ayana=Ayana.ADANA_KALA,
        english_months="Mid May to Mid July",
        dominant_rasa="Katu (Pungent)",
        dominant_mahabhuta="Agni + Vayu",
        doshic_sanchaya="VATA SANCHAYA (Excess dry heat accumulates Vata; Kapha pacifies)",
        doshic_prakopa="None (Agni is weak due to intense solar dehydration)",
        doshic_prashamana="Kapha Prashamana",
        indicated_shodhana="Shodhana contraindicated due to extreme debility (Alpa Bala); mild Sheetali Pranayama & cold baths indicated",
        pathya_ahara=["द्राक्षा (Sweet raisins)", "दाडिम (Pomegranate)", "शर्करा (Cane sugar)", "घृत (Cow ghee)", "मन्थ (Sweet cooling churned drinks)", "शाल्योदन (Boiled rice with milk)"],
        apathya_ahara=["कटु-अम्ल-लवण रस (Hot, pungent, sour, salty foods)", "मद्य (Alcoholic beverages)", "उष्ण तीक्ष्ण आहार (Spicy foods)"],
        pathya_vihara=["शीतल जल स्नान (Cool refreshing baths)", "चन्दन लेप (Cooling sandalwood paste)", "चन्द्रिका सेवा (Moonlight walks)", "दिवास्वप्न (Short daytime nap permitted ONLY in Grishma)"],
        apathya_vihara=["अति व्यायाम (Strenuous exercise)", "आतप सेवा (Direct harsh sun exposure)", "मैथुन (Excessive sexual indulgence)"]
    ),
    SeasonalRegimenProfile(
        ritu_code=RituCode.VARSHA,
        ritu_name="Varsha (Monsoon)",
        sanskrit_name="वर्षा ऋतु (Varsha Ritu)",
        ayana=Ayana.VISARGA_KALA,
        english_months="Mid July to Mid September",
        dominant_rasa="Amla (Sour)",
        dominant_mahabhuta="Prithvi + Agni",
        doshic_sanchaya="PITTA SANCHAYA (Acidic rainwater and sour digestion accumulate Pitta)",
        doshic_prakopa="VATA PRAKOPA (Cold rains, wet damp ground, and cloudy skies provoke severe Vata)",
        doshic_prashamana="None (Agni is critically depressed by atmospheric humidity)",
        indicated_shodhana="MANDATORY BASTI KARMA (Asthapana and Anuvasana medicated enemas) for Vata pacification",
        pathya_ahara=["पुराण धान्य (Aged grains)", "यव (Barley)", "गोधूम (Wheat)", "सूप (Warm lentil soups)", "मधु (Small amount of honey to reduce dampness)", "उष्ण जल (Boiled warm water)"],
        apathya_ahara=["नदी जल (Turbid river water)", "सक्तु (Dry roasted flour)", "दधि (Curd)", "अत्यम्बुपान (Excessive water intake)", "कन्दमूल (Heavy root vegetables)"],
        pathya_vihara=["धूपन (Fumigation of garments and room with Guggulu)", "उष्ण जल स्नान (Warm baths)", "पादत्राण धारण (Wearing dry protective footwear)"],
        apathya_vihara=["नदी स्नान (Bathing in flood rivers)", "दिवास्वप्न (Day sleep)", "पूर्वावात (East cold damp winds)", "व्यायाम (Heavy exertion)"]
    ),
    SeasonalRegimenProfile(
        ritu_code=RituCode.SHARAD,
        ritu_name="Sharad (Autumn)",
        sanskrit_name="शरद् ऋतु (Sharad Ritu)",
        ayana=Ayana.VISARGA_KALA,
        english_months="Mid September to Mid November",
        dominant_rasa="Lavana (Salty)",
        dominant_mahabhuta="Jala + Agni",
        doshic_sanchaya="None",
        doshic_prakopa="PITTA PRAKOPA (Sudden bright heat of autumn sun heats accumulated monsoon Pitta)",
        doshic_prashamana="VATA PRASHAMANA (Cooling autumn breezes calm Vata)",
        indicated_shodhana="MANDATORY VIRECHANA KARMA (Purgation) & RAKTAMOKSHANA (Bloodletting / Jalaukavacharana)",
        pathya_ahara=["रक्तशालि (Red rice)", "मुद्ग (Green gram)", "सितोपला (Rock candy)", "दाडिम (Pomegranate)", "आमलकी (Amla)", "तिक्त घृत (Bitter medicated ghee)"],
        apathya_ahara=["क्षार (Alkali)", "दधि (Curd)", "तैल (Heavy oils)", "मत्स्य (Fish)", "लवण-अम्ल-कटु रस (Excess salty, sour, pungent foods)"],
        pathya_vihara=["हंसोदक सेवन (Drinking pure Hansodaka water purified by sun and Agastya star)", "चन्द्रकिरण सेवा (Moonlight exposure)", "शुक्ल वस्त्र (Wearing light white clean garments)"],
        apathya_vihara=["दिवास्वप्न (Day sleep)", "आतप सेवा (Direct midday sun)", "अवश्याय (Exposure to night frost/mist)", "अति भोजन (Over-eating)"]
    ),
    SeasonalRegimenProfile(
        ritu_code=RituCode.HEMANTA,
        ritu_name="Hemanta (Early Winter)",
        sanskrit_name="हेमन्त ऋतु (Hemanta Ritu)",
        ayana=Ayana.VISARGA_KALA,
        english_months="Mid November to Mid January",
        dominant_rasa="Madhura (Sweet)",
        dominant_mahabhuta="Prithvi + Jala",
        doshic_sanchaya="None",
        doshic_prakopa="None (Natural equilibrium, peak bodily strength / Pravara Bala)",
        doshic_prashamana="PITTA PRASHAMANA (Cold weather pacifies Pitta; Agni becomes intense)",
        indicated_shodhana="Shodhana generally not indicated; ideal period for Rasayana (rejuvenation) and Vajikarana therapies",
        pathya_ahara=["गोधूम (Wheat)", "माष (Black gram)", "तिल (Sesame)", "नवान्न (Freshly harvested grains permitted)", "क्षीर (Warm rich milk)", "इक्षु विकार (Sugarcane jaggery)"],
        apathya_ahara=["वातवर्धक आहार (Dry, cold, light foods)", "प्रमिताशन (Starvation / sub-caloric diet suppresses high digestive fire)"],
        pathya_vihara=["अभ्यङ्ग (Warm oil massage)", "मूर्ध तैल (Oil on crown)", "उष्ण जल स्नान (Warm baths)", "उष्ण वस्त्र (Warm attire)"],
        apathya_vihara=["शीत वात सेवा (Cold drafts)", "दिवास्वप्न (Day sleep)"]
    ),
]

# ==============================================================================
# 13 NON-SUPPRESSIBLE NATURAL URGES (ADHARANIYA VEGAS) KNOWLEDGE MATRIX
# ==============================================================================

ADHARANIYA_VEGAS_DATA: Dict[AdharaniyaVegaType, Dict[str, Any]] = {
    AdharaniyaVegaType.MUTRA: {
        "sanskrit": "मूत्र वेग रोध (Suppression of Urine)",
        "classical_symptoms": ["बस्तिशूल (Bastishula / Bladder pain)", "मूत्रकृच्छ्र (Dysuria)", "शिरोरुजा (Headache)", "अश्मरी (Calculus formation)", "वङ्क्षणानह (Groin fullness)"],
        "vitiated_dosha": "Apana Vata & Vyana Vata",
        "secondary_udavarta_risk": "HIGH",
        "remediation": "Avagaha Sweda (Warm sitz bath), gentle pelvic Abhyanga with Sahacharadi Taila, Uttara Basti or Gokshuradi Kwatha with Shilajit."
    },
    AdharaniyaVegaType.PURISHA: {
        "sanskrit": "पुरीष वेग रोध (Suppression of Feces)",
        "classical_symptoms": ["पक्वाशयशूल (Colic pain in colon)", "शिरोवेदना (Headache)", "वातमूत्रसङ्ग (Retention of flatus/urine)", "पिण्डिकोद्वेष्टन (Calf muscle cramps)", "आध्मान (Abdominal distension)"],
        "vitiated_dosha": "Apana Vata (Purishavaha Srotorodha)",
        "secondary_udavarta_risk": "CRITICAL",
        "remediation": "Phala Varti (Rectal suppository), Sneha Basti with warm Sesame oil, abdominal fomentation, Gandharvahastadi Castor oil."
    },
    AdharaniyaVegaType.SHUKRA: {
        "sanskrit": "शुक्र वेग रोध (Suppression of Ejaculation)",
        "classical_symptoms": ["मेढ्रशूल (Penile/pelvic pain)", "वृषणशूल (Testicular pain)", "हृद्व्यथा (Precordial pain)", "मूत्रसङ्ग (Urinary hesitancy)"],
        "vitiated_dosha": "Apana Vata & Shukravaha Srotas",
        "secondary_udavarta_risk": "MODERATE",
        "remediation": "Abhyanga, warm therapeutic bath, milk processed with Vidari and Gokshura, psychological counseling."
    },
    AdharaniyaVegaType.APANA_VATA: {
        "sanskrit": "अधोवात वेग रोध (Suppression of Flatus)",
        "classical_symptoms": ["वातसङ्ग (Inability to pass wind)", "गुल्म (Phantom abdominal masses)", "उदारुक् (Colic pain)", "क्लम (Exhaustion without exertion)", "दृष्टि-अग्नि वध (Impairment of vision and digestion)"],
        "vitiated_dosha": "Apana Vata",
        "secondary_udavarta_risk": "CRITICAL",
        "remediation": "Hingwashtaka Churna with warm water, Anuvasana Basti, abdominal warmth, Vatanulomana carminatives."
    },
    AdharaniyaVegaType.CHHARDI: {
        "sanskrit": "छर्दि वेग रोध (Suppression of Vomiting)",
        "classical_symptoms": ["कुष्ठ (Cutaneous dermatoses)", "कण्डू (Pruritus)", "कोठ (Urticarial eruptions)", "शोथ (Edema)", "पाण्डु (Anemia)", "ज्वर (Fever)"],
        "vitiated_dosha": "Kapha-Pitta & Udana Vata",
        "secondary_udavarta_risk": "HIGH",
        "remediation": "Langhana (Fasting), Gandusha, dry smoking (Dhoomapana), mild Vamana Shodhana to clear trapped toxins."
    },
    AdharaniyaVegaType.KSHAVATHU: {
        "sanskrit": "क्षवथु वेग रोध (Suppression of Sneezing)",
        "classical_symptoms": ["मन्यास्तम्भ (Neck stiffness / Cervical spasm)", "शिरोरुक् (Severe cranial headache)", "अर्दित (Facial palsy risk)", "इन्द्रिय दौर्बल्य (Sensory blunting)"],
        "vitiated_dosha": "Udana Vata & Prana Vata",
        "secondary_udavarta_risk": "MODERATE",
        "remediation": "Teekshna Nasya, gazing at mild sun rays, warm medicated steam inhalation, head Abhyanga."
    },
    AdharaniyaVegaType.UDGARA: {
        "sanskrit": "उद्गार वेग रोध (Suppression of Belching)",
        "classical_symptoms": ["अरुचि (Anorexia)", "कम्प (Tremors)", "हृदुरोविबन्ध (Tightness in chest and throat)", "आध्मान (Epigastric bloating)"],
        "vitiated_dosha": "Samana Vata & Udana Vata",
        "secondary_udavarta_risk": "LOW",
        "remediation": "Management as in Hikka-Shwasa; administration of Drakshasava or Pippali Churna with ghee."
    },
    AdharaniyaVegaType.JRIMBHA: {
        "sanskrit": "जृम्भा वेग रोध (Suppression of Yawning)",
        "classical_symptoms": ["विनाम (Body deformities / curvature)", "कम्प (Tremors)", "सुप्ति (Numbness)", "सङ्कोच (Muscle spasms)"],
        "vitiated_dosha": "Prana Vata",
        "secondary_udavarta_risk": "LOW",
        "remediation": "Vatahara Swedana, gentle massage of face and neck, unctuous nourishing diet."
    },
    AdharaniyaVegaType.KSHUDHA: {
        "sanskrit": "क्षुधा वेग रोध (Suppression of Hunger)",
        "classical_symptoms": ["कार्श्य (Emaciation)", "दौर्बल्य (Profound debility)", "अङ्गमर्द (Body aches)", "भ्रम (Vertigo)", "अग्निमान्द्य (Extinction of Agni)"],
        "vitiated_dosha": "Prana Vata & Pachaka Pitta",
        "secondary_udavarta_risk": "LOW",
        "remediation": "Gradual administration of warm, unctuous, light gruels (Peya/Vilepi), Yavagu with ghee."
    },
    AdharaniyaVegaType.PIPASA: {
        "sanskrit": "पिपासा वेग रोध (Suppression of Thirst)",
        "classical_symptoms": ["कण्ठास्यशोष (Dryness of throat and mouth)", "बाधिर्य (Transient hearing impairment)", "हृद्व्यथा (Tachycardia / heart distress)", "भ्रम (Dizziness)"],
        "vitiated_dosha": "Prana Vata & Udakavaha Srotas",
        "secondary_udavarta_risk": "MODERATE",
        "remediation": "Cool soothing Demulcent Mantha, Shadanga Paniya, boiled lukewarm water with coriander and dry ginger."
    },
    AdharaniyaVegaType.BASHPA: {
        "sanskrit": "बाष्प वेग रोध (Suppression of Tears / Grief)",
        "classical_symptoms": ["प्रतिश्याय (Chronic rhinitis)", "अक्षिरोग (Ocular disorders)", "हृद्रोग (Psychosomatic heart disease)", "मन्यास्तम्भ (Neck stiffness)", "अरुचि (Anorexia)"],
        "vitiated_dosha": "Prana Vata, Alochaka Pitta & Manas",
        "secondary_udavarta_risk": "HIGH",
        "remediation": "Emotional catharsis, restful sleep (Swapna), comforting discourse (Priya-Katha), mild Drakshasava, head massage with Brahmi Taila."
    },
    AdharaniyaVegaType.SHRAMA_SHWASA: {
        "sanskrit": "श्रमश्वास वेग रोध (Suppression of Exertional Panting)",
        "classical_symptoms": ["गुल्म (Abdominal lump/phantom tumor)", "हृद्रोग (Cardiac arrhythmia/distress)", "संमोह (Syncope / loss of consciousness)"],
        "vitiated_dosha": "Prana Vata & Udana Vata",
        "secondary_udavarta_risk": "HIGH",
        "remediation": "Immediate complete rest, fan with cool breeze, warm nourishing milk or meat soup (Mamsarasa)."
    },
    AdharaniyaVegaType.NIDRA: {
        "sanskrit": "निद्रा वेग रोध (Suppression of Sleep)",
        "classical_symptoms": ["जृम्भा (Excessive yawning)", "अङ्गमर्द (Generalized aches)", "तन्द्रा (Stupor / Drowsiness)", "शिरोरोग (Headache)", "अक्षिगौरव (Heaviness in eyes)"],
        "vitiated_dosha": "Tarpaka Kapha & Vyana Vata",
        "secondary_udavarta_risk": "HIGH",
        "remediation": "Restful sound sleep, gentle head and body massage (Samvahana), warm milk with Nutmeg and Ghee."
    },
}

# ==============================================================================
# DATABASE INITIALIZATION & SEEDING ENGINE
# ==============================================================================

def initialize_swasthavritta_tables(conn: sqlite3.Connection) -> None:
    """Populate swasthavritta_dinacharya_catalog and swasthavritta_ritucharya_catalog if unseeded."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM swasthavritta_dinacharya_catalog;")
    row = cursor.fetchone()
    if row and row["cnt"] == 0:
        now = int(time.time())
        for step in SEED_DINACHARYA_STEPS:
            cursor.execute(
                """
                INSERT INTO swasthavritta_dinacharya_catalog (
                    step_id, step_name, sanskrit_name, ideal_time_window,
                    doshic_benefit, description, contraindications_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    step.step_id,
                    step.step_name,
                    step.sanskrit_name,
                    step.ideal_time_window,
                    step.doshic_benefit,
                    step.description,
                    json.dumps(step.contraindications),
                    now,
                )
            )

        for ritu in SEED_RITUCHARYA_CATALOG:
            cursor.execute(
                """
                INSERT INTO swasthavritta_ritucharya_catalog (
                    ritu_code, ritu_name, sanskrit_name, ayana,
                    english_months, dominant_rasa, dominant_mahabhuta,
                    doshic_sanchaya, doshic_prakopa, doshic_prashamana,
                    indicated_shodhana, pathya_ahara_json, apathya_ahara_json,
                    pathya_vihara_json, apathya_vihara_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    ritu.ritu_code.value,
                    ritu.ritu_name,
                    ritu.sanskrit_name,
                    ritu.ayana.value,
                    ritu.english_months,
                    ritu.dominant_rasa,
                    ritu.dominant_mahabhuta,
                    ritu.doshic_sanchaya,
                    ritu.doshic_prakopa,
                    ritu.doshic_prashamana,
                    ritu.indicated_shodhana,
                    json.dumps(ritu.pathya_ahara),
                    json.dumps(ritu.apathya_ahara),
                    json.dumps(ritu.pathya_vihara),
                    json.dumps(ritu.apathya_vihara),
                    now,
                )
            )
        conn.commit()


# ==============================================================================
# CIRCADIAN DOSHIC BIO-RHYTHM CLOCK ENGINE
# ==============================================================================

def evaluate_circadian_bio_rhythm(target_time: Optional[datetime] = None) -> CircadianClockStatus:
    """
    Computes real-time or designated circadian bio-rhythm, identifying active dosha,
    ideal clinical actions, and doshic contraindications.
    """
    dt = target_time or datetime.now()
    hour = dt.hour
    minute = dt.minute
    time_str = dt.strftime("%I:%M %p")

    # 24-hour Ayurvedic bio-clock segmentation
    if 2 <= hour < 6:
        period = CircadianPeriod.BRAHMA_MUHURTA
        dosha = "Vata (Predawn lightness, awakening, and natural urge evacuation)"
        recommended = ["Awakening (Brahme Muhurte)", "Meditation / Pranayama", "Warm water drinking (Ushapana)", "Bowel and bladder evacuation"]
        contraindicated = ["Heavy eating", "Sleeping past sunrise (causes Kapha block)", "Strenuous physical labor"]
        advisory = "Brahma Muhurta represents the golden window of neuroplasticity and Vata-governed evacuation. Rising now ensures clarity."
    elif 6 <= hour < 10:
        period = CircadianPeriod.KAPHA_MORNING
        dosha = "Kapha (Morning density, physical strength, sluggish metabolism)"
        recommended = ["Vyayama (Physical exercise up to half capacity)", "Abhyanga (Warm oil massage)", "Snana (Warm therapeutic bath)", "Light breakfast (Yava, Mudga)"]
        contraindicated = ["Daytime sleep", "Cold, heavy, creamy foods", "Sedentary lethargy"]
        advisory = "Kapha is naturally heavy in the morning. Vigorous exercise and oil massage break up stagnation and kindle Agni."
    elif 10 <= hour < 14:
        period = CircadianPeriod.PITTA_MIDDAY
        dosha = "Pitta (Midday solar peak, maximum enzymatic capacity, highest Jatharagni)"
        recommended = ["Principal / heaviest meal of the day (Madhyahna Bhojana)", "Digestive walk of 100 steps (Shatapadi)", "Productive mental focus"]
        contraindicated = ["Skipping lunch (causes Pitta erosions/hyperacidity)", "Harsh direct sun exposure", "Anger and conflict"]
        advisory = "Pachaka Pitta peaks between 11 AM and 1 PM. Consume your primary nourishing meal during this window for complete digestion."
    elif 14 <= hour < 18:
        period = CircadianPeriod.VATA_AFTERNOON
        dosha = "Vata (Afternoon mobility, lightness, heightened sensory perception)"
        recommended = ["Creative thinking, strategic work, writing", "Hydration with warm herbal tea", "Light healthy snack if hungry"]
        contraindicated = ["Day sleeping (Diva-swapna causes Meda/Kapha blockage)", "Excessive multi-tasking", "Dry cold drinks"]
        advisory = "Vata governs the afternoon hours. Maintain mental focus and avoid daytime naps which vitiate Kapha."
    elif 18 <= hour < 22:
        period = CircadianPeriod.KAPHA_EVENING
        dosha = "Kapha (Evening cooling, winding down, parasympathetic tone)"
        recommended = ["Light early dinner before 8 PM (Laghu Bhojana)", "Relaxing reading, gentle conversation", "Foot massage (Pada-Abhyanga) before bed"]
        contraindicated = ["Late night heavy dinners after 9 PM", "Curd consumption at night (Nishi Dadhi)", "Blue light screen stimulation"]
        advisory = "Digestion slows as Kapha dominates the evening. Eat lightly and retire before 10 PM to protect Agni."
    else:  # 22:00 to 02:00
        period = CircadianPeriod.PITTA_NIGHT
        dosha = "Pitta (Internal metabolic cellular regeneration, liver detox, Ahara Paka)"
        recommended = ["Deep restorative sleep in total darkness", "Internal metabolic healing"]
        contraindicated = ["Night vigil (Ratri Jagarana causes severe Vata-Pitta vitiation)", "Midnight snacking", "Screen exposure"]
        advisory = "Between 10 PM and 2 AM, Pitta works on internal cellular purification and liver metabolism. Staying awake disrupts hormonal homeostasis."

    return CircadianClockStatus(
        current_time_str=time_str,
        active_period=period,
        dominant_dosha=dosha,
        recommended_activities=recommended,
        contraindicated_activities=contraindicated,
        clinical_advisory=advisory
    )


# ==============================================================================
# PATIENT LIFESTYLE & DINACHARYA ROUTINE AUDIT ENGINE
# ==============================================================================

def audit_patient_dinacharya_routine(
    req: DinacharyaRoutineAuditRequest,
    hospital_id: str,
    conn: sqlite3.Connection
) -> DinacharyaRoutineAuditResponse:
    """
    Audits a patient's reported daily routine against canonical Dinacharya principles,
    calculates a compliance score (0-100), detects bio-rhythm misalignments,
    and produces actionable corrective lifestyle prescriptions.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM patients WHERE patient_id = ?;", (req.patient_id,))
    if not cursor.fetchone():
        raise RecordNotFoundException("Patient", req.patient_id)

    score = 0.0
    risks: List[str] = []
    recommendations: List[str] = []

    # 1. Wake-up time analysis
    wake_clean = req.wake_up_time.upper().strip()
    is_early_wake = any(t in wake_clean for t in ["04:", "05:", "4:", "5:"]) and "AM" in wake_clean
    is_moderate_wake = any(t in wake_clean for t in ["06:", "6:"]) and "AM" in wake_clean
    is_late_wake = any(t in wake_clean for t in ["07:", "08:", "09:", "10:", "7:", "8:", "9:", "10:"]) and "AM" in wake_clean

    if is_early_wake:
        score += 25.0
    elif is_moderate_wake:
        score += 15.0
    else:
        risks.append("KAPHA_ACCUMULATION_DELAYED_RISING: Waking after 7:00 AM causes sluggishness, heaviness (Gaurava), and channel blockage.")
        recommendations.append("Shift wake-up time progressively earlier toward Brahma Muhurta (05:00 - 05:30 AM).")

    # 2. Bedtime analysis
    bed_clean = req.bed_time.upper().strip()
    is_early_bed = any(t in bed_clean for t in ["09:", "10:", "9:", "10:"]) and "PM" in bed_clean
    is_moderate_bed = any(t in bed_clean for t in ["11:", "11:"]) and "PM" in bed_clean
    is_late_bed = ("AM" in bed_clean) or ("12:" in bed_clean) or ("01:" in bed_clean)

    if is_early_bed:
        score += 25.0
    elif is_moderate_bed:
        score += 15.0
    else:
        risks.append("RATRI_JAGARANA_PITTA_VATA_PROVOCATION: Sleeping past 11:30 PM depletes Ojas, overheats Pitta, and provokes Ruksha Vata.")
        recommendations.append("Establish a consistent sleep schedule retiring by 10:15 PM to align with circadian repair cycles.")

    # 3. Daytime sleep (Diva-swapna)
    if req.has_daytime_nap:
        score = max(0.0, score - 15.0)
        risks.append("DIVASWAPNA_KAPHA_MEDA_VRIDDHI: Sleeping during daytime provokes Kapha-Pitta, slows metabolic rate, and fosters Ama.")
        recommendations.append("Discontinue daytime napping. If fatigued, practice sitting quiet breathing or Shavasana for 10 minutes.")
    else:
        score += 10.0

    # 4. Exercise habit
    ex_habit = req.exercise_habit.upper()
    if ex_habit in ["MODERATE", "LIGHT"]:
        score += 15.0
    elif ex_habit == "NONE":
        risks.append("LACK_OF_VYAYAMA: Sedentary lifestyle leads to Sthaulya, Agnimandya, and joint stiffness.")
        recommendations.append("Incorporate daily morning Ardha-Shakti exercise (e.g. 20-30 minutes brisk walking or Surya Namaskara).")
    elif ex_habit == "EXCESSIVE":
        risks.append("ATI_VYAYAMA_VATA_KSHAYA: Strenuous over-exertion beyond half-capacity depletes Dhatus and exhausts Vata.")
        recommendations.append("Moderate exercise intensity to Ardha-Shakti (stop when forehead perspiration begins).")

    # 5. Dinacharya specific practices
    practices_count = len(req.dinacharya_practices)
    practices_score = min(25.0, practices_count * 5.0)
    score += practices_score

    if "ABHYANGA" not in [p.upper() for p in req.dinacharya_practices]:
        recommendations.append("Adopt regular warm oil Abhyanga (especially on head, ears, and soles) to nourish nerves and pacify Vata.")
    if "PRATIMARSHA_NASYA" not in [p.upper() for p in req.dinacharya_practices] and "NASYA" not in [p.upper() for p in req.dinacharya_practices]:
        recommendations.append("Initiate daily Pratimarsha Nasya with 2 drops of Anu Taila in each nostril every morning.")

    final_score = round(min(100.0, max(0.0, score)), 1)
    if final_score >= 80.0:
        alignment = "OPTIMAL"
    elif final_score >= 50.0:
        alignment = "MODERATE"
    else:
        alignment = "DYSREGULATED"

    now = int(time.time())
    audit_id = f"LIFESTYLE-{req.patient_id}-{now}"

    # Persist in patient_lifestyle_evaluations
    cursor.execute(
        """
        INSERT INTO patient_lifestyle_evaluations (
            evaluation_id, patient_id, hospital_id, evaluation_type,
            score, findings_json, recommendations_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            audit_id,
            req.patient_id,
            hospital_id,
            "DINACHARYA_AUDIT",
            final_score,
            json.dumps(risks),
            json.dumps(recommendations),
            now,
        )
    )
    conn.commit()

    return DinacharyaRoutineAuditResponse(
        audit_id=audit_id,
        patient_id=req.patient_id,
        compliance_score=final_score,
        circadian_alignment=alignment,
        doshic_vitiation_risks=risks,
        corrective_recommendations=recommendations,
        created_at=now,
    )


# ==============================================================================
# ADHARANIYA VEGA SUPPRESSION & UDAVARTA PATHOLOGY ENGINE
# ==============================================================================

def log_and_evaluate_vega_suppression(
    req: VegaSuppressionLogRequest,
    hospital_id: str,
    conn: sqlite3.Connection
) -> VegaPathologyResponse:
    """
    Evaluates chronic suppression of any of the 13 non-suppressible urges (Adharaniya Vegas),
    calculates risk of secondary Udavarta, and formulates classical reversal therapy.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM patients WHERE patient_id = ?;", (req.patient_id,))
    if not cursor.fetchone():
        raise RecordNotFoundException("Patient", req.patient_id)

    vega_meta = ADHARANIYA_VEGAS_DATA.get(req.vega_type)
    if not vega_meta:
        raise ClinicalGovernanceException(f"Invalid Adharaniya Vega type: {req.vega_type}")

    classical_symptoms = vega_meta["classical_symptoms"]
    vitiated_dosha = vega_meta["vitiated_dosha"]
    base_risk = vega_meta["secondary_udavarta_risk"]

    # If duration > 12 months or daily frequency, escalate risk
    calculated_risk = base_risk
    if req.frequency.upper() == "DAILY" and req.duration_months >= 6:
        if base_risk in ["HIGH", "CRITICAL"]:
            calculated_risk = "CRITICAL"
        else:
            calculated_risk = "HIGH"

    remediation = vega_meta["remediation"]

    now = int(time.time())
    log_id = f"VEGA-{req.patient_id}-{now}"

    # Persist in patient_vega_suppression_logs
    cursor.execute(
        """
        INSERT INTO patient_vega_suppression_logs (
            log_id, patient_id, hospital_id, vega_type,
            frequency, duration_months, manifestations_json,
            secondary_udavarta_risk, remediation_plan, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            log_id,
            req.patient_id,
            hospital_id,
            req.vega_type.value,
            req.frequency,
            req.duration_months,
            json.dumps(classical_symptoms),
            calculated_risk,
            remediation,
            now,
        )
    )
    conn.commit()

    return VegaPathologyResponse(
        log_id=log_id,
        patient_id=req.patient_id,
        vega_type=req.vega_type,
        classical_manifestations=classical_symptoms,
        secondary_udavarta_risk=calculated_risk,
        primary_vitiated_dosha=vitiated_dosha,
        remediation_protocol=remediation,
        created_at=now,
    )


# ==============================================================================
# RITUCHARYA (SEASONAL) CALENDAR & RITUSANDHI FIREWALL ENGINE
# ==============================================================================

def get_seasonal_calendar(conn: sqlite3.Connection) -> List[SeasonalRegimenProfile]:
    """Retrieve full annual 6-season profile from catalog."""
    initialize_swasthavritta_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM swasthavritta_ritucharya_catalog ORDER BY ritu_code ASC;")
    rows = cursor.fetchall()
    results: List[SeasonalRegimenProfile] = []
    for r in rows:
        results.append(
            SeasonalRegimenProfile(
                ritu_code=RituCode(r["ritu_code"]),
                ritu_name=r["ritu_name"],
                sanskrit_name=r["sanskrit_name"],
                ayana=Ayana(r["ayana"]),
                english_months=r["english_months"],
                dominant_rasa=r["dominant_rasa"],
                dominant_mahabhuta=r["dominant_mahabhuta"],
                doshic_sanchaya=r["doshic_sanchaya"],
                doshic_prakopa=r["doshic_prakopa"],
                doshic_prashamana=r["doshic_prashamana"],
                indicated_shodhana=r["indicated_shodhana"],
                pathya_ahara=json.loads(r["pathya_ahara_json"]),
                apathya_ahara=json.loads(r["apathya_ahara_json"]),
                pathya_vihara=json.loads(r["pathya_vihara_json"]),
                apathya_vihara=json.loads(r["apathya_vihara_json"]),
            )
        )
    return results


def evaluate_current_ritucharya(eval_date: Optional[datetime] = None) -> RitusandhiEvaluation:
    """
    Determines active Ritu based on solar month, detects whether date falls in the 14-day
    Ritusandhi vulnerability window, and reports indicated seasonal Shodhana and Padamshika Krama.
    """
    dt = eval_date or datetime.now()
    month = dt.month
    day = dt.day

    # Determine Ritu based on classical Indian solar calendar
    # Shishira: Jan 15 - Mar 14
    # Vasanta:  Mar 15 - May 14
    # Grishma:  May 15 - Jul 14
    # Varsha:   Jul 15 - Sep 14
    # Sharad:   Sep 15 - Nov 14
    # Hemanta:  Nov 15 - Jan 14

    day_of_year_scaled = month * 100 + day

    if 115 <= day_of_year_scaled < 315:
        active = RituCode.SHISHIRA
        transition_target = RituCode.VASANTA
        days_to_boundary = abs(315 - day_of_year_scaled)
        shodhana = "None indicated during Shishira. High Jatharagni; nourishing regimen."
    elif 315 <= day_of_year_scaled < 515:
        active = RituCode.VASANTA
        transition_target = RituCode.GRISHMA
        days_to_boundary = abs(515 - day_of_year_scaled)
        shodhana = "MANDATORY VAMANA KARMA (Therapeutic emesis) to evacuate liquefied spring Kapha."
    elif 515 <= day_of_year_scaled < 715:
        active = RituCode.GRISHMA
        transition_target = RituCode.VARSHA
        days_to_boundary = abs(715 - day_of_year_scaled)
        shodhana = "Shodhana contraindicated due to extreme debility (Alpa Bala); cooling hydration."
    elif 715 <= day_of_year_scaled < 915:
        active = RituCode.VARSHA
        transition_target = RituCode.SHARAD
        days_to_boundary = abs(915 - day_of_year_scaled)
        shodhana = "MANDATORY BASTI KARMA (Medicated enema) to pacify provoked monsoon Vata."
    elif 915 <= day_of_year_scaled < 1115:
        active = RituCode.SHARAD
        transition_target = RituCode.HEMANTA
        days_to_boundary = abs(1115 - day_of_year_scaled)
        shodhana = "MANDATORY VIRECHANA KARMA & RAKTAMOKSHANA for autumn Pitta clearance."
    else:
        active = RituCode.HEMANTA
        transition_target = RituCode.SHISHIRA
        days_to_boundary = abs(115 - day_of_year_scaled) if day_of_year_scaled < 115 else abs(1231 - day_of_year_scaled)
        shodhana = "Shodhana not required; peak strength (Pravara Bala); ideal for Rasayana."

    # Ritusandhi check: within 7 days before or after season boundary (approx days 8 to 22 of month)
    is_sandhi = (day <= 7 or day >= 23)
    transition_note = None
    padamshika = None

    if is_sandhi:
        transition_note = (
            f"VULNERABLE RITUSANDHI TRANSITION: Currently within the 14-day inter-seasonal sandhi window "
            f"approaching {transition_target.value}. Abrupt changes in diet or regimen precipitate acute Doshic outbreaks."
        )
        padamshika = (
            "PADAMSHIKA KRAMA MANDATED: Discontinue previous seasonal practices gradually by 1/4th each day "
            "while adopting incoming seasonal regimen by 1/4th each day over 7-14 days."
        )

    advisory_map = {
        RituCode.SHISHIRA: "Late Winter: Nourish high digestive fire with warm rich foods. Avoid cold water.",
        RituCode.VASANTA: "Spring: Kapha liquefies in sun. Vamana Shodhana is clinically indicated. Strictly avoid day sleep.",
        RituCode.GRISHMA: "Summer: Solar heat depletes bodily strength. Stay in cool shade, hydrate with sweet cooling liquids.",
        RituCode.VARSHA: "Monsoon: Cold rains provoke Vata while dampness fosters Pitta. Basti therapy indicated. Drink boiled water.",
        RituCode.SHARAD: "Autumn: Autumn sun flares accumulated Pitta. Virechana and Raktamokshana indicated. Take Hansodaka.",
        RituCode.HEMANTA: "Early Winter: Peak physical endurance and strong digestion. Exercise, oil massage, and rich nutrition indicated."
    }

    doshic_state_map = {
        RituCode.SHISHIRA: {"Vata": "SANCHAYA_BEGINS", "Pitta": "PRASHAMANA", "Kapha": "ACCUMULATES_FROZEN"},
        RituCode.VASANTA: {"Vata": "SAMA", "Pitta": "SAMA", "Kapha": "PRAKOPA"},
        RituCode.GRISHMA: {"Vata": "SANCHAYA", "Pitta": "SAMA", "Kapha": "PRASHAMANA"},
        RituCode.VARSHA: {"Vata": "PRAKOPA", "Pitta": "SANCHAYA", "Kapha": "SAMA"},
        RituCode.SHARAD: {"Vata": "PRASHAMANA", "Pitta": "PRAKOPA", "Kapha": "SAMA"},
        RituCode.HEMANTA: {"Vata": "SAMA", "Pitta": "PRASHAMANA", "Kapha": "SANCHAYA"}
    }

    return RitusandhiEvaluation(
        evaluated_date=dt.strftime("%Y-%m-%d"),
        active_ritu=active,
        in_ritusandhi=is_sandhi,
        transition_note=transition_note,
        padamshika_krama_rule=padamshika,
        active_doshic_state=doshic_state_map.get(active, {}),
        recommended_seasonal_shodhana=shodhana,
        seasonal_advisory=advisory_map.get(active, "")
    )
