from datetime import datetime

import pytest

from vedic_astro.jaimini import compute_chara_dasha, compute_chara_karakas
from vedic_astro.models import NakshatraPlacement, Planet, PlanetPosition, Sign

_DUMMY_NAKSHATRA = NakshatraPlacement(name="Ashwini", index=1, pada=1, lord=Planet.KETU)


def _planet(planet: Planet, sign: Sign, degree_in_sign: float, house: int = 1) -> PlanetPosition:
    return PlanetPosition(
        planet=planet,
        longitude=SIGN_INDEX[sign] * 30 + degree_in_sign,
        sign=sign,
        degree_in_sign=degree_in_sign,
        house=house,
        nakshatra=_DUMMY_NAKSHATRA,
        retrograde=False,
    )


SIGN_INDEX = {s: i for i, s in enumerate(Sign)}


def test_compute_chara_karakas_ranks_by_degree_descending() -> None:
    planets = [
        _planet(Planet.SUN, Sign.ARIES, 10.0),
        _planet(Planet.MOON, Sign.TAURUS, 25.0),
        _planet(Planet.MARS, Sign.GEMINI, 5.0),
        _planet(Planet.MERCURY, Sign.CANCER, 20.0),
        _planet(Planet.JUPITER, Sign.LEO, 15.0),
        _planet(Planet.VENUS, Sign.VIRGO, 29.0),
        _planet(Planet.SATURN, Sign.LIBRA, 1.0),
    ]
    karakas = compute_chara_karakas(planets)
    assert [k.planet for k in karakas] == [
        Planet.VENUS, Planet.MOON, Planet.MERCURY, Planet.JUPITER,
        Planet.SUN, Planet.MARS, Planet.SATURN,
    ]
    assert karakas[0].karaka == "Atmakaraka"
    assert karakas[-1].karaka == "Darakaraka"


def test_compute_chara_karakas_excludes_rahu_ketu() -> None:
    planets = [
        _planet(Planet.SUN, Sign.ARIES, 10.0),
        _planet(Planet.RAHU, Sign.TAURUS, 29.0),  # highest degree, but excluded
        _planet(Planet.KETU, Sign.SCORPIO, 29.0),
    ]
    karakas = compute_chara_karakas(planets)
    assert Planet.RAHU not in [k.planet for k in karakas]
    assert Planet.KETU not in [k.planet for k in karakas]
    assert karakas[0].planet == Planet.SUN


def _full_seven_planets(sign_of: dict[Planet, Sign]) -> list[PlanetPosition]:
    degrees = {
        Planet.SUN: 10.0, Planet.MOON: 15.0, Planet.MARS: 5.0, Planet.MERCURY: 20.0,
        Planet.JUPITER: 12.0, Planet.VENUS: 8.0, Planet.SATURN: 25.0,
    }
    return [_planet(p, sign_of.get(p, Sign.ARIES), degrees[p]) for p in degrees]


def test_compute_chara_dasha_starts_at_ascendant_sign() -> None:
    planets = _full_seven_planets({})
    result = compute_chara_dasha(Sign.LEO, planets, datetime(2000, 1, 1))
    assert result[0].sign == Sign.LEO


def test_compute_chara_dasha_sequence_is_forward_from_ascendant() -> None:
    planets = _full_seven_planets({})
    result = compute_chara_dasha(Sign.LEO, planets, datetime(2000, 1, 1))
    signs = [p.sign for p in result]
    assert signs == [
        Sign.LEO, Sign.VIRGO, Sign.LIBRA, Sign.SCORPIO, Sign.SAGITTARIUS, Sign.CAPRICORN,
        Sign.AQUARIUS, Sign.PISCES, Sign.ARIES, Sign.TAURUS, Sign.GEMINI, Sign.CANCER,
    ]


def test_compute_chara_dasha_returns_twelve_periods_covering_all_signs() -> None:
    planets = _full_seven_planets({})
    result = compute_chara_dasha(Sign.ARIES, planets, datetime(2000, 1, 1))
    assert len(result) == 12
    assert {p.sign for p in result} == set(Sign)


def test_compute_chara_dasha_periods_are_contiguous() -> None:
    planets = _full_seven_planets({})
    result = compute_chara_dasha(Sign.ARIES, planets, datetime(2000, 1, 1))
    for earlier, later in zip(result, result[1:]):
        assert earlier.end == later.start


def test_compute_chara_dasha_lord_matches_rashi_lord() -> None:
    planets = _full_seven_planets({})
    result = compute_chara_dasha(Sign.ARIES, planets, datetime(2000, 1, 1))
    aries_period = next(p for p in result if p.sign == Sign.ARIES)
    assert aries_period.lord == Planet.MARS
    taurus_period = next(p for p in result if p.sign == Sign.TAURUS)
    assert taurus_period.lord == Planet.VENUS


def test_compute_chara_dasha_own_sign_gives_twelve_years() -> None:
    # Mars placed in Aries itself -> Aries's own dasha period should be 12 years.
    planets = _full_seven_planets({Planet.MARS: Sign.ARIES})
    result = compute_chara_dasha(Sign.ARIES, planets, datetime(2000, 1, 1))
    aries_period = next(p for p in result if p.sign == Sign.ARIES)
    assert aries_period.years == pytest.approx(12.0)
