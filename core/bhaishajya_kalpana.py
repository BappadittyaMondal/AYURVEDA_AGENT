"""
Classical Formulation Architecture (Bhaishajya Kalpana) & Polyherbal Synergy Engine
=================================================================================
Implements:
1. Master registry of 15 classical compound formulations across diverse Kalpana forms
2. 8 classical Anupana (carrier vehicle) bio-enhancers
3. Viruddha Ahara safety firewalls (Equal Madhu-Ghrita ratio & heated Honey checks)
4. Polyherbal synergy vector calculus calculating composite Doshic impact
5. SQLite WAL persistence with fast indexed queries
"""

from __future__ import annotations
import json
import time
import sqlite3
from typing import List, Optional, Dict, Any, Tuple

from models.bhaishajya_kalpana import (
    AnupanaProfile,
    ClassicalFormulation,
    FormulationDosageStandard,
    FormulationIngredient,
    IngredientRole,
    KalpanaForm,
    SafetyWarning,
    SafetyWarningLevel,
    SynergyEvaluationRequest,
    SynergyEvaluationResponse,
)
from core.dravyaguna import (
    SEED_HERBAL_REGISTRY,
    calculate_doshic_modulation_vector,
)

# ==============================================================================
# CLASSICAL ANUPANA CARRIER MATRIX (8 VEHICLES)
# ==============================================================================

SEED_ANUPANA_REGISTRY: List[AnupanaProfile] = [
    AnupanaProfile(
        anupana_id="ANUPANA-USHNA-JALA",
        sanskrit_name="उष्ण जल (Ushna Jala)",
        english_name="Boiled Warm Water",
        doshic_affinity="Vata-Kapha Shamana",
        carrier_properties=["Deepana", "Pachana", "Srotoshodhana", "Rapid mucosal absorption"],
        contraindications=["Severe acute internal hemorrhage (Raktapitta)", "Heat stroke / Murcha"]
    ),
    AnupanaProfile(
        anupana_id="ANUPANA-KSHEERA",
        sanskrit_name="गोदुग्ध (Godugdha / Cow Milk)",
        english_name="Warm Cow Milk",
        doshic_affinity="Vata-Pitta Shamana",
        carrier_properties=["Snigdha", "Ojasya", "Jivaniya", "Lipophilic & protein-binding carrier"],
        contraindications=["Acute Ama toxicity", "Severe Mandagni", "Kaphaja bronchial congestion"]
    ),
    AnupanaProfile(
        anupana_id="ANUPANA-GHRITA",
        sanskrit_name="गोघृत (Goghrita / Cow Ghee)",
        english_name="Clarified Cow Butter",
        doshic_affinity="Vata-Pitta Shamana",
        carrier_properties=["Yogavahi", "Lipophilic carrier across blood-brain barrier", "Dhatuposhaka", "Agnivardhana"],
        contraindications=["Severe hypercholesterolemia with arterial plaques", "Acute diarrhea", "Ama conditions"]
    ),
    AnupanaProfile(
        anupana_id="ANUPANA-MADHU",
        sanskrit_name="मधु (Madhu / Raw Honey)",
        english_name="Unprocessed Raw Honey",
        doshic_affinity="Kapha Shamana",
        carrier_properties=["Yogavahi (Amplifies companion herb kinetics)", "Chedana", "Lekhana", "Sandhaniya"],
        contraindications=["STRICTLY PROHIBITED TO HEAT OR CONSUME WITH BOILING HOT SUBSTANCES", "Do not combine with Ghee in equal 1:1 weight"]
    ),
    AnupanaProfile(
        anupana_id="ANUPANA-TAKRA",
        sanskrit_name="तक्र (Takra / Churned Buttermilk)",
        english_name="Medicated Spiced Buttermilk",
        doshic_affinity="Vata-Kapha Shamana, Grahani Hita",
        carrier_properties=["Grahini", "Laghu", "Deepana", "Microbiome restorative"],
        contraindications=["Acute burning hyperacidity (Tikshna Pitta)", "Hot summer seasons with dehydration"]
    ),
    AnupanaProfile(
        anupana_id="ANUPANA-TAILA",
        sanskrit_name="तिल तैल (Tila Taila / Sesame Oil)",
        english_name="Pure Sesame Oil",
        doshic_affinity="Vata Shamana",
        carrier_properties=["Sukshma", "Vyavayi", "Vikasi", "Transdermal and transmucosal penetrator"],
        contraindications=["Pitta and Rakta vitiation", "Obesity with high Kapha"]
    ),
    AnupanaProfile(
        anupana_id="ANUPANA-KANJI",
        sanskrit_name="काञ्जिक (Kanjika)",
        english_name="Fermented Sour Rice Gruel",
        doshic_affinity="Vata Anulomana",
        carrier_properties=["Rochana", "Deepana", "Vata-hara", "Digestive bio-catalyst"],
        contraindications=["Raktapitta", "Severe gastritis", "Ulcerative colitis"]
    ),
    AnupanaProfile(
        anupana_id="ANUPANA-DRAKSHASAVA",
        sanskrit_name="द्राक्षासव (Drakshasava)",
        english_name="Fermented Medicated Raisin Wine",
        doshic_affinity="Vata-Pitta Shamana",
        carrier_properties=["Dhatuposhaka", "Raktavardhaka", "Rapid circulatory distribution via self-generated ethanol"],
        contraindications=["Active liver cirrhosis", "Alcohol dependence", "Severe peptic ulcer"]
    ),
]


# ==============================================================================
# CLASSICAL FORMULATION REGISTRY (15 MASTER COMPOUNDS)
# ==============================================================================

SEED_FORMULATIONS_REGISTRY: List[ClassicalFormulation] = [
    ClassicalFormulation(
        formulation_id="FORM-TRIKATU",
        sanskrit_name="त्रिकटु चूर्ण (Trikatu Churna)",
        kalpana_form=KalpanaForm.CHURNA,
        classical_reference="Sharangadhara Samhita Madhyama Khanda Ch. 6",
        ingredients=[
            FormulationIngredient(herb_id="HERB-SHUNTHI", herb_name="शुण्ठी (Shunthi)", proportion_parts=1.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-MARICHA", herb_name="मरिच (Maricha)", proportion_parts=1.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-PIPPALI", herb_name="पिप्पली (Pippali)", proportion_parts=1.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
        ],
        composite_veerya="USHNA",
        composite_vipaka="KATU",
        doshic_modulation={"vata_delta": -0.60, "pitta_delta": 0.55, "kapha_delta": -0.80},
        cardinal_indications=["Agnimandya (Sluggish metabolism)", "Amadosha", "Shvasa (Dyspnea)", "Kasa (Cough)", "Pinasa (Rhinitis)"],
        standard_anupana="ANUPANA-MADHU",
        dosage_standard=FormulationDosageStandard(min_dose_g=1.0, max_dose_g=3.0, recommended_timing="Pratah & Nishi (Before meals)", instructions="Mix with honey or warm water")
    ),

    ClassicalFormulation(
        formulation_id="FORM-TRIPHALA",
        sanskrit_name="त्रिफला चूर्ण (Triphala Churna)",
        kalpana_form=KalpanaForm.CHURNA,
        classical_reference="Sharangadhara Samhita Madhyama Khanda Ch. 6, Charaka Chikitsa 1",
        ingredients=[
            FormulationIngredient(herb_id="HERB-HARITAKI", herb_name="हरीतकी (Haritaki)", proportion_parts=1.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-BIBHITAKI", herb_name="बिभीतक (Bibhitaki)", proportion_parts=1.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-AMALAKI", herb_name="आमलकी (Amalaki)", proportion_parts=1.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
        ],
        composite_veerya="ANUSHNASHEETA (Balanced)",
        composite_vipaka="MADHURA",
        doshic_modulation={"vata_delta": -0.50, "pitta_delta": -0.50, "kapha_delta": -0.50},
        cardinal_indications=["Vibandha (Constipation)", "Chakshuroga (Eye disorders)", "Prameha (Metabolic disorders)", "Rasayana", "Kushtha"],
        standard_anupana="ANUPANA-USHNA-JALA",
        dosage_standard=FormulationDosageStandard(min_dose_g=3.0, max_dose_g=6.0, recommended_timing="Nishi (At bedtime with warm water)", instructions="Take with warm water or ghee-honey in unequal ratio")
    ),

    ClassicalFormulation(
        formulation_id="FORM-DASHAMULA",
        sanskrit_name="दशमूल क्वाथ (Dashamula Kwatha)",
        kalpana_form=KalpanaForm.KWATHA,
        classical_reference="Charaka Samhita Chikitsasthana Ch. 28, Sharangadhara",
        ingredients=[
            FormulationIngredient(herb_id="HERB-GOKSHURA", herb_name="गोक्षुर (Gokshura)", proportion_parts=1.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-PUNARNAVA", herb_name="पुनर्नवा (Punarnava)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
            FormulationIngredient(herb_id="HERB-ASHWAGANDHA", herb_name="अश्वगन्धा (Ashwagandha)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
        ],
        composite_veerya="USHNA",
        composite_vipaka="KATU",
        doshic_modulation={"vata_delta": -0.85, "pitta_delta": 0.15, "kapha_delta": -0.65},
        cardinal_indications=["Vata Vyadhi", "Shotharoga (Edema)", "Kasa", "Shvasa", "Sutikaroga (Puerperal disorders)"],
        standard_anupana="ANUPANA-USHNA-JALA",
        dosage_standard=FormulationDosageStandard(min_dose_g=30.0, max_dose_g=60.0, recommended_timing="Pratah & Sayam", instructions="Fresh decoction reduced to 1/4th")
    ),

    ClassicalFormulation(
        formulation_id="FORM-CHYAVANAPRASH",
        sanskrit_name="च्यवनप्राश अवलेह (Chyavanaprasha Avaleha)",
        kalpana_form=KalpanaForm.AVALEHA,
        classical_reference="Charaka Samhita Chikitsasthana Ch. 1 (Rasayanadhyaya)",
        ingredients=[
            FormulationIngredient(herb_id="HERB-AMALAKI", herb_name="आमलकी (Amalaki)", proportion_parts=5.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-PIPPALI", herb_name="पिप्पली (Pippali)", proportion_parts=1.0, ingredient_role=IngredientRole.PRAKSHEPA_DRAVYA),
            FormulationIngredient(herb_id="HERB-GUDUCHI", herb_name="गुडूची (Guduchi)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
            FormulationIngredient(herb_id="HERB-ASHWAGANDHA", herb_name="अश्वगन्धा (Ashwagandha)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
        ],
        composite_veerya="ANUSHNASHEETA",
        composite_vipaka="MADHURA",
        doshic_modulation={"vata_delta": -0.65, "pitta_delta": -0.55, "kapha_delta": -0.40},
        cardinal_indications=["Kshaya (Debility)", "Shvasa-Kasa", "Pranavaha Daurbalya", "Vayasthapana (Anti-aging)", "Balya"],
        standard_anupana="ANUPANA-KSHEERA",
        dosage_standard=FormulationDosageStandard(min_dose_g=10.0, max_dose_g=20.0, recommended_timing="Pratah (Empty stomach)", instructions="Follow with warm cow milk")
    ),

    ClassicalFormulation(
        formulation_id="FORM-YOGARAJA-GUGGULU",
        sanskrit_name="योगराज गुग्गुलु (Yogaraja Guggulu)",
        kalpana_form=KalpanaForm.GUGGULU,
        classical_reference="Bhaishajya Ratnavali Amavatarogadhikara",
        ingredients=[
            FormulationIngredient(herb_id="HERB-GUGGULU", herb_name="गुग्गुलु (Shuddha Guggulu)", proportion_parts=4.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-SHUNTHI", herb_name="शुण्ठी (Shunthi)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
            FormulationIngredient(herb_id="HERB-PIPPALI", herb_name="पिप्पली (Pippali)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
            FormulationIngredient(herb_id="HERB-HARITAKI", herb_name="हरीतकी (Haritaki)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
        ],
        composite_veerya="USHNA",
        composite_vipaka="KATU",
        doshic_modulation={"vata_delta": -0.85, "pitta_delta": 0.20, "kapha_delta": -0.75},
        cardinal_indications=["Amavata (Rheumatoid arthritis)", "Sandhigata Vata (Osteoarthritis)", "Kati Shula", "Vata-Raktahara"],
        standard_anupana="ANUPANA-USHNA-JALA",
        dosage_standard=FormulationDosageStandard(min_dose_g=1.0, max_dose_g=2.0, recommended_timing="Post-prandial twice daily", instructions="Take with warm water or Dashamula Kwatha")
    ),

    ClassicalFormulation(
        formulation_id="FORM-MAHARASNADI",
        sanskrit_name="महारास्नादि क्वाथ (Maharasnadi Kwatha)",
        kalpana_form=KalpanaForm.KWATHA,
        classical_reference="Sharangadhara Samhita Madhyama Khanda Ch. 2",
        ingredients=[
            FormulationIngredient(herb_id="HERB-ASHWAGANDHA", herb_name="अश्वगन्धा (Ashwagandha)", proportion_parts=2.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-GUDUCHI", herb_name="गुडूची (Guduchi)", proportion_parts=2.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
            FormulationIngredient(herb_id="HERB-GOKSHURA", herb_name="गोक्षुर (Gokshura)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
            FormulationIngredient(herb_id="HERB-SHUNTHI", herb_name="शुण्ठी (Shunthi)", proportion_parts=1.0, ingredient_role=IngredientRole.PRAKSHEPA_DRAVYA),
        ],
        composite_veerya="USHNA",
        composite_vipaka="MADHURA",
        doshic_modulation={"vata_delta": -0.90, "pitta_delta": -0.10, "kapha_delta": -0.60},
        cardinal_indications=["Sarva Vataroga", "Pakshaghata (Hemiplegia)", "Gridhrasi (Sciatica)", "Sandhigata Vata"],
        standard_anupana="ANUPANA-USHNA-JALA",
        dosage_standard=FormulationDosageStandard(min_dose_g=30.0, max_dose_g=50.0, recommended_timing="Morning and evening before food", instructions="Boil in 16 times water and reduce to 1/4th")
    ),

    ClassicalFormulation(
        formulation_id="FORM-ASHWAGANDHARISHTA",
        sanskrit_name="अश्वगन्धारिष्ट (Ashwagandhadhyarishta)",
        kalpana_form=KalpanaForm.ASAVA_ARISHTA,
        classical_reference="Bhaishajya Ratnavali Murchadhikara",
        ingredients=[
            FormulationIngredient(herb_id="HERB-ASHWAGANDHA", herb_name="अश्वगन्धा (Ashwagandha)", proportion_parts=4.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-HARIDRA", herb_name="हरिद्रा (Haridra)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
            FormulationIngredient(herb_id="HERB-MANJISTHA", herb_name="मञ्जिष्ठा (Manjistha)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
        ],
        composite_veerya="USHNA",
        composite_vipaka="MADHURA",
        doshic_modulation={"vata_delta": -0.80, "pitta_delta": 0.10, "kapha_delta": -0.50},
        cardinal_indications=["Murcha (Fainting/Syncope)", "Apasmara (Epilepsy)", "Karshya (Emaciation)", "Daurbalya"],
        standard_anupana="ANUPANA-USHNA-JALA",
        dosage_standard=FormulationDosageStandard(min_dose_g=15.0, max_dose_g=30.0, recommended_timing="Twice daily after meals", instructions="Mix with equal volume of boiled and cooled water")
    ),

    ClassicalFormulation(
        formulation_id="FORM-KHADIRARISHTA",
        sanskrit_name="खदिरारिष्ट (Khadirarishta)",
        kalpana_form=KalpanaForm.ASAVA_ARISHTA,
        classical_reference="Sharangadhara Samhita Madhyama Khanda Ch. 10",
        ingredients=[
            FormulationIngredient(herb_id="HERB-NIMBA", herb_name="निम्ब (Nimba)", proportion_parts=2.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-HARIDRA", herb_name="हरिद्रा (Haridra)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
            FormulationIngredient(herb_id="HERB-MANJISTHA", herb_name="मञ्जिष्ठा (Manjistha)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
        ],
        composite_veerya="SHEETA",
        composite_vipaka="KATU",
        doshic_modulation={"vata_delta": 0.15, "pitta_delta": -0.80, "kapha_delta": -0.70},
        cardinal_indications=["Kushtha (Chronic dermatoses)", "Mahakushtha", "Krimi (Parasitosis)", "Arbuda", "Raktashodhaka"],
        standard_anupana="ANUPANA-USHNA-JALA",
        dosage_standard=FormulationDosageStandard(min_dose_g=15.0, max_dose_g=30.0, recommended_timing="After meals", instructions="Dilute with equal volume of water")
    ),

    ClassicalFormulation(
        formulation_id="FORM-MAHANARAYANA-TAILA",
        sanskrit_name="महानारायण तैल (Mahanarayana Taila)",
        kalpana_form=KalpanaForm.TAILA,
        classical_reference="Bhaishajya Ratnavali Vatarogadhikara",
        ingredients=[
            FormulationIngredient(herb_id="HERB-ASHWAGANDHA", herb_name="अश्वगन्धा (Ashwagandha)", proportion_parts=2.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-SHATAVARI", herb_name="शतावरी (Shatavari)", proportion_parts=2.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
            FormulationIngredient(herb_id="HERB-GOKSHURA", herb_name="गोक्षुर (Gokshura)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
        ],
        composite_veerya="USHNA",
        composite_vipaka="MADHURA",
        doshic_modulation={"vata_delta": -0.95, "pitta_delta": -0.20, "kapha_delta": -0.30},
        cardinal_indications=["Sarva Vataroga", "Sandhigata Vata", "Gridhrasi", "Manyastambha", "Khanja-Pangu"],
        standard_anupana="ANUPANA-TAILA",
        dosage_standard=FormulationDosageStandard(min_dose_g=10.0, max_dose_g=50.0, recommended_timing="External Abhyanga / Basti", instructions="Warm slightly before application")
    ),

    ClassicalFormulation(
        formulation_id="FORM-KSHEERABALA-TAILA",
        sanskrit_name="क्षीरबला तैल (Ksheerabala Taila)",
        kalpana_form=KalpanaForm.TAILA,
        classical_reference="Ashtanga Hridaya Chikitsasthana Ch. 22",
        ingredients=[
            FormulationIngredient(herb_id="HERB-ASHWAGANDHA", herb_name="अश्वगन्धा (Balya herb)", proportion_parts=2.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-YASHTIMADHU", herb_name="यष्टीमधु (Yashtimadhu)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
        ],
        composite_veerya="SHEETA",
        composite_vipaka="MADHURA",
        doshic_modulation={"vata_delta": -0.80, "pitta_delta": -0.75, "kapha_delta": -0.10},
        cardinal_indications=["Vatarakta", "Jirna Jwara (Chronic fever)", "Svarabheda", "Sukrakshaya", "Shiro-roga"],
        standard_anupana="ANUPANA-KSHEERA",
        dosage_standard=FormulationDosageStandard(min_dose_g=5.0, max_dose_g=15.0, recommended_timing="Internal or Nasya or Abhyanga", instructions="Take internally with warm cow milk")
    ),

    ClassicalFormulation(
        formulation_id="FORM-SHATAVARI-GHRITA",
        sanskrit_name="शतावरी घृत (Shatavari Ghrita)",
        kalpana_form=KalpanaForm.GHRITA,
        classical_reference="Bhaishajya Ratnavali Yonivyapadadhikara",
        ingredients=[
            FormulationIngredient(herb_id="HERB-SHATAVARI", herb_name="शतावरी (Shatavari)", proportion_parts=4.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-YASHTIMADHU", herb_name="यष्टीमधु (Yashtimadhu)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
            FormulationIngredient(herb_id="HERB-GUDUCHI", herb_name="गुडूची (Guduchi)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
        ],
        composite_veerya="SHEETA",
        composite_vipaka="MADHURA",
        doshic_modulation={"vata_delta": -0.70, "pitta_delta": -0.90, "kapha_delta": 0.15},
        cardinal_indications=["Raktapitta", "Vatarakta", "Amlapitta", "Yonivyapad", "Dahashanti"],
        standard_anupana="ANUPANA-KSHEERA",
        dosage_standard=FormulationDosageStandard(min_dose_g=5.0, max_dose_g=10.0, recommended_timing="Early morning before food", instructions="Consume with warm milk or warm water")
    ),

    ClassicalFormulation(
        formulation_id="FORM-CHITRAKADI-VATI",
        sanskrit_name="चित्रकादि वटी (Chitrakadi Vati)",
        kalpana_form=KalpanaForm.VATI,
        classical_reference="Charaka Samhita Chikitsasthana Ch. 15 (Grahani Chikitsa)",
        ingredients=[
            FormulationIngredient(herb_id="HERB-SHUNTHI", herb_name="शुण्ठी (Shunthi)", proportion_parts=1.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-MARICHA", herb_name="मरिच (Maricha)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
            FormulationIngredient(herb_id="HERB-PIPPALI", herb_name="पिप्पली (Pippali)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
        ],
        composite_veerya="USHNA",
        composite_vipaka="KATU",
        doshic_modulation={"vata_delta": -0.75, "pitta_delta": 0.60, "kapha_delta": -0.85},
        cardinal_indications=["Agnimandya", "Grahani Rogadhikara", "Aruchi (Anorexia)", "Ama-Pachana"],
        standard_anupana="ANUPANA-TAKRA",
        dosage_standard=FormulationDosageStandard(min_dose_g=0.5, max_dose_g=1.0, recommended_timing="Immediately before meals", instructions="Chew or swallow with spiced Takra")
    ),

    ClassicalFormulation(
        formulation_id="FORM-SUDARSHANA-CHURNA",
        sanskrit_name="सुदर्शन चूर्ण (Sudarshana Churna)",
        kalpana_form=KalpanaForm.CHURNA,
        classical_reference="Bhaishajya Ratnavali Jwaradhikara",
        ingredients=[
            FormulationIngredient(herb_id="HERB-KATUKI", herb_name="कटुकी (Katuki / Bitter core)", proportion_parts=2.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-GUDUCHI", herb_name="गुडूची (Guduchi)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
            FormulationIngredient(herb_id="HERB-HARIDRA", herb_name="हरिद्रा (Haridra)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
            FormulationIngredient(herb_id="HERB-NIMBA", herb_name="निम्ब (Nimba)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
        ],
        composite_veerya="SHEETA",
        composite_vipaka="KATU",
        doshic_modulation={"vata_delta": 0.05, "pitta_delta": -0.85, "kapha_delta": -0.75},
        cardinal_indications=["Sarva Jwara (All acute & chronic fevers)", "Vishama Jwara", "Yakrit-Pleehodara", "Aruchi"],
        standard_anupana="ANUPANA-USHNA-JALA",
        dosage_standard=FormulationDosageStandard(min_dose_g=2.0, max_dose_g=4.0, recommended_timing="Twice daily after meals", instructions="Take with warm water")
    ),

    ClassicalFormulation(
        formulation_id="FORM-AVIPATTIKARA-CHURNA",
        sanskrit_name="अविपत्तिकर चूर्ण (Avipattikara Churna)",
        kalpana_form=KalpanaForm.CHURNA,
        classical_reference="Bhaishajya Ratnavali Amlapittadhikara",
        ingredients=[
            FormulationIngredient(herb_id="HERB-AMALAKI", herb_name="आमलकी (Amalaki)", proportion_parts=2.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-SHUNTHI", herb_name="शुण्ठी (Shunthi)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
            FormulationIngredient(herb_id="HERB-VIDANGA", herb_name="विडङ्ग (Vidanga)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
            FormulationIngredient(herb_id="HERB-YASHTIMADHU", herb_name="यष्टीमधु (Yashtimadhu)", proportion_parts=1.0, ingredient_role=IngredientRole.SAHAKARI_DRAVYA),
        ],
        composite_veerya="SHEETA",
        composite_vipaka="MADHURA",
        doshic_modulation={"vata_delta": -0.45, "pitta_delta": -0.85, "kapha_delta": -0.35},
        cardinal_indications=["Amlapitta (Hyperacidity)", "Hrit-Kantha Daha", "Vibandha (Constipation)", "Chhardi", "Agnimandya"],
        standard_anupana="ANUPANA-USHNA-JALA",
        dosage_standard=FormulationDosageStandard(min_dose_g=3.0, max_dose_g=6.0, recommended_timing="Before meals or at bedtime", instructions="Take with cool or lukewarm water or honey")
    ),

    ClassicalFormulation(
        formulation_id="FORM-HINGWASHTAKA-CHURNA",
        sanskrit_name="हिङ्ग्वाष्टक चूर्ण (Hingwashtaka Churna)",
        kalpana_form=KalpanaForm.CHURNA,
        classical_reference="Bhaishajya Ratnavali Agnimandyadhikara",
        ingredients=[
            FormulationIngredient(herb_id="HERB-SHUNTHI", herb_name="शुण्ठी (Shunthi)", proportion_parts=1.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-MARICHA", herb_name="मरिच (Maricha)", proportion_parts=1.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
            FormulationIngredient(herb_id="HERB-PIPPALI", herb_name="पिप्पली (Pippali)", proportion_parts=1.0, ingredient_role=IngredientRole.MUKHYA_DRAVYA),
        ],
        composite_veerya="USHNA",
        composite_vipaka="KATU",
        doshic_modulation={"vata_delta": -0.85, "pitta_delta": 0.45, "kapha_delta": -0.70},
        cardinal_indications=["Adhmana (Flatulence / tympanites)", "Anaha", "Udarashula (Colic)", "Agnimandya"],
        standard_anupana="ANUPANA-GHRITA",
        dosage_standard=FormulationDosageStandard(min_dose_g=1.0, max_dose_g=3.0, recommended_timing="Prathama Kavala (With the very first bite of food)", instructions="Mix with warm cow ghee and warm rice")
    ),
]


# ==============================================================================
# SEEDING, SEARCH & SYNERGY CALCULATOR
# ==============================================================================

def seed_formulations_and_anupana(conn: sqlite3.Connection) -> None:
    """Seeds classical formulations and Anupana carrier profiles into SQLite."""
    cursor = conn.cursor()
    now = int(time.time())

    # 1. Seed Anupana registry
    for anupana in SEED_ANUPANA_REGISTRY:
        cursor.execute(
            """
            INSERT OR IGNORE INTO anupana_registry (
                anupana_id, sanskrit_name, english_name, doshic_affinity,
                carrier_properties_json, contraindications_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                anupana.anupana_id,
                anupana.sanskrit_name,
                anupana.english_name,
                anupana.doshic_affinity,
                json.dumps(anupana.carrier_properties),
                json.dumps(anupana.contraindications),
                now,
            )
        )

    # 2. Seed Formulations registry
    for form in SEED_FORMULATIONS_REGISTRY:
        cursor.execute(
            """
            INSERT OR IGNORE INTO formulations_registry (
                formulation_id, sanskrit_name, kalpana_form, classical_reference,
                ingredients_json, composite_veerya, composite_vipaka,
                doshic_modulation_json, cardinal_indications_json,
                standard_anupana, dosage_standard_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                form.formulation_id,
                form.sanskrit_name,
                form.kalpana_form.value,
                form.classical_reference,
                json.dumps([i.model_dump() for i in form.ingredients]),
                form.composite_veerya,
                form.composite_vipaka,
                json.dumps(form.doshic_modulation),
                json.dumps(form.cardinal_indications),
                form.standard_anupana,
                json.dumps(form.dosage_standard.model_dump()),
                now,
            )
        )


def _row_to_formulation(r: sqlite3.Row) -> ClassicalFormulation:
    """Deserializes SQLite row to ClassicalFormulation."""
    return ClassicalFormulation(
        formulation_id=r["formulation_id"],
        sanskrit_name=r["sanskrit_name"],
        kalpana_form=KalpanaForm(r["kalpana_form"]),
        classical_reference=r["classical_reference"],
        ingredients=[FormulationIngredient(**i) for i in json.loads(r["ingredients_json"])],
        composite_veerya=r["composite_veerya"],
        composite_vipaka=r["composite_vipaka"],
        doshic_modulation=json.loads(r["doshic_modulation_json"]),
        cardinal_indications=json.loads(r["cardinal_indications_json"]),
        standard_anupana=r["standard_anupana"],
        dosage_standard=FormulationDosageStandard(**json.loads(r["dosage_standard_json"])),
    )


def search_formulations(
    conn: sqlite3.Connection,
    query: Optional[str] = None,
    kalpana: Optional[KalpanaForm] = None,
    indication: Optional[str] = None,
) -> List[ClassicalFormulation]:
    """Searches formulations by text query, Kalpana form, or clinical indication."""
    seed_formulations_and_anupana(conn)
    cursor = conn.cursor()

    sql = "SELECT * FROM formulations_registry WHERE 1=1"
    params: List[Any] = []

    if kalpana:
        sql += " AND kalpana_form = ?"
        params.append(kalpana.value)

    if query:
        q_norm = f"%{query.strip()}%"
        sql += """ AND (
            formulation_id LIKE ? OR
            sanskrit_name LIKE ? OR
            classical_reference LIKE ? OR
            cardinal_indications_json LIKE ?
        )"""
        params.extend([q_norm] * 4)

    sql += " ORDER BY sanskrit_name ASC;"
    cursor.execute(sql, params)
    rows = cursor.fetchall()

    formulations = [_row_to_formulation(r) for r in rows]

    if indication:
        ind_norm = indication.lower()
        formulations = [
            f for f in formulations
            if any(ind_norm in ind.lower() for ind in f.cardinal_indications)
        ]

    return formulations


def get_formulation_by_id(conn: sqlite3.Connection, formulation_id: str) -> Optional[ClassicalFormulation]:
    """Retrieves specific formulation by ID."""
    seed_formulations_and_anupana(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM formulations_registry WHERE formulation_id = ? LIMIT 1;", (formulation_id,))
    r = cursor.fetchone()
    if not r:
        return None
    return _row_to_formulation(r)


def get_all_anupana(conn: sqlite3.Connection) -> List[AnupanaProfile]:
    """Retrieves all registered classical Anupana vehicles."""
    seed_formulations_and_anupana(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM anupana_registry ORDER BY anupana_id ASC;")
    rows = cursor.fetchall()
    return [
        AnupanaProfile(
            anupana_id=r["anupana_id"],
            sanskrit_name=r["sanskrit_name"],
            english_name=r["english_name"],
            doshic_affinity=r["doshic_affinity"],
            carrier_properties=json.loads(r["carrier_properties_json"]),
            contraindications=json.loads(r["contraindications_json"]),
        )
        for r in rows
    ]


def evaluate_polyherbal_synergy(
    request: SynergyEvaluationRequest
) -> SynergyEvaluationResponse:
    """
    Computes aggregate polyherbal Doshic vector, composite pharmacodynamics,
    and enforces classical Viruddha Ahara safety firewalls.
    """
    herb_dict = {h.herb_id: h for h in SEED_HERBAL_REGISTRY}

    warnings: List[SafetyWarning] = []

    # 1. Viruddha Ahara Check: Equal proportions of Honey and Ghee
    honey_p = request.honey_ratio_parts or 0.0
    ghee_p = request.ghee_ratio_parts or 0.0

    if honey_p > 0 and ghee_p > 0:
        max_p = max(honey_p, ghee_p)
        min_p = min(honey_p, ghee_p)
        # If within 10% of each other (essentially equal ratio)
        if (max_p - min_p) / max_p <= 0.15:
            warnings.append(
                SafetyWarning(
                    code="VIRUDDHA_SAMYOGA_MADHU_GHRITA",
                    level=SafetyWarningLevel.CRITICAL_CONTRAINDICATION,
                    message="SAMYOGA VIRUDDHA: Honey (Madhu) and Ghee (Ghrita) combined in equal or near-equal proportions form toxic endogenous metabolites (Ama-Visha). Ratios must be strictly unequal (e.g. 2:1 or 1:3)."
                )
            )

    # 2. Viruddha Ahara Check: Heated Honey
    if request.is_heated_anupana and (honey_p > 0 or request.proposed_anupana_id == "ANUPANA-MADHU"):
        warnings.append(
            SafetyWarning(
                code="VIRUDDHA_USHNA_MADHU",
                level=SafetyWarningLevel.CRITICAL_CONTRAINDICATION,
                message="USHNA MADHU VIRUDDHA: Heating honey or mixing honey with boiling liquids is strictly contraindicated in classical toxicology as heat denatures enzymes into toxic HMF and causes acute Ama."
            )
        )

    # 3. Polyherbal Doshic Vector Synthesis
    total_parts = sum(i.proportion_parts for i in request.ingredients)
    if total_parts <= 0:
        total_parts = 1.0

    sum_v = 0.0
    sum_p = 0.0
    sum_k = 0.0
    ushna_count = 0
    sheeta_count = 0
    karma_set = set()

    for ing in request.ingredients:
        weight = ing.proportion_parts / total_parts
        if ing.herb_id in herb_dict:
            h = herb_dict[ing.herb_id]
            mod = calculate_doshic_modulation_vector(h)
            sum_v += weight * mod.vata_delta
            sum_p += weight * mod.pitta_delta
            sum_k += weight * mod.kapha_delta

            if h.veerya.value == "USHNA":
                ushna_count += ing.proportion_parts
            else:
                sheeta_count += ing.proportion_parts

            for k in h.therapeutics_karma:
                karma_set.add(k)
        else:
            # Fallback neutral score if unknown herb
            pass

    comp_veerya = "USHNA" if ushna_count >= sheeta_count else "SHEETA"
    comp_vipaka = "KATU" if comp_veerya == "USHNA" else "MADHURA"

    agg_vector = {
        "vata_delta": round(max(-1.0, min(1.0, sum_v)), 2),
        "pitta_delta": round(max(-1.0, min(1.0, sum_p)), 2),
        "kapha_delta": round(max(-1.0, min(1.0, sum_k)), 2)
    }

    rationale = (
        f"Compound recipe of {len(request.ingredients)} ingredients yields composite {comp_veerya} potency "
        f"with net Doshic vector: Vata ({agg_vector['vata_delta']:+.2f}), "
        f"Pitta ({agg_vector['pitta_delta']:+.2f}), Kapha ({agg_vector['kapha_delta']:+.2f})."
    )

    return SynergyEvaluationResponse(
        aggregate_doshic_vector=agg_vector,
        composite_veerya=comp_veerya,
        composite_vipaka=comp_vipaka,
        synergistic_karma=sorted(list(karma_set)),
        safety_warnings=warnings,
        rationale=rationale
    )
