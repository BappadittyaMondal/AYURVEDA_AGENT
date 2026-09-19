"""Core domain logic and safety firewall engine for Jalaukavacharana, Siravedha & Raktamokshana.

Classical references:
- Sushruta Samhita Sutrasthana Ch. 13 (Jalaukavacharaniya Adhyaya)
- Sushruta Samhita Sutrasthana Ch. 14 (Shonita Varniya Adhyaya)
- Sushruta Samhita Sharirasthana Ch. 8 (Siravyadha Viddhi Adhyaya)
"""
import json
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional

from core.database import get_sqlite_connection
from models.raktamokshana import (
    AvadhyaComplicationRisk,
    BloodDoshaVitiation,
    BodyQuadrant,
    HemostasisMethod,
    JalaukaSpecies,
    JalaukaType,
    RaktamokshanaModality,
    RaktamokshanaProcedureLogCreate,
    RaktamokshanaProcedureLogResponse,
    RogiBala,
    SafetyEvaluationRequest,
    SafetyEvaluationResponse,
    ShastraUsed,
    SiravedhaVein,
)

# -------------------------------------------------------------------------
# Classical Taxonomy Catalogs
# -------------------------------------------------------------------------

CLASSICAL_JALAUKA_CATALOG: List[Dict[str, Any]] = [
    # 6 Nirvisha (Therapeutic / Medicinal)
    {
        "species_id": "JAL-NIR-KAPILA",
        "sanskrit_name": "Kapila",
        "species_type": JalaukaType.NIRVISHA.value,
        "morphological_markers": [
            "Tawny/realgar (manashila) colored sides",
            "Greenish-yellow dorsal line",
            "Smooth and glistening skin",
            "Firm muscular cylindrical body"
        ],
        "salivary_enzymes_profile": {
            "hirudin_atu_per_ml": 45.0,
            "calin_activity_score": 88.0,
            "bdellin_eglin_level": "HIGH",
            "hyaluronidase_potency": "OPTIMAL",
            "destabilase_fibrinolytic": True,
            "apyrase_present": True
        },
        "habitat_water_type": "Padmavana (clear lotus ponds with fragrant clean fresh water)",
        "clinical_suitability": "Ideal for unctuous constitutions, Pitta-Rakta disorders, chronic non-healing ulcers."
    },
    {
        "species_id": "JAL-NIR-PINGALA",
        "sanskrit_name": "Pingala",
        "species_type": JalaukaType.NIRVISHA.value,
        "morphological_markers": [
            "Slightly reddish or tawny body",
            "Cylindrical rounded form",
            "Rapid serpentine motility",
            "Soft velvety ventral surface"
        ],
        "salivary_enzymes_profile": {
            "hirudin_atu_per_ml": 42.0,
            "calin_activity_score": 85.0,
            "bdellin_eglin_level": "MODERATE_HIGH",
            "hyaluronidase_potency": "HIGH",
            "destabilase_fibrinolytic": True,
            "apyrase_present": True
        },
        "habitat_water_type": "Clean flowing spring water rich in aquatic lily vegetation",
        "clinical_suitability": "Preferred for swift extraction in acute local inflammation and cellulitis."
    },
    {
        "species_id": "JAL-NIR-SHANKHAMUKHI",
        "sanskrit_name": "Shankhamukhi",
        "species_type": JalaukaType.NIRVISHA.value,
        "morphological_markers": [
            "Liver-colored or dark brownish-red",
            "Elongated narrow oral snout resembling a conch shell (shankha)",
            "Swift painless attachment",
            "Rapid high-volume suction"
        ],
        "salivary_enzymes_profile": {
            "hirudin_atu_per_ml": 55.0,
            "calin_activity_score": 92.0,
            "bdellin_eglin_level": "VERY_HIGH",
            "hyaluronidase_potency": "SUPERIOR",
            "destabilase_fibrinolytic": True,
            "apyrase_present": True
        },
        "habitat_water_type": "Pristine mountain streams with sandy limestone beds",
        "clinical_suitability": "Supreme medicinal leech for deep venous congestion, varicosities, and micro-reimplantation."
    },
    {
        "species_id": "JAL-NIR-MUSHIKA",
        "sanskrit_name": "Mushika",
        "species_type": JalaukaType.NIRVISHA.value,
        "morphological_markers": [
            "Color and shape resembling common field mouse (ash grey)",
            "Faint earthy odor",
            "Slender elongated tail disc",
            "Steady rhythmic contraction during feeding"
        ],
        "salivary_enzymes_profile": {
            "hirudin_atu_per_ml": 38.0,
            "calin_activity_score": 78.0,
            "bdellin_eglin_level": "MODERATE",
            "hyaluronidase_potency": "MODERATE",
            "destabilase_fibrinolytic": True,
            "apyrase_present": True
        },
        "habitat_water_type": "Shaded freshwater wetlands with floating aquatic grasses",
        "clinical_suitability": "General dermatological bloodletting, eczema, and localized hyperpigmentation."
    },
    {
        "species_id": "JAL-NIR-PUNDARIKAMUKHI",
        "sanskrit_name": "Pundarikamukhi",
        "species_type": JalaukaType.NIRVISHA.value,
        "morphological_markers": [
            "Color of mud or white lotus petal underside",
            "Oral disc wide and flared like an open lotus blossom",
            "Highly adherent muscular sucker",
            "Sustained gentle extraction"
        ],
        "salivary_enzymes_profile": {
            "hirudin_atu_per_ml": 48.0,
            "calin_activity_score": 90.0,
            "bdellin_eglin_level": "HIGH",
            "hyaluronidase_potency": "HIGH",
            "destabilase_fibrinolytic": True,
            "apyrase_present": True
        },
        "habitat_water_type": "Clean perennial lotus lakes rich in Nelumbo nucifera",
        "clinical_suitability": "Sensitive anatomical regions, facial lesions, alopecia areata, and delicate pediatric/geriatric skin."
    },
    {
        "species_id": "JAL-NIR-SAVARIKA",
        "sanskrit_name": "Savarika",
        "species_type": JalaukaType.NIRVISHA.value,
        "morphological_markers": [
            "Grass-green or lotus leaf hue",
            "Length up to 18 Angulas (large specimen)",
            "Prominent lateral longitudinal stripes",
            "Heavy suction volume capacity"
        ],
        "salivary_enzymes_profile": {
            "hirudin_atu_per_ml": 50.0,
            "calin_activity_score": 86.0,
            "bdellin_eglin_level": "HIGH",
            "hyaluronidase_potency": "HIGH",
            "destabilase_fibrinolytic": True,
            "apyrase_present": True
        },
        "habitat_water_type": "Extensive natural lake systems with abundant water weeds",
        "clinical_suitability": "Dense muscular sites, gluteal or thigh indurations, thick fibrotic lesions."
    },

    # 6 Savisha (Toxic / Strictly Contraindicated)
    {
        "species_id": "JAL-SAV-KRISHNA",
        "sanskrit_name": "Krishna",
        "species_type": JalaukaType.SAVISHA.value,
        "morphological_markers": [
            "Pitch black like powdered antimony (anjana)",
            "Disproportionately large bulbous head",
            "Rough dry wrinkled skin texture",
            "Sluggish uncoordinated wriggling"
        ],
        "salivary_enzymes_profile": {
            "toxic_neurotoxin": True,
            "histamine_surge_inducing": True,
            "necrotizing_toxins": "HIGH",
            "therapeutic_value": "NONE"
        },
        "habitat_water_type": "Foul stagnant ditches containing decomposing animal carcasses",
        "clinical_suitability": "STRICTLY CONTRAINDICATED. Causes acute emesis, syncope, systemic intoxication."
    },
    {
        "species_id": "JAL-SAV-KARBUDA",
        "sanskrit_name": "Karbuda",
        "species_type": JalaukaType.SAVISHA.value,
        "morphological_markers": [
            "Elongated and segmented like an eel/dace fish (varmi)",
            "Markedly raised, bulging abdomen",
            "Irregular mottled pigmentation",
            "Foul sulfurous odor"
        ],
        "salivary_enzymes_profile": {
            "toxic_neurotoxin": True,
            "histamine_surge_inducing": True,
            "necrotizing_toxins": "HIGH",
            "therapeutic_value": "NONE"
        },
        "habitat_water_type": "Muddy putrid swamps with rotting organic refuse",
        "clinical_suitability": "STRICTLY CONTRAINDICATED. Causes local tissue necrosis and severe febrile toxemia."
    },
    {
        "species_id": "JAL-SAV-ALAGARDA",
        "sanskrit_name": "Alagarda",
        "species_type": JalaukaType.SAVISHA.value,
        "morphological_markers": [
            "Covered with coarse fine hairs or bristle-like hairs",
            "Thick lateral flanks",
            "Jet-black oral orifice",
            "Extremely aggressive biting behavior"
        ],
        "salivary_enzymes_profile": {
            "toxic_neurotoxin": True,
            "histamine_surge_inducing": True,
            "necrotizing_toxins": "VERY_HIGH",
            "therapeutic_value": "NONE"
        },
        "habitat_water_type": "Contaminated urban runoff ponds and polluted effluents",
        "clinical_suitability": "STRICTLY CONTRAINDICATED. Triggers rapid brawny edema, excruciating pain, and high fever."
    },
    {
        "species_id": "JAL-SAV-SAAMUDRIKA",
        "sanskrit_name": "Saamudrika",
        "species_type": JalaukaType.SAVISHA.value,
        "morphological_markers": [
            "Yellowish-black body with circular variegated floral spots",
            "Slime-encrusted dorsal ridge",
            "Flattened disc-like posterior"
        ],
        "salivary_enzymes_profile": {
            "toxic_neurotoxin": True,
            "histamine_surge_inducing": True,
            "necrotizing_toxins": "HIGH",
            "therapeutic_value": "NONE"
        },
        "habitat_water_type": "Brackish estuarine marshes with toxic algal blooms",
        "clinical_suitability": "STRICTLY CONTRAINDICATED. Causes intractable burning sensation, severe pruritus, and bullous eruptions."
    },
    {
        "species_id": "JAL-SAV-INDRAYUDHA",
        "sanskrit_name": "Indrayudha",
        "species_type": JalaukaType.SAVISHA.value,
        "morphological_markers": [
            "Longitudinal dorsal stripes resembling an iridescent rainbow",
            "Vivid multi-colored bands",
            "Sharp needle-like oral papillae"
        ],
        "salivary_enzymes_profile": {
            "toxic_neurotoxin": True,
            "histamine_surge_inducing": True,
            "necrotizing_toxins": "LETHAL",
            "therapeutic_value": "NONE"
        },
        "habitat_water_type": "Decaying forest pools overgrown with poisonous toadstools and flora",
        "clinical_suitability": "STRICTLY CONTRAINDICATED. Lethal neurotoxic shock, convulsions, coma, and rapid cardiovascular collapse."
    },
    {
        "species_id": "JAL-SAV-GOCHANDANA",
        "sanskrit_name": "Gochandana",
        "species_type": JalaukaType.SAVISHA.value,
        "morphological_markers": [
            "Bifurcated posterior caudal sucker resembling bull's scrotum",
            "Very narrow anterior snout",
            "Yellow-green mottled body"
        ],
        "salivary_enzymes_profile": {
            "toxic_neurotoxin": True,
            "histamine_surge_inducing": True,
            "necrotizing_toxins": "HIGH",
            "therapeutic_value": "NONE"
        },
        "habitat_water_type": "Stagnant marshy pastures polluted by bovine excrement",
        "clinical_suitability": "STRICTLY CONTRAINDICATED. Produces progressive necrotizing fasciitis, gangrene, and sepsis."
    }
]

# -------------------------------------------------------------------------
# Classical Siravedha Matrix (Vidhya & Avadhya Siras - Sushruta Sharirasthana Ch. 8)
# Total 700 Siras in human body; exactly 98 are strictly Avadhya.
# -------------------------------------------------------------------------

CLASSICAL_SIRAVEDHA_CATALOG: List[Dict[str, Any]] = [
    # Indicated (Vidhya) Siras for specific clinical conditions
    {
        "vein_code": "V-GRIDHRASI-01",
        "sanskrit_name": "Janu-Gulpha Sandhistha Sira",
        "anatomical_location": "Great saphenous / posterior tibial tributary 4 Angulas above/below knee or ankle joint",
        "body_quadrant": BodyQuadrant.SHAKHA_ADHA.value,
        "is_avadhya": 0,
        "avadhya_complication_risk": AvadhyaComplicationRisk.NONE.value,
        "indicated_diseases": ["Gridhrasi (Sciatica)", "Kandara-vata", "Khalli", "Pada-harsha"],
        "puncture_depth_angula": 0.5,
        "instrument_shastra": ShastraUsed.VRIHIMUKHA.value
    },
    {
        "vein_code": "V-VATARAKTA-01",
        "sanskrit_name": "Kshipra-Marma-Upari Sira",
        "anatomical_location": "Dorsal venous arch 2 Angulas proximal to Kshipra Marma (web space between 1st & 2nd metatarsal)",
        "body_quadrant": BodyQuadrant.SHAKHA_ADHA.value,
        "is_avadhya": 0,
        "avadhya_complication_risk": AvadhyaComplicationRisk.NONE.value,
        "indicated_diseases": ["Vatarakta (Gouty arthritis)", "Vapadika", "Kushta", "Pada-daha"],
        "puncture_depth_angula": 0.25,
        "instrument_shastra": ShastraUsed.VRIHIMUKHA.value
    },
    {
        "vein_code": "V-SHIROROGA-01",
        "sanskrit_name": "Lalatastha Sira",
        "anatomical_location": "Supratrochlear / frontal tributary at midline forehead and anterior hairline border",
        "body_quadrant": BodyQuadrant.SHIRAH.value,
        "is_avadhya": 0,
        "avadhya_complication_risk": AvadhyaComplicationRisk.NONE.value,
        "indicated_diseases": ["Suryavarta", "Ardhavabhedaka (Migraine)", "Shirah-shula", "Ananta-vata"],
        "puncture_depth_angula": 0.125,
        "instrument_shastra": ShastraUsed.KUTHARIKA.value
    },
    {
        "vein_code": "V-VISARPA-SKIN-01",
        "sanskrit_name": "Shakha Parshvastha Sira",
        "anatomical_location": "Superficial cephalic/basilic collateral immediately adjacent to erythematous/indurated lesion",
        "body_quadrant": BodyQuadrant.SHAKHA_URDHVA.value,
        "is_avadhya": 0,
        "avadhya_complication_risk": AvadhyaComplicationRisk.NONE.value,
        "indicated_diseases": ["Visarpa (Erysipelas)", "Vidradhi (Abscess)", "Kushta", "Shleepada early stage"],
        "puncture_depth_angula": 0.25,
        "instrument_shastra": ShastraUsed.VRIHIMUKHA.value
    },
    {
        "vein_code": "V-PLEEHA-01",
        "sanskrit_name": "Vama Koorpara-sandhistha Sira",
        "anatomical_location": "Median cubital vein of the left antecubital fossa",
        "body_quadrant": BodyQuadrant.SHAKHA_URDHVA.value,
        "is_avadhya": 0,
        "avadhya_complication_risk": AvadhyaComplicationRisk.NONE.value,
        "indicated_diseases": ["Pleehodara (Splenomegaly)", "Gulma (Left hypochondriac)", "Jvara"],
        "puncture_depth_angula": 0.5,
        "instrument_shastra": ShastraUsed.VRIHIMUKHA.value
    },
    {
        "vein_code": "V-YAKRIT-01",
        "sanskrit_name": "Dakshina Koorpara-sandhistha Sira",
        "anatomical_location": "Median cubital vein of the right antecubital fossa",
        "body_quadrant": BodyQuadrant.SHAKHA_URDHVA.value,
        "is_avadhya": 0,
        "avadhya_complication_risk": AvadhyaComplicationRisk.NONE.value,
        "indicated_diseases": ["Yakrid-dalodara (Hepatomegaly)", "Kamala (Jaundice)", "Halimaka"],
        "puncture_depth_angula": 0.5,
        "instrument_shastra": ShastraUsed.VRIHIMUKHA.value
    },
    {
        "vein_code": "V-UNMADA-01",
        "sanskrit_name": "Apanga-Sandhistha Sira",
        "anatomical_location": "Superficial temporal tributary near outer orbital rim (excluding Avadhya)",
        "body_quadrant": BodyQuadrant.SHIRAH.value,
        "is_avadhya": 0,
        "avadhya_complication_risk": AvadhyaComplicationRisk.NONE.value,
        "indicated_diseases": ["Unmada (Psychosis)", "Apasmara (Epilepsy)", "Moha"],
        "puncture_depth_angula": 0.125,
        "instrument_shastra": ShastraUsed.KUTHARIKA.value
    },

    # 10 Classical Avadhya Siras (Prohibited veins representing the 98 Avadhya Siras)
    {
        "vein_code": "AV-GREEVA-MATRIKA-01",
        "sanskrit_name": "Greeva Matrika Sira (Ashta Matrika)",
        "anatomical_location": "Bilateral internal jugular vein and carotid sheath deep vascular trunks (8 veins)",
        "body_quadrant": BodyQuadrant.URO_GREEVA.value,
        "is_avadhya": 1,
        "avadhya_complication_risk": AvadhyaComplicationRisk.FATAL_HEMORRHAGE.value,
        "indicated_diseases": [],
        "puncture_depth_angula": 0.0,
        "instrument_shastra": ShastraUsed.NONE.value
    },
    {
        "vein_code": "AV-GREEVA-MANYA-01",
        "sanskrit_name": "Manya Sira (Ashta Manya)",
        "anatomical_location": "Deep cervical parasagittal veins supplying pharyngeal and prevertebral structures (8 veins)",
        "body_quadrant": BodyQuadrant.URO_GREEVA.value,
        "is_avadhya": 1,
        "avadhya_complication_risk": AvadhyaComplicationRisk.DEATH_ASPHYXIA.value,
        "indicated_diseases": [],
        "puncture_depth_angula": 0.0,
        "instrument_shastra": ShastraUsed.NONE.value
    },
    {
        "vein_code": "AV-SHIRAH-STHAPANI-01",
        "sanskrit_name": "Sthapani-Marma Sira",
        "anatomical_location": "Direct emissary venous channel traversing glabella at the Sthapani Marma midpoint",
        "body_quadrant": BodyQuadrant.SHIRAH.value,
        "is_avadhya": 1,
        "avadhya_complication_risk": AvadhyaComplicationRisk.FATAL_HEMORRHAGE.value,
        "indicated_diseases": [],
        "puncture_depth_angula": 0.0,
        "instrument_shastra": ShastraUsed.NONE.value
    },
    {
        "vein_code": "AV-SHIRAH-SIMANTA-01",
        "sanskrit_name": "Simanta Sira",
        "anatomical_location": "Venous anastomoses along the 5 coronal and sagittal cranial sutures (5 veins)",
        "body_quadrant": BodyQuadrant.SHIRAH.value,
        "is_avadhya": 1,
        "avadhya_complication_risk": AvadhyaComplicationRisk.FATAL_HEMORRHAGE.value,
        "indicated_diseases": [],
        "puncture_depth_angula": 0.0,
        "instrument_shastra": ShastraUsed.NONE.value
    },
    {
        "vein_code": "AV-SHIRAH-NETRA-01",
        "sanskrit_name": "Netra-Gata Avadhya Sira (Dve)",
        "anatomical_location": "Superior ophthalmic vein and lacrimal caruncle deep communicating vessels (2 veins)",
        "body_quadrant": BodyQuadrant.SHIRAH.value,
        "is_avadhya": 1,
        "avadhya_complication_risk": AvadhyaComplicationRisk.BLINDNESS.value,
        "indicated_diseases": [],
        "puncture_depth_angula": 0.0,
        "instrument_shastra": ShastraUsed.NONE.value
    },
    {
        "vein_code": "AV-SHAKHA-URVI-01",
        "sanskrit_name": "Urvi Sira (Femoral Trunks)",
        "anatomical_location": "Deep femoral venous trunk traversing midpoint of thigh directly over Urvi Marma",
        "body_quadrant": BodyQuadrant.SHAKHA_ADHA.value,
        "is_avadhya": 1,
        "avadhya_complication_risk": AvadhyaComplicationRisk.FATAL_HEMORRHAGE.value,
        "indicated_diseases": [],
        "puncture_depth_angula": 0.0,
        "instrument_shastra": ShastraUsed.NONE.value
    },
    {
        "vein_code": "AV-SHAKHA-JALADHARA-01",
        "sanskrit_name": "Jaladhara Sira",
        "anatomical_location": "Deep inter-digital palmar and plantar venous arches (4 veins in 4 limbs)",
        "body_quadrant": BodyQuadrant.SHAKHA_ADHA.value,
        "is_avadhya": 1,
        "avadhya_complication_risk": AvadhyaComplicationRisk.PARALYSIS.value,
        "indicated_diseases": [],
        "puncture_depth_angula": 0.0,
        "instrument_shastra": ShastraUsed.NONE.value
    },
    {
        "vein_code": "AV-KOSTHA-HRIDAYA-01",
        "sanskrit_name": "Hridaya-Ashrita Urah Sira",
        "anatomical_location": "Internal thoracic / mediastinal pericardiophrenic venous channels (8 veins in chest)",
        "body_quadrant": BodyQuadrant.KOSTHA.value,
        "is_avadhya": 1,
        "avadhya_complication_risk": AvadhyaComplicationRisk.ORGAN_FAILURE.value,
        "indicated_diseases": [],
        "puncture_depth_angula": 0.0,
        "instrument_shastra": ShastraUsed.NONE.value
    },
    {
        "vein_code": "AV-KOSTHA-BASTI-01",
        "sanskrit_name": "Basti-Ashrita Shroni Sira",
        "anatomical_location": "Deep perivesical and prostatic/uterine venous plexus in pelvic bowl (8 veins)",
        "body_quadrant": BodyQuadrant.KOSTHA.value,
        "is_avadhya": 1,
        "avadhya_complication_risk": AvadhyaComplicationRisk.ORGAN_FAILURE.value,
        "indicated_diseases": [],
        "puncture_depth_angula": 0.0,
        "instrument_shastra": ShastraUsed.NONE.value
    },
    {
        "vein_code": "AV-KOSTHA-NABHI-01",
        "sanskrit_name": "Nabhi-Ashrita Udara Sira",
        "anatomical_location": "Paraumbilical portal-systemic venous shunts immediately surrounding Nabhi Marma (4 veins)",
        "body_quadrant": BodyQuadrant.KOSTHA.value,
        "is_avadhya": 1,
        "avadhya_complication_risk": AvadhyaComplicationRisk.FATAL_HEMORRHAGE.value,
        "indicated_diseases": [],
        "puncture_depth_angula": 0.0,
        "instrument_shastra": ShastraUsed.NONE.value
    }
]


# -------------------------------------------------------------------------
# Seeding and Catalog Management
# -------------------------------------------------------------------------

def seed_raktamokshana_catalogs(conn: sqlite3.Connection) -> None:
    """Ensure classical leeches and Siravedha veins are seeded in the database."""
    now = int(time.time())
    cursor = conn.cursor()

    # Seed Jalauka Species
    for j in CLASSICAL_JALAUKA_CATALOG:
        cursor.execute("SELECT COUNT(*) as cnt FROM jalauka_species_registry WHERE species_id = ?;", (j["species_id"],))
        if cursor.fetchone()["cnt"] == 0:
            cursor.execute(
                """
                INSERT INTO jalauka_species_registry (
                    species_id, sanskrit_name, species_type, morphological_markers_json,
                    salivary_enzymes_profile_json, habitat_water_type, clinical_suitability, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    j["species_id"],
                    j["sanskrit_name"],
                    j["species_type"],
                    json.dumps(j["morphological_markers"]),
                    json.dumps(j["salivary_enzymes_profile"]),
                    j["habitat_water_type"],
                    j["clinical_suitability"],
                    now
                )
            )

    # Seed Siravedha Vein Selection Matrix
    for v in CLASSICAL_SIRAVEDHA_CATALOG:
        cursor.execute("SELECT COUNT(*) as cnt FROM siravedha_vein_selection_matrix WHERE vein_code = ?;", (v["vein_code"],))
        if cursor.fetchone()["cnt"] == 0:
            cursor.execute(
                """
                INSERT INTO siravedha_vein_selection_matrix (
                    vein_code, sanskrit_name, anatomical_location, body_quadrant,
                    is_avadhya, avadhya_complication_risk, indicated_diseases_json,
                    puncture_depth_angula, instrument_shastra, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    v["vein_code"],
                    v["sanskrit_name"],
                    v["anatomical_location"],
                    v["body_quadrant"],
                    v["is_avadhya"],
                    v["avadhya_complication_risk"],
                    json.dumps(v["indicated_diseases"]),
                    v["puncture_depth_angula"],
                    v["instrument_shastra"],
                    now
                )
            )

    conn.commit()


# -------------------------------------------------------------------------
# Mathematical Permissible Volume Calculator
# -------------------------------------------------------------------------

def calculate_max_permissible_blood_volume(
    rogi_bala: RogiBala,
    weight_kg: float,
    current_season: str = "SHARAD"
) -> float:
    """Calculate maximum permissible bloodletting volume in mL based on Sushruta Sutrasthana Ch. 14.

    Classical benchmark:
    - 1 Prastha = 640 mL maximum theoretical for Uttama Bala in adult.
    - Madhyama Bala: 0.5 Prastha (320 mL).
    - Avara Bala: 0.25 Prastha (160 mL).
    - Season modification: Sharad = 1.0; Varsha/Grishma = 0.70; Hemanta/Shishira = 0.85; Vasanta = 0.90.
    - Weight scaling factor: Normal adult reference = 70 kg.
    """
    season_factor = {
        "SHARAD": 1.0,
        "VASANTA": 0.90,
        "HEMANTA": 0.85,
        "SHISHIRA": 0.85,
        "VARSHA": 0.70,
        "GRISHMA": 0.70
    }.get(current_season.upper(), 0.85)

    bala_caps = {
        RogiBala.UTTAMA: 640.0,
        RogiBala.MADHYAMA: 320.0,
        RogiBala.AVARA: 160.0
    }

    bala_per_kg = {
        RogiBala.UTTAMA: 8.0,
        RogiBala.MADHYAMA: 4.5,
        RogiBala.AVARA: 2.2
    }

    weight_based_limit = weight_kg * bala_per_kg[rogi_bala]
    cap = bala_caps[rogi_bala]

    max_volume = min(weight_based_limit, cap) * season_factor
    return round(max_volume, 1)


def estimate_post_op_hemoglobin(pre_op_hb: float, blood_loss_ml: float) -> float:
    """Estimate post-procedure hemoglobin drop (~1.0 g/dL drop per 500 mL blood loss)."""
    drop = (blood_loss_ml / 500.0) * 1.0
    post_hb = max(0.0, round(pre_op_hb - drop, 2))
    return post_hb


# -------------------------------------------------------------------------
# Safety Firewall Verification
# -------------------------------------------------------------------------

def evaluate_raktamokshana_safety(
    req: SafetyEvaluationRequest,
    conn: Optional[sqlite3.Connection] = None
) -> SafetyEvaluationResponse:
    """Evaluate multi-tiered clinical and classical safety firewalls for Raktamokshana."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        max_vol = calculate_max_permissible_blood_volume(
            rogi_bala=req.rogi_bala,
            weight_kg=req.patient_weight_kg,
            current_season=req.current_season
        )

        estimated_post_hb = estimate_post_op_hemoglobin(
            pre_op_hb=req.baseline_hemoglobin_g_dl,
            blood_loss_ml=req.proposed_volume_ml
        )

        # Standard post-procedure nutritional replenishment prescription
        replenishment = [
            "Drakshadya Ghrita (5-10 mL) with warm cow's milk",
            "Dadimadya Ghrita / Fresh pomegranate juice (100 mL)",
            "Aja Mamsa Rasa (Goat bone marrow broth) for Dhatu regeneration",
            "Lohasava (15 mL twice daily post meals for Rakta-dhatu replenishment)",
            "Avoidance of heavy unctuous exercise (Vyayama) and direct sun exposure (Atapa)"
        ]

        # 1. Severe Anemia Firewall (Hb < 8.0 g/dL)
        if req.baseline_hemoglobin_g_dl < 8.0:
            return SafetyEvaluationResponse(
                cleared=False,
                firewall_status="CODE_RED_SEVERE_ANEMIA_CONTRAINDICATION",
                reason=(
                    f"Baseline Hemoglobin is critically low ({req.baseline_hemoglobin_g_dl} g/dL < 8.0 g/dL). "
                    "All Raktamokshana modalities are strictly contraindicated to prevent catastrophic tissue hypoxia and syncope."
                ),
                max_permissible_volume_ml=0.0,
                recommended_modality=RaktamokshanaModality.JALAUKAVACHARANA,
                suggested_hemostasis=HemostasisMethod.SANDHANA,
                post_procedure_nutritional_replenishment=replenishment,
                estimated_post_op_hb_g_dl=req.baseline_hemoglobin_g_dl
            )

        # 2. Moderate Anemia Siravedha Restriction (Hb < 10.0 g/dL)
        if req.baseline_hemoglobin_g_dl < 10.0 and req.modality == RaktamokshanaModality.SIRAVEDHA:
            return SafetyEvaluationResponse(
                cleared=False,
                firewall_status="CODE_ORANGE_MODERATE_ANEMIA_SIRAVEDHA_RESTRICTION",
                reason=(
                    f"Baseline Hemoglobin ({req.baseline_hemoglobin_g_dl} g/dL) is below 10.0 g/dL threshold. "
                    "Venesection (Siravedha) is contraindicated. Jalaukavacharana (max 1-2 leeches, <= 30 mL) is the only permissible alternative."
                ),
                max_permissible_volume_ml=30.0,
                recommended_modality=RaktamokshanaModality.JALAUKAVACHARANA,
                suggested_hemostasis=HemostasisMethod.SANDHANA,
                post_procedure_nutritional_replenishment=replenishment,
                estimated_post_op_hb_g_dl=estimate_post_op_hemoglobin(req.baseline_hemoglobin_g_dl, 30.0)
            )

        # 3. Coagulopathy / Bleeding Diathesis Firewall
        if (
            req.has_active_bleeding_diathesis
            or req.inr > 1.5
            or req.platelet_count < 50000
        ):
            return SafetyEvaluationResponse(
                cleared=False,
                firewall_status="CODE_RED_COAGULOPATHY_FIREWALL",
                reason=(
                    "Severe coagulopathy / active bleeding diathesis detected "
                    f"(INR: {req.inr}, Platelets: {req.platelet_count}/uL). "
                    "Raktamokshana will lead to uncontrollable exsanguination and hemodynamic collapse."
                ),
                max_permissible_volume_ml=0.0,
                recommended_modality=RaktamokshanaModality.JALAUKAVACHARANA,
                suggested_hemostasis=HemostasisMethod.DAHANA,
                post_procedure_nutritional_replenishment=replenishment,
                estimated_post_op_hb_g_dl=req.baseline_hemoglobin_g_dl
            )

        # 4. Hemodynamic Shock / Severe Hypotension Firewall
        map_bp = (req.systolic_bp + 2 * req.diastolic_bp) / 3.0
        if req.systolic_bp < 90 or map_bp < 65.0:
            return SafetyEvaluationResponse(
                cleared=False,
                firewall_status="CODE_RED_HYPOTENSION_SHOCK",
                reason=(
                    f"Hemodynamic instability (BP: {req.systolic_bp}/{req.diastolic_bp} mmHg, MAP: {round(map_bp, 1)} mmHg). "
                    "Bloodletting will precipitate profound hypovolemic shock and cardiac arrest."
                ),
                max_permissible_volume_ml=0.0,
                recommended_modality=RaktamokshanaModality.JALAUKAVACHARANA,
                suggested_hemostasis=HemostasisMethod.SANDHANA,
                post_procedure_nutritional_replenishment=replenishment,
                estimated_post_op_hb_g_dl=req.baseline_hemoglobin_g_dl
            )

        # 5. Savisha Leech Species Firewall
        if req.species_id:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT sanskrit_name, species_type FROM jalauka_species_registry WHERE species_id = ?;",
                (req.species_id,)
            )
            row = cursor.fetchone()
            if row and row["species_type"] == JalaukaType.SAVISHA.value:
                return SafetyEvaluationResponse(
                    cleared=False,
                    firewall_status="SAVISHA_SPECIES_TOXIC_HAZARD",
                    reason=(
                        f"Species '{row['sanskrit_name']}' is classified as SAVISHA (poisonous). "
                        "Application causes necrotizing cellulitis, intractable burning, convulsions, and toxic shock. Strictly prohibited."
                    ),
                    max_permissible_volume_ml=0.0,
                    recommended_modality=RaktamokshanaModality.JALAUKAVACHARANA,
                    suggested_hemostasis=HemostasisMethod.SANDHANA,
                    post_procedure_nutritional_replenishment=replenishment,
                    estimated_post_op_hb_g_dl=req.baseline_hemoglobin_g_dl
                )

        # 6. Avadhya Sira (Contraindicated Vein) Firewall for Siravedha
        if req.modality == RaktamokshanaModality.SIRAVEDHA and req.vein_code:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT sanskrit_name, is_avadhya, avadhya_complication_risk FROM siravedha_vein_selection_matrix WHERE vein_code = ?;",
                (req.vein_code,)
            )
            row = cursor.fetchone()
            if row and row["is_avadhya"] == 1:
                return SafetyEvaluationResponse(
                    cleared=False,
                    firewall_status="AVADHYA_SIRA_VIOLATION_FATAL_RISK",
                    reason=(
                        f"Vein '{row['sanskrit_name']}' is one of Sushruta's 98 strictly AVADHYA SIRAS (prohibited veins). "
                        f"Puncture carries catastrophic risk of: {row['avadhya_complication_risk']}."
                    ),
                    max_permissible_volume_ml=0.0,
                    recommended_modality=RaktamokshanaModality.JALAUKAVACHARANA,
                    suggested_hemostasis=HemostasisMethod.DAHANA,
                    post_procedure_nutritional_replenishment=replenishment,
                    estimated_post_op_hb_g_dl=req.baseline_hemoglobin_g_dl
                )

        # 7. Pregnancy Contraindication for Major Evacuation
        if req.is_pregnant and req.modality in (RaktamokshanaModality.SIRAVEDHA, RaktamokshanaModality.PRACHHANA):
            return SafetyEvaluationResponse(
                cleared=False,
                firewall_status="PREGNANCY_INVASIVE_RAKTAMOKSHANA_CONTRAINDICATED",
                reason=(
                    "Invasive bloodletting (Siravedha/Prachhana) is contraindicated during pregnancy due to fetal distress, "
                    "placental perfusion drop, and premature uterine contraction risk."
                ),
                max_permissible_volume_ml=0.0,
                recommended_modality=RaktamokshanaModality.JALAUKAVACHARANA,
                suggested_hemostasis=HemostasisMethod.SANDHANA,
                post_procedure_nutritional_replenishment=replenishment,
                estimated_post_op_hb_g_dl=req.baseline_hemoglobin_g_dl
            )

        # 8. Volume Overdraw Firewall
        if req.proposed_volume_ml > max_vol:
            return SafetyEvaluationResponse(
                cleared=False,
                firewall_status="EXCESSIVE_BLOOD_VOLUME_RISK",
                reason=(
                    f"Proposed blood volume ({req.proposed_volume_ml} mL) exceeds maximum permissible safe limit "
                    f"({max_vol} mL) for {req.rogi_bala.value} Bala in {req.current_season} season. "
                    "Risk of Ati-visravana complications: dizziness (bhrama), syncope (murchha), and tremors (kampa)."
                ),
                max_permissible_volume_ml=max_vol,
                recommended_modality=req.modality,
                suggested_hemostasis=HemostasisMethod.SANDHANA,
                post_procedure_nutritional_replenishment=replenishment,
                estimated_post_op_hb_g_dl=estimated_post_hb
            )

        # All Safety Firewalls Cleared
        suggested_hemostasis = HemostasisMethod.SANDHANA
        if req.modality == RaktamokshanaModality.JALAUKAVACHARANA:
            suggested_hemostasis = HemostasisMethod.SANDHANA  # Lodhra, Haridra, Priyangu churna application
        elif req.modality == RaktamokshanaModality.SIRAVEDHA:
            suggested_hemostasis = HemostasisMethod.SKANDANA  # Cold unction, compression bandage (Pichu)

        return SafetyEvaluationResponse(
            cleared=True,
            firewall_status="CLEARED",
            reason="All Sushruta classical and modern hemodynamic safety firewalls cleared.",
            max_permissible_volume_ml=max_vol,
            recommended_modality=req.modality,
            suggested_hemostasis=suggested_hemostasis,
            post_procedure_nutritional_replenishment=replenishment,
            estimated_post_op_hb_g_dl=estimated_post_hb
        )

    finally:
        if should_close:
            conn.close()


# -------------------------------------------------------------------------
# Procedure Execution Logging Engine
# -------------------------------------------------------------------------

def record_raktamokshana_procedure(
    payload: RaktamokshanaProcedureLogCreate,
    conn: Optional[sqlite3.Connection] = None
) -> RaktamokshanaProcedureLogResponse:
    """Validate safety status and persist Raktamokshana procedure execution log."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        # Pre-execution safety evaluation
        eval_req = SafetyEvaluationRequest(
            patient_id=payload.patient_id,
            hospital_id=payload.hospital_id,
            modality=payload.modality,
            rogi_bala=RogiBala.MADHYAMA,
            patient_age=35,
            patient_weight_kg=65.0,
            baseline_hemoglobin_g_dl=payload.pre_procedure_hb,
            proposed_volume_ml=payload.evacuated_volume_ml,
            species_id=payload.species_id,
            vein_code=payload.vein_or_point_id
        )

        eval_res = evaluate_raktamokshana_safety(eval_req, conn=conn)
        if not eval_res.cleared:
            raise ValueError(f"Procedure safety firewall violation: [{eval_res.firewall_status}] {eval_res.reason}")

        post_hb = payload.post_procedure_hb
        if post_hb is None:
            post_hb = estimate_post_op_hemoglobin(payload.pre_procedure_hb, payload.evacuated_volume_ml)

        now = int(time.time())
        proc_id = f"PROC-RAKTA-{now}-{uuid.uuid4().hex[:6].upper()}"

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO raktamokshana_procedure_logs (
                procedure_id, patient_id, hospital_id, modality, target_anatomical_site,
                vein_or_point_id, jalauka_count, evacuated_volume_ml, pre_procedure_hb,
                post_procedure_hb, blood_dosha_vitiation, hemostasis_method,
                safety_firewall_cleared, complications_observed_json, practitioner_arn, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                proc_id,
                payload.patient_id,
                payload.hospital_id,
                payload.modality.value,
                payload.target_anatomical_site,
                payload.vein_or_point_id,
                payload.jalauka_count,
                payload.evacuated_volume_ml,
                payload.pre_procedure_hb,
                post_hb,
                payload.blood_dosha_vitiation.value,
                payload.hemostasis_method.value,
                1 if eval_res.cleared else 0,
                json.dumps(payload.complications_observed),
                payload.practitioner_arn,
                now
            )
        )
        conn.commit()

        return RaktamokshanaProcedureLogResponse(
            procedure_id=proc_id,
            patient_id=payload.patient_id,
            hospital_id=payload.hospital_id,
            modality=payload.modality,
            target_anatomical_site=payload.target_anatomical_site,
            vein_or_point_id=payload.vein_or_point_id,
            species_id=payload.species_id,
            jalauka_count=payload.jalauka_count,
            evacuated_volume_ml=payload.evacuated_volume_ml,
            pre_procedure_hb=payload.pre_procedure_hb,
            post_procedure_hb=post_hb,
            blood_dosha_vitiation=payload.blood_dosha_vitiation,
            hemostasis_method=payload.hemostasis_method,
            safety_firewall_cleared=True,
            complications_observed=payload.complications_observed,
            practitioner_arn=payload.practitioner_arn,
            created_at=now
        )
    finally:
        if should_close:
            conn.close()


def list_jalauka_species(species_type: Optional[JalaukaType] = None, conn: Optional[sqlite3.Connection] = None) -> List[JalaukaSpecies]:
    """Retrieve catalog of classical leeches, optionally filtered by Nirvisha or Savisha."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        seed_raktamokshana_catalogs(conn)
        cursor = conn.cursor()
        if species_type:
            cursor.execute(
                "SELECT * FROM jalauka_species_registry WHERE species_type = ? ORDER BY sanskrit_name;",
                (species_type.value,)
            )
        else:
            cursor.execute("SELECT * FROM jalauka_species_registry ORDER BY species_type, sanskrit_name;")

        rows = cursor.fetchall()
        result = []
        for r in rows:
            result.append(
                JalaukaSpecies(
                    species_id=r["species_id"],
                    sanskrit_name=r["sanskrit_name"],
                    species_type=JalaukaType(r["species_type"]),
                    morphological_markers=json.loads(r["morphological_markers_json"]),
                    salivary_enzymes_profile=json.loads(r["salivary_enzymes_profile_json"]),
                    habitat_water_type=r["habitat_water_type"],
                    clinical_suitability=r["clinical_suitability"],
                    created_at=r["created_at"]
                )
            )
        return result
    finally:
        if should_close:
            conn.close()


def list_siravedha_veins(only_avadhya: Optional[bool] = None, quadrant: Optional[BodyQuadrant] = None, conn: Optional[sqlite3.Connection] = None) -> List[SiravedhaVein]:
    """Retrieve Siravedha vein matrix, with optional filters for Avadhya status and body quadrant."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        seed_raktamokshana_catalogs(conn)
        cursor = conn.cursor()
        query = "SELECT * FROM siravedha_vein_selection_matrix WHERE 1=1"
        params = []

        if only_avadhya is not None:
            query += " AND is_avadhya = ?"
            params.append(1 if only_avadhya else 0)

        if quadrant is not None:
            query += " AND body_quadrant = ?"
            params.append(quadrant.value)

        query += " ORDER BY body_quadrant, sanskrit_name;"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        result = []
        for r in rows:
            result.append(
                SiravedhaVein(
                    vein_code=r["vein_code"],
                    sanskrit_name=r["sanskrit_name"],
                    anatomical_location=r["anatomical_location"],
                    body_quadrant=BodyQuadrant(r["body_quadrant"]),
                    is_avadhya=bool(r["is_avadhya"]),
                    avadhya_complication_risk=AvadhyaComplicationRisk(r["avadhya_complication_risk"]),
                    indicated_diseases=json.loads(r["indicated_diseases_json"]),
                    puncture_depth_angula=r["puncture_depth_angula"],
                    instrument_shastra=ShastraUsed(r["instrument_shastra"]),
                    created_at=r["created_at"]
                )
            )
        return result
    finally:
        if should_close:
            conn.close()


def get_patient_raktamokshana_history(patient_id: str, conn: Optional[sqlite3.Connection] = None) -> List[RaktamokshanaProcedureLogResponse]:
    """Retrieve all Raktamokshana procedure records for a patient."""
    should_close = False
    if conn is None:
        conn = get_sqlite_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM raktamokshana_procedure_logs WHERE patient_id = ? ORDER BY created_at DESC;",
            (patient_id,)
        )
        rows = cursor.fetchall()

        result = []
        for r in rows:
            result.append(
                RaktamokshanaProcedureLogResponse(
                    procedure_id=r["procedure_id"],
                    patient_id=r["patient_id"],
                    hospital_id=r["hospital_id"],
                    modality=RaktamokshanaModality(r["modality"]),
                    target_anatomical_site=r["target_anatomical_site"],
                    vein_or_point_id=r["vein_or_point_id"],
                    species_id=None,
                    jalauka_count=r["jalauka_count"],
                    evacuated_volume_ml=r["evacuated_volume_ml"],
                    pre_procedure_hb=r["pre_procedure_hb"],
                    post_procedure_hb=r["post_procedure_hb"],
                    blood_dosha_vitiation=BloodDoshaVitiation(r["blood_dosha_vitiation"]),
                    hemostasis_method=HemostasisMethod(r["hemostasis_method"]),
                    safety_firewall_cleared=bool(r["safety_firewall_cleared"]),
                    complications_observed=json.loads(r["complications_observed_json"]),
                    practitioner_arn=r["practitioner_arn"],
                    created_at=r["created_at"]
                )
            )
        return result
    finally:
        if should_close:
            conn.close()
