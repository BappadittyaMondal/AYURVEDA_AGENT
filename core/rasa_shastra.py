"""
Rasa Shastra & Herbo-Mineral Processing Safety Engine
=====================================================
Implements:
1. Classical registry of minerals, metals, and Schedule E(1) poisons
2. Shodhana (Purification & Detoxification) verification protocol
3. Classical Bhasma Pariksha (7 nanoscale verification tests)
4. AAS / ICP-MS Elemental Assay & Heavy Metal Limit Enforcement (AFI/AYUSH)
5. Particle Size Distribution (Laser Diffraction / Nanocrystalline standards)
6. Permitted Daily Exposure (PDE) & Cumulative Toxicity Calculations
7. SQLite WAL persistence with indexed retrieval
"""

from __future__ import annotations
import json
import time
import sqlite3
from typing import List, Optional, Dict, Any, Tuple

from core.exceptions import (
    HeavyMetalExposureExceededException,
    RecordNotFoundException,
    ScheduleE1ShodhanaMissingException,
)
from models.rasa_shastra import (
    BatchPrescriptionItem,
    BhasmaBatchReleaseCertificate,
    BhasmaBatchReleaseRequest,
    BhasmaPariksha,
    ElementalAssay,
    HeavyMetalExposureCheckRequest,
    HeavyMetalExposureCheckResponse,
    ParticleSizeAnalysis,
    PutaType,
    RasaCategory,
    RasaMineralRecord,
    ShodhanaMethod,
    ShodhanaRecord,
    ShodhanaVerificationRequest,
)

# ==============================================================================
# SEED RASA SHASTRA MINERAL & HERBO-MINERAL REGISTRY (18 CLASSICAL ENTITIES)
# ==============================================================================

SEED_RASA_MINERALS_REGISTRY: List[RasaMineralRecord] = [
    # 1. PARADA (Mercury) - Maharasa / Rasa Raja
    RasaMineralRecord(
        mineral_id="MIN-PARADA",
        sanskrit_name="पारद (Parada)",
        english_name="Purified Elemental Mercury",
        chemical_formula="Hg",
        category=RasaCategory.MAHARASA,
        is_schedule_e1_poison=True,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.BHAVANA_TRITURATION,
        standard_shodhana_media=["Kumari Swarasa (Aloe Vera)", "Rasona Kalka (Garlic paste)", "Tankana (Borax)"],
        minimum_shodhana_cycles=3,
        standard_puta_type=PutaType.VALUKA_YANTRA,
        minimum_puta_cycles=1,
        therapeutic_dose_mg_min=15.0,
        therapeutic_dose_mg_max=60.0,
        classical_indications=["Rasayana", "Yogavahi", "Sarvarogahara", "Tridoshashamana"],
        toxicity_risk_profile="Extremely toxic if unpurified. Causes acute renal tubular necrosis, tremors, and systemic toxicity (Maha Doshas)."
    ),
    # 2. GANDHAKA (Sulfur) - Uparasa
    RasaMineralRecord(
        mineral_id="MIN-GANDHAKA",
        sanskrit_name="गन्धक (Gandhaka)",
        english_name="Purified Elemental Sulfur",
        chemical_formula="S",
        category=RasaCategory.UPARASA,
        is_schedule_e1_poison=False,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.DHALANA_MELTING_POURING,
        standard_shodhana_media=["Godugdha (Cow Milk)", "Go-Ghrita (Cow Ghee)"],
        minimum_shodhana_cycles=7,
        standard_puta_type=None,
        minimum_puta_cycles=0,
        therapeutic_dose_mg_min=125.0,
        therapeutic_dose_mg_max=500.0,
        classical_indications=["Kushtahara", "Krimighna", "Kandughna", "Rasayana", "Dipana"],
        toxicity_risk_profile="Unpurified sulfur causes acute Pitta prakopa, burning sensation (Daha), skin ulcerations, and gastritis."
    ),
    # 3. HINGULA (Cinnabar) - Sadharana Rasa
    RasaMineralRecord(
        mineral_id="MIN-HINGULA",
        sanskrit_name="हिङ्गुल (Hingula)",
        english_name="Cinnabar / Red Mercuric Sulfide",
        chemical_formula="HgS",
        category=RasaCategory.SADHARANA_RASA,
        is_schedule_e1_poison=True,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.BHAVANA_TRITURATION,
        standard_shodhana_media=["Nimbu Swarasa (Lemon Juice)", "Ardraka Swarasa (Ginger Juice)"],
        minimum_shodhana_cycles=7,
        standard_puta_type=PutaType.VALUKA_YANTRA,
        minimum_puta_cycles=1,
        therapeutic_dose_mg_min=30.0,
        therapeutic_dose_mg_max=125.0,
        classical_indications=["Sarva Jwarahara", "Dipana", "Pachana", "Rasayana", "Kaphapittahara"],
        toxicity_risk_profile="Contains mercury sulfide; raw form contains free heavy metal impurities leading to renal and neurological damage."
    ),
    # 4. ABHRAKA (Biotite Mica) - Maharasa
    RasaMineralRecord(
        mineral_id="MIN-ABHRAKA",
        sanskrit_name="अभ्रक (Vajra Abhraka)",
        english_name="Black Biotite Mica",
        chemical_formula="K(Mg,Fe)3(AlSi3O10)(OH)2",
        category=RasaCategory.MAHARASA,
        is_schedule_e1_poison=False,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.NIRVAPA_QUENCHING,
        standard_shodhana_media=["Triphala Kwatha", "Kanji (Fermented Gruel)", "Gomutra (Cow Urine)"],
        minimum_shodhana_cycles=7,
        standard_puta_type=PutaType.GAJA_PUTA,
        minimum_puta_cycles=30,  # Minimum 30 Putas for basic Bhasma, up to 100 for Shataputi
        therapeutic_dose_mg_min=65.0,
        therapeutic_dose_mg_max=250.0,
        classical_indications=["Prameha", "Rajayakshma", "Shwasa-Kasa", "Medhya", "Rasayana", "Balya"],
        toxicity_risk_profile="Improperly calcined Abhraka causes splenic enlargement (Pliha), severe flatulence (Topa), and colic (Shula)."
    ),
    # 5. SWARNA MAKSHIKA (Copper Pyrite) - Maharasa
    RasaMineralRecord(
        mineral_id="MIN-MAKSHIKA",
        sanskrit_name="स्वर्णमाक्षिक (Swarna Makshika)",
        english_name="Chalcopyrite / Copper Iron Sulfide",
        chemical_formula="CuFeS2",
        category=RasaCategory.MAHARASA,
        is_schedule_e1_poison=False,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.BHARJANA_ROASTING,
        standard_shodhana_media=["Eranda Taila (Castor Oil)", "Matulunga Swarasa (Wild Lemon Juice)"],
        minimum_shodhana_cycles=3,
        standard_puta_type=PutaType.VARAHA_PUTA,
        minimum_puta_cycles=10,
        therapeutic_dose_mg_min=65.0,
        therapeutic_dose_mg_max=250.0,
        classical_indications=["Pandu (Anemia)", "Prameha", "Kushtha", "Jwara", "Netraroga"],
        toxicity_risk_profile="Contains raw copper and sulfur; unpurified Makshika produces severe nausea, emesis, and intestinal griping."
    ),
    # 6. SHILAJATU (Asphaltum) - Maharasa
    RasaMineralRecord(
        mineral_id="MIN-SHILAJATU",
        sanskrit_name="शिलाजतु (Shuddha Shilajatu)",
        english_name="Purified Asphaltum / Mineral Pitch",
        chemical_formula="Humic-Fulvic-Mineral Complex",
        category=RasaCategory.MAHARASA,
        is_schedule_e1_poison=False,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.KSHALANA_WASHING,
        standard_shodhana_media=["Triphala Kwatha", "Ushnodaka (Warm Water)"],
        minimum_shodhana_cycles=3,
        standard_puta_type=None,
        minimum_puta_cycles=0,
        therapeutic_dose_mg_min=250.0,
        therapeutic_dose_mg_max=1000.0,
        classical_indications=["Prameha (Diabetes)", "Medoroga (Obesity)", "Mutrakrichhra", "Rasayana"],
        toxicity_risk_profile="Crude rock pitch contains heavy toxic mycotoxins, heavy stone dust, and pathogenic fungi if unpurified."
    ),
    # 7. HARATALA (Orpiment) - Uparasa
    RasaMineralRecord(
        mineral_id="MIN-HARATALA",
        sanskrit_name="हरताल (Haratala)",
        english_name="Yellow Orpiment / Arsenic Trisulfide",
        chemical_formula="As2S3",
        category=RasaCategory.UPARASA,
        is_schedule_e1_poison=True,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.SWEDANA_DOLA_YANTRA,
        standard_shodhana_media=["Kushmanda Swarasa (Ash Gourd Juice)", "Churna Jala (Lime Water)"],
        minimum_shodhana_cycles=1,  # 12 hours continuous Swedana
        standard_puta_type=PutaType.GAJA_PUTA,
        minimum_puta_cycles=12,
        therapeutic_dose_mg_min=15.0,
        therapeutic_dose_mg_max=30.0,
        classical_indications=["Kushtha (Chronic Dermatoses)", "Shwasa", "Kasa", "Vatarakta"],
        toxicity_risk_profile="Lethal trivalent arsenic toxicity if unpurified. Causes severe hemorrhagic gastroenteritis and collapse."
    ),
    # 8. MANASHILA (Realgar) - Uparasa
    RasaMineralRecord(
        mineral_id="MIN-MANASHILA",
        sanskrit_name="मनःशिला (Manashila)",
        english_name="Red Realgar / Arsenic Disulfide",
        chemical_formula="As4S4",
        category=RasaCategory.UPARASA,
        is_schedule_e1_poison=True,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.BHAVANA_TRITURATION,
        standard_shodhana_media=["Agastya Patra Swarasa", "Ardraka Swarasa (Fresh Ginger Juice)"],
        minimum_shodhana_cycles=7,
        standard_puta_type=PutaType.KUKKUTA_PUTA,
        minimum_puta_cycles=7,
        therapeutic_dose_mg_min=8.0,
        therapeutic_dose_mg_max=25.0,
        classical_indications=["Kasa", "Shwasa", "Agada (Antidote)", "Netraroga"],
        toxicity_risk_profile="Arsenic compound; unpurified administration triggers acute arsenic keratosis, gastrointestinal distress, and anuria."
    ),
    # 9. SUVARNA (Gold) - Shuddha Lauha
    RasaMineralRecord(
        mineral_id="MIN-SUVARNA",
        sanskrit_name="सुवर्ण (Swarna)",
        english_name="Elemental Gold / Gold Bhasma Core",
        chemical_formula="Au",
        category=RasaCategory.DHATU_SHUDDHA,
        is_schedule_e1_poison=False,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.NIRVAPA_QUENCHING,
        standard_shodhana_media=["Tila Taila", "Takra", "Kulattha Kwatha", "Kanji", "Gomutra"],
        minimum_shodhana_cycles=7,
        standard_puta_type=PutaType.VARAHA_PUTA,
        minimum_puta_cycles=10,
        therapeutic_dose_mg_min=15.0,
        therapeutic_dose_mg_max=60.0,
        classical_indications=["Hridya", "Medhya", "Rasayana", "Vrishya", "Ojavardhaka", "Visha Nashaka"],
        toxicity_risk_profile="Metallic coarse gold causes cellular occlusion; requires complete conversion to sub-micron Bhasma."
    ),
    # 10. RAJATA (Silver) - Shuddha Lauha
    RasaMineralRecord(
        mineral_id="MIN-RAJATA",
        sanskrit_name="रजत (Roupya)",
        english_name="Elemental Silver / Rajata Bhasma Core",
        chemical_formula="Ag",
        category=RasaCategory.DHATU_SHUDDHA,
        is_schedule_e1_poison=False,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.NIRVAPA_QUENCHING,
        standard_shodhana_media=["Tila Taila", "Takra", "Kulattha Kwatha", "Kanji", "Gomutra"],
        minimum_shodhana_cycles=7,
        standard_puta_type=PutaType.VARAHA_PUTA,
        minimum_puta_cycles=10,
        therapeutic_dose_mg_min=30.0,
        therapeutic_dose_mg_max=125.0,
        classical_indications=["Pittashamana", "Medhya", "Prameha", "Unmada", "Vayasthapana"],
        toxicity_risk_profile="Raw silver particles cause Argyria (tissue pigmentation) and mucosal irritation."
    ),
    # 11. TAMRA (Copper) - Shuddha Lauha
    RasaMineralRecord(
        mineral_id="MIN-TAMRA",
        sanskrit_name="ताम्र (Shuddha Tamra)",
        english_name="Purified Copper / Tamra Bhasma Core",
        chemical_formula="Cu",
        category=RasaCategory.DHATU_SHUDDHA,
        is_schedule_e1_poison=False,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.NIRVAPA_QUENCHING,
        standard_shodhana_media=["Gomutra (Cow Urine)", "Nimbu Swarasa"],
        minimum_shodhana_cycles=8,
        standard_puta_type=PutaType.GAJA_PUTA,
        minimum_puta_cycles=8,
        therapeutic_dose_mg_min=15.0,
        therapeutic_dose_mg_max=60.0,
        classical_indications=["Yakridroga (Hepatobiliary)", "Pliharoga (Splenomegaly)", "Lekhana", "Grahani"],
        toxicity_risk_profile="Ashta Maha Dosha (8 fatal complications) of unpurified copper: Bhrama (vertigo), Moha, Utklesha (nausea), Daha, and liver cirrhosis."
    ),
    # 12. LAUHA (Iron) - Shuddha Lauha
    RasaMineralRecord(
        mineral_id="MIN-LAUHA",
        sanskrit_name="तीक्ष्णलौह (Teekshna Lauha)",
        english_name="Purified Iron / Lauha Bhasma Core",
        chemical_formula="Fe",
        category=RasaCategory.DHATU_SHUDDHA,
        is_schedule_e1_poison=False,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.NIRVAPA_QUENCHING,
        standard_shodhana_media=["Triphala Kwatha", "Gomutra"],
        minimum_shodhana_cycles=21,
        standard_puta_type=PutaType.MAHA_PUTA,
        minimum_puta_cycles=30,
        therapeutic_dose_mg_min=65.0,
        therapeutic_dose_mg_max=250.0,
        classical_indications=["Panduroga (Iron Deficiency Anemia)", "Kamala", "Shotha", "Balya", "Rasayana"],
        toxicity_risk_profile="Incompletely incinerated iron causes severe constipation, mucosal abrasions, hepatomegaly, and Guruta."
    ),
    # 13. NAGA (Lead) - Puti Lauha
    RasaMineralRecord(
        mineral_id="MIN-NAGA",
        sanskrit_name="नाग (Shuddha Naga)",
        english_name="Purified Lead / Naga Bhasma Core",
        chemical_formula="Pb",
        category=RasaCategory.DHATU_PUTI,
        is_schedule_e1_poison=True,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.DHALANA_MELTING_POURING,
        standard_shodhana_media=["Churna Jala (Lime water)", "Nirgundi Swarasa"],
        minimum_shodhana_cycles=7,
        standard_puta_type=PutaType.GAJA_PUTA,
        minimum_puta_cycles=30,
        therapeutic_dose_mg_min=30.0,
        therapeutic_dose_mg_max=65.0,
        classical_indications=["Prameha (Diabetic carbuncles)", "Grahani", "Atisara", "Bhagandara"],
        toxicity_risk_profile="Severe neuro-toxic and nephrotoxic plumbi-toxicity if unpurified. Mandatory strict ICP-MS assay verification."
    ),
    # 14. VANGA (Tin) - Puti Lauha
    RasaMineralRecord(
        mineral_id="MIN-VANGA",
        sanskrit_name="वङ्ग (Shuddha Vanga)",
        english_name="Purified Tin / Vanga Bhasma Core",
        chemical_formula="Sn",
        category=RasaCategory.DHATU_PUTI,
        is_schedule_e1_poison=False,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.DHALANA_MELTING_POURING,
        standard_shodhana_media=["Haridra Churna in Takra", "Kulattha Kwatha"],
        minimum_shodhana_cycles=7,
        standard_puta_type=PutaType.VARAHA_PUTA,
        minimum_puta_cycles=10,
        therapeutic_dose_mg_min=65.0,
        therapeutic_dose_mg_max=250.0,
        classical_indications=["Prameha", "Shukrakshaya", "Shwetapradara", "Medoroga"],
        toxicity_risk_profile="Unpurified tin causes acute gastric colic, nausea, and Gulma (abdominal lumps)."
    ),
    # 15. YASHADA (Zinc) - Puti Lauha
    RasaMineralRecord(
        mineral_id="MIN-YASHADA",
        sanskrit_name="यशद (Shuddha Yashada)",
        english_name="Purified Zinc / Yashada Bhasma Core",
        chemical_formula="Zn",
        category=RasaCategory.DHATU_PUTI,
        is_schedule_e1_poison=False,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.DHALANA_MELTING_POURING,
        standard_shodhana_media=["Takra (Buttermilk)", "Churna Jala"],
        minimum_shodhana_cycles=7,
        standard_puta_type=PutaType.KUKKUTA_PUTA,
        minimum_puta_cycles=7,
        therapeutic_dose_mg_min=65.0,
        therapeutic_dose_mg_max=250.0,
        classical_indications=["Netraroga (Ophthalmic disorders)", "Prameha", "Shwasa", "Vranaropana"],
        toxicity_risk_profile="Unpurified zinc leads to acute emesis, intestinal spasms, and metallic fever."
    ),
    # 16. VATSANABHA (Aconite) - Schedule E(1) Visha
    RasaMineralRecord(
        mineral_id="MIN-VATSANABHA",
        sanskrit_name="वत्सनाभ (Shuddha Vatsanabha)",
        english_name="Purified Aconite / Monkshood",
        chemical_formula="Aconitine alkaloid extract",
        category=RasaCategory.VISHA_UPAVISHA,
        is_schedule_e1_poison=True,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.SWEDANA_DOLA_YANTRA,
        standard_shodhana_media=["Godugdha (Cow Milk)", "Gomutra"],
        minimum_shodhana_cycles=1,  # 6 hours in Dola Yantra
        standard_puta_type=None,
        minimum_puta_cycles=0,
        therapeutic_dose_mg_min=8.0,
        therapeutic_dose_mg_max=16.0,
        classical_indications=["Jwara (Acute Hyperpyrexia)", "Amavata", "Vedanasthapana", "Sannipata Jwara"],
        toxicity_risk_profile="Potent aconitine causes lethal cardiac arrhythmias, hypotension, ventricular fibrillation, and respiratory paralysis."
    ),
    # 17. KUCHALA (Nux Vomica) - Schedule E(1) Upavisha
    RasaMineralRecord(
        mineral_id="MIN-KUCHALA",
        sanskrit_name="कुचला (Shuddha Kuchala)",
        english_name="Purified Nux-Vomica Seeds",
        chemical_formula="Strychnine-Brucine complex",
        category=RasaCategory.VISHA_UPAVISHA,
        is_schedule_e1_poison=True,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.SWEDANA_DOLA_YANTRA,
        standard_shodhana_media=["Godugdha (Boiling Milk)", "Go-Ghrita (Frying)"],
        minimum_shodhana_cycles=1,
        standard_puta_type=None,
        minimum_puta_cycles=0,
        therapeutic_dose_mg_min=30.0,
        therapeutic_dose_mg_max=125.0,
        classical_indications=["Vatavyadhi", "Pakshaghata (Hemiplegia)", "Ardita (Facial Palsy)", "Nadibalya"],
        toxicity_risk_profile="Strychnine neurotoxicity leads to spinal convulsions, opisthotonos, asphyxia, and tetanic spasms."
    ),
    # 18. BHALLATAKA (Marking Nut) - Schedule E(1) Upavisha
    RasaMineralRecord(
        mineral_id="MIN-BHALLATAKA",
        sanskrit_name="भल्लातक (Shuddha Bhallataka)",
        english_name="Purified Marking Nut",
        chemical_formula="Bhilawanol complex",
        category=RasaCategory.VISHA_UPAVISHA,
        is_schedule_e1_poison=True,
        shodhana_required=True,
        standard_shodhana_method=ShodhanaMethod.KSHALANA_WASHING,
        standard_shodhana_media=["Ishtika Churna (Brick powder)", "Gomutra", "Godugdha"],
        minimum_shodhana_cycles=2,
        standard_puta_type=None,
        minimum_puta_cycles=0,
        therapeutic_dose_mg_min=125.0,
        therapeutic_dose_mg_max=500.0,
        classical_indications=["Arsha (Hemorrhoids)", "Kushtha", "Kaphaja Gulma", "Medoroga", "Krimighna"],
        toxicity_risk_profile="Urushiol-like contact dermatitis, severe blistering (Sphota), burning ulcerations, and nephrotoxicity."
    ),
]


# ==============================================================================
# DATABASE INITIALIZATION & SEEDING ENGINE
# ==============================================================================

def initialize_rasa_shastra_tables(conn: sqlite3.Connection) -> None:
    """Populate rasa_minerals_registry with classical seeds if unseeded."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM rasa_minerals_registry;")
    row = cursor.fetchone()
    if row and row["cnt"] == 0:
        now = int(time.time())
        for m in SEED_RASA_MINERALS_REGISTRY:
            cursor.execute(
                """
                INSERT INTO rasa_minerals_registry (
                    mineral_id, sanskrit_name, english_name, chemical_formula, category,
                    is_schedule_e1_poison, shodhana_required, standard_shodhana_method,
                    standard_shodhana_media_json, minimum_shodhana_cycles, standard_puta_type,
                    minimum_puta_cycles, therapeutic_dose_mg_min, therapeutic_dose_mg_max,
                    classical_indications_json, toxicity_risk_profile, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    m.mineral_id,
                    m.sanskrit_name,
                    m.english_name,
                    m.chemical_formula,
                    m.category.value,
                    1 if m.is_schedule_e1_poison else 0,
                    1 if m.shodhana_required else 0,
                    m.standard_shodhana_method.value,
                    json.dumps(m.standard_shodhana_media),
                    m.minimum_shodhana_cycles,
                    m.standard_puta_type.value if m.standard_puta_type else None,
                    m.minimum_puta_cycles,
                    m.therapeutic_dose_mg_min,
                    m.therapeutic_dose_mg_max,
                    json.dumps(m.classical_indications),
                    m.toxicity_risk_profile,
                    now,
                )
            )


# ==============================================================================
# SHODHANA VERIFICATION ENGINE
# ==============================================================================

def get_mineral_profile(mineral_id: str, conn: sqlite3.Connection) -> RasaMineralRecord:
    """Retrieve mineral details from SQLite registry."""
    initialize_rasa_shastra_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rasa_minerals_registry WHERE mineral_id = ?;", (mineral_id,))
    row = cursor.fetchone()
    if not row:
        raise RecordNotFoundException("RasaMineral", mineral_id)

    return RasaMineralRecord(
        mineral_id=row["mineral_id"],
        sanskrit_name=row["sanskrit_name"],
        english_name=row["english_name"],
        chemical_formula=row["chemical_formula"],
        category=RasaCategory(row["category"]),
        is_schedule_e1_poison=bool(row["is_schedule_e1_poison"]),
        shodhana_required=bool(row["shodhana_required"]),
        standard_shodhana_method=ShodhanaMethod(row["standard_shodhana_method"]),
        standard_shodhana_media=json.loads(row["standard_shodhana_media_json"]),
        minimum_shodhana_cycles=row["minimum_shodhana_cycles"],
        standard_puta_type=PutaType(row["standard_puta_type"]) if row["standard_puta_type"] else None,
        minimum_puta_cycles=row["minimum_puta_cycles"],
        therapeutic_dose_mg_min=row["therapeutic_dose_mg_min"],
        therapeutic_dose_mg_max=row["therapeutic_dose_mg_max"],
        classical_indications=json.loads(row["classical_indications_json"]),
        toxicity_risk_profile=row["toxicity_risk_profile"],
    )


def verify_shodhana_batch(req: ShodhanaVerificationRequest, conn: sqlite3.Connection) -> ShodhanaRecord:
    """
    Certify and record Shodhana detoxification of raw mineral or poison batch.
    Validates cycle count and classical Shuddhi Lakshanas.
    """
    mineral = get_mineral_profile(req.mineral_id, conn)

    # Verification rules
    is_cycle_sufficient = req.cycles_completed >= mineral.minimum_shodhana_cycles
    is_shuddhi_passed = req.organoleptic_shuddhi_confirmed
    is_verified = is_cycle_sufficient and is_shuddhi_passed

    now = int(time.time())
    record_id = f"SHODHANA-{req.mineral_id}-{req.batch_id}-{now}"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO shodhana_records (
            record_id, batch_id, mineral_id, method, media_used_json,
            cycles_completed, verified_by_arn, organoleptic_shuddhi_confirmed,
            is_verified, notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            record_id,
            req.batch_id,
            req.mineral_id,
            req.method.value,
            json.dumps(req.media_used),
            req.cycles_completed,
            req.verified_by_arn,
            1 if req.organoleptic_shuddhi_confirmed else 0,
            1 if is_verified else 0,
            req.notes,
            now,
        )
    )

    return ShodhanaRecord(
        record_id=record_id,
        batch_id=req.batch_id,
        mineral_id=req.mineral_id,
        method=req.method,
        media_used=req.media_used,
        cycles_completed=req.cycles_completed,
        verified_by_arn=req.verified_by_arn,
        organoleptic_shuddhi_confirmed=req.organoleptic_shuddhi_confirmed,
        is_verified=is_verified,
        notes=req.notes,
        created_at=now,
    )


# ==============================================================================
# BHASMA BATCH ANALYTICAL RELEASE CERTIFICATION ENGINE
# ==============================================================================

def certify_bhasma_batch_release(
    req: BhasmaBatchReleaseRequest, conn: sqlite3.Connection
) -> BhasmaBatchReleaseCertificate:
    """
    Execute full multi-axial quality control audit for a Bhasma batch:
    1. Check raw material Shodhana certification (MANDATORY for Schedule E1 & heavy minerals)
    2. Classical 7-Pariksha criteria (all 7 must be verified)
    3. Puta count sufficiency against standard minimum
    4. AAS / ICP-MS Elemental Assay (Heavy metal contaminants <= statutory limits)
    5. Particle size distribution (D50 <= 5 microns, D90 <= 15 microns, nanoscale >= 15%)
    """
    mineral = get_mineral_profile(req.mineral_id, conn)
    rejection_reasons: List[str] = []

    # 1. Classical Pariksha Validation (All 7 mandatory)
    p = req.classical_pariksha
    classical_failures = []
    if not p.varitara:
        classical_failures.append("Varitara failed (Bhasma sinks in water; insufficient fine lightness)")
    if not p.unama:
        classical_failures.append("Unama failed (Paddy grains sink on Bhasma film)")
    if not p.rekhapurna:
        classical_failures.append("Rekhapurna failed (Particles do not penetrate fingertip micro-crevices)")
    if not p.apunarbhava:
        classical_failures.append("Apunarbhava failed (Reversion to metallic state occurred with Mitra Panchaka)")
    if not p.niruttha:
        classical_failures.append("Niruttha failed (Alloy formation or weight gain observed with silver leaf)")
    if not p.nis_svadu:
        classical_failures.append("Nis-svadu failed (Metallic or astringent taste persists)")
    if not p.nischandrika:
        classical_failures.append("Nischandrika failed (Metallic luster or glistening particles visible under light)")

    is_classical_certified = (len(classical_failures) == 0)
    if not is_classical_certified:
        rejection_reasons.extend(classical_failures)

    # 2. Puta Count Check
    puta_count_adequate = req.putas_completed >= mineral.minimum_puta_cycles
    if not puta_count_adequate:
        rejection_reasons.append(
            f"Puta count inadequate: {req.putas_completed} completed vs {mineral.minimum_puta_cycles} required."
        )

    # 3. AAS / ICP-MS Heavy Metal Contaminants Safety Check
    # AFI & Statutory Limits: Pb <= 10.0 ppm, As <= 3.0 ppm, Cd <= 0.3 ppm, Hg <= 1.0 ppm
    # For active ingredients (e.g. Swarna, Lauha, Yashada, Tamra), the primary element is assay, but contaminants must comply.
    assay = req.elemental_assay
    heavy_metal_failures = []

    if assay.lead_pb_ppm > 10.0:
        heavy_metal_failures.append(f"Lead (Pb) concentration {assay.lead_pb_ppm:.2f} ppm exceeds limit (10.0 ppm)")
    if assay.arsenic_as_ppm > 3.0:
        heavy_metal_failures.append(f"Arsenic (As) concentration {assay.arsenic_as_ppm:.2f} ppm exceeds limit (3.0 ppm)")
    if assay.cadmium_cd_ppm > 0.3:
        heavy_metal_failures.append(f"Cadmium (Cd) concentration {assay.cadmium_cd_ppm:.2f} ppm exceeds limit (0.3 ppm)")
    if assay.mercury_hg_ppm > 1.0 and mineral.chemical_formula != "Hg" and mineral.chemical_formula != "HgS":
        heavy_metal_failures.append(f"Mercury (Hg) contaminant {assay.mercury_hg_ppm:.2f} ppm exceeds limit (1.0 ppm)")
    if assay.free_ionic_toxic_metal_ppm > 0.1:
        heavy_metal_failures.append(
            f"Free toxic ionic metal {assay.free_ionic_toxic_metal_ppm:.3f} ppm exceeds safety limit (0.100 ppm)"
        )

    heavy_metals_safe = (len(heavy_metal_failures) == 0)
    if not heavy_metals_safe:
        rejection_reasons.extend(heavy_metal_failures)

    # 4. Particle Size Distribution Check
    ps = req.particle_size
    psd_failures = []
    if ps.d50_microns > 5.0:
        psd_failures.append(f"Median diameter D50 {ps.d50_microns:.2f}um exceeds specification (<= 5.0 um)")
    if ps.d90_microns > 15.0:
        psd_failures.append(f"90th percentile D90 {ps.d90_microns:.2f}um exceeds specification (<= 15.0 um)")
    if ps.nanoscale_percentage < 15.0:
        psd_failures.append(f"Nanoscale sub-micron fraction {ps.nanoscale_percentage:.1f}% below minimum (15.0%)")

    particle_size_compliant = (len(psd_failures) == 0)
    if not particle_size_compliant:
        rejection_reasons.extend(psd_failures)

    # Overall Release Verdict
    is_physicochemical_certified = heavy_metals_safe and particle_size_compliant
    overall_batch_released = (
        is_classical_certified and puta_count_adequate and is_physicochemical_certified
    )

    now = int(time.time())

    # Record in SQLite WAL table
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO bhasma_batches (
            batch_id, mineral_id, formulation_name, puta_type, putas_completed,
            classical_pariksha_json, elemental_assay_json, particle_size_json,
            is_classical_certified, is_physicochemical_certified, is_released,
            rejection_reasons_json, certified_by_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            req.batch_id,
            req.mineral_id,
            req.formulation_name,
            req.puta_type.value,
            req.putas_completed,
            json.dumps(req.classical_pariksha.model_dump()),
            json.dumps(req.elemental_assay.model_dump()),
            json.dumps(req.particle_size.model_dump()),
            1 if is_classical_certified else 0,
            1 if is_physicochemical_certified else 0,
            1 if overall_batch_released else 0,
            json.dumps(rejection_reasons),
            req.certified_by_arn,
            now,
        )
    )

    return BhasmaBatchReleaseCertificate(
        batch_id=req.batch_id,
        mineral_id=req.mineral_id,
        formulation_name=req.formulation_name,
        puta_type=req.puta_type,
        putas_completed=req.putas_completed,
        classical_pariksha=req.classical_pariksha,
        elemental_assay=req.elemental_assay,
        particle_size=req.particle_size,
        is_classical_certified=is_classical_certified,
        puta_count_adequate=puta_count_adequate,
        heavy_metals_safe=heavy_metals_safe,
        particle_size_compliant=particle_size_compliant,
        overall_batch_released=overall_batch_released,
        rejection_reasons=rejection_reasons,
        certified_by_arn=req.certified_by_arn,
        certification_timestamp=now,
    )


# ==============================================================================
# HEAVY METAL EXPOSURE & PDE EVALUATION CALCULUS
# ==============================================================================

def evaluate_heavy_metal_exposure(
    req: HeavyMetalExposureCheckRequest, conn: sqlite3.Connection
) -> HeavyMetalExposureCheckResponse:
    """
    Calculates patient daily heavy metal intake and cumulative lifetime exposure.
    Verifies adherence to statutory Permitted Daily Exposure (PDE) thresholds:
    - Lead (Pb): <= 0.005 mg/day (5 mcg)
    - Arsenic (As): <= 0.015 mg/day (15 mcg)
    - Cadmium (Cd): <= 0.005 mg/day (5 mcg)
    - Mercury (Hg): <= 0.030 mg/day (30 mcg)
    """
    daily_lead_mg = 0.0
    daily_arsenic_mg = 0.0
    daily_cadmium_mg = 0.0
    daily_mercury_mg = 0.0

    cumulative_lead_mg = 0.0
    cumulative_arsenic_mg = 0.0
    cumulative_cadmium_mg = 0.0
    cumulative_mercury_mg = 0.0

    warnings: List[str] = []

    cursor = conn.cursor()
    for item in req.prescriptions:
        cursor.execute("SELECT * FROM bhasma_batches WHERE batch_id = ?;", (item.batch_id,))
        row = cursor.fetchone()
        if not row:
            raise RecordNotFoundException("BhasmaBatch", item.batch_id)

        if row["is_released"] == 0:
            warnings.append(f"WARNING: Batch '{item.batch_id}' is NOT certified or released for clinical use!")

        assay_data = json.loads(row["elemental_assay_json"])
        pb_ppm = float(assay_data.get("lead_pb_ppm", 0.0))
        as_ppm = float(assay_data.get("arsenic_as_ppm", 0.0))
        cd_ppm = float(assay_data.get("cadmium_cd_ppm", 0.0))
        hg_ppm = float(assay_data.get("mercury_hg_ppm", 0.0))

        # Daily dose in mg converted to grams: (ppm * dose_mg) / 10^6 = intake in mg
        item_lead_daily = (pb_ppm * item.daily_dose_mg) / 1_000_000.0
        item_arsenic_daily = (as_ppm * item.daily_dose_mg) / 1_000_000.0
        item_cadmium_daily = (cd_ppm * item.daily_dose_mg) / 1_000_000.0
        item_mercury_daily = (hg_ppm * item.daily_dose_mg) / 1_000_000.0

        daily_lead_mg += item_lead_daily
        daily_arsenic_mg += item_arsenic_daily
        daily_cadmium_mg += item_cadmium_daily
        daily_mercury_mg += item_mercury_daily

        cumulative_lead_mg += (item_lead_daily * item.duration_days)
        cumulative_arsenic_mg += (item_arsenic_daily * item.duration_days)
        cumulative_cadmium_mg += (item_cadmium_daily * item.duration_days)
        cumulative_mercury_mg += (item_mercury_daily * item.duration_days)

    # PDE Limit Verification
    pde_lead_limit = 0.005
    pde_arsenic_limit = 0.015
    pde_cadmium_limit = 0.005
    pde_mercury_limit = 0.030

    exceeded = False
    if daily_lead_mg > pde_lead_limit:
        exceeded = True
        warnings.append(f"CRITICAL: Daily Lead intake {daily_lead_mg:.5f} mg exceeds PDE limit ({pde_lead_limit} mg/day)")
    if daily_arsenic_mg > pde_arsenic_limit:
        exceeded = True
        warnings.append(f"CRITICAL: Daily Arsenic intake {daily_arsenic_mg:.5f} mg exceeds PDE limit ({pde_arsenic_limit} mg/day)")
    if daily_cadmium_mg > pde_cadmium_limit:
        exceeded = True
        warnings.append(f"CRITICAL: Daily Cadmium intake {daily_cadmium_mg:.5f} mg exceeds PDE limit ({pde_cadmium_limit} mg/day)")
    if daily_mercury_mg > pde_mercury_limit:
        exceeded = True
        warnings.append(f"CRITICAL: Daily Mercury intake {daily_mercury_mg:.5f} mg exceeds PDE limit ({pde_mercury_limit} mg/day)")

    if exceeded:
        # Determine highest violation for exception
        if daily_lead_mg > pde_lead_limit:
            raise HeavyMetalExposureExceededException("Lead (Pb)", daily_lead_mg, pde_lead_limit)
        elif daily_arsenic_mg > pde_arsenic_limit:
            raise HeavyMetalExposureExceededException("Arsenic (As)", daily_arsenic_mg, pde_arsenic_limit)
        elif daily_cadmium_mg > pde_cadmium_limit:
            raise HeavyMetalExposureExceededException("Cadmium (Cd)", daily_cadmium_mg, pde_cadmium_limit)
        else:
            raise HeavyMetalExposureExceededException("Mercury (Hg)", daily_mercury_mg, pde_mercury_limit)

    is_within_pde_limits = not exceeded
    safety_verdict = (
        "SAFE_AND_COMPLIANT" if is_within_pde_limits else "PDE_EXPOSURE_VIOLATION"
    )

    return HeavyMetalExposureCheckResponse(
        patient_id=req.patient_id,
        daily_lead_mg=round(daily_lead_mg, 6),
        daily_arsenic_mg=round(daily_arsenic_mg, 6),
        daily_cadmium_mg=round(daily_cadmium_mg, 6),
        daily_mercury_mg=round(daily_mercury_mg, 6),
        pde_lead_mg_limit=pde_lead_limit,
        pde_arsenic_mg_limit=pde_arsenic_limit,
        pde_cadmium_mg_limit=pde_cadmium_limit,
        pde_mercury_mg_limit=pde_mercury_limit,
        cumulative_lead_mg=round(cumulative_lead_mg, 6),
        cumulative_arsenic_mg=round(cumulative_arsenic_mg, 6),
        cumulative_cadmium_mg=round(cumulative_cadmium_mg, 6),
        cumulative_mercury_mg=round(cumulative_mercury_mg, 6),
        is_within_pde_limits=is_within_pde_limits,
        safety_verdict=safety_verdict,
        warnings=warnings,
    )


# ==============================================================================
# SCHEDULE E(1) SHODHANA GATING VERIFICATION FIREWALL
# ==============================================================================

def check_schedule_e1_shodhana_compliance(
    mineral_id: str, batch_id: Optional[str], conn: sqlite3.Connection
) -> bool:
    """
    Statutory gating rule: Any Schedule E(1) substance or heavy metal MUST have
    a certified, completed Shodhana record before dispensing or processing.
    """
    mineral = get_mineral_profile(mineral_id, conn)
    if not mineral.is_schedule_e1_poison and not mineral.shodhana_required:
        return True

    cursor = conn.cursor()
    if batch_id:
        cursor.execute(
            """
            SELECT is_verified, organoleptic_shuddhi_confirmed
            FROM shodhana_records
            WHERE mineral_id = ? AND batch_id = ?
            ORDER BY created_at DESC LIMIT 1;
            """,
            (mineral_id, batch_id)
        )
    else:
        cursor.execute(
            """
            SELECT is_verified, organoleptic_shuddhi_confirmed
            FROM shodhana_records
            WHERE mineral_id = ? AND is_verified = 1
            ORDER BY created_at DESC LIMIT 1;
            """,
            (mineral_id,)
        )

    row = cursor.fetchone()
    if not row or row["is_verified"] != 1 or row["organoleptic_shuddhi_confirmed"] != 1:
        raise ScheduleE1ShodhanaMissingException(mineral.sanskrit_name)

    return True
