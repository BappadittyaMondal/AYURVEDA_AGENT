"""SQLite Write-Ahead Logging (WAL) Persistent Edge Database Engine."""
import hashlib
import json
import sqlite3
import time
from enum import Enum
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, Optional

from config.settings import get_settings
from core.security import ClinicalRole, hash_password


def get_sqlite_connection(database_path: Optional[Path] = None) -> sqlite3.Connection:
    """Instantiate and configure an ACID-compliant SQLite connection with WAL pragmas."""
    settings = get_settings()
    db_file = database_path or settings.database_path
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(db_file),
        timeout=settings.sqlite_busy_timeout_ms / 1000.0,
        isolation_level=None  # Enable autocommit mode; transactions handled explicitly
    )
    conn.row_factory = sqlite3.Row

    # Enforce performance and safety PRAGMAs
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute(f"PRAGMA journal_mode = {settings.sqlite_journal_mode};")
    cursor.execute(f"PRAGMA synchronous = {settings.sqlite_synchronous};")
    cursor.execute(f"PRAGMA busy_timeout = {settings.sqlite_busy_timeout_ms};")
    cursor.close()

    return conn


@contextmanager
def get_db(database_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for acquiring and safely releasing SQLite connections."""
    conn = get_sqlite_connection(database_path)
    try:
        yield conn
    finally:
        conn.close()


class DatabaseEngineType(str, Enum):
    SQLITE_WAL = "SQLITE_WAL"
    POSTGRESQL_RLS = "POSTGRESQL_RLS"


class DatabaseEngineAdapter:
    """
    Dual Database Engine Adapter.
    Architectural abstraction enabling seamless operation across:
    1. Local / Edge SQLite with Write-Ahead Logging (WAL) for rural clinics, offline OPDs, and local embedded nodes.
    2. Apex Central PostgreSQL with Row-Level Security (RLS) for tertiary hospital clusters and high-concurrency cloud deployments.
    """
    def __init__(
        self,
        engine_type: DatabaseEngineType = DatabaseEngineType.SQLITE_WAL,
        sqlite_path: Optional[Path] = None,
        postgres_dsn: Optional[str] = None
    ):
        self.engine_type = engine_type
        self.sqlite_path = sqlite_path
        self.postgres_dsn = postgres_dsn

    def get_connection(self) -> Any:
        """Acquire a raw database connection according to the active engine type."""
        if self.engine_type == DatabaseEngineType.SQLITE_WAL:
            return get_sqlite_connection(self.sqlite_path)
        elif self.engine_type == DatabaseEngineType.POSTGRESQL_RLS:
            if not self.postgres_dsn:
                raise ValueError("PostgreSQL DSN must be configured when using POSTGRESQL_RLS engine.")
            try:
                import psycopg2
                conn = psycopg2.connect(self.postgres_dsn)
                return conn
            except ImportError:
                raise RuntimeError(
                    "psycopg2 library is required for POSTGRESQL_RLS mode. "
                    "Install via 'pip install psycopg2-binary' or use SQLITE_WAL."
                )
        else:
            raise ValueError(f"Unsupported database engine type: {self.engine_type}")

    @contextmanager
    def session(
        self,
        tenant_hospital_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role: Optional[str] = None
    ) -> Generator[Any, None, None]:
        """
        Session context manager enforcing multi-tenant isolation.
        In PostgreSQL mode, applies Row-Level Security (RLS) session variables (SET app.current_hospital_id).
        In SQLite mode, validates connection and provides transactional isolation.
        """
        conn = self.get_connection()
        try:
            if self.engine_type == DatabaseEngineType.POSTGRESQL_RLS and tenant_hospital_id:
                cursor = conn.cursor()
                cursor.execute("SET app.current_hospital_id = %s;", (tenant_hospital_id,))
                if user_id:
                    cursor.execute("SET app.current_user_id = %s;", (user_id,))
                if role:
                    cursor.execute("SET app.current_role = %s;", (role,))
                cursor.close()
            yield conn
        finally:
            conn.close()

    def verify_engine_health(self) -> Dict[str, Any]:
        """Validates database engine connectivity, latency, and security configuration."""
        start = time.time()
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            cursor.fetchone()
            latency_ms = round((time.time() - start) * 1000.0, 2)

            wal_enabled = False
            if self.engine_type == DatabaseEngineType.SQLITE_WAL:
                cursor.execute("PRAGMA journal_mode;")
                row = cursor.fetchone()
                wal_enabled = (row[0].upper() == "WAL") if row else False

            cursor.close()
            return {
                "status": "HEALTHY",
                "engine_type": self.engine_type.value,
                "latency_ms": latency_ms,
                "wal_enabled": wal_enabled,
                "rls_enforced": self.engine_type == DatabaseEngineType.POSTGRESQL_RLS
            }
        finally:
            conn.close()


def append_audit_log(
    conn: sqlite3.Connection,
    hospital_id: str,
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    details: Dict[str, Any]
) -> str:
    """Append an immutable audit entry protected by SHA-256 hash chaining."""
    cursor = conn.cursor()
    # Fetch last entry hash
    cursor.execute(
        "SELECT entry_hash FROM audit_ledger WHERE hospital_id = ? ORDER BY id DESC LIMIT 1;",
        (hospital_id,)
    )
    row = cursor.fetchone()
    prev_hash = row["entry_hash"] if row else "GENESIS_BLOCK_AYURVEDA_AGENT_V3"

    timestamp = int(time.time() * 1000)
    details_str = json.dumps(details, sort_keys=True)
    hash_payload = f"{prev_hash}|{hospital_id}|{actor_id}|{action}|{entity_type}|{entity_id}|{details_str}|{timestamp}"
    entry_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

    cursor.execute(
        """
        INSERT INTO audit_ledger (
            hospital_id, actor_id, action, entity_type, entity_id, details_json, timestamp, prev_hash, entry_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (hospital_id, actor_id, action, entity_type, entity_id, details_str, timestamp, prev_hash, entry_hash)
    )
    return entry_hash


def init_database(database_path: Optional[Path] = None) -> None:
    """Bootstrap core database tables and seed baseline institutional accounts."""
    settings = get_settings()
    with get_db(database_path) as conn:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE;")
        try:
            # 1. Hospitals (Multi-tenancy isolation table)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS hospitals (
                hospital_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                nabh_accreditation_status TEXT NOT NULL DEFAULT 'ACCREDITED_LEVEL_2',
                state_council_code TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 2. Institutional Staff & Users
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                hospital_id TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                arn TEXT,  -- Ayush Registration Number (NCISM)
                role TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT
            );
            """)

            # 3. Master Patient Index (MPI)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                patient_id TEXT PRIMARY KEY,
                hospital_id TEXT NOT NULL,
                abha_id TEXT UNIQUE,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                dob TEXT NOT NULL,
                gender TEXT NOT NULL,
                contact_phone TEXT,
                prakriti_vata REAL DEFAULT 0.3333,
                prakriti_pitta REAL DEFAULT 0.3333,
                prakriti_kapha REAL DEFAULT 0.3334,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT
            );
            """)

            # 4. Immutable Audit Ledger with SHA-256 Chaining
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hospital_id TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                details_json TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                prev_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT
            );
            """)

            # 5. NCISM Accredited Practitioners Registry
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS practitioners (
                arn TEXT PRIMARY KEY,  -- Format: ARN-NCISM-YYYY-XXXX
                hospital_id TEXT NOT NULL,
                full_name TEXT NOT NULL,
                qualification TEXT NOT NULL,  -- BAMS, MD_AYU, MS_AYU, PHD_AYU
                university TEXT NOT NULL,
                registration_year INTEGER NOT NULL,
                state_council TEXT NOT NULL,
                is_verified INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT
            );
            """)

            # 6. Prakriti Constitutional Assessment Store
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS prakriti_assessments (
                assessment_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                evaluated_by_arn TEXT NOT NULL,
                vata_score REAL NOT NULL,
                pitta_score REAL NOT NULL,
                kapha_score REAL NOT NULL,
                classification TEXT NOT NULL,
                answers_json TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT
            );
            """)

            # 7. Dynamic Vikriti Pathological Assessment Store
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS vikriti_assessments (
                assessment_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                evaluated_by_arn TEXT NOT NULL,
                vata_v REAL NOT NULL,
                pitta_v REAL NOT NULL,
                kapha_v REAL NOT NULL,
                kl_divergence REAL NOT NULL,
                mahalanobis_dist REAL NOT NULL,
                vsi_score REAL NOT NULL,
                severity_tier TEXT NOT NULL,
                deltas_json TEXT NOT NULL,
                answers_json TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT
            );
            """)

            # 8. Ashtavidha Pariksha 8-Fold Examination Store
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ashtavidha_examinations (
                exam_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                examiner_arn TEXT NOT NULL,
                nadi_json TEXT NOT NULL,
                mutra_json TEXT NOT NULL,
                mala_json TEXT NOT NULL,
                jihwa_json TEXT NOT NULL,
                shabda_json TEXT NOT NULL,
                sparsha_json TEXT NOT NULL,
                drik_json TEXT NOT NULL,
                akriti_json TEXT NOT NULL,
                vata_score REAL NOT NULL,
                pitta_score REAL NOT NULL,
                kapha_score REAL NOT NULL,
                primary_dosha TEXT NOT NULL,
                secondary_dosha TEXT,
                ama_suspected INTEGER NOT NULL DEFAULT 0,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT
            );
            """)

            # 9. Dashavidha Pariksha 10-Fold Systemic Assessment Store
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dashavidha_assessments (
                assessment_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                evaluator_arn TEXT NOT NULL,
                dushya_json TEXT NOT NULL,
                desha_json TEXT NOT NULL,
                bala_json TEXT NOT NULL,
                anala_json TEXT NOT NULL,
                ahara_json TEXT NOT NULL,
                rogi_bala REAL NOT NULL,
                roga_bala REAL NOT NULL,
                rogi_roga_ratio REAL NOT NULL,
                eligibility TEXT NOT NULL,
                rationale TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT
            );
            """)

            # 10. Nadi Waveform Telemetry DSP Sessions
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS nadi_telemetry_sessions (
                session_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                sampling_rate_hz INTEGER NOT NULL,
                raw_samples_count INTEGER NOT NULL,
                heart_rate_bpm REAL NOT NULL,
                doshic_power_v REAL NOT NULL,
                doshic_power_p REAL NOT NULL,
                doshic_power_k REAL NOT NULL,
                primary_gati TEXT NOT NULL,
                spectral_metrics_json TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT
            );
            """)

            # 11. Taila Bindu Pariksha Diagnostic Fluid Dynamics Store
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS taila_bindu_sessions (
                session_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                evaluator_arn TEXT NOT NULL,
                urine_temp REAL NOT NULL,
                surface_tension REAL NOT NULL,
                spreading_coeff REAL NOT NULL,
                spreading_velocity REAL NOT NULL,
                eccentricity REAL NOT NULL,
                circularity REAL NOT NULL,
                direction TEXT NOT NULL,
                fragment_count INTEGER NOT NULL,
                submerged INTEGER NOT NULL DEFAULT 0,
                doshic_shape TEXT NOT NULL,
                prognosis_verdict TEXT NOT NULL,
                commentary TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT
            );
            """)

            # 12. Jihwa Pariksha Computer Vision & Micro-Colorimetry Store
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS jihwa_examinations (
                exam_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                examiner_arn TEXT NOT NULL,
                image_hash TEXT,
                coating_ratio REAL NOT NULL,
                coating_thickness TEXT NOT NULL,
                dominant_color TEXT NOT NULL,
                fissure_density REAL NOT NULL,
                cie_l REAL NOT NULL,
                cie_a REAL NOT NULL,
                cie_b REAL NOT NULL,
                ama_score REAL NOT NULL,
                vata_score REAL NOT NULL,
                pitta_score REAL NOT NULL,
                kapha_score REAL NOT NULL,
                primary_dosha TEXT NOT NULL,
                is_sama INTEGER NOT NULL DEFAULT 0,
                findings_json TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT
            );
            """)

            # 13. Quantitative Ama Grading Index & Agni Gating Store
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ama_agni_assessments (
                assessment_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                evaluator_arn TEXT NOT NULL,
                agi_score REAL NOT NULL,
                ama_grade TEXT NOT NULL,
                agni_type TEXT NOT NULL,
                agni_vector_json TEXT NOT NULL,
                symptoms_json TEXT NOT NULL,
                shodhana_permitted INTEGER NOT NULL DEFAULT 0,
                gating_status TEXT NOT NULL,
                therapeutic_directives_json TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT
            );
            """)

            # 14. Dhatu Sarata Tissue Vitality Store
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dhatu_sarata_assessments (
                assessment_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                evaluator_arn TEXT NOT NULL,
                overall_sarata_index REAL NOT NULL,
                sarata_tier TEXT NOT NULL,
                dhatu_scores_json TEXT NOT NULL,
                vulnerable_dhatus_json TEXT NOT NULL,
                rasayana_directives_json TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT
            );
            """)

            # 15. Srotas Pathology & Khavaigunya Store
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS srotas_assessments (
                assessment_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                evaluator_arn TEXT NOT NULL,
                overall_srotas_index REAL NOT NULL,
                vulnerable_channels_count INTEGER NOT NULL,
                channel_details_json TEXT NOT NULL,
                khavaigunya_channels_json TEXT NOT NULL,
                srotoshodhana_directives_json TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT
            );
            """)

            # 16. Shat Kriya Kala Pathological Stage Store
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS kriya_kala_assessments (
                assessment_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                evaluator_arn TEXT NOT NULL,
                current_stage TEXT NOT NULL,
                pathological_progression_index REAL NOT NULL,
                stage_probabilities_json TEXT NOT NULL,
                prodromal_symptoms_json TEXT NOT NULL,
                manifest_symptoms_json TEXT NOT NULL,
                complications_json TEXT NOT NULL,
                reversibility_percentage REAL NOT NULL,
                curability_prognosis TEXT NOT NULL,
                therapeutic_window_directive TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT
            );
            """)

            # 17. Roga Rogi Bala Ganan Yantra Store
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS roga_rogi_bala_assessments (
                assessment_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                evaluator_arn TEXT NOT NULL,
                rogi_bala_score REAL NOT NULL,
                roga_bala_score REAL NOT NULL,
                bala_ratio REAL NOT NULL,
                bala_differential REAL NOT NULL,
                therapeutic_category TEXT NOT NULL,
                dosage_scalar REAL NOT NULL,
                shodhana_eligibility_status TEXT NOT NULL,
                governor_directives_json TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT
            );
            """)

            # 18. Nidana Panchaka Diagnostic Knowledge Graph & Differential Diagnosis Store
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS nidana_panchaka_assessments (
                assessment_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                evaluator_arn TEXT NOT NULL,
                primary_diagnosis_code TEXT NOT NULL,
                primary_diagnosis_name TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                match_score REAL NOT NULL,
                presented_roopa_json TEXT NOT NULL,
                presented_nidana_json TEXT NOT NULL,
                presented_purvaroopa_json TEXT NOT NULL,
                upashaya_trials_json TEXT NOT NULL,
                differentials_json TEXT NOT NULL,
                samprapti_ghatakas_json TEXT NOT NULL,
                pratyatma_linga_matched_json TEXT NOT NULL,
                clinical_recommendations_json TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT
            );
            """)

            # 19. Classical Disease Taxonomy & Morbidity Dual-Coding Registry (Ashtodara Shata & AYUSH Crosswalk)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS disease_classification_registry (
                disease_code TEXT PRIMARY KEY,
                sanskrit_name TEXT NOT NULL,
                english_name TEXT NOT NULL,
                namaste_code TEXT NOT NULL,
                icd11_tm2_code TEXT NOT NULL,
                icd11_biomed_code TEXT NOT NULL,
                icd10_code TEXT NOT NULL,
                doshic_category TEXT NOT NULL,
                classical_text_source TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 20. Patient Diagnosis Dual-Coding & FHIR Condition Store
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS patient_diagnosis_codings (
                coding_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                diagnosing_arn TEXT NOT NULL,
                disease_code TEXT NOT NULL,
                clinical_notes TEXT,
                verification_status TEXT NOT NULL,
                fhir_condition_json TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (hospital_id) ON DELETE RESTRICT,
                FOREIGN KEY (disease_code) REFERENCES disease_classification_registry (disease_code) ON DELETE RESTRICT
            );
            """)

            # 21. Classical Herbology (Dravya Guna) Knowledge Graph & Phytochemical Registry
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dravyaguna_herbal_registry (
                herb_id TEXT PRIMARY KEY,
                sanskrit_name TEXT NOT NULL,
                botanical_name TEXT NOT NULL,
                botanical_family TEXT NOT NULL,
                classical_synonyms_json TEXT NOT NULL,
                rasa_json TEXT NOT NULL,
                guna_json TEXT NOT NULL,
                veerya TEXT NOT NULL,
                vipaka TEXT NOT NULL,
                prabhava TEXT,
                doshic_karma_json TEXT NOT NULL,
                therapeutics_karma_json TEXT NOT NULL,
                phytochemicals_json TEXT NOT NULL,
                parts_used_json TEXT NOT NULL,
                dosage_range_json TEXT NOT NULL,
                contraindications_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 22. Classical Formulation Architecture (Bhaishajya Kalpana) Registry
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS formulations_registry (
                formulation_id TEXT PRIMARY KEY,
                sanskrit_name TEXT NOT NULL,
                kalpana_form TEXT NOT NULL,
                classical_reference TEXT NOT NULL,
                ingredients_json TEXT NOT NULL,
                composite_veerya TEXT NOT NULL,
                composite_vipaka TEXT NOT NULL,
                doshic_modulation_json TEXT NOT NULL,
                cardinal_indications_json TEXT NOT NULL,
                standard_anupana TEXT NOT NULL,
                dosage_standard_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 23. Anupana Carrier & Vehicle Matrix
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS anupana_registry (
                anupana_id TEXT PRIMARY KEY,
                sanskrit_name TEXT NOT NULL,
                english_name TEXT NOT NULL,
                doshic_affinity TEXT NOT NULL,
                carrier_properties_json TEXT NOT NULL,
                contraindications_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 24. Rasa Shastra Mineral & Herbo-Mineral Registry
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS rasa_minerals_registry (
                mineral_id TEXT PRIMARY KEY,
                sanskrit_name TEXT NOT NULL,
                english_name TEXT NOT NULL,
                chemical_formula TEXT NOT NULL,
                category TEXT NOT NULL,
                is_schedule_e1_poison INTEGER NOT NULL,
                shodhana_required INTEGER NOT NULL,
                standard_shodhana_method TEXT NOT NULL,
                standard_shodhana_media_json TEXT NOT NULL,
                minimum_shodhana_cycles INTEGER NOT NULL,
                standard_puta_type TEXT,
                minimum_puta_cycles INTEGER NOT NULL,
                therapeutic_dose_mg_min REAL NOT NULL,
                therapeutic_dose_mg_max REAL NOT NULL,
                classical_indications_json TEXT NOT NULL,
                toxicity_risk_profile TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 25. Shodhana (Purification/Detoxification) Process Records
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS shodhana_records (
                record_id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                mineral_id TEXT NOT NULL,
                method TEXT NOT NULL,
                media_used_json TEXT NOT NULL,
                cycles_completed INTEGER NOT NULL,
                verified_by_arn TEXT NOT NULL,
                organoleptic_shuddhi_confirmed INTEGER NOT NULL,
                is_verified INTEGER NOT NULL,
                notes TEXT,
                created_at INTEGER NOT NULL
            );
            """)

            # 26. Bhasma Nanocrystalline Batches & Analytical Release Dossiers
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS bhasma_batches (
                batch_id TEXT PRIMARY KEY,
                mineral_id TEXT NOT NULL,
                formulation_name TEXT NOT NULL,
                puta_type TEXT NOT NULL,
                putas_completed INTEGER NOT NULL,
                classical_pariksha_json TEXT NOT NULL,
                elemental_assay_json TEXT NOT NULL,
                particle_size_json TEXT NOT NULL,
                is_classical_certified INTEGER NOT NULL,
                is_physicochemical_certified INTEGER NOT NULL,
                is_released INTEGER NOT NULL,
                rejection_reasons_json TEXT NOT NULL,
                certified_by_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 27. Panchakarma Treatment Plans & Protocols
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS panchakarma_treatment_plans (
                plan_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                procedure_type TEXT NOT NULL,
                target_shuddhi_tier TEXT NOT NULL,
                current_stage TEXT NOT NULL,
                purva_karma_data_json TEXT NOT NULL,
                prescribed_by_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 28. Panchakarma Bedside Real-Time Vega Logging
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS panchakarma_bedside_vegas (
                vega_id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                bout_number INTEGER NOT NULL,
                time_recorded INTEGER NOT NULL,
                output_volume_ml REAL NOT NULL,
                dominant_content TEXT NOT NULL,
                vitals_bp_systolic INTEGER NOT NULL,
                vitals_bp_diastolic INTEGER NOT NULL,
                vitals_pulse_bpm INTEGER NOT NULL,
                attending_nurse_id TEXT NOT NULL,
                clinical_notes TEXT
            );
            """)

            # 29. Panchakarma Chaturvidha Shuddhi & Samsarjana Krama Assessments
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS panchakarma_shuddhi_assessments (
                assessment_id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                vaigiki_vega_count INTEGER NOT NULL,
                maniki_total_volume_ml REAL NOT NULL,
                antiki_milestone TEXT NOT NULL,
                laingiki_symptoms_json TEXT NOT NULL,
                overall_shuddhi_grade TEXT NOT NULL,
                samsarjana_krama_plan_json TEXT NOT NULL,
                atiyoga_complications_json TEXT NOT NULL,
                assessed_by_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 30. Upakarma & Bahya Parimarjana Therapies Catalog
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS upakarma_therapies_catalog (
                therapy_id TEXT PRIMARY KEY,
                sanskrit_name TEXT NOT NULL,
                modality_code TEXT NOT NULL,
                target_temperature_min_c REAL NOT NULL,
                target_temperature_max_c REAL NOT NULL,
                max_safe_temperature_c REAL NOT NULL,
                standard_duration_minutes INTEGER NOT NULL,
                recommended_media_json TEXT NOT NULL,
                cardinal_indications_json TEXT NOT NULL,
                contraindications_json TEXT NOT NULL,
                doshic_affinity TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 31. Upakarma Clinical Session Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS upakarma_session_logs (
                session_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                therapy_id TEXT NOT NULL,
                medium_used TEXT NOT NULL,
                operating_temperature_c REAL NOT NULL,
                duration_minutes INTEGER NOT NULL,
                flow_rate_ml_sec REAL,
                height_cm REAL,
                lepa_thickness_mm REAL,
                pre_vitals_bp TEXT NOT NULL,
                post_vitals_bp TEXT NOT NULL,
                therapist_id TEXT NOT NULL,
                adverse_events_json TEXT NOT NULL,
                clinical_notes TEXT,
                created_at INTEGER NOT NULL
            );
            """)

            # 32. Classical Ahara Varga Ingredients & Nutrition Catalog
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS diet_ingredients_catalog (
                ingredient_id TEXT PRIMARY KEY,
                sanskrit_name TEXT NOT NULL,
                english_name TEXT NOT NULL,
                ahara_varga TEXT NOT NULL,
                rasa TEXT NOT NULL,
                veerya TEXT NOT NULL,
                vipaka TEXT NOT NULL,
                guna_json TEXT NOT NULL,
                doshic_effect_json TEXT NOT NULL,
                calories_per_100g REAL NOT NULL,
                protein_g REAL NOT NULL,
                carbs_g REAL NOT NULL,
                fat_g REAL NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 33. Disease-Specific Pathya & Apathya Registry
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS disease_pathya_apathya_registry (
                registry_id TEXT PRIMARY KEY,
                disease_code TEXT NOT NULL,
                disease_name TEXT NOT NULL,
                pathya_ahara_json TEXT NOT NULL,
                apathya_ahara_json TEXT NOT NULL,
                pathya_vihara_json TEXT NOT NULL,
                apathya_vihara_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 34. Patient Clinical Diet Prescriptions & Viruddha Ahara Audits
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS patient_diet_prescriptions (
                diet_plan_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                diagnosis_code TEXT NOT NULL,
                target_calories REAL NOT NULL,
                meals_json TEXT NOT NULL,
                viruddha_check_passed INTEGER NOT NULL,
                viruddha_violations_json TEXT NOT NULL,
                prescribed_by_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 35. Swasthavritta Dinacharya Protocol Steps Catalog
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS swasthavritta_dinacharya_catalog (
                step_id TEXT PRIMARY KEY,
                step_name TEXT NOT NULL,
                sanskrit_name TEXT NOT NULL,
                ideal_time_window TEXT NOT NULL,
                doshic_benefit TEXT NOT NULL,
                description TEXT NOT NULL,
                contraindications_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 36. Swasthavritta Ritucharya & Seasonal Shodhana Catalog
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS swasthavritta_ritucharya_catalog (
                ritu_code TEXT PRIMARY KEY,
                ritu_name TEXT NOT NULL,
                sanskrit_name TEXT NOT NULL,
                ayana TEXT NOT NULL,
                english_months TEXT NOT NULL,
                dominant_rasa TEXT NOT NULL,
                dominant_mahabhuta TEXT NOT NULL,
                doshic_sanchaya TEXT NOT NULL,
                doshic_prakopa TEXT NOT NULL,
                doshic_prashamana TEXT NOT NULL,
                indicated_shodhana TEXT NOT NULL,
                pathya_ahara_json TEXT NOT NULL,
                apathya_ahara_json TEXT NOT NULL,
                pathya_vihara_json TEXT NOT NULL,
                apathya_vihara_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 37. Patient Lifestyle & Circadian Routine Audits
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS patient_lifestyle_evaluations (
                evaluation_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                evaluation_type TEXT NOT NULL,
                score REAL NOT NULL,
                findings_json TEXT NOT NULL,
                recommendations_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 38. Patient Adharaniya Vega Suppression Clinical Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS patient_vega_suppression_logs (
                log_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                vega_type TEXT NOT NULL,
                frequency TEXT NOT NULL,
                duration_months INTEGER NOT NULL,
                manifestations_json TEXT NOT NULL,
                secondary_udavarta_risk TEXT NOT NULL,
                remediation_plan TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 39. Classical Manasa Roga Classification & Psychiatric Registry
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS manasa_roga_classification_registry (
                disorder_code TEXT PRIMARY KEY,
                sanskrit_name TEXT NOT NULL,
                english_name TEXT NOT NULL,
                icd11_mapping TEXT NOT NULL,
                manasa_dosha TEXT NOT NULL,
                sharirika_dosha TEXT NOT NULL,
                faculty_impairment_json TEXT NOT NULL,
                medhya_rasayana_json TEXT NOT NULL,
                sattvavajaya_modalities_json TEXT NOT NULL,
                emergency_escalation_criteria_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 40. Patient Manasa Roga & Triguna Psychometric Assessments
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS patient_manasa_assessments (
                assessment_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                triguna_sattva REAL NOT NULL,
                triguna_rajas REAL NOT NULL,
                triguna_tamas REAL NOT NULL,
                dhi_score REAL NOT NULL,
                dhriti_score REAL NOT NULL,
                smriti_score REAL NOT NULL,
                prajnaparadha_index REAL NOT NULL,
                primary_manasa_disorder TEXT NOT NULL,
                clinical_summary TEXT NOT NULL,
                crisis_risk_level TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 41. Patient Trividha & Sattvavajaya Clinical Prescriptions
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS patient_sattvavajaya_prescriptions (
                prescription_id TEXT PRIMARY KEY,
                assessment_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                daivavyapashraya_json TEXT NOT NULL,
                yukti_medhya_rasayana_json TEXT NOT NULL,
                sattvavajaya_interventions_json TEXT NOT NULL,
                prescribed_by_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 42. Classical Marma Sharira Catalog & Surgical Vulnerability Specifications
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS marma_sharira_catalog (
                marma_id TEXT PRIMARY KEY,
                sanskrit_name TEXT NOT NULL,
                english_name TEXT NOT NULL,
                marma_type TEXT NOT NULL,
                structural_predominance TEXT NOT NULL,
                anatomical_region TEXT NOT NULL,
                dimension_angula REAL NOT NULL,
                anatomical_landmarks TEXT NOT NULL,
                trauma_manifestations_json TEXT NOT NULL,
                vulnerability_radius_cm REAL NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 43. Agnikarma Thermal Cauterization Procedure Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS agnikarma_procedure_logs (
                session_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                anatomical_site TEXT NOT NULL,
                dahanopakarana TEXT NOT NULL,
                operating_temperature_c REAL NOT NULL,
                contact_time_seconds REAL NOT NULL,
                pattern TEXT NOT NULL,
                samya_dagdha_verified INTEGER NOT NULL,
                post_care_dressing TEXT NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 44. Ksharasutra Anorectal Medicated Seton Treatment Episodes
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ksharasutra_treatment_episodes (
                episode_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                fistula_type TEXT NOT NULL,
                initial_track_length_cm REAL NOT NULL,
                current_track_length_cm REAL NOT NULL,
                sittings_count INTEGER NOT NULL,
                unit_cutting_time_days_per_cm REAL NOT NULL,
                complications_json TEXT NOT NULL,
                healing_status TEXT NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 45. Vrana Surgical Wound & Shashti-Upakrama Clinical Evaluations
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS vrana_wound_evaluations (
                evaluation_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                wound_stage TEXT NOT NULL,
                location TEXT NOT NULL,
                dimensions_cm TEXT NOT NULL,
                exudate_type TEXT NOT NULL,
                prescribed_shashti_upakramas_json TEXT NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 46. Shalakya Tantra 76 Netra Roga Catalog & Ophthalmic Classifications
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS shalakya_netra_roga_catalog (
                roga_code TEXT PRIMARY KEY,
                sanskrit_name TEXT NOT NULL,
                english_name TEXT NOT NULL,
                icd11_mapping TEXT NOT NULL,
                anatomical_mandala TEXT NOT NULL,
                anatomical_patala TEXT NOT NULL,
                doshic_etiology TEXT NOT NULL,
                sadhya_asadhyata TEXT NOT NULL,
                kriya_kalpa_indications_json TEXT NOT NULL,
                contraindicated_procedures_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 47. Netra Kriya Kalpa Tarpana Procedure Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS kriya_kalpa_tarpana_logs (
                session_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                eye_side TEXT NOT NULL,
                ghrita_used TEXT NOT NULL,
                retention_matrakalas INTEGER NOT NULL,
                retention_duration_seconds INTEGER NOT NULL,
                clinical_indication TEXT NOT NULL,
                post_procedure_precautions_json TEXT NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 48. ENT Karna & Nasa Micro-Therapeutic Procedure Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ent_karna_nasa_procedure_logs (
                procedure_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                therapy_type TEXT NOT NULL,
                anatomical_site TEXT NOT NULL,
                medicated_oil_used TEXT NOT NULL,
                dosage_drops_or_ml TEXT NOT NULL,
                observations TEXT NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 49. Garbhini Month-by-Month Antenatal Regimen Catalog (Months 1-9)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS garbhini_month_regimen_catalog (
                month_number INTEGER PRIMARY KEY,
                sanskrit_name TEXT NOT NULL,
                dietary_regimen TEXT NOT NULL,
                medicated_milk_or_ghee TEXT NOT NULL,
                therapeutic_procedures TEXT NOT NULL,
                fetal_development_milestone TEXT NOT NULL,
                contraindicated_drugs_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 50. Garbhini Antenatal Consultation & High-Risk Obstetric Triage Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS garbhini_antenatal_consultation_logs (
                consultation_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                gestational_age_weeks REAL NOT NULL,
                gestational_month INTEGER NOT NULL,
                blood_pressure_systolic INTEGER NOT NULL,
                blood_pressure_diastolic INTEGER NOT NULL,
                fundal_height_cm REAL NOT NULL,
                fetal_heart_rate_bpm INTEGER NOT NULL,
                weight_kg REAL NOT NULL,
                edema_present INTEGER NOT NULL,
                vaginal_bleeding_present INTEGER NOT NULL,
                dauhrida_desires_json TEXT NOT NULL,
                high_risk_flags_json TEXT NOT NULL,
                obstetric_triage_level TEXT NOT NULL,
                prescribed_regimen TEXT NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 51. Classical 20 Yoni Vyapad Gynecological Clinical Assessments
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS yoni_vyapad_clinical_assessments (
                assessment_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                vyapad_code TEXT NOT NULL,
                vyapad_name TEXT NOT NULL,
                doshic_class TEXT NOT NULL,
                icd11_mapping TEXT NOT NULL,
                symptoms_json TEXT NOT NULL,
                local_therapies_json TEXT NOT NULL,
                oral_formulations_json TEXT NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 52. Kaumarbhritya Developmental Milestones & Samskara Catalog
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS kaumarbhritya_milestones_catalog (
                milestone_id TEXT PRIMARY KEY,
                age_months INTEGER NOT NULL,
                classical_samskara TEXT NOT NULL,
                motor_milestone TEXT NOT NULL,
                cognitive_milestone TEXT NOT NULL,
                sharngadhara_dosage_ratti REAL NOT NULL,
                dietary_stage TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 53. Pediatric Clinical Consultations & Dual-Posology Dosing Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS pediatric_consultation_dosing_logs (
                consultation_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                age_months INTEGER NOT NULL,
                weight_kg REAL NOT NULL,
                bala_roga_diagnosis TEXT NOT NULL,
                icd11_mapping TEXT NOT NULL,
                adult_reference_dose_mg REAL NOT NULL,
                calculated_dose_clark_mg REAL NOT NULL,
                calculated_dose_cowling_mg REAL NOT NULL,
                calculated_dose_sharngadhara_mg REAL NOT NULL,
                final_dispensed_dose_mg REAL NOT NULL,
                prescribed_formulation TEXT NOT NULL,
                safety_firewall_passed INTEGER NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 54. Suvarnaprashana Immunomodulation Protocol Administration Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS suvarnaprashana_administration_logs (
                dose_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                age_months INTEGER NOT NULL,
                pushya_nakshatra_date TEXT NOT NULL,
                suvarna_bhasma_mg REAL NOT NULL,
                madhu_ghrita_ratio TEXT NOT NULL,
                medhya_herbs_json TEXT NOT NULL,
                adverse_events TEXT NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 55. Agada Tantra Classical & Environmental Toxicology Registry
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS agada_toxicology_registry (
                visha_code TEXT PRIMARY KEY,
                sanskrit_name TEXT NOT NULL,
                english_name TEXT NOT NULL,
                visha_category TEXT NOT NULL,
                source_origin TEXT NOT NULL,
                cardinal_manifestations_json TEXT NOT NULL,
                upakrama_indications_json TEXT NOT NULL,
                specific_agada_formulations_json TEXT NOT NULL,
                modern_antidote_mapping TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 56. Acute Visha Emergency Admissions & Envenomation Triage Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS visha_emergency_admissions_logs (
                episode_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                suspected_visha_code TEXT NOT NULL,
                envenomation_syndrome TEXT NOT NULL,
                bite_to_admission_minutes INTEGER NOT NULL,
                twenty_minute_wbct_clotted INTEGER NOT NULL,
                neurotoxic_signs_present INTEGER NOT NULL,
                hemotoxic_signs_present INTEGER NOT NULL,
                triage_level TEXT NOT NULL,
                asv_indicated_vials INTEGER NOT NULL,
                upakramas_executed_json TEXT NOT NULL,
                cardioprotective_hridaya_avarana TEXT NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 57. Dushi Visha Chronic Bioaccumulation & Environmental Detox Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dushi_visha_chronic_treatment_logs (
                log_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                suspected_toxin_source TEXT NOT NULL,
                chronicity_months INTEGER NOT NULL,
                manifestations_json TEXT NOT NULL,
                dooshivishari_agada_prescribed INTEGER NOT NULL,
                shodhana_protocol TEXT NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 58. Rasayana Protocols & Classical Formulations Catalog
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS rasayana_protocols_catalog (
                protocol_id TEXT PRIMARY KEY,
                sanskrit_name TEXT NOT NULL,
                rasayana_type TEXT NOT NULL,
                mode TEXT NOT NULL,
                primary_ingredients_json TEXT NOT NULL,
                target_dhatu TEXT NOT NULL,
                classical_reference TEXT NOT NULL,
                indications_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 59. Ojas Reserve, Vyadhikshamatwa & Biological Ageing Evaluations
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ojas_biological_age_evaluations (
                evaluation_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                chronological_age INTEGER NOT NULL,
                biological_age REAL NOT NULL,
                ojas_score REAL NOT NULL,
                ojas_status TEXT NOT NULL,
                visramsa_score REAL NOT NULL,
                vyapat_score REAL NOT NULL,
                kshaya_score REAL NOT NULL,
                decadal_attribute_decay TEXT NOT NULL,
                prescribed_rasayana_id TEXT NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 60. Kuti Praveshika Intensive Rejuvenation Episodes
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS kuti_praveshika_treatment_episodes (
                episode_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                duration_days INTEGER NOT NULL,
                pre_shodhana_completed INTEGER NOT NULL,
                rasayana_formulation TEXT NOT NULL,
                isolation_compliance_score REAL NOT NULL,
                eligibility_cleared INTEGER NOT NULL,
                observations TEXT NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 61. Ashta Shukra Dushti Classification Registry
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS shukra_dushti_classification_registry (
                dushti_code TEXT PRIMARY KEY,
                sanskrit_name TEXT NOT NULL,
                doshic_etiology TEXT NOT NULL,
                classical_characteristics_json TEXT NOT NULL,
                who_semen_correlate TEXT NOT NULL,
                indicated_shodhana_protocol TEXT NOT NULL,
                classical_herbal_remedies_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 62. Semen Analysis Diagnostic Records (WHO 6th Ed. Dual Mapping)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS semen_analysis_diagnostic_records (
                analysis_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                volume_ml REAL NOT NULL,
                ph_level REAL NOT NULL,
                liquefaction_time_min INTEGER NOT NULL,
                viscosity_grade TEXT NOT NULL,
                sperm_concentration_million_ml REAL NOT NULL,
                total_motility_percent REAL NOT NULL,
                progressive_motility_percent REAL NOT NULL,
                normal_morphology_percent REAL NOT NULL,
                vitality_percent REAL NOT NULL,
                pus_cells_per_hpf INTEGER NOT NULL,
                erythrocytes_present INTEGER NOT NULL,
                primary_shukra_dushti TEXT NOT NULL,
                shukra_shuddhi_score REAL NOT NULL,
                fertility_prognosis TEXT NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 63. Vajikarana Treatment Protocols & Reproductive Formulations
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS vajikarana_treatment_protocols (
                protocol_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                klaibya_type TEXT NOT NULL,
                shukra_action_class TEXT NOT NULL,
                pre_shodhana_verified INTEGER NOT NULL,
                prescribed_formulations_json TEXT NOT NULL,
                dietary_lifestyle_pathya_json TEXT NOT NULL,
                psychosexual_counseling_notes TEXT NOT NULL,
                safety_firewall_cleared INTEGER NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 64. Marma Points Detailed Anatomy & Vulnerability Registry (107 Marmas)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS marma_points_detailed_registry (
                marma_code TEXT PRIMARY KEY,
                sanskrit_name TEXT NOT NULL,
                anatomical_region TEXT NOT NULL,
                rachana_structure TEXT NOT NULL,
                parinama_prognosis TEXT NOT NULL,
                angula_dimension REAL NOT NULL,
                cardinal_vulnerability TEXT NOT NULL,
                emergency_management TEXT NOT NULL,
                therapeutic_indications_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 65. Marma Trauma Emergency & Triage Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS marma_trauma_emergency_logs (
                log_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                injured_marma_code TEXT NOT NULL,
                trauma_mechanism TEXT NOT NULL,
                depth_penetration_mm REAL NOT NULL,
                foreign_body_present INTEGER NOT NULL,
                tri_marma_involved INTEGER NOT NULL,
                triage_tier TEXT NOT NULL,
                emergency_resuscitation_protocol TEXT NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 66. Marma Chikitsa Therapeutic Stimulation Sessions
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS marma_chikitsa_therapeutic_sessions (
                session_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                targeted_marma_code TEXT NOT NULL,
                stimulation_modality TEXT NOT NULL,
                pressure_intensity_kg REAL NOT NULL,
                cycles_count INTEGER NOT NULL,
                clinical_objective TEXT NOT NULL,
                immediate_response TEXT NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 67. Shalya Tantra Yantra-Shastra Microsurgical Instruments Registry
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS shalya_yantra_shastra_registry (
                instrument_code TEXT PRIMARY KEY,
                instrument_type TEXT NOT NULL,
                sanskrit_name TEXT NOT NULL,
                category_group TEXT NOT NULL,
                angula_dimension REAL NOT NULL,
                target_tissues_json TEXT NOT NULL,
                primary_action TEXT NOT NULL,
                sterilization_protocol TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 68. Ashtavidha Shastra Karma Operative Procedure Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ashtavidha_operative_procedure_logs (
                procedure_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                operative_karma TEXT NOT NULL,
                surgical_instruments_used_json TEXT NOT NULL,
                anesthesia_or_sangyaharana TEXT NOT NULL,
                parasurgical_modality TEXT NOT NULL,
                safety_firewall_cleared INTEGER NOT NULL,
                operative_notes TEXT NOT NULL,
                surgeon_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 69. Yogya Surgical Simulation Competency Assessments
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS surgical_simulation_yogya_assessments (
                assessment_id TEXT PRIMARY KEY,
                practitioner_arn TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                operative_karma_tested TEXT NOT NULL,
                simulation_model_used TEXT NOT NULL,
                precision_score REAL NOT NULL,
                tissue_handling_score REAL NOT NULL,
                overall_competency_certified INTEGER NOT NULL,
                examiner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 70. Jalauka Species Registry
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS jalauka_species_registry (
                species_id TEXT PRIMARY KEY,
                sanskrit_name TEXT NOT NULL,
                species_type TEXT NOT NULL,
                morphological_markers_json TEXT NOT NULL,
                salivary_enzymes_profile_json TEXT NOT NULL,
                habitat_water_type TEXT NOT NULL,
                clinical_suitability TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 71. Raktamokshana Operative Procedure Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS raktamokshana_procedure_logs (
                procedure_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                modality TEXT NOT NULL,
                target_anatomical_site TEXT NOT NULL,
                vein_or_point_id TEXT,
                jalauka_count INTEGER,
                evacuated_volume_ml REAL NOT NULL,
                pre_procedure_hb REAL NOT NULL,
                post_procedure_hb REAL NOT NULL,
                blood_dosha_vitiation TEXT NOT NULL,
                hemostasis_method TEXT NOT NULL,
                safety_firewall_cleared INTEGER NOT NULL,
                complications_observed_json TEXT NOT NULL,
                practitioner_arn TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 72. Siravedha Vein Selection Matrix (Avadhya and Vidhya Siras)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS siravedha_vein_selection_matrix (
                vein_code TEXT PRIMARY KEY,
                sanskrit_name TEXT NOT NULL,
                anatomical_location TEXT NOT NULL,
                body_quadrant TEXT NOT NULL,
                is_avadhya INTEGER NOT NULL,
                avadhya_complication_risk TEXT NOT NULL,
                indicated_diseases_json TEXT NOT NULL,
                puncture_depth_angula REAL NOT NULL,
                instrument_shastra TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 73. Unified Clinical Diagnosis Episodes (A-CDSS Orchestrator)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS clinical_diagnosis_episodes (
                episode_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                intake_data_json TEXT NOT NULL,
                primary_diagnosis_sanskrit TEXT NOT NULL,
                primary_diagnosis_namaste_code TEXT NOT NULL,
                primary_diagnosis_icd11_code TEXT NOT NULL,
                vikriti_vector_json TEXT NOT NULL,
                vikriti_divergence_metric REAL NOT NULL,
                agni_status TEXT NOT NULL,
                ama_status TEXT NOT NULL,
                shat_kriya_kala_stage TEXT NOT NULL,
                rogi_bala TEXT NOT NULL,
                doshic_dushti_json TEXT NOT NULL,
                treatment_protocol_json TEXT NOT NULL,
                safety_firewalls_cleared INTEGER NOT NULL,
                safety_alerts_json TEXT NOT NULL,
                governance_status TEXT NOT NULL,
                attending_physician_arn TEXT,
                countersigned_at INTEGER,
                created_at INTEGER NOT NULL
            );
            """)

            # 74. Paschat Karma & Post-Panchakarma Rehabilitation Episodes
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS paschat_karma_episodes (
                episode_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                plan_id TEXT NOT NULL,
                procedure_type TEXT NOT NULL,
                shuddhi_grade TEXT NOT NULL,
                total_annakalas INTEGER NOT NULL,
                total_days INTEGER NOT NULL,
                current_annakala INTEGER NOT NULL DEFAULT 1,
                agni_restoration_status TEXT NOT NULL,
                parihara_restrictions_json TEXT NOT NULL,
                rasayana_readiness INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                attending_physician_arn TEXT NOT NULL,
                started_at INTEGER NOT NULL,
                completed_at INTEGER,
                created_at INTEGER NOT NULL
            );
            """)

            # 75. Samsarjana Krama Longitudinal Bedside Meal Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS samsarjana_krama_logs (
                log_id TEXT PRIMARY KEY,
                episode_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                day_number INTEGER NOT NULL,
                annakala_number INTEGER NOT NULL,
                meal_time_type TEXT NOT NULL,
                prescribed_diet_form TEXT NOT NULL,
                preparation_details TEXT NOT NULL,
                caloric_estimate_kcal REAL NOT NULL,
                digestibility_index REAL NOT NULL,
                patient_appetite_observed TEXT NOT NULL,
                digestion_tolerance_noted TEXT NOT NULL,
                compliance_status TEXT NOT NULL,
                clinical_notes TEXT,
                nurse_or_practitioner_id TEXT NOT NULL,
                logged_at INTEGER NOT NULL
            );
            """)

            # 76. Western Emergency Break-Glass Events (NABH COP.6)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS emergency_break_glass_events (
                event_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                trigger_reason TEXT NOT NULL,
                trigger_vitals_json TEXT NOT NULL,
                initiating_user_id TEXT NOT NULL,
                initiating_role TEXT NOT NULL,
                physician_arn TEXT,
                state_lockdown_enforced INTEGER NOT NULL DEFAULT 1,
                sbar_handover_report_json TEXT NOT NULL,
                emergency_icu_destination TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 77. Acute Critical Care Transfer Records (NABH COP.6)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS critical_care_transfers (
                transfer_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                ambulance_service_called INTEGER NOT NULL DEFAULT 1,
                paramedic_call_timestamp INTEGER NOT NULL,
                allopathic_physician_notified TEXT NOT NULL,
                medical_superintendent_alerted INTEGER NOT NULL DEFAULT 1,
                handover_signed_by_arn TEXT NOT NULL,
                receiving_hospital_name TEXT NOT NULL,
                receiving_doctor_name TEXT NOT NULL,
                transfer_completed_at INTEGER,
                clinical_notes TEXT,
                created_at INTEGER NOT NULL
            );
            """)

            # 78. Real-Time Herb-Drug Interaction (HDI) Rules Catalog
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS hdi_interaction_rules (
                rule_id TEXT PRIMARY KEY,
                ayurvedic_herb_or_formulation TEXT NOT NULL,
                allopathic_drug_or_class TEXT NOT NULL,
                mechanism_of_interaction TEXT NOT NULL,
                clinical_severity TEXT NOT NULL,
                potential_adverse_effects TEXT NOT NULL,
                evidence_grade TEXT NOT NULL,
                recommended_clinical_action TEXT NOT NULL,
                reference_citations TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 79. Real-Time Herb-Drug Clinical Intercept Audit Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS hdi_audit_intercepts (
                intercept_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                prescribed_herb TEXT NOT NULL,
                concurrent_allopathic_drug TEXT NOT NULL,
                rule_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                override_reason TEXT,
                physician_arn TEXT NOT NULL,
                intercepted_at INTEGER NOT NULL
            );
            """)

            # 80. Multi-Lingual Regional Translation Lexicon Cache (Phase 37)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS multilingual_lexicon_cache (
                entry_id TEXT PRIMARY KEY,
                language_code TEXT NOT NULL,
                vernacular_phrase TEXT NOT NULL,
                phonetic_transcription TEXT NOT NULL,
                ayurvedic_concept_sanskrit TEXT NOT NULL,
                namaste_code TEXT,
                confidence_score REAL NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 81. Audio Intake & Vernacular Speech Transcripts (Phase 37)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_intake_transcripts (
                transcript_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                audio_session_id TEXT NOT NULL,
                source_language TEXT NOT NULL,
                raw_transcript_text TEXT NOT NULL,
                translated_clinical_text TEXT NOT NULL,
                extracted_entities_json TEXT NOT NULL,
                transcribed_at INTEGER NOT NULL
            );
            """)

            # 82. Tele-AYUSH Video & Audio Consultation Sessions (Phase 38)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tele_ayush_consultations (
                session_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                physician_arn TEXT NOT NULL,
                scheduled_timestamp INTEGER NOT NULL,
                started_timestamp INTEGER,
                ended_timestamp INTEGER,
                session_status TEXT NOT NULL,
                call_type TEXT NOT NULL,
                clinical_notes TEXT,
                created_at INTEGER NOT NULL
            );
            """)

            # 83. Tamper-Evident QR-Verified Digital e-Prescriptions (Phase 38)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS digital_eprescriptions (
                prescription_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                physician_arn TEXT NOT NULL,
                formulations_json TEXT NOT NULL,
                pathya_diet_instructions TEXT NOT NULL,
                verification_hash TEXT NOT NULL,
                qr_code_payload TEXT NOT NULL,
                dispensation_status TEXT NOT NULL,
                issued_at INTEGER NOT NULL
            );
            """)

            # 84. IoT Pulse Sensor Hardware Registrations (Phase 39)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS iot_sensor_registrations (
                device_id TEXT PRIMARY KEY,
                hospital_id TEXT NOT NULL,
                device_model TEXT NOT NULL,
                sampling_rate_hz INTEGER NOT NULL DEFAULT 500,
                calibration_factor REAL NOT NULL DEFAULT 1.0,
                assigned_ward_or_clinic TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                registered_at INTEGER NOT NULL
            );
            """)

            # 85. Raw Nadi Arterial Waveform Packets (Phase 39)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_nadi_waveform_packets (
                packet_id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                packet_index INTEGER NOT NULL,
                pressure_samples_json TEXT NOT NULL,
                pulse_wave_velocity_mps REAL NOT NULL,
                radial_reflection_index REAL NOT NULL,
                doshic_dominant_wave TEXT NOT NULL,
                captured_at INTEGER NOT NULL
            );
            """)

            # 86. Computer Vision Optical Diagnostic Inference Records (Phase 40)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS vision_inference_records (
                inference_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                anatomical_target TEXT NOT NULL,
                raw_image_hash TEXT NOT NULL,
                calibrated_cielab_l REAL NOT NULL,
                calibrated_cielab_a REAL NOT NULL,
                calibrated_cielab_b REAL NOT NULL,
                coating_thickness_pct REAL NOT NULL,
                icterus_index REAL,
                clinical_interpretation TEXT NOT NULL,
                analyzed_at INTEGER NOT NULL
            );
            """)

            # 87. Optical Color-Card Calibration Reference Targets (Phase 40)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS optical_calibration_targets (
                target_id TEXT PRIMARY KEY,
                color_card_standard TEXT NOT NULL,
                reference_l REAL NOT NULL,
                reference_a REAL NOT NULL,
                reference_b REAL NOT NULL,
                tolerance_delta_e REAL NOT NULL DEFAULT 2.0,
                created_at INTEGER NOT NULL
            );
            """)

            # 88. Patient Portal Accounts (Phase 41)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS patient_portal_accounts (
                account_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                abha_address TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                last_login_at INTEGER,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE RESTRICT
            );
            """)

            # 89. Patient Daily Lifestyle & Pathya Logs (Phase 41)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS patient_daily_logs (
                log_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                log_date TEXT NOT NULL,
                diet_adherence_score INTEGER NOT NULL DEFAULT 100,
                pathya_followed_notes TEXT,
                ahara_craving TEXT,
                bowel_movement_type TEXT NOT NULL,
                sleep_duration_hours REAL NOT NULL,
                stress_level INTEGER NOT NULL DEFAULT 1,
                logged_at INTEGER NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE RESTRICT
            );
            """)

            # 90. AYUSH GRID ABDM Bridge Logs (Phase 42)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ayush_grid_bridge_logs (
                bridge_id TEXT PRIMARY KEY,
                hospital_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                abdm_bundle_type TEXT NOT NULL,
                fhir_bundle_json TEXT NOT NULL,
                status TEXT NOT NULL,
                dispatch_timestamp INTEGER NOT NULL,
                ack_reference TEXT,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE RESTRICT
            );
            """)

            # 91. Zero-Knowledge Cryptographic Proof Records (Phase 42)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS zero_knowledge_proof_records (
                proof_id TEXT PRIMARY KEY,
                hospital_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                clinical_attribute TEXT NOT NULL,
                commitment_hash TEXT NOT NULL,
                zk_proof_payload TEXT NOT NULL,
                verifier_arn TEXT NOT NULL,
                is_verified INTEGER NOT NULL DEFAULT 1,
                generated_at INTEGER NOT NULL,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE RESTRICT
            );
            """)

            # 92. Edge Node Registries (Phase 43)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS edge_node_registries (
                node_id TEXT PRIMARY KEY,
                hospital_id TEXT NOT NULL,
                facility_name TEXT NOT NULL,
                facility_type TEXT NOT NULL,
                sync_passkey_hash TEXT NOT NULL,
                last_sync_timestamp INTEGER,
                is_online INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE RESTRICT
            );
            """)

            # 93. CRDT Replication Sync Queue (Phase 43)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS replication_sync_queue (
                queue_id TEXT PRIMARY KEY,
                node_id TEXT NOT NULL,
                entity_table TEXT NOT NULL,
                record_id TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                vector_clock_counter INTEGER NOT NULL DEFAULT 1,
                sync_status TEXT NOT NULL DEFAULT 'PENDING',
                queued_at INTEGER NOT NULL,
                synced_at INTEGER,
                FOREIGN KEY (node_id) REFERENCES edge_node_registries(node_id) ON DELETE CASCADE
            );
            """)

            # 94. Pharmacovigilance ADR Reports (Phase 44)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS adr_pharmacovigilance_reports (
                report_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                suspected_formulation TEXT NOT NULL,
                batch_number TEXT,
                adverse_reaction_description TEXT NOT NULL,
                onset_latency_hours REAL,
                naranjo_asu_score INTEGER NOT NULL,
                causality_category TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                reporting_rmp_arn TEXT NOT NULL,
                npvcc_submission_status TEXT NOT NULL DEFAULT 'DRAFT',
                reported_at INTEGER NOT NULL,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE RESTRICT
            );
            """)

            # 95. Suspected Formulation Lots (Phase 44)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS suspected_formulation_lots (
                lot_id TEXT PRIMARY KEY,
                report_id TEXT NOT NULL,
                formulation_name TEXT NOT NULL,
                manufacturer_name TEXT NOT NULL,
                mfg_license_number TEXT NOT NULL,
                expiry_date TEXT,
                chemical_heavy_metal_audit_notes TEXT,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (report_id) REFERENCES adr_pharmacovigilance_reports(report_id) ON DELETE CASCADE
            );
            """)

            # 96. Evidence-Based Clinical Trial Protocols (Phase 45)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS clinical_trial_protocols (
                protocol_id TEXT PRIMARY KEY,
                ctri_registration_number TEXT UNIQUE,
                trial_title TEXT NOT NULL,
                ayurvedic_intervention_arm TEXT NOT NULL,
                control_arm TEXT NOT NULL,
                sample_size_target INTEGER NOT NULL,
                primary_outcome_measure TEXT NOT NULL,
                principal_investigator_arn TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)

            # 97. Clinical Trial Cohort Subjects (Phase 45)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS trial_cohort_subjects (
                subject_id TEXT PRIMARY KEY,
                protocol_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                assigned_arm TEXT NOT NULL,
                baseline_prakriti TEXT NOT NULL,
                baseline_score REAL NOT NULL,
                current_score REAL NOT NULL,
                compliance_rate_pct REAL NOT NULL DEFAULT 100.0,
                enrolled_at INTEGER NOT NULL,
                FOREIGN KEY (protocol_id) REFERENCES clinical_trial_protocols(protocol_id) ON DELETE CASCADE
            );
            """)

            # 98. IPD Inpatient Bed Allocations (Phase 46)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ipd_bed_allocations (
                allocation_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                ward_name TEXT NOT NULL,
                bed_number TEXT NOT NULL,
                admission_timestamp INTEGER NOT NULL,
                discharge_timestamp INTEGER,
                status TEXT NOT NULL,
                attending_rmp_arn TEXT NOT NULL,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE RESTRICT
            );
            """)

            # 99. Panchakarma Daily Nursing Charts (Phase 46)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS panchakarma_daily_nursing_charts (
                chart_id TEXT PRIMARY KEY,
                allocation_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                vital_bp_systolic INTEGER NOT NULL,
                vital_bp_diastolic INTEGER NOT NULL,
                vital_pulse_bpm INTEGER NOT NULL,
                panchakarma_therapy_administered TEXT NOT NULL,
                vega_count INTEGER NOT NULL DEFAULT 0,
                jeerna_ahara_lakshana TEXT,
                nursing_notes TEXT,
                nurse_name TEXT NOT NULL,
                charted_at INTEGER NOT NULL,
                FOREIGN KEY (allocation_id) REFERENCES ipd_bed_allocations(allocation_id) ON DELETE CASCADE
            );
            """)

            # 100. OPD Queue Token Management (Phase 47)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS opd_token_queues (
                token_id TEXT PRIMARY KEY,
                hospital_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                department TEXT NOT NULL,
                token_number INTEGER NOT NULL,
                priority_tier TEXT NOT NULL,
                status TEXT NOT NULL,
                estimated_wait_minutes INTEGER NOT NULL,
                issued_at INTEGER NOT NULL,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE RESTRICT
            );
            """)

            # 101. Consultation Time Audits (Phase 47)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS consultation_time_audits (
                audit_id TEXT PRIMARY KEY,
                token_id TEXT NOT NULL,
                physician_arn TEXT NOT NULL,
                consultation_start_timestamp INTEGER NOT NULL,
                consultation_end_timestamp INTEGER,
                duration_seconds INTEGER,
                efficiency_rating REAL,
                FOREIGN KEY (token_id) REFERENCES opd_token_queues(token_id) ON DELETE CASCADE
            );
            """)

            # 102. Pharmacy Barcode & Inventory Lots (Phase 48)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS pharmacy_inventory_lots (
                lot_id TEXT PRIMARY KEY,
                hospital_id TEXT NOT NULL,
                formulation_name TEXT NOT NULL,
                batch_number TEXT NOT NULL,
                gs1_datamatrix_barcode TEXT UNIQUE,
                manufacturer_name TEXT NOT NULL,
                stock_quantity_units INTEGER NOT NULL,
                unit_measure TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                is_quarantined INTEGER NOT NULL DEFAULT 0,
                contains_schedule_e1 INTEGER NOT NULL DEFAULT 0,
                certified_shodhana_batch_code TEXT,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE RESTRICT
            );
            """)

            # 103. Formulation Dispensation Records (Phase 48)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dispensation_records (
                dispensation_id TEXT PRIMARY KEY,
                prescription_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                lot_id TEXT NOT NULL,
                quantity_dispensed INTEGER NOT NULL,
                pharmacist_user_id TEXT NOT NULL,
                dispensed_at INTEGER NOT NULL,
                safety_invariants_verified INTEGER NOT NULL DEFAULT 1,
                two_physician_verified INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (lot_id) REFERENCES pharmacy_inventory_lots(lot_id) ON DELETE RESTRICT
            );
            """)

            # Auto-migrate pharmacy tables if upgraded in existing databases
            try:
                cursor.execute("ALTER TABLE pharmacy_inventory_lots ADD COLUMN contains_schedule_e1 INTEGER NOT NULL DEFAULT 0;")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE pharmacy_inventory_lots ADD COLUMN certified_shodhana_batch_code TEXT;")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE dispensation_records ADD COLUMN safety_invariants_verified INTEGER NOT NULL DEFAULT 1;")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE dispensation_records ADD COLUMN two_physician_verified INTEGER NOT NULL DEFAULT 0;")
            except sqlite3.OperationalError:
                pass

            # 104. Disaster Recovery Snapshot Catalog (Phase 49)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS backup_snapshots_catalog (
                snapshot_id TEXT PRIMARY KEY,
                hospital_id TEXT NOT NULL,
                snapshot_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                sha256_checksum TEXT NOT NULL,
                is_verified INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE RESTRICT
            );
            """)

            # 105. Point-in-Time Recovery Drill Records (Phase 49)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS recovery_drill_records (
                drill_id TEXT PRIMARY KEY,
                snapshot_id TEXT NOT NULL,
                drill_type TEXT NOT NULL,
                recovery_time_seconds REAL NOT NULL,
                data_integrity_status TEXT NOT NULL,
                simulated_by_user_id TEXT NOT NULL,
                executed_at INTEGER NOT NULL,
                FOREIGN KEY (snapshot_id) REFERENCES backup_snapshots_catalog(snapshot_id) ON DELETE CASCADE
            );
            """)

            # 106. Zero-Trust Security Threat Telemetry (Phase 50)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_threat_telemetry (
                event_id TEXT PRIMARY KEY,
                hospital_id TEXT NOT NULL,
                source_ip TEXT NOT NULL,
                threat_category TEXT NOT NULL,
                request_uri TEXT NOT NULL,
                action_intercepted TEXT NOT NULL,
                severity_level TEXT NOT NULL,
                detected_at INTEGER NOT NULL,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE RESTRICT
            );
            """)

            # 107. Penetration Testing & DAST Audit Findings (Phase 50)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS penetration_audit_findings (
                finding_id TEXT PRIMARY KEY,
                audit_suite_name TEXT NOT NULL,
                target_endpoint TEXT NOT NULL,
                cve_or_cwe_identifier TEXT,
                mitigation_status TEXT NOT NULL,
                audited_by TEXT NOT NULL,
                audited_at INTEGER NOT NULL
            );
            """)

            # 108. Final Production Release Certifications (Phase 51)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS production_release_certifications (
                cert_id TEXT PRIMARY KEY,
                release_version TEXT NOT NULL,
                all_51_phases_verified INTEGER NOT NULL DEFAULT 1,
                zero_regression_passed INTEGER NOT NULL DEFAULT 1,
                total_tests_executed INTEGER NOT NULL,
                sha256_manifest_seal TEXT NOT NULL,
                certified_by_superintendent_arn TEXT NOT NULL,
                certified_at INTEGER NOT NULL
            );
            """)

            # 109. Hospital Site Production Configurations (Phase 51)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS hospital_site_configurations (
                config_id TEXT PRIMARY KEY,
                hospital_id TEXT NOT NULL UNIQUE,
                deployment_tier TEXT NOT NULL,
                hostinger_vps_specs_json TEXT NOT NULL,
                active_modules_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PRODUCTION_ACTIVE',
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE RESTRICT
            );
            """)


            # Indexes for fast lookup
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_hospital ON users(hospital_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_patients_hospital ON patients(hospital_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_hospital ON audit_ledger(hospital_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_practitioners_hospital ON practitioners(hospital_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_prakriti_patient ON prakriti_assessments(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vikriti_patient ON vikriti_assessments(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ashtavidha_patient ON ashtavidha_examinations(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dashavidha_patient ON dashavidha_assessments(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nadi_patient ON nadi_telemetry_sessions(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_taila_patient ON taila_bindu_sessions(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jihwa_patient ON jihwa_examinations(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ama_agni_patient ON ama_agni_assessments(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dhatu_sarata_patient ON dhatu_sarata_assessments(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_srotas_patient ON srotas_assessments(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kriya_kala_patient ON kriya_kala_assessments(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_roga_rogi_patient ON roga_rogi_bala_assessments(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nidana_panchaka_patient ON nidana_panchaka_assessments(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_diagnosis_patient ON patient_diagnosis_codings(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_diagnosis_hospital ON patient_diagnosis_codings(hospital_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_registry_namaste ON disease_classification_registry(namaste_code);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_registry_icd11 ON disease_classification_registry(icd11_tm2_code);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_herb_botanical ON dravyaguna_herbal_registry(botanical_name);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_herb_sanskrit ON dravyaguna_herbal_registry(sanskrit_name);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_herb_veerya ON dravyaguna_herbal_registry(veerya);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_formulation_kalpana ON formulations_registry(kalpana_form);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_formulation_name ON formulations_registry(sanskrit_name);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_anupana_doshic ON anupana_registry(doshic_affinity);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rasa_category ON rasa_minerals_registry(category);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rasa_poison ON rasa_minerals_registry(is_schedule_e1_poison);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_shodhana_batch ON shodhana_records(batch_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_shodhana_mineral ON shodhana_records(mineral_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bhasma_batch ON bhasma_batches(batch_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bhasma_mineral ON bhasma_batches(mineral_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bhasma_release ON bhasma_batches(is_released);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pk_plan_patient ON panchakarma_treatment_plans(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pk_plan_hospital ON panchakarma_treatment_plans(hospital_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pk_vega_plan ON panchakarma_bedside_vegas(plan_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pk_vega_patient ON panchakarma_bedside_vegas(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pk_shuddhi_plan ON panchakarma_shuddhi_assessments(plan_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pk_shuddhi_patient ON panchakarma_shuddhi_assessments(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_upakarma_modality ON upakarma_therapies_catalog(modality_code);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_upakarma_session_patient ON upakarma_session_logs(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_upakarma_session_hospital ON upakarma_session_logs(hospital_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_upakarma_session_therapy ON upakarma_session_logs(therapy_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_diet_varga ON diet_ingredients_catalog(ahara_varga);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_diet_rasa ON diet_ingredients_catalog(rasa);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pathya_disease ON disease_pathya_apathya_registry(disease_code);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_diet_plan_patient ON patient_diet_prescriptions(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_diet_plan_hospital ON patient_diet_prescriptions(hospital_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dinacharya_step ON swasthavritta_dinacharya_catalog(step_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ritucharya_code ON swasthavritta_ritucharya_catalog(ritu_code);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lifestyle_patient ON patient_lifestyle_evaluations(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vega_patient ON patient_vega_suppression_logs(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_manasa_disorder ON manasa_roga_classification_registry(disorder_code);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_manasa_patient ON patient_manasa_assessments(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_manasa_crisis ON patient_manasa_assessments(crisis_risk_level);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sattvavajaya_patient ON patient_sattvavajaya_prescriptions(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_marma_type ON marma_sharira_catalog(marma_type);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_marma_region ON marma_sharira_catalog(anatomical_region);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_agnikarma_patient ON agnikarma_procedure_logs(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ksharasutra_patient ON ksharasutra_treatment_episodes(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vrana_patient ON vrana_wound_evaluations(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_netra_roga_mandala ON shalakya_netra_roga_catalog(anatomical_mandala);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_netra_roga_patala ON shalakya_netra_roga_catalog(anatomical_patala);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tarpana_patient ON kriya_kalpa_tarpana_logs(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ent_procedure_patient ON ent_karna_nasa_procedure_logs(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_garbhini_patient ON garbhini_antenatal_consultation_logs(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_garbhini_hospital ON garbhini_antenatal_consultation_logs(hospital_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_garbhini_risk ON garbhini_antenatal_consultation_logs(obstetric_triage_level);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_yoni_vyapad_patient ON yoni_vyapad_clinical_assessments(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_yoni_vyapad_code ON yoni_vyapad_clinical_assessments(vyapad_code);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pediatric_patient ON pediatric_consultation_dosing_logs(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pediatric_hospital ON pediatric_consultation_dosing_logs(hospital_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_suvarna_patient ON suvarnaprashana_administration_logs(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_suvarna_pushya ON suvarnaprashana_administration_logs(pushya_nakshatra_date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_visha_category ON agada_toxicology_registry(visha_category);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_visha_emergency_patient ON visha_emergency_admissions_logs(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_visha_emergency_triage ON visha_emergency_admissions_logs(triage_level);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dushi_patient ON dushi_visha_chronic_treatment_logs(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rasayana_type ON rasayana_protocols_catalog(rasayana_type);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ojas_eval_patient ON ojas_biological_age_evaluations(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ojas_eval_status ON ojas_biological_age_evaluations(ojas_status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kuti_patient ON kuti_praveshika_treatment_episodes(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_shukra_dushti_code ON shukra_dushti_classification_registry(dushti_code);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_semen_analysis_patient ON semen_analysis_diagnostic_records(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_semen_analysis_dushti ON semen_analysis_diagnostic_records(primary_shukra_dushti);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vajikarana_patient ON vajikarana_treatment_protocols(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vajikarana_klaibya ON vajikarana_treatment_protocols(klaibya_type);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_marma_detailed_code ON marma_points_detailed_registry(marma_code);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_marma_detailed_region ON marma_points_detailed_registry(anatomical_region);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_marma_detailed_parinama ON marma_points_detailed_registry(parinama_prognosis);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_marma_trauma_patient ON marma_trauma_emergency_logs(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_marma_trauma_triage ON marma_trauma_emergency_logs(triage_tier);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_marma_chikitsa_patient ON marma_chikitsa_therapeutic_sessions(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_instrument_code ON shalya_yantra_shastra_registry(instrument_code);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_instrument_type ON shalya_yantra_shastra_registry(instrument_type);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_instrument_cat ON shalya_yantra_shastra_registry(category_group);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_operative_patient ON ashtavidha_operative_procedure_logs(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_operative_karma ON ashtavidha_operative_procedure_logs(operative_karma);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_yogya_practitioner ON surgical_simulation_yogya_assessments(practitioner_arn);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jalauka_type ON jalauka_species_registry(species_type);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_raktamokshana_patient ON raktamokshana_procedure_logs(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_raktamokshana_modality ON raktamokshana_procedure_logs(modality);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_siravedha_quadrant ON siravedha_vein_selection_matrix(body_quadrant);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_siravedha_avadhya ON siravedha_vein_selection_matrix(is_avadhya);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_diag_episode_patient ON clinical_diagnosis_episodes(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_diag_episode_hospital ON clinical_diagnosis_episodes(hospital_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_diag_episode_status ON clinical_diagnosis_episodes(governance_status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_paschat_patient ON paschat_karma_episodes(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_paschat_plan ON paschat_karma_episodes(plan_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_paschat_status ON paschat_karma_episodes(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_samsarjana_episode ON samsarjana_krama_logs(episode_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_samsarjana_patient ON samsarjana_krama_logs(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_breakglass_patient ON emergency_break_glass_events(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_breakglass_status ON emergency_break_glass_events(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transfer_patient ON critical_care_transfers(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transfer_event ON critical_care_transfers(event_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hdi_herb ON hdi_interaction_rules(ayurvedic_herb_or_formulation);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hdi_drug ON hdi_interaction_rules(allopathic_drug_or_class);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hdi_severity ON hdi_interaction_rules(clinical_severity);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hdi_intercept_patient ON hdi_audit_intercepts(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lexicon_lang ON multilingual_lexicon_cache(language_code);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audio_transcript_patient ON audio_intake_transcripts(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tele_session_patient ON tele_ayush_consultations(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tele_session_physician ON tele_ayush_consultations(physician_arn);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_eprescription_session ON digital_eprescriptions(session_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_eprescription_hash ON digital_eprescriptions(verification_hash);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_iot_sensor_hosp ON iot_sensor_registrations(hospital_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nadi_packet_patient ON raw_nadi_waveform_packets(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vision_patient ON vision_inference_records(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vision_target ON vision_inference_records(anatomical_target);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_portal_patient ON patient_portal_accounts(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_portal_phone ON patient_portal_accounts(phone_number);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_log_patient ON patient_daily_logs(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ayush_grid_patient ON ayush_grid_bridge_logs(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_zkp_patient ON zero_knowledge_proof_records(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_zkp_hash ON zero_knowledge_proof_records(commitment_hash);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_edge_node_hosp ON edge_node_registries(hospital_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_queue_node ON replication_sync_queue(node_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_queue_status ON replication_sync_queue(sync_status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_adr_patient ON adr_pharmacovigilance_reports(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_adr_herb ON adr_pharmacovigilance_reports(suspected_formulation);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trial_protocol_ctri ON clinical_trial_protocols(ctri_registration_number);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trial_subject_protocol ON trial_cohort_subjects(protocol_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trial_subject_patient ON trial_cohort_subjects(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ipd_bed_patient ON ipd_bed_allocations(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ipd_bed_status ON ipd_bed_allocations(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nursing_chart_alloc ON panchakarma_daily_nursing_charts(allocation_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_opd_token_hosp ON opd_token_queues(hospital_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_opd_token_status ON opd_token_queues(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_time_audit_token ON consultation_time_audits(token_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pharmacy_lot_barcode ON pharmacy_inventory_lots(gs1_datamatrix_barcode);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pharmacy_lot_name ON pharmacy_inventory_lots(formulation_name);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dispensation_patient ON dispensation_records(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_backup_snapshot_hosp ON backup_snapshots_catalog(hospital_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_recovery_drill_snapshot ON recovery_drill_records(snapshot_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_security_threat_hosp ON security_threat_telemetry(hospital_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_security_threat_cat ON security_threat_telemetry(threat_category);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pen_audit_suite ON penetration_audit_findings(audit_suite_name);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_prod_cert_ver ON production_release_certifications(release_version);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_site_config_hosp ON hospital_site_configurations(hospital_id);")

            # Seed default hospital if not present
            cursor.execute("SELECT COUNT(*) as count FROM hospitals WHERE hospital_id = ?;", (settings.default_hospital_id,))
            if cursor.fetchone()["count"] == 0:
                now = int(time.time())
                cursor.execute(
                    """
                    INSERT INTO hospitals (hospital_id, name, nabh_accreditation_status, state_council_code, created_at)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (settings.default_hospital_id, "All India Institute of Ayurveda (AIIA) Apex Centre", "NABH_AYUSH_2ND_ED_CERTIFIED", "DL-NCISM-001", now)
                )

                # Seed default Superintendent & Clinical RMP
                admin_pw = hash_password("Superintendent@AIIA2026")
                cursor.execute(
                    """
                    INSERT INTO users (user_id, hospital_id, username, password_hash, full_name, arn, role, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?);
                    """,
                    ("user-superintendent-001", settings.default_hospital_id, "superintendent", admin_pw, "Prof. Dr. V. Sharma, MD(Ayu)", "ARN-NCISM-1998-0421", ClinicalRole.SUPERINTENDENT.value, now)
                )

                rmp_pw = hash_password("Physician@AIIA2026")
                cursor.execute(
                    """
                    INSERT INTO users (user_id, hospital_id, username, password_hash, full_name, arn, role, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?);
                    """,
                    ("user-physician-001", settings.default_hospital_id, "physician_rmp", rmp_pw, "Dr. Ananya Sen, BAMS, MD(Kayachikitsa)", "ARN-NCISM-2015-8832", ClinicalRole.PHYSICIAN_RMP.value, now)
                )

                append_audit_log(
                    conn,
                    settings.default_hospital_id,
                    "SYSTEM_INIT",
                    "BOOTSTRAP_DATABASE",
                    "SYSTEM",
                    "CORE_DB",
                    {"event": "Initialized SQLite WAL database schema and seeded institutional principals."}
                )

            cursor.execute("COMMIT;")
        except Exception:
            cursor.execute("ROLLBACK;")
            raise
