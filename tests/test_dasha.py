from datetime import datetime, timedelta

from vedic_astro.dasha import (
    DASHA_YEARS,
    DAYS_PER_YEAR,
    TOTAL_CYCLE_YEARS,
    compute_deeper_sub_periods,
    compute_vimshottari_dasha,
)
from vedic_astro.models import Planet
from vedic_astro.nakshatra import DASHA_LORD_CYCLE, NAKSHATRA_SPAN


def test_moon_at_nakshatra_start_gives_full_first_mahadasha() -> None:
    birth = datetime(2000, 1, 1, 12, 0, 0)
    dasha = compute_vimshottari_dasha(moon_longitude=0.0, birth_datetime=birth)  # start of Ashwini
    first = dasha.periods[0]
    assert first.planet == Planet.KETU  # Ashwini's lord
    # start should equal birth (no balance already elapsed before birth)
    assert abs((first.start - birth).total_seconds()) < 1
    expected_years = DASHA_YEARS[Planet.KETU]
    expected_end = birth + timedelta(days=expected_years * DAYS_PER_YEAR)
    assert abs((first.end - expected_end).total_seconds()) < 1


def test_moon_near_nakshatra_end_gives_almost_no_balance() -> None:
    birth = datetime(2000, 1, 1, 12, 0, 0)
    almost_end = NAKSHATRA_SPAN * 0.999  # just before Ashwini ends
    dasha = compute_vimshottari_dasha(moon_longitude=almost_end, birth_datetime=birth)
    first = dasha.periods[0]
    # Almost the entire Ketu mahadasha has already elapsed before birth.
    remaining_days = (first.end - birth).days
    assert 0 <= remaining_days < 10


def test_mahadasha_order_follows_fixed_cycle_from_nakshatra_lord() -> None:
    birth = datetime(2000, 1, 1, 12, 0, 0)
    dasha = compute_vimshottari_dasha(moon_longitude=0.0, birth_datetime=birth)
    lords = [p.planet for p in dasha.periods]
    start_index = DASHA_LORD_CYCLE.index(Planet.KETU)
    expected = [DASHA_LORD_CYCLE[(start_index + i) % 9] for i in range(9)]
    assert lords == expected


def test_periods_are_contiguous_and_cover_full_120_years() -> None:
    birth = datetime(2000, 1, 1, 12, 0, 0)
    dasha = compute_vimshottari_dasha(moon_longitude=45.0, birth_datetime=birth)
    for earlier, later in zip(dasha.periods, dasha.periods[1:]):
        assert earlier.end == later.start
    total_days = (dasha.periods[-1].end - dasha.periods[0].start).days
    expected_days = TOTAL_CYCLE_YEARS * DAYS_PER_YEAR
    assert abs(total_days - expected_days) < 2


def test_antardashas_sum_to_mahadasha_span() -> None:
    birth = datetime(2000, 1, 1, 12, 0, 0)
    dasha = compute_vimshottari_dasha(moon_longitude=0.0, birth_datetime=birth)
    for period in dasha.periods:
        assert period.sub_periods[0].start == period.start
        assert period.sub_periods[-1].end == period.end
        assert len(period.sub_periods) == 9
        for earlier, later in zip(period.sub_periods, period.sub_periods[1:]):
            assert earlier.end == later.start


def test_antardasha_lord_sequence_starts_at_mahadasha_lord() -> None:
    birth = datetime(2000, 1, 1, 12, 0, 0)
    dasha = compute_vimshottari_dasha(moon_longitude=0.0, birth_datetime=birth)
    first_mahadasha = dasha.periods[0]
    assert first_mahadasha.sub_periods[0].planet == first_mahadasha.planet


def test_current_mahadasha_and_antardasha_lookup() -> None:
    birth = datetime(2000, 1, 1, 12, 0, 0)
    dasha = compute_vimshottari_dasha(moon_longitude=0.0, birth_datetime=birth)
    at_birth_maha = dasha.current_mahadasha(birth)
    assert at_birth_maha is not None
    assert at_birth_maha.planet == Planet.KETU
    at_birth_antar = dasha.current_antardasha(birth)
    assert at_birth_antar is not None
    assert at_birth_antar.planet == Planet.KETU

    far_future = birth + timedelta(days=200 * 365)
    assert dasha.current_mahadasha(far_future) is None


def test_compute_deeper_sub_periods_one_level_matches_subdivide_logic() -> None:
    start = datetime(2000, 1, 1)
    result = compute_deeper_sub_periods(Planet.KETU, start, years=7.0, levels=1)
    assert len(result) == 9
    assert result[0].planet == Planet.KETU  # sequence starts at the lord itself
    assert result[0].start == start
    assert result[-1].end == start + timedelta(days=7.0 * DAYS_PER_YEAR)
    # Level 1 means no further nesting.
    assert all(p.sub_periods == [] for p in result)


def test_compute_deeper_sub_periods_three_levels_nests_correctly() -> None:
    start = datetime(2000, 1, 1)
    result = compute_deeper_sub_periods(Planet.KETU, start, years=7.0, levels=3)
    assert len(result) == 9  # Pratyantardasha
    for pratyantardasha in result:
        assert len(pratyantardasha.sub_periods) == 9  # Sookshma
        for sookshma in pratyantardasha.sub_periods:
            assert len(sookshma.sub_periods) == 9  # Prana
            assert all(p.sub_periods == [] for p in sookshma.sub_periods)


def test_compute_deeper_sub_periods_durations_sum_to_parent_span() -> None:
    start = datetime(2000, 1, 1)
    years = 7.0
    result = compute_deeper_sub_periods(Planet.KETU, start, years, levels=2)
    assert result[0].start == start
    assert result[-1].end == start + timedelta(days=years * DAYS_PER_YEAR)
    for pratyantardasha in result:
        assert pratyantardasha.sub_periods[0].start == pratyantardasha.start
        assert pratyantardasha.sub_periods[-1].end == pratyantardasha.end


def test_compute_deeper_sub_periods_each_level_starts_at_its_own_lord() -> None:
    start = datetime(2000, 1, 1)
    result = compute_deeper_sub_periods(Planet.VENUS, start, years=20.0, levels=2)
    assert result[0].planet == Planet.VENUS
    assert result[0].sub_periods[0].planet == Planet.VENUS


def test_compute_deeper_sub_periods_periods_are_contiguous() -> None:
    start = datetime(2000, 1, 1)
    result = compute_deeper_sub_periods(Planet.SUN, start, years=6.0, levels=2)
    for earlier, later in zip(result, result[1:]):
        assert earlier.end == later.start
    for period in result:
        for earlier, later in zip(period.sub_periods, period.sub_periods[1:]):
            assert earlier.end == later.start
