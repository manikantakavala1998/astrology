from datetime import date, time

import pytest

from vedic_astro.bhava_bala import (
    bhava_dig_bala,
    bhava_drishti_bala,
    compute_bhava_bala,
    occupancy_adjustment_rupas,
)
from vedic_astro.chart import build_kundali_chart
from vedic_astro.models import BirthData, NakshatraPlacement, Planet, PlanetPosition, Sign
from vedic_astro.shadbala import compute_shadbala


def _sample_birth_data() -> BirthData:
    return BirthData(
        birth_date=date(1990, 6, 15),
        birth_time=time(8, 30, 0),
        latitude=13.0827,
        longitude=80.2707,
        utc_offset_hours=5.5,
    )


_DUMMY_NAKSHATRA = NakshatraPlacement(name="Ashwini", index=1, pada=1, lord=Planet.KETU)


def _planet(planet: Planet, bhava_chalit_house: int) -> PlanetPosition:
    return PlanetPosition(
        planet=planet,
        longitude=0.0,
        sign=Sign.ARIES,
        degree_in_sign=0.0,
        house=bhava_chalit_house,
        nakshatra=_DUMMY_NAKSHATRA,
        retrograde=False,
        bhava_chalit_house=bhava_chalit_house,
    )


# ---------------------------------------------------------------------------
# Bhava Dig Bala
# ---------------------------------------------------------------------------


def test_bhava_dig_bala_is_60_at_the_reference_cusp() -> None:
    # A bhava cusp in Cancer (whose reference point is the Ascendant)
    # placed exactly 180 degrees from the Ascendant is at full strength.
    cusps = [0.0] * 12
    cusps[0] = 10.0  # Ascendant
    cancer_start = 90.0  # Cancer spans 90-120 degrees
    bhava_longitude = cancer_start + 5.0  # inside Cancer
    # Place the Ascendant 180 degrees away from this bhava longitude.
    cusps[0] = (bhava_longitude + 180.0) % 360
    assert bhava_dig_bala(bhava_longitude, cusps) == pytest.approx(60.0, abs=0.01)


def test_bhava_dig_bala_is_0_at_the_reference_cusp_itself() -> None:
    cusps = [0.0] * 12
    cancer_start = 90.0
    bhava_longitude = cancer_start + 5.0
    cusps[0] = bhava_longitude  # Ascendant coincides with the bhava itself
    assert bhava_dig_bala(bhava_longitude, cusps) == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# Bhava Drishti Bala
# ---------------------------------------------------------------------------


def test_bhava_drishti_bala_zero_when_nothing_aspects() -> None:
    planets = [_planet(Planet.SUN, 5)]  # far from house 1, no 7th-house reach
    assert bhava_drishti_bala(1, 30.0, planets, moon_is_waxing=True) == pytest.approx(0.0)


def test_bhava_drishti_bala_benefic_aspect_increases_by_a_quarter() -> None:
    # Jupiter in Bhava-Chalit house 7 aspects house 1 (its universal 7th).
    planets = [_planet(Planet.JUPITER, 7)]
    delta = bhava_drishti_bala(1, 40.0, planets, moon_is_waxing=True)
    # +25% of 40 (the quarter-increase) plus Jupiter's own full-strength
    # bonus (60, since this is Jupiter's universal, non-special aspect).
    assert delta == pytest.approx(40.0 * 0.25 + 60.0)


def test_bhava_drishti_bala_malefic_aspect_decreases_by_a_quarter() -> None:
    # Saturn in Bhava-Chalit house 7 aspects house 1 (its universal 7th,
    # not one of Saturn's 3rd/10th specials).
    planets = [_planet(Planet.SATURN, 7)]
    delta = bhava_drishti_bala(1, 40.0, planets, moon_is_waxing=True)
    assert delta == pytest.approx(-40.0 * 0.25)


def test_bhava_drishti_bala_mercury_special_case_adds_its_own_strength() -> None:
    # Mercury (a natural-neutral-for-this-rule planet, not benefic/malefic
    # in this module's classification) aspecting still contributes its own
    # flat bonus without a +-1/4 adjustment.
    planets = [_planet(Planet.MERCURY, 7)]
    delta = bhava_drishti_bala(1, 40.0, planets, moon_is_waxing=True)
    assert delta == pytest.approx(60.0)


# ---------------------------------------------------------------------------
# Occupancy adjustment
# ---------------------------------------------------------------------------


def test_occupancy_adjustment_positive_for_jupiter_and_mercury() -> None:
    planets = [_planet(Planet.JUPITER, 3), _planet(Planet.MERCURY, 3)]
    assert occupancy_adjustment_rupas(3, planets) == pytest.approx(2.0)


def test_occupancy_adjustment_negative_for_malefic_occupants() -> None:
    planets = [_planet(Planet.SATURN, 3), _planet(Planet.MARS, 3), _planet(Planet.SUN, 3)]
    assert occupancy_adjustment_rupas(3, planets) == pytest.approx(-3.0)


def test_occupancy_adjustment_neutral_for_moon_and_venus() -> None:
    planets = [_planet(Planet.MOON, 3), _planet(Planet.VENUS, 3)]
    assert occupancy_adjustment_rupas(3, planets) == pytest.approx(0.0)


def test_occupancy_adjustment_ignores_other_houses() -> None:
    planets = [_planet(Planet.SATURN, 5)]
    assert occupancy_adjustment_rupas(3, planets) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Orchestrator (integration, on a real chart)
# ---------------------------------------------------------------------------


def test_compute_bhava_bala_covers_all_twelve_houses() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    shadbala = compute_shadbala(
        chart.planets, chart.ascendant.sign, chart.bhava_chalit_cusps,
        chart.aspects, chart.birth_data, chart.panchanga.paksha == "Shukla",
    )
    results = compute_bhava_bala(
        chart.planets, chart.bhava_chalit_cusps, chart.ascendant.sign,
        shadbala, chart.panchanga.paksha == "Shukla",
    )
    assert set(results) == set(range(1, 13))


def test_compute_bhava_bala_totals_are_internally_consistent() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    shadbala = compute_shadbala(
        chart.planets, chart.ascendant.sign, chart.bhava_chalit_cusps,
        chart.aspects, chart.birth_data, chart.panchanga.paksha == "Shukla",
    )
    results = compute_bhava_bala(
        chart.planets, chart.bhava_chalit_cusps, chart.ascendant.sign,
        shadbala, chart.panchanga.paksha == "Shukla",
    )
    for result in results.values():
        expected = (
            result.bhavadhipati_bala + result.bhava_dig_bala + result.bhava_drishti_bala
            + result.occupancy_adjustment + result.diurnal_bonus
        )
        assert result.total_rupas == pytest.approx(expected)
        assert result.diurnal_bonus == 0.0
