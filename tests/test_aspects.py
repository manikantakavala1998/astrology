import pytest

from vedic_astro.aspects import aspected_houses, compute_aspects, sign_aspects
from vedic_astro.models import NakshatraPlacement, Planet, PlanetPosition, Sign

_DUMMY_NAKSHATRA = NakshatraPlacement(name="Ashwini", index=1, pada=1, lord=Planet.KETU)


def _planet(planet: Planet, house: int) -> PlanetPosition:
    return PlanetPosition(
        planet=planet,
        longitude=0.0,
        sign=Sign.ARIES,
        degree_in_sign=0.0,
        house=house,
        nakshatra=_DUMMY_NAKSHATRA,
        retrograde=False,
    )


@pytest.mark.parametrize(
    ("planet", "expected"),
    [
        (Planet.SUN, [7]),
        (Planet.MOON, [7]),
        (Planet.MERCURY, [7]),
        (Planet.VENUS, [7]),
        (Planet.MARS, [4, 7, 8]),
        (Planet.JUPITER, [5, 7, 9]),
        (Planet.SATURN, [3, 7, 10]),
    ],
)
def test_aspected_houses_from_house_one(planet: Planet, expected: list[int]) -> None:
    assert aspected_houses(planet, from_house=1) == expected


def test_aspected_houses_wraps_around_the_zodiac() -> None:
    # From house 10, the 7th aspect lands on house 4 (10 -> 11 -> 12 -> 1 -> 2 -> 3 -> 4).
    assert aspected_houses(Planet.SUN, from_house=10) == [4]
    # Saturn from house 10: 3rd->12, 7th->4, 10th->7.
    assert aspected_houses(Planet.SATURN, from_house=10) == [4, 7, 12]


def test_rahu_and_ketu_aspect_nothing_as_a_source() -> None:
    assert aspected_houses(Planet.RAHU, from_house=1) == []
    assert aspected_houses(Planet.KETU, from_house=1) == []


def test_compute_aspects_mars_in_house_one_aspects_four_seven_eight() -> None:
    planets = [
        _planet(Planet.MARS, house=1),
        _planet(Planet.VENUS, house=4),
        _planet(Planet.SATURN, house=7),
        _planet(Planet.JUPITER, house=8),
        _planet(Planet.MOON, house=2),  # not aspected
    ]
    results = compute_aspects(planets)
    targets = {r.target_planet for r in results if r.source_planet == Planet.MARS}
    assert targets == {Planet.VENUS, Planet.SATURN, Planet.JUPITER}


def test_compute_aspects_marks_special_aspects_correctly() -> None:
    planets = [
        _planet(Planet.MARS, house=1),
        _planet(Planet.VENUS, house=4),  # Mars's special aspect
        _planet(Planet.SATURN, house=7),  # Mars's universal 7th, not special
    ]
    results = compute_aspects(planets)
    by_target = {r.target_planet: r for r in results if r.source_planet == Planet.MARS}
    assert by_target[Planet.VENUS].is_special is True
    assert by_target[Planet.SATURN].is_special is False


def test_compute_aspects_planet_never_aspects_its_own_house() -> None:
    planets = [_planet(Planet.MARS, house=1), _planet(Planet.VENUS, house=1)]
    results = compute_aspects(planets)
    # Mars and Venus share a house (conjunction) - drishti does not include same-house.
    assert results == []


def test_compute_aspects_rahu_ketu_never_appear_as_source() -> None:
    planets = [_planet(Planet.RAHU, house=1), _planet(Planet.MOON, house=7)]
    results = compute_aspects(planets)
    assert all(r.source_planet not in (Planet.RAHU, Planet.KETU) for r in results)


def test_compute_aspects_rahu_ketu_can_still_be_a_target() -> None:
    planets = [_planet(Planet.SUN, house=1), _planet(Planet.RAHU, house=7)]
    results = compute_aspects(planets)
    assert any(r.target_planet == Planet.RAHU for r in results)


@pytest.mark.parametrize(
    ("sign", "expected"),
    [
        (Sign.ARIES, [Sign.LEO, Sign.SCORPIO, Sign.AQUARIUS]),
        (Sign.TAURUS, [Sign.CANCER, Sign.LIBRA, Sign.CAPRICORN]),
        (Sign.GEMINI, [Sign.VIRGO, Sign.SAGITTARIUS, Sign.PISCES]),
    ],
)
def test_sign_aspects_known_values(sign: Sign, expected: list[Sign]) -> None:
    assert sign_aspects(sign) == expected


def test_sign_aspects_every_sign_has_exactly_three_aspects() -> None:
    for sign in Sign:
        assert len(sign_aspects(sign)) == 3


def test_sign_aspects_never_aspects_itself() -> None:
    for sign in Sign:
        assert sign not in sign_aspects(sign)


def test_sign_aspects_are_mutual() -> None:
    # This classical system is reciprocal: if A aspects B, B aspects A.
    for sign in Sign:
        for aspected in sign_aspects(sign):
            assert sign in sign_aspects(aspected)


def test_sign_aspects_movable_never_aspects_adjacent_fixed_sign() -> None:
    # Aries (movable) is adjacent to Taurus (fixed) - Taurus must be excluded.
    assert Sign.TAURUS not in sign_aspects(Sign.ARIES)
    assert Sign.PISCES not in sign_aspects(Sign.ARIES)  # Pisces is dual, never aspected by a movable sign anyway
