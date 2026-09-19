"""
Shalakya Tantra, Netra Kriya Kalpa & ENT Microsurgical Models
============================================================
Defines schemas for:
1. 76 Classical Netra Rogas across 6 Mandalas & 4 Patalas
2. 7 Ocular Kriya Kalpas (Aschyotana, Seka, Pindi, Bidalaka, Tarpana, Putapaka, Anjana)
3. Tarpana Matrakala dosage timing, lipid pool mechanics & photoprotection protocols
4. Acute Adhimantha (Angle-Closure Glaucoma) Emergency Triage Firewall
5. ENT micro-therapeutics (Karna Purana, Karna Dhoopana, Pratimarsa/Marsha Nasya)
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class NetraMandala(str, Enum):
    PAKSHMA = "PAKSHMA"          # Cilia & Lid margins (Pakshmakopa, Pakshmashata)
    VARTMA = "VARTMA"            # Eyelids & Tarsus (Utsangini, Kumbhika, Pothaki, Vartmakardama)
    SHUKLA = "SHUKLA"            # Sclera & Bulbar Conjunctiva (Arma, Suktika, Sirajala, Pishtaka)
    KRISHNA = "KRISHNA"          # Cornea & Limbal region (Savrana Sukra, Avrana Sukra, Ajakajata)
    DRISHTI = "DRISHTI"          # Pupil, Lens, Retina, Visual apparatus (Timira, Kacha, Linganasha)
    SARVAGATA = "SARVAGATA"      # Pan-ocular disorders (Abhishyanda, Adhimantha, Sasopha Netrapaka)


class NetraPatala(str, Enum):
    BAHYA = "BAHYA"              # Superficial / External tissue involvement
    PRATHAMA = "PRATHAMA"        # 1st Tunic: Tejas + Dosha causing indistinct/hazy vision (Avyakta Darshana)
    DWITIYA = "DWITIYA"          # 2nd Tunic: Distorted vision, flies/webs floating (Vihvala Darshana)
    TRITIYA = "TRITIYA"          # 3rd Tunic: Severe loss, quadrant field defect, diplopia (Kacha/Adhimantha)
    CHATURTHA = "CHATURTHA"      # 4th Tunic: Complete visual occlusion / blindess (Linganasha)
    SARVA_PATALA = "SARVA_PATALA"# Generalized pan-patala penetration


class SadhyaAsadhyata(str, Enum):
    SADHYA = "SADHYA"                    # Easily curable
    KRICCHRA_SADHYA = "KRICCHRA_SADHYA"  # Curable with difficulty / refractory
    YAPYA = "YAPYA"                      # Palliative / chronicity requiring life-long management
    ASADHYA = "ASADHYA"                  # Incurable / surgical/medical contraindication


class KriyaKalpaType(str, Enum):
    ASCHYOTANA = "ASCHYOTANA"    # Medicated eye drops / instillations
    SEKA = "SEKA"                # Continuous closed-eye medicated liquid irrigation
    PINDI = "PINDI"              # Medicated warm/cool herbal poultice bandaging
    BIDALAKA = "BIDALAKA"        # Medicated herbal paste smeared on eyelids (excluding lashes)
    TARPANA = "TARPANA"          # Medicated unctuous lipid retention in periorbital dough ring
    PUTAPAKA = "PUTAPAKA"        # Post-Tarpana lipid/decoction bio-extractive retention
    ANJANA = "ANJANA"            # Medicated collyrium applied to lid margins (Gutika, Rasa, Churna)


class NetraRogaProfile(BaseModel):
    """Classical Netra Roga anatomical and clinical specification."""
    roga_code: str
    sanskrit_name: str
    english_name: str
    icd11_mapping: str
    anatomical_mandala: NetraMandala
    anatomical_patala: NetraPatala
    doshic_etiology: str
    sadhya_asadhyata: SadhyaAsadhyata
    kriya_kalpa_indications: List[KriyaKalpaType]
    contraindicated_procedures: List[KriyaKalpaType]


class TarpanaSessionCreate(BaseModel):
    """Log an ocular Tarpana Kriya Kalpa session."""
    patient_id: str
    eye_side: str = Field(..., description="LEFT, RIGHT, or BILATERAL")
    ghrita_used: str = Field(..., description="E.g. Triphala Ghrita, Mahatriphala Ghrita, Jeevantyadi Ghrita")
    doshic_indication: str = Field(..., description="VATAJA, PITTAJA, KAPHAJA, SWASTHA, or DRISHTI_PRASADANA")
    clinical_indication: str
    retention_matrakalas: Optional[int] = Field(None, ge=100, le=1200, description="Matrakala count; computed if omitted")
    practitioner_arn: str


class TarpanaSessionResponse(BaseModel):
    """Validated Tarpana procedure record with exact retentive timings and safety regimen."""
    session_id: str
    patient_id: str
    hospital_id: str
    eye_side: str
    ghrita_used: str
    retention_matrakalas: int
    retention_duration_seconds: int
    clinical_indication: str
    post_procedure_precautions: List[str]
    practitioner_arn: str
    created_at: int


class EntTherapyType(str, Enum):
    KARNA_PURANA = "KARNA_PURANA"          # Medicated ear oil filling / retention
    KARNA_DHOOPANA = "KARNA_DHOOPANA"      # Medicated aseptic ear fumigation
    KARNA_PRAKSHALANA = "KARNA_PRAKSHALANA"# Medicated auditory canal washing
    PRATIMARSHA_NASYA = "PRATIMARSHA_NASYA"# Prophylactic daily 2-drop nasal oil instillation
    MARSHA_NASYA = "MARSHA_NASYA"          # Intensive therapeutic 4-8 drop nasal oil instillation
    NASYA_DHUMAPANA = "NASYA_DHUMAPANA"    # Medicated smoke inhalation via nasal route
    KAVALA_GANDUSHA = "KAVALA_GANDUSHA"    # Oral gargle or medicated retention for supraclavicular health


class EntProcedureCreate(BaseModel):
    """Log an ENT micro-therapeutic procedure."""
    patient_id: str
    therapy_type: EntTherapyType
    anatomical_site: str = Field(..., description="LEFT_EAR, RIGHT_EAR, BILATERAL_EARS, BILATERAL_NASAL, OROPHARYNX")
    medicated_oil_used: str = Field(..., description="E.g. Bilva Taila, Ksharatila Taila, Anu Taila, Shadbindu Taila")
    dosage_drops_or_ml: str = Field(..., description="E.g. '10 drops', '5 ml', '2 drops each nostril'")
    eardrum_perforated: bool = Field(False, description="Tympanic membrane perforation status")
    observations: str
    practitioner_arn: str


class EntProcedureResponse(BaseModel):
    """ENT therapeutic procedure execution response with safety clearance."""
    procedure_id: str
    patient_id: str
    hospital_id: str
    therapy_type: EntTherapyType
    anatomical_site: str
    medicated_oil_used: str
    dosage_drops_or_ml: str
    observations: str
    safety_cleared: bool
    contraindication_notes: Optional[str] = None
    practitioner_arn: str
    created_at: int


class OphthalmicScreeningRequest(BaseModel):
    """Emergency ophthalmic screening and triage evaluation."""
    patient_id: str
    presenting_symptoms: List[str]
    intraocular_pressure_mmhg: Optional[float] = Field(None, ge=0.0, le=90.0, description="IOP by tonometry in mmHg")
    visual_acuity: Optional[str] = None
    severe_ocular_pain: bool = False
    hemicrania_headache: bool = False
    halos_around_lights: bool = False
    sudden_vision_loss: bool = False
    corneal_edema_steamy: bool = False
    pupil_fixed_mid_dilated: bool = False
    evaluator_arn: str


class OphthalmicScreeningResponse(BaseModel):
    """Ophthalmic screening triage with acute Adhimantha (Glaucoma) firewall."""
    patient_id: str
    triage_level: str = Field(..., description="NORMAL, ROUTINE, URGENT, CRITICAL_EMERGENCY")
    suspected_condition: str
    adhimantha_glaucoma_firewall_triggered: bool
    contraindicated_kriya_kalpas: List[KriyaKalpaType]
    clinical_action_plan: List[str]
    emergency_escalation_protocol: Optional[str] = None
