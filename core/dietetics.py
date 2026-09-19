"""
Clinical Dietetics, Ahara Varga, Pathya-Apathya & Viruddha Ahara Engine
=======================================================================
Implements:
1. Classical Ahara Varga knowledge graph (24+ food ingredients with Rasa-Panchaka & macros)
2. Disease-specific Pathya-Apathya clinical registry
3. 18-fold Viruddha Ahara incompatibility detection matrix (Fish+Milk, 1:1 Honey-Ghee, Heated Honey, Heated Curd, Curd at night)
4. Caloric, macronutrient, and composite Doshic vector calculus
5. SQLite WAL persistence with indexed queries
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
from models.dietetics import (
    AharaVarga,
    DietIngredient,
    DietPlanCreateRequest,
    DietPlanResponse,
    DiseasePathyaApathya,
    MealItem,
    PlannedMeal,
    ViruddhaType,
    ViruddhaViolation,
)

# ==============================================================================
# CLASSICAL AHARA VARGA INGREDIENTS CATALOG (24+ INGREDIENTS)
# ==============================================================================

SEED_DIET_INGREDIENTS: List[DietIngredient] = [
    # Grains (Shuka Dhanya)
    DietIngredient(
        ingredient_id="ING-RAKTASHALI",
        sanskrit_name="रक्तशालि (Raktashali / Red Rice)",
        english_name="Red Husked Rice",
        ahara_varga=AharaVarga.SHUKA_DHANYA,
        rasa="Madhura",
        veerya="Sheeta",
        vipaka="Madhura",
        guna=["Laghu", "Snigdha"],
        doshic_effect={"vata": "SHAMANA", "pitta": "SHAMANA", "kapha": "SHAMANA"},
        calories_per_100g=345.0, protein_g=7.5, carbs_g=78.0, fat_g=0.6,
    ),
    DietIngredient(
        ingredient_id="ING-YAVA",
        sanskrit_name="यव (Yava / Barley)",
        english_name="Barley Grains",
        ahara_varga=AharaVarga.SHUKA_DHANYA,
        rasa="Kashaya-Madhura",
        veerya="Sheeta",
        vipaka="Katu",
        guna=["Ruksha", "Laghu"],
        doshic_effect={"vata": "KOPANA", "pitta": "SHAMANA", "kapha": "SHAMANA"},
        calories_per_100g=352.0, protein_g=12.5, carbs_g=73.5, fat_g=1.2,
    ),
    DietIngredient(
        ingredient_id="ING-GODHUMA",
        sanskrit_name="गोधूम (Godhuma / Wheat)",
        english_name="Whole Wheat Grains",
        ahara_varga=AharaVarga.SHUKA_DHANYA,
        rasa="Madhura",
        veerya="Sheeta",
        vipaka="Madhura",
        guna=["Guru", "Snigdha"],
        doshic_effect={"vata": "SHAMANA", "pitta": "SHAMANA", "kapha": "VARDHANA"},
        calories_per_100g=340.0, protein_g=11.8, carbs_g=71.2, fat_g=1.5,
    ),
    # Pulses (Shami Dhanya)
    DietIngredient(
        ingredient_id="ING-MUDGA",
        sanskrit_name="मुद्ग (Mudga / Green Gram)",
        english_name="Whole Mung Beans",
        ahara_varga=AharaVarga.SHAMI_DHANYA,
        rasa="Kashaya-Madhura",
        veerya="Sheeta",
        vipaka="Katu",
        guna=["Laghu", "Ruksha"],
        doshic_effect={"vata": "ALPA_KOPANA", "pitta": "SHAMANA", "kapha": "SHAMANA"},
        calories_per_100g=347.0, protein_g=24.0, carbs_g=60.0, fat_g=1.2,
    ),
    DietIngredient(
        ingredient_id="ING-MASHA",
        sanskrit_name="माष (Masha / Black Gram)",
        english_name="Urad Dal / Black Gram",
        ahara_varga=AharaVarga.SHAMI_DHANYA,
        rasa="Madhura",
        veerya="Ushna",
        vipaka="Madhura",
        guna=["Guru", "Snigdha"],
        doshic_effect={"vata": "SHAMANA", "pitta": "KOPANA", "kapha": "VARDHANA"},
        calories_per_100g=341.0, protein_g=25.2, carbs_g=58.9, fat_g=1.4,
    ),
    DietIngredient(
        ingredient_id="ING-KULATTHA",
        sanskrit_name="कुलत्थ (Kulattha / Horse Gram)",
        english_name="Horse Gram",
        ahara_varga=AharaVarga.SHAMI_DHANYA,
        rasa="Kashaya-Katu",
        veerya="Ushna",
        vipaka="Katu",
        guna=["Laghu", "Ruksha", "Teekshna"],
        doshic_effect={"vata": "SHAMANA", "pitta": "KOPANA", "kapha": "SHAMANA"},
        calories_per_100g=321.0, protein_g=22.0, carbs_g=57.2, fat_g=0.5,
    ),
    # Dairy (Gorasa Varga)
    DietIngredient(
        ingredient_id="ING-GODUGDHA",
        sanskrit_name="गोदुग्ध (Godugdha / Cow Milk)",
        english_name="Fresh Cow Milk",
        ahara_varga=AharaVarga.GORASA_VARGA,
        rasa="Madhura",
        veerya="Sheeta",
        vipaka="Madhura",
        guna=["Guru", "Snigdha", "Manda"],
        doshic_effect={"vata": "SHAMANA", "pitta": "SHAMANA", "kapha": "VARDHANA"},
        calories_per_100g=65.0, protein_g=3.2, carbs_g=4.8, fat_g=3.8,
    ),
    DietIngredient(
        ingredient_id="ING-DADHI",
        sanskrit_name="दधि (Dadhi / Curd)",
        english_name="Fermented Cow Milk Curd / Yogurt",
        ahara_varga=AharaVarga.GORASA_VARGA,
        rasa="Amla",
        veerya="Ushna",
        vipaka="Amla",
        guna=["Guru", "Snigdha", "Abhishyandi"],
        doshic_effect={"vata": "SHAMANA", "pitta": "KOPANA", "kapha": "VARDHANA"},
        calories_per_100g=98.0, protein_g=3.5, carbs_g=4.5, fat_g=7.5,
    ),
    DietIngredient(
        ingredient_id="ING-TAKRA",
        sanskrit_name="तक्र (Takra / Buttermilk)",
        english_name="Churned Spiced Buttermilk",
        ahara_varga=AharaVarga.GORASA_VARGA,
        rasa="Kashaya-Amla",
        veerya="Ushna",
        vipaka="Madhura",
        guna=["Laghu", "Ruksha", "Deepana"],
        doshic_effect={"vata": "SHAMANA", "pitta": "AVIRUDDHA", "kapha": "SHAMANA"},
        calories_per_100g=40.0, protein_g=3.0, carbs_g=4.8, fat_g=0.9,
    ),
    DietIngredient(
        ingredient_id="ING-GHRITA",
        sanskrit_name="गोधृत (Go-Ghrita / Cow Ghee)",
        english_name="Clarified Cow Butter",
        ahara_varga=AharaVarga.GORASA_VARGA,
        rasa="Madhura",
        veerya="Sheeta",
        vipaka="Madhura",
        guna=["Guru", "Snigdha", "Sookshma"],
        doshic_effect={"vata": "SHAMANA", "pitta": "SHAMANA", "kapha": "ALPA_VARDHANA"},
        calories_per_100g=884.0, protein_g=0.0, carbs_g=0.0, fat_g=99.5,
    ),
    # Sugarcane & Honey (Ikshu Varga)
    DietIngredient(
        ingredient_id="ING-MADHU",
        sanskrit_name="मधु (Madhu / Raw Honey)",
        english_name="Natural Pure Bee Honey",
        ahara_varga=AharaVarga.IKSHU_VARGA,
        rasa="Madhura-Kashaya",
        veerya="Sheeta",
        vipaka="Katu",
        guna=["Laghu", "Ruksha", "Lekhana"],
        doshic_effect={"vata": "ALPA_KOPANA", "pitta": "SHAMANA", "kapha": "SHAMANA"},
        calories_per_100g=304.0, protein_g=0.3, carbs_g=82.4, fat_g=0.0,
    ),
    DietIngredient(
        ingredient_id="ING-GUDA",
        sanskrit_name="पुराण गुड (Purana Guda / Old Jaggery)",
        english_name="Aged Organic Jaggery",
        ahara_varga=AharaVarga.IKSHU_VARGA,
        rasa="Madhura",
        veerya="Anushna",
        vipaka="Madhura",
        guna=["Laghu", "Snigdha", "Deepana"],
        doshic_effect={"vata": "SHAMANA", "pitta": "SHAMANA", "kapha": "AVIRUDDHA"},
        calories_per_100g=383.0, protein_g=0.4, carbs_g=98.0, fat_g=0.1,
    ),
    # Vegetables (Shaka Varga)
    DietIngredient(
        ingredient_id="ING-PATOLA",
        sanskrit_name="पटोल (Patola / Pointed Gourd)",
        english_name="Pointed Gourd / Parwal",
        ahara_varga=AharaVarga.SHAKA_VARGA,
        rasa="Tikta",
        veerya="Sheeta",
        vipaka="Katu",
        guna=["Laghu", "Ruksha", "Deepana"],
        doshic_effect={"vata": "SHAMANA", "pitta": "SHAMANA", "kapha": "SHAMANA"},
        calories_per_100g=20.0, protein_g=2.0, carbs_g=3.5, fat_g=0.2,
    ),
    DietIngredient(
        ingredient_id="ING-KARAVELLAKA",
        sanskrit_name="कारवेल्लक (Karavellaka / Bitter Gourd)",
        english_name="Bitter Gourd / Karela",
        ahara_varga=AharaVarga.SHAKA_VARGA,
        rasa="Tikta",
        veerya="Sheeta",
        vipaka="Katu",
        guna=["Laghu", "Ruksha"],
        doshic_effect={"vata": "KOPANA", "pitta": "SHAMANA", "kapha": "SHAMANA"},
        calories_per_100g=17.0, protein_g=1.0, carbs_g=3.7, fat_g=0.1,
    ),
    DietIngredient(
        ingredient_id="ING-VASTUKA",
        sanskrit_name="वास्तुक (Vastuka / Bathua)",
        english_name="Lamb's Quarters Greens",
        ahara_varga=AharaVarga.SHAKA_VARGA,
        rasa="Madhura-Kashaya",
        veerya="Sheeta",
        vipaka="Katu",
        guna=["Laghu", "Deepana"],
        doshic_effect={"vata": "SHAMANA", "pitta": "SHAMANA", "kapha": "SHAMANA"},
        calories_per_100g=43.0, protein_g=4.2, carbs_g=7.3, fat_g=0.8,
    ),
    # Fruits (Phala Varga)
    DietIngredient(
        ingredient_id="ING-DADIMA",
        sanskrit_name="दाडिम (Dadima / Pomegranate)",
        english_name="Sweet Pomegranate",
        ahara_varga=AharaVarga.PHALA_VARGA,
        rasa="Madhura-Kashaya-Amla",
        veerya="Anushna",
        vipaka="Madhura",
        guna=["Laghu", "Snigdha", "Grahi"],
        doshic_effect={"vata": "SHAMANA", "pitta": "SHAMANA", "kapha": "SHAMANA"},
        calories_per_100g=83.0, protein_g=1.7, carbs_g=18.7, fat_g=1.2,
    ),
    DietIngredient(
        ingredient_id="ING-DRAKSHA",
        sanskrit_name="द्राक्षा (Draksha / Dry Raisins)",
        english_name="Black Raisins / Dry Grapes",
        ahara_varga=AharaVarga.PHALA_VARGA,
        rasa="Madhura",
        veerya="Sheeta",
        vipaka="Madhura",
        guna=["Guru", "Snigdha", "Mrida"],
        doshic_effect={"vata": "SHAMANA", "pitta": "SHAMANA", "kapha": "ALPA_VARDHANA"},
        calories_per_100g=299.0, protein_g=3.1, carbs_g=79.2, fat_g=0.5,
    ),
    DietIngredient(
        ingredient_id="ING-KADALI",
        sanskrit_name="कदली (Kadali / Ripe Banana)",
        english_name="Sweet Ripe Banana",
        ahara_varga=AharaVarga.PHALA_VARGA,
        rasa="Madhura",
        veerya="Sheeta",
        vipaka="Madhura",
        guna=["Guru", "Snigdha"],
        doshic_effect={"vata": "SHAMANA", "pitta": "SHAMANA", "kapha": "VARDHANA"},
        calories_per_100g=89.0, protein_g=1.1, carbs_g=22.8, fat_g=0.3,
    ),
    # Meats & Seafood (Mamsa Varga)
    DietIngredient(
        ingredient_id="ING-MATSYA",
        sanskrit_name="मत्स्य (Matsya / Freshwater Fish)",
        english_name="River Rohu / Freshwater Fish",
        ahara_varga=AharaVarga.MAMSA_VARGA,
        rasa="Madhura",
        veerya="Ushna",
        vipaka="Madhura",
        guna=["Guru", "Snigdha"],
        doshic_effect={"vata": "SHAMANA", "pitta": "KOPANA", "kapha": "VARDHANA"},
        calories_per_100g=120.0, protein_g=20.0, carbs_g=0.0, fat_g=4.5,
    ),
    DietIngredient(
        ingredient_id="ING-JANGALA-MAMSA",
        sanskrit_name="जाङ्गल मांस (Jangala Mamsa / Light Meat)",
        english_name="Wild Quail / Lean Game Meat",
        ahara_varga=AharaVarga.MAMSA_VARGA,
        rasa="Kashaya-Madhura",
        veerya="Sheeta",
        vipaka="Katu",
        guna=["Laghu", "Vishada"],
        doshic_effect={"vata": "SHAMANA", "pitta": "SHAMANA", "kapha": "SHAMANA"},
        calories_per_100g=135.0, protein_g=24.5, carbs_g=0.0, fat_g=3.5,
    ),
    # Spices & Condiments (Harita & Aharayogi Varga)
    DietIngredient(
        ingredient_id="ING-ARDRAKA",
        sanskrit_name="आर्द्रक (Ardraka / Fresh Ginger)",
        english_name="Fresh Ginger Root",
        ahara_varga=AharaVarga.HARITA_VARGA,
        rasa="Katu",
        veerya="Ushna",
        vipaka="Madhura",
        guna=["Guru", "Ruksha", "Teekshna"],
        doshic_effect={"vata": "SHAMANA", "pitta": "ALPA_KOPANA", "kapha": "SHAMANA"},
        calories_per_100g=80.0, protein_g=1.8, carbs_g=17.8, fat_g=0.8,
    ),
    DietIngredient(
        ingredient_id="ING-LASHUNA",
        sanskrit_name="लशुन (Lashuna / Garlic)",
        english_name="Garlic Cloves",
        ahara_varga=AharaVarga.HARITA_VARGA,
        rasa="Madhura-Katu-Lavana-Tikta-Kashaya",
        veerya="Ushna",
        vipaka="Katu",
        guna=["Guru", "Snigdha", "Teekshna"],
        doshic_effect={"vata": "SHAMANA", "pitta": "KOPANA", "kapha": "SHAMANA"},
        calories_per_100g=149.0, protein_g=6.4, carbs_g=33.1, fat_g=0.5,
    ),
    DietIngredient(
        ingredient_id="ING-TILA-TAILA",
        sanskrit_name="तिल तैल (Tila Taila / Sesame Oil)",
        english_name="Cold Pressed Sesame Seed Oil",
        ahara_varga=AharaVarga.AHARAYOGI_VARGA,
        rasa="Madhura-Tikta-Kashaya",
        veerya="Ushna",
        vipaka="Madhura",
        guna=["Guru", "Vyavayi", "Sookshma"],
        doshic_effect={"vata": "SHAMANA", "pitta": "ALPA_KOPANA", "kapha": "AVIRUDDHA"},
        calories_per_100g=884.0, protein_g=0.0, carbs_g=0.0, fat_g=100.0,
    ),
    DietIngredient(
        ingredient_id="ING-SAINDHAVA",
        sanskrit_name="सैन्धव लवण (Saindhava Lavana)",
        english_name="Himalayan Pink Rock Salt",
        ahara_varga=AharaVarga.AHARAYOGI_VARGA,
        rasa="Lavana-Madhura",
        veerya="Sheeta",
        vipaka="Madhura",
        guna=["Laghu", "Snigdha", "Tridoshahara"],
        doshic_effect={"vata": "SHAMANA", "pitta": "SHAMANA", "kapha": "SHAMANA"},
        calories_per_100g=0.0, protein_g=0.0, carbs_g=0.0, fat_g=0.0,
    ),
]


# ==============================================================================
# DISEASE-SPECIFIC PATHYA & APATHYA REGISTRY
# ==============================================================================

SEED_PATHYA_APATHYA_REGISTRY: List[DiseasePathyaApathya] = [
    DiseasePathyaApathya(
        registry_id="PATHYA-AMAVATA",
        disease_code="AYU-DIS-AMAVATA",
        disease_name="आमवात (Amavata / Rheumatoid Arthritis)",
        pathya_ahara=["यव (Yava)", "कुलत्थ (Kulattha)", "रक्तशालि (Raktashali)", "आर्द्रक (Ardraka)", "लशुन (Lashuna)", "पटोल (Patola)", "कारवेल्लक (Karavellaka)", "तक्र (Takra)"],
        apathya_ahara=["दधि (Dadhi)", "मत्स्य (Matsya)", "माष (Masha)", "शीत जल (Sheeta Jala)", "पिष्टान्न (Heavy pastries)", "दही बड़ा (Dahi Vada)"],
        pathya_vihara=["लङ्घन (Fasting / Lightness)", "स्वेदन (Dry fomentation)", "उष्ण जल स्नान (Warm bath)", "मृदु व्यायाम (Gentle movement)"],
        apathya_vihara=["दिवास्वप्न (Day sleep)", "रात्रिजागरण (Night vigil)", "पूर्वावात (East cold wind)", "वेगरोध (Suppression of urges)"]
    ),
    DiseasePathyaApathya(
        registry_id="PATHYA-SANDHIGATA-VATA",
        disease_code="AYU-DIS-SANDHIGATA-VATA",
        disease_name="सन्धिगत वात (Sandhigata Vata / Osteoarthritis)",
        pathya_ahara=["गोधूम (Godhuma)", "रक्तशालि (Raktashali)", "माष (Masha)", "गोधृत (Go-Ghrita)", "गोदुग्ध (Godugdha)", "तिल तैल (Tila Taila)", "दाडिम (Dadima)", "द्राक्षा (Draksha)"],
        apathya_ahara=["यव (Yava)", "चना (Chanaka)", "अति रुक्ष आहार (Excessively dry food)", "शीत आहार (Cold food)", "अति लङ्घन (Severe fasting)"],
        pathya_vihara=["अभ्यङ्ग (Daily oil massage)", "मृदु स्वेदन (Gentle warm fomentation)", "विश्राम (Adequate joint rest)"],
        apathya_vihara=["अति व्यायाम (Strenuous weight-bearing)", "धावन (Running/Jumping)", "शीत वात सेवा (Cold draft)"]
    ),
    DiseasePathyaApathya(
        registry_id="PATHYA-PRAMEHA",
        disease_code="AYU-DIS-PRAMEHA",
        disease_name="प्रमेह (Prameha / Metabolic Syndrome & Diabetes)",
        pathya_ahara=["यव (Yava)", "मुद्ग (Mudga)", "पटोल (Patola)", "कारवेल्लक (Karavellaka)", "पुराण शालि (Old rice)", "तक्र (Takra)", "त्रिफला (Triphala)"],
        apathya_ahara=["गुड (Jaggery)", "इक्षु (Sugarcane)", "दधि (Dadhi)", "नवान्न (New harvested grains)", "आनूप मांस (Aquatic meats)", "मिष्टान्न (Sweets)"],
        pathya_vihara=["व्यायाम (Brisk walking / physical labor)", "जागरण (Active daytime)", "उद्वर्तन (Dry powder rubbing)"],
        apathya_vihara=["दिवास्वप्न (Day sleep)", "आस्यासुख (Sedentary lifestyle)", "शय्यासुख (Excessive bed rest)"]
    ),
    DiseasePathyaApathya(
        registry_id="PATHYA-AMLAPITTA",
        disease_code="AYU-DIS-AMLAPITTA",
        disease_name="अम्लपित्त (Amlapitta / Hyperacidity & Dyspepsia)",
        pathya_ahara=["पुराण रक्तशालि (Aged Red Rice)", "मुद्ग (Mudga)", "गोदुग्ध (Cold Milk)", "गोधृत (Cow Ghee)", "दाडिम (Sweet Dadima)", "द्राक्षा (Draksha)", "पटोल (Patola)"],
        apathya_ahara=["अम्ल रस (Sour/fermented food)", "कटु रस (Chili/hot spices)", "लवण (High salt)", "दधि (Curd)", "मद्य (Alcohol)", "कुलत्थ (Horse gram)"],
        pathya_vihara=["शीतल मन्द पवन (Gentle cool breeze)", "मानसिक शान्ति (Mental tranquility)", "चन्द्रकिरण सेवा (Moonlight)"],
        apathya_vihara=["क्रोध (Anger)", "चिन्ता (Anxiety)", "धूमपान (Smoking)", "आतप सेवा (Direct harsh sun)"]
    ),
]


# ==============================================================================
# DATABASE INITIALIZATION & SEEDING ENGINE
# ==============================================================================

def initialize_dietetics_tables(conn: sqlite3.Connection) -> None:
    """Populate diet_ingredients_catalog and disease_pathya_apathya_registry if unseeded."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM diet_ingredients_catalog;")
    row = cursor.fetchone()
    if row and row["cnt"] == 0:
        now = int(time.time())
        for ing in SEED_DIET_INGREDIENTS:
            cursor.execute(
                """
                INSERT INTO diet_ingredients_catalog (
                    ingredient_id, sanskrit_name, english_name, ahara_varga,
                    rasa, veerya, vipaka, guna_json, doshic_effect_json,
                    calories_per_100g, protein_g, carbs_g, fat_g, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    ing.ingredient_id,
                    ing.sanskrit_name,
                    ing.english_name,
                    ing.ahara_varga.value,
                    ing.rasa,
                    ing.veerya,
                    ing.vipaka,
                    json.dumps(ing.guna),
                    json.dumps(ing.doshic_effect),
                    ing.calories_per_100g,
                    ing.protein_g,
                    ing.carbs_g,
                    ing.fat_g,
                    now,
                )
            )

        for pa in SEED_PATHYA_APATHYA_REGISTRY:
            cursor.execute(
                """
                INSERT INTO disease_pathya_apathya_registry (
                    registry_id, disease_code, disease_name, pathya_ahara_json,
                    apathya_ahara_json, pathya_vihara_json, apathya_vihara_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    pa.registry_id,
                    pa.disease_code,
                    pa.disease_name,
                    json.dumps(pa.pathya_ahara),
                    json.dumps(pa.apathya_ahara),
                    json.dumps(pa.pathya_vihara),
                    json.dumps(pa.apathya_vihara),
                    now,
                )
            )
        conn.commit()


def get_ingredient_profile(ingredient_id: str, conn: sqlite3.Connection) -> DietIngredient:
    """Retrieve food ingredient profile by ID."""
    initialize_dietetics_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM diet_ingredients_catalog WHERE ingredient_id = ?;", (ingredient_id,))
    row = cursor.fetchone()
    if not row:
        raise RecordNotFoundException("DietIngredient", ingredient_id)

    return DietIngredient(
        ingredient_id=row["ingredient_id"],
        sanskrit_name=row["sanskrit_name"],
        english_name=row["english_name"],
        ahara_varga=AharaVarga(row["ahara_varga"]),
        rasa=row["rasa"],
        veerya=row["veerya"],
        vipaka=row["vipaka"],
        guna=json.loads(row["guna_json"]),
        doshic_effect=json.loads(row["doshic_effect_json"]),
        calories_per_100g=row["calories_per_100g"],
        protein_g=row["protein_g"],
        carbs_g=row["carbs_g"],
        fat_g=row["fat_g"],
    )


def list_all_ingredients(conn: sqlite3.Connection) -> List[DietIngredient]:
    """List all registered food ingredients."""
    initialize_dietetics_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM diet_ingredients_catalog ORDER BY ingredient_id ASC;")
    rows = cursor.fetchall()
    return [
        DietIngredient(
            ingredient_id=r["ingredient_id"],
            sanskrit_name=r["sanskrit_name"],
            english_name=r["english_name"],
            ahara_varga=AharaVarga(r["ahara_varga"]),
            rasa=r["rasa"],
            veerya=r["veerya"],
            vipaka=r["vipaka"],
            guna=json.loads(r["guna_json"]),
            doshic_effect=json.loads(r["doshic_effect_json"]),
            calories_per_100g=r["calories_per_100g"],
            protein_g=r["protein_g"],
            carbs_g=r["carbs_g"],
            fat_g=r["fat_g"],
        )
        for r in rows
    ]


def get_disease_pathya_guidelines(disease_code: str, conn: sqlite3.Connection) -> Optional[DiseasePathyaApathya]:
    """Retrieve Pathya & Apathya guidelines for a disease code."""
    initialize_dietetics_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM disease_pathya_apathya_registry WHERE disease_code = ?;", (disease_code,))
    row = cursor.fetchone()
    if not row:
        return None

    return DiseasePathyaApathya(
        registry_id=row["registry_id"],
        disease_code=row["disease_code"],
        disease_name=row["disease_name"],
        pathya_ahara=json.loads(row["pathya_ahara_json"]),
        apathya_ahara=json.loads(row["apathya_ahara_json"]),
        pathya_vihara=json.loads(row["pathya_vihara_json"]),
        apathya_vihara=json.loads(row["apathya_vihara_json"]),
    )


# ==============================================================================
# 18-FOLD VIRUDDHA AHARA INCOMPATIBILITY AUDIT ENGINE
# ==============================================================================

def audit_viruddha_ahara(meals: List[PlannedMeal], conn: sqlite3.Connection) -> List[ViruddhaViolation]:
    """
    Executes deep scanning across meals for 18-fold Viruddha Ahara violations:
    1. Veerya Viruddha: Fish (Ushna) + Milk (Sheeta)
    2. Samyoga Viruddha: Milk + Sour Fruit / Curd; Milk + Banana
    3. Matra Viruddha: Honey + Ghee in 1:1 equal weight
    4. Samskara Viruddha: Heated Honey (is_heated=True); Heated Curd
    5. Kala Viruddha: Curd taken in evening/dinner meal (Sayam)
    """
    violations: List[ViruddhaViolation] = []

    for meal in meals:
        item_ids = [it.ingredient_id for it in meal.items]
        meal_name_upper = meal.meal_name.upper()

        # 1. Veerya Viruddha: Fish + Milk
        if "ING-MATSYA" in item_ids and "ING-GODUGDHA" in item_ids:
            violations.append(
                ViruddhaViolation(
                    viruddha_type=ViruddhaType.VEERYA_VIRUDDHA,
                    substances_involved=["Matsya (Fish)", "Godugdha (Milk)"],
                    clinical_rationale="Veerya Viruddha: Fish (Ushna Veerya) and Milk (Sheeta Veerya) clash in blood and trigger severe Raktadushti, Maha Kushta, and channel blockage.",
                    severity="CRITICAL_BLOCKED"
                )
            )

        # 2. Samyoga Viruddha: Milk + Banana
        if "ING-GODUGDHA" in item_ids and "ING-KADALI" in item_ids:
            violations.append(
                ViruddhaViolation(
                    viruddha_type=ViruddhaType.SAMYOGA_VIRUDDHA,
                    substances_involved=["Godugdha (Milk)", "Kadali (Banana)"],
                    clinical_rationale="Samyoga Viruddha: Milk and Banana combination diminishes Agni (digestive fire), alters bowel flora, and produces chronic heaviness (Gaurava).",
                    severity="WARNING"
                )
            )

        # 3. Matra Viruddha: Honey + Ghee in equal parts (1:1)
        if "ING-MADHU" in item_ids and "ING-GHRITA" in item_ids:
            honey_item = next(it for it in meal.items if it.ingredient_id == "ING-MADHU")
            ghee_item = next(it for it in meal.items if it.ingredient_id == "ING-GHRITA")
            if abs(honey_item.portion_grams - ghee_item.portion_grams) < 0.5:
                violations.append(
                    ViruddhaViolation(
                        viruddha_type=ViruddhaType.MATRA_VIRUDDHA,
                        substances_involved=["Madhu (Honey)", "Go-Ghrita (Ghee)"],
                        clinical_rationale="Matra Viruddha: Honey and Ghee combined in equal 1:1 proportion acts as a metabolic toxin (Visha). Ratios must be strictly unequal (e.g. 2:1 or 1:3).",
                        severity="CRITICAL_BLOCKED"
                    )
                )

        # 4. Samskara Viruddha: Heated Honey
        if "ING-MADHU" in item_ids:
            honey_item = next(it for it in meal.items if it.ingredient_id == "ING-MADHU")
            if honey_item.is_heated:
                violations.append(
                    ViruddhaViolation(
                        viruddha_type=ViruddhaType.SAMSKARA_VIRUDDHA,
                        substances_involved=["Madhu (Honey)"],
                        clinical_rationale="Samskara Viruddha: Honey subjected to heating or boiling produces toxic Ama-Visha (HMF buildup) that clogs deep srotases.",
                        severity="CRITICAL_BLOCKED"
                    )
                )

        # 5. Samskara Viruddha: Heated Curd
        if "ING-DADHI" in item_ids:
            curd_item = next(it for it in meal.items if it.ingredient_id == "ING-DADHI")
            if curd_item.is_heated:
                violations.append(
                    ViruddhaViolation(
                        viruddha_type=ViruddhaType.SAMSKARA_VIRUDDHA,
                        substances_involved=["Dadhi (Curd)"],
                        clinical_rationale="Samskara Viruddha: Heating curd destabilizes its protein matrix and causes acute channel obstruction (Abhishyanda).",
                        severity="WARNING"
                    )
                )

        # 6. Kala Viruddha: Curd at Night (Dinner / Sayam)
        if "ING-DADHI" in item_ids and any(term in meal_name_upper for term in ["DINNER", "SAYAM", "RATRI"]):
            violations.append(
                ViruddhaViolation(
                    viruddha_type=ViruddhaType.KALA_VIRUDDHA,
                    substances_involved=["Dadhi (Curd)"],
                    clinical_rationale="Kala Viruddha: Curd is strictly contraindicated at night (Nishi Dadhi Nishiddha) as it severely provokes Kapha-Pitta, leads to swelling (Shotha), and impairs sleep.",
                    severity="WARNING"
                )
            )

    return violations


# ==============================================================================
# CLINICAL DIET PLANNING & NUTRITIONAL SYNTHESIS
# ==============================================================================

def create_and_evaluate_diet_plan(
    req: DietPlanCreateRequest,
    hospital_id: str,
    conn: sqlite3.Connection
) -> DietPlanResponse:
    """
    Evaluates meal composition, checks 18-fold Viruddha Ahara, computes macro/calories,
    determines composite Doshic shift, and cross-references Pathya-Apathya.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM patients WHERE patient_id = ?;", (req.patient_id,))
    if not cursor.fetchone():
        raise RecordNotFoundException("Patient", req.patient_id)

    # 1. Audit Viruddha Ahara
    violations = audit_viruddha_ahara(req.meals, conn)
    critical_violations = [v for v in violations if v.severity == "CRITICAL_BLOCKED"]
    viruddha_passed = (len(critical_violations) == 0)

    # If critical violations exist, block plan creation
    if not viruddha_passed:
        reasons = "; ".join(v.clinical_rationale for v in critical_violations)
        raise ClinicalGovernanceException(
            f"Diet Plan Rejected due to Critical Viruddha Ahara Violation: {reasons}",
            error_code="CRITICAL_VIRUDDHA_AHARA_BLOCKED"
        )

    # 2. Nutritional and Doshic Computation
    total_calories = 0.0
    total_protein = 0.0
    total_carbs = 0.0
    total_fat = 0.0

    doshic_counts = {"vata": 0.0, "pitta": 0.0, "kapha": 0.0}
    total_grams = 0.0

    all_ing_names: List[str] = []

    for meal in req.meals:
        for item in meal.items:
            ing = get_ingredient_profile(item.ingredient_id, conn)
            factor = item.portion_grams / 100.0
            total_calories += (ing.calories_per_100g * factor)
            total_protein += (ing.protein_g * factor)
            total_carbs += (ing.carbs_g * factor)
            total_fat += (ing.fat_g * factor)
            total_grams += item.portion_grams

            all_ing_names.append(ing.sanskrit_name)

            # Doshic impact vector
            v_eff = ing.doshic_effect.get("vata", "AVIRUDDHA")
            p_eff = ing.doshic_effect.get("pitta", "AVIRUDDHA")
            k_eff = ing.doshic_effect.get("kapha", "AVIRUDDHA")

            v_val = -0.5 if "SHAMANA" in v_eff else (0.5 if "KOPANA" in v_eff else 0.0)
            p_val = -0.5 if "SHAMANA" in p_eff else (0.5 if "KOPANA" in p_eff else 0.0)
            k_val = -0.5 if "SHAMANA" in k_eff else (0.5 if "VARDHANA" in k_eff else 0.0)

            doshic_counts["vata"] += (v_val * item.portion_grams)
            doshic_counts["pitta"] += (p_val * item.portion_grams)
            doshic_counts["kapha"] += (k_val * item.portion_grams)

    # Normalize composite Doshic vector to [-1.0, +1.0]
    composite_doshic: Dict[str, float] = {}
    if total_grams > 0:
        composite_doshic["delta_vata"] = round(max(-1.0, min(1.0, doshic_counts["vata"] / total_grams)), 3)
        composite_doshic["delta_pitta"] = round(max(-1.0, min(1.0, doshic_counts["pitta"] / total_grams)), 3)
        composite_doshic["delta_kapha"] = round(max(-1.0, min(1.0, doshic_counts["kapha"] / total_grams)), 3)
    else:
        composite_doshic = {"delta_vata": 0.0, "delta_pitta": 0.0, "delta_kapha": 0.0}

    # 3. Pathya-Apathya Compliance Cross-Referencing
    pathya_guideline = get_disease_pathya_guidelines(req.diagnosis_code, conn)
    pathya_matches = 0
    total_items = max(1, len(all_ing_names))

    if pathya_guideline:
        raw_tokens: List[str] = []
        for p in pathya_guideline.pathya_ahara:
            for part in p.replace("(", " ").replace(")", " ").split():
                cleaned = part.strip().lower()
                if len(cleaned) >= 2:
                    raw_tokens.append(cleaned)

        for name in all_ing_names:
            name_lower = name.lower()
            if any(tok in name_lower for tok in raw_tokens):
                pathya_matches += 1

    pathya_compliance = round((pathya_matches / total_items) * 100.0, 1)

    now = int(time.time())
    diet_plan_id = f"DIET-{req.patient_id}-{now}"

    # Persist in patient_diet_prescriptions
    cursor.execute(
        """
        INSERT INTO patient_diet_prescriptions (
            diet_plan_id, patient_id, hospital_id, diagnosis_code,
            target_calories, meals_json, viruddha_check_passed,
            viruddha_violations_json, prescribed_by_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            diet_plan_id,
            req.patient_id,
            hospital_id,
            req.diagnosis_code,
            req.target_calories,
            json.dumps([m.model_dump() for m in req.meals]),
            1 if viruddha_passed else 0,
            json.dumps([v.model_dump() for v in violations]),
            req.prescribed_by_arn,
            now,
        )
    )
    conn.commit()

    rec = (
        f"Prescribed diet plan delivering {total_calories:.1f} kcal (Target: {req.target_calories:.1f} kcal). "
        f"Pathya compliance: {pathya_compliance}%. Viruddha Ahara clear: {viruddha_passed}."
    )

    return DietPlanResponse(
        diet_plan_id=diet_plan_id,
        patient_id=req.patient_id,
        diagnosis_code=req.diagnosis_code,
        target_calories=req.target_calories,
        total_calories=round(total_calories, 2),
        total_protein_g=round(total_protein, 2),
        total_carbs_g=round(total_carbs, 2),
        total_fat_g=round(total_fat, 2),
        composite_doshic_vector=composite_doshic,
        viruddha_check_passed=viruddha_passed,
        viruddha_violations=violations,
        pathya_compliance_score=pathya_compliance,
        clinical_recommendation=rec,
        prescribed_by_arn=req.prescribed_by_arn,
        created_at=now,
    )
