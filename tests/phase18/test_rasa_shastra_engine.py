"""
Unit Tests for Rasa Shastra & Herbo-Mineral Processing Safety Engine (Phase 18).
"""

import tempfile
from pathlib import Path
import pytest

from core.database import get_sqlite_connection, init_database
from core.exceptions import (
    HeavyMetalExposureExceededException,
    RecordNotFoundException,
    ScheduleE1ShodhanaMissingException,
)
from core.rasa_shastra import (
    SEED_RASA_MINERALS_REGISTRY,
    certify_bhasma_batch_release,
    check_schedule_e1_shodhana_compliance,
    evaluate_heavy_metal_exposure,
    get_mineral_profile,
    initialize_rasa_shastra_tables,
    verify_shodhana_batch,
)
from models.rasa_shastra import (
    BatchPrescriptionItem,
    BhasmaBatchReleaseRequest,
    BhasmaPariksha,
    ElementalAssay,
    HeavyMetalExposureCheckRequest,
    ParticleSizeAnalysis,
    PutaType,
    RasaCategory,
    ShodhanaMethod,
    ShodhanaVerificationRequest,
)


def get_fresh_db():
    """Create isolated SQLite database in a safe temp directory."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test_rasashastra.db"
    init_database(db_path)
    conn = get_sqlite_connection(db_path)
    initialize_rasa_shastra_tables(conn)
    return tmpdir, conn


def test_rasa_minerals_registry_completeness():
    """Verify registry contains 18 classical minerals, metals, and Schedule E(1) poisons."""
    tmpdir, conn = get_fresh_db()
    try:
        assert len(SEED_RASA_MINERALS_REGISTRY) >= 18

        # Check required key mineral entities
        parada = get_mineral_profile("MIN-PARADA", conn)
        assert parada.sanskrit_name.startswith("पारद")
        assert parada.category == RasaCategory.MAHARASA
        assert parada.is_schedule_e1_poison is True
        assert parada.shodhana_required is True

        abhraka = get_mineral_profile("MIN-ABHRAKA", conn)
        assert abhraka.category == RasaCategory.MAHARASA
        assert abhraka.minimum_puta_cycles >= 30
        assert abhraka.standard_puta_type == PutaType.GAJA_PUTA

        tamra = get_mineral_profile("MIN-TAMRA", conn)
        assert tamra.category == RasaCategory.DHATU_SHUDDHA
        assert "Yakridroga" in str(tamra.classical_indications)
        assert "Ashta Maha Dosha" in tamra.toxicity_risk_profile

        vatsanabha = get_mineral_profile("MIN-VATSANABHA", conn)
        assert vatsanabha.category == RasaCategory.VISHA_UPAVISHA
        assert vatsanabha.is_schedule_e1_poison is True
    finally:
        conn.close()
        tmpdir.cleanup()


def test_shodhana_verification_lifecycle():
    """Verify Shodhana detoxification submission, validation, and database persistence."""
    tmpdir, conn = get_fresh_db()
    try:
        req = ShodhanaVerificationRequest(
            batch_id="LOT-GANDHAKA-2026-001",
            mineral_id="MIN-GANDHAKA",
            method=ShodhanaMethod.DHALANA_MELTING_POURING,
            media_used=["Godugdha", "Go-Ghrita"],
            cycles_completed=7,
            organoleptic_shuddhi_confirmed=True,
            verified_by_arn="ARN-NCISM-2015-8832",
            notes="Successfully purified through 7 cycles of Dhalana in milk and ghee.",
        )

        record = verify_shodhana_batch(req, conn)
        assert record.is_verified is True
        assert record.cycles_completed == 7
        assert record.mineral_id == "MIN-GANDHAKA"

        # Check in database
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shodhana_records WHERE batch_id = ?;", ("LOT-GANDHAKA-2026-001",))
        row = cursor.fetchone()
        assert row is not None
        assert row["is_verified"] == 1
    finally:
        conn.close()
        tmpdir.cleanup()


def test_schedule_e1_shodhana_gating_firewall():
    """Ensure Schedule E(1) substances cannot be processed without certified Shodhana."""
    tmpdir, conn = get_fresh_db()
    try:
        # 1. Unpurified Vatsanabha must trigger ScheduleE1ShodhanaMissingException
        with pytest.raises(ScheduleE1ShodhanaMissingException) as exc_info:
            check_schedule_e1_shodhana_compliance("MIN-VATSANABHA", "BATCH-RAW-001", conn)
        assert "Shodhana verification" in str(exc_info.value)

        # 2. Complete Shodhana for Vatsanabha
        shodhana_req = ShodhanaVerificationRequest(
            batch_id="BATCH-VATSANABHA-SHODHITA-001",
            mineral_id="MIN-VATSANABHA",
            method=ShodhanaMethod.SWEDANA_DOLA_YANTRA,
            media_used=["Godugdha (Cow Milk)"],
            cycles_completed=1,
            organoleptic_shuddhi_confirmed=True,
            verified_by_arn="ARN-NCISM-2015-8832",
        )
        verify_shodhana_batch(shodhana_req, conn)

        # 3. Compliance check should now pass
        compliant = check_schedule_e1_shodhana_compliance(
            "MIN-VATSANABHA", "BATCH-VATSANABHA-SHODHITA-001", conn
        )
        assert compliant is True
    finally:
        conn.close()
        tmpdir.cleanup()


def test_classical_bhasma_pariksha_nanoscale_criteria():
    """Verify that all 7 classical tests must pass for Bhasma certification."""
    tmpdir, conn = get_fresh_db()
    try:
        # Standard passing 7-Pariksha
        valid_pariksha = BhasmaPariksha(
            varitara=True,
            unama=True,
            rekhapurna=True,
            apunarbhava=True,
            niruttha=True,
            nis_svadu=True,
            nischandrika=True,
        )

        valid_assay = ElementalAssay(
            lead_pb_ppm=2.1,
            arsenic_as_ppm=0.8,
            cadmium_cd_ppm=0.05,
            mercury_hg_ppm=0.1,
            active_metal_name="Zinc",
            active_metal_percentage=55.4,
            free_ionic_toxic_metal_ppm=0.0,
        )

        valid_psd = ParticleSizeAnalysis(
            d10_microns=0.6,
            d50_microns=2.8,
            d90_microns=8.4,
            nanoscale_percentage=28.5,
        )

        req_pass = BhasmaBatchReleaseRequest(
            batch_id="LOT-YASHADA-BHASMA-001",
            mineral_id="MIN-YASHADA",
            formulation_name="Yashada Bhasma",
            puta_type=PutaType.KUKKUTA_PUTA,
            putas_completed=7,
            classical_pariksha=valid_pariksha,
            elemental_assay=valid_assay,
            particle_size=valid_psd,
            certified_by_arn="ARN-NCISM-2015-8832",
        )

        cert = certify_bhasma_batch_release(req_pass, conn)
        assert cert.is_classical_certified is True
        assert cert.puta_count_adequate is True
        assert cert.heavy_metals_safe is True
        assert cert.particle_size_compliant is True
        assert cert.overall_batch_released is True
        assert len(cert.rejection_reasons) == 0

        # Now test failure when Varitara fails (Bhasma sinks) and Apunarbhava fails (reverts to metal)
        failing_pariksha = BhasmaPariksha(
            varitara=False,  # Fails!
            unama=False,     # Fails!
            rekhapurna=True,
            apunarbhava=False, # Fails!
            niruttha=True,
            nis_svadu=True,
            nischandrika=True,
        )

        req_fail = BhasmaBatchReleaseRequest(
            batch_id="LOT-YASHADA-BHASMA-002",
            mineral_id="MIN-YASHADA",
            formulation_name="Yashada Bhasma",
            puta_type=PutaType.KUKKUTA_PUTA,
            putas_completed=7,
            classical_pariksha=failing_pariksha,
            elemental_assay=valid_assay,
            particle_size=valid_psd,
            certified_by_arn="ARN-NCISM-2015-8832",
        )

        cert_fail = certify_bhasma_batch_release(req_fail, conn)
        assert cert_fail.is_classical_certified is False
        assert cert_fail.overall_batch_released is False
        assert any("Varitara" in r for r in cert_fail.rejection_reasons)
        assert any("Apunarbhava" in r for r in cert_fail.rejection_reasons)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_puta_count_adequacy_enforcement():
    """Verify that insufficient Puta cycles prevent Bhasma batch release."""
    tmpdir, conn = get_fresh_db()
    try:
        # Abhraka Bhasma requires minimum 30 Putas
        valid_pariksha = BhasmaPariksha(
            varitara=True, unama=True, rekhapurna=True, apunarbhava=True,
            niruttha=True, nis_svadu=True, nischandrika=True,
        )
        valid_assay = ElementalAssay(
            lead_pb_ppm=1.5, arsenic_as_ppm=0.5, cadmium_cd_ppm=0.02,
            mercury_hg_ppm=0.05, active_metal_name="Mica Complex",
            active_metal_percentage=98.0, free_ionic_toxic_metal_ppm=0.0,
        )
        valid_psd = ParticleSizeAnalysis(
            d10_microns=0.5, d50_microns=2.2, d90_microns=7.1, nanoscale_percentage=32.0
        )

        # Submit with only 12 Putas instead of 30
        req = BhasmaBatchReleaseRequest(
            batch_id="LOT-ABHRAKA-INCOMPLETE-001",
            mineral_id="MIN-ABHRAKA",
            formulation_name="Abhraka Bhasma (Shataputi in progress)",
            puta_type=PutaType.GAJA_PUTA,
            putas_completed=12,
            classical_pariksha=valid_pariksha,
            elemental_assay=valid_assay,
            particle_size=valid_psd,
            certified_by_arn="ARN-NCISM-2015-8832",
        )

        cert = certify_bhasma_batch_release(req, conn)
        assert cert.puta_count_adequate is False
        assert cert.overall_batch_released is False
        assert any("Puta count inadequate" in r for r in cert.rejection_reasons)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_heavy_metal_elemental_assay_and_particle_size_validation():
    """Verify that AAS/ICP-MS contamination or coarse particle size triggers batch rejection."""
    tmpdir, conn = get_fresh_db()
    try:
        valid_pariksha = BhasmaPariksha(
            varitara=True, unama=True, rekhapurna=True, apunarbhava=True,
            niruttha=True, nis_svadu=True, nischandrika=True,
        )

        # Contaminated assay: Lead = 24.5 ppm (> 10.0 ppm limit) and Arsenic = 5.2 ppm (> 3.0 ppm limit)
        toxic_assay = ElementalAssay(
            lead_pb_ppm=24.5,
            arsenic_as_ppm=5.2,
            cadmium_cd_ppm=0.1,
            mercury_hg_ppm=0.2,
            active_metal_name="Copper",
            active_metal_percentage=52.0,
            free_ionic_toxic_metal_ppm=0.25,  # Exceeds 0.1 limit!
        )

        # Coarse particle size: D50 = 12.5um (> 5um) and nanoscale = 4% (< 15%)
        coarse_psd = ParticleSizeAnalysis(
            d10_microns=3.2,
            d50_microns=12.5,
            d90_microns=28.0,
            nanoscale_percentage=4.0,
        )

        req = BhasmaBatchReleaseRequest(
            batch_id="LOT-TAMRA-FAILED-001",
            mineral_id="MIN-TAMRA",
            formulation_name="Tamra Bhasma",
            puta_type=PutaType.GAJA_PUTA,
            putas_completed=8,
            classical_pariksha=valid_pariksha,
            elemental_assay=toxic_assay,
            particle_size=coarse_psd,
            certified_by_arn="ARN-NCISM-2015-8832",
        )

        cert = certify_bhasma_batch_release(req, conn)
        assert cert.heavy_metals_safe is False
        assert cert.particle_size_compliant is False
        assert cert.overall_batch_released is False
        assert any("Lead (Pb)" in r for r in cert.rejection_reasons)
        assert any("Arsenic (As)" in r for r in cert.rejection_reasons)
        assert any("Free toxic ionic metal" in r for r in cert.rejection_reasons)
        assert any("Median diameter D50" in r for r in cert.rejection_reasons)
    finally:
        conn.close()
        tmpdir.cleanup()


def test_heavy_metal_pde_exposure_and_limit_enforcement():
    """Verify daily Permitted Daily Exposure (PDE) calculus and safety violations."""
    tmpdir, conn = get_fresh_db()
    try:
        # Create a certified safe batch of Swarna Bhasma (Au)
        valid_pariksha = BhasmaPariksha(
            varitara=True, unama=True, rekhapurna=True, apunarbhava=True,
            niruttha=True, nis_svadu=True, nischandrika=True,
        )
        safe_assay = ElementalAssay(
            lead_pb_ppm=1.2,
            arsenic_as_ppm=0.4,
            cadmium_cd_ppm=0.02,
            mercury_hg_ppm=0.05,
            active_metal_name="Gold",
            active_metal_percentage=98.5,
            free_ionic_toxic_metal_ppm=0.0,
        )
        safe_psd = ParticleSizeAnalysis(
            d10_microns=0.4, d50_microns=1.8, d90_microns=5.5, nanoscale_percentage=42.0
        )

        certify_bhasma_batch_release(
            BhasmaBatchReleaseRequest(
                batch_id="LOT-SWARNA-SAFE-001",
                mineral_id="MIN-SUVARNA",
                formulation_name="Swarna Bhasma",
                puta_type=PutaType.VARAHA_PUTA,
                putas_completed=10,
                classical_pariksha=valid_pariksha,
                elemental_assay=safe_assay,
                particle_size=safe_psd,
                certified_by_arn="ARN-NCISM-2015-8832",
            ),
            conn,
        )

        # 1. Evaluate safe therapeutic dose: 30 mg daily for 30 days
        safe_check = evaluate_heavy_metal_exposure(
            HeavyMetalExposureCheckRequest(
                patient_id="patient-001",
                prescriptions=[
                    BatchPrescriptionItem(batch_id="LOT-SWARNA-SAFE-001", daily_dose_mg=30.0, duration_days=30)
                ],
            ),
            conn,
        )
        assert safe_check.is_within_pde_limits is True
        assert safe_check.safety_verdict == "SAFE_AND_COMPLIANT"
        assert safe_check.daily_lead_mg < safe_check.pde_lead_mg_limit

        # 2. Evaluate extreme overdose that exceeds Lead PDE limit
        # Create batch with 9.5 ppm lead (allowed in bulk batch, but high)
        borderline_assay = ElementalAssay(
            lead_pb_ppm=9.5, arsenic_as_ppm=2.8, cadmium_cd_ppm=0.25,
            mercury_hg_ppm=0.8, active_metal_name="Iron",
            active_metal_percentage=54.0, free_ionic_toxic_metal_ppm=0.0,
        )
        certify_bhasma_batch_release(
            BhasmaBatchReleaseRequest(
                batch_id="LOT-LAUHA-BORDERLINE-001",
                mineral_id="MIN-LAUHA",
                formulation_name="Lauha Bhasma",
                puta_type=PutaType.MAHA_PUTA,
                putas_completed=30,
                classical_pariksha=valid_pariksha,
                elemental_assay=borderline_assay,
                particle_size=safe_psd,
                certified_by_arn="ARN-NCISM-2015-8832",
            ),
            conn,
        )

        # Prescribing an excessive daily dose of 1500 mg:
        # Lead daily intake = (9.5 * 1500) / 10^6 = 0.01425 mg > 0.005 mg limit
        with pytest.raises(HeavyMetalExposureExceededException) as exc_info:
            evaluate_heavy_metal_exposure(
                HeavyMetalExposureCheckRequest(
                    patient_id="patient-001",
                    prescriptions=[
                        BatchPrescriptionItem(batch_id="LOT-LAUHA-BORDERLINE-001", daily_dose_mg=1500.0, duration_days=14)
                    ],
                ),
                conn,
            )
        assert "Lead (Pb)" in str(exc_info.value)
    finally:
        conn.close()
        tmpdir.cleanup()
