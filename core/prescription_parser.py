"""
core/prescription_parser.py - Clinical Prescription Shorthand, Dosage Form (Kalpana),
and Regional Herb/Tree Vernacular Resolution Engine.
===================================================================================
Solves:
1. Decoding Latin and hospital clinical frequency abbreviations (OD, BD, TDS, QID, HS, AC, PC, SOS).
2. Normalizing Ayurvedic dosage forms (Kw., Ch., Vati, Ghr., Tail., Av., Asv., Ar.) to KalpanaForm.
3. Multi-lingual vernacular medicine tree / plant synonym crosswalk (Hindi, Bengali, Tamil, Telugu, Malayalam, Marathi, Kannada, Gujarati).
4. Automatic Schedule E-1 statutory poison tagging for toxic botanicals identified through vernacular names.
5. Structured entity parsing from doctors' unstructured written text.
"""

from __future__ import annotations
import re
from typing import List, Optional, Dict, Any, Tuple
from models.bhaishajya_kalpana import KalpanaForm
from models.prescription_parser import (
    AushadhaSevanaKala,
    ClinicalFrequency,
    ParsedPrescriptionItem,
    PrescriptionTextParseRequest,
    PrescriptionTextParseResponse,
    VernacularHerbMatch,
)

# ==============================================================================
# 1. REGIONAL VERNACULAR HERB & MEDICINE TREE KNOWLEDGE GRAPH
# ==============================================================================

MEDICINE_TREE_VERNACULAR_REGISTRY: List[Dict[str, Any]] = [
    {
        "canonical_sanskrit": "Arjuna",
        "botanical_binomial": "Terminalia arjuna (Roxb. ex DC.) Wight & Arn.",
        "botanical_family": "Combretaceae",
        "is_schedule_e1": False,
        "aliases": [
            ("arjuna", "Sanskrit"),
            ("arjun", "Hindi / Bengali"),
            ("kahu", "Hindi / Punjabi"),
            ("marudhamaram", "Tamil"),
            ("marudhu", "Malayalam"),
            ("thella maddi", "Telugu"),
            ("maddi", "Telugu"),
            ("neer maruthu", "Malayalam"),
            ("sadado", "Gujarati"),
            ("sadada", "Marathi"),
            ("arjan", "Punjabi"),
            ("bili matthi", "Kannada"),
        ]
    },
    {
        "canonical_sanskrit": "Ashwagandha",
        "botanical_binomial": "Withania somnifera (L.) Dunal",
        "botanical_family": "Solanaceae",
        "is_schedule_e1": False,
        "aliases": [
            ("ashwagandha", "Sanskrit"),
            ("asgandh", "Hindi / Urdu"),
            ("asgand", "Hindi"),
            ("ashvagandha", "Bengali"),
            ("amukkara", "Tamil"),
            ("amukkuram", "Malayalam"),
            ("penneru", "Telugu"),
            ("dommadolu", "Telugu"),
            ("asundha", "Gujarati"),
            ("askandha", "Marathi"),
            ("hiremaddina", "Kannada"),
            ("indian ginseng", "Common English"),
        ]
    },
    {
        "canonical_sanskrit": "Guduchi",
        "botanical_binomial": "Tinospora cordifolia (Willd.) Miers",
        "botanical_family": "Menispermaceae",
        "is_schedule_e1": False,
        "aliases": [
            ("guduchi", "Sanskrit"),
            ("giloy", "Hindi"),
            ("amrita", "Sanskrit / Bengali"),
            ("gulvel", "Marathi"),
            ("galo", "Gujarati"),
            ("seenthil kodi", "Tamil"),
            ("seenthil", "Tamil"),
            ("tippa teega", "Telugu"),
            ("chittamruthu", "Malayalam"),
            ("amrutha balli", "Kannada"),
            ("garo", "Odia"),
            ("heart-leaved moonseed", "Common English"),
        ]
    },
    {
        "canonical_sanskrit": "Haritaki",
        "botanical_binomial": "Terminalia chebula Retz.",
        "botanical_family": "Combretaceae",
        "is_schedule_e1": False,
        "aliases": [
            ("haritaki", "Sanskrit"),
            ("harad", "Hindi"),
            ("harar", "Punjabi / Hindi"),
            ("kadukkai", "Tamil"),
            ("karakkaya", "Telugu"),
            ("katukka", "Malayalam"),
            ("harde", "Gujarati"),
            ("hirda", "Marathi"),
            ("alale kayi", "Kannada"),
            ("harida", "Bengali"),
            ("chebulic myrobalan", "Common English"),
        ]
    },
    {
        "canonical_sanskrit": "Amalaki",
        "botanical_binomial": "Phyllanthus emblica L.",
        "botanical_family": "Phyllanthaceae",
        "is_schedule_e1": False,
        "aliases": [
            ("amalaki", "Sanskrit"),
            ("amla", "Hindi"),
            ("amlaki", "Bengali"),
            ("nellikai", "Tamil / Kannada"),
            ("usirikaya", "Telugu"),
            ("usiri", "Telugu"),
            ("nelli", "Malayalam"),
            ("ambla", "Gujarati"),
            ("avali", "Marathi"),
            ("indian gooseberry", "Common English"),
        ]
    },
    {
        "canonical_sanskrit": "Bibhitaki",
        "botanical_binomial": "Terminalia bellirica (Gaertn.) Roxb.",
        "botanical_family": "Combretaceae",
        "is_schedule_e1": False,
        "aliases": [
            ("bibhitaki", "Sanskrit"),
            ("baheda", "Hindi"),
            ("bahera", "Bengali / Hindi"),
            ("thanikkai", "Tamil"),
            ("thandrakaaya", "Telugu"),
            ("thanni", "Malayalam"),
            ("bahedo", "Gujarati"),
            ("behada", "Marathi"),
            ("tare kayi", "Kannada"),
            ("belleric myrobalan", "Common English"),
        ]
    },
    {
        "canonical_sanskrit": "Nimba",
        "botanical_binomial": "Azadirachta indica A. Juss.",
        "botanical_family": "Meliaceae",
        "is_schedule_e1": False,
        "aliases": [
            ("nimba", "Sanskrit"),
            ("neem", "Hindi / Bengali / English"),
            ("nimb", "Marathi"),
            ("veppamaram", "Tamil"),
            ("veppai", "Tamil"),
            ("vepa chettu", "Telugu"),
            ("vepa", "Telugu"),
            ("veppu", "Malayalam"),
            ("bevu", "Kannada"),
            ("limdo", "Gujarati"),
            ("margosa tree", "Common English"),
        ]
    },
    {
        "canonical_sanskrit": "Bhallataka",
        "botanical_binomial": "Semecarpus anacardium L.f.",
        "botanical_family": "Anacardiaceae",
        "is_schedule_e1": True,  # Schedule E-1 Statutory Poison!
        "aliases": [
            ("bhallataka", "Sanskrit"),
            ("bhilawa", "Hindi"),
            ("bhela", "Bengali"),
            ("serankottai", "Tamil"),
            ("jidi mamidi", "Telugu"),
            ("cherukuru", "Malayalam"),
            ("bhilamu", "Gujarati"),
            ("bibba", "Marathi"),
            ("geru kayi", "Kannada"),
            ("marking nut", "Common English"),
        ]
    },
    {
        "canonical_sanskrit": "Vatsanabha",
        "botanical_binomial": "Aconitum ferox Wall. ex Ser.",
        "botanical_family": "Ranunculaceae",
        "is_schedule_e1": True,  # Schedule E-1 Statutory Poison!
        "aliases": [
            ("vatsanabha", "Sanskrit"),
            ("meetha zahar", "Hindi / Urdu"),
            ("bachnag", "Hindi"),
            ("kathvish", "Bengali"),
            ("vasanabhi", "Tamil / Telugu"),
            ("vatsanabhi", "Malayalam"),
            ("mithavish", "Gujarati"),
            ("bachnak", "Marathi"),
            ("vatsanabhi", "Kannada"),
            ("indian aconite", "Common English"),
            ("monk's hood", "Common English"),
        ]
    },
    {
        "canonical_sanskrit": "Kupilu",
        "botanical_binomial": "Strychnos nux-vomica L.",
        "botanical_family": "Loganiaceae",
        "is_schedule_e1": True,  # Schedule E-1 Statutory Poison!
        "aliases": [
            ("kupilu", "Sanskrit"),
            ("vishatinduka", "Sanskrit"),
            ("kuchla", "Hindi"),
            ("kuchila", "Bengali"),
            ("etti", "Tamil"),
            ("etti maram", "Tamil"),
            ("musti", "Telugu"),
            ("visamushti", "Telugu"),
            ("kanjiram", "Malayalam"),
            ("kajra", "Marathi"),
            ("hemushti", "Kannada"),
            ("nux vomica", "Common English"),
            ("poison nut", "Common English"),
        ]
    },
    {
        "canonical_sanskrit": "Shigru",
        "botanical_binomial": "Moringa oleifera Lam.",
        "botanical_family": "Moringaceae",
        "is_schedule_e1": False,
        "aliases": [
            ("shigru", "Sanskrit"),
            ("sahjan", "Hindi"),
            ("sahjana", "Hindi"),
            ("sojne", "Bengali"),
            ("murungai", "Tamil"),
            ("munaga", "Telugu"),
            ("muringa", "Malayalam"),
            ("saragvo", "Gujarati"),
            ("shevaga", "Marathi"),
            ("nugge kayi", "Kannada"),
            ("drumstick tree", "Common English"),
            ("moringa", "Common English"),
        ]
    },
    {
        "canonical_sanskrit": "Shatavari",
        "botanical_binomial": "Asparagus racemosus Willd.",
        "botanical_family": "Asparagaceae",
        "is_schedule_e1": False,
        "aliases": [
            ("shatavari", "Sanskrit"),
            ("satavar", "Hindi"),
            ("satmuli", "Bengali"),
            ("thanneer vittan", "Tamil"),
            ("pilli pichara", "Telugu"),
            ("shathavali", "Malayalam"),
            ("satavari", "Gujarati"),
            ("shatavari", "Marathi"),
            ("majjige gadde", "Kannada"),
        ]
    },
    {
        "canonical_sanskrit": "Mandukaparni",
        "botanical_binomial": "Centella asiatica (L.) Urb.",
        "botanical_family": "Apiaceae",
        "is_schedule_e1": False,
        "aliases": [
            ("mandukaparni", "Sanskrit"),
            ("gotu kola", "Common / Sinhala"),
            ("thankuni", "Bengali"),
            ("vallarai", "Tamil"),
            ("saraswathi aku", "Telugu"),
            ("muthil", "Malayalam"),
            ("brahmi manduki", "Hindi"),
            ("kudangal", "Malayalam"),
            ("ondelaga", "Kannada"),
            ("brahmabuti", "Hindi"),
        ]
    },
    {
        "canonical_sanskrit": "Brahmi",
        "botanical_binomial": "Bacopa monnieri (L.) Wettst.",
        "botanical_family": "Plantaginaceae",
        "is_schedule_e1": False,
        "aliases": [
            ("brahmi", "Sanskrit / Hindi / Bengali"),
            ("neerbrahmi", "Tamil / Malayalam"),
            ("jalabrahmi", "Hindi / Gujarati"),
            ("sambhrani aku", "Telugu"),
            ("neeru brahmi", "Kannada"),
            ("water hyssop", "Common English"),
        ]
    },
    {
        "canonical_sanskrit": "Tulasi",
        "botanical_binomial": "Ocimum sanctum L. (syn. Ocimum tenuiflorum)",
        "botanical_family": "Lamiaceae",
        "is_schedule_e1": False,
        "aliases": [
            ("tulasi", "Sanskrit / Telugu / Kannada"),
            ("tulsi", "Hindi / Bengali / Marathi"),
            ("thulasi", "Tamil / Malayalam"),
            ("holy basil", "Common English"),
        ]
    },
    {
        "canonical_sanskrit": "Haridra",
        "botanical_binomial": "Curcuma longa L.",
        "botanical_family": "Zingiberaceae",
        "is_schedule_e1": False,
        "aliases": [
            ("haridra", "Sanskrit"),
            ("haldi", "Hindi / Marathi / Gujarati"),
            ("holud", "Bengali"),
            ("manjal", "Tamil / Malayalam"),
            ("pasupu", "Telugu"),
            ("arishina", "Kannada"),
            ("turmeric", "Common English"),
        ]
    },
    {
        "canonical_sanskrit": "Yashtimadhu",
        "botanical_binomial": "Glycyrrhiza glabra L.",
        "botanical_family": "Fabaceae",
        "is_schedule_e1": False,
        "aliases": [
            ("yashtimadhu", "Sanskrit"),
            ("mulethi", "Hindi"),
            ("jethimadh", "Gujarati / Marathi"),
            ("joshthimadhu", "Bengali"),
            ("athimadhuram", "Tamil / Malayalam / Telugu"),
            ("yashtimadhuka", "Kannada"),
            ("licorice", "Common English"),
            ("liquorice", "Common English"),
        ]
    },
    {
        "canonical_sanskrit": "Guggulu",
        "botanical_binomial": "Commiphora mukul (Stocks) Hook.",
        "botanical_family": "Burseraceae",
        "is_schedule_e1": False,
        "aliases": [
            ("guggulu", "Sanskrit"),
            ("guggul", "Hindi / Bengali / Marathi"),
            ("guggal", "Punjabi"),
            ("gukkulu", "Tamil"),
            ("guggilam", "Telugu"),
            ("guggulu", "Malayalam / Kannada"),
            ("indian bdellium", "Common English"),
        ]
    },
]

# Quick lookup index for vernacular aliases
_VERNACULAR_ALIAS_MAP: Dict[str, Dict[str, Any]] = {}
for entry in MEDICINE_TREE_VERNACULAR_REGISTRY:
    for alias, lang in entry["aliases"]:
        norm_alias = alias.strip().lower()
        _VERNACULAR_ALIAS_MAP[norm_alias] = {
            "canonical_sanskrit": entry["canonical_sanskrit"],
            "botanical_binomial": entry["botanical_binomial"],
            "botanical_family": entry["botanical_family"],
            "is_schedule_e1": entry["is_schedule_e1"],
            "matched_vernacular_language": lang,
            "regional_common_name": alias.title(),
        }


def resolve_vernacular_herb_or_tree(query: str) -> Optional[VernacularHerbMatch]:
    """
    Resolves local Indian vernacular plant/tree names or trade synonyms to canonical
    Ayurvedic Sanskrit and Botanical Latin taxonomies.
    """
    if not query:
        return None
    cleaned = query.strip().lower()

    # Exact alias match
    if cleaned in _VERNACULAR_ALIAS_MAP:
        rec = _VERNACULAR_ALIAS_MAP[cleaned]
        return VernacularHerbMatch(
            matched_query=query,
            canonical_sanskrit=rec["canonical_sanskrit"],
            botanical_binomial=rec["botanical_binomial"],
            botanical_family=rec["botanical_family"],
            matched_vernacular_language=rec["matched_vernacular_language"],
            regional_common_name=rec["regional_common_name"],
            is_schedule_e1_poison=rec["is_schedule_e1"],
            confidence_score=1.0,
        )

    # Substring / partial match
    for alias, rec in _VERNACULAR_ALIAS_MAP.items():
        if alias in cleaned or cleaned in alias:
            # Avoid trivial matches under 4 chars unless exact
            if len(alias) >= 4 or alias == cleaned:
                return VernacularHerbMatch(
                    matched_query=query,
                    canonical_sanskrit=rec["canonical_sanskrit"],
                    botanical_binomial=rec["botanical_binomial"],
                    botanical_family=rec["botanical_family"],
                    matched_vernacular_language=rec["matched_vernacular_language"],
                    regional_common_name=rec["regional_common_name"],
                    is_schedule_e1_poison=rec["is_schedule_e1"],
                    confidence_score=0.90,
                )
    return None


# ==============================================================================
# 2. DOSAGE FORM (KALPANA) ABBREVIATION DICTIONARY
# ==============================================================================

DOSAGE_FORM_PATTERNS: List[Tuple[str, KalpanaForm, str]] = [
    (r"\b(kwath|kwatha|kw\b|kashayam|kashaya|kash\b|decoction)\b", KalpanaForm.KWATHA, "kw"),
    (r"\b(churna|churnam|chur\b|ch\b|powder|pwd\b)\b", KalpanaForm.CHURNA, "ch"),
    (r"\b(vati|bati|gutika|tab\b|tablet|tablets|pill|pills)\b", KalpanaForm.VATI, "tab"),
    (r"\b(avaleha|lehyam|lehya|avl\b|av\b|electuary|herbal jam)\b", KalpanaForm.AVALEHA, "av"),
    (r"\b(ghrita|ghee|ghr\b|gulam)\b", KalpanaForm.GHRITA, "ghr"),
    (r"\b(taila|tailam|thailam|thaila|tail\b|medicated oil|oil)\b", KalpanaForm.TAILA, "tail"),
    (r"\b(asava|arishta|arishtam|asv\b|ar\b|fermented liquid|syrup|syr\b)\b", KalpanaForm.ASAVA_ARISHTA, "asv"),
    (r"\b(guggulu|guggul|gugg\b)\b", KalpanaForm.GUGGULU, "gugg"),
    (r"\b(svarasa|swarasa|fresh juice|juice)\b", KalpanaForm.SVARASA, "svarasa"),
    (r"\b(kalka|paste|bolus)\b", KalpanaForm.KALKA, "kalka"),
    (r"\b(hima|cold infusion)\b", KalpanaForm.HIMA, "hima"),
    (r"\b(phanta|hot infusion)\b", KalpanaForm.PHANTA, "phanta"),
]

def normalize_dosage_form(text: str) -> Tuple[Optional[KalpanaForm], Optional[str]]:
    """Identifies and normalizes raw dosage form abbreviations to KalpanaForm."""
    lower = text.lower()
    for pattern, kalpana, raw_abbr in DOSAGE_FORM_PATTERNS:
        if re.search(pattern, lower):
            return kalpana, raw_abbr
    return None, None


# ==============================================================================
# 3. CLINICAL FREQUENCY & TIMING SHORTHAND PARSER
# ==============================================================================

FREQUENCY_PATTERNS: List[Tuple[str, ClinicalFrequency]] = [
    (r"\b(q\.?i\.?d\.?|4\s*times|four\s*times|qid)\b", ClinicalFrequency.QID),
    (r"\b(t\.?d\.?s\.?|t\.?i\.?d\.?|3\s*times|thrice|tds|tid)\b", ClinicalFrequency.TDS),
    (r"\b(b\.?d\.?|b\.?i\.?d\.?|2\s*times|twice|bd|bid)\b", ClinicalFrequency.BD),
    (r"\b(o\.?d\.?|q\.?d\.?|1\s*time|once\s*daily|once|od|qd)\b", ClinicalFrequency.OD),
    (r"\b(h\.?s\.?|q\.?h\.?s\.?|bedtime|at\s*night|night|hs)\b", ClinicalFrequency.HS),
    (r"\b(s\.?o\.?s\.?|p\.?r\.?n\.?|as\s*needed|when\s*required|sos|prn)\b", ClinicalFrequency.SOS),
    (r"\b(stat|immediately)\b", ClinicalFrequency.STAT),
    (r"\b(mane|morning)\b", ClinicalFrequency.MANE),
    (r"\b(vesper|sayam|evening)\b", ClinicalFrequency.VESPER),
]

TIMING_PATTERNS: List[Tuple[str, AushadhaSevanaKala]] = [
    (r"\b(a\.?c\.?|before\s*food|before\s*meals|bbf|empty\s*stomach|pragbhakta)\b", AushadhaSevanaKala.PRAGBHAKTA),
    (r"\b(p\.?c\.?|after\s*food|after\s*meals|adhobhakta)\b", AushadhaSevanaKala.ADHOBHAKTA),
    (r"\b(c\.?c\.?|with\s*food|mid\s*meal|madhyabhakta)\b", AushadhaSevanaKala.MADHYABHAKTA),
    (r"\b(at\s*bedtime|before\s*sleep|nishi|shayana)\b", AushadhaSevanaKala.NISHI),
    (r"\b(frequently|every\s*hour|muhurmuhuh)\b", AushadhaSevanaKala.MUHURMUHUH),
]

ANUPANA_PATTERNS: List[Tuple[str, str]] = [
    (r"\b(warm\s*water|ushna\s*jala|garam\s*pani|hot\s*water)\b", "Warm water (Ushna Jala)"),
    (r"\b(honey|madhu|shahad)\b", "Honey (Madhu)"),
    (r"\b(milk|godugdha|dudh|warm\s*milk)\b", "Warm Cow Milk (Godugdha)"),
    (r"\b(ghee|goghrita|cow\s*ghee)\b", "Cow Ghee (Goghrita)"),
    (r"\b(buttermilk|takra|chhaachh|mattha)\b", "Medicated Buttermilk (Takra)"),
    (r"\b(equal\s*water|sama\s*jala)\b", "Equal quantity warm water"),
    (r"\b(water|jala|pani)\b", "Water (Jala)"),
]


# ==============================================================================
# 4. PRESCRIPTION LINE & FULL TEXT PARSER ENGINE
# ==============================================================================

def parse_prescription_line(raw_line: str) -> ParsedPrescriptionItem:
    """
    Parses a single unstructured line of clinical prescription shorthand,
    extracting formulation, dosage form, dose, frequency, timing, and carrier.
    """
    line = raw_line.strip()
    if not line:
        return ParsedPrescriptionItem(raw_line=raw_line, formulation_name="EMPTY")

    # 1. Dosage form normalization
    form, raw_form = normalize_dosage_form(line)

    # 2. Clinical frequency extraction
    frequency: Optional[ClinicalFrequency] = None
    for pattern, freq in FREQUENCY_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            frequency = freq
            break

    # 3. Administration timing extraction
    timing: Optional[AushadhaSevanaKala] = None
    for pattern, t_val in TIMING_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            timing = t_val
            break

    # If HS (Hora Somni) was specified, it inherently denotes Nishi (bedtime) administration timing
    if frequency == ClinicalFrequency.HS and timing is None:
        timing = AushadhaSevanaKala.NISHI

    # 4. Anupana / carrier vehicle extraction
    anupana: Optional[str] = None
    for pattern, vehicle in ANUPANA_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            anupana = vehicle
            break

    # 5. Dose amount extraction (e.g. "2 tab", "500 mg", "15 ml", "3 g", "2 tsp")
    dose_match = re.search(
        r"(\d+(?:\.\d+)?\s*(?:mg|g|gm|ml|tsp|tbsp|drops|tablets?|tabs?|caps?|capsules?|ratti|bindu))",
        line,
        re.IGNORECASE
    )
    dose_amount = dose_match.group(1) if dose_match else None

    # 6. Duration extraction (e.g. "x 15 days", "for 1 month", "10 days")
    dur_match = re.search(
        r"(?:x\s*|for\s*)?(\d+\s*(?:days?|weeks?|months?|d|w|m))\b",
        line,
        re.IGNORECASE
    )
    duration = dur_match.group(1) if dur_match else None

    # 7. Isolate drug / herb formulation name candidate
    # Strip detected dose, frequency, timing, anupana tokens to get the clean formulation name
    stripped = line
    # Remove leading form like "Tab. ", "Kw. "
    stripped = re.sub(r"^(?:tab\b|cap\b|kw\b|ch\b|syr\b|av\b|ghr\b|tail\b|bhasm\b)\.?\s*", "", stripped, flags=re.IGNORECASE)
    # Remove dosage numbers
    if dose_amount:
        stripped = stripped.replace(dose_amount, "")
    # Remove frequency
    for pattern, _ in FREQUENCY_PATTERNS:
        stripped = re.sub(pattern, "", stripped, flags=re.IGNORECASE)
    # Remove timing
    for pattern, _ in TIMING_PATTERNS:
        stripped = re.sub(pattern, "", stripped, flags=re.IGNORECASE)
    # Remove "with ...", "for ..."
    stripped = re.sub(r"\b(with|anupana|along\s*with)\b.*$", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\b(x\s*\d+.*|for\s*\d+.*)$", "", stripped, flags=re.IGNORECASE)
    cleaned_name = re.sub(r"[^\w\s\-\.]", " ", stripped).strip()
    # Normalize multiple whitespace
    cleaned_name = re.sub(r"\s+", " ", cleaned_name)

    # 8. Resolve against vernacular plant/tree registry
    matched_herb = resolve_vernacular_herb_or_tree(cleaned_name)

    # Check for statutory Schedule E-1 alerts
    sched_e1 = False
    if matched_herb and matched_herb.is_schedule_e1_poison:
        sched_e1 = True
    elif any(p in line.upper() for p in ["VATSANABHA", "BHALLATAKA", "KUPILU", "KUCHLA", "BHILAWA", "BACHNAG"]):
        sched_e1 = True

    return ParsedPrescriptionItem(
        raw_line=raw_line,
        formulation_name=cleaned_name or line,
        matched_herb=matched_herb,
        dosage_form=form,
        dosage_form_raw=raw_form,
        dose_amount=dose_amount,
        frequency=frequency,
        administration_timing=timing,
        anupana_carrier=anupana,
        duration=duration,
        schedule_e1_alert=sched_e1,
    )


def parse_prescription_text(text: str) -> PrescriptionTextParseResponse:
    """
    Parses a multi-line doctor's clinical prescription text, normalizing all
    items, resolving vernacular tree/plant names, and flagging toxic substances.
    """
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    items: List[ParsedPrescriptionItem] = []
    sched_e1_alerts: List[str] = []
    unrecognized: List[str] = []

    for line in lines:
        # Skip header/footer lines if they look like doctor metadata
        if any(hdr in line.upper() for hdr in ["RX", "PRESCRIPTION", "PATIENT NAME", "AGE/GENDER", "DATE:"]):
            continue

        item = parse_prescription_line(line)
        if item.formulation_name != "EMPTY":
            items.append(item)
            if item.schedule_e1_alert:
                name = item.matched_herb.canonical_sanskrit if item.matched_herb else item.formulation_name
                sched_e1_alerts.append(f"{name} (Statutory Schedule E-1 Poison - Shodhana & 2-Physician Verification Mandatory)")
            if not item.matched_herb and not item.dosage_form:
                unrecognized.append(item.formulation_name)

    return PrescriptionTextParseResponse(
        total_lines_processed=len(items),
        items_extracted=items,
        schedule_e1_items_detected=sched_e1_alerts,
        unrecognized_tokens=unrecognized,
        requires_rmp_verification=True,
        governance_status="DRAFT_PARSED_PRESCRIPTION"
    )
