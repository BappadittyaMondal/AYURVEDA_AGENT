"""
Rasa Shastra & Herbo-Mineral Processing Safety Models
=====================================================
Defines schemas for:
1. Classical classification of minerals, metals, and Schedule E(1) poisons
2. Shodhana (purification & detoxification) protocols and verification records
3. Marana & Puta (calcination) furnace types and cycle standards
4. Classical Bhasma Pariksha (7 nanoscale quality control criteria)
5. Modern Physicochemical, Elemental (AAS/ICP-MS), and Particle Size standards
6. Permitted Daily Exposure (PDE) & cumulative heavy metal safety thresholds
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RasaCategory(str, Enum):
    MAHARASA = "MAHARASA"                    # 8 primary sovereign minerals
    UPARASA = "UPARASA"                      # 8 secondary sulfur & salt minerals
    SADHARANA_RASA = "SADHARANA_RASA"        # 8 common minerals & compounds
    DHATU_SHUDDHA = "DHATU_SHUDDHA"          # Noble / Pure metals (Au, Ag, Cu, Fe)
    DHATU_PUTI = "DHATU_PUTI"                # Low-melting / volatile metals (Pb, Sn, Zn)
    DHATU_MISHRA = "DHATU_MISHRA"            # Classical metal alloys (Brass, Bronze, Varta)
    RATNA_UPARATNA = "RATNA_UPARATNA"        # Precious gems & subordinate stones
    VISHA_UPAVISHA = "VISHA_UPAVISHA"        # Schedule E(1) statutory plant/mineral poisons


class ShodhanaMethod(str, Enum):
    SWEDANA_DOLA_YANTRA = "SWEDANA_DOLA_YANTRA"  # Steaming/boiling in liquid media in suspended pouch
    BHAVANA_TRITURATION = "BHAVANA_TRITURATION"  # Wet trituration/levigation in mortar with herbal decoctions
    NIRVAPA_QUENCHING = "NIRVAPA_QUENCHING"      # Repeated heating to red-hot and quenching in liquid media
    DHALANA_MELTING_POURING = "DHALANA_MELTING_POURING"  # Melting and pouring into liquid through cloth/filter
    KSHALANA_WASHING = "KSHALANA_WASHING"        # Successive washings with hot water or alkaline decoction
    BHARJANA_ROASTING = "BHARJANA_ROASTING"      # Dry or medicated pan roasting/calcining on open heat


class PutaType(str, Enum):
    MAHA_PUTA = "MAHA_PUTA"          # 1500 cow dung cakes (1000-1100°C) - for Abhraka, Lauha
    GAJA_PUTA = "GAJA_PUTA"          # 1000 cow dung cakes (900-1000°C) - for Tamra, Lauha, Vaikranta
    VARAHA_PUTA = "VARAHA_PUTA"      # 500 cow dung cakes (750-850°C) - for Swarna, Rajata, Shankha
    KUKKUTA_PUTA = "KUKKUTA_PUTA"    # 100 cow dung cakes (500-600°C) - for Vanga, Yashada, Swarna Makshika
    KAPOTA_PUTA = "KAPOTA_PUTA"      # 8 cow dung cakes (400-450°C) - for mild surface incineration
    VALUKA_YANTRA = "VALUKA_YANTRA"  # Sand-bath gradual thermal gradient for Kupipakwa Rasayana


class BhasmaPariksha(BaseModel):
    """
    Seven Classical Nanocrystalline Criteria for Bhasma Verification (Rasaratnasamucchaya).
    All seven must be verified True for a Bhasma batch release.
    """
    varitara: bool = Field(..., description="Floats on stagnant water surface due to ultra-fine particle size")
    unama: bool = Field(..., description="Grains of rice placed on floating Bhasma layer remain floating")
    rekhapurna: bool = Field(..., description="Particles enter micro-furrows of fingertips upon rubbing (<20 microns)")
    apunarbhava: bool = Field(..., description="Does not revert to metallic state when heated with Mitra Panchaka at high temperature")
    niruttha: bool = Field(..., description="Does not form alloy or impart weight increase when heated with silver leaf (Rajata Patra)")
    nis_svadu: bool = Field(..., description="Completely devoid of metallic, astringent, or caustic taste")
    nischandrika: bool = Field(..., description="Total absence of metallic luster or shine under bright light/sunlight")


class ElementalAssay(BaseModel):
    """
    AAS / ICP-MS Elemental Assay and Toxic Contaminant Quantitation (AFI / AYUSH Standards).
    All heavy metal contaminant thresholds in parts per million (ppm = mg/kg).
    """
    lead_pb_ppm: float = Field(..., ge=0.0, description="Lead (Pb) concentration in ppm (Statutory max: 10.0 ppm)")
    arsenic_as_ppm: float = Field(..., ge=0.0, description="Arsenic (As) concentration in ppm (Statutory max: 3.0 ppm)")
    cadmium_cd_ppm: float = Field(..., ge=0.0, description="Cadmium (Cd) concentration in ppm (Statutory max: 0.3 ppm)")
    mercury_hg_ppm: float = Field(..., ge=0.0, description="Mercury (Hg) concentration in ppm (Statutory max: 1.0 ppm)")
    active_metal_name: Optional[str] = Field(None, description="Name of intended therapeutic metallic element (e.g. Gold, Iron, Zinc, Copper)")
    active_metal_percentage: Optional[float] = Field(None, ge=0.0, le=100.0, description="Total therapeutic element assay percentage (w/w)")
    free_ionic_toxic_metal_ppm: float = Field(0.0, ge=0.0, description="Free toxic ionic metal concentration (e.g. Free Hg2+, Free Cu2+; max <= 0.1 ppm)")


class ParticleSizeAnalysis(BaseModel):
    """Laser Diffraction Particle Size Distribution (PSD) metrics."""
    d10_microns: float = Field(..., gt=0.0, description="10% cumulative diameter in microns")
    d50_microns: float = Field(..., gt=0.0, description="Median diameter (D50) in microns (Standard <= 5.0 microns)")
    d90_microns: float = Field(..., gt=0.0, description="90% cumulative diameter (D90) in microns (Standard <= 15.0 microns)")
    nanoscale_percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of particles under 1.0 micron (Standard >= 15%)")


class RasaMineralRecord(BaseModel):
    """Registered Classical Mineral, Metal, or Schedule E(1) Poison Profile."""
    mineral_id: str = Field(..., description="Unique mineral identifier")
    sanskrit_name: str = Field(..., description="Classical Sanskrit nomenclature")
    english_name: str = Field(..., description="Standard English / Mineralogical name")
    chemical_formula: str = Field(..., description="Principal chemical formula or geological composition")
    category: RasaCategory = Field(..., description="Rasashastra taxonomic category")
    is_schedule_e1_poison: bool = Field(..., description="Flag indicating Drugs & Cosmetics Act Schedule E(1) status")
    shodhana_required: bool = Field(..., description="Mandatory purification requirement prior to any processing")
    standard_shodhana_method: ShodhanaMethod = Field(..., description="Canonical classical Shodhana procedure")
    standard_shodhana_media: List[str] = Field(..., description="Liquid or herbal processing media used during Shodhana")
    minimum_shodhana_cycles: int = Field(..., ge=1, description="Minimum cycles/repetitions required for complete Shodhana")
    standard_puta_type: Optional[PutaType] = Field(None, description="Standard furnace/puta type for Marana")
    minimum_puta_cycles: int = Field(0, ge=0, description="Mandatory minimum Puta calcination cycles")
    therapeutic_dose_mg_min: float = Field(..., gt=0.0, description="Minimum single therapeutic dose in mg")
    therapeutic_dose_mg_max: float = Field(..., gt=0.0, description="Maximum single therapeutic dose in mg")
    classical_indications: List[str] = Field(..., description="Therapeutic indications and target conditions")
    toxicity_risk_profile: str = Field(..., description="Toxicological risk and consequence of improper purification")


class ShodhanaVerificationRequest(BaseModel):
    """Submission schema to certify Shodhana completion for a raw material batch."""
    batch_id: str = Field(..., description="Unique raw material batch identifier")
    mineral_id: str = Field(..., description="Identifier of mineral/poison from registry")
    method: ShodhanaMethod = Field(..., description="Method utilized for Shodhana")
    media_used: List[str] = Field(..., description="Processing media employed")
    cycles_completed: int = Field(..., ge=1, description="Number of complete Shodhana cycles carried out")
    organoleptic_shuddhi_confirmed: bool = Field(..., description="Verification that classical Shuddhi Lakshanas are satisfied")
    verified_by_arn: str = Field(..., description="NCISM ARN of supervising Rasa Shastra physician or pharmacist")
    notes: Optional[str] = Field(None, description="Optional analytical or process remarks")


class ShodhanaRecord(BaseModel):
    """Persisted Shodhana verification record."""
    record_id: str
    batch_id: str
    mineral_id: str
    method: ShodhanaMethod
    media_used: List[str]
    cycles_completed: int
    verified_by_arn: str
    organoleptic_shuddhi_confirmed: bool
    is_verified: bool
    notes: Optional[str] = None
    created_at: int


class BhasmaBatchReleaseRequest(BaseModel):
    """Quality control submission for Bhasma batch analytical release."""
    batch_id: str = Field(..., description="Unique Bhasma batch lot number")
    mineral_id: str = Field(..., description="Source mineral/metal identifier")
    formulation_name: str = Field(..., description="Classical formulation title (e.g. Yashada Bhasma, Swarna Bhasma)")
    puta_type: PutaType = Field(..., description="Furnace type utilized during Marana")
    putas_completed: int = Field(..., ge=1, description="Number of completed Puta calcination cycles")
    classical_pariksha: BhasmaPariksha = Field(..., description="Seven classical nanoscale quality tests")
    elemental_assay: ElementalAssay = Field(..., description="AAS / ICP-MS heavy metal and active element concentrations")
    particle_size: ParticleSizeAnalysis = Field(..., description="Particle size distribution metrics")
    certified_by_arn: str = Field(..., description="NCISM ARN of certifying Quality Assurance Physician")


class BhasmaBatchReleaseCertificate(BaseModel):
    """Full analytical release dossier and safety verdict for a Bhasma batch."""
    batch_id: str
    mineral_id: str
    formulation_name: str
    puta_type: PutaType
    putas_completed: int
    classical_pariksha: BhasmaPariksha
    elemental_assay: ElementalAssay
    particle_size: ParticleSizeAnalysis
    is_classical_certified: bool
    puta_count_adequate: bool
    heavy_metals_safe: bool
    particle_size_compliant: bool
    overall_batch_released: bool
    rejection_reasons: List[str]
    certified_by_arn: str
    certification_timestamp: int


class BatchPrescriptionItem(BaseModel):
    """Specific Bhasma batch item in a therapeutic prescription regimen."""
    batch_id: str = Field(..., description="Batch lot number")
    daily_dose_mg: float = Field(..., gt=0.0, description="Daily prescribed dose in mg")
    duration_days: int = Field(..., ge=1, le=180, description="Course duration in days")


class HeavyMetalExposureCheckRequest(BaseModel):
    """Patient prescription heavy metal exposure evaluation request."""
    patient_id: str = Field(..., description="Patient identifier")
    prescriptions: List[BatchPrescriptionItem] = Field(..., min_length=1, description="Prescription items to assess")


class HeavyMetalExposureCheckResponse(BaseModel):
    """Permitted Daily Exposure (PDE) & cumulative safety verdict."""
    patient_id: str
    daily_lead_mg: float
    daily_arsenic_mg: float
    daily_cadmium_mg: float
    daily_mercury_mg: float
    pde_lead_mg_limit: float = 0.005      # 5 mcg/day
    pde_arsenic_mg_limit: float = 0.015   # 15 mcg/day
    pde_cadmium_mg_limit: float = 0.005   # 5 mcg/day
    pde_mercury_mg_limit: float = 0.030   # 30 mcg/day
    cumulative_lead_mg: float
    cumulative_arsenic_mg: float
    cumulative_cadmium_mg: float
    cumulative_mercury_mg: float
    is_within_pde_limits: bool
    safety_verdict: str
    warnings: List[str]
