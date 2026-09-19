"""
Unit Tests for Shalakya Tantra, Netra Kriya Kalpa & ENT Microsurgical Engine (Phase 25).
"""

import tempfile
from pathlib import Path
import pytest

from core.database import get_sqlite_connection, init_database
from core.exceptions import (
    ClinicalGovernanceException,
    RecordNotFoundException,
)
from core.shalakya_tantra import (
    SEED_NETRA_ROGA_CATALOG,
    evaluate_ophthalmic_screening,
    get_netra_roga_profile,
    initialize_shalakya_tables,
    list_all_netra_rogas,
    list_ent_procedures,
    list_tarpana_sessions,
    record_ent_procedure,
    record_tarpana_session,
)
from models.shalakya_tantra import (
    EntProcedureCreate,
    EntTherapyType,
    KriyaKalpaType,
    NetraMandala,
    NetraPatala,
    OphthalmicScreeningRequest,
    SadhyaAsadhyata,
    TarpanaSessionCreate,
)


def get_fresh_db_with_patient():
    """Create isolated SQLite database with a seeded patient in a safe temp directory."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_shalakya.db"
    init_database(db_path)
    conn = get_sqlite_connection(db_path)
    initialize_shalakya_tables(conn)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patients (patient_id, hospital_id, first_name, last_name, dob, gender, contact_phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("PAT-SHALAKYA-001", "aiia-delhi-central-001", "Radha", "Nair", "1982-08-14", "FEMALE", "+919876543002", 1700000000)
    )
    return tmpdir, conn


def test_netra_roga_catalog_completeness():
    """Verify classical Netra Roga catalog covers all 6 Mandalas and 4 Patalas with ICD-11 coding."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        rogas = list_all_netra_rogas(conn)
        assert len(rogas) >= 20

        mandalas_found = {r.anatomical_mandala for r in rogas}
        assert NetraMandala.PAKSHMA in mandalas_found
        assert NetraMandala.VARTMA in mandalas_found
        assert NetraMandala.SHUKLA in mandalas_found
        assert NetraMandala.KRISHNA in mandalas_found
        assert NetraMandala.DRISHTI in mandalas_found
        assert NetraMandala.SARVAGATA in mandalas_found

        patalas_found = {r.anatomical_patala for r in rogas}
        assert NetraPatala.BAHYA in patalas_found
        assert NetraPatala.PRATHAMA in patalas_found
        assert NetraPatala.DWITIYA in patalas_found
        assert NetraPatala.TRITIYA in patalas_found
        assert NetraPatala.CHATURTHA in patalas_found

        # Verify specific condition specs
        timira1 = get_netra_roga_profile("NETRA-DRI-01", conn)
        assert timira1.anatomical_patala == NetraPatala.PRATHAMA
        assert KriyaKalpaType.TARPANA in timira1.kriya_kalpa_indications
        assert "9D00" in timira1.icd11_mapping

        linganasha = get_netra_roga_profile("NETRA-DRI-04", conn)
        assert linganasha.sadhya_asadhyata == SadhyaAsadhyata.ASADHYA
        assert KriyaKalpaType.TARPANA in linganasha.contraindicated_procedures
    finally:
        conn.close()
        tmpdir.cleanup()


def test_netra_roga_filtering():
    """Verify filtering by Mandala and Patala."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        vartma_rogas = list_all_netra_rogas(conn, mandala=NetraMandala.VARTMA)
        assert len(vartma_rogas) >= 4
        assert all(r.anatomical_mandala == NetraMandala.VARTMA for r in vartma_rogas)

        tritiya_rogas = list_all_netra_rogas(conn, patala=NetraPatala.TRITIYA)
        assert len(tritiya_rogas) >= 1
        assert tritiya_rogas[0].roga_code == "NETRA-DRI-03"
    finally:
        conn.close()
        tmpdir.cleanup()


def test_tarpana_retention_matrakalas_and_doshic_rules():
    """Verify Doshic Matrakala duration calculations and post-procedure precautions."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Vataja condition -> 1000 Matrakalas = 200 seconds
        session_vata = TarpanaSessionCreate(
            patient_id="PAT-SHALAKYA-001",
            eye_side="BILATERAL",
            ghrita_used="Mahatriphala Ghrita",
            doshic_indication="VATAJA",
            clinical_indication="Severe dry eye syndrome and visual strain (Shushkakshipaka)",
            practitioner_arn="AY-DL-2024-998811",
        )
        res_vata = record_tarpana_session(conn, "aiia-delhi-central-001", session_vata)
        assert res_vata.retention_matrakalas == 1000
        assert res_vata.retention_duration_seconds == 200
        assert any("complete abstention from VDU screens" in p for p in res_vata.post_procedure_precautions)

        # Pittaja condition -> 800 Matrakalas = 160 seconds
        session_pitta = TarpanaSessionCreate(
            patient_id="PAT-SHALAKYA-001",
            eye_side="LEFT",
            ghrita_used="Patoladi Ghrita",
            doshic_indication="PITTAJA",
            clinical_indication="Pittadagdha Drishti / Photophobia",
            practitioner_arn="AY-DL-2024-998811",
        )
        res_pitta = record_tarpana_session(conn, "aiia-delhi-central-001", session_pitta)
        assert res_pitta.retention_matrakalas == 800
        assert res_pitta.retention_duration_seconds == 160

        # Custom explicit Matrakalas override
        session_custom = TarpanaSessionCreate(
            patient_id="PAT-SHALAKYA-001",
            eye_side="RIGHT",
            ghrita_used="Jeevantyadi Ghrita",
            doshic_indication="KAPHAJA",
            clinical_indication="Mild Timira",
            retention_matrakalas=750,
            practitioner_arn="AY-DL-2024-998811",
        )
        res_custom = record_tarpana_session(conn, "aiia-delhi-central-001", session_custom)
        assert res_custom.retention_matrakalas == 750
        assert res_custom.retention_duration_seconds == 150

        # Verify historical listing
        history = list_tarpana_sessions("PAT-SHALAKYA-001", conn)
        assert len(history) == 3
    finally:
        conn.close()
        tmpdir.cleanup()


def test_acute_adhimantha_glaucoma_firewall_high_iop():
    """Verify tonometry IOP >= 30 mmHg triggers CRITICAL_EMERGENCY and blocks Tarpana."""
    req = OphthalmicScreeningRequest(
        patient_id="PAT-SHALAKYA-001",
        presenting_symptoms=["Severe eye pain", "Blurred vision"],
        intraocular_pressure_mmhg=42.5,
        severe_ocular_pain=True,
        evaluator_arn="AY-DL-2024-998811",
    )
    res = evaluate_ophthalmic_screening(req)
    assert res.triage_level == "CRITICAL_EMERGENCY"
    assert res.adhimantha_glaucoma_firewall_triggered is True
    assert KriyaKalpaType.TARPANA in res.contraindicated_kriya_kalpas
    assert KriyaKalpaType.SEKA in res.contraindicated_kriya_kalpas
    assert "IV Mannitol" in "".join(res.clinical_action_plan)


def test_acute_adhimantha_glaucoma_firewall_symptom_triad():
    """Verify acute pain + hemicrania + steamy cornea + halos triggers firewall even without tonometry."""
    req = OphthalmicScreeningRequest(
        patient_id="PAT-SHALAKYA-001",
        presenting_symptoms=["Agonizing eye pain", "Hemicranial headache", "Rainbow halos around lamps"],
        severe_ocular_pain=True,
        hemicrania_headache=True,
        halos_around_lights=True,
        corneal_edema_steamy=True,
        pupil_fixed_mid_dilated=True,
        evaluator_arn="AY-DL-2024-998811",
    )
    res = evaluate_ophthalmic_screening(req)
    assert res.triage_level == "CRITICAL_EMERGENCY"
    assert res.adhimantha_glaucoma_firewall_triggered is True
    assert "Acute Angle-Closure Glaucoma Crisis" in res.suspected_condition


def test_ophthalmic_screening_urgent_and_routine():
    """Verify subacute IOP elevation is flagged URGENT and mild asthenopia is ROUTINE."""
    # Urgent: Mild IOP elevation (25 mmHg)
    req_urgent = OphthalmicScreeningRequest(
        patient_id="PAT-SHALAKYA-001",
        presenting_symptoms=["Mild ocular heaviness"],
        intraocular_pressure_mmhg=25.0,
        evaluator_arn="AY-DL-2024-998811",
    )
    res_urgent = evaluate_ophthalmic_screening(req_urgent)
    assert res_urgent.triage_level == "URGENT"
    assert res_urgent.adhimantha_glaucoma_firewall_triggered is False
    assert KriyaKalpaType.TARPANA in res_urgent.contraindicated_kriya_kalpas

    # Routine: Dry eyes with normal pressure
    req_routine = OphthalmicScreeningRequest(
        patient_id="PAT-SHALAKYA-001",
        presenting_symptoms=["Foreign body sensation", "Dryness in both eyes"],
        intraocular_pressure_mmhg=15.0,
        evaluator_arn="AY-DL-2024-998811",
    )
    res_routine = evaluate_ophthalmic_screening(req_routine)
    assert res_routine.triage_level == "ROUTINE"
    assert len(res_routine.contraindicated_kriya_kalpas) == 0


def test_ent_karna_purana_success_and_perforation_firewall():
    """Verify Karna Purana executes safely with intact eardrum but blocks on perforation."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        # Safe Karna Purana
        safe_proc = EntProcedureCreate(
            patient_id="PAT-SHALAKYA-001",
            therapy_type=EntTherapyType.KARNA_PURANA,
            anatomical_site="BILATERAL_EARS",
            medicated_oil_used="Bilva Taila",
            dosage_drops_or_ml="10 drops per ear",
            eardrum_perforated=False,
            observations="Patient with bilateral Karnanada (tinnitus) and mild hearing impairment",
            practitioner_arn="AY-DL-2024-998811",
        )
        res_safe = record_ent_procedure(conn, "aiia-delhi-central-001", safe_proc)
        assert res_safe.procedure_id.startswith("ent-")
        assert res_safe.safety_cleared is True

        # Perforation check firewall
        unsafe_proc = EntProcedureCreate(
            patient_id="PAT-SHALAKYA-001",
            therapy_type=EntTherapyType.KARNA_PURANA,
            anatomical_site="LEFT_EAR",
            medicated_oil_used="Ksharatila Taila",
            dosage_drops_or_ml="8 drops",
            eardrum_perforated=True,  # Perforated!
            observations="Chronic suppurative otitis media with central perforation",
            practitioner_arn="AY-DL-2024-998811",
        )
        with pytest.raises(ClinicalGovernanceException) as exc_info:
            record_ent_procedure(conn, "aiia-delhi-central-001", unsafe_proc)
        assert "Perforated tympanic membrane" in str(exc_info.value)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_ent_nasya_and_procedure_listing():
    """Verify Nasya procedures are recorded and retrievable."""
    tmpdir, conn = get_fresh_db_with_patient()
    try:
        nasya_proc = EntProcedureCreate(
            patient_id="PAT-SHALAKYA-001",
            therapy_type=EntTherapyType.PRATIMARSHA_NASYA,
            anatomical_site="BILATERAL_NASAL",
            medicated_oil_used="Anu Taila",
            dosage_drops_or_ml="2 drops each nostril",
            eardrum_perforated=False,
            observations="Daily prophylactic Dinacharya nasya for prevention of Shiroroga",
            practitioner_arn="AY-DL-2024-998811",
        )
        res_nasya = record_ent_procedure(conn, "aiia-delhi-central-001", nasya_proc)
        assert res_nasya.therapy_type == EntTherapyType.PRATIMARSHA_NASYA

        # Retrieve history
        history = list_ent_procedures("PAT-SHALAKYA-001", conn)
        assert len(history) == 1
        assert history[0].procedure_id == res_nasya.procedure_id
    finally:
        conn.close()
        tmpdir.cleanup()
