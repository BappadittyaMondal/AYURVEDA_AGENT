"""
Unit Tests for Classical Herbology (Dravya Guna) Knowledge Graph & Phytochemical Database.
"""

import tempfile
from pathlib import Path
import sqlite3
import pytest
from core.database import init_database
from core.dravyaguna import (
    SEED_HERBAL_REGISTRY,
    calculate_doshic_modulation_vector,
    get_herb_by_id,
    search_herbs,
    seed_dravyaguna_registry,
)
from models.dravyaguna import (
    DoshicEffect,
    Guna,
    Rasa,
    Veerya,
    Vipaka,
)


def test_herbal_registry_completeness():
    """Verify that all 25 classical medicinal herbs are present and strictly populated."""
    assert len(SEED_HERBAL_REGISTRY) >= 25

    for herb in SEED_HERBAL_REGISTRY:
        assert herb.herb_id.startswith("HERB-")
        assert len(herb.sanskrit_name) > 0
        assert len(herb.botanical_name) > 0
        assert len(herb.botanical_family) > 0
        assert len(herb.rasa) >= 1
        assert len(herb.guna) >= 1
        assert isinstance(herb.veerya, Veerya)
        assert isinstance(herb.vipaka, Vipaka)
        assert isinstance(herb.doshic_karma.vata, DoshicEffect)
        assert isinstance(herb.doshic_karma.pitta, DoshicEffect)
        assert isinstance(herb.doshic_karma.kapha, DoshicEffect)
        assert len(herb.therapeutics_karma) >= 2
        assert len(herb.phytochemicals) >= 1
        assert len(herb.parts_used) >= 1
        assert len(herb.dosages) >= 1


def test_classical_rasa_panchaka_vectors_accuracy():
    """Verify pharmacological ground truth for hallmark classical plants."""
    herb_map = {h.herb_id: h for h in SEED_HERBAL_REGISTRY}

    # 1. Ashwagandha
    ashwa = herb_map["HERB-ASHWAGANDHA"]
    assert Rasa.TIKTA in ashwa.rasa and Rasa.MADHURA in ashwa.rasa
    assert ashwa.veerya == Veerya.USHNA
    assert ashwa.vipaka == Vipaka.MADHURA
    assert ashwa.doshic_karma.vata == DoshicEffect.SHAMANA
    assert ashwa.doshic_karma.kapha == DoshicEffect.SHAMANA
    assert any("Withaferin" in p.compound_name for p in ashwa.phytochemicals)

    # 2. Guduchi
    guduchi = herb_map["HERB-GUDUCHI"]
    assert Rasa.TIKTA in guduchi.rasa
    assert guduchi.veerya == Veerya.USHNA
    assert guduchi.vipaka == Vipaka.MADHURA
    assert guduchi.doshic_karma.vata == DoshicEffect.SHAMANA
    assert guduchi.doshic_karma.pitta == DoshicEffect.SHAMANA
    assert guduchi.doshic_karma.kapha == DoshicEffect.SHAMANA

    # 3. Amalaki (Pancharasa alavana - all except salty)
    amalaki = herb_map["HERB-AMALAKI"]
    assert len(amalaki.rasa) == 5
    assert Rasa.LAVANA not in amalaki.rasa
    assert amalaki.veerya == Veerya.SHEETA
    assert amalaki.vipaka == Vipaka.MADHURA

    # 4. Shunthi
    shunthi = herb_map["HERB-SHUNTHI"]
    assert Rasa.KATU in shunthi.rasa
    assert shunthi.veerya == Veerya.USHNA
    assert shunthi.vipaka == Vipaka.MADHURA

    # 5. Nimba
    nimba = herb_map["HERB-NIMBA"]
    assert Rasa.TIKTA in nimba.rasa
    assert nimba.veerya == Veerya.SHEETA
    assert nimba.vipaka == Vipaka.KATU
    assert nimba.doshic_karma.vata == DoshicEffect.KOPANA
    assert nimba.doshic_karma.pitta == DoshicEffect.SHAMANA


def test_dravyaguna_search_and_multi_axial_filtering():
    """Verify text search and multi-axial pharmacological filtering."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_dg_search.db"
        init_database(db_file)
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row

        # 1. Search by bioactive metabolite
        curcumin_herbs = search_herbs(conn, query="Curcumin")
        assert len(curcumin_herbs) == 1
        assert curcumin_herbs[0].herb_id == "HERB-HARIDRA"

        # 2. Filter by Sheeta Veerya
        sheeta_herbs = search_herbs(conn, veerya=Veerya.SHEETA)
        assert len(sheeta_herbs) >= 8
        for h in sheeta_herbs:
            assert h.veerya == Veerya.SHEETA

        # 3. Filter by Madhura Vipaka
        madhura_vipaka_herbs = search_herbs(conn, vipaka=Vipaka.MADHURA)
        assert len(madhura_vipaka_herbs) >= 8
        for h in madhura_vipaka_herbs:
            assert h.vipaka == Vipaka.MADHURA

        # 4. Filter by Medhya Karma
        medhya_herbs = search_herbs(conn, karma="Medhya")
        medhya_ids = [h.herb_id for h in medhya_herbs]
        assert "HERB-BRAHMI" in medhya_ids
        assert "HERB-SHANKHAPUSHPI" in medhya_ids

        conn.close()


def test_doshic_modulation_vector_synthesis():
    """Verify quantitative directional Doshic score calculations."""
    herb_map = {h.herb_id: h for h in SEED_HERBAL_REGISTRY}

    # Ashwagandha: Pacifies Vata & Kapha
    ashwa = herb_map["HERB-ASHWAGANDHA"]
    ashwa_mod = calculate_doshic_modulation_vector(ashwa)
    assert ashwa_mod.vata_delta < -0.50
    assert ashwa_mod.kapha_delta < -0.50

    # Nimba: Aggravates Vata, Pacifies Pitta & Kapha
    nimba = herb_map["HERB-NIMBA"]
    nimba_mod = calculate_doshic_modulation_vector(nimba)
    assert nimba_mod.vata_delta > 0.30
    assert nimba_mod.pitta_delta < -0.50

    # Guduchi: Pacifies all 3 Doshas
    guduchi = herb_map["HERB-GUDUCHI"]
    guduchi_mod = calculate_doshic_modulation_vector(guduchi)
    assert guduchi_mod.vata_delta <= 0.0
    assert guduchi_mod.pitta_delta <= 0.0
    assert guduchi_mod.kapha_delta <= 0.0
