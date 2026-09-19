"""
Prasuti Tantra, Stri Roga & Garbhini Paricharya Engine
======================================================
Implements:
1. Garbha Sambhava Samagri (Ritu, Kshetra, Ambu, Beeja) Preconception Fertility Calculus
2. Month-by-Month Garbhini Paricharya Regimen (1st through 9th Month)
3. Antenatal Consultation with High-Risk Obstetric Triage & Emergency Firewall
4. Classical 20 Yoni Vyapad Gynecological Classification & Therapeutics
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
from models.prasuti_tantra import (
    AntenatalConsultationCreate,
    AntenatalConsultationResponse,
    DoshicClass,
    FertilityReadinessRequest,
    FertilityReadinessResponse,
    GarbhiniMonthRegimen,
    ObstetricTriageLevel,
    YoniVyapadAssessmentCreate,
    YoniVyapadAssessmentResponse,
    YoniVyapadProfile,
)

# ==============================================================================
# 1. GARBHINI MONTH-BY-MONTH REGIMEN CATALOG (MONTHS 1-9)
# ==============================================================================

SEED_GARBHINI_MONTH_REGIMEN: List[GarbhiniMonthRegimen] = [
    GarbhiniMonthRegimen(
        month_number=1,
        sanskrit_name="प्रथम मास (Prathama Masa)",
        dietary_regimen="Frequent intake of cold sweet non-medicated milk (Sheeta Madhura Dugdha) and light liquid food conforming to natural maternal appetite.",
        medicated_milk_or_ghee="Non-medicated cow milk boiled and cooled with sugar candy.",
        therapeutic_procedures="Strict avoidance of heating, heavy, or pungent foods. Bed rest, avoid strenuous exertion and travel.",
        fetal_development_milestone="Garbha Sthapana & Kalala formation (Zygote blastocyst implantation and embryonic disc formation).",
        contraindicated_drugs=["Vamana", "Virechana", "Shirodhara", "Chitrakadi Vati", "Langali", "Hingu", "Kasisadi Bhasma", "Excessive Tikshna/Ushna herbs"]
    ),
    GarbhiniMonthRegimen(
        month_number=2,
        sanskrit_name="द्वितीय मास (Dwitiya Masa)",
        dietary_regimen="Milk medicated with sweet (Madhura-varga) herbs like Shatavari, Yashtimadhu, and Kakoli.",
        medicated_milk_or_ghee="Shatavari Ksheerapaka or Yashtimadhu-siddha Ksheera twice daily.",
        therapeutic_procedures="Gentle unhurried walking, light nourishing diet, prevention of emesis (Chhardi).",
        fetal_development_milestone="Ghana/Pinda/Peshi formation (Embryonic compaction and initial somite condensation).",
        contraindicated_drugs=["Pippali", "Lashuna", "Guggulu", "Virechana", "Deep abdominal massage"]
    ),
    GarbhiniMonthRegimen(
        month_number=3,
        sanskrit_name="तृतीय मास (Tritiya Masa)",
        dietary_regimen="Milk with honey and cow ghee (unequal proportions, ghee predominant) and cooked red Shali rice.",
        medicated_milk_or_ghee="Cow milk with 1 teaspoon cow ghee and half teaspoon honey.",
        therapeutic_procedures="Consistently soothe nausea/emesis with Lajamanda (parched rice water) and pomegranate juice.",
        fetal_development_milestone="Initial organogenesis; limb buds and sensory rudiments begin differentiation.",
        contraindicated_drugs=["Trikatu", "Kshara preparations", "Basti", "Bloodletting / Siravedha"]
    ),
    GarbhiniMonthRegimen(
        month_number=4,
        sanskrit_name="चतुर्थ मास (Chaturtha Masa)",
        dietary_regimen="Freshly churned butter (Navanita) extracted from milk, mixed with sugar candy and cooked rice porridge.",
        medicated_milk_or_ghee="Navanita (unsalted white butter) with milk or Shali rice.",
        therapeutic_procedures="Mandatory Dauhrida (bifocal fetal-maternal desire) recognition and supportive psychological fulfillment.",
        fetal_development_milestone="Anga-Pratyanga Vyakti (limbs and digits distinct); Fetal cardiac activity manifests (Dauhrida phase).",
        contraindicated_drugs=["Suppression of maternal cravings (Dauhridavamana)", "Purgation", "Sudation / Swedana"]
    ),
    GarbhiniMonthRegimen(
        month_number=5,
        sanskrit_name="पञ्चम मास (Panchama Masa)",
        dietary_regimen="Cow ghee medicated with Ksheera or herbs; increased wholesome proteins, milk, and light meat broth (Mamsarasa) if non-vegetarian.",
        medicated_milk_or_ghee="Kalyanaka Ghrita or pure cow ghee with milk.",
        therapeutic_procedures="Support maternal mental tranquility; soothing Vedic recitations and Medhya lifestyle.",
        fetal_development_milestone="Chetana/Manas awakens (Fetal mind and conscious responsiveness awaken; hair, nails, and skin develop).",
        contraindicated_drugs=["Lifting heavy loads", "Sexual intercourse / Vyavaya", "Suppression of natural urges"]
    ),
    GarbhiniMonthRegimen(
        month_number=6,
        sanskrit_name="षष्ठ मास (Shashtha Masa)",
        dietary_regimen="Ghee medicated with Madhura herbs (Gokshura, Shatavari, Vidari) or Yavagu prepared with Gokshura.",
        medicated_milk_or_ghee="Gokshura-siddha Ghrita or Yavagu for diuretic support and preventing pedal edema.",
        therapeutic_procedures="Kikkisa (striae gravidarum and abdominal pruritus) management: application of Chandana-Usheera lepa or Karaveera oil.",
        fetal_development_milestone="Buddhi (Intellectual faculties) develops; hair, muscular tissue, and subcutaneous fat deposition.",
        contraindicated_drugs=["Diuretic abuse", "Fasting", "Excessive salt intake"]
    ),
    GarbhiniMonthRegimen(
        month_number=7,
        sanskrit_name="सप्तम मास (Saptama Masa)",
        dietary_regimen="Ghee medicated with Vidarigandhadi (Prithakparnyadi) group of herbs.",
        medicated_milk_or_ghee="Vidarigandhadi Ghrita to promote optimal fetal somatic growth and intrauterine vitality.",
        therapeutic_procedures="Continue soothing oils for abdominal distension and pruritus; avoid sleeping in supine position.",
        fetal_development_milestone="Sarva-Anga Sampoornata (All vital bodily organs and systems attain functional maturity).",
        contraindicated_drugs=["Sleeping during daytime", "Irregular sleep / Ratrijagarana", "Rough dry food"]
    ),
    GarbhiniMonthRegimen(
        month_number=8,
        sanskrit_name="अष्टम मास (Ashtama Masa)",
        dietary_regimen="Ksheera-Yavagu (milk and rice porridge) mixed with warm cow ghee, Asthapana and Anuvasana Basti.",
        medicated_milk_or_ghee="Anuvasana Basti with Bala Taila / Madhuroushadha-siddha oil; Ksheera-Yavagu with ghee.",
        therapeutic_procedures="Asthapana Basti for regulating Apana Vayu and clearing bowel; close vigil against premature labor.",
        fetal_development_milestone="Ojas instability (Ojas oscillates between maternal circulation and fetus; high vulnerability period).",
        contraindicated_drugs=["Strenuous physical movement", "Travel", "Anxiety", "Heavy indigestible food"]
    ),
    GarbhiniMonthRegimen(
        month_number=9,
        sanskrit_name="नवम मास (Navama Masa)",
        dietary_regimen="Light nourishing rice with meat broth or milk, easily assimilable oily unctuous diet.",
        medicated_milk_or_ghee="Regular Anuvasana Basti with Bala Taila or Sukumara Ghrita.",
        therapeutic_procedures="Daily Yoni Pichu (sterile vaginal tampon saturated with warm Bala Taila or Dhanwantaram Taila) for cervical softening and pelvic compliance.",
        fetal_development_milestone="Full fetal maturity and pelvic engagement; readiness for Sukha Prasava (smooth spontaneous vaginal delivery).",
        contraindicated_drugs=["Excessive sitting or standing", "Mental distress", "Post-maturity neglect"]
    )
]


# ==============================================================================
# 2. CLASSICAL 20 YONI VYAPAD CATALOG
# ==============================================================================

SEED_YONI_VYAPAD_CATALOG: List[YoniVyapadProfile] = [
    # Vataja Yoni Vyapads (5)
    YoniVyapadProfile(
        vyapad_code="YONI-VAT-01",
        sanskrit_name="वातज योनिव्यापत् (Vataja Yoni Vyapad)",
        english_name="Vataja Vaginitis & Pelvic Pain Syndrome",
        doshic_class=DoshicClass.VATAJA,
        icd11_mapping="GA00 (Pelvic pain associated with female genital organs)",
        pathogenesis_summary="Vata aggravation from cold, dry foods and overexertion lodging in reproductive tract causing severe pain and dryness.",
        cardinal_symptoms=["Stabbing vaginal pain (Toda)", "Severe vaginal dryness (Rukshata)", "Frothy discharge with flatus (Phenila Srava)", "Loss of libido"],
        local_therapies=["Yoni Parisheka with Dashamoola Kwatha", "Yoni Pichu with Bala Taila", "Uttarabasti with Phala Ghrita"],
        classical_formulations=["Dashamoolarishta", "Phala Ghrita", "Balarishta", "Chandraprabha Vati"]
    ),
    YoniVyapadProfile(
        vyapad_code="YONI-VAT-02",
        sanskrit_name="उदावर्तिनी योनिव्यापत् (Udavartini Yoni Vyapad)",
        english_name="Spasmodic Primary Dysmenorrhea (Retrograde Apana Vayu)",
        doshic_class=DoshicClass.VATAJA,
        icd11_mapping="GA00.0 (Dysmenorrhea)",
        pathogenesis_summary="Suppression of natural urges forces Apana Vayu to move upward (Udavarta), causing agonizing menstrual cramps relieved upon clot/flow expulsion.",
        cardinal_symptoms=["Excruciating pre-menstrual and menstrual cramps", "Pain instantly relieved once menstrual flow establishes", "Scanty difficult flow"],
        local_therapies=["Yoni Pichu with Dhanwantaram Taila", "Matra Basti with Sahacharadi Taila"],
        classical_formulations=["Rajapravartini Vati", "Sukumarasava", "Dashamoola Kashaya", "Hingwashtaka Churna"]
    ),
    YoniVyapadProfile(
        vyapad_code="YONI-VAT-03",
        sanskrit_name="वन्ध्या योनिव्यापत् (Bandhya Yoni Vyapad)",
        english_name="Anovulatory / Structural Infertility",
        doshic_class=DoshicClass.VATAJA,
        icd11_mapping="GA31 (Female infertility)",
        pathogenesis_summary="Chronic Vata vitiation causing destruction or non-manifestation of healthy ovum (Beejotsarga rodha) and endometrial atrophy.",
        cardinal_symptoms=["Absence of conception despite regular coitus", "Irregular anovulatory cycles", "Emaciation of pelvic tissues"],
        local_therapies=["Uttarabasti with Phala Ghrita on 6th to 8th day of cycle", "Yoni Pichu with Shatavari Ghrita"],
        classical_formulations=["Phala Ghrita", "Shatavari Gulam", "Ashokarishta", "Pushpadhanwa Rasa"]
    ),
    YoniVyapadProfile(
        vyapad_code="YONI-VAT-04",
        sanskrit_name="विप्लुता योनिव्यापत् (Vipluta Yoni Vyapad)",
        english_name="Chronic Intractable Dyspareunia & Pelvic Neuralgia",
        doshic_class=DoshicClass.VATAJA,
        icd11_mapping="GA20 (Dyspareunia)",
        pathogenesis_summary="Persistent Vata vitiation creating perpetual hypersensitivity, tingling, and sharp pain during coitus.",
        cardinal_symptoms=["Continuous pelvic ache", "Intense dyspareunia", "Tingling sensation in perineum"],
        local_therapies=["Yoni Pichu with Yashtimadhu Taila", "Ksheera Seka"],
        classical_formulations=["Saraswatarishta", "Maharasnadi Kashaya", "Ashwagandha Lehyam"]
    ),
    YoniVyapadProfile(
        vyapad_code="YONI-VAT-05",
        sanskrit_name="परिप्लुता योनिव्यापत् (Paripluta Yoni Vyapad)",
        english_name="Acute Pelvic Inflammatory Disease (PID) with Vata-Pitta Dominance",
        doshic_class=DoshicClass.VATAJA,
        icd11_mapping="GA07 (Pelvic inflammatory disease)",
        pathogenesis_summary="Suppression of sneezing/eructation during coitus causing Vata and Pitta to engorge pelvic viscera.",
        cardinal_symptoms=["Severe pelvic tenderness", "Low backache and fever", "Painful coitus with yellowish discharge"],
        local_therapies=["Yoni Prakshalana with Nyagrodhadi Kwatha", "Yoni Pichu with Jatyadi Taila"],
        classical_formulations=["Gokshuradi Guggulu", "Triphala Guggulu", "Chandraprabha Vati", "Lodhrasava"]
    ),

    # Pittaja Yoni Vyapads (5)
    YoniVyapadProfile(
        vyapad_code="YONI-PIT-01",
        sanskrit_name="पित्तज योनिव्यापत् (Pittaja Yoni Vyapad)",
        english_name="Acute Pittaja Vaginitis & Vulvitis",
        doshic_class=DoshicClass.PITTAJA,
        icd11_mapping="GA01 (Vaginitis and vulvovaginitis)",
        pathogenesis_summary="Intake of hot, pungent, sour foods aggravating Pitta and Rakta, resulting in burning and ulceration in genital tract.",
        cardinal_symptoms=["Intense burning sensation (Daha)", "Erythema and swelling (Paka)", "Yellowish malodorous discharge", "Pyrexia"],
        local_therapies=["Yoni Parisheka with cold decoction of Panchavalkala", "Yoni Pichu with Shatadhouta Ghrita"],
        classical_formulations=["Chandanadi Vati", "Sarivadyasava", "Usheerasava", "Praval Pishti"]
    ),
    YoniVyapadProfile(
        vyapad_code="YONI-PIT-02",
        sanskrit_name="असृग्दर / रक्तयोनि (Asrigdara / Raktayoni)",
        english_name="Menorrhagia & Abnormal Uterine Bleeding (AUB)",
        doshic_class=DoshicClass.PITTAJA,
        icd11_mapping="GA15 (Abnormal uterine or vaginal bleeding)",
        pathogenesis_summary="Pitta vitiating Rakta Dhatu causing continuous or excessive non-cyclical heavy uterine hemorrhage.",
        cardinal_symptoms=["Profuse prolonged menstrual flow (Atipravritti)", "Weakness, pallor, and dizziness", "Lower abdominal heaviness"],
        local_therapies=["Yoni Pichu with Lodhra and Priyangu decoction / Nyagrodhadi Ghrita", "Sheeta Avagaha"],
        classical_formulations=["Pushyanuga Churna with Tandulodaka", "Ashokarishta", "Bolabaddha Rasa", "Pradarantaka Lauha"]
    ),
    YoniVyapadProfile(
        vyapad_code="YONI-PIT-03",
        sanskrit_name="अचरणा योनिव्यापत् (Acharana Yoni Vyapad)",
        english_name="Trichomoniasis / Vulval Pruritus with Excessive Libido",
        doshic_class=DoshicClass.PITTAJA,
        icd11_mapping="GA01.0 (Infective vaginitis)",
        pathogenesis_summary="Inadequate local hygiene fostering parasitic microbes (Krimi) causing unceasing itching and erotic agitation.",
        cardinal_symptoms=["Intense unbearable genital itching", "Excessive nymphomania/arousal", "Purulent burning discharge"],
        local_therapies=["Yoni Dhavana with Triphala and Sphatika (Alum) water", "Nimba Taila Yoni Pichu"],
        classical_formulations=["Krimikuthar Rasa", "Gandhaka Rasayana", "Vidangasava", "Kaishore Guggulu"]
    ),
    YoniVyapadProfile(
        vyapad_code="YONI-PIT-04",
        sanskrit_name="अतिचरणा योनिव्यापत् (Aticharana Yoni Vyapad)",
        english_name="Endocervicitis & Traumatic Vulvo-Vaginal Inflammation",
        doshic_class=DoshicClass.PITTAJA,
        icd11_mapping="GA10 (Inflammatory diseases of cervix)",
        pathogenesis_summary="Excessive and forceful sexual indulgence causing mechanical and thermal injury to the vaginal mucosa and cervix.",
        cardinal_symptoms=["Pelvic numbness and aching", "Contact bleeding and cervical redness", "Swelling of introitus"],
        local_therapies=["Yoni Pichu with Jatyadi Taila and Yashtimadhu Ghrita"],
        classical_formulations=["Shatavari Ghrita", "Chandanasava", "Kamadudha Rasa"]
    ),
    YoniVyapadProfile(
        vyapad_code="YONI-PIT-05",
        sanskrit_name="प्राक्चरणा योनिव्यापत् (Prakcharana Yoni Vyapad)",
        english_name="Adolescent Vulvodynia / Premature Coital Trauma",
        doshic_class=DoshicClass.PITTAJA,
        icd11_mapping="GA21 (Vulvodynia)",
        pathogenesis_summary="Coitus prior to menarche or anatomical maturity leading to laceration and Vata-Pitta vitiation.",
        cardinal_symptoms=["Severe backache and groin pain", "Vaginal excoriation", "Urinary burning"],
        local_therapies=["Seka with warm milk and licorice decoction", "Phala Ghrita tampon"],
        classical_formulations=["Chandraprabha Vati", "Ashokarishta", "Drakshasava"]
    ),

    # Kaphaja Yoni Vyapads (5)
    YoniVyapadProfile(
        vyapad_code="YONI-KAP-01",
        sanskrit_name="श्लैष्मिकी / कफज योनिव्यापत् (Shlaishmiki / Kaphaja Yoni Vyapad)",
        english_name="Candidal Vaginitis / Chronic Leukorrhea",
        doshic_class=DoshicClass.KAPHAJA,
        icd11_mapping="GA01.1 (Candidal vulvovaginitis)",
        pathogenesis_summary="Excessive sweet, heavy foods aggravating Kapha, producing copious cold, unctuous, white, sticky discharge.",
        cardinal_symptoms=["Thick white curd-like vaginal discharge (Picchila Pichha)", "Genital pruritus", "Coldness in pelvic region", "Mild dull ache"],
        local_therapies=["Yoni Prakshalana with Triphala-Panchavalkala Kwatha", "Karanja Taila Yoni Pichu", "Yoni Dhoopana with Guggulu & Haridra"],
        classical_formulations=["Pradaranashak Vati", "Triphala Guggulu", "Lodhrasava", "Chandraprabha Vati"]
    ),
    YoniVyapadProfile(
        vyapad_code="YONI-KAP-02",
        sanskrit_name="कर्णिनी योनिव्यापत् (Karnini Yoni Vyapad)",
        english_name="Cervical Erosion / Ectropion with Polypoid Hypertrophy",
        doshic_class=DoshicClass.KAPHAJA,
        icd11_mapping="GA10.0 (Cervical erosion and ectropion)",
        pathogenesis_summary="Straining during anovulatory labor or chronic infection causes Kapha and Rakta to occlude cervix forming polypoid fleshy nodules (Karnika).",
        cardinal_symptoms=["Fleshy polypoid projection at external os", "Muco-purulent intermenstrual spotting", "Sense of foreign body in vagina"],
        local_therapies=["Local Kshara Karma with Apamarga Kshara", "Yoni Pichu with Jatyadi Taila", "Panchavalkala Kwatha Dhavana"],
        classical_formulations=["Kanchanara Guggulu", "Varunadi Kashaya", "Pushyanuga Churna", "Arogyavardhini Vati"]
    ),
    YoniVyapadProfile(
        vyapad_code="YONI-KAP-03",
        sanskrit_name="उपप्लुता योनिव्यापत् (Upapluta Yoni Vyapad)",
        english_name="Gestational Vaginitis / Secondary Leukorrhea of Pregnancy",
        doshic_class=DoshicClass.KAPHAJA,
        icd11_mapping="JA60 (Infections of genital tract in pregnancy)",
        pathogenesis_summary="Vitiated Kapha and Vata lodging in reproductive canal during pregnancy, causing profuse white-yellowish discharge.",
        cardinal_symptoms=["Copious whitish vaginal discharge in pregnancy", "Perineal irritation", "Absence of deep uterine bleeding"],
        local_therapies=["Gentle external wash with Triphala decoction", "Safe herbal douches (avoid high pressure)"],
        classical_formulations=["Garba Raksha Kashaya", "Gokshura Kwatha", "Safe oral Shatavari preparations"]
    ),
    YoniVyapadProfile(
        vyapad_code="YONI-KAP-04",
        sanskrit_name="आनन्दिनी / श्लेष्मला (Anandini / Shleshmala)",
        english_name="Chronic Cervical Hypersecretion / Endocervical Catarrh",
        doshic_class=DoshicClass.KAPHAJA,
        icd11_mapping="GA01 (Vaginal discharge)",
        pathogenesis_summary="Constitutional Kapha excess causing persistent non-purulent slippery mucous secretion without acute pain.",
        cardinal_symptoms=["Continuous clear or milky mucus discharge", "Pelvic heaviness", "Loss of appetite"],
        local_therapies=["Yoni Dhoopana with Nimba and Agaru", "Lodhra churna tampon"],
        classical_formulations=["Khadirarishta", "Punarnavadi Kashaya", "Triphala Churna"]
    ),
    YoniVyapadProfile(
        vyapad_code="YONI-KAP-05",
        sanskrit_name="लोहितक्षरा योनिव्यापत् (Lohitakshara Yoni Vyapad)",
        english_name="Chronic Metrorrhagia with Mucoid Blood Discharge",
        doshic_class=DoshicClass.KAPHAJA,
        icd11_mapping="GA15.1 (Intermenstrual bleeding)",
        pathogenesis_summary="Kapha and Rakta interacting to produce sluggish, pale pink or blood-tinged mucoid continuous discharge with burning.",
        cardinal_symptoms=["Pale pinkish watery continuous discharge", "Mild burning and fatigue", "Anemia"],
        local_therapies=["Yoni Pichu with Nyagrodhadi Kwatha and Lodhra"],
        classical_formulations=["Pushyanuga Churna", "Lohasava", "Bolabaddha Rasa"]
    ),

    # Sannipataja & Structural Yoni Vyapads (5)
    YoniVyapadProfile(
        vyapad_code="YONI-SAN-01",
        sanskrit_name="सन्निपातज योनिव्यापत् (Sannipataja Yoni Vyapad)",
        english_name="Severe Mixed Multi-Microbial Pelvic Infection",
        doshic_class=DoshicClass.SANNIPATAJA,
        icd11_mapping="GA01.Z (Vulvovaginitis, unspecified)",
        pathogenesis_summary="Simultaneous aggravation of Vata, Pitta, and Kapha producing multi-colored, burning, purulent, painful foul discharge.",
        cardinal_symptoms=["Severe burning, stabbing pain, and pruritus combined", "Multi-colored malodorous discharge", "High fever and pelvic toxemia"],
        local_therapies=["Yoni Dhavana with Dashamoola and Triphala", "Yoni Pichu with Mahatiktaka Ghrita"],
        classical_formulations=["Mahatiktaka Ghrita", "Triphala Guggulu", "Amritarishta", "Sudarshana Churna"]
    ),
    YoniVyapadProfile(
        vyapad_code="YONI-SAN-02",
        sanskrit_name="षण्ढयोनिव्यापत् (Shandhayoni Vyapad)",
        english_name="Congenital Uterine / Ovarian Agenesis (Primary Amenorrhea)",
        doshic_class=DoshicClass.SANNIPATAJA,
        icd11_mapping="GA30 (Primary amenorrhea)",
        pathogenesis_summary="Beeja-dosha (congenital chromosomal/developmental defect) leading to absence of breast development and failure of menarche.",
        cardinal_symptoms=["Primary failure of menarche by age 16", "Absence of breast development (Anastani)", "Aversion to coitus"],
        local_therapies=["Counseling and supportive hormone-precursor Rasayanas (incurable / Asadhya for anatomical agenesis)"],
        classical_formulations=["Phala Ghrita", "Shatavari Gulam", "Ashwagandha Lehyam"]
    ),
    YoniVyapadProfile(
        vyapad_code="YONI-SAN-03",
        sanskrit_name="फलिनी / महायोनि (Phalini / Mahayoni)",
        english_name="Pelvic Organ Prolapse / Uterine Descent (Procidentia)",
        doshic_class=DoshicClass.SANNIPATAJA,
        icd11_mapping="GC00 (Female pelvic organ prolapse)",
        pathogenesis_summary="Severe multi-doshic tissue laxity (Mamsa-Meda relaxation) and perineal trauma during labor causing uterine prolapse through introitus.",
        cardinal_symptoms=["Protrusion of fleshy mass from vagina (like fruit / Phala)", "Bearing-down sensation", "Urinary frequency and stress incontinence"],
        local_therapies=["Manual reduction and Yoni Bandhana", "Yoni Pichu saturated with Changeryadi Ghrita or Bala Taila", "Kashaya Parisheka"],
        classical_formulations=["Phala Ghrita", "Chandraprabha Vati", "Lodhrasava", "Kashmiri Kashaya"]
    ),
    YoniVyapadProfile(
        vyapad_code="YONI-SAN-04",
        sanskrit_name="अन्तर्मुखी योनिव्यापत् (Antarmukhi Yoni Vyapad)",
        english_name="Marked Retroversion / Uterine Axis Displacement with Dyspareunia",
        doshic_class=DoshicClass.SANNIPATAJA,
        icd11_mapping="GA23 (Malposition of uterus)",
        pathogenesis_summary="Engorged full bladder or inappropriate coital posture displacing the cervical os backward toward the sacral hollow.",
        cardinal_symptoms=["Severe backache aggravated by coitus", "Severe deep dyspareunia", "Difficulty in conception due to misaligned os"],
        local_therapies=["Pelvic posture alignment (Yoni Namana / Knee-chest position)", "Uttarabasti with medicated ghee"],
        classical_formulations=["Sukumara Ghrita", "Dashamoolarishta", "Phala Ghrita"]
    ),
    YoniVyapadProfile(
        vyapad_code="YONI-SAN-05",
        sanskrit_name="सूचीमुखी योनिव्यापत् (Suchimukhi Yoni Vyapad)",
        english_name="Cervical Os Pin-hole Stenosis / Congenital Narrowing",
        doshic_class=DoshicClass.SANNIPATAJA,
        icd11_mapping="GA12 (Stricture of cervix uteri)",
        pathogenesis_summary="Vitiated Vata and Kapha causing extreme constriction of the cervical canal to the diameter of a needle eye (Suchi).",
        cardinal_symptoms=["Pin-hole cervical external os", "Obstructed painful menstrual dribbling (Cryptomenorrhea / Dysmenorrhea)", "Infertility"],
        local_therapies=["Graduated cervical dilation with medicated probes lubricated with Bala Taila", "Uttarabasti"],
        classical_formulations=["Sahacharadi Kashaya", "Phala Ghrita", "Rajapravartini Vati"]
    )
]


# ==============================================================================
# DATABASE INITIALIZATION & SEEDING ENGINE
# ==============================================================================

def initialize_prasuti_tables(conn: sqlite3.Connection) -> None:
    """Populate garbhini_month_regimen_catalog if unseeded."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM garbhini_month_regimen_catalog;")
    row = cursor.fetchone()
    if row and row["cnt"] == 0:
        now = int(time.time())
        for m in SEED_GARBHINI_MONTH_REGIMEN:
            cursor.execute(
                """
                INSERT INTO garbhini_month_regimen_catalog (
                    month_number, sanskrit_name, dietary_regimen,
                    medicated_milk_or_ghee, therapeutic_procedures,
                    fetal_development_milestone, contraindicated_drugs_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    m.month_number,
                    m.sanskrit_name,
                    m.dietary_regimen,
                    m.medicated_milk_or_ghee,
                    m.therapeutic_procedures,
                    m.fetal_development_milestone,
                    json.dumps(m.contraindicated_drugs),
                    now,
                )
            )
        conn.commit()


def get_garbhini_month_regimen(month: int, conn: sqlite3.Connection) -> GarbhiniMonthRegimen:
    """Retrieve Garbhini month-by-month regimen by month number (1-9)."""
    initialize_prasuti_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM garbhini_month_regimen_catalog WHERE month_number = ?;", (month,))
    row = cursor.fetchone()
    if not row:
        raise RecordNotFoundException("GarbhiniMonthRegimen", str(month))

    return GarbhiniMonthRegimen(
        month_number=row["month_number"],
        sanskrit_name=row["sanskrit_name"],
        dietary_regimen=row["dietary_regimen"],
        medicated_milk_or_ghee=row["medicated_milk_or_ghee"],
        therapeutic_procedures=row["therapeutic_procedures"],
        fetal_development_milestone=row["fetal_development_milestone"],
        contraindicated_drugs=json.loads(row["contraindicated_drugs_json"]),
    )


def list_all_month_regimens(conn: sqlite3.Connection) -> List[GarbhiniMonthRegimen]:
    """List all 9 monthly Garbhini Paricharya regimens."""
    initialize_prasuti_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM garbhini_month_regimen_catalog ORDER BY month_number ASC;")
    rows = cursor.fetchall()
    return [
        GarbhiniMonthRegimen(
            month_number=r["month_number"],
            sanskrit_name=r["sanskrit_name"],
            dietary_regimen=r["dietary_regimen"],
            medicated_milk_or_ghee=r["medicated_milk_or_ghee"],
            therapeutic_procedures=r["therapeutic_procedures"],
            fetal_development_milestone=r["fetal_development_milestone"],
            contraindicated_drugs=json.loads(r["contraindicated_drugs_json"]),
        )
        for r in rows
    ]


# ==============================================================================
# GARBHA SAMBHAVA SAMAGRI (PRECONCEPTION FERTILITY ENGINE)
# ==============================================================================

def evaluate_fertility_readiness(
    req: FertilityReadinessRequest
) -> FertilityReadinessResponse:
    """
    Computes Composite Readiness Score (CRS) based on the 4 canonical pillars:
    Garbha = f(Ritu, Kshetra, Ambu, Beeja) - Sushruta Sharirasthana 2/33.
    """
    crs = (0.25 * req.ritu_score) + (0.25 * req.kshetra_score) + (0.25 * req.ambu_score) + (0.25 * req.beeja_score)

    if crs >= 80.0:
        tier = "EXCELLENT"
    elif crs >= 60.0:
        tier = "ADEQUATE"
    elif crs >= 40.0:
        tier = "COMPROMISED"
    else:
        tier = "POOR"

    def status_label(val: float) -> str:
        if val >= 75.0:
            return "OPTIMAL"
        elif val >= 50.0:
            return "MODERATE"
        else:
            return "DEFICIENT"

    recommendations: List[str] = []
    purifications: List[str] = []

    # Factor-specific clinical intelligence
    if req.beeja_score < 65.0:
        recommendations.append("Indicated Shukra/Artava Rasayana: Phala Ghrita, Shatavari Ksheerapaka, and Ashwagandha Lehyam.")
        purifications.append("Mridu Shodhana (Virechana) followed by Phala Ghrita Uttarabasti.")
    if req.kshetra_score < 65.0:
        recommendations.append("Address reproductive tract and endometrial receptivity via Dashamoola Parisheka and Yoni Pichu.")
        purifications.append("Ksheera Basti and Yoni Prakshalana with Nyagrodhadi Kwatha.")
    if req.ritu_score < 65.0:
        recommendations.append("Circadian and ovulatory synchronization: regularize sleep, Ashokarishta, and ovulation tracking (Days 12-16).")
    if req.ambu_score < 65.0:
        recommendations.append("Enhance maternal metabolic Rasa Dhatu volume with Dadima, Draksha, and optimal electrolyte hydration.")

    if not recommendations:
        recommendations.append("All 4 Garbha Sambhava Samagri factors in optimal equilibrium. Ready for Garbhadhana Samskara.")
        purifications.append("Prophylactic Phala Ghrita administration during Ritumati Kala.")

    return FertilityReadinessResponse(
        patient_id=req.patient_id,
        composite_readiness_score=round(crs, 2),
        readiness_tier=tier,
        ritu_status=status_label(req.ritu_score),
        kshetra_status=status_label(req.kshetra_score),
        ambu_status=status_label(req.ambu_score),
        beeja_status=status_label(req.beeja_score),
        preconception_recommendations=recommendations,
        indicated_shodhana_or_rasayana=purifications,
    )


# ==============================================================================
# ANTENATAL CONSULTATION & HIGH-RISK OBSTETRIC TRIAGE FIREWALL
# ==============================================================================

def record_antenatal_consultation(
    conn: sqlite3.Connection,
    hospital_id: str,
    consult_in: AntenatalConsultationCreate
) -> AntenatalConsultationResponse:
    """
    Log antenatal visit, evaluate gestational month regimen, and trigger
    Obstetric Emergency Triage Firewall on pre-eclampsia, hemorrhage, or fetal distress.
    """
    gest_month = min(9, max(1, int((consult_in.gestational_age_weeks - 1) // 4) + 1))
    high_risk_flags: List[str] = []
    contraindicated_therapies: List[str] = [
        "Vamana", "Virechana", "Shirodhara", "Teekshna Basti", "Udvartana",
        "Uterine stimulants (Guggulu, Langali, Chitrak, Hingu, Kasisadi)"
    ]

    is_emergency = False
    emergency_notes: Optional[str] = None

    # Condition 1: Antepartum Hemorrhage / Threatened Miscarriage (Garbhasrava / Garbhapata)
    if consult_in.vaginal_bleeding_present:
        is_emergency = True
        if consult_in.gestational_age_weeks < 16.0:
            flag = "CRITICAL: Vaginal bleeding in early pregnancy (Threatened Garbhasrava / Miscarriage)"
        else:
            flag = "CRITICAL: Antepartum vaginal hemorrhage (Suspected Placental Abruption / Placenta Previa)"
        high_risk_flags.append(flag)

    # Condition 2: Pre-eclampsia / Eclampsia Crisis (Garbhini Shotha & Raktachapa)
    sys_bp = consult_in.blood_pressure_systolic
    dia_bp = consult_in.blood_pressure_diastolic
    if sys_bp >= 140 or dia_bp >= 90:
        if sys_bp >= 160 or dia_bp >= 110 or consult_in.severe_headache_or_scotoma:
            is_emergency = True
            high_risk_flags.append(
                f"CRITICAL: Severe Pre-eclampsia / Impending Eclampsia (BP {sys_bp}/{dia_bp} mmHg with CNS symptoms)"
            )
        else:
            high_risk_flags.append(
                f"WARNING: Gestational Hypertension (BP {sys_bp}/{dia_bp} mmHg)"
            )

    # Condition 3: Fetal Heart Rate Distress
    fhr = consult_in.fetal_heart_rate_bpm
    if consult_in.gestational_age_weeks >= 20.0 and fhr > 0:
        if fhr < 110 or fhr > 160:
            is_emergency = True
            high_risk_flags.append(
                f"CRITICAL: Fetal Heart Rate Bradycardia/Tachycardia ({fhr} bpm; Normal: 110-160 bpm)"
            )

    # Determine Triage Level
    if is_emergency:
        triage_level = ObstetricTriageLevel.CRITICAL_OBSTETRIC_EMERGENCY
        emergency_notes = (
            "EMERGENCY PROTOCOL ACTIVATED: Immediate maternal-fetal resuscitation required. "
            "Strict bed rest in left lateral position, oxygenation, continuous CTG cardiotocography, "
            "urgent obstetric ultrasonography, and immediate transfer to Tertiary Labor & Delivery ICU."
        )
    elif len(high_risk_flags) > 0 or consult_in.edema_present:
        triage_level = ObstetricTriageLevel.CAUTION
        if consult_in.edema_present and not any("Hypertension" in f for f in high_risk_flags):
            high_risk_flags.append("Pedal edema observed without hypertension (Physiological vs Subclinical Pre-eclampsia)")
    else:
        triage_level = ObstetricTriageLevel.NORMAL

    # Regimen retrieval
    regimen_rec = get_garbhini_month_regimen(gest_month, conn)
    prescribed_text = f"Month {gest_month} ({regimen_rec.sanskrit_name}): {regimen_rec.dietary_regimen} | {regimen_rec.medicated_milk_or_ghee}."

    # Dauhrida recognition
    dauhrida_log = consult_in.dauhrida_desires
    if gest_month in (4, 5) and dauhrida_log:
        prescribed_text += f" | Dauhrida Desires Noted: {', '.join(dauhrida_log)}. Classical guideline: Supportively fulfill maternal cravings to ensure sound cardiac-psychological fetal morphogenesis."

    now = int(time.time())
    consult_id = f"anc-{now}-{uuid.uuid4().hex[:6]}"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO garbhini_antenatal_consultation_logs (
            consultation_id, patient_id, hospital_id, gestational_age_weeks,
            gestational_month, blood_pressure_systolic, blood_pressure_diastolic,
            fundal_height_cm, fetal_heart_rate_bpm, weight_kg, edema_present,
            vaginal_bleeding_present, dauhrida_desires_json, high_risk_flags_json,
            obstetric_triage_level, prescribed_regimen, practitioner_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            consult_id,
            consult_in.patient_id,
            hospital_id,
            consult_in.gestational_age_weeks,
            gest_month,
            consult_in.blood_pressure_systolic,
            consult_in.blood_pressure_diastolic,
            consult_in.fundal_height_cm,
            consult_in.fetal_heart_rate_bpm,
            consult_in.weight_kg,
            1 if consult_in.edema_present else 0,
            1 if consult_in.vaginal_bleeding_present else 0,
            json.dumps(dauhrida_log),
            json.dumps(high_risk_flags),
            triage_level.value,
            prescribed_text,
            consult_in.practitioner_arn,
            now,
        )
    )
    conn.commit()

    return AntenatalConsultationResponse(
        consultation_id=consult_id,
        patient_id=consult_in.patient_id,
        hospital_id=hospital_id,
        gestational_age_weeks=consult_in.gestational_age_weeks,
        gestational_month=gest_month,
        blood_pressure_systolic=consult_in.blood_pressure_systolic,
        blood_pressure_diastolic=consult_in.blood_pressure_diastolic,
        fundal_height_cm=consult_in.fundal_height_cm,
        fetal_heart_rate_bpm=consult_in.fetal_heart_rate_bpm,
        weight_kg=consult_in.weight_kg,
        edema_present=consult_in.edema_present,
        vaginal_bleeding_present=consult_in.vaginal_bleeding_present,
        dauhrida_desires=dauhrida_log,
        high_risk_flags=high_risk_flags,
        obstetric_triage_level=triage_level,
        contraindicated_ayurvedic_therapies=contraindicated_therapies,
        prescribed_regimen=prescribed_text,
        emergency_escalation_notes=emergency_notes,
        practitioner_arn=consult_in.practitioner_arn,
        created_at=now,
    )


def list_antenatal_consultations(
    patient_id: str,
    conn: sqlite3.Connection
) -> List[AntenatalConsultationResponse]:
    """Retrieve historical antenatal consultation records for a pregnant patient."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM garbhini_antenatal_consultation_logs WHERE patient_id = ? ORDER BY created_at DESC;",
        (patient_id,)
    )
    rows = cursor.fetchall()
    return [
        AntenatalConsultationResponse(
            consultation_id=r["consultation_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            gestational_age_weeks=r["gestational_age_weeks"],
            gestational_month=r["gestational_month"],
            blood_pressure_systolic=r["blood_pressure_systolic"],
            blood_pressure_diastolic=r["blood_pressure_diastolic"],
            fundal_height_cm=r["fundal_height_cm"],
            fetal_heart_rate_bpm=r["fetal_heart_rate_bpm"],
            weight_kg=r["weight_kg"],
            edema_present=bool(r["edema_present"]),
            vaginal_bleeding_present=bool(r["vaginal_bleeding_present"]),
            dauhrida_desires=json.loads(r["dauhrida_desires_json"]),
            high_risk_flags=json.loads(r["high_risk_flags_json"]),
            obstetric_triage_level=ObstetricTriageLevel(r["obstetric_triage_level"]),
            contraindicated_ayurvedic_therapies=[
                "Vamana", "Virechana", "Shirodhara", "Teekshna Basti", "Udvartana",
                "Uterine stimulants (Guggulu, Langali, Chitrak, Hingu, Kasisadi)"
            ],
            prescribed_regimen=r["prescribed_regimen"],
            emergency_escalation_notes=None,
            practitioner_arn=r["practitioner_arn"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


# ==============================================================================
# CLASSICAL 20 YONI VYAPAD MANAGEMENT ENGINE
# ==============================================================================

def get_yoni_vyapad_profile(vyapad_code: str) -> YoniVyapadProfile:
    """Retrieve specification of a classical Yoni Vyapad by code."""
    for vyapad in SEED_YONI_VYAPAD_CATALOG:
        if vyapad.vyapad_code == vyapad_code:
            return vyapad
    raise RecordNotFoundException("YoniVyapadProfile", vyapad_code)


def list_all_yoni_vyapads(
    doshic_class: Optional[DoshicClass] = None
) -> List[YoniVyapadProfile]:
    """List all 20 classical Yoni Vyapad conditions with optional Doshic filter."""
    if doshic_class:
        return [v for v in SEED_YONI_VYAPAD_CATALOG if v.doshic_class == doshic_class]
    return SEED_YONI_VYAPAD_CATALOG


def record_yoni_vyapad_assessment(
    conn: sqlite3.Connection,
    hospital_id: str,
    assess_in: YoniVyapadAssessmentCreate
) -> YoniVyapadAssessmentResponse:
    """Record a clinical Yoni Vyapad gynecological diagnosis and prescribe therapy."""
    vyapad = get_yoni_vyapad_profile(assess_in.vyapad_code)

    now = int(time.time())
    assessment_id = f"yoni-{now}-{uuid.uuid4().hex[:6]}"

    treatment_summary = (
        f"Diagnosed {vyapad.sanskrit_name} ({vyapad.english_name}). "
        f"Local Interventions: {', '.join(vyapad.local_therapies)}. "
        f"Oral Therapeutics: {', '.join(vyapad.classical_formulations)}."
    )

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO yoni_vyapad_clinical_assessments (
            assessment_id, patient_id, hospital_id, vyapad_code,
            vyapad_name, doshic_class, icd11_mapping, symptoms_json,
            local_therapies_json, oral_formulations_json, practitioner_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            assessment_id,
            assess_in.patient_id,
            hospital_id,
            vyapad.vyapad_code,
            vyapad.sanskrit_name,
            vyapad.doshic_class.value,
            vyapad.icd11_mapping,
            json.dumps(assess_in.reported_symptoms),
            json.dumps(vyapad.local_therapies),
            json.dumps(vyapad.classical_formulations),
            assess_in.practitioner_arn,
            now,
        )
    )
    conn.commit()

    return YoniVyapadAssessmentResponse(
        assessment_id=assessment_id,
        patient_id=assess_in.patient_id,
        hospital_id=hospital_id,
        vyapad_code=vyapad.vyapad_code,
        vyapad_name=vyapad.sanskrit_name,
        doshic_class=vyapad.doshic_class,
        icd11_mapping=vyapad.icd11_mapping,
        symptoms=assess_in.reported_symptoms,
        local_therapies=vyapad.local_therapies,
        oral_formulations=vyapad.classical_formulations,
        treatment_protocol=treatment_summary,
        practitioner_arn=assess_in.practitioner_arn,
        created_at=now,
    )


def list_yoni_vyapad_assessments(
    patient_id: str,
    conn: sqlite3.Connection
) -> List[YoniVyapadAssessmentResponse]:
    """Retrieve historical Yoni Vyapad assessments for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM yoni_vyapad_clinical_assessments WHERE patient_id = ? ORDER BY created_at DESC;",
        (patient_id,)
    )
    rows = cursor.fetchall()
    return [
        YoniVyapadAssessmentResponse(
            assessment_id=r["assessment_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            vyapad_code=r["vyapad_code"],
            vyapad_name=r["vyapad_name"],
            doshic_class=DoshicClass(r["doshic_class"]),
            icd11_mapping=r["icd11_mapping"],
            symptoms=json.loads(r["symptoms_json"]),
            local_therapies=json.loads(r["local_therapies_json"]),
            oral_formulations=json.loads(r["oral_formulations_json"]),
            treatment_protocol=f"Historical therapy logged for {r['vyapad_name']}.",
            practitioner_arn=r["practitioner_arn"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
