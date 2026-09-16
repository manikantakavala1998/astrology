import pytest

from vedic_astro.models import Planet
from vedic_astro.nakshatra import (
    NAKSHATRA_SPAN,
    TARA_FAVORABLE,
    compute_navatara_chakra,
    nakshatra_for_longitude,
    tara_category,
)


def test_ashwini_at_zero_degrees() -> None:
    n = nakshatra_for_longitude(0.0)
    assert n.name == "Ashwini"
    assert n.index == 1
    assert n.pada == 1
    assert n.lord == Planet.KETU


def test_revati_near_360_degrees() -> None:
    n = nakshatra_for_longitude(359.9)
    assert n.name == "Revati"
    assert n.index == 27
    assert n.pada == 4
    assert n.lord == Planet.MERCURY


def test_wraps_at_360() -> None:
    assert nakshatra_for_longitude(360.0).name == "Ashwini"


@pytest.mark.parametrize("boundary_index", range(27))
def test_every_nakshatra_start_boundary_is_stable(boundary_index: int) -> None:
    longitude = boundary_index * NAKSHATRA_SPAN
    n = nakshatra_for_longitude(longitude)
    assert n.index == boundary_index + 1
    assert n.pada == 1


def test_pada_progression_within_a_nakshatra() -> None:
    # Bharani spans 13.3333-26.6667 degrees; check all four pada boundaries.
    start = NAKSHATRA_SPAN  # start of Bharani
    pada_span = NAKSHATRA_SPAN / 4
    for pada_number in range(1, 5):
        n = nakshatra_for_longitude(start + (pada_number - 1) * pada_span)
        assert n.name == "Bharani"
        assert n.pada == pada_number


def test_lords_cycle_through_all_nine_planets_three_times() -> None:
    lords = [nakshatra_for_longitude(i * NAKSHATRA_SPAN).lord for i in range(27)]
    assert lords[:9] == lords[9:18] == lords[18:27]
    assert len(set(lords[:9])) == 9


def test_navatara_chakra_has_all_27_nakshatras_in_order() -> None:
    entries = compute_navatara_chakra(1)
    assert len(entries) == 27
    assert [e.nakshatra_index for e in entries] == list(range(1, 28))


def test_navatara_chakra_own_nakshatra_is_janma_and_unfavorable() -> None:
    # Moon in Rohini(4): Rohini counted from itself is always "Janma".
    entries = compute_navatara_chakra(4)
    own = next(e for e in entries if e.nakshatra_index == 4)
    assert own.tara_category == "Janma"
    assert own.is_favorable is False


def test_navatara_chakra_categories_repeat_every_ninth_nakshatra() -> None:
    entries = compute_navatara_chakra(7)
    categories = [e.tara_category for e in entries]
    assert categories[0:9] == categories[9:18] == categories[18:27]


def test_navatara_chakra_matches_tested_tara_category_function() -> None:
    moon_index = 15
    entries = compute_navatara_chakra(moon_index)
    for entry in entries:
        expected = tara_category(moon_index, entry.nakshatra_index)
        assert entry.tara_category == expected
        assert entry.is_favorable == (expected in TARA_FAVORABLE)


def test_navatara_chakra_names_match_nakshatra_index_order() -> None:
    entries = compute_navatara_chakra(1)
    assert entries[0].nakshatra == "Ashwini"
    assert entries[3].nakshatra == "Rohini"
    assert entries[26].nakshatra == "Revati"
