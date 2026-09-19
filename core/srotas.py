"""Srotas Pathology Matrix & Khavaigunya Mapping Engine (14 Channels).

Classical References:
- Charaka Samhita, Vimanasthana Ch. 5 (Srotovimana Adhyaya)
- Sushruta Samhita, Sharirasthana Ch. 9 (Dhamani Vyakhyana Sharira)
- Ashtanga Hridaya, Sharirasthana Ch. 3 (Angavibhaga Adhyaya)
"""
import uuid
import time
from typing import Dict, List, Tuple

from models.srotas import (
    SrotasType,
    DushtiType,
    ChannelObservation,
    ChannelDetail,
    SrotoshodhanaDirective,
    SrotasInput,
    SrotasOutput,
)


MULA_STHANA_REGISTRY: Dict[SrotasType, List[str]] = {
    SrotasType.PRANAVAHA: ["Hridaya (Heart)", "Mahasrotas (Alimentary tract / Bronchi)"],
    SrotasType.UDAKAVAHA: ["Talu (Palate)", "Kloma (Pancreas / fluid regulator)"],
    SrotasType.ANNAVAHA: ["Amashaya (Stomach)", "Vamaparshva (Left flank / gastro-esophageal junction)"],
    SrotasType.RASAVAHA: ["Hridaya (Heart)", "Dasha Dhamanis (Ten Great Vessels)"],
    SrotasType.RAKTAVAHA: ["Yakrit (Liver)", "Pleeha (Spleen)"],
    SrotasType.MAMSAVAHA: ["Snayu (Tendons/ligaments)", "Tvak (Dermis)"],
    SrotasType.MEDOVAHA: ["Vrikka (Kidneys)", "Vapavahana (Omentum / mesentery)"],
    SrotasType.ASTHIVAHA: ["Medas (Adipose tissue)", "Jaghana (Pelvic girdle)"],
    SrotasType.MAJJAVAHA: ["Asthi (Bones)", "Sandhi (Articulations / joints)"],
    SrotasType.SHUKRAVAHA: ["Vrishana (Testes / ovaries)", "Shepha / Stana (Genitalia / mammary)"],
    SrotasType.MUTRAVAHA: ["Basti (Urinary bladder)", "Vankshana (Ureters / inguinal canals)"],
    SrotasType.PURISHAVAHA: ["Pakvashaya (Colon)", "Sthulaguda (Rectum)"],
    SrotasType.SVEDAVAHA: ["Medas (Adipose tissue)", "Romakupa (Hair follicles / sweat pores)"],
    SrotasType.MANOVAHA: ["Hridaya (Center of consciousness)", "Dasha Dhamanis (Cerebral axes)"],
}

SROTOSHODHANA_REGISTRY: Dict[SrotasType, Dict[str, List[str] | str]] = {
    SrotasType.PRANAVAHA: {
        "karma": "Vamana (for Kaphaja Sanga) or Mridu Swedana with Shringyadi",
        "herbs": ["Pippali", "Vasa", "Kantakari", "Talisadi Churna"],
        "diet": ["Warm ginger water", "Light vegetable broth", "Strict avoidance of cold items"],
    },
    SrotasType.UDAKAVAHA: {
        "karma": "Langhana and Mridu Virechana",
        "herbs": ["Musta", "Usheera", "Parpataka", "Chandanadi Kwatha"],
        "diet": ["Boiled cooling water", "Light Mudga Yusha"],
    },
    SrotasType.ANNAVAHA: {
        "karma": "Langhana, Amapachana, Vamana (if acute Sama)",
        "herbs": ["Chitrakadi Vati", "Hingwashtaka Churna", "Panchakola Phanta"],
        "diet": ["Warm Mudga Yusha", "Laja Manda", "Avoid heavy oily foods"],
    },
    SrotasType.RASAVAHA: {
        "karma": "Langhana (Fasting / light diet) per Charaka Sutra 28",
        "herbs": ["Musta", "Nagaram (Dry ginger)", "Kiratatikta", "Sudarshana"],
        "diet": ["Light warm gruel", "Avoid dairy and sweets during acute Sanga"],
    },
    SrotasType.RAKTAVAHA: {
        "karma": "Virechana & Raktamokshana (Bloodletting / Jalaukavacharana)",
        "herbs": ["Manjistha", "Sariva", "Khadira", "Guduchi"],
        "diet": ["Bitter and astringent greens", "Pomegranate", "Avoid sour and fermented foods"],
    },
    SrotasType.MAMSAVAHA: {
        "karma": "Shodhana, Ksharakarma, and Lekhana therapy",
        "herbs": ["Kanchanara Guggulu", "Triphala Guggulu", "Shilajit"],
        "diet": ["Barley", "Green gram", "Avoid heavy curds and sedentary lifestyle"],
    },
    SrotasType.MEDOVAHA: {
        "karma": "Ruksha Udvartana & Lekhana Basti",
        "herbs": ["Shilajit", "Guggulu", "Varunadi Kwatha", "Triphala"],
        "diet": ["Yava (Barley)", "Honey with warm water", "Avoid oily sweets"],
    },
    SrotasType.ASTHIVAHA: {
        "karma": "Tikta Ksheera Basti per Charaka Sutra 28",
        "herbs": ["Lakshadi Guggulu", "Pravala Pishti", "Asthisamharaka", "Ashwagandha"],
        "diet": ["A2 Milk boiled with ginger", "Sesame seeds", "Finger millet (Ragi)"],
    },
    SrotasType.MAJJAVAHA: {
        "karma": "Madhura-Tikta Snehana & Shirovasti",
        "herbs": ["Brahmi", "Guduchi", "Shankhapushpi", "Jyotishmati"],
        "diet": ["Cow's ghee", "Walnuts", "Warm nourishing spiced milk"],
    },
    SrotasType.SHUKRAVAHA: {
        "karma": "Uttarabasti & Rasayana / Vajikarana therapy",
        "herbs": ["Kapikacchu", "Ashwagandha", "Gokshura", "Shatavari"],
        "diet": ["Milk, ghee, saffron, soaked almonds"],
    },
    SrotasType.MUTRAVAHA: {
        "karma": "Uttarabasti, Mridu Virechana, Kashaya Avagaha",
        "herbs": ["Gokshuradi Guggulu", "Varunadi Kwatha", "Punarnava", "Chandraprabha Vati"],
        "diet": ["Barley water", "Cucumber", "Avoid excessive sodium and pungent pickles"],
    },
    SrotasType.PURISHAVAHA: {
        "karma": "Anuvasana & Niruha Basti (Medicated Enema)",
        "herbs": ["Haritaki", "Triphala", "Gandharvahastadi Castor Oil", "Abhayarishta"],
        "diet": ["Fiber-rich warm cooked vegetables", "Warm water", "Ghee at night"],
    },
    SrotasType.SVEDAVAHA: {
        "karma": "Svedana or Langhana (depending on Atipravritti vs Sanga)",
        "herbs": ["Usheera", "Chandana", "Sariva", "Nimba"],
        "diet": ["Cooling herbal infusions", "Light clothing", "Avoid intense heat"],
    },
    SrotasType.MANOVAHA: {
        "karma": "Shirodhara, Nasya, Satvavajaya Chikitsa, Pranayama",
        "herbs": ["Brahmi Rasayana", "Saraswatarishta", "Shankhapushpi", "Jatamansi"],
        "diet": ["Pure Satvik fresh meals", "Ghee", "Warm milk before bed"],
    },
}


def evaluate_channel_pathology(obs: ChannelObservation) -> Tuple[float, DushtiType, bool, str]:
    """Calculate channel involvement score, dominant Dushti, and Khavaigunya vulnerability."""
    raw_score = obs.ati_pravritti + obs.sanga + obs.sira_granthi + obs.vimarga_gamana
    involvement_score = min(100.0, (raw_score / 12.0) * 100.0)

    # Determine dominant Dushti pattern
    dushti_scores = [
        (DushtiType.SANGA, obs.sanga),
        (DushtiType.ATI_PRAVRITTI, obs.ati_pravritti),
        (DushtiType.SIRA_GRANTHI, obs.sira_granthi),
        (DushtiType.VIMARGA_GAMANA, obs.vimarga_gamana),
    ]

    if raw_score == 0:
        dominant_dushti = DushtiType.PRAKRITA
    else:
        dominant_dushti = max(dushti_scores, key=lambda x: x[1])[0]

    has_khavaigunya = obs.pre_existing_defect or (involvement_score >= 30.0)

    # Textual manifestation
    if dominant_dushti == DushtiType.PRAKRITA:
        manifestation = "Channel is patent and physiologically balanced (Prakrita)."
    elif dominant_dushti == DushtiType.SANGA:
        manifestation = "Prominent luminal obstruction, stagnation, and retention (Sanga)."
    elif dominant_dushti == DushtiType.ATI_PRAVRITTI:
        manifestation = "Excessive outflow, hyper-secretion, and hyperactive transit (Ati-pravritti)."
    elif dominant_dushti == DushtiType.SIRA_GRANTHI:
        manifestation = "Dilation, nodular fibrotic constriction, and tortuous varicosity (Sira-granthi)."
    else:
        manifestation = "Extravasation, reverse peristalsis, and aberrant pathway translocation (Vimarga-gamana)."

    return (round(involvement_score, 2), dominant_dushti, has_khavaigunya, manifestation)


def evaluate_srotas_matrix(
    input_data: SrotasInput,
    evaluator_arn: str,
    hospital_id: str,
) -> SrotasOutput:
    """Execute complete 14-channel Srotas pathology analysis, Khavaigunya detection, and therapeutic protocol."""
    channel_details: List[ChannelDetail] = []
    khavaigunya_channels: List[str] = []
    directives: List[SrotoshodhanaDirective] = []

    total_involvement = 0.0

    for obs in input_data.channels:
        score, dushti, khavaigunya, manifestation = evaluate_channel_pathology(obs)
        total_involvement += score

        mula = MULA_STHANA_REGISTRY.get(obs.srotas, ["Unknown Mula"])

        channel_details.append(
            ChannelDetail(
                srotas=obs.srotas,
                mula_sthana=mula,
                involvement_score=score,
                dominant_dushti=dushti,
                has_khavaigunya=khavaigunya,
                clinical_manifestation=manifestation,
            )
        )

        if khavaigunya:
            khavaigunya_channels.append(obs.srotas.value)

        # Generate Srotoshodhana directive if channel has significant pathology or pre-existing defect
        if score > 0.0 or obs.pre_existing_defect:
            reg = SROTOSHODHANA_REGISTRY.get(
                obs.srotas,
                {"karma": "General Deepana-Pachana", "herbs": ["Trikatu"], "diet": ["Warm water"]},
            )
            directives.append(
                SrotoshodhanaDirective(
                    srotas=obs.srotas,
                    primary_dushti=dushti,
                    shodhana_karma=str(reg["karma"]),
                    herbal_clearing_agents=list(reg["herbs"]),
                    dietary_guidelines=list(reg["diet"]),
                )
            )

    overall_index = round(total_involvement / len(input_data.channels), 2)

    return SrotasOutput(
        assessment_id=f"sro-{uuid.uuid4().hex[:12]}",
        patient_id=input_data.patient_id,
        hospital_id=hospital_id,
        evaluator_arn=evaluator_arn,
        overall_srotas_index=overall_index,
        vulnerable_channels_count=len(khavaigunya_channels),
        channel_details=channel_details,
        khavaigunya_channels=khavaigunya_channels,
        srotoshodhana_directives=directives,
        timestamp=int(time.time()),
    )
