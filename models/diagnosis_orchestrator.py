"""Pydantic schemas for the Unified Clinical Diagnostic & Decision Support Orchestrator (A-CDSS)."""
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class AgniStatus(str, Enum):
    """Four classical functional states of Jatharagni."""
    SAMAGNI = "SAMAGNI"          # Equilibrium / optimal enzymatic metabolism
    VISHAMAGNI = "VISHAMAGNI"    # Irregular / Vata-predominant metabolism
    TIKSHNAGNI = "TIKSHNAGNI"    # Hyperactive / Pitta-predominant metabolism
    MANDAGNI = "MANDAGNI"        # Hypoactive / Kapha-Ama predominant metabolism


class AmaStatus(str, Enum):
    """Presence or absence of endotoxic biometabolic byproduct (Ama)."""
    SAMA = "SAMA"                # Toxic unprocessed metabolites present (Deepana-Pachana mandatory)
    NIRAMA = "NIRAMA"            # Clear of endotoxins (Shodhana / Rasayana eligible)


class ShatKriyaKalaStage(str, Enum):
    """Six stages of pathogenesis according to Sushruta Sutrasthana Ch. 21."""
    SANCHAYA = "SANCHAYA"                    # Accumulation in primary seat
    PRAKOPA = "PRAKOPA"                      # Aggravation / excitation
    PRASARA = "PRASARA"                      # Systemic overflow and dissemination
    STHANA_SAMSHRAYA = "STHANA_SAMSHRAYA"    # Localization in defective Srotas (Prodromal)
    VYAKTI = "VYAKTI"                        # Full clinical manifestation of disease
    BHEDAVASTHA = "BHEDAVASTHA"              # Chronicity, complications, tissue structural damage


class RogiBalaGrade(str, Enum):
    """Patient stamina and physical reserve grading."""
    UTTAMA = "UTTAMA"            # Superior vitality
    MADHYAMA = "MADHYAMA"        # Moderate vitality
    AVARA = "AVARA"              # Debilitated vitality


class GovernanceStatus(str, Enum):
    """Statutory Human-in-the-Loop decision support lifecycle under NCISM Act 2020."""
    DRAFT_DECISION_SUPPORT = "DRAFT_DECISION_SUPPORT"
    PHYSICIAN_COUNTERSIGNED = "PHYSICIAN_COUNTERSIGNED"
    REJECTED_BY_PHYSICIAN = "REJECTED_BY_PHYSICIAN"


class ShodhanaEligibility(str, Enum):
    """Panchakarma bio-purification eligibility based on Ama and Rogi Bala gating."""
    CONTRAINDICATED_SAMA_STATE = "CONTRAINDICATED_SAMA_STATE"  # Shodhana causes fatal Ama displacement
    ELIGIBLE_FOR_PURVAKARMA = "ELIGIBLE_FOR_PURVAKARMA"        # Deepana-Pachana completed, Snehana-Swedana indicated
    READY_FOR_PRADHANA_KARMA = "READY_FOR_PRADHANA_KARMA"      # Utklishta Doshas ready for Vamana/Virechana/Basti
    NOT_INDICATED = "NOT_INDICATED"                            # Managed strictly with Shamana and Ahara-Vihara


# -------------------------------------------------------------------------
# Sub-Models & Evidence Hierarchy
# -------------------------------------------------------------------------

class EvidenceRankingLevel(str, Enum):
    """Clinical Evidence Ranking Hierarchy (Levels A to F)."""
    LEVEL_A = "Level A (Systematic Reviews / Double-Blind RCTs)"
    LEVEL_B = "Level B (Controlled Clinical Trials / Open Pragmatic Trials)"
    LEVEL_C = "Level C (Cohort Studies / Pharmacovigilance Registries)"
    LEVEL_D = "Level D (Published Institutional Case Reports)"
    LEVEL_E = "Level E (Classical Brihat/Laghu Trayi Shastra Citations)"
    LEVEL_F = "Level F (Clinical Expert Consensus)"


class EvidenceAttribution(BaseModel):
    """Evidence grading and provenance tracking."""
    level: str = "Level E (Classical Brihat/Laghu Trayi Shastra Citations)"
    source_reference: str = "Charaka Samhita / Sushruta Samhita / CCRAS Clinical Guidelines"
    source_doi_or_shloka: str = "CS.Chi.1/1; AH.Su.1/1"
    verification_hash: Optional[str] = None
    confidence_score: float = Field(default=0.85, ge=0.0, le=1.0)


class DualMorbidityCode(BaseModel):
    """Dual-coding entity bridging classical Ayurveda, NAMASTE portal, and WHO ICD-11 TM2."""
    sanskrit_name: str
    namaste_code: str
    icd11_tm2_code: str
    icd11_title: str
    confidence_score: float = Field(ge=0.0, le=1.0)


class PrescribedFormulation(BaseModel):
    """Polyherbal medicinal formulation with dosage, timing, and anupana vehicle."""
    formulation_name: str
    kalpana_form: str
    dosage: str
    timing: str
    anupana: str
    classical_reference: str
    target_pathology: str


class GenericSubstitution(BaseModel):
    """IMPCL / PMBJP Jan Aushadhi generic alternative with cost transparency."""
    branded_or_classical_name: str
    generic_impcl_name: str
    jan_aushadhi_code: str
    cost_savings_percentage: float = 40.0


class ComprehensiveTreatmentPlan(BaseModel):
    """Unified therapeutic prescription protocol complying with Canonical 9-Part Standard."""
    evidence_ranking: EvidenceAttribution = Field(default_factory=EvidenceAttribution)
    shamana_chikitsa: List[PrescribedFormulation] = Field(default_factory=list)
    generic_substitutions: List[GenericSubstitution] = Field(default_factory=list)
    shodhana_eligibility: ShodhanaEligibility = ShodhanaEligibility.NOT_INDICATED
    shodhana_guidance_notes: str = ""
    samsarjana_krama_schedule: Optional[Dict[str, Any]] = None
    pathya_ahara: List[str] = Field(default_factory=list)
    apathya_ahara: List[str] = Field(default_factory=list)
    swasthavritta_vihara: List[str] = Field(default_factory=list)
    parasurgical_referral: Optional[str] = None
    rasayana_rehabilitation: Optional[str] = None
    tier1_ayurvedic_requisitions: List[str] = Field(default_factory=list)
    tier2_integrative_biomarkers: List[str] = Field(default_factory=list)
    emergency_escalation_criteria: Optional[str] = None


class ClinicalIntakeData(BaseModel):
    """Patient clinical intake presentation and examination findings."""
    patient_id: str
    hospital_id: str
    chief_complaints: List[str]
    symptoms: List[str]
    duration_weeks: float = 2.0
    prakriti_vector: Optional[Dict[str, float]] = None
    vikriti_vector: Optional[Dict[str, float]] = None
    nadi_gati: Optional[str] = None
    jihwa_coating: Optional[str] = None
    appetite_and_digestion: Optional[str] = None
    vitiated_srotases: Optional[List[str]] = None
    vitiated_dhatus: Optional[List[str]] = None
    rogi_bala: RogiBalaGrade = RogiBalaGrade.MADHYAMA
    systolic_bp: int = 120
    diastolic_bp: int = 80
    hemoglobin_g_dl: float = 13.0
    is_pregnant: bool = False
    current_medications: List[str] = Field(default_factory=list)


class CounterSignRequest(BaseModel):
    """NCISM Registered Physician Counter-Signature payload."""
    physician_arn: str
    action: str = Field(default="COUNTERSIGN", description="'COUNTERSIGN' or 'REJECT'")
    clinical_notes: Optional[str] = None


class DiagnosisEpisodeResponse(BaseModel):
    """Authoritative Ayurvedic Diagnostic Record and Clinical Decision Support Summary."""
    episode_id: str
    patient_id: str
    hospital_id: str
    primary_diagnosis: DualMorbidityCode
    differential_diagnoses: List[DualMorbidityCode]
    vikriti_vector: Dict[str, float]
    vikriti_divergence_metric: float
    agni_status: AgniStatus
    ama_status: AmaStatus
    shat_kriya_kala_stage: ShatKriyaKalaStage
    rogi_bala: RogiBalaGrade
    doshic_dushya_sammurchhana: Dict[str, Any]
    treatment_protocol: ComprehensiveTreatmentPlan
    safety_firewalls_cleared: bool
    safety_alerts: List[str]
    governance_status: GovernanceStatus
    attending_physician_arn: Optional[str] = None
    countersigned_at: Optional[int] = None
    patient_summary_report_markdown: str
    created_at: int
