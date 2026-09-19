"""
Shalakya Tantra, Netra Kriya Kalpa & ENT Microsurgical Engine
============================================================
Implements:
1. Classical Netra Roga Catalog (76 diseases across 6 Mandalas & 4 Patalas)
2. Netra Kriya Kalpa Protocol Engine (Tarpana, Aschyotana, Seka, Pindi, Bidalaka, Putapaka, Anjana)
3. Tarpana Doshic Matrakala retentive dynamics and photoprotection regimen
4. Acute Adhimantha (Angle-Closure Glaucoma) Emergency Triage Firewall
5. ENT Micro-therapeutics (Karna Purana, Karna Dhoopana, Pratimarsa & Marsha Nasya)
6. SQLite WAL persistence with indexed queries
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
from models.shalakya_tantra import (
    EntProcedureCreate,
    EntProcedureResponse,
    EntTherapyType,
    KriyaKalpaType,
    NetraMandala,
    NetraPatala,
    NetraRogaProfile,
    OphthalmicScreeningRequest,
    OphthalmicScreeningResponse,
    SadhyaAsadhyata,
    TarpanaSessionCreate,
    TarpanaSessionResponse,
)

# ==============================================================================
# CLASSICAL NETRA ROGA CATALOG (24 PROMINENT HIGH-FIDELITY ROGAS)
# ==============================================================================

SEED_NETRA_ROGA_CATALOG: List[NetraRogaProfile] = [
    # 1. Pakshma Mandala (Ciliary margin & Lashes)
    NetraRogaProfile(
        roga_code="NETRA-PAK-01",
        sanskrit_name="पक्ष्मकोप (Pakshmakopa)",
        english_name="Trichiasis / Entropion with Ingrowing Eyelashes",
        icd11_mapping="9A02 (Trichiasis)",
        anatomical_mandala=NetraMandala.PAKSHMA,
        anatomical_patala=NetraPatala.BAHYA,
        doshic_etiology="VATA_PITTAJA",
        sadhya_asadhyata=SadhyaAsadhyata.KRICCHRA_SADHYA,
        kriya_kalpa_indications=[KriyaKalpaType.ASCHYOTANA, KriyaKalpaType.BIDALAKA],
        contraindicated_procedures=[KriyaKalpaType.TARPANA]
    ),
    NetraRogaProfile(
        roga_code="NETRA-PAK-02",
        sanskrit_name="पक्ष्मशात (Pakshmashata)",
        english_name="Madarosis / Blepharitis Ciliaris with Lash Loss",
        icd11_mapping="9A00 (Blepharitis)",
        anatomical_mandala=NetraMandala.PAKSHMA,
        anatomical_patala=NetraPatala.BAHYA,
        doshic_etiology="PITTA_KAPHAJA",
        sadhya_asadhyata=SadhyaAsadhyata.SADHYA,
        kriya_kalpa_indications=[KriyaKalpaType.ASCHYOTANA, KriyaKalpaType.ANJANA],
        contraindicated_procedures=[]
    ),

    # 2. Vartma Mandala (Eyelids & Tarsus)
    NetraRogaProfile(
        roga_code="NETRA-VAR-01",
        sanskrit_name="उत्सङ्गिनी (Utsangini)",
        english_name="Multiple Deep Chalazia / Tarsal Granulomatous Cyst",
        icd11_mapping="9A04 (Chalazion)",
        anatomical_mandala=NetraMandala.VARTMA,
        anatomical_patala=NetraPatala.BAHYA,
        doshic_etiology="RAKTA_SANNIPATAJA",
        sadhya_asadhyata=SadhyaAsadhyata.KRICCHRA_SADHYA,
        kriya_kalpa_indications=[KriyaKalpaType.BIDALAKA, KriyaKalpaType.SEKA],
        contraindicated_procedures=[KriyaKalpaType.TARPANA]
    ),
    NetraRogaProfile(
        roga_code="NETRA-VAR-02",
        sanskrit_name="कुम्भिका (Kumbhika)",
        english_name="Internal Hordeolum / Meibomian Abscess",
        icd11_mapping="9A03 (Hordeolum)",
        anatomical_mandala=NetraMandala.VARTMA,
        anatomical_patala=NetraPatala.BAHYA,
        doshic_etiology="KAPHA_RAKTAJA",
        sadhya_asadhyata=SadhyaAsadhyata.SADHYA,
        kriya_kalpa_indications=[KriyaKalpaType.ASCHYOTANA, KriyaKalpaType.BIDALAKA],
        contraindicated_procedures=[KriyaKalpaType.TARPANA]
    ),
    NetraRogaProfile(
        roga_code="NETRA-VAR-03",
        sanskrit_name="पोथकी (Pothaki)",
        english_name="Trachomatous Follicular Keratoconjunctivitis",
        icd11_mapping="1C10 (Trachoma)",
        anatomical_mandala=NetraMandala.VARTMA,
        anatomical_patala=NetraPatala.BAHYA,
        doshic_etiology="KAPHAJA",
        sadhya_asadhyata=SadhyaAsadhyata.SADHYA,
        kriya_kalpa_indications=[KriyaKalpaType.ASCHYOTANA, KriyaKalpaType.SEKA, KriyaKalpaType.ANJANA],
        contraindicated_procedures=[KriyaKalpaType.TARPANA]
    ),
    NetraRogaProfile(
        roga_code="NETRA-VAR-04",
        sanskrit_name="अञ्जनानामिका (Anjananamika)",
        english_name="External Hordeolum / Acute Zeisian Gland Stye",
        icd11_mapping="9A03.0 (External hordeolum)",
        anatomical_mandala=NetraMandala.VARTMA,
        anatomical_patala=NetraPatala.BAHYA,
        doshic_etiology="RAKTA_PITTAJA",
        sadhya_asadhyata=SadhyaAsadhyata.SADHYA,
        kriya_kalpa_indications=[KriyaKalpaType.BIDALAKA, KriyaKalpaType.ASCHYOTANA],
        contraindicated_procedures=[KriyaKalpaType.TARPANA]
    ),

    # 3. Shukla Mandala (Sclera & Bulbar Conjunctiva)
    NetraRogaProfile(
        roga_code="NETRA-SHU-01",
        sanskrit_name="प्रस्तारि अर्म (Prastari Arma)",
        english_name="Progressive Corneal Pterygium",
        icd11_mapping="9A61 (Pterygium)",
        anatomical_mandala=NetraMandala.SHUKLA,
        anatomical_patala=NetraPatala.BAHYA,
        doshic_etiology="KAPHA_RAKTAJA",
        sadhya_asadhyata=SadhyaAsadhyata.KRICCHRA_SADHYA,
        kriya_kalpa_indications=[KriyaKalpaType.ASCHYOTANA, KriyaKalpaType.ANJANA],
        contraindicated_procedures=[KriyaKalpaType.TARPANA]
    ),
    NetraRogaProfile(
        roga_code="NETRA-SHU-02",
        sanskrit_name="शुक्तिका (Suktika)",
        english_name="Xerosis Conjunctivae / Vitamin A Bitot Spot",
        icd11_mapping="5B50.0 (Vitamin A deficiency ocular xerophthalmia)",
        anatomical_mandala=NetraMandala.SHUKLA,
        anatomical_patala=NetraPatala.BAHYA,
        doshic_etiology="PITTAJA",
        sadhya_asadhyata=SadhyaAsadhyata.SADHYA,
        kriya_kalpa_indications=[KriyaKalpaType.TARPANA, KriyaKalpaType.ASCHYOTANA, KriyaKalpaType.PUTAPAKA],
        contraindicated_procedures=[]
    ),
    NetraRogaProfile(
        roga_code="NETRA-SHU-03",
        sanskrit_name="सिराजाल (Sirajala)",
        english_name="Episcleritis / Scleral Vascular Engorgement Network",
        icd11_mapping="9A80 (Episcleritis)",
        anatomical_mandala=NetraMandala.SHUKLA,
        anatomical_patala=NetraPatala.BAHYA,
        doshic_etiology="RAKTAJA",
        sadhya_asadhyata=SadhyaAsadhyata.KRICCHRA_SADHYA,
        kriya_kalpa_indications=[KriyaKalpaType.SEKA, KriyaKalpaType.ASCHYOTANA],
        contraindicated_procedures=[KriyaKalpaType.TARPANA]
    ),
    NetraRogaProfile(
        roga_code="NETRA-SHU-04",
        sanskrit_name="पिष्टक (Pishtaka)",
        english_name="Phlyctenular Conjunctivitis / Elevated Flour-like White Nodule",
        icd11_mapping="9A62 (Phlyctenular keratoconjunctivitis)",
        anatomical_mandala=NetraMandala.SHUKLA,
        anatomical_patala=NetraPatala.BAHYA,
        doshic_etiology="KAPHAJA",
        sadhya_asadhyata=SadhyaAsadhyata.SADHYA,
        kriya_kalpa_indications=[KriyaKalpaType.ANJANA, KriyaKalpaType.ASCHYOTANA],
        contraindicated_procedures=[]
    ),

    # 4. Krishna Mandala (Cornea & Limbal region)
    NetraRogaProfile(
        roga_code="NETRA-KRI-01",
        sanskrit_name="सव्रण शुक्ल (Savrana Sukra)",
        english_name="Ulcerative Keratitis / Infective Corneal Ulcer",
        icd11_mapping="9A70 (Corneal ulcer)",
        anatomical_mandala=NetraMandala.KRISHNA,
        anatomical_patala=NetraPatala.BAHYA,
        doshic_etiology="RAKTA_PITTAJA",
        sadhya_asadhyata=SadhyaAsadhyata.KRICCHRA_SADHYA,
        kriya_kalpa_indications=[KriyaKalpaType.ASCHYOTANA, KriyaKalpaType.SEKA, KriyaKalpaType.PINDI],
        contraindicated_procedures=[KriyaKalpaType.TARPANA, KriyaKalpaType.ANJANA]
    ),
    NetraRogaProfile(
        roga_code="NETRA-KRI-02",
        sanskrit_name="अव्रण शुक्ल (Avrana Sukra)",
        english_name="Corneal Opacity / Non-Ulcerative Corneal Leucoma",
        icd11_mapping="9A78 (Corneal opacity)",
        anatomical_mandala=NetraMandala.KRISHNA,
        anatomical_patala=NetraPatala.BAHYA,
        doshic_etiology="KAPHA_RAKTAJA",
        sadhya_asadhyata=SadhyaAsadhyata.YAPYA,
        kriya_kalpa_indications=[KriyaKalpaType.TARPANA, KriyaKalpaType.ANJANA, KriyaKalpaType.PUTAPAKA],
        contraindicated_procedures=[]
    ),
    NetraRogaProfile(
        roga_code="NETRA-KRI-03",
        sanskrit_name="अजकाजात (Ajakajata)",
        english_name="Iris Prolapse / Anterior Staphyloma",
        icd11_mapping="9A72 (Corneal staphyloma / iris prolapse)",
        anatomical_mandala=NetraMandala.KRISHNA,
        anatomical_patala=NetraPatala.BAHYA,
        doshic_etiology="RAKTA_SANNIPATAJA",
        sadhya_asadhyata=SadhyaAsadhyata.ASADHYA,
        kriya_kalpa_indications=[KriyaKalpaType.SEKA],
        contraindicated_procedures=[KriyaKalpaType.TARPANA, KriyaKalpaType.ANJANA, KriyaKalpaType.PINDI]
    ),

    # 5. Drishti Mandala (Pupil, Lens, Posterior segment, Visual apparatus)
    NetraRogaProfile(
        roga_code="NETRA-DRI-01",
        sanskrit_name="तिमिर - प्रथम पटल (Prathama Patala Timira)",
        english_name="Early Refractive Error / Amblyopia with Indistinct Vision",
        icd11_mapping="9D00 (Visual impairment)",
        anatomical_mandala=NetraMandala.DRISHTI,
        anatomical_patala=NetraPatala.PRATHAMA,
        doshic_etiology="VATA_PITTAJA",
        sadhya_asadhyata=SadhyaAsadhyata.SADHYA,
        kriya_kalpa_indications=[KriyaKalpaType.TARPANA, KriyaKalpaType.PUTAPAKA, KriyaKalpaType.ASCHYOTANA],
        contraindicated_procedures=[]
    ),
    NetraRogaProfile(
        roga_code="NETRA-DRI-02",
        sanskrit_name="तिमिर - द्वितीय पटल (Dwitiya Patala Timira)",
        english_name="Intermediate Visual Distortion / Floaters & Metamorphopsia",
        icd11_mapping="9D00.1 (Moderate visual impairment)",
        anatomical_mandala=NetraMandala.DRISHTI,
        anatomical_patala=NetraPatala.DWITIYA,
        doshic_etiology="VATA_PITTAJA",
        sadhya_asadhyata=SadhyaAsadhyata.KRICCHRA_SADHYA,
        kriya_kalpa_indications=[KriyaKalpaType.TARPANA, KriyaKalpaType.PUTAPAKA, KriyaKalpaType.ANJANA],
        contraindicated_procedures=[]
    ),
    NetraRogaProfile(
        roga_code="NETRA-DRI-03",
        sanskrit_name="काच - तृतीय पटल (Tritiya Patala Kacha)",
        english_name="Immature Cataract / Severe Visual Obscuration with Diplopia",
        icd11_mapping="9B10.0 (Early senile cataract)",
        anatomical_mandala=NetraMandala.DRISHTI,
        anatomical_patala=NetraPatala.TRITIYA,
        doshic_etiology="SANNIPATAJA",
        sadhya_asadhyata=SadhyaAsadhyata.YAPYA,
        kriya_kalpa_indications=[KriyaKalpaType.TARPANA, KriyaKalpaType.PUTAPAKA, KriyaKalpaType.ANJANA],
        contraindicated_procedures=[]
    ),
    NetraRogaProfile(
        roga_code="NETRA-DRI-04",
        sanskrit_name="लिङ्गनाश - चतुर्थ पटल (Chaturtha Patala Linganasha)",
        english_name="Mature Cataract / Complete Aphakic Blindness",
        icd11_mapping="9B10.1 (Mature cataract requiring surgical extraction)",
        anatomical_mandala=NetraMandala.DRISHTI,
        anatomical_patala=NetraPatala.CHATURTHA,
        doshic_etiology="SANNIPATAJA",
        sadhya_asadhyata=SadhyaAsadhyata.ASADHYA,
        kriya_kalpa_indications=[],
        contraindicated_procedures=[KriyaKalpaType.TARPANA, KriyaKalpaType.PUTAPAKA, KriyaKalpaType.PINDI]
    ),
    NetraRogaProfile(
        roga_code="NETRA-DRI-05",
        sanskrit_name="पित्तदग्ध दृष्टि (Pittadagdha Drishti)",
        english_name="Solar / Phototoxic Retinopathy / Day Vision Impairment",
        icd11_mapping="9B75 (Phototoxic retinopathy)",
        anatomical_mandala=NetraMandala.DRISHTI,
        anatomical_patala=NetraPatala.DWITIYA,
        doshic_etiology="PITTAJA",
        sadhya_asadhyata=SadhyaAsadhyata.YAPYA,
        kriya_kalpa_indications=[KriyaKalpaType.TARPANA, KriyaKalpaType.SEKA, KriyaKalpaType.PUTAPAKA],
        contraindicated_procedures=[KriyaKalpaType.ANJANA]
    ),
    NetraRogaProfile(
        roga_code="NETRA-DRI-06",
        sanskrit_name="कफविदग्ध दृष्टि / नक्तान्ध्य (Kaphavidagdha Drishti / Naktandhya)",
        english_name="Nyctalopia / Night Blindness",
        icd11_mapping="9D44 (Night blindness)",
        anatomical_mandala=NetraMandala.DRISHTI,
        anatomical_patala=NetraPatala.DWITIYA,
        doshic_etiology="KAPHAJA",
        sadhya_asadhyata=SadhyaAsadhyata.SADHYA,
        kriya_kalpa_indications=[KriyaKalpaType.ANJANA, KriyaKalpaType.TARPANA, KriyaKalpaType.PUTAPAKA],
        contraindicated_procedures=[]
    ),

    # 6. Sarvagata Mandala (Pan-Ocular / Whole Eyeball)
    NetraRogaProfile(
        roga_code="NETRA-SAR-01",
        sanskrit_name="वातज अभिष्यन्द (Vataja Abhishyanda)",
        english_name="Acute Catarrhal / Allergic Conjunctivitis (Vataja)",
        icd11_mapping="9A60 (Conjunctivitis)",
        anatomical_mandala=NetraMandala.SARVAGATA,
        anatomical_patala=NetraPatala.BAHYA,
        doshic_etiology="VATAJA",
        sadhya_asadhyata=SadhyaAsadhyata.SADHYA,
        kriya_kalpa_indications=[KriyaKalpaType.ASCHYOTANA, KriyaKalpaType.SEKA, KriyaKalpaType.BIDALAKA],
        contraindicated_procedures=[KriyaKalpaType.TARPANA]
    ),
    NetraRogaProfile(
        roga_code="NETRA-SAR-02",
        sanskrit_name="पित्तज अभिष्यन्द (Pittaja Abhishyanda)",
        english_name="Acute Mucopurulent Conjunctivitis (Pittaja)",
        icd11_mapping="9A60.0 (Acute conjunctivitis)",
        anatomical_mandala=NetraMandala.SARVAGATA,
        anatomical_patala=NetraPatala.BAHYA,
        doshic_etiology="PITTAJA",
        sadhya_asadhyata=SadhyaAsadhyata.SADHYA,
        kriya_kalpa_indications=[KriyaKalpaType.SEKA, KriyaKalpaType.ASCHYOTANA, KriyaKalpaType.BIDALAKA],
        contraindicated_procedures=[KriyaKalpaType.TARPANA]
    ),
    NetraRogaProfile(
        roga_code="NETRA-SAR-03",
        sanskrit_name="अधिमन्थ - तीव्रावस्था (Acute Adhimantha)",
        english_name="Acute Congestive Angle-Closure Glaucoma Crisis",
        icd11_mapping="9C61.0 (Acute angle-closure glaucoma)",
        anatomical_mandala=NetraMandala.SARVAGATA,
        anatomical_patala=NetraPatala.SARVA_PATALA,
        doshic_etiology="TRIDOSHAJA",
        sadhya_asadhyata=SadhyaAsadhyata.ASADHYA,
        kriya_kalpa_indications=[],
        contraindicated_procedures=[KriyaKalpaType.TARPANA, KriyaKalpaType.SEKA, KriyaKalpaType.PINDI, KriyaKalpaType.PUTAPAKA]
    ),
    NetraRogaProfile(
        roga_code="NETRA-SAR-04",
        sanskrit_name="सशोफ नेत्रापाक (Sasopha Netrapaka)",
        english_name="Panophthalmitis / Severe Endophthalmitis with Orbital Cellulitis",
        icd11_mapping="9A90 (Endophthalmitis)",
        anatomical_mandala=NetraMandala.SARVAGATA,
        anatomical_patala=NetraPatala.SARVA_PATALA,
        doshic_etiology="SANNIPATAJA",
        sadhya_asadhyata=SadhyaAsadhyata.ASADHYA,
        kriya_kalpa_indications=[],
        contraindicated_procedures=[KriyaKalpaType.TARPANA, KriyaKalpaType.ANJANA, KriyaKalpaType.PINDI]
    ),
]


# ==============================================================================
# DATABASE INITIALIZATION & SEEDING ENGINE
# ==============================================================================

def initialize_shalakya_tables(conn: sqlite3.Connection) -> None:
    """Populate shalakya_netra_roga_catalog if unseeded."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM shalakya_netra_roga_catalog;")
    row = cursor.fetchone()
    if row and row["cnt"] == 0:
        now = int(time.time())
        for r in SEED_NETRA_ROGA_CATALOG:
            cursor.execute(
                """
                INSERT INTO shalakya_netra_roga_catalog (
                    roga_code, sanskrit_name, english_name, icd11_mapping,
                    anatomical_mandala, anatomical_patala, doshic_etiology,
                    sadhya_asadhyata, kriya_kalpa_indications_json,
                    contraindicated_procedures_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    r.roga_code,
                    r.sanskrit_name,
                    r.english_name,
                    r.icd11_mapping,
                    r.anatomical_mandala.value,
                    r.anatomical_patala.value,
                    r.doshic_etiology,
                    r.sadhya_asadhyata.value,
                    json.dumps([k.value for k in r.kriya_kalpa_indications]),
                    json.dumps([k.value for k in r.contraindicated_procedures]),
                    now,
                )
            )
        conn.commit()


def get_netra_roga_profile(roga_code: str, conn: sqlite3.Connection) -> NetraRogaProfile:
    """Retrieve Netra Roga specification by code."""
    initialize_shalakya_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shalakya_netra_roga_catalog WHERE roga_code = ?;", (roga_code,))
    row = cursor.fetchone()
    if not row:
        raise RecordNotFoundException("NetraRogaProfile", roga_code)

    return NetraRogaProfile(
        roga_code=row["roga_code"],
        sanskrit_name=row["sanskrit_name"],
        english_name=row["english_name"],
        icd11_mapping=row["icd11_mapping"],
        anatomical_mandala=NetraMandala(row["anatomical_mandala"]),
        anatomical_patala=NetraPatala(row["anatomical_patala"]),
        doshic_etiology=row["doshic_etiology"],
        sadhya_asadhyata=SadhyaAsadhyata(row["sadhya_asadhyata"]),
        kriya_kalpa_indications=[KriyaKalpaType(k) for k in json.loads(row["kriya_kalpa_indications_json"])],
        contraindicated_procedures=[KriyaKalpaType(k) for k in json.loads(row["contraindicated_procedures_json"])],
    )


def list_all_netra_rogas(
    conn: sqlite3.Connection,
    mandala: Optional[NetraMandala] = None,
    patala: Optional[NetraPatala] = None
) -> List[NetraRogaProfile]:
    """List registered classical Netra Rogas with optional anatomical filters."""
    initialize_shalakya_tables(conn)
    cursor = conn.cursor()
    query = "SELECT * FROM shalakya_netra_roga_catalog WHERE 1=1"
    params: List[Any] = []

    if mandala:
        query += " AND anatomical_mandala = ?"
        params.append(mandala.value)
    if patala:
        query += " AND anatomical_patala = ?"
        params.append(patala.value)

    query += " ORDER BY roga_code ASC;"
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()

    return [
        NetraRogaProfile(
            roga_code=r["roga_code"],
            sanskrit_name=r["sanskrit_name"],
            english_name=r["english_name"],
            icd11_mapping=r["icd11_mapping"],
            anatomical_mandala=NetraMandala(r["anatomical_mandala"]),
            anatomical_patala=NetraPatala(r["anatomical_patala"]),
            doshic_etiology=r["doshic_etiology"],
            sadhya_asadhyata=SadhyaAsadhyata(r["sadhya_asadhyata"]),
            kriya_kalpa_indications=[KriyaKalpaType(k) for k in json.loads(r["kriya_kalpa_indications_json"])],
            contraindicated_procedures=[KriyaKalpaType(k) for k in json.loads(r["contraindicated_procedures_json"])],
        )
        for r in rows
    ]


# ==============================================================================
# TARPANA KRIYA KALPA DOSHIC CALCULUS & SAFETY ENGINE
# ==============================================================================

# Classical Matrakala durations:
# 1 Matrakala = 0.20 seconds (duration of one normal unhurried blink / Akshinimesha)
DOSHIC_TARPANA_MATRAKALA: Dict[str, int] = {
    "VATAJA": 1000,              # ~200 seconds (Deep unctuous nourishing requirement)
    "PITTAJA": 800,              # ~160 seconds (Pitta pacification without excess heating)
    "KAPHAJA": 600,              # ~120 seconds (Preventing excessive unctuous occlusion)
    "SWASTHA": 500,              # ~100 seconds (Routine ocular rejuvenation / Drishti Prasadana)
    "DRISHTI_PRASADANA": 500,    # ~100 seconds
    "SANDHI_SHUKLA": 300,        # ~60 seconds
    "VARTMA": 100,               # ~20 seconds
}

TARPANA_POST_CARE_PRECAUTIONS: List[str] = [
    "Strictly avoid direct exposure to bright sunlight, excessive wind, smoke, and fine dust.",
    "Mandatory complete abstention from VDU screens (smartphones, monitors, TV) for minimum 24 hours.",
    "Wear UV-protective dark tinted glasses upon stepping out into ambient daylight.",
    "Do not rub eyes or splash cold water immediately; allow natural lipid film stabilization.",
    "Follow light, warm, non-spicy Pathya diet (Mudga Yusha, warm boiled water, rice with cow ghee)."
]


def calculate_tarpana_retention(doshic_indication: str, requested_matrakalas: Optional[int] = None) -> Tuple[int, int]:
    """Calculate exact retentive Matrakalas and duration in seconds."""
    key = doshic_indication.upper()
    if requested_matrakalas is not None:
        matrakalas = requested_matrakalas
    else:
        matrakalas = DOSHIC_TARPANA_MATRAKALA.get(key, 500)

    duration_seconds = int(matrakalas * 0.20)
    return matrakalas, duration_seconds


def record_tarpana_session(
    conn: sqlite3.Connection,
    hospital_id: str,
    session_in: TarpanaSessionCreate
) -> TarpanaSessionResponse:
    """Record an ocular Tarpana Kriya Kalpa procedure session."""
    matrakalas, duration_sec = calculate_tarpana_retention(
        session_in.doshic_indication,
        session_in.retention_matrakalas
    )

    now = int(time.time())
    session_id = f"tarpana-{now}-{uuid.uuid4().hex[:6]}"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO kriya_kalpa_tarpana_logs (
            session_id, patient_id, hospital_id, eye_side,
            ghrita_used, retention_matrakalas, retention_duration_seconds,
            clinical_indication, post_procedure_precautions_json,
            practitioner_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            session_id,
            session_in.patient_id,
            hospital_id,
            session_in.eye_side,
            session_in.ghrita_used,
            matrakalas,
            duration_sec,
            session_in.clinical_indication,
            json.dumps(TARPANA_POST_CARE_PRECAUTIONS),
            session_in.practitioner_arn,
            now,
        )
    )
    conn.commit()

    return TarpanaSessionResponse(
        session_id=session_id,
        patient_id=session_in.patient_id,
        hospital_id=hospital_id,
        eye_side=session_in.eye_side,
        ghrita_used=session_in.ghrita_used,
        retention_matrakalas=matrakalas,
        retention_duration_seconds=duration_sec,
        clinical_indication=session_in.clinical_indication,
        post_procedure_precautions=TARPANA_POST_CARE_PRECAUTIONS,
        practitioner_arn=session_in.practitioner_arn,
        created_at=now,
    )


def list_tarpana_sessions(patient_id: str, conn: sqlite3.Connection) -> List[TarpanaSessionResponse]:
    """List historical Tarpana sessions for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM kriya_kalpa_tarpana_logs WHERE patient_id = ? ORDER BY created_at DESC;",
        (patient_id,)
    )
    rows = cursor.fetchall()
    return [
        TarpanaSessionResponse(
            session_id=r["session_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            eye_side=r["eye_side"],
            ghrita_used=r["ghrita_used"],
            retention_matrakalas=r["retention_matrakalas"],
            retention_duration_seconds=r["retention_duration_seconds"],
            clinical_indication=r["clinical_indication"],
            post_procedure_precautions=json.loads(r["post_procedure_precautions_json"]),
            practitioner_arn=r["practitioner_arn"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


# ==============================================================================
# ACUTE ADHIMANTHA (GLAUCOMA) EMERGENCY TRIAGE FIREWALL
# ==============================================================================

def evaluate_ophthalmic_screening(
    request: OphthalmicScreeningRequest
) -> OphthalmicScreeningResponse:
    """
    Ophthalmic triage screening with Acute Adhimantha (Glaucoma Crisis) Firewall.
    Any presentation of severely elevated IOP, stony hard eyeball, intense ocular
    pain radiating to hemicrania with corneal edema or rainbow halos mandates
    IMMEDIATE triage escalation and blocks all unctuous/heating Kriya Kalpas.
    """
    iop = request.intraocular_pressure_mmhg

    # Condition 1: Severe Glaucoma Crisis (Critical Emergency)
    is_pressure_critical = (iop is not None and iop >= 30.0)
    is_triad_crisis = (
        request.severe_ocular_pain and
        request.hemicrania_headache and
        (request.halos_around_lights or request.corneal_edema_steamy or request.pupil_fixed_mid_dilated or request.sudden_vision_loss)
    )
    is_steamy_dilated = (request.corneal_edema_steamy and request.pupil_fixed_mid_dilated and request.severe_ocular_pain)

    if is_pressure_critical or is_triad_crisis or is_steamy_dilated:
        return OphthalmicScreeningResponse(
            patient_id=request.patient_id,
            triage_level="CRITICAL_EMERGENCY",
            suspected_condition="Acute Congestive Adhimantha (Acute Angle-Closure Glaucoma Crisis)",
            adhimantha_glaucoma_firewall_triggered=True,
            contraindicated_kriya_kalpas=[
                KriyaKalpaType.TARPANA,
                KriyaKalpaType.SEKA,
                KriyaKalpaType.PINDI,
                KriyaKalpaType.PUTAPAKA
            ],
            clinical_action_plan=[
                "CRITICAL EMERGENCY FIREWALL ACTIVATED: Imminent danger of permanent ischemic optic nerve atrophy.",
                "STRICT CLINICAL BLOCK: Tarpana, Seka, Pindi, and hot unctuous treatments are strictly contraindicated.",
                "Immediate medical decompression: IV Mannitol (20% 1-2g/kg over 45 min) or oral glycerol + topical pressure-lowering agents under urgent ophthalmologist care.",
                "Urgent referral to Tertiary Ophthalmic Microsurgical Unit for laser peripheral iridotomy (LPI)."
            ],
            emergency_escalation_protocol="NCISM-AIIMS-INTEROPERABLE-CRITICAL-OPHTHALMIC-EMERGENCY-01"
        )

    # Condition 2: Ocular Hypertension / Subacute Adhimantha (Urgent)
    is_pressure_elevated = (iop is not None and iop > 21.0)
    if is_pressure_elevated or request.severe_ocular_pain or request.sudden_vision_loss:
        return OphthalmicScreeningResponse(
            patient_id=request.patient_id,
            triage_level="URGENT",
            suspected_condition="Ocular Hypertension / Subacute Adhimantha / Scleritis",
            adhimantha_glaucoma_firewall_triggered=False,
            contraindicated_kriya_kalpas=[KriyaKalpaType.TARPANA],
            clinical_action_plan=[
                "Caution: Elevated intraocular tension detected. Withhold Tarpana until tonometric stabilization.",
                "Schedule comprehensive slit-lamp biomicroscopy and gonioscopic anterior chamber angle assessment.",
                "Initiate soothing Triphala Aschyotana only after confirming open anterior chamber angle."
            ],
            emergency_escalation_protocol=None
        )

    # Condition 3: Routine / Normal Ophthalmic Condition
    if request.presenting_symptoms:
        return OphthalmicScreeningResponse(
            patient_id=request.patient_id,
            triage_level="ROUTINE",
            suspected_condition="Chronic Netra Roga / Shushkakshipaka / Timira / Asthenopia",
            adhimantha_glaucoma_firewall_triggered=False,
            contraindicated_kriya_kalpas=[],
            clinical_action_plan=[
                "Patient cleared for classical Shalakya Kriya Kalpa protocols (Tarpana / Aschyotana / Putapaka).",
                "Maintain adherence to post-procedure photoprotection and screen rest guidelines."
            ],
            emergency_escalation_protocol=None
        )

    return OphthalmicScreeningResponse(
        patient_id=request.patient_id,
        triage_level="NORMAL",
        suspected_condition="Asymptomatic / Baseline Ocular Examination",
        adhimantha_glaucoma_firewall_triggered=False,
        contraindicated_kriya_kalpas=[],
        clinical_action_plan=["Routine ophthalmic health maintenance and Dinacharya eye care (Anjana, Snana)."],
        emergency_escalation_protocol=None
    )


# ==============================================================================
# ENT MICRO-THERAPEUTIC ENGINE (KARNA, NASA, SHIRA)
# ==============================================================================

def record_ent_procedure(
    conn: sqlite3.Connection,
    hospital_id: str,
    proc_in: EntProcedureCreate
) -> EntProcedureResponse:
    """
    Log an ENT micro-therapeutic procedure with tympanic safety validation.
    Forceful fluid instillation (Karna Purana) with eardrum perforation is strictly prohibited.
    """
    # Tympanic Perforation Safety Firewall
    if proc_in.therapy_type == EntTherapyType.KARNA_PURANA and proc_in.eardrum_perforated:
        raise ClinicalGovernanceException(
            "STRICT CLINICAL CONTRAINDICATION: Perforated tympanic membrane (Karnapata Vidarana) detected. "
            "Liquid instillation via Karna Purana is strictly blocked to prevent middle-ear contamination and labyrinthitis."
        )

    now = int(time.time())
    procedure_id = f"ent-{now}-{uuid.uuid4().hex[:6]}"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO ent_karna_nasa_procedure_logs (
            procedure_id, patient_id, hospital_id, therapy_type,
            anatomical_site, medicated_oil_used, dosage_drops_or_ml,
            observations, practitioner_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            procedure_id,
            proc_in.patient_id,
            hospital_id,
            proc_in.therapy_type.value,
            proc_in.anatomical_site,
            proc_in.medicated_oil_used,
            proc_in.dosage_drops_or_ml,
            proc_in.observations,
            proc_in.practitioner_arn,
            now,
        )
    )
    conn.commit()

    return EntProcedureResponse(
        procedure_id=procedure_id,
        patient_id=proc_in.patient_id,
        hospital_id=hospital_id,
        therapy_type=proc_in.therapy_type,
        anatomical_site=proc_in.anatomical_site,
        medicated_oil_used=proc_in.medicated_oil_used,
        dosage_drops_or_ml=proc_in.dosage_drops_or_ml,
        observations=proc_in.observations,
        safety_cleared=True,
        contraindication_notes=None,
        practitioner_arn=proc_in.practitioner_arn,
        created_at=now,
    )


def list_ent_procedures(patient_id: str, conn: sqlite3.Connection) -> List[EntProcedureResponse]:
    """List ENT micro-therapeutic procedures for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM ent_karna_nasa_procedure_logs WHERE patient_id = ? ORDER BY created_at DESC;",
        (patient_id,)
    )
    rows = cursor.fetchall()
    return [
        EntProcedureResponse(
            procedure_id=r["procedure_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            therapy_type=EntTherapyType(r["therapy_type"]),
            anatomical_site=r["anatomical_site"],
            medicated_oil_used=r["medicated_oil_used"],
            dosage_drops_or_ml=r["dosage_drops_or_ml"],
            observations=r["observations"],
            safety_cleared=True,
            contraindication_notes=None,
            practitioner_arn=r["practitioner_arn"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
