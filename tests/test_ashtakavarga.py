from datetime import date, time

import pytest

from vedic_astro.ashtakavarga import (
    ASHTAKAVARGA_PLANETS,
    BAV_FIXED_TOTALS,
    _BAV_CONTRIBUTION_TABLE,
    bhava_ashtakavarga,
    bhinnashtakavarga,
    compute_ashtakavarga,
    samudaya_ashtakavarga,
)
from vedic_astro.chart import build_kundali_chart
from vedic_astro.models import BirthData, Planet, Sign


def _sample_birth_data() -> BirthData:
    return BirthData(
        birth_date=date(1990, 6, 15),
        birth_time=time(8, 30, 0),
        latitude=13.0827,
        longitude=80.2707,  # Chennai
        utc_offset_hours=5.5,
    )


def _another_birth_data() -> BirthData:
    return BirthData(
        birth_date=date(1975, 12, 1),
        birth_time=time(23, 5, 0),
        latitude=28.6139,
        longitude=77.2090,  # Delhi
        utc_offset_hours=5.5,
    )


@pytest.mark.parametrize("planet", list(BAV_FIXED_TOTALS))
def test_bav_contribution_table_row_totals_match_known_fixed_totals(planet: Planet) -> None:
    # A well-known, independently-verifiable fact of the Parasara system:
    # each planet's BAV always has this exact total bindu count, regardless
    # of birth data. This is a strong check on the raw contribution table
    # itself, not on the computation logic.
    total_houses = sum(len(houses) for houses in _BAV_CONTRIBUTION_TABLE[planet].values())
    assert total_houses == BAV_FIXED_TOTALS[planet]


def test_bav_fixed_totals_sum_to_337() -> None:
    assert sum(BAV_FIXED_TOTALS.values()) == 337


@pytest.mark.parametrize("birth_data", [_sample_birth_data(), _another_birth_data()])
def test_samudaya_ashtakavarga_totals_337_regardless_of_birth_data(birth_data: BirthData) -> None:
    chart = build_kundali_chart(birth_data)
    sav = samudaya_ashtakavarga(chart.planets, chart.ascendant.sign)
    assert sum(sav.values()) == 337


@pytest.mark.parametrize("planet", ASHTAKAVARGA_PLANETS)
def test_bhinnashtakavarga_scores_are_between_zero_and_eight(planet: Planet) -> None:
    chart = build_kundali_chart(_sample_birth_data())
    bav = bhinnashtakavarga(chart.planets, chart.ascendant.sign, planet)
    assert set(bav.keys()) == set(Sign)
    for score in bav.values():
        assert 0 <= score <= 8


def test_compute_ashtakavarga_bav_by_planet_totals_match_fixed_totals() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    result = compute_ashtakavarga(chart.planets, chart.ascendant.sign, chart.bhava_chalit_cusps)
    for planet in ASHTAKAVARGA_PLANETS:
        assert sum(result.bav_by_planet[planet].values()) == BAV_FIXED_TOTALS[planet]


def test_compute_ashtakavarga_sav_totals_337() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    result = compute_ashtakavarga(chart.planets, chart.ascendant.sign, chart.bhava_chalit_cusps)
    assert sum(result.sav.values()) == 337


def test_bhava_ashtakavarga_preserves_the_337_total() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    sav = samudaya_ashtakavarga(chart.planets, chart.ascendant.sign)
    bhava_sav = bhava_ashtakavarga(sav, chart.bhava_chalit_cusps)
    assert sum(bhava_sav.values()) == 337
    assert set(bhava_sav.keys()) == set(range(1, 13))


def test_bhava_ashtakavarga_never_spuriously_zeroes_a_house() -> None:
    # Regression test: the earlier "assign a sign's whole SAV to whichever
    # house contains its midpoint" method could leave a house at exactly 0
    # whenever its Placidus cusp span was narrow enough to miss every
    # sign's midpoint, while a neighboring house absorbed two signs' worth
    # of bindus instead - a real user caught this with this exact birth
    # data/time (Andhra Pradesh, evening). Proportional degree-overlap
    # redistribution should never do this, since every house has positive
    # width and therefore always overlaps at least one sign.
    birth_data = BirthData(
        birth_date=date(1998, 9, 4),
        birth_time=time(19, 30, 0),
        latitude=17.91589,
        longitude=82.81578,
        utc_offset_hours=5.5,
    )
    chart = build_kundali_chart(birth_data)
    assert chart.ashtakavarga is not None
    bhava_sav = chart.ashtakavarga.bhava_ashtakavarga
    assert all(score > 0 for score in bhava_sav.values())
    assert sum(bhava_sav.values()) == 337


@pytest.mark.parametrize("hour", [1, 4, 7, 10, 13, 16, 19, 22])
def test_bhava_ashtakavarga_no_spurious_zero_across_many_birth_times(hour: int) -> None:
    birth_data = BirthData(
        birth_date=date(1998, 9, 4),
        birth_time=time(hour, 30, 0),
        latitude=17.91589,
        longitude=82.81578,
        utc_offset_hours=5.5,
    )
    chart = build_kundali_chart(birth_data)
    assert chart.ashtakavarga is not None
    bhava_sav = chart.ashtakavarga.bhava_ashtakavarga
    assert all(score > 0 for score in bhava_sav.values()), (hour, bhava_sav)
    assert sum(bhava_sav.values()) == 337
