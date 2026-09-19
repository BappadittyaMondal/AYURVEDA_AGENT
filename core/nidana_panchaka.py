"""
Nidana Panchaka Diagnostic Knowledge Graph & Differential Diagnosis Engine
========================================================================
Core computational engine implementing the classical 5-fold Ayurvedic diagnostic methodology:
1. Nidana (Etiological causality matching)
2. Purvaroopa (Prodromal symptom correlation)
3. Roopa (Pathognomonic hallmark / Pratyatma Linga & cardinal symptom scoring)
4. Upashaya / Anupashaya (Therapeutic diagnostic trial verification)
5. Samprapti (Complete pathogenetic matrix & Ghatakas decomposition)
"""

from __future__ import annotations
import json
import time
import uuid
import sqlite3
from typing import Dict, List, Optional, Tuple

from models.nidana_panchaka import (
    NidanaPanchakaEvaluationInput,
    NidanaPanchakaEvaluationOutput,
    DifferentialDiagnosisItem,
    DiseaseArchetype,
    SampraptiGhatakas,
    AgniState,
    AmaStatus,
    Rogamarga,
    SrotodushtiPattern,
    CurabilityPrognosis,
    UpashayaOutcome,
)


# ==============================================================================
# CLASSICAL REFERENCE KNOWLEDGE GRAPH: 10 DISEASE ARCHETYPES
# ==============================================================================

DISEASE_ARCHETYPE_REGISTRY: Dict[str, DiseaseArchetype] = {
    "AMAVATA": DiseaseArchetype(
        code="AMAVATA",
        sanskrit_name="आमवात",
        english_name="Rheumatoid Arthropathy / Endotoxin-Induced Arthritis",
        doshic_predominance=["Vata", "Kapha"],
        nidanas=[
            "Viruddha Ahara (Incompatible diet)",
            "Snigdha Bhojana followed by heavy exercise (Vyayama)",
            "Mandagni (Impaired digestive bio-fire)",
            "Divaswapna (Daytime sleeping)",
            "Nishchalata (Sedentary physical inactivity)"
        ],
        purvaroopas=[
            "Alasya (Lethargy and lassitude)",
            "Gaurava (Generalized heaviness of the body)",
            "Aruchi (Loss of taste and anorexia)",
            "Trishna (Excessive thirst)",
            "Apaka (Indigestion and delayed gastric emptying)"
        ],
        roopas=[
            "Sandhi Shula (Excruciating joint pain)",
            "Sandhi Shotha (Bilateral joint swelling)",
            "Stambha (Severe morning stiffness)",
            "Angamarda (Generalized body aches)",
            "Jwara (Low to moderate pyrexia)",
            "Agnimandya (Sluggish metabolism)",
            "Kukshi Shula (Abdominal cramps with sluggish bowel)"
        ],
        pratyatma_lingas=[
            "Vrischika Damshavat Shula (Excruciating joint pain resembling scorpion sting)",
            "Morning Stambha in peripheral joints with swelling",
            "Sinking Ama stool with profound systemic Gaurava"
        ],
        beneficial_upashayas=[
            "Langhana (Fasting / therapeutic starvation)",
            "Ruksha Sweda (Dry sand/Valuka fomentation)",
            "Tikta-Katu Deepana (Panchakola / Shunthi decoctions)",
            "Ushna Jala (Warm water drinking)"
        ],
        aggravating_anupashayas=[
            "Snehadravya (Unctuous oil massage / heavy ghee)",
            "Sheeta Ahara (Cold drinks, ice, refrigerants)",
            "Snigdha Sweda (Moist steam bath)",
            "Divaswapna (Daytime nap)"
        ],
        samprapti_ghatakas=SampraptiGhatakas(
            primary_dosha="Vata",
            secondary_doshas=["Kapha"],
            dushya=["Rasa", "Asthi", "Sandhi", "Snayu"],
            agni=AgniState.MANDAGNI,
            ama=AmaStatus.SAMA,
            srotas=["Rasavaha", "Asthivaha", "Annavaha"],
            srotodushti=[SrotodushtiPattern.SANGA, SrotodushtiPattern.VIMARGA_GAMANA],
            udbhava_sthana="Amashaya (Stomach / Upper digestive tract)",
            sanchara_sthana="Rasayani / Sarva Sharira (Systemic vascular channels)",
            vyakti_sthana="Sandhi / Trika / Hridaya (Joints, sacrum, heart)",
            rogamarga=Rogamarga.MADHYAMA
        ),
        curability=CurabilityPrognosis.KRICHRASADHYA
    ),

    "SANDHIGATA_VATA": DiseaseArchetype(
        code="SANDHIGATA_VATA",
        sanskrit_name="सन्धिगत वात",
        english_name="Osteoarthropathy / Degenerative Joint Disease",
        doshic_predominance=["Vata"],
        nidanas=[
            "Ruksha-Sheeta Ahara (Dry, cold, stale, deficient diet)",
            "Dhatukshaya (Degenerative tissue wasting)",
            "Ati-vyayama (Excessive mechanical joint strain)",
            "Abhighata (Trauma or past joint injury)",
            "Vridhavastha (Senile degeneration / advanced age)"
        ],
        purvaroopas=[
            "Subtle joint stiffness on cold exposure",
            "Occasional non-inflammatory crepitation",
            "Dryness of skin over joints"
        ],
        roopas=[
            "Sandhi Shula during motion (Mechanical joint pain)",
            "Vata Purna Driti Sparsha (Bag of air sensation / soft crepitant effusion)",
            "Sandhi Sphutana (Joint crackling sound on movement)",
            "Prasarana Akunchana Pravritti Vedana (Pain on flexion and extension)",
            "Absence of fever or systemic endotoxin symptoms"
        ],
        pratyatma_lingas=[
            "Vata Purna Driti Sparsha (Palpatory sensation of an air-filled leather pouch)",
            "Sandhi Sphutana on active movement",
            "Prasarana Akunchana Vedana without systemic fever or Ama"
        ],
        beneficial_upashayas=[
            "Abhyanga (Warm medicinal oil massage like Mahanarayana)",
            "Snigdha Sweda (Moist unctuous fomentation)",
            "Ushna Upachara (Warm heating pads)",
            "Brimhana Ahara (Nourishing, unctuous diet)"
        ],
        aggravating_anupashayas=[
            "Ruksha Sweda (Dry sand heat accelerates degeneration)",
            "Langhana (Starvation / fasting worsens Vata)",
            "Sheeta Vihara (Cold drafts, air-conditioning)",
            "Excess walking / load-bearing"
        ],
        samprapti_ghatakas=SampraptiGhatakas(
            primary_dosha="Vata",
            secondary_doshas=[],
            dushya=["Asthi", "Majja", "Sandhi", "Snayu"],
            agni=AgniState.VISHAMAGNI,
            ama=AmaStatus.NIRAMA,
            srotas=["Asthivaha", "Majjavaha"],
            srotodushti=[SrotodushtiPattern.SANGA],
            udbhava_sthana="Pakvashaya (Colon / Pelvic seat of Vata)",
            sanchara_sthana="Vatavaha Srotas",
            vyakti_sthana="Janu / Kati / Greeva Sandhi (Knees, spine, neck)",
            rogamarga=Rogamarga.MADHYAMA
        ),
        curability=CurabilityPrognosis.KRICHRASADHYA
    ),

    "VATARAKTA": DiseaseArchetype(
        code="VATARAKTA",
        sanskrit_name="वातरक्त",
        english_name="Gout / Metabolic Microvascular Arthropathy",
        doshic_predominance=["Vata", "Pitta"],
        nidanas=[
            "Lavana, Amla, Katu, Ushna Ahara (Salty, sour, spicy, hot foods)",
            "Dadhi (Curds), Kulattha (Horse gram), Masha (Black gram)",
            "Madya (Alcohol / fermented beverages)",
            "Sukhumara Sukhibhoji (Sedentary luxury with rich diets)",
            "Ashwa-Gaja-Yana (Excessive vehicular vibration / riding)"
        ],
        purvaroopas=[
            "Kara-Pada Suptata (Numbness or pins-and-needles in hands/feet)",
            "Sparshajnana (Transient sensory hyperesthesia)",
            "Ati-Sveda or Asveda (Profuse local sweating or complete anhidrosis)",
            "Toda in Padangustha (Subtle pricking sensation in the great toe)"
        ],
        roopas=[
            "Padangustha Shula (Acute throbbing pain starting in the big toe)",
            "Raga (Intense erythema / purplish-red discoloration)",
            "Daha (Severe burning agony in the affected joint)",
            "Shyava-Tamra Varna (Coppery or dusky swelling)",
            "Nocturnal aggravation with hyperalgesia (Vrischika/Akshu-vat)",
            "Shifting peripheral joint involvement"
        ],
        pratyatma_lingas=[
            "Padangustha Mula Shotha with Raga (Acute erythematous inflammation of the 1st MTP joint)",
            "Daha and Toda with Shyava-Tamra discoloration",
            "Teevra nocturnal hyperalgesia aggravated by slight touch"
        ],
        beneficial_upashayas=[
            "Raktamokshana (Jalaukavacharana / therapeutic leeching)",
            "Sheeta Pradeha (Cool medicinal paste application)",
            "Guduchi and Manjistha decoctions",
            "Virechana (Therapeutic purgation)"
        ],
        aggravating_anupashayas=[
            "Ushna Lepa (Warm or heating pastes exacerbate burning)",
            "Madya / Alcohol consumption",
            "Lavana-Katu rich diet",
            "Atapa Sevana (Direct sun exposure)"
        ],
        samprapti_ghatakas=SampraptiGhatakas(
            primary_dosha="Vata",
            secondary_doshas=["Pitta"],
            dushya=["Rakta", "Tvak", "Mamsa"],
            agni=AgniState.TIKSHNAGNI,
            ama=AmaStatus.NIRAMA,
            srotas=["Raktavaha", "Rasavaha"],
            srotodushti=[SrotodushtiPattern.SANGA, SrotodushtiPattern.VIMARGA_GAMANA],
            udbhava_sthana="Pakvashaya and Raktashaya",
            sanchara_sthana="Raktavaha Srotas / Shakha",
            vyakti_sthana="Padangustha / Kara-Pada Sandhi (First MTP joint, small joints)",
            rogamarga=Rogamarga.BAHYA
        ),
        curability=CurabilityPrognosis.KRICHRASADHYA
    ),

    "JWARA_VATAJA": DiseaseArchetype(
        code="JWARA_VATAJA",
        sanskrit_name="वातज ज्वर",
        english_name="Vataja Pyrexia (Irregular Febrile Syndrome)",
        doshic_predominance=["Vata"],
        nidanas=[
            "Ruksha-Laghu Ahara (Deficient, dry diet)",
            "Upavasa (Excessive fasting)",
            "Ratrijagarana (Late night wakefulness)",
            "Ativyayama (Physical exhaustion)",
            "Shoka / Bhaya (Grief, anxiety, psychological stress)"
        ],
        purvaroopas=[
            "Jrumbhadhikya (Excessive repeated yawning)",
            "Romaharsha (Horripilation / goosebumps)",
            "Angamarda (Generalized muscle aches)"
        ],
        roopas=[
            "Vishama Vega (Unpredictable, erratic temperature spikes)",
            "Parva Bheda (Excruciating aching in interphalangeal joints)",
            "Dantaharsha (Hypersensitive teeth)",
            "Shirograha (Tension headache / cephalalgia)",
            "Asya Vairasya (Astringent, tasteless mouth)",
            "Tvak Rukshata (Severe cutaneous dryness)"
        ],
        pratyatma_lingas=[
            "Vishama Vega (Irregular temperature fluctuations with chills)",
            "Jrumbhadhikya with Romaharsha",
            "Parvabheda with generalized hyperesthesia"
        ],
        beneficial_upashayas=[
            "Ushna Paniya (Warm medicated fluids)",
            "Snigdha-Ushna Vata Shamana decoctions (Dashamula)",
            "Rest in warm unexposed room"
        ],
        aggravating_anupashayas=[
            "Sheeta Sparsha / Pravata (Cold drafts of wind)",
            "Upavasa (Prolonged fasting)",
            "Cold drinks or ice"
        ],
        samprapti_ghatakas=SampraptiGhatakas(
            primary_dosha="Vata",
            secondary_doshas=[],
            dushya=["Rasa", "Sweda"],
            agni=AgniState.VISHAMAGNI,
            ama=AmaStatus.SAMA,
            srotas=["Rasavaha", "Swedavaha"],
            srotodushti=[SrotodushtiPattern.SANGA, SrotodushtiPattern.VIMARGA_GAMANA],
            udbhava_sthana="Amashaya (Stomach)",
            sanchara_sthana="Sarva Sharira (Systemic circulation)",
            vyakti_sthana="Tvak (Skin / Thermoregulatory surface)",
            rogamarga=Rogamarga.ABHYANTARA
        ),
        curability=CurabilityPrognosis.SUKHASADHYA
    ),

    "JWARA_PITTAJA": DiseaseArchetype(
        code="JWARA_PITTAJA",
        sanskrit_name="पित्तज ज्वर",
        english_name="Pittaja Pyrexia (High-Grade Inflammatory Febrile Syndrome)",
        doshic_predominance=["Pitta"],
        nidanas=[
            "Katu-Amla-Lavana Ahara (Sharp, pungent, sour, salty foods)",
            "Ushna-Tikshna substances",
            "Atapa (Direct scorching sunlight exposure)",
            "Krodha (Intense anger / emotional outburst)",
            "Agni Sevana (Working near intense furnaces / heat)"
        ],
        purvaroopas=[
            "Nayana Dvesha (Marked photophobia)",
            "Tikta Asyata (Bitter taste in mouth)",
            "Santapa (Internal burning sensation before fever)"
        ],
        roopas=[
            "Teekshna Jwara (Continuous high-grade fever)",
            "Daha (Intense internal and external burning heat)",
            "Trishna (Unquenchable intense thirst)",
            "Sweda Pravritti (Profuse sweating with strong odor)",
            "Pralapa (Delirious speech during peak temperature)",
            "Peeta Mutra-Netra-Tvak (Yellowish sclera, urine, and skin)"
        ],
        pratyatma_lingas=[
            "Teekshna Jwara with Generalized Burning (Santapa)",
            "Pitta Vamana with Tikta Asyata (Bitter emesis and parched tongue)",
            "Profuse sweating with persistent hyperpyrexia"
        ],
        beneficial_upashayas=[
            "Sheeta Upachara (Cool sponging, cool ambient room)",
            "Tikta-Kashaya Kashaya (Chirayata, Chandana, Usheera)",
            "Tikta Deepana-Pachana"
        ],
        aggravating_anupashayas=[
            "Ushna Ahara / Hot spices",
            "Direct sunlight exposure",
            "Fermented beverages or alcohol"
        ],
        samprapti_ghatakas=SampraptiGhatakas(
            primary_dosha="Pitta",
            secondary_doshas=[],
            dushya=["Rasa", "Rakta", "Sweda"],
            agni=AgniState.TIKSHNAGNI,
            ama=AmaStatus.SAMA,
            srotas=["Rasavaha", "Raktavaha", "Swedavaha"],
            srotodushti=[SrotodushtiPattern.ATI_PRAVRITTI, SrotodushtiPattern.SANGA],
            udbhava_sthana="Amashaya",
            sanchara_sthana="Sarva Sharira",
            vyakti_sthana="Tvak and Netra",
            rogamarga=Rogamarga.ABHYANTARA
        ),
        curability=CurabilityPrognosis.SUKHASADHYA
    ),

    "JWARA_KAPHAJA": DiseaseArchetype(
        code="JWARA_KAPHAJA",
        sanskrit_name="कफज ज्वर",
        english_name="Kaphaja Pyrexia (Low-Grade Congestive Febrile Syndrome)",
        doshic_predominance=["Kapha"],
        nidanas=[
            "Snigdha-Guru-Madhura Ahara (Heavy, sweet, unctuous food)",
            "Sheeta Dravya (Cold milk, refrigerated food)",
            "Divaswapna (Daytime sleep)",
            "Avyayama (Sedentary lack of exertion)"
        ],
        purvaroopas=[
            "Praseka (Excessive mucoid salivation)",
            "Aruchi (Severe loss of appetite)",
            "Alasya (Profound mental and motor sluggishness)",
            "Hrillasa (Persistent nausea)"
        ],
        roopas=[
            "Manda Jwara (Low-grade lingering fever)",
            "Gaurava (Profound heaviness of head and body)",
            "Tandra (Stupor, somnolence, drowsiness)",
            "Chhardi (Mucoid vomiting)",
            "Mukhamadhurya (Sweetish taste in oral cavity)",
            "Shweta Jihwa (Thick white coated tongue)"
        ],
        pratyatma_lingas=[
            "Manda Jwara with Extreme Somnolence (Tandra) and Gaurava",
            "Mukhamadhurya with Kaphapraseka (Mucoid hyper-salivation)",
            "Thick unctuous Shweta coating on tongue with loss of appetite"
        ],
        beneficial_upashayas=[
            "Langhana (Therapeutic fasting)",
            "Ruksha Sweda (Dry heat)",
            "Trikatu / Shunthi-Maricha-Pippali hot decoctions",
            "Ushna Jala (Warm water)"
        ],
        aggravating_anupashayas=[
            "Snigdha Ahara (Ghee, milk, dairy, sweets)",
            "Daytime naps (Divaswapna)",
            "Cold humid atmosphere"
        ],
        samprapti_ghatakas=SampraptiGhatakas(
            primary_dosha="Kapha",
            secondary_doshas=[],
            dushya=["Rasa", "Medas", "Sweda"],
            agni=AgniState.MANDAGNI,
            ama=AmaStatus.SAMA,
            srotas=["Rasavaha", "Annavaha", "Swedavaha"],
            srotodushti=[SrotodushtiPattern.SANGA],
            udbhava_sthana="Amashaya",
            sanchara_sthana="Sarva Sharira",
            vyakti_sthana="Tvak and Kostha",
            rogamarga=Rogamarga.ABHYANTARA
        ),
        curability=CurabilityPrognosis.SUKHASADHYA
    ),

    "TAMAKA_SHWASA": DiseaseArchetype(
        code="TAMAKA_SHWASA",
        sanskrit_name="तमत श्वास",
        english_name="Bronchial Asthma / Paroxysmal Obstructive Dyspnea",
        doshic_predominance=["Vata", "Kapha"],
        nidanas=[
            "Raja-Dhooma Sevana (Inhalation of dust, pollen, smoke)",
            "Sheeta Vata (Exposure to cold wind / draft)",
            "Pragvata (Direct exposure to easterly humid winds)",
            "Guru-Sheeta-Abhishyandi Ahara (Cold curds, cheese, heavy sweets)"
        ],
        purvaroopas=[
            "Anaha (Abdominal bloating / distension)",
            "Parshva Shula (Aching pain in lateral chest wall)",
            "Hridaya Peedana (Sensation of cardiac / thoracic constriction)",
            "Prana Pratilomyam (Subtle reversal of breath flow)"
        ],
        roopas=[
            "Teevra Shwasa Krichrata (Acute paroxysmal respiratory distress)",
            "Ghurghuraka (Audible wheezing, rhonchi, chest rattling)",
            "Asino Labhate Saukhyam (Relief exclusively on sitting upright / orthopnea)",
            "Shleshmakrichranishthivanam (Relief following expectoration of sticky mucous)",
            "Kasa with chest tightness",
            "Meghambuvata Prakopa (Aggravation during cloudy, rainy weather)"
        ],
        pratyatma_lingas=[
            "Asino Labhate Saukhyam (Mandatory orthopneic upright posture for relief)",
            "Ghurghuraka Shabda (Audible bronchospastic wheezing)",
            "Shleshmakrichranishthivana with post-expectoration transient relief"
        ],
        beneficial_upashayas=[
            "Asino Avastha (Upright sitting posture)",
            "Lavana-Taila Abhyanga on chest with Nadi Sweda (Warm salt-oil chest compress)",
            "Ushna Paniya (Warm fluids)",
            "Katu-Ushna Vata-Kapha Hara herbs (Kantakari, Vasa, Talisadi)"
        ],
        aggravating_anupashayas=[
            "Shayana (Lying flat supine provokes acute suffocative paroxysm)",
            "Exposure to dust, cold drafts, or smoke",
            "Cold drinks or refrigerated curd",
            "Cloudy, overcast, or raining climate"
        ],
        samprapti_ghatakas=SampraptiGhatakas(
            primary_dosha="Vata",
            secondary_doshas=["Kapha"],
            dushya=["Prana", "Rasa", "Udana"],
            agni=AgniState.MANDAGNI,
            ama=AmaStatus.SAMA,
            srotas=["Pranavaha", "Annavaha", "Udakovaha"],
            srotodushti=[SrotodushtiPattern.SANGA, SrotodushtiPattern.VIMARGA_GAMANA],
            udbhava_sthana="Pittashaya / Amashaya",
            sanchara_sthana="Pranavaha Srotas / Uras (Thoracic cavity)",
            vyakti_sthana="Phupphusa / Uras (Lungs and bronchial airways)",
            rogamarga=Rogamarga.MADHYAMA
        ),
        curability=CurabilityPrognosis.YAPYA
    ),

    "PRAMEHA_KAPHAJA": DiseaseArchetype(
        code="PRAMEHA_KAPHAJA",
        sanskrit_name="कफज प्रमेह",
        english_name="Kaphaja Metabolic Impairment / Pre-Diabetes Mellitus",
        doshic_predominance=["Kapha"],
        nidanas=[
            "Asyasukhya (Excessive sedentary indulgence, sitting all day)",
            "Swapnasukha (Excessive sleep, prolonged diurnal naps)",
            "Dadhi (Excessive curd consumption)",
            "Gramya-Anupa-Audaka Mamsa (Marshy/fatty animal meats)",
            "Nava-Dhanya (Freshly harvested grains), Guda (Jaggery/sugar)"
        ],
        purvaroopas=[
            "Kara-Pada Tala Daha (Burning sensation in palms and soles)",
            "Kara-Pada Suptata (Numbness of extremities)",
            "Dantamaladhikya (Accumulation of thick tartar on teeth)",
            "Mukhashosha (Dryness of mouth despite hydration)",
            "Pipasa (Increased thirst)"
        ],
        roopas=[
            "Prabhoota Mutrata (Copious frequency and volume of urination)",
            "Avila Mutrata (Turbid, cloudy urine)",
            "Madhura Mutrata (Sweet urine attracting insects / glucosuria)",
            "Meda-Dhatu Shaithilya (Flabbiness of muscle and subcutaneous tissues)",
            "Alasya and excessive lethargy"
        ],
        pratyatma_lingas=[
            "Prabhoota Avila Mutrata (Copious turbid polyuria)",
            "Kara-Pada Tala Daha with Pipasa",
            "Madhura Mutrata attracting ants"
        ],
        beneficial_upashayas=[
            "Vyayama (Vigorous regular physical exercise)",
            "Yava Ahara (Barley-dominant coarse grain diet)",
            "Tikta-Kashaya herbs (Asanadi, Triphala, Haridra)",
            "Langhana / Apatarpana"
        ],
        aggravating_anupashayas=[
            "Asyasukhya (Inactivity and prolonged lying down)",
            "Madhura-Snigdha Ahara (Sweets, ghee, dairy)",
            "Divaswapna"
        ],
        samprapti_ghatakas=SampraptiGhatakas(
            primary_dosha="Kapha",
            secondary_doshas=["Pitta", "Vata"],
            dushya=["Meda", "Mamsa", "Kleda", "Shukra", "Rasa"],
            agni=AgniState.MANDAGNI,
            ama=AmaStatus.SAMA,
            srotas=["Mutravaha", "Medovaha", "Udakovaha"],
            srotodushti=[SrotodushtiPattern.ATI_PRAVRITTI],
            udbhava_sthana="Amashaya",
            sanchara_sthana="Sarva Sharira / Medovaha Srotas",
            vyakti_sthana="Basti / Mutravaha Marga (Urinary bladder and kidneys)",
            rogamarga=Rogamarga.ABHYANTARA
        ),
        curability=CurabilityPrognosis.SUKHASADHYA
    ),

    "GRAHANI_DOSHA": DiseaseArchetype(
        code="GRAHANI_DOSHA",
        sanskrit_name="ग्रहणी दोष",
        english_name="Malabsorption Syndrome / Post-Dysenteric Dysbiosis",
        doshic_predominance=["Vata", "Kapha", "Pitta"],
        nidanas=[
            "Abhojana / Atibhojana (Fasting followed by binge eating)",
            "Vishamashana (Eating at irregular hours)",
            "Asatmya Bhojana (Consuming incompatible unwholesome foods)",
            "Vegadharana (Suppression of natural urges)",
            "Suppression of acute diarrhea without resolving toxins"
        ],
        purvaroopas=[
            "Praseka (Excessive salivation)",
            "Gaurava (Abdominal heaviness)",
            "Vidaha (Sour burning sensation during digestion)",
            "Annasya Chirat Paka (Slow sluggish digestion)"
        ],
        roopas=[
            "Muhur Baddha Muhur Shithila Mala (Alternating constipation and loose stools)",
            "Apakva Durgandhita Mala (Undigested, foul-smelling stool with mucus)",
            "Aruchi and Trishna (Loss of appetite with dry throat)",
            "Parikartika (Cutting spasmodic pain before defecation)",
            "Daurbalya (Systemic weakness, weight loss, and fatigue)",
            "Post-prandial abdominal fullness relieved by defecation"
        ],
        pratyatma_lingas=[
            "Muhur Baddha Muhur Shithila Mala (Alternating hard and watery mucus-laden stool)",
            "Apakva Ama-Yukta stool with foul odor",
            "Severe Agnimandya with post-prandial borborygmi and cramps"
        ],
        beneficial_upashayas=[
            "Takra Prayoga (Medicated buttermilk with Pippali, Shunthi, Jeeraka)",
            "Deepana-Pachana drugs (Chitrakadi Vati, Panchakola)",
            "Laghu-Ushna Ahara (Light warm digestible diet)"
        ],
        aggravating_anupashayas=[
            "Guru-Snigdha Ahara (Heavy fats, fried pastries)",
            "Cold, unpasteurized, or stale foods",
            "Irregular meal timing (Vishamashana)"
        ],
        samprapti_ghatakas=SampraptiGhatakas(
            primary_dosha="Vata",
            secondary_doshas=["Pitta", "Kapha"],
            dushya=["Anna", "Rasa", "Purisha"],
            agni=AgniState.MANDAGNI,
            ama=AmaStatus.SAMA,
            srotas=["Annavaha", "Purishavaha"],
            srotodushti=[SrotodushtiPattern.SANGA, SrotodushtiPattern.VIMARGA_GAMANA],
            udbhava_sthana="Grahani / Pachyamanashaya (Duodenum / Upper small intestine)",
            sanchara_sthana="Kostha / Digestive tract",
            vyakti_sthana="Grahani / Pakvashaya (Small and large intestine)",
            rogamarga=Rogamarga.ABHYANTARA
        ),
        curability=CurabilityPrognosis.KRICHRASADHYA
    ),

    "AMLAPITTA": DiseaseArchetype(
        code="AMLAPITTA",
        sanskrit_name="अम्लपित्त",
        english_name="Hyperchlorhydria / Non-Ulcer Dyspepsia (Acid Peptic Disorder)",
        doshic_predominance=["Pitta", "Kapha"],
        nidanas=[
            "Viruddha Ahara (Incompatible dietary combinations)",
            "Vidahi Ahara (Fermented, excessively pungent, deep-fried snacks)",
            "Ati-Ushna / Ati-Lavana Ahara",
            "Kulattha, Masha, Pishtanna (Heavy pulses and stale pastries)",
            "Chinta and Krodha during eating"
        ],
        purvaroopas=[
            "Avipaka (Delayed digestion)",
            "Klama (Fatigue without physical labor)",
            "Utklesha (Nausea with sour salivation)",
            "Tikta-Amla Udgara (Bitter or acidic eructations)"
        ],
        roopas=[
            "Amla-Tikta Udgara (Acid and bitter regurgitation / heartburn)",
            "Hrit-Kantha Daha (Burning sensation in chest and throat)",
            "Aruchi (Aversion to food)",
            "Kukshi Daha (Burning distress in epigastrium)",
            "Chhardi (Vomiting of bitter, sour, acidic fluid)",
            "Shirashula (Frontal headache associated with acidity)"
        ],
        pratyatma_lingas=[
            "Hrit-Kantha Daha (Retrosternal and throat pyrosis)",
            "Tikta-Amla Udgara (Acid and bitter regurgitation)",
            "Kukshi Daha with nauseating sour vomiting"
        ],
        beneficial_upashayas=[
            "Sheeta Dugdha (Cold cow milk in small sips)",
            "Tikta Rasa herbs (Shatavari, Patola, Kamadudha, Praval)",
            "Mudga Yusha (Light green gram soup)",
            "Dadima (Sweet pomegranate juice)"
        ],
        aggravating_anupashayas=[
            "Amla Rasa (Vinegar, citrus, sour tamarind, pickles)",
            "Vidahi and deep-fried oily foods",
            "Alcohol or caffeinated beverages",
            "Skipping meals / erratic fasting"
        ],
        samprapti_ghatakas=SampraptiGhatakas(
            primary_dosha="Pitta",
            secondary_doshas=["Kapha"],
            dushya=["Rasa", "Rakta"],
            agni=AgniState.TIKSHNAGNI,
            ama=AmaStatus.SAMA,
            srotas=["Annavaha", "Rasavaha"],
            srotodushti=[SrotodushtiPattern.ATI_PRAVRITTI, SrotodushtiPattern.VIMARGA_GAMANA],
            udbhava_sthana="Amashaya (Stomach)",
            sanchara_sthana="Kostha and Kantha",
            vyakti_sthana="Amashaya, Uras, and Kantha",
            rogamarga=Rogamarga.ABHYANTARA
        ),
        curability=CurabilityPrognosis.SUKHASADHYA
    ),
}


# ==============================================================================
# DIFFERENTIAL DIAGNOSIS RANKING & SIMILARITY ENGINE
# ==============================================================================

def _normalize_string(s: str) -> str:
    """Normalize text string for fuzzy token matching."""
    return s.lower().replace("-", " ").replace("_", " ").strip()


def _calculate_token_overlap(patient_items: List[str], archetype_items: List[str]) -> Tuple[float, List[str]]:
    """
    Computes reciprocal token overlap between patient presentation and archetype features.
    Returns (overlap_ratio, matched_archetype_items).
    """
    if not patient_items or not archetype_items:
        return 0.0, []

    matched = []
    patient_tokens_list = [_normalize_string(item).split() for item in patient_items]

    for arch_item in archetype_items:
        arch_norm = _normalize_string(arch_item)
        for p_tokens in patient_tokens_list:
            # Match if key tokens of patient item appear in archetype description or vice-versa
            token_matches = sum(1 for tok in p_tokens if tok in arch_norm and len(tok) > 2)
            if token_matches >= 1:
                matched.append(arch_item)
                break

    overlap_ratio = min(1.0, len(matched) / max(1, len(archetype_items)))
    return overlap_ratio, matched


def _calculate_pratyatma_linga_matches(patient_roopa: List[str], archetype: DiseaseArchetype) -> List[str]:
    """Identifies hallmark cardinal signs (Pratyatma Linga) present in the patient."""
    matched_lingas = []
    patient_text = " ".join([_normalize_string(r) for r in patient_roopa])

    for linga in archetype.pratyatma_lingas:
        linga_tokens = [tok for tok in _normalize_string(linga).split() if len(tok) > 3]
        matches = sum(1 for tok in linga_tokens if tok in patient_text)
        if matches >= 1:
            matched_lingas.append(linga)

    return matched_lingas


def _evaluate_upashaya_trials(trials: List[Any], archetype: DiseaseArchetype) -> Tuple[float, List[str]]:
    """
    Evaluates patient response to Upashaya/Anupashaya trials against archetype pharmacology.
    """
    if not trials:
        # If no diagnostic trials conducted, return neutral diagnostic baseline
        return 0.50, []

    score_sum = 0.0
    matched_trials = []

    for trial in trials:
        t_desc = _normalize_string(trial.description)
        t_outcome = trial.outcome

        # Check against beneficial upashayas
        matches_beneficial = any(
            any(tok in t_desc for tok in _normalize_string(b).split() if len(tok) > 3)
            for b in archetype.beneficial_upashayas
        )

        # Check against aggravating anupashayas
        matches_aggravating = any(
            any(tok in t_desc for tok in _normalize_string(a).split() if len(tok) > 3)
            for a in archetype.aggravating_anupashayas
        )

        if matches_beneficial and t_outcome == UpashayaOutcome.UPASHAYA_RELIEVED:
            score_sum += 1.0
            matched_trials.append(f"Beneficial trial relief confirmed: {trial.description}")
        elif matches_aggravating and t_outcome == UpashayaOutcome.ANUPASHAYA_AGGRAVATED:
            score_sum += 1.0
            matched_trials.append(f"Expected Anupashaya aggravation confirmed: {trial.description}")
        elif matches_beneficial and t_outcome == UpashayaOutcome.ANUPASHAYA_AGGRAVATED:
            score_sum -= 0.5  # Contradicts expected response
        elif matches_aggravating and t_outcome == UpashayaOutcome.UPASHAYA_RELIEVED:
            score_sum -= 0.5  # Contradicts expected response
        else:
            score_sum += 0.25

    trial_ratio = max(0.0, min(1.0, score_sum / len(trials)))
    return trial_ratio, matched_trials


def _generate_exclusion_rationale(top_code: str, diff_code: str) -> Tuple[List[str], str]:
    """
    Generates classical differential exclusion rationale and discriminating features
    between top candidate and competing differential.
    """
    differentiators = []
    rationale = ""

    pair = {top_code, diff_code}

    if "AMAVATA" in pair and "SANDHIGATA_VATA" in pair:
        differentiators = [
            "Amavata exhibits systemic Ama toxicity, morning Stambha, and migratory scorpion-sting pain (Vrischika Damshavat).",
            "Sandhigata Vata is localized degenerative Vata characterized by crepitus (Vata Purna Driti Sparsha) without fever or systemic Ama."
        ]
        if top_code == "AMAVATA":
            rationale = "Sandhigata Vata excluded as primary diagnosis due to the presence of systemic Ama, inflammatory morning stiffness, and lack of purely localized degenerative crepitus."
        else:
            rationale = "Amavata excluded as primary diagnosis due to the absence of systemic Ama toxicity, absence of morning stiffness, and presence of classic non-inflammatory mechanical crepitation."

    elif "AMAVATA" in pair and "VATARAKTA" in pair:
        differentiators = [
            "Amavata manifests primarily in large/multiple joints with Ama, swelling, and morning stiffness.",
            "Vatarakta originates at the base of the great toe (Padangustha) with profound Rakta/Pitta burning (Daha), erythema (Raga), and nocturnal hyperesthesia."
        ]
        if top_code == "AMAVATA":
            rationale = "Vatarakta relegated due to lack of initial Padangustha presentation, absence of predominant burning agony (Daha), and presence of generalized Ama-Vata morning Stambha."
        else:
            rationale = "Amavata relegated due to the cardinal onset in the big toe with intense erythema, burning pain, and absence of generalized digestive Ama syndrome."

    elif "SANDHIGATA_VATA" in pair and "VATARAKTA" in pair:
        differentiators = [
            "Sandhigata Vata is cold, dry, non-inflammatory degeneration relieved by warm oil massage.",
            "Vatarakta is an acute inflammatory microvascular syndrome with extreme erythema and heat, aggravated by warm oil."
        ]
        rationale = f"{diff_code} excluded based on distinct thermal response and inflammatory markers."

    elif "JWARA_VATAJA" in pair and ("JWARA_PITTAJA" in pair or "JWARA_KAPHAJA" in pair):
        differentiators = [
            "Vataja Jwara presents with erratic temperature spikes (Vishama Vega), body chills, and frequent yawning.",
            "Pittaja Jwara presents with continuous burning heat (Santapa), photophobia, and thirst.",
            "Kaphaja Jwara presents with low-grade fever, severe heaviness (Gaurava), and thick white coated tongue."
        ]
        rationale = f"{diff_code} relegated due to non-concordant thermal pattern and Doshic sign profile."

    else:
        differentiators = [
            f"Primary candidate {top_code} matches pathognomonic cardinal signs more strongly than {diff_code}."
        ]
        rationale = f"{diff_code} exhibits lower overall vector congruence across Nidana Panchaka dimensions."

    return differentiators, rationale


def evaluate_nidana_panchaka(
    input_data: NidanaPanchakaEvaluationInput,
    evaluator_arn: str = "ARN-NCISM-2015-8832",
    hospital_id: str = "hosp-apex-001"
) -> NidanaPanchakaEvaluationOutput:
    """
    Executes algorithmic differential diagnosis matching across all registered classical disease archetypes.
    """
    ranked_candidates: List[DifferentialDiagnosisItem] = []

    # Weights for the 5-fold dimensions:
    # Roopa (0.40), Purvaroopa (0.15), Nidana (0.20), Upashaya (0.15), Samprapti/Doshic (0.10)
    W_ROOPA = 0.40
    W_PURVAROOPA = 0.15
    W_NIDANA = 0.20
    W_UPASHAYA = 0.15
    W_SAMPRAPTI = 0.10

    for code, archetype in DISEASE_ARCHETYPE_REGISTRY.items():
        # 1. Roopa Overlap
        roopa_ratio, matched_roopa = _calculate_token_overlap(input_data.presented_roopa, archetype.roopas)

        # 2. Purvaroopa Overlap
        purva_ratio, matched_purva = _calculate_token_overlap(input_data.presented_purvaroopa, archetype.purvaroopas)

        # 3. Nidana Overlap
        nidana_ratio, matched_nidana = _calculate_token_overlap(input_data.presented_nidana, archetype.nidanas)

        # 4. Upashaya / Anupashaya Trials
        upashaya_ratio, matched_upashaya = _evaluate_upashaya_trials(input_data.upashaya_trials, archetype)

        # 5. Samprapti / Doshic Concordance
        samprapti_ratio = 0.0
        if input_data.observed_doshas:
            dosha_matches = sum(1 for d in input_data.observed_doshas if d.lower() in [x.lower() for x in archetype.doshic_predominance])
            samprapti_ratio = min(1.0, dosha_matches / max(1, len(archetype.doshic_predominance)))
        else:
            samprapti_ratio = 0.5  # Neutral default

        # Pratyatma Linga matches
        pratyatma_matched = _calculate_pratyatma_linga_matches(input_data.presented_roopa, archetype)
        linga_bonus = 15.0 if len(pratyatma_matched) > 0 else 0.0

        # Raw composite match score
        raw_score = 100.0 * (
            W_ROOPA * roopa_ratio +
            W_PURVAROOPA * purva_ratio +
            W_NIDANA * nidana_ratio +
            W_UPASHAYA * upashaya_ratio +
            W_SAMPRAPTI * samprapti_ratio
        ) + linga_bonus

        match_score = round(min(100.0, max(0.0, raw_score)), 2)

        # Confidence computation: scales with match score and Pratyatma Linga verification
        linga_factor = 0.25 if len(pratyatma_matched) > 0 else 0.0
        confidence = round(min(1.0, (match_score / 100.0) * (0.75 + linga_factor)), 3)

        diff_item = DifferentialDiagnosisItem(
            disease_code=archetype.code,
            disease_name=archetype.sanskrit_name + " (" + archetype.english_name + ")",
            match_score=match_score,
            confidence_score=confidence,
            matched_roopa=matched_roopa,
            matched_purvaroopa=matched_purva,
            matched_nidana=matched_nidana,
            matched_upashaya=matched_upashaya,
            pratyatma_linga_matched=pratyatma_matched,
            key_differentiators=[],
            exclusion_rationale=None
        )
        ranked_candidates.append(diff_item)

    # Sort descending by match_score
    ranked_candidates.sort(key=lambda x: x.match_score, reverse=True)

    primary = ranked_candidates[0]
    top_archetype = DISEASE_ARCHETYPE_REGISTRY[primary.disease_code]

    # Generate differential list and exclusion rationales
    differentials: List[DifferentialDiagnosisItem] = []
    for diff in ranked_candidates[1:]:
        if diff.match_score >= 10.0:  # Threshold for clinically relevant differential
            diffs, rationale = _generate_exclusion_rationale(primary.disease_code, diff.disease_code)
            diff.key_differentiators = diffs
            diff.exclusion_rationale = rationale
            differentials.append(diff)

    # Compile clinical recommendations
    recommendations: List[str] = [
        f"Primary diagnostic hypothesis: {primary.disease_name} (Confidence: {primary.confidence_score * 100:.1f}%).",
        f"Targeted Pathogenetic Axis (Samprapti): {top_archetype.samprapti_ghatakas.udbhava_sthana} -> {top_archetype.samprapti_ghatakas.vyakti_sthana} via {top_archetype.samprapti_ghatakas.rogamarga.value} rogamarga.",
        f"Recommended diagnostic Upashaya protocol: Administer {', '.join(top_archetype.beneficial_upashayas[:2])} to confirm symptom remission.",
        f"Strict diagnostic Anupashaya contraindication: Avoid {', '.join(top_archetype.aggravating_anupashayas[:2])} which exacerbate {top_archetype.samprapti_ghatakas.primary_dosha}."
    ]

    now = int(time.time())
    assessment_id = f"np-{uuid.uuid4().hex[:12]}"

    return NidanaPanchakaEvaluationOutput(
        assessment_id=assessment_id,
        patient_id=input_data.patient_id,
        hospital_id=hospital_id,
        evaluator_arn=evaluator_arn,
        primary_diagnosis=primary,
        differential_diagnoses=differentials[:4],  # Top 4 differentials
        samprapti_ghatakas=top_archetype.samprapti_ghatakas,
        pratyatma_linga_matched=primary.pratyatma_linga_matched,
        clinical_recommendations=recommendations,
        timestamp=now
    )


# ==============================================================================
# DATABASE PERSISTENCE & RETRIEVAL FUNCTIONS
# ==============================================================================

def save_nidana_panchaka_assessment(
    conn: sqlite3.Connection,
    assessment: NidanaPanchakaEvaluationOutput,
    raw_input: NidanaPanchakaEvaluationInput
) -> None:
    """Persists a verified Nidana Panchaka evaluation into the SQLite database."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO nidana_panchaka_assessments (
            assessment_id,
            patient_id,
            hospital_id,
            evaluator_arn,
            primary_diagnosis_code,
            primary_diagnosis_name,
            confidence_score,
            match_score,
            presented_roopa_json,
            presented_nidana_json,
            presented_purvaroopa_json,
            upashaya_trials_json,
            differentials_json,
            samprapti_ghatakas_json,
            pratyatma_linga_matched_json,
            clinical_recommendations_json,
            timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            assessment.assessment_id,
            assessment.patient_id,
            assessment.hospital_id,
            assessment.evaluator_arn,
            assessment.primary_diagnosis.disease_code,
            assessment.primary_diagnosis.disease_name,
            assessment.primary_diagnosis.confidence_score,
            assessment.primary_diagnosis.match_score,
            json.dumps(raw_input.presented_roopa),
            json.dumps(raw_input.presented_nidana),
            json.dumps(raw_input.presented_purvaroopa),
            json.dumps([t.model_dump() for t in raw_input.upashaya_trials]),
            json.dumps([d.model_dump() for d in assessment.differential_diagnoses]),
            json.dumps(assessment.samprapti_ghatakas.model_dump()),
            json.dumps(assessment.pratyatma_linga_matched),
            json.dumps(assessment.clinical_recommendations),
            assessment.timestamp
        )
    )


def get_latest_nidana_panchaka_assessment(
    conn: sqlite3.Connection,
    patient_id: str
) -> Optional[Dict[str, Any]]:
    """Retrieves the latest Nidana Panchaka assessment for a patient using deterministic ordering."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM nidana_panchaka_assessments
        WHERE patient_id = ?
        ORDER BY timestamp DESC, rowid DESC
        LIMIT 1;
        """,
        (patient_id,)
    )
    row = cursor.fetchone()
    if not row:
        return None
    return dict(row)


def get_nidana_panchaka_history(
    conn: sqlite3.Connection,
    patient_id: str
) -> List[Dict[str, Any]]:
    """Retrieves chronological trajectory of differential diagnosis assessments."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM nidana_panchaka_assessments
        WHERE patient_id = ?
        ORDER BY timestamp ASC, rowid ASC;
        """,
        (patient_id,)
    )
    return [dict(r) for r in cursor.fetchall()]
