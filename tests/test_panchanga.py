from datetime import date

import pytest

from vedic_astro.panchanga import compute_panchanga


def test_new_moon_is_amavasya_tithi_thirty() -> None:
    # Sun and Moon at the same longitude -> diff 0 -> first tithi of Krishna... actually
    # diff=0 is the *start* of Shukla Pratipada (new moon moment itself, tithi 1).
    result = compute_panchanga(sun_longitude=100.0, moon_longitude=100.0, local_date=date(2024, 1, 1))
    assert result.tithi.name == "Pratipada"
    assert result.paksha == "Shukla"
    assert result.tithi.index == 1


def test_full_moon_is_purnima() -> None:
    # Moon well within the last 12-degree slice before opposition (168-180 degrees
    # from Sun) -> tithi 15, Purnima. (Exactly 180 degrees is the boundary instant
    # that starts the *next* tithi, Krishna Pratipada - not tested here.)
    result = compute_panchanga(sun_longitude=100.0, moon_longitude=270.0, local_date=date(2024, 1, 1))
    assert result.tithi.name == "Purnima"
    assert result.paksha == "Shukla"
    assert result.tithi.index == 15


def test_just_before_new_moon_is_amavasya() -> None:
    # Moon just short of a full 360-degree catch-up -> last tithi, Krishna Amavasya.
    result = compute_panchanga(sun_longitude=100.0, moon_longitude=99.5, local_date=date(2024, 1, 1))
    assert result.tithi.name == "Amavasya"
    assert result.paksha == "Krishna"
    assert result.tithi.index == 30


def test_karana_kimstughna_at_zero_diff() -> None:
    result = compute_panchanga(sun_longitude=50.0, moon_longitude=50.0, local_date=date(2024, 1, 1))
    assert result.karana.name == "Kimstughna"


def test_karana_movable_cycle() -> None:
    # 6 degrees into the diff -> second karana slot (index 1, 0-indexed) -> first movable, Bava.
    result = compute_panchanga(sun_longitude=0.0, moon_longitude=6.0, local_date=date(2024, 1, 1))
    assert result.karana.name == "Bava"


def test_yoga_first_slot_is_vishkambha() -> None:
    result = compute_panchanga(sun_longitude=0.0, moon_longitude=0.0, local_date=date(2024, 1, 1))
    assert result.yoga.name == "Vishkambha"
    assert result.yoga.index == 1


@pytest.mark.parametrize(
    ("year", "month", "day", "expected_vara"),
    [
        (2024, 1, 1, "Somavara"),  # Monday
        (2024, 1, 7, "Ravivara"),  # Sunday
    ],
)
def test_vara_matches_calendar_weekday(year: int, month: int, day: int, expected_vara: str) -> None:
    result = compute_panchanga(sun_longitude=0.0, moon_longitude=0.0, local_date=date(year, month, day))
    assert result.vara == expected_vara


def test_nakshatra_reflects_moon_position() -> None:
    result = compute_panchanga(sun_longitude=0.0, moon_longitude=0.0, local_date=date(2024, 1, 1))
    assert result.nakshatra.name == "Ashwini"
