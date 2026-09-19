"""Roga Rogi Bala Ganan Yantra (Bi-Directional Balance Engine & Therapeutic Intensity Governor).

Classical References:
- Charaka Samhita, Vimanasthana Ch. 8 (Rogabhishagjitiya Adhyaya - Bala Pariksha)
- Charaka Samhita, Sutrasthana Ch. 15 & 16 (Upakalpaniya & Chikitsaprabhritiya)
- Ashtanga Hridaya, Sutrasthana Ch. 13 (Upakramaniya Adhyaya)
"""
import uuid
import time
from typing import Dict, List, Tuple

from models.roga_rogi_bala import (
    TherapeuticCategory,
    ShodhanaEligibilityStatus,
    RogiBalaInput,
    RogaBalaInput,
    RogaRogiBalaInput,
    TherapeuticGovernorDirective,
    RogaRogiBalaOutput,
)


def calculate_rogi_bala(data: RogiBalaInput) -> float:
    """Calculate composite Host Vitality Score (0-100) combining Trividha Bala, Sarata, Sattva, and Agni."""
    # 1. Sahaja Bala (Constitutional): 15%
    # 2. Kalaja Bala (Chronobiological/Age): 10%
    # 3. Yuktikrita Bala (Acquired/Lifestyle): 15%
    # 4. Dhatu Sarata OSI: 25%
    # 5. Sattva Bala (Mental resilience): 20%
    # 6. Agni Bala (Metabolic fire): 15%
    score = (
        15.0 * data.sahaja_bala +
        10.0 * data.kalaja_bala +
        15.0 * data.yuktikrita_bala +
        25.0 * (data.dhatu_sarata_osi / 100.0) +
        20.0 * data.sattva_score +
        15.0 * data.agni_strength
    )
    return round(min(100.0, max(0.0, score)), 2)


def calculate_roga_bala(data: RogaBalaInput) -> float:
    """Calculate composite Disease Virulence Score (0-100) combining VSI, Srotas, PPI, AGI, and Chronicity."""
    # 1. Vikriti Severity Index (VSI): 25%
    # 2. Srotas Involvement: 20%
    # 3. Vulnerable Channels Count (max 14): 15%
    # 4. Pathological Progression Index (PPI 1-6): 20% -> (PPI-1)/5
    # 5. Ama Grading Index (AGI): 10%
    # 6. Chronicity (scaled to 24 months): 10%
    norm_channels = min(1.0, data.vulnerable_channels_count / 14.0)
    norm_ppi = min(1.0, max(0.0, (data.kriya_kala_ppi - 1.0) / 5.0))
    norm_chronicity = min(1.0, data.chronicity_months / 24.0)

    score = (
        25.0 * (data.vikriti_vsi / 100.0) +
        20.0 * (data.srotas_involvement_osi / 100.0) +
        15.0 * norm_channels +
        20.0 * norm_ppi +
        10.0 * (data.ama_agi_score / 100.0) +
        10.0 * norm_chronicity
    )
    return round(min(100.0, max(0.0, score)), 2)


def evaluate_therapeutic_governor(
    rogi_bala: float,
    roga_bala: float,
) -> Tuple[float, float, TherapeuticCategory, float, ShodhanaEligibilityStatus, List[TherapeuticGovernorDirective]]:
    """Evaluate bi-directional ratio, assign therapeutic category, dosage scalar, and safety constraints."""
    ratio = round(rogi_bala / max(roga_bala, 1.0), 3)
    diff = round(rogi_bala - roga_bala, 2)

    directives: List[TherapeuticGovernorDirective] = []

    # Case 1: Low Host, High Disease -> STRICT CONTRAINDICATION
    if rogi_bala < 45.0 and roga_bala >= 50.0:
        category = TherapeuticCategory.CONTRAINDICATED_SHODHANA_EMERGENCY_BRIMHANA
        eligibility = ShodhanaEligibilityStatus.STRICTLY_CONTRAINDICATED
        dosage_scalar = 0.50
        rationale = (
            "Host vitality (B_rogi < 45) is critically insufficient to withstand the physical demands of Shodhana "
            "against strong disease virulence (B_roga >= 50). Administering bio-purification will cause severe Ojas "
            "depletion or vital collapse (Pranahara). Strictly contraindicated; proceed with mild Brimhana."
        )
        directives.append(
            TherapeuticGovernorDirective(
                protocol_name="EMERGENCY_HOST_SUPPORT_PROTOCOL",
                intensity_level="MRIDU (Low Intensity)",
                dosage_multiplier=dosage_scalar,
                permissible_panchakarma_procedures=["Mridu Abhyanga with Ksheerabala Taila", "Snigdha Sweda"],
                forbidden_procedures=["Vamana", "Virechana", "Tikshna Niruha Basti", "Raktamokshana", "Tikshna Nasya"],
                clinical_rationale=rationale,
            )
        )

    # Case 2: High Host, High Disease -> FULL TIKSHNA SHODHANA
    elif rogi_bala >= 65.0 and roga_bala >= 55.0:
        category = TherapeuticCategory.TIKSHNA_SHODHANA
        eligibility = ShodhanaEligibilityStatus.FULL_ELIGIBILITY
        dosage_scalar = 1.25
        rationale = (
            "Patient possesses Pravara Bala (robust vitality) and disease exhibits high virulence. The patient has optimal "
            "resilience to tolerate radical bio-cleansing (Tikshna Vamana or Virechana) followed by restorative Samsarjana."
        )
        directives.append(
            TherapeuticGovernorDirective(
                protocol_name="RADICAL_BIOCLEANSING_PROTOCOL",
                intensity_level="TIKSHNA (High Intensity)",
                dosage_multiplier=dosage_scalar,
                permissible_panchakarma_procedures=["Classical Vamana Karma", "Virechana Karma", "Kala / Karma Basti", "Tikshna Snehapana"],
                forbidden_procedures=["Akalika Brihmana (excess premature nourishing before purification)"],
                clinical_rationale=rationale,
            )
        )

    # Case 3: High Host, Low Disease -> SHAMANA SUFFICIENT
    elif rogi_bala >= 60.0 and roga_bala < 40.0:
        category = TherapeuticCategory.MADHYAMA_SHAMANA
        eligibility = ShodhanaEligibilityStatus.NOT_INDICATED
        dosage_scalar = 0.85
        rationale = (
            "Host vitality is robust while disease pathology is mild or localized. Radical Shodhana is unnecessary; "
            "targeted Shamana pacification, Langhana, and lifestyle correction will resolve pathology efficiently."
        )
        directives.append(
            TherapeuticGovernorDirective(
                protocol_name="TARGETED_PACIFICATION_PROTOCOL",
                intensity_level="MADHYAMA (Moderate Pacification)",
                dosage_multiplier=dosage_scalar,
                permissible_panchakarma_procedures=["Mridu Matra Basti", "Pratimarsa Nasya", "Sarvanga Abhyanga"],
                forbidden_procedures=["Aggressive radical emesis / purgation (unwarranted)"],
                clinical_rationale=rationale,
            )
        )

    # Case 4: Low Host, Low Disease -> GENTLE PACIFICATION & NOURISHING
    elif rogi_bala < 45.0 and roga_bala < 40.0:
        category = TherapeuticCategory.MRIDU_SHAMANA_BRIMHANA
        eligibility = ShodhanaEligibilityStatus.NOT_INDICATED
        dosage_scalar = 0.60
        rationale = (
            "Both host vitality and disease virulence are low. Radical cleansing would deplete fragile vitality. "
            "Gentle herbal pacification combined with nourishing dietary therapy (Santarpana) is indicated."
        )
        directives.append(
            TherapeuticGovernorDirective(
                protocol_name="NOURISHING_PACIFICATION_PROTOCOL",
                intensity_level="MRIDU_BRIMHANA",
                dosage_multiplier=dosage_scalar,
                permissible_panchakarma_procedures=["Matra Basti with Sahacharadi Taila", "Ksheera Dhara", "Snigdha Abhyanga"],
                forbidden_procedures=["Vamana", "Virechana", "Rukshana", "Intense fasting (Langhana)"],
                clinical_rationale=rationale,
            )
        )

    # Case 5: Moderate Host, Moderate Disease
    else:
        category = TherapeuticCategory.MADHYAMA_SHODHANA_OR_SHAMANA
        eligibility = ShodhanaEligibilityStatus.CONDITIONAL_ELIGIBILITY
        dosage_scalar = 1.00
        rationale = (
            "Balanced host vitality and disease virulence. Patient is conditionally eligible for moderate bio-purification "
            "(Mridu Virechana or Yoga Basti) with careful monitoring of Agni and vital signs."
        )
        directives.append(
            TherapeuticGovernorDirective(
                protocol_name="MODERATE_PURIFICATION_PACIFICATION_PROTOCOL",
                intensity_level="MADHYAMA",
                dosage_multiplier=dosage_scalar,
                permissible_panchakarma_procedures=["Mridu Virechana with Eranda / Triphala", "Yoga Basti", "Bashpa Sweda"],
                forbidden_procedures=["Tikshna radical emesis in outpatient setting"],
                clinical_rationale=rationale,
            )
        )

    return (ratio, diff, category, dosage_scalar, eligibility, directives)


def evaluate_roga_rogi_bala(
    input_data: RogaRogiBalaInput,
    evaluator_arn: str,
    hospital_id: str,
) -> RogaRogiBalaOutput:
    """Execute complete bi-directional host vs disease equilibrium and therapeutic governance."""
    rogi_score = calculate_rogi_bala(input_data.rogi_bala)
    roga_score = calculate_roga_bala(input_data.roga_bala)

    ratio, diff, category, scalar, eligibility, directives = evaluate_therapeutic_governor(
        rogi_bala=rogi_score,
        roga_bala=roga_score,
    )

    return RogaRogiBalaOutput(
        assessment_id=f"bal-{uuid.uuid4().hex[:12]}",
        patient_id=input_data.patient_id,
        hospital_id=hospital_id,
        evaluator_arn=evaluator_arn,
        rogi_bala_score=rogi_score,
        roga_bala_score=roga_score,
        bala_ratio=ratio,
        bala_differential=diff,
        therapeutic_category=category,
        dosage_scalar=scalar,
        shodhana_eligibility_status=eligibility,
        governor_directives=directives,
        timestamp=int(time.time()),
    )
