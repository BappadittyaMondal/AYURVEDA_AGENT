"""
Unit Tests for Classical Disease Classification & Morbidity Dual-Coding Engine.
"""

import tempfile
from pathlib import Path
import sqlite3
import pytest
from core.database import init_database
from core.morbidity_coding import (
    SEED_CROSSWALK_REGISTRY,
    generate_fhir_condition_resource,
    get_crosswalk_entry,
    get_patient_diagnoses,
    record_patient_diagnosis,
    search_morbidity_registry,
    seed_disease_classification_registry,
)
from models.morbidity_coding import (
    DoshicCategory,
    PatientDiagnosisCodingInput,
    VerificationStatus,
)


def test_seed_crosswalk_registry_completeness():
    """Verify that all 20 classical crosswalk entries are present and strictly populated."""
    assert len(SEED_CROSSWALK_REGISTRY) >= 20

    for entry in SEED_CROSSWALK_REGISTRY:
        assert entry.disease_code.startswith("AYU-DIS-")
        assert len(entry.sanskrit_name) > 0
        assert len(entry.english_name) > 0
        assert entry.namaste_code.startswith("NAMASTE-AYU-")
        assert entry.icd11_tm2_code.startswith("TM2-AYU-")
        assert len(entry.icd11_biomed_code) > 0
        assert len(entry.icd10_code) > 0
        assert isinstance(entry.doshic_category, DoshicCategory)
        assert len(entry.classical_text_source) > 0


def test_crosswalk_resolution_multi_identifier():
    """Test resolution of disease entry by disease_code, namaste_code, icd11_tm2_code, and icd11_biomed_code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_morbidity.db"
        init_database(db_file)
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row

        # 1. By disease code
        entry1 = get_crosswalk_entry(conn, "AYU-DIS-AMAVATA")
        assert entry1 is not None
        assert entry1.disease_code == "AYU-DIS-AMAVATA"
        assert entry1.sanskrit_name == "आमवात"
        assert entry1.namaste_code == "NAMASTE-AYU-014"

        # 2. By NAMASTE code
        entry2 = get_crosswalk_entry(conn, "NAMASTE-AYU-014")
        assert entry2 is not None
        assert entry2.disease_code == "AYU-DIS-AMAVATA"

        # 3. By ICD-11 TM2 code
        entry3 = get_crosswalk_entry(conn, "TM2-AYU-AMA")
        assert entry3 is not None
        assert entry3.disease_code == "AYU-DIS-AMAVATA"

        # 4. By ICD-11 Biomedicine code
        entry4 = get_crosswalk_entry(conn, "FA20.Z")
        assert entry4 is not None
        assert entry4.disease_code == "AYU-DIS-AMAVATA"

        # 5. Non-existent returns None
        assert get_crosswalk_entry(conn, "UNKNOWN-CODE-999") is None
        conn.close()


def test_search_and_doshic_filtering():
    """Verify full-text search and Doshic category filtering."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_search.db"
        init_database(db_file)
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row

        # Search for Jwara (should match all 3 Jwara entries)
        jwara_results = search_morbidity_registry(conn, query="ज्वर")
        assert len(jwara_results) >= 3
        for r in jwara_results:
            assert "ज्वर" in r.sanskrit_name or "JWARA" in r.disease_code

        # Filter by Vataja
        vataja_results = search_morbidity_registry(conn, doshic_filter=DoshicCategory.VATAJA)
        assert len(vataja_results) >= 5
        for r in vataja_results:
            assert r.doshic_category == DoshicCategory.VATAJA

        # Combined search and filter: Vataja Jwara
        combined = search_morbidity_registry(conn, query="Jwara", doshic_filter=DoshicCategory.VATAJA)
        assert len(combined) == 1
        assert combined[0].disease_code == "AYU-DIS-JWARA-VATAJA"
        conn.close()


def test_fhir_condition_resource_generation():
    """Verify generated FHIR Condition resource conforms to ABDM multi-terminology standards."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_fhir.db"
        init_database(db_file)
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row

        crosswalk = get_crosswalk_entry(conn, "AYU-DIS-TAMAKA-SHWASA")
        assert crosswalk is not None

        fhir_json = generate_fhir_condition_resource(
            patient_id="pat-asthma-001",
            diagnosing_arn="ARN-NCISM-2015-8832",
            crosswalk=crosswalk,
            verification_status=VerificationStatus.DIFFERENTIAL_CONFIRMED,
            clinical_notes="Patient presents with orthopneic wheezing and sticky sputum expectoration",
            timestamp=1710892800,
        )

        assert fhir_json["resourceType"] == "Condition"
        assert fhir_json["clinicalStatus"]["coding"][0]["code"] == "active"
        assert fhir_json["verificationStatus"]["coding"][0]["code"] == "differential_confirmed"
        assert fhir_json["subject"]["reference"] == "Patient/pat-asthma-001"
        assert fhir_json["recorder"]["reference"] == "Practitioner/ARN-NCISM-2015-8832"

        # Verify multi-system codings (NAMASTE, ICD-11 TM2, ICD-11 Biomed, ICD-10)
        codings = fhir_json["code"]["coding"]
        systems = [c["system"] for c in codings]
        codes = [c["code"] for c in codings]

        assert "https://namstp.ayush.gov.in/#/morbidity" in systems
        assert "NAMASTE-AYU-045" in codes

        assert "http://id.who.int/icd/release/11/mms/tm2" in systems
        assert "TM2-AYU-TMS" in codes

        assert "http://id.who.int/icd/release/11/mms" in systems
        assert "CA23" in codes

        assert fhir_json["note"][0]["text"].startswith("Patient presents with")
        conn.close()


def test_patient_diagnosis_persistence_and_retrieval():
    """Verify recording and querying of patient dual-coded diagnoses."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_diag_record.db"
        init_database(db_file)
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row

        # Insert test patient
        conn.execute(
            """
            INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("pat-test-diag-001", "aiia-delhi-central-001", "Devendra", "Joshi", "1980-05-12", "MALE", "+919876543299", 1710892800)
        )
        conn.commit()

        diag_input = PatientDiagnosisCodingInput(
            patient_id="pat-test-diag-001",
            disease_code="AYU-DIS-SANDHIGATA-VATA",
            clinical_notes="Bilateral knee crepitation and morning pain without Ama",
            verification_status=VerificationStatus.DIFFERENTIAL_CONFIRMED,
        )

        result = record_patient_diagnosis(
            conn=conn,
            input_data=diag_input,
            diagnosing_arn="ARN-NCISM-2015-8832",
            hospital_id="aiia-delhi-central-001",
        )
        conn.commit()

        assert result.coding_id.startswith("diag-")
        assert result.patient_id == "pat-test-diag-001"
        assert result.disease_crosswalk.disease_code == "AYU-DIS-SANDHIGATA-VATA"
        assert result.disease_crosswalk.icd11_biomed_code == "FA00"
        assert result.verification_status == VerificationStatus.DIFFERENTIAL_CONFIRMED

        # Retrieve patient diagnoses
        diagnoses = get_patient_diagnoses(conn, "pat-test-diag-001")
        assert len(diagnoses) == 1
        assert diagnoses[0].coding_id == result.coding_id
        assert diagnoses[0].disease_crosswalk.namaste_code == "NAMASTE-AYU-022"
        conn.close()
