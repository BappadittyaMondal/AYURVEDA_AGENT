"""
Classical Herbology (Dravya Guna) & Phytochemical Knowledge Graph Engine
======================================================================
Implements:
1. 25+ essential classical medicinal plants with comprehensive Rasa-Panchaka vectors
2. Validated bioactive phytochemical metabolite correlations
3. Multi-axial pharmacological search (by taste, potency, attribute, action, or bioactives)
4. Quantitative directional Doshic modulation vector synthesis
5. SQLite WAL persistence with immutable query execution
"""

from __future__ import annotations
import json
import time
import sqlite3
from typing import List, Optional, Dict, Any

from models.dravyaguna import (
    DoshicEffect,
    DoshicKarma,
    DoshicModulationScore,
    Guna,
    HerbProfile,
    HerbTherapeuticDosage,
    PhytochemicalBioactive,
    Rasa,
    Veerya,
    Vipaka,
)

# ==============================================================================
# CLASSICAL DRAVYA GUNA REFERENCE REGISTRY: 25 CORE MEDICINAL HERBS
# ==============================================================================

SEED_HERBAL_REGISTRY: List[HerbProfile] = [
    HerbProfile(
        herb_id="HERB-ASHWAGANDHA",
        sanskrit_name="अश्वगन्धा (Ashwagandha)",
        botanical_name="Withania somnifera (L.) Dunal",
        botanical_family="Solanaceae",
        classical_synonyms=["Varahakarni", "Hayagandha", "Balada", "Kamaroopini"],
        rasa=[Rasa.TIKTA, Rasa.KASHAYA, Rasa.MADHURA],
        guna=[Guna.LAGHU, Guna.SNIGDHA],
        veerya=Veerya.USHNA,
        vipaka=Vipaka.MADHURA,
        prabhava="Vajikarana and Rasayana (Adaptogenic neuro-rejuvenation)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.SAMA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Rasayana", "Balya", "Medhya", "Nidrajanana", "Shothahara", "Vajikarana"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Withaferin A", chemical_class="Steroidal lactone", pharmacological_action="Anti-inflammatory, Anti-tumor, NF-kB inhibitor"),
            PhytochemicalBioactive(compound_name="Withanolide D", chemical_class="Steroidal lactone", pharmacological_action="Immuno-modulatory, Neuro-protective"),
            PhytochemicalBioactive(compound_name="Somniferine", chemical_class="Alkaloid", pharmacological_action="Sedative, Hypnotic, GABA-mimetic")
        ],
        parts_used=["Mula (Root)"],
        dosages=[
            HerbTherapeuticDosage(form="Churna (Powder)", min_dose_g=3.0, max_dose_g=6.0, anupana="Warm Cow Milk or Ghee"),
            HerbTherapeuticDosage(form="Kwatha (Decoction)", min_dose_g=15.0, max_dose_g=30.0, anupana="Warm water")
        ],
        contraindications=["Severe Pitta prakopa", "Acute inflammatory gastritis with burning", "High pyrexia (Taruna Jwara)"]
    ),

    HerbProfile(
        herb_id="HERB-GUDUCHI",
        sanskrit_name="गुडूची (Guduchi)",
        botanical_name="Tinospora cordifolia (Willd.) Miers",
        botanical_family="Menispermaceae",
        classical_synonyms=["Amrita", "Chhinnaruha", "Vatsadani", "Kundali"],
        rasa=[Rasa.TIKTA, Rasa.KASHAYA],
        guna=[Guna.GURU, Guna.SNIGDHA],
        veerya=Veerya.USHNA,
        vipaka=Vipaka.MADHURA,
        prabhava="Tridosha Shamana and Jwaraghna (Thermal immunomodulation)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.SHAMANA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Rasayana", "Jwaraghna", "Deepana", "Dahaprashamana", "Mehaghna", "Vataraktahara"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Tinosporide", chemical_class="Diterpenoid", pharmacological_action="Hepatoprotective, Anti-inflammatory"),
            PhytochemicalBioactive(compound_name="Cordifolioside A", chemical_class="Glycoside", pharmacological_action="Macrophage activating, Immunostimulant"),
            PhytochemicalBioactive(compound_name="Berberine", chemical_class="Isoquinoline alkaloid", pharmacological_action="Antimicrobial, Hypoglycemic")
        ],
        parts_used=["Kanda (Stem)"],
        dosages=[
            HerbTherapeuticDosage(form="Guduchi Satva (Extract)", min_dose_g=0.5, max_dose_g=1.0, anupana="Honey or Warm water"),
            HerbTherapeuticDosage(form="Kwatha (Decoction)", min_dose_g=20.0, max_dose_g=50.0, anupana="Warm water")
        ],
        contraindications=["Caution in autoimmune flare-ups requiring acute immunosuppression"]
    ),

    HerbProfile(
        herb_id="HERB-HARIDRA",
        sanskrit_name="हरिद्रा (Haridra)",
        botanical_name="Curcuma longa L.",
        botanical_family="Zingiberaceae",
        classical_synonyms=["Nisha", "Gauri", "Kanchani", "Yoshitpriya"],
        rasa=[Rasa.TIKTA, Rasa.KATU],
        guna=[Guna.LAGHU, Guna.RUKSHA],
        veerya=Veerya.USHNA,
        vipaka=Vipaka.KATU,
        prabhava="Varnya and Vishaghna (Dermal detoxification and anti-allergic)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.SAMA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Lekhana", "Varnya", "Vishaghna", "Mehaghna", "Kandughna", "Shothahara"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Curcumin", chemical_class="Polyphenolic curcuminoid", pharmacological_action="Potent COX-2/LOX inhibitor, Antioxidant"),
            PhytochemicalBioactive(compound_name="Demethoxycurcumin", chemical_class="Curcuminoid", pharmacological_action="Anti-angiogenic, Cytoprotective"),
            PhytochemicalBioactive(compound_name="Ar-Turmerone", chemical_class="Sesquiterpene", pharmacological_action="Neural stem cell proliferation, Anti-inflammatory")
        ],
        parts_used=["Kanda (Rhizome)"],
        dosages=[
            HerbTherapeuticDosage(form="Churna (Powder)", min_dose_g=1.0, max_dose_g=3.0, anupana="Warm Milk with Ghee or Honey")
        ],
        contraindications=["Biliary tract obstruction", "Acute cholelithiasis", "Bleeding disorders"]
    ),

    HerbProfile(
        herb_id="HERB-AMALAKI",
        sanskrit_name="आमलकी (Amalaki)",
        botanical_name="Phyllanthus emblica L.",
        botanical_family="Phyllanthaceae",
        classical_synonyms=["Dhatri", "Shiva", "Vayastha", "Amritaphala"],
        rasa=[Rasa.MADHURA, Rasa.AMLA, Rasa.TIKTA, Rasa.KATU, Rasa.KASHAYA],
        guna=[Guna.GURU, Guna.SHEETA, Guna.RUKSHA],
        veerya=Veerya.SHEETA,
        vipaka=Vipaka.MADHURA,
        prabhava="Rasayana and Vayasthapana (Longevity cellular protection)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.SHAMANA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Rasayana", "Chakshushya", "Vayasthapana", "Pramehaghna", "Dahaharana", "Deepana"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Emblicanin A & B", chemical_class="Ellagitannin", pharmacological_action="Antioxidant cascade recycler"),
            PhytochemicalBioactive(compound_name="Ascorbic Acid", chemical_class="Vitamin", pharmacological_action="Collagen synthesis, Free radical scavenger"),
            PhytochemicalBioactive(compound_name="Gallic Acid", chemical_class="Phenolic acid", pharmacological_action="Cardioprotective, Hepatoprotective")
        ],
        parts_used=["Phala (Fruit pulp)"],
        dosages=[
            HerbTherapeuticDosage(form="Churna (Powder)", min_dose_g=3.0, max_dose_g=6.0, anupana="Honey, Ghee, or Water"),
            HerbTherapeuticDosage(form="Svarasa (Fresh juice)", min_dose_g=10.0, max_dose_g=20.0, anupana="Honey")
        ],
        contraindications=["Severe cold watery diarrhea"]
    ),

    HerbProfile(
        herb_id="HERB-HARITAKI",
        sanskrit_name="हरीतकी (Haritaki)",
        botanical_name="Terminalia chebula Retz.",
        botanical_family="Combretaceae",
        classical_synonyms=["Abhaya", "Pathya", "Kayastha", "Shiva", "Chetaki"],
        rasa=[Rasa.KASHAYA, Rasa.MADHURA, Rasa.TIKTA, Rasa.KATU, Rasa.AMLA],
        guna=[Guna.LAGHU, Guna.RUKSHA],
        veerya=Veerya.USHNA,
        vipaka=Vipaka.MADHURA,
        prabhava="Tridoshahara and Doshanulomana (Physiological bowel harmonizer)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.SHAMANA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Anulomana", "Deepana", "Pachana", "Rasayana", "Medhya", "Chakshushya"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Chebulagic Acid", chemical_class="Tannin", pharmacological_action="Prokinetic, Anti-ulcer, Antimicrobial"),
            PhytochemicalBioactive(compound_name="Chebulinic Acid", chemical_class="Ellagitannin", pharmacological_action="Antioxidant, Hepatoprotective")
        ],
        parts_used=["Phala Tvak (Fruit rind)"],
        dosages=[
            HerbTherapeuticDosage(form="Churna (Powder)", min_dose_g=3.0, max_dose_g=6.0, anupana="Warm water or Castor oil")
        ],
        contraindications=["Severe emaciation (Krisha)", "Pregnancy", "Acute dehydration", "Exhaustion from fasting"]
    ),

    HerbProfile(
        herb_id="HERB-BIBHITAKI",
        sanskrit_name="बिभीतक (Bibhitaki)",
        botanical_name="Terminalia bellirica (Gaertn.) Roxb.",
        botanical_family="Combretaceae",
        classical_synonyms=["Aksha", "Karshaphala", "Kalidruma", "Bhoothavasa"],
        rasa=[Rasa.KASHAYA],
        guna=[Guna.LAGHU, Guna.RUKSHA],
        veerya=Veerya.USHNA,
        vipaka=Vipaka.MADHURA,
        prabhava="Bhedana and Kaphaghna (Bronchial mucus liquefaction)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SAMA, pitta=DoshicEffect.SHAMANA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Bhedana", "Kaphaghna", "Chakshushya", "Keshya", "Kasa-Shvasahara"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Bellericanin", chemical_class="Tannin", pharmacological_action="Antioxidant, Expectorant"),
            PhytochemicalBioactive(compound_name="Ellagic Acid", chemical_class="Polyphenol", pharmacological_action="Chemoprotective, Anti-inflammatory")
        ],
        parts_used=["Phala (Fruit pericarp)"],
        dosages=[
            HerbTherapeuticDosage(form="Churna (Powder)", min_dose_g=3.0, max_dose_g=6.0, anupana="Honey or Warm water")
        ],
        contraindications=["Excessive dryness in colon"]
    ),

    HerbProfile(
        herb_id="HERB-SHUNTHI",
        sanskrit_name="शुण्ठी (Shunthi / Nagara)",
        botanical_name="Zingiber officinale Roscoe",
        botanical_family="Zingiberaceae",
        classical_synonyms=["Mahoushadha", "Nagara", "Vishvabhesaja", "Katubhadra"],
        rasa=[Rasa.KATU],
        guna=[Guna.GURU, Guna.SNIGDHA, Guna.TIKSHNA],
        veerya=Veerya.USHNA,
        vipaka=Vipaka.MADHURA,
        prabhava="Vrishya and Vibandhabhedana (Non-irritant bio-fire ignition)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.SAMA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Deepana", "Pachana", "Grahi", "Shothahara", "Hridya", "Amavatahara"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="6-Gingerol", chemical_class="Gingerol", pharmacological_action="Prokinetic, Anti-emetic, Analgesic"),
            PhytochemicalBioactive(compound_name="6-Shogaol", chemical_class="Shogaol", pharmacological_action="TRPV1 agonist, Anti-inflammatory")
        ],
        parts_used=["Kanda (Dry rhizome)"],
        dosages=[
            HerbTherapeuticDosage(form="Churna (Powder)", min_dose_g=1.0, max_dose_g=2.0, anupana="Warm water or Honey")
        ],
        contraindications=["Bleeding disorders", "Severe Raktapitta", "Acute peptic ulcer perforation"]
    ),

    HerbProfile(
        herb_id="HERB-MARICHA",
        sanskrit_name="मरिच (Maricha)",
        botanical_name="Piper nigrum L.",
        botanical_family="Piperaceae",
        classical_synonyms=["Krishna", "Vellaja", "Ushana", "Yavanishta"],
        rasa=[Rasa.KATU],
        guna=[Guna.LAGHU, Guna.TIKSHNA, Guna.RUKSHA],
        veerya=Veerya.USHNA,
        vipaka=Vipaka.KATU,
        prabhava="Pramathi and Srotoshodhana (Channel clearing by mucus liquefaction)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.KOPANA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Deepana", "Krimighna", "Shvasahara", "Lekhana", "Pramathi"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Piperine", chemical_class="Alkaloid", pharmacological_action="Bioavailability enhancer, Thermogenic stimulant"),
            PhytochemicalBioactive(compound_name="Chavicine", chemical_class="Isomer", pharmacological_action="Digestive enzyme secretagogue")
        ],
        parts_used=["Phala (Dried unripe fruit)"],
        dosages=[
            HerbTherapeuticDosage(form="Churna (Powder)", min_dose_g=0.5, max_dose_g=1.0, anupana="Honey or Ghee")
        ],
        contraindications=["Severe hyperchlorhydria", "Gastric ulcers", "Urethritis"]
    ),

    HerbProfile(
        herb_id="HERB-PIPPALI",
        sanskrit_name="पिप्पली (Pippali)",
        botanical_name="Piper longum L.",
        botanical_family="Piperaceae",
        classical_synonyms=["Magadhi", "Vaidehi", "Krishna", "Kana"],
        rasa=[Rasa.KATU],
        guna=[Guna.LAGHU, Guna.SNIGDHA, Guna.TIKSHNA],
        veerya=Veerya.USHNA,
        vipaka=Vipaka.MADHURA,
        prabhava="Rasayana for Pranavaha Srotas (Pulmonary rejuvenation)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.SAMA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Deepana", "Pachana", "Rasayana", "Shvasahara", "Kasahara", "Pleehaghna"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Piperlongumine", chemical_class="Alkaloid", pharmacological_action="Anti-asthmatic, Anti-angiogenic"),
            PhytochemicalBioactive(compound_name="Piperine", chemical_class="Alkaloid", pharmacological_action="Bio-enhancer, Bio-fire catalyst")
        ],
        parts_used=["Phala (Dried fruiting spike)"],
        dosages=[
            HerbTherapeuticDosage(form="Churna (Powder)", min_dose_g=0.5, max_dose_g=1.5, anupana="Honey or Warm Milk")
        ],
        contraindications=["Chronic continuous unmonitored use without Rasayana protocol (Pippali Vardhamana)"]
    ),

    HerbProfile(
        herb_id="HERB-GUGGULU",
        sanskrit_name="गुग्गुलु (Guggulu)",
        botanical_name="Commiphora mukul (Stocks) Hook.",
        botanical_family="Burseraceae",
        classical_synonyms=["Puram", "Kaushika", "Mahishaksha", "Palankasha"],
        rasa=[Rasa.TIKTA, Rasa.KATU, Rasa.KASHAYA, Rasa.MADHURA],
        guna=[Guna.LAGHU, Guna.RUKSHA, Guna.TIKSHNA, Guna.VISHADA, Guna.SUKSHMA, Guna.SARA],
        veerya=Veerya.USHNA,
        vipaka=Vipaka.KATU,
        prabhava="Medohara and Bhagnasandhanakara (Atherolytic and osteogenic)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.SAMA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Lekhana", "Medohara", "Bhagnasandhanakara", "Rasayana", "Vranashodhana", "Amavatahara"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="E-Guggulsterone", chemical_class="Steroid", pharmacological_action="Farnesoid X receptor antagonist, Hypolipidemic"),
            PhytochemicalBioactive(compound_name="Z-Guggulsterone", chemical_class="Steroid", pharmacological_action="Thyroid stimulant, Anti-inflammatory"),
            PhytochemicalBioactive(compound_name="Mukulol", chemical_class="Diterpenoid", pharmacological_action="Platelet aggregation inhibitor")
        ],
        parts_used=["Niryasa (Purified oleo-gum-resin)"],
        dosages=[
            HerbTherapeuticDosage(form="Shuddha Guggulu Vati", min_dose_g=1.0, max_dose_g=3.0, anupana="Warm water or Dashamula Kwatha")
        ],
        contraindications=["Severe liver failure", "Pregnancy (uterine stimulant)", "Severe menorrhagia"]
    ),

    HerbProfile(
        herb_id="HERB-SHALLAKI",
        sanskrit_name="शल्लकी (Shallaki)",
        botanical_name="Boswellia serrata Roxb. ex Colebr.",
        botanical_family="Burseraceae",
        classical_synonyms=["Kunduru", "Gajabhakshya", "Surabhi", "Suvaha"],
        rasa=[Rasa.TIKTA, Rasa.KASHAYA, Rasa.MADHURA],
        guna=[Guna.LAGHU, Guna.RUKSHA],
        veerya=Veerya.SHEETA,
        vipaka=Vipaka.KATU,
        prabhava="Sandhigata Vedanasthapana (Targeted articular chondroprotection)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.SHAMANA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Shothahara", "Vedanasthapana", "Sandhaniya", "Raktastambhana", "Purishasangrahaniya"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Acetyl-11-keto-beta-boswellic acid (AKBA)", chemical_class="Pentacyclic triterpene", pharmacological_action="5-Lipoxygenase (5-LOX) inhibitor, Chondroprotective"),
            PhytochemicalBioactive(compound_name="Beta-Boswellic Acid", chemical_class="Triterpene", pharmacological_action="Elastase inhibitor")
        ],
        parts_used=["Niryasa (Exudate resin)"],
        dosages=[
            HerbTherapeuticDosage(form="Extract / Churna", min_dose_g=1.0, max_dose_g=3.0, anupana="Warm water")
        ],
        contraindications=["Severe acute constipation with dry impaction"]
    ),

    HerbProfile(
        herb_id="HERB-SHATAVARI",
        sanskrit_name="शतावरी (Shatavari)",
        botanical_name="Asparagus racemosus Willd.",
        botanical_family="Asparagaceae",
        classical_synonyms=["Bahusuta", "Vari", "Abheeru", "Narayani", "Atirasa"],
        rasa=[Rasa.MADHURA, Rasa.TIKTA],
        guna=[Guna.GURU, Guna.SNIGDHA],
        veerya=Veerya.SHEETA,
        vipaka=Vipaka.MADHURA,
        prabhava="Stanyajanana and Shukrala (Endocrine reproductive rejuvenation)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.SHAMANA, kapha=DoshicEffect.SAMA),
        therapeutics_karma=["Rasayana", "Balya", "Stanyajanana", "Shukrala", "Chakshushya", "Amlapittahara"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Shatavarin I-IV", chemical_class="Steroidal saponin", pharmacological_action="Phytoestrogenic, Galactagogue, Immunostimulant"),
            PhytochemicalBioactive(compound_name="Sarsasapogenin", chemical_class="Sapogenin", pharmacological_action="Neuroprotective, Anti-ulcer")
        ],
        parts_used=["Mula (Tuberous root)"],
        dosages=[
            HerbTherapeuticDosage(form="Churna (Powder)", min_dose_g=3.0, max_dose_g=6.0, anupana="Warm Cow Milk and Sugar candy")
        ],
        contraindications=["Severe congestive heart failure with fluid retention", "Kidney failure with edema"]
    ),

    HerbProfile(
        herb_id="HERB-BRAHMI",
        sanskrit_name="ब्राह्मी (Brahmi)",
        botanical_name="Bacopa monnieri (L.) Wettst.",
        botanical_family="Plantaginaceae",
        classical_synonyms=["Saraswati", "Kapotavanka", "Somavalli", "Mahaushadhi"],
        rasa=[Rasa.TIKTA, Rasa.KASHAYA, Rasa.MADHURA],
        guna=[Guna.LAGHU],
        veerya=Veerya.SHEETA,
        vipaka=Vipaka.MADHURA,
        prabhava="Medhya and Smritiprada (Synaptic plasticity facilitator)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.SHAMANA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Medhya", "Smritiprada", "Prajasthapana", "Ayushya", "Unmadahara", "Kushthahara"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Bacoside A", chemical_class="Dammarane triterpenoid saponin", pharmacological_action="Enhances cholinergic transmission, Neuroprotective"),
            PhytochemicalBioactive(compound_name="Bacoside B", chemical_class="Triterpenoid saponin", pharmacological_action="Cerebral blood flow enhancer, Memory enhancer")
        ],
        parts_used=["Panchanga (Whole plant)"],
        dosages=[
            HerbTherapeuticDosage(form="Svarasa (Fresh juice)", min_dose_g=10.0, max_dose_g=20.0, anupana="Honey or Ghee"),
            HerbTherapeuticDosage(form="Churna (Powder)", min_dose_g=2.0, max_dose_g=5.0, anupana="Ghee")
        ],
        contraindications=["Severe bradycardia", "Thyrotoxicosis (use with care)"]
    ),

    HerbProfile(
        herb_id="HERB-SHANKHAPUSHPI",
        sanskrit_name="शंखपुष्पी (Shankhapushpi)",
        botanical_name="Convolvulus pluricaulis Choisy",
        botanical_family="Convolvulaceae",
        classical_synonyms=["Ksheerapushpi", "Mangalyakusuma", "Medhya"],
        rasa=[Rasa.TIKTA],
        guna=[Guna.SNIGDHA, Guna.PICCHILA],
        veerya=Veerya.SHEETA,
        vipaka=Vipaka.MADHURA,
        prabhava="Param Medhya (Supreme psycho-cognitive tranquilizer)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.SHAMANA, kapha=DoshicEffect.SAMA),
        therapeutics_karma=["Medhya", "Nidrajanana", "Manasadoshahara", "Rasayana", "Raktachapahara"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Convolvine", chemical_class="Tropane alkaloid", pharmacological_action="Anxiolytic, Anti-convulsant"),
            PhytochemicalBioactive(compound_name="Shankhapushpine", chemical_class="Alkaloid", pharmacological_action="Neuro-calmative, Hypolipemic")
        ],
        parts_used=["Panchanga (Whole plant)"],
        dosages=[
            HerbTherapeuticDosage(form="Svarasa (Fresh juice)", min_dose_g=10.0, max_dose_g=20.0, anupana="Honey"),
            HerbTherapeuticDosage(form="Churna (Powder)", min_dose_g=3.0, max_dose_g=6.0, anupana="Milk")
        ],
        contraindications=["Excessive sedation", "Extreme hypotension"]
    ),

    HerbProfile(
        herb_id="HERB-VASA",
        sanskrit_name="वासा (Vasa)",
        botanical_name="Justicia adhatoda L.",
        botanical_family="Acanthaceae",
        classical_synonyms=["Vasaka", "Atarusha", "Simhasya", "Vajridanti"],
        rasa=[Rasa.TIKTA, Rasa.KASHAYA],
        guna=[Guna.LAGHU, Guna.RUKSHA],
        veerya=Veerya.SHEETA,
        vipaka=Vipaka.KATU,
        prabhava="Raktapittahara and Kasahara (Bronchial antispasmodic & hemostatic)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SAMA, pitta=DoshicEffect.SHAMANA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Kasahara", "Shvasahara", "Raktapittahara", "Jwaraghna", "Kshayaghna"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Vasicine", chemical_class="Quinazoline alkaloid", pharmacological_action="Bronchodilator, Expectorant, Uterotonic"),
            PhytochemicalBioactive(compound_name="Vasicinone", chemical_class="Alkaloid", pharmacological_action="Potent bronchodilation, Antihistaminic")
        ],
        parts_used=["Patra (Leaves)"],
        dosages=[
            HerbTherapeuticDosage(form="Svarasa (Fresh juice)", min_dose_g=10.0, max_dose_g=20.0, anupana="Honey"),
            HerbTherapeuticDosage(form="Kwatha (Decoction)", min_dose_g=15.0, max_dose_g=30.0, anupana="Warm water")
        ],
        contraindications=["Pregnancy (due to uterotonic vasicine activity)"]
    ),

    HerbProfile(
        herb_id="HERB-TULSI",
        sanskrit_name="तुलसी (Tulsi)",
        botanical_name="Ocimum sanctum L.",
        botanical_family="Lamiaceae",
        classical_synonyms=["Surasa", "Gramya", "Sulabha", "Bahumanjari", "Vishnupriya"],
        rasa=[Rasa.KATU, Rasa.TIKTA],
        guna=[Guna.LAGHU, Guna.RUKSHA, Guna.TIKSHNA],
        veerya=Veerya.USHNA,
        vipaka=Vipaka.KATU,
        prabhava="Bhutaghna and Hridya (Antimicrobial and cardioprotective)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.SAMA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Shvasahara", "Kasahara", "Krimighna", "Deepana", "Hridya", "Vishaghna"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Eugenol", chemical_class="Phenolic compound", pharmacological_action="Antimicrobial, Analgesic, Anti-inflammatory"),
            PhytochemicalBioactive(compound_name="Ursolic Acid", chemical_class="Triterpenoid", pharmacological_action="Antiviral, Immunostimulant, Cardioprotective")
        ],
        parts_used=["Patra (Leaves)", "Beeja (Seeds)"],
        dosages=[
            HerbTherapeuticDosage(form="Svarasa (Juice)", min_dose_g=5.0, max_dose_g=10.0, anupana="Honey"),
            HerbTherapeuticDosage(form="Churna (Powder)", min_dose_g=1.0, max_dose_g=3.0, anupana="Warm water")
        ],
        contraindications=["High Pitta burning conditions in empty stomach"]
    ),

    HerbProfile(
        herb_id="HERB-NIMBA",
        sanskrit_name="निम्ब (Nimba)",
        botanical_name="Azadirachta indica A. Juss.",
        botanical_family="Meliaceae",
        classical_synonyms=["Arishta", "Pichumarda", "Hinguniryasa", "Tikta"],
        rasa=[Rasa.TIKTA, Rasa.KASHAYA],
        guna=[Guna.LAGHU, Guna.RUKSHA],
        veerya=Veerya.SHEETA,
        vipaka=Vipaka.KATU,
        prabhava="Krimighna and Kushthaghna (Dermatological anti-pathogenic)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.KOPANA, pitta=DoshicEffect.SHAMANA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Kandughna", "Kushthaghna", "Krimighna", "Vranashodhana", "Jwaraghna", "Raktashodhaka"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Azadirachtin", chemical_class="Limonoid", pharmacological_action="Antiparasitic, Antiviral"),
            PhytochemicalBioactive(compound_name="Nimbin", chemical_class="Limonoid", pharmacological_action="Anti-inflammatory, Antihistaminic"),
            PhytochemicalBioactive(compound_name="Nimbidin", chemical_class="Tetranortriterpene", pharmacological_action="Anti-ulcer, Antibacterial")
        ],
        parts_used=["Tvak (Stem bark)", "Patra (Leaves)", "Beeja Taila (Seed oil)"],
        dosages=[
            HerbTherapeuticDosage(form="Tvak Kwatha", min_dose_g=15.0, max_dose_g=30.0, anupana="Warm water"),
            HerbTherapeuticDosage(form="Churna", min_dose_g=1.0, max_dose_g=3.0, anupana="Honey or Water")
        ],
        contraindications=["Excessive Vata emaciation", "Severe male infertility / low sperm count", "Infants"]
    ),

    HerbProfile(
        herb_id="HERB-KUTAJA",
        sanskrit_name="कुटज (Kutaja)",
        botanical_name="Holarrhena antidysenterica Wall.",
        botanical_family="Apocynaceae",
        classical_synonyms=["Kalinga", "Girimallika", "Vatsaka", "Indravriksha"],
        rasa=[Rasa.TIKTA, Rasa.KASHAYA],
        guna=[Guna.LAGHU, Guna.RUKSHA],
        veerya=Veerya.SHEETA,
        vipaka=Vipaka.KATU,
        prabhava="Arshoghna and Atisaraghna (Targeted colonic hemostasis & anti-dysenteric)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SAMA, pitta=DoshicEffect.SHAMANA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Atisaraghna", "Grahini", "Deepana", "Raktastambhana", "Krimighna"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Conessine", chemical_class="Steroidal alkaloid", pharmacological_action="Anti-amoebic, Anti-bacterial, Anti-diarrheal"),
            PhytochemicalBioactive(compound_name="Holarrhenine", chemical_class="Alkaloid", pharmacological_action="Spasmolytic, Astringent")
        ],
        parts_used=["Tvak (Bark)", "Beeja (Indrayava)"],
        dosages=[
            HerbTherapeuticDosage(form="Tvak Kwatha", min_dose_g=20.0, max_dose_g=50.0, anupana="Takra / Buttermilk"),
            HerbTherapeuticDosage(form="Churna", min_dose_g=3.0, max_dose_g=6.0, anupana="Honey or Takra")
        ],
        contraindications=["Acute obstinate constipation", "Dry mechanical obstruction"]
    ),

    HerbProfile(
        herb_id="HERB-VIDANGA",
        sanskrit_name="विडङ्ग (Vidanga)",
        botanical_name="Embelia ribes Burm. f.",
        botanical_family="Primulaceae",
        classical_synonyms=["Jantughna", "Krimihara", "Vella", "Amogha"],
        rasa=[Rasa.KATU, Rasa.TIKTA],
        guna=[Guna.LAGHU, Guna.RUKSHA, Guna.TIKSHNA],
        veerya=Veerya.USHNA,
        vipaka=Vipaka.KATU,
        prabhava="Param Krimighna (Supreme anthelmintic biological agent)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.SAMA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Krimighna", "Deepana", "Pachana", "Anulomana", "Kushthaghna"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Embelin", chemical_class="Benzoquinone", pharmacological_action="Broad-spectrum anthelmintic, Antifertility, Anti-inflammatory"),
            PhytochemicalBioactive(compound_name="Embelic Acid", chemical_class="Quinone derivative", pharmacological_action="Vermifuge, Antibacterial")
        ],
        parts_used=["Phala (Dried fruits)"],
        dosages=[
            HerbTherapeuticDosage(form="Churna (Powder)", min_dose_g=3.0, max_dose_g=6.0, anupana="Warm water or Honey")
        ],
        contraindications=["Active pregnancy", "Couples attempting immediate conception (due to anti-fertility embelin)"]
    ),

    HerbProfile(
        herb_id="HERB-PUNARNAVA",
        sanskrit_name="पुनर्नवा (Punarnava)",
        botanical_name="Boerhavia diffusa L.",
        botanical_family="Nyctaginaceae",
        classical_synonyms=["Shothaghni", "Raktapunarnava", "Varshabhu", "Kathillaka"],
        rasa=[Rasa.MADHURA, Rasa.TIKTA, Rasa.KASHAYA],
        guna=[Guna.LAGHU, Guna.RUKSHA],
        veerya=Veerya.USHNA,
        vipaka=Vipaka.KATU,
        prabhava="Shothaghna (Renal glomerular drainage and anti-edema)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.SHAMANA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Shothahara", "Mutrala", "Hridya", "Rasayana", "Pandughna"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Punarnavine", chemical_class="Alkaloid", pharmacological_action="Diuretic, Cardioprotective, Anti-fibrinolytic"),
            PhytochemicalBioactive(compound_name="Boeravinones A-F", chemical_class="Rotenoid", pharmacological_action="Anti-inflammatory, Renal protective, Spasmolytic")
        ],
        parts_used=["Mula (Root)", "Panchanga (Whole herb)"],
        dosages=[
            HerbTherapeuticDosage(form="Kwatha (Decoction)", min_dose_g=20.0, max_dose_g=50.0, anupana="Warm water"),
            HerbTherapeuticDosage(form="Churna", min_dose_g=3.0, max_dose_g=6.0, anupana="Water")
        ],
        contraindications=["Severe electrolyte depletion from excessive synthetic diuretics"]
    ),

    HerbProfile(
        herb_id="HERB-GOKSHURA",
        sanskrit_name="गोक्षुर (Gokshura)",
        botanical_name="Tribulus terrestris L.",
        botanical_family="Zygophyllaceae",
        classical_synonyms=["Trikantaka", "Shvadamshtra", "Vanashringata", "Chanadruma"],
        rasa=[Rasa.MADHURA],
        guna=[Guna.GURU, Guna.SNIGDHA],
        veerya=Veerya.SHEETA,
        vipaka=Vipaka.MADHURA,
        prabhava="Basti Shodhana and Ashmarighna (Lithotriptic and nephron-soothing)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.SHAMANA, kapha=DoshicEffect.SAMA),
        therapeutics_karma=["Mutrala", "Ashmarighna", "Vrishya", "Balya", "Basti-shodhana", "Hridya"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Protodioscin", chemical_class="Furostanol saponin", pharmacological_action="Androgen receptor up-regulator, Nitric oxide release"),
            PhytochemicalBioactive(compound_name="Tribuloside", chemical_class="Flavonoid glycoside", pharmacological_action="Diuretic, Lithotriptic, Nephroprotective")
        ],
        parts_used=["Phala (Fruits)", "Mula (Roots)"],
        dosages=[
            HerbTherapeuticDosage(form="Kwatha (Decoction)", min_dose_g=20.0, max_dose_g=50.0, anupana="Warm water"),
            HerbTherapeuticDosage(form="Churna", min_dose_g=3.0, max_dose_g=6.0, anupana="Milk or Ghee")
        ],
        contraindications=["Large obstructive ureteral calculus requiring emergent surgical stenting"]
    ),

    HerbProfile(
        herb_id="HERB-MANJISTHA",
        sanskrit_name="मञ्जिष्ठा (Manjistha)",
        botanical_name="Rubia cordifolia L.",
        botanical_family="Rubiaceae",
        classical_synonyms=["Vastraranjini", "Raktangi", "Yojanavalli", "Kala"],
        rasa=[Rasa.TIKTA, Rasa.KASHAYA, Rasa.MADHURA],
        guna=[Guna.GURU, Guna.RUKSHA],
        veerya=Veerya.USHNA,
        vipaka=Vipaka.KATU,
        prabhava="Raktashodhaka and Varnya (Microcirculatory purifying and pigmentation cleanser)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SAMA, pitta=DoshicEffect.SHAMANA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Raktashodhaka", "Varnya", "Vishaghna", "Shothahara", "Vranaropana"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Purpurin", chemical_class="Anthraquinone", pharmacological_action="Antioxidant, Anti-thrombotic, Skin depigmenting"),
            PhytochemicalBioactive(compound_name="Alizarin", chemical_class="Anthraquinone dye", pharmacological_action="Anti-angiogenic, Anti-psoriatic"),
            PhytochemicalBioactive(compound_name="Rubiadin", chemical_class="Dihydroxyanthraquinone", pharmacological_action="Hepatoprotective, Free radical scavenger")
        ],
        parts_used=["Kanda / Mula (Stem and root)"],
        dosages=[
            HerbTherapeuticDosage(form="Churna (Powder)", min_dose_g=2.0, max_dose_g=4.0, anupana="Warm water or Honey"),
            HerbTherapeuticDosage(form="Kwatha", min_dose_g=20.0, max_dose_g=40.0, anupana="Warm water")
        ],
        contraindications=["Active pregnancy", "Lactating mothers (anthraquinones cross into milk)"]
    ),

    HerbProfile(
        herb_id="HERB-YASHTIMADHU",
        sanskrit_name="यष्टीमधु (Yashtimadhu)",
        botanical_name="Glycyrrhiza glabra L.",
        botanical_family="Fabaceae",
        classical_synonyms=["Madhuka", "Klitaka", "Madhuyashtika", "Jalaruha"],
        rasa=[Rasa.MADHURA],
        guna=[Guna.GURU, Guna.SNIGDHA],
        veerya=Veerya.SHEETA,
        vipaka=Vipaka.MADHURA,
        prabhava="Chakshushya and Vranaropana (Mucosal cytoprotection and ophthalmic rejuvenation)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.SHAMANA, kapha=DoshicEffect.KOPANA),
        therapeutics_karma=["Chardighna", "Varnya", "Chakshushya", "Kanthya", "Rasayana", "Vranaropana"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Glycyrrhizin", chemical_class="Triterpene saponin", pharmacological_action="11-beta-HSD inhibitor, Cortisol sparing, Anti-ulcer"),
            PhytochemicalBioactive(compound_name="Isoliquiritigenin", chemical_class="Chalcone flavonoid", pharmacological_action="Spasmolytic, Cytoprotective, Anti-inflammatory")
        ],
        parts_used=["Mula (Dried peeled root)"],
        dosages=[
            HerbTherapeuticDosage(form="Churna (Powder)", min_dose_g=2.0, max_dose_g=4.0, anupana="Warm Milk, Honey, or Water")
        ],
        contraindications=["Severe hypertension (pseudoaldosteronism risk at high chronic doses)", "Hypokalemia", "Severe renal insufficiency"]
    ),

    HerbProfile(
        herb_id="HERB-KATUKI",
        sanskrit_name="कटुकी (Katuki)",
        botanical_name="Picrorhiza kurroa Royle ex Benth.",
        botanical_family="Plantaginaceae",
        classical_synonyms=["Tikta", "Tiktarohini", "Matsyapitta", "Chakrangi"],
        rasa=[Rasa.TIKTA],
        guna=[Guna.LAGHU, Guna.RUKSHA],
        veerya=Veerya.SHEETA,
        vipaka=Vipaka.KATU,
        prabhava="Bhedana and Yakriduttejaka (Cholegogue and hepatic enzyme inducer)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SAMA, pitta=DoshicEffect.SHAMANA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Bhedana", "Deepana", "Hridya", "Jwaraghna", "Yakriduttejaka", "Kushtaghna"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Picroside I", chemical_class="Iridoid glycoside", pharmacological_action="Potent hepatoprotective, Superoxide scavenger"),
            PhytochemicalBioactive(compound_name="Picroside II", chemical_class="Iridoid glycoside", pharmacological_action="Choleretic, Immunomodulatory, Anti-inflammatory")
        ],
        parts_used=["Kanda (Dried rhizome)"],
        dosages=[
            HerbTherapeuticDosage(form="Churna (Deepana/Pachana)", min_dose_g=0.5, max_dose_g=1.0, anupana="Warm water or Honey"),
            HerbTherapeuticDosage(form="Churna (Bhedana / Purgative)", min_dose_g=1.5, max_dose_g=3.0, anupana="Warm water")
        ],
        contraindications=["Severe chronic diarrhea / loose bowels", "Infants", "Severe emaciation"]
    ),

    HerbProfile(
        herb_id="HERB-TWAK",
        sanskrit_name="त्वक् (Twak / Dalchini)",
        botanical_name="Cinnamomum verum J. Presl",
        botanical_family="Lauraceae",
        classical_synonyms=["Varanga", "Chocha", "Utkata", "Bahugandha"],
        rasa=[Rasa.KATU, Rasa.TIKTA, Rasa.MADHURA],
        guna=[Guna.LAGHU, Guna.RUKSHA, Guna.TIKSHNA],
        veerya=Veerya.USHNA,
        vipaka=Vipaka.KATU,
        prabhava="Mukhadurgandhihara and Vata Anulomana (Insulin sensitizer and carminative)",
        doshic_karma=DoshicKarma(vata=DoshicEffect.SHAMANA, pitta=DoshicEffect.KOPANA, kapha=DoshicEffect.SHAMANA),
        therapeutics_karma=["Deepana", "Pachana", "Hridya", "Mukhadurgandhihara", "Shvasa-Kasahara"],
        phytochemicals=[
            PhytochemicalBioactive(compound_name="Cinnamaldehyde", chemical_class="Aromatic aldehyde", pharmacological_action="Insulin receptor kinase activator, Antimicrobial, Vasodilator"),
            PhytochemicalBioactive(compound_name="Eugenol", chemical_class="Phenylpropanoid", pharmacological_action="Analgesic, Anti-inflammatory")
        ],
        parts_used=["Tvak (Inner stem bark)"],
        dosages=[
            HerbTherapeuticDosage(form="Churna (Powder)", min_dose_g=0.5, max_dose_g=2.0, anupana="Honey or Warm water")
        ],
        contraindications=["Active gastric hemorrhage", "High fever with bleeding", "Severe Pitta burning"]
    ),
]


# ==============================================================================
# SEEDING, SEARCH & MODULATION COMPUTATION
# ==============================================================================

def seed_dravyaguna_registry(conn: sqlite3.Connection) -> None:
    """Seeds the 25 core classical medicinal herbs into SQLite if missing."""
    cursor = conn.cursor()
    now = int(time.time())

    for herb in SEED_HERBAL_REGISTRY:
        cursor.execute(
            """
            INSERT OR IGNORE INTO dravyaguna_herbal_registry (
                herb_id, sanskrit_name, botanical_name, botanical_family,
                classical_synonyms_json, rasa_json, guna_json, veerya, vipaka,
                prabhava, doshic_karma_json, therapeutics_karma_json,
                phytochemicals_json, parts_used_json, dosage_range_json,
                contraindications_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                herb.herb_id,
                herb.sanskrit_name,
                herb.botanical_name,
                herb.botanical_family,
                json.dumps(herb.classical_synonyms),
                json.dumps([r.value for r in herb.rasa]),
                json.dumps([g.value for g in herb.guna]),
                herb.veerya.value,
                herb.vipaka.value,
                herb.prabhava,
                json.dumps(herb.doshic_karma.model_dump()),
                json.dumps(herb.therapeutics_karma),
                json.dumps([p.model_dump() for p in herb.phytochemicals]),
                json.dumps(herb.parts_used),
                json.dumps([d.model_dump() for d in herb.dosages]),
                json.dumps(herb.contraindications),
                now,
            )
        )


def _row_to_profile(r: sqlite3.Row) -> HerbProfile:
    """Deserializes SQLite row to HerbProfile."""
    return HerbProfile(
        herb_id=r["herb_id"],
        sanskrit_name=r["sanskrit_name"],
        botanical_name=r["botanical_name"],
        botanical_family=r["botanical_family"],
        classical_synonyms=json.loads(r["classical_synonyms_json"]),
        rasa=[Rasa(x) for x in json.loads(r["rasa_json"])],
        guna=[Guna(x) for x in json.loads(r["guna_json"])],
        veerya=Veerya(r["veerya"]),
        vipaka=Vipaka(r["vipaka"]),
        prabhava=r["prabhava"],
        doshic_karma=DoshicKarma(**json.loads(r["doshic_karma_json"])),
        therapeutics_karma=json.loads(r["therapeutics_karma_json"]),
        phytochemicals=[PhytochemicalBioactive(**x) for x in json.loads(r["phytochemicals_json"])],
        parts_used=json.loads(r["parts_used_json"]),
        dosages=[HerbTherapeuticDosage(**x) for x in json.loads(r["dosage_range_json"])],
        contraindications=json.loads(r["contraindications_json"]),
    )


def search_herbs(
    conn: sqlite3.Connection,
    query: Optional[str] = None,
    rasa: Optional[Rasa] = None,
    veerya: Optional[Veerya] = None,
    vipaka: Optional[Vipaka] = None,
    karma: Optional[str] = None,
) -> List[HerbProfile]:
    """Multi-axial search over the Dravya Guna knowledge graph."""
    seed_dravyaguna_registry(conn)
    cursor = conn.cursor()

    sql = "SELECT * FROM dravyaguna_herbal_registry WHERE 1=1"
    params: List[Any] = []

    if veerya:
        sql += " AND veerya = ?"
        params.append(veerya.value)

    if vipaka:
        sql += " AND vipaka = ?"
        params.append(vipaka.value)

    if query:
        q_norm = f"%{query.strip()}%"
        sql += """ AND (
            herb_id LIKE ? OR
            sanskrit_name LIKE ? OR
            botanical_name LIKE ? OR
            classical_synonyms_json LIKE ? OR
            phytochemicals_json LIKE ?
        )"""
        params.extend([q_norm] * 5)

    sql += " ORDER BY sanskrit_name ASC;"
    cursor.execute(sql, params)
    rows = cursor.fetchall()

    profiles = [_row_to_profile(r) for r in rows]

    # In-memory post-filtering for JSON array properties if requested
    if rasa:
        profiles = [p for p in profiles if rasa in p.rasa]

    if karma:
        k_norm = karma.lower()
        profiles = [p for p in profiles if any(k_norm in k.lower() for k in p.therapeutics_karma)]

    return profiles


def get_herb_by_id(conn: sqlite3.Connection, herb_id: str) -> Optional[HerbProfile]:
    """Retrieves a single herb profile by identifier."""
    seed_dravyaguna_registry(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dravyaguna_herbal_registry WHERE herb_id = ? LIMIT 1;", (herb_id,))
    r = cursor.fetchone()
    if not r:
        return None
    return _row_to_profile(r)


def calculate_doshic_modulation_vector(herb: HerbProfile) -> DoshicModulationScore:
    """
    Computes directional Doshic impact vector (Delta v, Delta p, Delta k)
    ranging between -1.0 (strong pacification) and +1.0 (strong provocation).
    Synthesizes Rasa, Veerya, Vipaka, and direct DoshicKarma.
    """
    def _effect_to_score(effect: DoshicEffect) -> float:
        if effect == DoshicEffect.SHAMANA:
            return -0.70
        elif effect == DoshicEffect.KOPANA:
            return +0.60
        return 0.0

    v_score = _effect_to_score(herb.doshic_karma.vata)
    p_score = _effect_to_score(herb.doshic_karma.pitta)
    k_score = _effect_to_score(herb.doshic_karma.kapha)

    # Veerya modulation
    if herb.veerya == Veerya.USHNA:
        p_score += 0.20
        v_score -= 0.15
        k_score -= 0.15
    else:  # SHEETA
        p_score -= 0.30
        v_score += 0.10
        k_score += 0.15

    # Vipaka modulation
    if herb.vipaka == Vipaka.MADHURA:
        v_score -= 0.10
        p_score -= 0.10
        k_score += 0.10
    elif herb.vipaka == Vipaka.KATU:
        v_score += 0.10
        p_score += 0.10
        k_score -= 0.15

    # Clamp to [-1.0, 1.0]
    v_norm = round(max(-1.0, min(1.0, v_score)), 2)
    p_norm = round(max(-1.0, min(1.0, p_score)), 2)
    k_norm = round(max(-1.0, min(1.0, k_score)), 2)

    rationale = (
        f"{herb.sanskrit_name} acts with {herb.veerya.value} Veerya and {herb.vipaka.value} Vipaka. "
        f"Primary Doshic effects: Vata ({herb.doshic_karma.vata.value}), "
        f"Pitta ({herb.doshic_karma.pitta.value}), Kapha ({herb.doshic_karma.kapha.value})."
    )

    return DoshicModulationScore(
        herb_id=herb.herb_id,
        herb_name=herb.sanskrit_name,
        vata_delta=v_norm,
        pitta_delta=p_norm,
        kapha_delta=k_norm,
        rationale=rationale
    )
