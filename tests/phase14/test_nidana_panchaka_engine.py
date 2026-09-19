"""
Unit Tests for Nidana Panchaka Diagnostic Knowledge Graph & Differential Diagnosis Engine.
"""

import pytest
from core.nidana_panchaka import (
    DISEASE_ARCHETYPE_REGISTRY,
    evaluate_nidana_panchaka,
)
from models.nidana_panchaka import (
    NidanaPanchakaEvaluationInput,
    UpashayaTrialInput,
    UpashayaCategory,
    UpashayaOutcome,
    AgniState,
    AmaStatus,
    Rogamarga,
)


def test_archetype_registry_completeness():
    """Verify that all 10 core classical disease archetypes are present and strictly typed."""
    expected_codes = {
        "AMAVATA", "SANDHIGATA_VATA", "VATARAKTA",
        "JWARA_VATAJA", "JWARA_PITTAJA", "JWARA_KAPHAJA",
        "TAMAKA_SHWASA", "PRAMEHA_KAPHAJA", "GRAHANI_DOSHA", "AMLAPITTA"
    }
    assert set(DISEASE_ARCHETYPE_REGISTRY.keys()) == expected_codes

    for code, archetype in DISEASE_ARCHETYPE_REGISTRY.items():
        assert archetype.code == code
        assert len(archetype.sanskrit_name) > 0
        assert len(archetype.english_name) > 0
        assert len(archetype.nidanas) >= 3
        assert len(archetype.purvaroopas) >= 2
        assert len(archetype.roopas) >= 4
        assert len(archetype.pratyatma_lingas) >= 1
        assert len(archetype.beneficial_upashayas) >= 2
        assert len(archetype.aggravating_anupashayas) >= 2

        # Samprapti Ghatakas validation
        sg = archetype.samprapti_ghatakas
        assert sg.primary_dosha in ["Vata", "Pitta", "Kapha"]
        assert len(sg.dushya) >= 1
        assert isinstance(sg.agni, AgniState)
        assert isinstance(sg.ama, AmaStatus)
        assert len(sg.srotas) >= 1
        assert len(sg.srotodushti) >= 1
        assert len(sg.udbhava_sthana) > 0
        assert len(sg.vyakti_sthana) > 0
        assert isinstance(sg.rogamarga, Rogamarga)


def test_differential_diagnosis_amavata_primary_over_sandhigata_and_vatarakta():
    """
    Presentation of classic Amavata (bilateral joint swelling, morning stiffness,
    scorpion-bite pain, body aches, anorexia, and sinking stool) must diagnose AMAVATA
    as primary, with Sandhigata Vata and Vatarakta in differentials having explicit exclusion rationale.
    """
    patient_input = NidanaPanchakaEvaluationInput(
        patient_id="pat-test-amavata-001",
        presented_nidana=[
            "Viruddha Ahara (Incompatible foods)",
            "Mandagni (Impaired digestion)",
            "Divaswapna (Daytime sleep)"
        ],
        presented_purvaroopa=[
            "Alasya (Lethargy)",
            "Gaurava (Generalized heaviness)",
            "Aruchi (Loss of appetite)"
        ],
        presented_roopa=[
            "Sandhi Shula (Severe joint pain)",
            "Sandhi Shotha (Bilateral joint swelling)",
            "Stambha (Severe morning stiffness)",
            "Angamarda (Generalized body aches)",
            "Vrischika Damshavat Shula (Excruciating joint pain resembling scorpion sting)",
            "Agnimandya"
        ],
        upashaya_trials=[
            UpashayaTrialInput(
                description="Langhana (Fasting) and Ruksha Sweda (Dry sand heat)",
                category=UpashayaCategory.VYADHI_VIPARITA,
                outcome=UpashayaOutcome.UPASHAYA_RELIEVED,
                modality="Aushadha/Ahara"
            ),
            UpashayaTrialInput(
                description="Snehadravya (Heavy oil massage)",
                category=UpashayaCategory.HETU_VIPARITARTHAKARI,
                outcome=UpashayaOutcome.ANUPASHAYA_AGGRAVATED,
                modality="Vihara"
            )
        ],
        observed_doshas=["Vata", "Kapha"]
    )

    output = evaluate_nidana_panchaka(patient_input)

    assert output.primary_diagnosis.disease_code == "AMAVATA"
    assert output.primary_diagnosis.match_score >= 70.0
    assert output.primary_diagnosis.confidence_score >= 0.70
    assert len(output.pratyatma_linga_matched) > 0
    assert output.samprapti_ghatakas.ama == AmaStatus.SAMA
    assert output.samprapti_ghatakas.primary_dosha == "Vata"

    # Check that differentials contain SANDHIGATA_VATA or VATARAKTA with exclusion rationales
    diff_codes = [d.disease_code for d in output.differential_diagnoses]
    assert "SANDHIGATA_VATA" in diff_codes or "VATARAKTA" in diff_codes

    for diff in output.differential_diagnoses:
        if diff.disease_code == "SANDHIGATA_VATA":
            assert diff.exclusion_rationale is not None
            assert "Ama" in diff.exclusion_rationale or "stiffness" in diff.exclusion_rationale


def test_differential_diagnosis_sandhigata_vata_pure_degenerative():
    """
    Presentation of classic Sandhigata Vata (crepitus, pain on movement,
    air-bag sensation, without systemic fever or Ama) must select SANDHIGATA_VATA.
    """
    patient_input = NidanaPanchakaEvaluationInput(
        patient_id="pat-test-sandhigata-002",
        presented_nidana=[
            "Ruksha-Sheeta Ahara (Dry cold food)",
            "Dhatukshaya (Tissue wasting)",
            "Vridhavastha (Senile age)"
        ],
        presented_purvaroopa=[
            "Subtle joint stiffness on cold exposure",
            "Dryness of skin"
        ],
        presented_roopa=[
            "Sandhi Shula during motion (Mechanical joint pain)",
            "Vata Purna Driti Sparsha (Bag of air sensation)",
            "Sandhi Sphutana (Joint crackling sound on movement)",
            "Prasarana Akunchana Pravritti Vedana (Pain on flexion and extension)"
        ],
        upashaya_trials=[
            UpashayaTrialInput(
                description="Abhyanga with warm Mahanarayana Taila and Snigdha Sweda",
                category=UpashayaCategory.HETU_VIPARITA,
                outcome=UpashayaOutcome.UPASHAYA_RELIEVED,
                modality="Aushadha"
            )
        ],
        observed_doshas=["Vata"]
    )

    output = evaluate_nidana_panchaka(patient_input)

    assert output.primary_diagnosis.disease_code == "SANDHIGATA_VATA"
    assert output.primary_diagnosis.match_score >= 65.0
    assert output.samprapti_ghatakas.ama == AmaStatus.NIRAMA
    assert output.samprapti_ghatakas.primary_dosha == "Vata"


def test_differential_diagnosis_vatarakta_metabolic_gout():
    """
    Presentation of acute Podagra/Vatarakta (onset in great toe, intense burning, erythema,
    hyperesthesia, nocturnal spikes) must select VATARAKTA.
    """
    patient_input = NidanaPanchakaEvaluationInput(
        patient_id="pat-test-vatarakta-003",
        presented_nidana=[
            "Lavana, Amla, Katu, Ushna Ahara",
            "Madya (Alcohol / fermented beverages)",
            "Dadhi (Curds)"
        ],
        presented_purvaroopa=[
            "Kara-Pada Suptata",
            "Toda in Padangustha (Pricking in great toe)"
        ],
        presented_roopa=[
            "Padangustha Shula (Acute throbbing pain starting in the big toe)",
            "Raga (Intense erythema / purplish-red discoloration)",
            "Daha (Severe burning agony)",
            "Shyava-Tamra Varna",
            "Padangustha Mula Shotha with Raga (Acute erythematous inflammation of the 1st MTP joint)"
        ],
        upashaya_trials=[
            UpashayaTrialInput(
                description="Sheeta Pradeha (Cool herbal paste) and Guduchi decoction",
                category=UpashayaCategory.HETU_VIPARITA,
                outcome=UpashayaOutcome.UPASHAYA_RELIEVED,
                modality="Aushadha"
            ),
            UpashayaTrialInput(
                description="Ushna Lepa (Warm oil paste)",
                category=UpashayaCategory.HETU_VIPARITARTHAKARI,
                outcome=UpashayaOutcome.ANUPASHAYA_AGGRAVATED,
                modality="Aushadha"
            )
        ],
        observed_doshas=["Vata", "Pitta"]
    )

    output = evaluate_nidana_panchaka(patient_input)

    assert output.primary_diagnosis.disease_code == "VATARAKTA"
    assert output.primary_diagnosis.match_score >= 70.0
    assert output.primary_diagnosis.confidence_score >= 0.70
    assert "Padangustha" in " ".join(output.primary_diagnosis.matched_roopa)


def test_jwara_doshic_subtype_discrimination():
    """
    Pittaja Jwara presentation (continuous high fever, burning heat, bitter mouth,
    photophobia, yellow urine) must cleanly select JWARA_PITTAJA over Vataja or Kaphaja subtypes.
    """
    patient_input = NidanaPanchakaEvaluationInput(
        patient_id="pat-test-jwara-pitta-004",
        presented_nidana=[
            "Katu-Amla-Lavana Ahara",
            "Atapa (Direct scorching sun)",
            "Krodha (Intense anger)"
        ],
        presented_purvaroopa=[
            "Nayana Dvesha (Marked photophobia)",
            "Tikta Asyata (Bitter taste in mouth)",
            "Santapa (Internal burning sensation)"
        ],
        presented_roopa=[
            "Teekshna Jwara (Continuous high-grade fever)",
            "Daha (Intense internal and external burning heat)",
            "Trishna (Unquenchable intense thirst)",
            "Sweda Pravritti (Profuse sweating)",
            "Peeta Mutra-Netra-Tvak (Yellowish sclera and urine)",
            "Teekshna Jwara with Generalized Burning (Santapa)"
        ],
        upashaya_trials=[
            UpashayaTrialInput(
                description="Sheeta Upachara (Cool sponging) and Chandana decoction",
                category=UpashayaCategory.HETU_VIPARITA,
                outcome=UpashayaOutcome.UPASHAYA_RELIEVED,
                modality="Vihara/Aushadha"
            )
        ],
        observed_doshas=["Pitta"]
    )

    output = evaluate_nidana_panchaka(patient_input)

    assert output.primary_diagnosis.disease_code == "JWARA_PITTAJA"
    assert output.primary_diagnosis.match_score >= 75.0

    # Ensure other Jwara variants are scored lower
    for diff in output.differential_diagnoses:
        if diff.disease_code in ["JWARA_VATAJA", "JWARA_KAPHAJA"]:
            assert diff.match_score < output.primary_diagnosis.match_score


def test_upashaya_anupashaya_confirmation_effect():
    """
    Verifies that confirming Upashaya and Anupashaya trials boost match score and confidence
    compared to presentation without diagnostic trial verification.
    """
    base_roopa = [
        "Teevra Shwasa Krichrata (Acute paroxysmal respiratory distress)",
        "Ghurghuraka (Audible wheezing)",
        "Asino Labhate Saukhyam (Relief exclusively on sitting upright / orthopnea)",
        "Kasa with chest tightness"
    ]

    input_without_trials = NidanaPanchakaEvaluationInput(
        patient_id="pat-asthma-001",
        presented_nidana=["Raja-Dhooma Sevana", "Sheeta Vata"],
        presented_purvaroopa=["Parshva Shula", "Anaha"],
        presented_roopa=base_roopa,
        upashaya_trials=[]
    )

    input_with_confirming_trials = NidanaPanchakaEvaluationInput(
        patient_id="pat-asthma-001",
        presented_nidana=["Raja-Dhooma Sevana", "Sheeta Vata"],
        presented_purvaroopa=["Parshva Shula", "Anaha"],
        presented_roopa=base_roopa,
        upashaya_trials=[
            UpashayaTrialInput(
                description="Asino Avastha (Upright posture) and warm fluid drinking",
                category=UpashayaCategory.VYADHI_VIPARITA,
                outcome=UpashayaOutcome.UPASHAYA_RELIEVED,
                modality="Vihara"
            ),
            UpashayaTrialInput(
                description="Shayana (Lying flat supine) causes paroxysm",
                category=UpashayaCategory.HETU_VIPARITARTHAKARI,
                outcome=UpashayaOutcome.ANUPASHAYA_AGGRAVATED,
                modality="Vihara"
            )
        ]
    )

    out_no_trials = evaluate_nidana_panchaka(input_without_trials)
    out_with_trials = evaluate_nidana_panchaka(input_with_confirming_trials)

    assert out_no_trials.primary_diagnosis.disease_code == "TAMAKA_SHWASA"
    assert out_with_trials.primary_diagnosis.disease_code == "TAMAKA_SHWASA"

    # Match score with confirmed trials should be higher
    assert out_with_trials.primary_diagnosis.match_score >= out_no_trials.primary_diagnosis.match_score
    assert out_with_trials.primary_diagnosis.confidence_score >= out_no_trials.primary_diagnosis.confidence_score
