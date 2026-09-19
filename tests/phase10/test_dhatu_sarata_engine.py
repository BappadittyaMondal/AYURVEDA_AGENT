"""Unit tests for Dhatu Sarata Quantitative Tissue Vitality Index (7 Dhatus + Sattva)."""
import pytest
from core.dhatu_sarata import (
    calculate_overall_sarata_index,
    generate_dhatu_directives,
    classify_tier_from_score,
)
from models.dhatu_sarata import (
    DhatuType,
    SarataTier,
    DhatuRating,
)


def test_tier_classification_bounds():
    """Verify tier classification boundaries."""
    assert classify_tier_from_score(1.0) == SarataTier.PRAVARA
    assert classify_tier_from_score(0.75) == SarataTier.PRAVARA
    assert classify_tier_from_score(0.749) == SarataTier.MADHYAMA
    assert classify_tier_from_score(0.50) == SarataTier.MADHYAMA
    assert classify_tier_from_score(0.499) == SarataTier.AVARA
    assert classify_tier_from_score(0.0) == SarataTier.AVARA


def test_overall_sarata_index_extremes():
    """Verify 100% OSI for all-Pravara and 0% for all-Avara."""
    pravara_ratings = [DhatuRating(dhatu=d, score=1.0) for d in DhatuType]
    osi_high, tier_high, scores_high = calculate_overall_sarata_index(pravara_ratings)
    assert osi_high == 100.0
    assert tier_high == SarataTier.PRAVARA
    assert len(scores_high) == 8

    avara_ratings = [DhatuRating(dhatu=d, score=0.0) for d in DhatuType]
    osi_low, tier_low, scores_low = calculate_overall_sarata_index(avara_ratings)
    assert osi_low == 0.0
    assert tier_low == SarataTier.AVARA


def test_vulnerable_dhatu_identification_and_rasayana():
    """Verify that tissues with score < 0.60 are flagged as vulnerable with targeted Rasayanas."""
    mixed_ratings = [
        DhatuRating(dhatu=DhatuType.RASA, score=0.8),
        DhatuRating(dhatu=DhatuType.RAKTA, score=0.4),  # Vulnerable
        DhatuRating(dhatu=DhatuType.MAMSA, score=0.85),
        DhatuRating(dhatu=DhatuType.MEDA, score=0.7),
        DhatuRating(dhatu=DhatuType.ASTHI, score=0.35),  # Vulnerable
        DhatuRating(dhatu=DhatuType.MAJJA, score=0.75),
        DhatuRating(dhatu=DhatuType.SHUKRA, score=0.9),
        DhatuRating(dhatu=DhatuType.SATTVA, score=0.8),
    ]

    vulnerable, directives = generate_dhatu_directives(mixed_ratings)
    assert "RAKTA" in vulnerable
    assert "ASTHI" in vulnerable
    assert "MAMSA" not in vulnerable

    # Verify Rakta herbs
    rakta_dir = next(d for d in directives if d.dhatu == DhatuType.RAKTA)
    assert "Amalaki" in rakta_dir.indicated_rasayana_herbs
    assert "Sariva" in rakta_dir.indicated_rasayana_herbs

    # Verify Asthi herbs
    asthi_dir = next(d for d in directives if d.dhatu == DhatuType.ASTHI)
    assert "Pravala Pishti" in asthi_dir.indicated_rasayana_herbs
