"""
Nidana Panchaka Diagnostic Knowledge Graph & Differential Diagnosis Models
========================================================================
Implements Pydantic schemas for the 5-fold classical diagnostic framework:
1. Nidana (Etiology: Aharaja, Viharaja, Manasika, Agantuja)
2. Purvaroopa (Prodrome: Samanya, Vishishta)
3. Roopa (Cardinal Signs & Symptoms, Pratyatma Linga)
4. Upashaya / Anupashaya (Therapeutic Diagnostic Trial & Verification)
5. Samprapti (Pathophysiological Dynamics & Ghatakas)
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class NidanaCategory(str, Enum):
    AHARAJA = "AHARAJA"
    VIHARAJA = "VIHARAJA"
    MANASIKA = "MANASIKA"
    AGANTUJA = "AGANTUJA"


class UpashayaCategory(str, Enum):
    HETU_VIPARITA = "HETU_VIPARITA"                  # Inverse to causative factor
    VYADHI_VIPARITA = "VYADHI_VIPARITA"              # Inverse to disease essence
    HETU_VIPARITARTHAKARI = "HETU_VIPARITARTHAKARI"  # Mimicking cause, therapeutic effect
    VYADHI_VIPARITARTHAKARI = "VYADHI_VIPARITARTHAKARI" # Mimicking symptom, therapeutic effect


class UpashayaOutcome(str, Enum):
    UPASHAYA_RELIEVED = "UPASHAYA_RELIEVED"          # Symptoms alleviated (confirms diagnosis)
    ANUPASHAYA_AGGRAVATED = "ANUPASHAYA_AGGRAVATED"  # Symptoms exacerbated (confirms contraindication/doshic axis)
    EQUIVOCAL = "EQUIVOCAL"                          # Indifferent / no significant alteration


class Rogamarga(str, Enum):
    ABHYANTARA = "ABHYANTARA"  # Internal / Kostha / Digestive tract
    BAHYA = "BAHYA"            # External / Shakha / Twak, Rakta, Mamsa
    MADHYAMA = "MADHYAMA"      # Intermediate / Marma, Asthi, Sandhi, Snayu


class SrotodushtiPattern(str, Enum):
    ATI_PRAVRITTI = "ATI_PRAVRITTI"    # Excessive overflow / hypersecretion
    SANGA = "SANGA"                    # Obstruction / stagnation
    SIRA_GRANTHI = "SIRA_GRANTHI"      # Nodulation / morphological dilations
    VIMARGA_GAMANA = "VIMARGA_GAMANA"  # Extravasation / retrograde circulation


class AgniState(str, Enum):
    SAMAGNI = "SAMAGNI"
    VISHAMAGNI = "VISHAMAGNI"
    TIKSHNAGNI = "TIKSHNAGNI"
    MANDAGNI = "MANDAGNI"


class AmaStatus(str, Enum):
    NIRAMA = "NIRAMA"
    SAMA = "SAMA"


class CurabilityPrognosis(str, Enum):
    SUKHASADHYA = "SUKHASADHYA"
    KRICHRASADHYA = "KRICHRASADHYA"
    YAPYA = "YAPYA"
    ASADHYA = "ASADHYA"


class UpashayaTrialInput(BaseModel):
    """Represents a diagnostic therapeutic test administered to the patient."""
    description: str = Field(..., description="Details of the Ahara, Aushadha, or Vihara administered")
    category: UpashayaCategory = Field(..., description="Classical Upashaya category")
    outcome: UpashayaOutcome = Field(..., description="Observed outcome after administration")
    modality: str = Field(default="Aushadha", description="Ahara, Aushadha, or Vihara")


class SampraptiGhatakas(BaseModel):
    """Comprehensive classical pathogenetic breakdown."""
    primary_dosha: str
    secondary_doshas: List[str] = Field(default_factory=list)
    dushya: List[str] = Field(..., description="Tissues or waste products primarily vitiated")
    agni: AgniState
    ama: AmaStatus
    srotas: List[str] = Field(..., description="Involved internal channels")
    srotodushti: List[SrotodushtiPattern] = Field(..., description="Observed patterns of channel dysregulation")
    udbhava_sthana: str = Field(..., description="Site of pathological inception")
    sanchara_sthana: str = Field(..., description="Path of systemic dissemination")
    vyakti_sthana: str = Field(..., description="Anatomical location of full manifestation")
    rogamarga: Rogamarga = Field(..., description="Disease pathway tier")


class DiseaseArchetype(BaseModel):
    """Classical reference disease entity in the diagnostic knowledge graph."""
    code: str
    sanskrit_name: str
    english_name: str
    doshic_predominance: List[str]
    nidanas: List[str] = Field(..., description="Cardinal etiological factors")
    purvaroopas: List[str] = Field(..., description="Prodromal symptoms")
    roopas: List[str] = Field(..., description="Cardinal clinical symptoms")
    pratyatma_lingas: List[str] = Field(..., description="Hallmark pathognomonic clinical features")
    beneficial_upashayas: List[str] = Field(default_factory=list, description="Substances or regimens relieving condition")
    aggravating_anupashayas: List[str] = Field(default_factory=list, description="Substances or regimens aggravating condition")
    samprapti_ghatakas: SampraptiGhatakas
    curability: CurabilityPrognosis


class DifferentialDiagnosisItem(BaseModel):
    """Ranked diagnosis candidate with match analytics and key discriminators."""
    disease_code: str
    disease_name: str
    match_score: float = Field(..., ge=0.0, le=100.0, description="Overall weighted multi-axial overlap percentage")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Calculated diagnostic confidence")
    matched_roopa: List[str] = Field(default_factory=list)
    matched_purvaroopa: List[str] = Field(default_factory=list)
    matched_nidana: List[str] = Field(default_factory=list)
    matched_upashaya: List[str] = Field(default_factory=list)
    pratyatma_linga_matched: List[str] = Field(default_factory=list)
    key_differentiators: List[str] = Field(default_factory=list, description="Features that distinguish this from other candidates")
    exclusion_rationale: Optional[str] = Field(default=None, description="Reason if relegated to secondary differential")


class NidanaPanchakaEvaluationInput(BaseModel):
    """Patient presentation payload for differential diagnostic evaluation."""
    patient_id: str
    presented_nidana: List[str] = Field(default_factory=list, description="Observed dietary, lifestyle, or mental triggers")
    presented_purvaroopa: List[str] = Field(default_factory=list, description="Observed prodromal symptoms")
    presented_roopa: List[str] = Field(..., min_length=1, description="Active clinical symptoms and signs")
    upashaya_trials: List[UpashayaTrialInput] = Field(default_factory=list, description="Results of therapeutic diagnostic trials")
    observed_doshas: Optional[List[str]] = Field(default=None, description="Clinically determined doshas (e.g. from Vikriti)")
    observed_dushya: Optional[List[str]] = Field(default=None, description="Clinically determined tissues involved")


class NidanaPanchakaEvaluationOutput(BaseModel):
    """Diagnostic evaluation response with ranked differentials and Samprapti breakdown."""
    assessment_id: str
    patient_id: str
    hospital_id: str
    evaluator_arn: str
    primary_diagnosis: DifferentialDiagnosisItem
    differential_diagnoses: List[DifferentialDiagnosisItem]
    samprapti_ghatakas: SampraptiGhatakas
    pratyatma_linga_matched: List[str]
    clinical_recommendations: List[str]
    timestamp: int
