"""Pydantic schemas for Srotas Pathology Matrix & Khavaigunya Mapping Engine (14 Channels)."""
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class SrotasType(str, Enum):
    """The 14 classical macro and micro-circulatory channels (Charaka Vimanasthana 5)."""
    PRANAVAHA = "PRANAVAHA"      # Respiratory / vital prana channel
    UDAKAVAHA = "UDAKAVAHA"      # Fluid / water metabolism channel
    ANNAVAHA = "ANNAVAHA"        # Alimentary / digestive channel
    RASAVAHA = "RASAVAHA"        # Lymphatic / plasma channel
    RAKTAVAHA = "RAKTAVAHA"      # Hematopoietic / vascular channel
    MAMSAVAHA = "MAMSAVAHA"      # Muscular / fascial channel
    MEDOVAHA = "MEDOVAHA"        # Adipose / lipid channel
    ASTHIVAHA = "ASTHIVAHA"      # Skeletal / osseous channel
    MAJJAVAHA = "MAJJAVAHA"      # Bone marrow / neuro-endocrine channel
    SHUKRAVAHA = "SHUKRAVAHA"    # Reproductive / generative channel
    MUTRAVAHA = "MUTRAVAHA"      # Urinary / renal channel
    PURISHAVAHA = "PURISHAVAHA"  # Lower gastrointestinal / fecal channel
    SVEDAVAHA = "SVEDAVAHA"      # Sudoriferous / thermoregulatory channel
    MANOVAHA = "MANOVAHA"        # Psychological / neuro-cognitive channel


class DushtiType(str, Enum):
    """Chaturvidha Srotodushti classical pathological mechanisms."""
    ATI_PRAVRITTI = "ATI_PRAVRITTI"    # Hyper-secretion / excessive outflow / hyperactivity
    SANGA = "SANGA"                    # Obstruction / occlusion / stenosis / retention
    SIRA_GRANTHI = "SIRA_GRANTHI"      # Aneurysmal dilatation / nodulation / varicose distortion
    VIMARGA_GAMANA = "VIMARGA_GAMANA"  # Extravasation / retrograde translocation / aberrant path
    PRAKRITA = "PRAKRITA"              # Physiological normal patency


class ChannelObservation(BaseModel):
    """Examiner ratings for the four pathological manifestations per channel (0-3 scale)."""
    srotas: SrotasType
    ati_pravritti: int = Field(default=0, ge=0, le=3, description="0=None, 1=Mild, 2=Mod, 3=Severe")
    sanga: int = Field(default=0, ge=0, le=3, description="Obstruction / retention")
    sira_granthi: int = Field(default=0, ge=0, le=3, description="Nodulation / structural deformity")
    vimarga_gamana: int = Field(default=0, ge=0, le=3, description="Aberrant / reverse flow")
    pre_existing_defect: bool = Field(default=False, description="True if anatomical or constitutional Khavaigunya exists")


class SrotasInput(BaseModel):
    """Input payload providing telemetry or examiner observation for evaluated Srotamsi."""
    patient_id: str = Field(..., description="Target patient UUID")
    channels: List[ChannelObservation] = Field(..., min_length=1, max_length=14, description="Channel observations")


class ChannelDetail(BaseModel):
    """Processed pathological metrics and anatomical root correlation for a Srotas."""
    srotas: SrotasType
    mula_sthana: List[str]
    involvement_score: float
    dominant_dushti: DushtiType
    has_khavaigunya: bool
    clinical_manifestation: str


class SrotoshodhanaDirective(BaseModel):
    """Clinical therapeutics for channel clearance and tissue restoration."""
    srotas: SrotasType
    primary_dushti: DushtiType
    shodhana_karma: str
    herbal_clearing_agents: List[str]
    dietary_guidelines: List[str]


class SrotasOutput(BaseModel):
    """Complete Srotas pathology profile, Khavaigunya mapping, and Srotoshodhana protocol."""
    assessment_id: str
    patient_id: str
    hospital_id: str
    evaluator_arn: str
    overall_srotas_index: float
    vulnerable_channels_count: int
    channel_details: List[ChannelDetail]
    khavaigunya_channels: List[str]
    srotoshodhana_directives: List[SrotoshodhanaDirective]
    timestamp: int
    model_config = ConfigDict(from_attributes=True)
