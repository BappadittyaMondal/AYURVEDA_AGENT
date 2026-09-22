"""
tests/test_prescription_parser.py - Unit tests for Clinical Prescription Shorthand,
Dosage Form (Kalpana) Normalization, and Regional Medicine Tree Vernacular Resolution.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from models.bhaishajya_kalpana import KalpanaForm
from models.prescription_parser import (
    ClinicalFrequency,
    AushadhaSevanaKala,
)
from core.prescription_parser import (
    resolve_vernacular_herb_or_tree,
    normalize_dosage_form,
    parse_prescription_line,
    parse_prescription_text,
)


def test_clinical_frequency_and_timing_shorthand():
    """Verify standard hospital Latin abbreviations and classical Aushadha Sevana Kala decoding."""
    # 1. Twice daily after meals
    item1 = parse_prescription_line("Tab. Yograj Guggulu 2 tabs BD pc with warm water x 15 days")
    assert item1.dosage_form == KalpanaForm.VATI
    assert item1.dosage_form_raw == "tab"
    assert item1.dose_amount == "2 tabs"
    assert item1.frequency == ClinicalFrequency.BD
    assert item1.administration_timing == AushadhaSevanaKala.ADHOBHAKTA
    assert item1.anupana_carrier == "Warm water (Ushna Jala)"
    assert item1.duration == "15 days"

    # 2. Thrice daily before meals
    item2 = parse_prescription_line("Kw. Dashamoola 20ml TDS ac with equal water for 10 days")
    assert item2.dosage_form == KalpanaForm.KWATHA
    assert item2.dose_amount == "20ml"
    assert item2.frequency == ClinicalFrequency.TDS
    assert item2.administration_timing == AushadhaSevanaKala.PRAGBHAKTA
    assert item2.anupana_carrier == "Equal quantity warm water"
    assert item2.duration == "10 days"

    # 3. Nightly at bedtime
    item3 = parse_prescription_line("Churna Haritaki 3g HS with warm water")
    assert item3.dosage_form == KalpanaForm.CHURNA
    assert item3.frequency == ClinicalFrequency.HS
    assert item3.administration_timing == AushadhaSevanaKala.NISHI


def test_dosage_form_kalpana_normalization():
    """Verify diverse clinical shorthand mappings to canonical Bhaishajya Kalpanas."""
    assert normalize_dosage_form("Kw. Maharasnadi")[0] == KalpanaForm.KWATHA
    assert normalize_dosage_form("Kashayam Amruthotharam")[0] == KalpanaForm.KWATHA
    assert normalize_dosage_form("Chur. Triphala")[0] == KalpanaForm.CHURNA
    assert normalize_dosage_form("Tab. Chandraprabha")[0] == KalpanaForm.VATI
    assert normalize_dosage_form("Gutika Lavangadi")[0] == KalpanaForm.VATI
    assert normalize_dosage_form("Av. Chyavanprash")[0] == KalpanaForm.AVALEHA
    assert normalize_dosage_form("Ghr. Kalyanaka")[0] == KalpanaForm.GHRITA
    assert normalize_dosage_form("Tail. Mahanarayana")[0] == KalpanaForm.TAILA
    assert normalize_dosage_form("Ar. Dashamoolarishta")[0] == KalpanaForm.ASAVA_ARISHTA
    assert normalize_dosage_form("Syr. Liv.52")[0] == KalpanaForm.ASAVA_ARISHTA


def test_vernacular_tree_and_plant_resolution():
    """Verify local Indian vernacular names resolve to canonical Sanskrit and Botanical names."""
    # 1. Arjuna tree: "Kahu" (Hindi/Punjabi), "Marudhamaram" (Tamil)
    match_kahu = resolve_vernacular_herb_or_tree("Kahu")
    assert match_kahu is not None
    assert match_kahu.canonical_sanskrit == "Arjuna"
    assert match_kahu.botanical_binomial.startswith("Terminalia arjuna")

    match_marudhu = resolve_vernacular_herb_or_tree("Marudhamaram")
    assert match_marudhu is not None
    assert match_marudhu.canonical_sanskrit == "Arjuna"

    # 2. Guduchi: "Giloy" (Hindi), "Seenthil Kodi" (Tamil), "Tippa Teega" (Telugu)
    match_giloy = resolve_vernacular_herb_or_tree("Giloy")
    assert match_giloy is not None
    assert match_giloy.canonical_sanskrit == "Guduchi"
    assert match_giloy.botanical_binomial.startswith("Tinospora cordifolia")

    match_seenthil = resolve_vernacular_herb_or_tree("Seenthil Kodi")
    assert match_seenthil is not None
    assert match_seenthil.canonical_sanskrit == "Guduchi"

    # 3. Neem: "Veppamaram" (Tamil), "Vepa" (Telugu), "Bevu" (Kannada)
    match_veppa = resolve_vernacular_herb_or_tree("Veppamaram")
    assert match_veppa is not None
    assert match_veppa.canonical_sanskrit == "Nimba"

    # 4. Licorice: "Mulethi" (Hindi), "Athimadhuram" (Tamil/Malayalam)
    match_mulethi = resolve_vernacular_herb_or_tree("Mulethi")
    assert match_mulethi is not None
    assert match_mulethi.canonical_sanskrit == "Yashtimadhu"

    # 5. Mandukaparni: "Thankuni" (Bengali), "Gotu Kola" (Sinhala/Common), "Vallarai" (Tamil)
    match_thankuni = resolve_vernacular_herb_or_tree("Thankuni")
    assert match_thankuni is not None
    assert match_thankuni.canonical_sanskrit == "Mandukaparni"


def test_schedule_e1_poison_detection_from_vernacular_names():
    """Verify statutory poison registry triggers even when written in colloquial / local names."""
    # 1. Bhallataka written as "Bhilawa" (Hindi) or "Serankottai" (Tamil)
    bhilawa_item = parse_prescription_line("Bhilawa churna 500mg OD pc")
    assert bhilawa_item.schedule_e1_alert is True
    assert bhilawa_item.matched_herb is not None
    assert bhilawa_item.matched_herb.canonical_sanskrit == "Bhallataka"
    assert bhilawa_item.matched_herb.is_schedule_e1_poison is True

    # 2. Vatsanabha written as "Meetha Zahar" (Hindi) or "Bachnag"
    bachnag_item = parse_prescription_line("Bachnag vati 1 tab BD")
    assert bachnag_item.schedule_e1_alert is True
    assert bachnag_item.matched_herb.canonical_sanskrit == "Vatsanabha"

    # 3. Kupilu written as "Kuchla" (Hindi) or "Etti" (Tamil)
    kuchla_item = parse_prescription_line("Kuchla capsule 1 cap OD pc")
    assert kuchla_item.schedule_e1_alert is True
    assert kuchla_item.matched_herb.canonical_sanskrit == "Kupilu"


def test_full_prescription_text_parser():
    """Verify parsing of complete unstructured multi-item prescription dossier."""
    prescription_doc = """
    RX - CLINICAL PRESCRIPTION
    Patient Name: Anand Kumar (45/M)
    Date: 2026-09-22

    1. Tab. Yograj Guggulu 2 tabs BD pc with warm water x 15 days
    2. Kw. Dashamoola 20ml TDS ac with equal water for 14 days
    3. Giloy satva 500mg BD with honey x 21 days
    4. Bhilawa churna 250mg OD pc with milk
    """

    res = parse_prescription_text(prescription_doc)
    assert res.total_lines_processed == 4
    assert len(res.items_extracted) == 4
    assert res.governance_status == "DRAFT_PARSED_PRESCRIPTION"
    assert res.requires_rmp_verification is True

    # Check that Schedule E-1 poison was detected from vernacular name "Bhilawa"
    assert len(res.schedule_e1_items_detected) >= 1
    assert any("Bhallataka" in alert for alert in res.schedule_e1_items_detected)

    # Check individual item attributes
    item_guggul = res.items_extracted[0]
    assert item_guggul.dosage_form == KalpanaForm.VATI
    assert item_guggul.frequency == ClinicalFrequency.BD
    assert item_guggul.anupana_carrier == "Warm water (Ushna Jala)"

    item_kwatha = res.items_extracted[1]
    assert item_kwatha.dosage_form == KalpanaForm.KWATHA
    assert item_kwatha.frequency == ClinicalFrequency.TDS
    assert item_kwatha.administration_timing == AushadhaSevanaKala.PRAGBHAKTA


def test_prescription_parser_api_endpoints():
    """Verify FastAPI endpoints for parsing, vernacular lookup, and image registration."""
    client = TestClient(app)

    # 1. Parse text endpoint
    parse_resp = client.post(
        "/api/v1/prescription-parser/parse-text",
        json={"raw_prescription_text": "Tab. Yograj Guggulu 2 tab BD pc\nKw. Dashamoola 20ml TDS ac"}
    )
    assert parse_resp.status_code == 200
    data = parse_resp.json()
    assert data["total_lines_processed"] == 2
    assert len(data["items_extracted"]) == 2
    assert data["governance_status"] == "DRAFT_PARSED_PRESCRIPTION"

    # 2. Resolve herb endpoint
    herb_resp = client.get("/api/v1/prescription-parser/resolve-herb?query=Marudhamaram")
    assert herb_resp.status_code == 200
    herb_data = herb_resp.json()
    assert herb_data["canonical_sanskrit"] == "Arjuna"
    assert herb_data["matched_vernacular_language"] == "Tamil"

    # 3. Reference dosage forms
    df_resp = client.get("/api/v1/prescription-parser/reference/dosage-forms")
    assert df_resp.status_code == 200
    assert len(df_resp.json()) >= 10

    # 4. Reference frequencies
    freq_resp = client.get("/api/v1/prescription-parser/reference/frequencies")
    assert freq_resp.status_code == 200
    assert len(freq_resp.json()) >= 8

    # 5. Upload handwritten prescription image buffer
    import base64
    fake_image_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"
    b64_str = base64.b64encode(fake_image_bytes).decode("utf-8")
    upload_resp = client.post(
        "/api/v1/prescription-parser/upload-handwritten-image",
        json={
            "image_base64": b64_str,
            "filename": "prescription_rx_001.jpg",
            "prescriber_arn": "ARN-NCISM-2015-8832"
        }
    )
    assert upload_resp.status_code == 200
    up_data = upload_resp.json()
    assert up_data["status"] == "IMAGE_RECEIVED_FOR_MULTIMODAL_OCR"
    assert up_data["regulatory_governance"]["prescriber_arn_attached"] == "ARN-NCISM-2015-8832"

    # 6. Visual cards list endpoint
    vc_list_resp = client.get("/api/v1/prescription-parser/visual-cards")
    assert vc_list_resp.status_code == 200
    assert len(vc_list_resp.json()) >= 6

    # 7. Visual card by vernacular name endpoint ("Amla" -> Amalaki)
    amla_resp = client.get("/api/v1/prescription-parser/visual-card/Amla")
    assert amla_resp.status_code == 200
    amla_card = amla_resp.json()
    assert amla_card["canonical_sanskrit"] == "Amalaki"
    assert amla_card["primary_part_used"] == "FRUIT"
    assert "feather" in amla_card["leaf_morphology"].lower()
    assert amla_card["visual_reference_asset_id"] == "amalaki_medicinal_fruit"


    # 8. Visual card by vernacular name ("Giloy" -> Guduchi)
    giloy_resp = client.get("/api/v1/prescription-parser/visual-card/Giloy")
    assert giloy_resp.status_code == 200
    giloy_card = giloy_resp.json()
    assert giloy_card["canonical_sanskrit"] == "Guduchi"
    assert "heart-shaped" in giloy_card["leaf_morphology"].lower()
    assert "toxic" in giloy_card["toxic_lookalike_warning"].lower()



def test_botanical_visual_cards_resolution():
    """Verify botanical visual cards resolve correctly for leaves, fruits, bark, and lookalike warnings."""
    from core.prescription_parser import get_botanical_visual_card, list_all_botanical_visual_cards
    from models.prescription_parser import PlantPartType

    # 1. Total cards registered
    cards = list_all_botanical_visual_cards()
    assert len(cards) >= 6

    # 2. Amalaki - Fruit and leaf
    card_amla = get_botanical_visual_card("Amalaki")
    assert card_amla is not None
    assert card_amla.primary_part_used == PlantPartType.FRUIT
    assert "6 faint" in card_amla.fruit_morphology or "6 longitudinal" in card_amla.fruit_morphology
    assert "Hindi" in card_amla.patient_guidance_vernacular

    # 3. Guduchi - Stem and heart-shaped leaf via Hindi vernacular "Giloy"
    card_giloy = get_botanical_visual_card("Giloy")
    assert card_giloy is not None
    assert card_giloy.canonical_sanskrit == "Guduchi"
    assert card_giloy.primary_part_used == PlantPartType.STEM
    assert "cordate" in card_giloy.leaf_morphology.lower()
    assert "lenticels" in card_giloy.bark_or_stem_morphology.lower()
    assert card_giloy.toxic_lookalike_warning is not None
    assert "CRITICAL" in card_giloy.toxic_lookalike_warning

    # 4. Arjuna - Bark and 5-winged fruit via Tamil vernacular "Marudhamaram"
    card_arjuna = get_botanical_visual_card("Marudhamaram")
    assert card_arjuna is not None
    assert card_arjuna.canonical_sanskrit == "Arjuna"
    assert card_arjuna.primary_part_used == PlantPartType.BARK
    assert "5-winged" in card_arjuna.visual_description or "5 hard" in card_arjuna.fruit_morphology

    # 5. Nimba - Sickle leaflets and toxic chinaberry lookalike warning via "Neem"
    card_neem = get_botanical_visual_card("Neem")
    assert card_neem is not None
    assert card_neem.canonical_sanskrit == "Nimba"
    assert card_neem.primary_part_used == PlantPartType.LEAF
    assert "Melia azedarach" in card_neem.toxic_lookalike_warning

    # 6. Bilva - Trifoliate leaves (Shiva Trishula) and hard-shelled bael fruit
    card_bilva = get_botanical_visual_card("Bilva")
    assert card_bilva is not None
    assert card_bilva.primary_part_used == PlantPartType.FRUIT
    assert "trifoliate" in card_bilva.leaf_morphology.lower()

    # 7. Bhallataka - Jet black nut on orange cup (Schedule E-1 warning)
    card_bhallataka = get_botanical_visual_card("Bhilawa")
    assert card_bhallataka is not None
    assert card_bhallataka.canonical_sanskrit == "Bhallataka"
    assert "SCHEDULE E-1" in card_bhallataka.toxic_lookalike_warning


