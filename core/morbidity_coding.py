"""
Morbidity Dual-Coding & Classical Taxonomy Engine
================================================
Implements:
1. Ashtodara Shata classical taxonomy registry (20+ core entities)
2. Dual-coding crosswalk linking AYUSH NAMASTE, WHO ICD-11 TM2, ICD-11 Biomedicine, and ICD-10
3. ABDM / HL7 FHIR Condition resource generator with multi-terminology coding
4. SQLite persistence with immutable audit trails and deterministic retrieval
"""

from __future__ import annotations
import json
import time
import uuid
import sqlite3
from typing import Dict, List, Optional, Any

from models.morbidity_coding import (
    MorbidityCrosswalkEntry,
    PatientDiagnosisCodingInput,
    PatientDiagnosisCodingOutput,
    VerificationStatus,
    DoshicCategory,
)

# ==============================================================================
# CLASSICAL ASHTODARA SHATA & DUAL-CODING REFERENCE REGISTRY
# ==============================================================================

SEED_CROSSWALK_REGISTRY: List[MorbidityCrosswalkEntry] = [
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-AMAVATA",
        sanskrit_name="आमवात",
        english_name="Rheumatoid Arthropathy / Endotoxin-Induced Arthritis",
        namaste_code="NAMASTE-AYU-014",
        icd11_tm2_code="TM2-AYU-AMA",
        icd11_biomed_code="FA20.Z",
        icd10_code="M06.9",
        doshic_category=DoshicCategory.DVANDVAJA,
        classical_text_source="Madhava Nidana Ch. 25, Charaka Chikitsasthana"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-SANDHIGATA-VATA",
        sanskrit_name="सन्धिगत वात",
        english_name="Osteoarthropathy / Degenerative Joint Disease",
        namaste_code="NAMASTE-AYU-022",
        icd11_tm2_code="TM2-AYU-SGV",
        icd11_biomed_code="FA00",
        icd10_code="M19.9",
        doshic_category=DoshicCategory.VATAJA,
        classical_text_source="Charaka Samhita Chikitsasthana Ch. 28"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-VATARAKTA",
        sanskrit_name="वातरक्त",
        english_name="Gout / Metabolic Microvascular Arthropathy",
        namaste_code="NAMASTE-AYU-031",
        icd11_tm2_code="TM2-AYU-VTR",
        icd11_biomed_code="FA20.0",
        icd10_code="M10.9",
        doshic_category=DoshicCategory.DVANDVAJA,
        classical_text_source="Charaka Samhita Chikitsasthana Ch. 29"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-JWARA-VATAJA",
        sanskrit_name="वातज ज्वर",
        english_name="Vataja Pyrexia / Irregular Febrile Syndrome",
        namaste_code="NAMASTE-AYU-001",
        icd11_tm2_code="TM2-AYU-JWV",
        icd11_biomed_code="MG26",
        icd10_code="R50.9",
        doshic_category=DoshicCategory.VATAJA,
        classical_text_source="Charaka Samhita Nidanasthana Ch. 1"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-JWARA-PITTAJA",
        sanskrit_name="पित्तज ज्वर",
        english_name="Pittaja Pyrexia / Inflammatory Hyperpyrexia",
        namaste_code="NAMASTE-AYU-002",
        icd11_tm2_code="TM2-AYU-JWP",
        icd11_biomed_code="MG26.0",
        icd10_code="R50.8",
        doshic_category=DoshicCategory.PITTAJA,
        classical_text_source="Charaka Samhita Nidanasthana Ch. 1"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-JWARA-KAPHAJA",
        sanskrit_name="कफज ज्वर",
        english_name="Kaphaja Pyrexia / Low-Grade Lingering Fever",
        namaste_code="NAMASTE-AYU-003",
        icd11_tm2_code="TM2-AYU-JWK",
        icd11_biomed_code="MG26.1",
        icd10_code="R50.8",
        doshic_category=DoshicCategory.KAPHAJA,
        classical_text_source="Charaka Samhita Nidanasthana Ch. 1"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-TAMAKA-SHWASA",
        sanskrit_name="तमक श्वास",
        english_name="Bronchial Asthma / Paroxysmal Obstructive Dyspnea",
        namaste_code="NAMASTE-AYU-045",
        icd11_tm2_code="TM2-AYU-TMS",
        icd11_biomed_code="CA23",
        icd10_code="J45.9",
        doshic_category=DoshicCategory.DVANDVAJA,
        classical_text_source="Charaka Samhita Chikitsasthana Ch. 17"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-PRAMEHA-KAPHAJA",
        sanskrit_name="कफज प्रमेह",
        english_name="Kaphaja Metabolic Impairment / Pre-Diabetes Mellitus",
        namaste_code="NAMASTE-AYU-056",
        icd11_tm2_code="TM2-AYU-PRM",
        icd11_biomed_code="5A11",
        icd10_code="E11.9",
        doshic_category=DoshicCategory.KAPHAJA,
        classical_text_source="Charaka Samhita Nidanasthana Ch. 4"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-GRAHANI-DOSHA",
        sanskrit_name="ग्रहणी दोष",
        english_name="Malabsorption Syndrome / Post-Dysenteric Dysbiosis",
        namaste_code="NAMASTE-AYU-062",
        icd11_tm2_code="TM2-AYU-GRH",
        icd11_biomed_code="DD90.0",
        icd10_code="K90.9",
        doshic_category=DoshicCategory.SANNIPATAJA,
        classical_text_source="Charaka Samhita Chikitsasthana Ch. 15"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-AMLAPITTA",
        sanskrit_name="अम्लपित्त",
        english_name="Hyperchlorhydria / Non-Ulcer Dyspepsia",
        namaste_code="NAMASTE-AYU-071",
        icd11_tm2_code="TM2-AYU-AMP",
        icd11_biomed_code="MD90.2",
        icd10_code="K30",
        doshic_category=DoshicCategory.PITTAJA,
        classical_text_source="Kashyapa Samhita Khilasthana Ch. 16"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-KAMALA-KOSTHASHRAYA",
        sanskrit_name="कोष्ठाश्रय कामला",
        english_name="Hepatocellular / Obstructive Jaundice",
        namaste_code="NAMASTE-AYU-083",
        icd11_tm2_code="TM2-AYU-KML",
        icd11_biomed_code="DB90.0",
        icd10_code="K76.9",
        doshic_category=DoshicCategory.PITTAJA,
        classical_text_source="Charaka Samhita Chikitsasthana Ch. 16"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-ARSHAS-VATAJA",
        sanskrit_name="वातज अर्श",
        english_name="Vataja Hemorrhoidal Vascular Disease",
        namaste_code="NAMASTE-AYU-091",
        icd11_tm2_code="TM2-AYU-ARS",
        icd11_biomed_code="DB60",
        icd10_code="I84.9",
        doshic_category=DoshicCategory.VATAJA,
        classical_text_source="Charaka Samhita Chikitsasthana Ch. 14"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-HRIDROGA-VATAJA",
        sanskrit_name="वातज हृद्रोग",
        english_name="Vataja Ischemic Precordial Distress / Angina Pectoris",
        namaste_code="NAMASTE-AYU-102",
        icd11_tm2_code="TM2-AYU-HRD",
        icd11_biomed_code="BA41",
        icd10_code="I20.9",
        doshic_category=DoshicCategory.VATAJA,
        classical_text_source="Charaka Samhita Chikitsasthana Ch. 26"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-RAJAYAKSHMA",
        sanskrit_name="राजयक्ष्मा",
        english_name="Pulmonary / Systemic Consumption (Tuberculosis)",
        namaste_code="NAMASTE-AYU-115",
        icd11_tm2_code="TM2-AYU-RJY",
        icd11_biomed_code="1B10",
        icd10_code="A15.0",
        doshic_category=DoshicCategory.SANNIPATAJA,
        classical_text_source="Charaka Samhita Chikitsasthana Ch. 8"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-ATISARA-VATAJA",
        sanskrit_name="वातज अतिसार",
        english_name="Acute Vataja Enteritis / Diarrhea",
        namaste_code="NAMASTE-AYU-124",
        icd11_tm2_code="TM2-AYU-ATS",
        icd11_biomed_code="ME05.1",
        icd10_code="A09",
        doshic_category=DoshicCategory.VATAJA,
        classical_text_source="Charaka Samhita Chikitsasthana Ch. 19"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-KASA-VATAJA",
        sanskrit_name="वातज कास",
        english_name="Dry Unproductive Bronchial Cough",
        namaste_code="NAMASTE-AYU-133",
        icd11_tm2_code="TM2-AYU-KSA",
        icd11_biomed_code="MD10",
        icd10_code="R05",
        doshic_category=DoshicCategory.VATAJA,
        classical_text_source="Charaka Samhita Chikitsasthana Ch. 18"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-APASMARA",
        sanskrit_name="अपस्मार",
        english_name="Convulsive Seizure Disorder / Epilepsy",
        namaste_code="NAMASTE-AYU-141",
        icd11_tm2_code="TM2-AYU-APS",
        icd11_biomed_code="8A60",
        icd10_code="G40.9",
        doshic_category=DoshicCategory.SANNIPATAJA,
        classical_text_source="Charaka Samhita Nidanasthana Ch. 8"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-UNMADA-VATAJA",
        sanskrit_name="वातज उन्माद",
        english_name="Affective Psychiatric Disorder / Agitated Psychosis",
        namaste_code="NAMASTE-AYU-152",
        icd11_tm2_code="TM2-AYU-UNM",
        icd11_biomed_code="6A20",
        icd10_code="F20.9",
        doshic_category=DoshicCategory.VATAJA,
        classical_text_source="Charaka Samhita Nidanasthana Ch. 7"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-KUSHTHA-KITIBHA",
        sanskrit_name="किटिभ कुष्ठ",
        english_name="Psoriasis Vulgaris / Lichenified Dermatosis",
        namaste_code="NAMASTE-AYU-165",
        icd11_tm2_code="TM2-AYU-KSH",
        icd11_biomed_code="EA90",
        icd10_code="L40.0",
        doshic_category=DoshicCategory.DVANDVAJA,
        classical_text_source="Charaka Samhita Chikitsasthana Ch. 7"
    ),
    MorbidityCrosswalkEntry(
        disease_code="AYU-DIS-SHVITRA",
        sanskrit_name="श्वित्र",
        english_name="Vitiligo / Depigmentary Dermatosis",
        namaste_code="NAMASTE-AYU-174",
        icd11_tm2_code="TM2-AYU-SVT",
        icd11_biomed_code="ED63",
        icd10_code="L80",
        doshic_category=DoshicCategory.DVANDVAJA,
        classical_text_source="Charaka Samhita Chikitsasthana Ch. 7"
    ),
]


def seed_disease_classification_registry(conn: sqlite3.Connection) -> None:
    """Seeds the 20+ classical diseases into the database registry if not already present."""
    cursor = conn.cursor()
    now = int(time.time())
    for entry in SEED_CROSSWALK_REGISTRY:
        cursor.execute(
            """
            INSERT OR IGNORE INTO disease_classification_registry (
                disease_code, sanskrit_name, english_name, namaste_code,
                icd11_tm2_code, icd11_biomed_code, icd10_code,
                doshic_category, classical_text_source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                entry.disease_code,
                entry.sanskrit_name,
                entry.english_name,
                entry.namaste_code,
                entry.icd11_tm2_code,
                entry.icd11_biomed_code,
                entry.icd10_code,
                entry.doshic_category.value,
                entry.classical_text_source,
                now,
            )
        )


def search_morbidity_registry(
    conn: sqlite3.Connection,
    query: Optional[str] = None,
    doshic_filter: Optional[DoshicCategory] = None,
) -> List[MorbidityCrosswalkEntry]:
    """Searches morbidity registry by text (Sanskrit, English, code) and optional Doshic category."""
    seed_disease_classification_registry(conn)
    cursor = conn.cursor()

    sql = "SELECT * FROM disease_classification_registry WHERE 1=1"
    params: List[Any] = []

    if doshic_filter:
        sql += " AND doshic_category = ?"
        params.append(doshic_filter.value)

    if query:
        q_norm = f"%{query.strip()}%"
        sql += """ AND (
            disease_code LIKE ? OR
            sanskrit_name LIKE ? OR
            english_name LIKE ? OR
            namaste_code LIKE ? OR
            icd11_tm2_code LIKE ? OR
            icd11_biomed_code LIKE ? OR
            icd10_code LIKE ?
        )"""
        params.extend([q_norm] * 7)

    sql += " ORDER BY disease_code ASC;"
    cursor.execute(sql, params)
    rows = cursor.fetchall()

    return [
        MorbidityCrosswalkEntry(
            disease_code=r["disease_code"],
            sanskrit_name=r["sanskrit_name"],
            english_name=r["english_name"],
            namaste_code=r["namaste_code"],
            icd11_tm2_code=r["icd11_tm2_code"],
            icd11_biomed_code=r["icd11_biomed_code"],
            icd10_code=r["icd10_code"],
            doshic_category=DoshicCategory(r["doshic_category"]),
            classical_text_source=r["classical_text_source"],
        )
        for r in rows
    ]


def get_crosswalk_entry(
    conn: sqlite3.Connection,
    identifier: str
) -> Optional[MorbidityCrosswalkEntry]:
    """Resolves a crosswalk entry by disease_code, namaste_code, icd11_tm2_code, or icd11_biomed_code."""
    seed_disease_classification_registry(conn)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM disease_classification_registry
        WHERE disease_code = ? OR namaste_code = ? OR icd11_tm2_code = ? OR icd11_biomed_code = ?
        LIMIT 1;
        """,
        (identifier, identifier, identifier, identifier)
    )
    r = cursor.fetchone()
    if not r:
        return None

    return MorbidityCrosswalkEntry(
        disease_code=r["disease_code"],
        sanskrit_name=r["sanskrit_name"],
        english_name=r["english_name"],
        namaste_code=r["namaste_code"],
        icd11_tm2_code=r["icd11_tm2_code"],
        icd11_biomed_code=r["icd11_biomed_code"],
        icd10_code=r["icd10_code"],
        doshic_category=DoshicCategory(r["doshic_category"]),
        classical_text_source=r["classical_text_source"],
    )


def generate_fhir_condition_resource(
    patient_id: str,
    diagnosing_arn: str,
    crosswalk: MorbidityCrosswalkEntry,
    verification_status: VerificationStatus,
    clinical_notes: Optional[str],
    timestamp: int,
) -> Dict[str, Any]:
    """
    Synthesizes an ABDM / HL7 FHIR R4 Condition resource with dual-coded terminology
    (Ministry of AYUSH NAMASTE and WHO ICD-11).
    """
    recorded_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp))
    condition_id = f"cond-{uuid.uuid4().hex[:12]}"

    fhir_json: Dict[str, Any] = {
        "resourceType": "Condition",
        "id": condition_id,
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active",
                    "display": "Active"
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": verification_status.value.lower(),
                    "display": verification_status.value
                }
            ]
        },
        "code": {
            "coding": [
                {
                    "system": "https://namstp.ayush.gov.in/#/morbidity",
                    "code": crosswalk.namaste_code,
                    "display": f"{crosswalk.sanskrit_name} ({crosswalk.english_name})"
                },
                {
                    "system": "http://id.who.int/icd/release/11/mms/tm2",
                    "code": crosswalk.icd11_tm2_code,
                    "display": f"Ayurveda TM2: {crosswalk.sanskrit_name}"
                },
                {
                    "system": "http://id.who.int/icd/release/11/mms",
                    "code": crosswalk.icd11_biomed_code,
                    "display": crosswalk.english_name
                },
                {
                    "system": "http://hl7.org/fhir/sid/icd-10",
                    "code": crosswalk.icd10_code,
                    "display": crosswalk.english_name
                }
            ],
            "text": f"{crosswalk.sanskrit_name} - {crosswalk.english_name} [NAMASTE: {crosswalk.namaste_code} | ICD-11: {crosswalk.icd11_biomed_code}]"
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "recordedDate": recorded_iso,
        "recorder": {
            "reference": f"Practitioner/{diagnosing_arn}",
            "display": f"AYUSH NCISM Registered Medical Practitioner {diagnosing_arn}"
        }
    }

    if clinical_notes:
        fhir_json["note"] = [{"text": clinical_notes}]

    return fhir_json


def record_patient_diagnosis(
    conn: sqlite3.Connection,
    input_data: PatientDiagnosisCodingInput,
    diagnosing_arn: str,
    hospital_id: str,
) -> PatientDiagnosisCodingOutput:
    """Records a verified dual-coded diagnosis into the patient EHR and persists the FHIR Condition."""
    seed_disease_classification_registry(conn)
    crosswalk = get_crosswalk_entry(conn, input_data.disease_code)
    if not crosswalk:
        raise ValueError(f"Disease code '{input_data.disease_code}' not found in classification registry")

    now = int(time.time())
    coding_id = f"diag-{uuid.uuid4().hex[:12]}"

    fhir_condition = generate_fhir_condition_resource(
        patient_id=input_data.patient_id,
        diagnosing_arn=diagnosing_arn,
        crosswalk=crosswalk,
        verification_status=input_data.verification_status,
        clinical_notes=input_data.clinical_notes,
        timestamp=now,
    )

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patient_diagnosis_codings (
            coding_id, patient_id, hospital_id, diagnosing_arn,
            disease_code, clinical_notes, verification_status,
            fhir_condition_json, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            coding_id,
            input_data.patient_id,
            hospital_id,
            diagnosing_arn,
            crosswalk.disease_code,
            input_data.clinical_notes,
            input_data.verification_status.value,
            json.dumps(fhir_condition),
            now,
        )
    )

    return PatientDiagnosisCodingOutput(
        coding_id=coding_id,
        patient_id=input_data.patient_id,
        hospital_id=hospital_id,
        diagnosing_arn=diagnosing_arn,
        disease_crosswalk=crosswalk,
        verification_status=input_data.verification_status,
        clinical_notes=input_data.clinical_notes,
        fhir_condition=fhir_condition,
        timestamp=now,
    )


def get_patient_diagnoses(
    conn: sqlite3.Connection,
    patient_id: str
) -> List[PatientDiagnosisCodingOutput]:
    """Retrieves all dual-coded diagnoses for a patient ordered chronologically."""
    seed_disease_classification_registry(conn)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT c.*, r.sanskrit_name, r.english_name, r.namaste_code,
               r.icd11_tm2_code, r.icd11_biomed_code, r.icd10_code,
               r.doshic_category, r.classical_text_source
        FROM patient_diagnosis_codings c
        JOIN disease_classification_registry r ON c.disease_code = r.disease_code
        WHERE c.patient_id = ?
        ORDER BY c.timestamp ASC, c.rowid ASC;
        """,
        (patient_id,)
    )
    rows = cursor.fetchall()

    outputs: List[PatientDiagnosisCodingOutput] = []
    for r in rows:
        cw = MorbidityCrosswalkEntry(
            disease_code=r["disease_code"],
            sanskrit_name=r["sanskrit_name"],
            english_name=r["english_name"],
            namaste_code=r["namaste_code"],
            icd11_tm2_code=r["icd11_tm2_code"],
            icd11_biomed_code=r["icd11_biomed_code"],
            icd10_code=r["icd10_code"],
            doshic_category=DoshicCategory(r["doshic_category"]),
            classical_text_source=r["classical_text_source"],
        )
        outputs.append(
            PatientDiagnosisCodingOutput(
                coding_id=r["coding_id"],
                patient_id=r["patient_id"],
                hospital_id=r["hospital_id"],
                diagnosing_arn=r["diagnosing_arn"],
                disease_crosswalk=cw,
                verification_status=VerificationStatus(r["verification_status"]),
                clinical_notes=r["clinical_notes"],
                fhir_condition=json.loads(r["fhir_condition_json"]),
                timestamp=r["timestamp"],
            )
        )
    return outputs
