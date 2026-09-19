"""
Vajikarana Tantra, Shukra Dushti & Reproductive Eugenics Engine
===============================================================
Implements:
1. The 8 Classical Shukra Dushtis Registry (Ashta Shukra Dushtis per Charaka & Sushruta)
2. WHO 6th Edition Semen Analysis Dual-Mapping Diagnostic Calculus
3. Shuddha Shukra Benchmark & Quantitative Shukra Shuddhi Score
4. Klaibya 4-Fold Stratification (Beejopaghataja, Dhvajabhangaja, Jarasambhava, Shukrakshayaja)
5. Vajikarana Pharmacodynamic Dynamics (Shukra-Janana, Rechaka, Stambhana, Shodhaka)
6. Pre-Vajikarana Shodhana Safety Firewall & Eugenics Protocols
7. SQLite WAL Persistence with SHA-256 Hash-Chained Audit Ledger Logging
"""

from __future__ import annotations
import json
import time
import uuid
import sqlite3
from typing import List, Optional, Dict, Any, Tuple

from core.database import append_audit_log
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from models.vajikarana_tantra import (
    KlaibyaType,
    SemenAnalysisCreate,
    SemenAnalysisResponse,
    ShukraDushtiProfile,
    ShukraDushtiType,
    VajikaranaActionClass,
    VajikaranaPrescriptionCreate,
    VajikaranaPrescriptionResponse,
    ViscosityGrade,
)

# ==============================================================================
# 1. THE 8 CLASSICAL SHUKRA DUSHTIS REGISTRY
# ==============================================================================

SEED_SHUKRA_DUSHTI_CATALOG: List[ShukraDushtiProfile] = [
    ShukraDushtiProfile(
        dushti_code="DUSHTI-VAT-01",
        sanskrit_name="वातज शुक्रदुष्टि (Vataja Shukra Dushti)",
        doshic_etiology="Aggravated Vata Dosha (Ruksha, Laghu, Sheeta, Khara qualities)",
        classical_characteristics=[
            "Phenila (Frothy / bubbly appearance on emission)",
            "Tanu (Thin / watery low viscosity fluid)",
            "Ruksha (Dry / non-unctuous seminal consistency)",
            "Kritsrena Pravritti (Painful, hesitant, and interrupted emission)"
        ],
        who_semen_correlate="Severe Asthenozoospermia (Progressive motility PR < 30%), hypospermia, low viscosity",
        indicated_shodhana_protocol="Anuvasana & Yapana Basti with Ashwagandhadya Taila, followed by Madhura-Snigdha Brimhana",
        classical_herbal_remedies=[
            "Ashwagandha Leha",
            "Balarishta",
            "Mashabaladi Kwatha",
            "Go-Ghrita cooked with Vidari and Shatavari"
        ]
    ),
    ShukraDushtiProfile(
        dushti_code="DUSHTI-PIT-02",
        sanskrit_name="पित्तज शुक्रदुष्टि (Pittaja Shukra Dushti)",
        doshic_etiology="Aggravated Pitta Dosha (Ushna, Tikshna, Amla, Sara qualities)",
        classical_characteristics=[
            "Peeta / Neela Varna (Yellowish or bluish-green discoloration)",
            "Ati-Ushna (Excessive heat and genital burning on ejaculation)",
            "Durgandha (Acrid, acidic, or sour pungent odor)",
            "Daha-yukta (Penile and urethral burning dysuria)"
        ],
        who_semen_correlate="Necrozoospermia (low viability < 54%), abnormal pH deviation (< 7.2 or > 8.0), oxidative DNA fragmentation",
        indicated_shodhana_protocol="Virechana with Avipattikara Churna & Draksha Kwatha, followed by Sheeta Pitta-Shamana",
        classical_herbal_remedies=[
            "Shatavari Ghrita",
            "Chandanadi Vati",
            "Gokshuradi Guggulu",
            "Praval Pishti with cold milk"
        ]
    ),
    ShukraDushtiProfile(
        dushti_code="DUSHTI-KAPH-03",
        sanskrit_name="कफज शुक्रदुष्टि (Kaphaja Shukra Dushti)",
        doshic_etiology="Aggravated Kapha Dosha (Guru, Sheeta, Sandra, Picchila qualities)",
        classical_characteristics=[
            "Ati-Picchila (Hyperviscous with elastic thread length > 4 cm)",
            "Sandra (Dense, gelatinous, heavy seminal fluid)",
            "Majjati (Sinks in water instead of dispersing evenly)",
            "Chira-Pravritti (Delayed liquefaction time exceeding 60 minutes)"
        ],
        who_semen_correlate="Semen Hyperviscosity, liquefaction failure (> 60 min), secondary entrapment asthenozoospermia",
        indicated_shodhana_protocol="Vamana with Madanaphala decoction, followed by Katu-Tikta Deepana-Pachana",
        classical_herbal_remedies=[
            "Gokshura Churna",
            "Chitrakadi Vati",
            "Shilajatu Vati with Triphala decoction",
            "Punarnavadi Kwatha"
        ]
    ),
    ShukraDushtiProfile(
        dushti_code="DUSHTI-RAKT-04",
        sanskrit_name="रक्तज शुक्रदुष्टि (Raktaja Shukra Dushti)",
        doshic_etiology="Aggravated Pitta and Rakta Dhatu vitiation (Raktapitta involvement)",
        classical_characteristics=[
            "Rakta-Varnam (Blood-tinged or dark reddish-brown ejaculate)",
            "Garbhadhana Ayogya (Failure of biological conception)",
            "Rudhirasrava (Gross or microscopic hematospermia)",
            "Toda & Daha (Pricking urethral discomfort during emission)"
        ],
        who_semen_correlate="Hematospermia (erythrocytes in semen), acute or subacute seminal vesiculitis or prostatitis",
        indicated_shodhana_protocol="Mridu Virechana followed by Rakta-Prasadana and Raktastambhana regimens",
        classical_herbal_remedies=[
            "Ushirasava",
            "Bolbaddha Rasa",
            "Sarivadyasava",
            "Gokshuradi Kwatha with pure Honey"
        ]
    ),
    ShukraDushtiProfile(
        dushti_code="DUSHTI-KUN-05",
        sanskrit_name="कुणपगन्धि शुक्रदुष्टि (Kunapa-Gandhi Shukra Dushti)",
        doshic_etiology="Severe Pitta-Rakta deep vascular putrefaction with necrotic tissue breakdown",
        classical_characteristics=[
            "Kunapa-gandhi (Cadaveric, decomposing, foul necrotic odor)",
            "Vivarana (Dark, dirty, or purplish discolored ejaculate)",
            "Paka-yukta (Active suppurative necrotizing tissue process)"
        ],
        who_semen_correlate="Severe Necrospermia, acute necrotizing infection of male accessory glands, severe pyospermia",
        indicated_shodhana_protocol="Extensive Raktamokshana and Mridu Tikshna Virechana, followed by Dhatu-Shodhana",
        classical_herbal_remedies=[
            "Khadirarishta",
            "Manjishtadi Kwatha",
            "Gandhaka Rasayana",
            "Panchatikta Ghrita"
        ]
    ),
    ShukraDushtiProfile(
        dushti_code="DUSHTI-GRAN-06",
        sanskrit_name="ग्रन्थिभूत शुक्रदुष्टि (Granthi-Bhuta Shukra Dushti)",
        doshic_etiology="Combined Sannipatika Vata-Kapha coagulative obstruction",
        classical_characteristics=[
            "Granthi-sannibha (Clotted, aggregated, nodular, clumped ejaculate)",
            "Srotorodha (Ductal and epididymal transit impedance)",
            "Ashma-vat kashaya (Insoluble curd-like gelatinous clumps)"
        ],
        who_semen_correlate="Severe Sperm Agglutination / Clumping, high anti-sperm antibodies (MAR test > 50%)",
        indicated_shodhana_protocol="Lekhana Basti and Snehana-Swedana to dissolve micro-nodular srotal obstruction",
        classical_herbal_remedies=[
            "Kanchanara Guggulu",
            "Varunadi Kwatha",
            "Shilajatu with Gokshura",
            "Shatavaryadi Ghrita"
        ]
    ),
    ShukraDushtiProfile(
        dushti_code="DUSHTI-PUTI-07",
        sanskrit_name="पूति-पूय शुक्रदुष्टि (Puti-Puya Shukra Dushti)",
        doshic_etiology="Pitta-Kapha suppurative infection with pus formation (Purulent)",
        classical_characteristics=[
            "Puya-sankasha (Purulent discharge with macroscopic or microscopic pus)",
            "Puti-gandha (Putrid, stale, foul-smelling ejaculate)",
            "Shoola & Daha (Painful ejaculation and testicular tenderness)"
        ],
        who_semen_correlate="Leukocytospermia (pus cells >= 5/HPF or peroxidase-positive leukocytes >= 1x10^6/mL)",
        indicated_shodhana_protocol="Tikta-Gana Shodhana followed by antimicrobial Shothahara Uttar Basti",
        classical_herbal_remedies=[
            "Chandraprabha Vati",
            "Triphala Guggulu",
            "Nimbadi Kwatha",
            "Guduchi Swarasa"
        ]
    ),
    ShukraDushtiProfile(
        dushti_code="DUSHTI-KSHI-08",
        sanskrit_name="क्षीण शुक्रदुष्टि (Kshina Shukra Dushti)",
        doshic_etiology="Pitta and Vata induced depletion of Shukra Dhatu essence",
        classical_characteristics=[
            "Alpa-Matra (Severe reduction in volume < 1.5 mL)",
            "Alpa-Shukra (Low sperm density and count)",
            "Chirat-Pravritti (Delayed, prolonged latency)",
            "Dourbalya (Post-coital systemic fatigue and lower back ache)"
        ],
        who_semen_correlate="Oligozoospermia (sperm concentration < 15 M/mL) and hypospermia (volume < 1.5 mL)",
        indicated_shodhana_protocol="Mridu Snehana followed by Santarpana Brimhana and Shukra-Janana therapy",
        classical_herbal_remedies=[
            "Musli Pak",
            "Ashwagandha Avaleha",
            "Kapikacchu Churna with warm milk",
            "Shukramatrika Vati"
        ]
    )
]


# ==============================================================================
# 2. DATABASE INITIALIZATION & SEEDING
# ==============================================================================

def initialize_vajikarana_tables(conn: sqlite3.Connection) -> None:
    """Seed classical Ashta Shukra Dushti catalog if empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM shukra_dushti_classification_registry;")
    row = cursor.fetchone()
    if row and row["cnt"] == 0:
        now = int(time.time())
        for d in SEED_SHUKRA_DUSHTI_CATALOG:
            cursor.execute(
                """
                INSERT INTO shukra_dushti_classification_registry (
                    dushti_code, sanskrit_name, doshic_etiology,
                    classical_characteristics_json, who_semen_correlate,
                    indicated_shodhana_protocol, classical_herbal_remedies_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    d.dushti_code,
                    d.sanskrit_name,
                    d.doshic_etiology,
                    json.dumps(d.classical_characteristics),
                    d.who_semen_correlate,
                    d.indicated_shodhana_protocol,
                    json.dumps(d.classical_herbal_remedies),
                    now
                )
            )
        conn.commit()


# ==============================================================================
# 3. CATALOG LOOKUPS
# ==============================================================================

def list_all_shukra_dushtis(conn: sqlite3.Connection) -> List[ShukraDushtiProfile]:
    """Retrieve full catalog of the 8 classical Shukra Dushtis."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shukra_dushti_classification_registry ORDER BY dushti_code ASC;")
    rows = cursor.fetchall()
    return [
        ShukraDushtiProfile(
            dushti_code=r["dushti_code"],
            sanskrit_name=r["sanskrit_name"],
            doshic_etiology=r["doshic_etiology"],
            classical_characteristics=json.loads(r["classical_characteristics_json"]),
            who_semen_correlate=r["who_semen_correlate"],
            indicated_shodhana_protocol=r["indicated_shodhana_protocol"],
            classical_herbal_remedies=json.loads(r["classical_herbal_remedies_json"]),
        )
        for r in rows
    ]


def get_shukra_dushti_by_code(dushti_code: str, conn: sqlite3.Connection) -> ShukraDushtiProfile:
    """Retrieve single Shukra Dushti specification by code."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shukra_dushti_classification_registry WHERE dushti_code = ?;", (dushti_code,))
    r = cursor.fetchone()
    if not r:
        raise RecordNotFoundException(entity="Shukra Dushti", identifier=dushti_code)
    return ShukraDushtiProfile(
        dushti_code=r["dushti_code"],
        sanskrit_name=r["sanskrit_name"],
        doshic_etiology=r["doshic_etiology"],
        classical_characteristics=json.loads(r["classical_characteristics_json"]),
        who_semen_correlate=r["who_semen_correlate"],
        indicated_shodhana_protocol=r["indicated_shodhana_protocol"],
        classical_herbal_remedies=json.loads(r["classical_herbal_remedies_json"]),
    )


# ==============================================================================
# 4. SEMEN ANALYSIS DUAL-MAPPING DIAGNOSTIC ENGINE
# ==============================================================================

def evaluate_semen_analysis(
    conn: sqlite3.Connection,
    hospital_id: str,
    data: SemenAnalysisCreate
) -> SemenAnalysisResponse:
    """
    Evaluates WHO 6th edition semen analysis parameters and maps them to:
    1. Primary and Secondary Ayurvedic Ashta Shukra Dushti
    2. Quantitative Shukra Shuddhi Score (0.0 to 100.0)
    3. WHO diagnostic classifications (Oligo-, Astheno-, Terato-, Necro-, Leukocytospermia)
    4. Fertility prognosis and Shodhana readiness
    """
    who_findings: List[str] = []

    # 1. WHO 6th Ed. Benchmarks Evaluation
    # Volume: norm >= 1.5 mL
    if data.volume_ml < 1.5:
        who_findings.append(f"Hypospermia (Volume {data.volume_ml:.1f} mL < 1.5 mL)")
        vol_score = 5.0 if data.volume_ml >= 1.0 else 2.0
    else:
        vol_score = 15.0

    # Sperm Concentration: norm >= 15 M/mL
    if data.sperm_concentration_million_ml == 0.0:
        who_findings.append("Azoospermia (Complete absence of spermatozoa in ejaculate)")
        count_score = 0.0
    elif data.sperm_concentration_million_ml < 15.0:
        who_findings.append(f"Oligozoospermia (Concentration {data.sperm_concentration_million_ml:.1f} M/mL < 15 M/mL)")
        count_score = 10.0 if data.sperm_concentration_million_ml >= 10.0 else 5.0
    else:
        count_score = 25.0

    # Progressive Motility: norm >= 30%
    if data.progressive_motility_percent < 30.0:
        who_findings.append(f"Asthenozoospermia (Progressive motility {data.progressive_motility_percent:.1f}% < 30%)")
        mot_score = 10.0 if data.progressive_motility_percent >= 20.0 else 4.0
    else:
        mot_score = 20.0

    # Normal Morphology: norm >= 4%
    if data.normal_morphology_percent < 4.0:
        who_findings.append(f"Teratozoospermia (Normal morphology {data.normal_morphology_percent:.1f}% < 4%)")
        morph_score = 6.0 if data.normal_morphology_percent >= 2.0 else 2.0
    else:
        morph_score = 15.0

    # Vitality: norm >= 54%
    if data.vitality_percent < 54.0:
        who_findings.append(f"Necrozoospermia / Low Vitality ({data.vitality_percent:.1f}% < 54%)")
        vit_score = 4.0 if data.vitality_percent >= 40.0 else 1.0
    else:
        vit_score = 10.0

    # Liquefaction & Viscosity: norm < 60 min and NORMAL viscosity
    if data.liquefaction_time_min >= 60 or data.viscosity_grade == ViscosityGrade.HIGH_PICCHILA:
        who_findings.append(f"Delayed Liquefaction ({data.liquefaction_time_min} min) / Semen Hyperviscosity ({data.viscosity_grade.value})")
        liq_score = 0.0
    elif data.viscosity_grade == ViscosityGrade.MODERATE_INCREASED:
        liq_score = 5.0
    else:
        liq_score = 10.0

    # Leukocytes / Pus cells: norm < 5 / HPF
    if data.pus_cells_per_hpf >= 5:
        who_findings.append(f"Leukocytospermia / Pyospermia ({data.pus_cells_per_hpf} pus cells/HPF >= 5/HPF)")
        pus_score = 0.0
    else:
        pus_score = 3.0

    # Erythrocytes / Hematospermia
    if data.erythrocytes_present:
        who_findings.append("Hematospermia (Presence of erythrocytes in seminal fluid)")
        rbc_score = 0.0
    else:
        rbc_score = 2.0

    if not who_findings:
        who_findings.append("Normozoospermia (All WHO 6th edition parameters within normative ranges)")

    # 2. Composite Shukra Shuddhi Score (0.0 to 100.0)
    shukra_shuddhi_score = round(min(100.0, vol_score + count_score + mot_score + morph_score + vit_score + liq_score + pus_score + rbc_score), 1)

    # 3. Ayurvedic Ashta Shukra Dushti Classification
    primary_dushti: ShukraDushtiType
    secondary_dushti: Optional[ShukraDushtiType] = None

    if data.erythrocytes_present:
        primary_dushti = ShukraDushtiType.RAKTAJA
        if data.pus_cells_per_hpf >= 5:
            secondary_dushti = ShukraDushtiType.PUTI_PUYA
    elif data.pus_cells_per_hpf >= 5:
        primary_dushti = ShukraDushtiType.PUTI_PUYA
        if data.progressive_motility_percent < 30.0:
            secondary_dushti = ShukraDushtiType.VATIKA
    elif data.liquefaction_time_min >= 60 or data.viscosity_grade == ViscosityGrade.HIGH_PICCHILA:
        primary_dushti = ShukraDushtiType.KAPHAJA
        if data.sperm_concentration_million_ml < 15.0:
            secondary_dushti = ShukraDushtiType.KSHINA
    elif data.sperm_concentration_million_ml < 15.0 or data.volume_ml < 1.5:
        primary_dushti = ShukraDushtiType.KSHINA
        if data.progressive_motility_percent < 30.0:
            secondary_dushti = ShukraDushtiType.VATIKA
    elif data.progressive_motility_percent < 30.0:
        primary_dushti = ShukraDushtiType.VATIKA
    elif data.vitality_percent < 54.0 or data.ph_level < 7.2 or data.ph_level > 8.0:
        primary_dushti = ShukraDushtiType.PAITTIKA
    else:
        primary_dushti = ShukraDushtiType.SHUDDHA_SHUKRA

    # 4. Fertility Prognosis Verdict
    if shukra_shuddhi_score >= 80.0 and primary_dushti == ShukraDushtiType.SHUDDHA_SHUKRA:
        fertility_prognosis = "Excellent Fertility Potential (Shuddha Shukra Sampat - Highly Favorable for Garbhadhana)"
    elif shukra_shuddhi_score >= 50.0:
        fertility_prognosis = "Moderate Subfertility (Sadhyatva - Amenable to targeted Shodhana and Vajikarana)"
    else:
        fertility_prognosis = "Severe Shukra Dushti / Infertility (Kashtasadhya - Mandates Intensive Panchakarma Shodhana, Rasayana & Extended Vajikarana)"

    now = int(time.time())
    analysis_id = f"sem-{now}-{uuid.uuid4().hex[:6]}"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO semen_analysis_diagnostic_records (
            analysis_id, patient_id, hospital_id, volume_ml, ph_level,
            liquefaction_time_min, viscosity_grade, sperm_concentration_million_ml,
            total_motility_percent, progressive_motility_percent, normal_morphology_percent,
            vitality_percent, pus_cells_per_hpf, erythrocytes_present,
            primary_shukra_dushti, shukra_shuddhi_score, fertility_prognosis,
            practitioner_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            analysis_id,
            data.patient_id,
            hospital_id,
            data.volume_ml,
            data.ph_level,
            data.liquefaction_time_min,
            data.viscosity_grade.value,
            data.sperm_concentration_million_ml,
            data.total_motility_percent,
            data.progressive_motility_percent,
            data.normal_morphology_percent,
            data.vitality_percent,
            data.pus_cells_per_hpf,
            1 if data.erythrocytes_present else 0,
            primary_dushti.value,
            shukra_shuddhi_score,
            fertility_prognosis,
            data.practitioner_arn,
            now
        )
    )
    conn.commit()

    append_audit_log(
        conn=conn,
        hospital_id=hospital_id,
        actor_id=data.practitioner_arn,
        action="SEMEN_ANALYSIS_EVALUATION",
        entity_type="SEMEN_DIAGNOSTICS",
        entity_id=analysis_id,
        details={
            "patient_id": data.patient_id,
            "primary_shukra_dushti": primary_dushti.value,
            "shukra_shuddhi_score": shukra_shuddhi_score,
            "sperm_concentration": data.sperm_concentration_million_ml,
            "progressive_motility": data.progressive_motility_percent
        }
    )

    return SemenAnalysisResponse(
        analysis_id=analysis_id,
        patient_id=data.patient_id,
        hospital_id=hospital_id,
        volume_ml=data.volume_ml,
        ph_level=data.ph_level,
        liquefaction_time_min=data.liquefaction_time_min,
        viscosity_grade=data.viscosity_grade,
        sperm_concentration_million_ml=data.sperm_concentration_million_ml,
        total_motility_percent=data.total_motility_percent,
        progressive_motility_percent=data.progressive_motility_percent,
        normal_morphology_percent=data.normal_morphology_percent,
        vitality_percent=data.vitality_percent,
        pus_cells_per_hpf=data.pus_cells_per_hpf,
        erythrocytes_present=data.erythrocytes_present,
        primary_shukra_dushti=primary_dushti,
        secondary_shukra_dushti=secondary_dushti,
        shukra_shuddhi_score=shukra_shuddhi_score,
        who_diagnostic_interpretation=who_findings,
        fertility_prognosis=fertility_prognosis,
        practitioner_arn=data.practitioner_arn,
        created_at=now
    )


def list_patient_semen_analyses(
    patient_id: str,
    conn: sqlite3.Connection
) -> List[SemenAnalysisResponse]:
    """Retrieve historical semen analysis diagnostic records for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM semen_analysis_diagnostic_records
        WHERE patient_id = ?
        ORDER BY created_at DESC;
        """,
        (patient_id,)
    )
    rows = cursor.fetchall()
    return [
        SemenAnalysisResponse(
            analysis_id=r["analysis_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            volume_ml=r["volume_ml"],
            ph_level=r["ph_level"],
            liquefaction_time_min=r["liquefaction_time_min"],
            viscosity_grade=ViscosityGrade(r["viscosity_grade"]),
            sperm_concentration_million_ml=r["sperm_concentration_million_ml"],
            total_motility_percent=r["total_motility_percent"],
            progressive_motility_percent=r["progressive_motility_percent"],
            normal_morphology_percent=r["normal_morphology_percent"],
            vitality_percent=r["vitality_percent"],
            pus_cells_per_hpf=r["pus_cells_per_hpf"],
            erythrocytes_present=bool(r["erythrocytes_present"]),
            primary_shukra_dushti=ShukraDushtiType(r["primary_shukra_dushti"]),
            secondary_shukra_dushti=None,
            shukra_shuddhi_score=r["shukra_shuddhi_score"],
            who_diagnostic_interpretation=["Historical Diagnostic Entry"],
            fertility_prognosis=r["fertility_prognosis"],
            practitioner_arn=r["practitioner_arn"],
            created_at=r["created_at"]
        )
        for r in rows
    ]


# ==============================================================================
# 5. VAJIKARANA PROTOCOL & SAFETY FIREWALL ENGINE
# ==============================================================================

def prescribe_vajikarana_protocol(
    conn: sqlite3.Connection,
    hospital_id: str,
    req: VajikaranaPrescriptionCreate
) -> VajikaranaPrescriptionResponse:
    """
    Formulates a targeted Vajikarana prescription matching Klaibya pathology
    and pharmacodynamic action class, enforcing the Pre-Vajikarana Shodhana Firewall.
    """
    warnings: List[str] = []

    # Safety Firewall Rule 1: Prior Shodhana Verification
    if not req.pre_shodhana_completed:
        warnings.append(
            "CONTRAINDICATION: Prior Panchakarma bio-cleansing or mild Kostha Shuddhi not verified. "
            "Administering potent Vajikarana into an unpurified body precipitates toxic Ama accumulation, "
            "Vidradhi (deep abscesses), or metabolic obstruction (Charaka Samhita Chikitsa 2/1)."
        )

    # Safety Firewall Rule 2: Active Ama / Sluggish Agni
    if req.has_active_ama:
        warnings.append(
            "CONTRAINDICATION: Active Sama Avastha detected. Deepana-Pachana (with Trikatu/Chitrakadi) "
            "is strictly mandatory prior to initiating heavy Brimhana/Vajikarana tonics."
        )

    safety_cleared = (len(warnings) == 0)

    # Pharmacodynamic Drug Selection
    formulations: List[str] = []
    if req.target_action_class == VajikaranaActionClass.SHUKRA_JANANA:
        formulations = [
            "Ashwagandha Leha (10g twice daily with warm A2 cow milk)",
            "Shatavari Ghrita (5g at bedtime)",
            "Vidaryadi Churna (3g twice daily with honey and ghee in unequal parts)",
            "Musli Pak (5g morning on empty stomach)"
        ]
    elif req.target_action_class == VajikaranaActionClass.SHUKRA_RECHAKA:
        formulations = [
            "Akarakarabhadi Vati (1 tablet 1 hour before sleep with warm milk)",
            "Brihat Vata Chintamani Rasa with milk (under clinical RMP supervision)",
            "Hingwashtaka Churna (for Vata Anulomana & apana balance)"
        ]
    elif req.target_action_class == VajikaranaActionClass.SHUKRA_JANANA_PRAVARTAKA:
        formulations = [
            "Vanari Kalpa (Purified Mucuna pruriens / Kapikacchu seed compound with cow milk)",
            "Shivalingi Beeja Churna with milk",
            "Ashwagandharishta (20 mL with equal water post-meals)",
            "Go-Ghrita & Go-Ksheera intensive Brimhana regimen"
        ]
    elif req.target_action_class == VajikaranaActionClass.SHUKRA_STAMBHANA:
        formulations = [
            "Jatiphala Churna (Nutmeg - 1g with lukewarm milk)",
            "Akarakara and Pushpadhanwa Rasa",
            "Kamadev Ghrita (5g twice daily)",
            "Vanga Bhasma with honey (unequal ratio)"
        ]
    elif req.target_action_class == VajikaranaActionClass.SHUKRA_SHODHAKA:
        formulations = [
            "Gokshuradi Guggulu (2 tablets twice daily)",
            "Chandraprabha Vati (2 tablets twice daily with water)",
            "Shuddha Shilajatu (500mg with Triphala decoction)",
            "Triphala Kwatha"
        ]

    # Dietary & Lifestyle Pathya
    pathya = [
        "Go-Ksheera (Organic A2 Cow Milk) boiled with cardamom and Shatavari.",
        "Go-Ghrita (Pure Cow Ghee), Black gram (Masha), and soaked almonds.",
        "Avoidance of excessively sour (Amla), salty (Lavana), and pungent (Katu) foods that scorch Shukra.",
        "Strict cessation of tobacco, alcohol, and late night sleeplessness (Ratri-Jagarana).",
        "Sensory and sexual rest during the initial Shodhana-Purification window to consolidate Ojas."
    ]

    # Psychosexual Counseling Notes
    psychosexual_notes = (
        "Somanasya (Mental cheerfulness) is declared the foremost Vajikarana entity by Maharshi Charaka "
        "('सौमनस्यं गर्भधारणानां श्रेष्ठम्'). Cultivation of mutual affection, elimination of performance anxiety, "
        "and harmonious environment are clinically essential for full therapeutic efficacy."
    )

    now = int(time.time())
    protocol_id = f"vaji-{now}-{uuid.uuid4().hex[:6]}"

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO vajikarana_treatment_protocols (
            protocol_id, patient_id, hospital_id, klaibya_type,
            shukra_action_class, pre_shodhana_verified,
            prescribed_formulations_json, dietary_lifestyle_pathya_json,
            psychosexual_counseling_notes, safety_firewall_cleared,
            practitioner_arn, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            protocol_id,
            req.patient_id,
            hospital_id,
            req.klaibya_type.value,
            req.target_action_class.value,
            1 if req.pre_shodhana_completed else 0,
            json.dumps(formulations),
            json.dumps(pathya),
            psychosexual_notes,
            1 if safety_cleared else 0,
            req.practitioner_arn,
            now
        )
    )
    conn.commit()

    append_audit_log(
        conn=conn,
        hospital_id=hospital_id,
        actor_id=req.practitioner_arn,
        action="VAJIKARANA_PRESCRIPTION_CREATE",
        entity_type="VAJIKARANA_PROTOCOL",
        entity_id=protocol_id,
        details={
            "patient_id": req.patient_id,
            "klaibya_type": req.klaibya_type.value,
            "shukra_action_class": req.target_action_class.value,
            "safety_firewall_cleared": safety_cleared,
            "warning_count": len(warnings)
        }
    )

    return VajikaranaPrescriptionResponse(
        protocol_id=protocol_id,
        patient_id=req.patient_id,
        hospital_id=hospital_id,
        klaibya_type=req.klaibya_type,
        shukra_action_class=req.target_action_class,
        pre_shodhana_verified=req.pre_shodhana_completed,
        prescribed_classical_formulations=formulations,
        dietary_lifestyle_pathya=pathya,
        psychosexual_counseling_notes=psychosexual_notes,
        safety_firewall_cleared=safety_cleared,
        contraindication_warnings=warnings,
        practitioner_arn=req.practitioner_arn,
        created_at=now
    )


def list_patient_vajikarana_prescriptions(
    patient_id: str,
    conn: sqlite3.Connection
) -> List[VajikaranaPrescriptionResponse]:
    """Retrieve historical Vajikarana treatment protocols for a patient."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM vajikarana_treatment_protocols
        WHERE patient_id = ?
        ORDER BY created_at DESC;
        """,
        (patient_id,)
    )
    rows = cursor.fetchall()
    return [
        VajikaranaPrescriptionResponse(
            protocol_id=r["protocol_id"],
            patient_id=r["patient_id"],
            hospital_id=r["hospital_id"],
            klaibya_type=KlaibyaType(r["klaibya_type"]),
            shukra_action_class=VajikaranaActionClass(r["shukra_action_class"]),
            pre_shodhana_verified=bool(r["pre_shodhana_verified"]),
            prescribed_classical_formulations=json.loads(r["prescribed_formulations_json"]),
            dietary_lifestyle_pathya=json.loads(r["dietary_lifestyle_pathya_json"]),
            psychosexual_counseling_notes=r["psychosexual_counseling_notes"],
            safety_firewall_cleared=bool(r["safety_firewall_cleared"]),
            contraindication_warnings=[],
            practitioner_arn=r["practitioner_arn"],
            created_at=r["created_at"]
        )
        for r in rows
    ]
