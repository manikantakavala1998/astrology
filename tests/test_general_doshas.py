from vedic_astro.general_doshas import (
    compute_guru_chandala_dosha,
    compute_kalasarpa_dosha,
    compute_kuja_dosha,
)
from vedic_astro.models import NakshatraPlacement, Planet, PlanetAspect, PlanetPosition, Sign

_DUMMY_NAKSHATRA = NakshatraPlacement(name="Ashwini", index=1, pada=1, lord=Planet.KETU)


def _planet(planet: Planet, house: int, sign: Sign = Sign.ARIES) -> PlanetPosition:
    return PlanetPosition(
        planet=planet,
        longitude=0.0,
        sign=sign,
        degree_in_sign=0.0,
        house=house,
        nakshatra=_DUMMY_NAKSHATRA,
        retrograde=False,
    )


# ---- Kalasarpa Dosha ----

_SEVEN_CLASSICAL = [
    Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY,
    Planet.JUPITER, Planet.VENUS, Planet.SATURN,
]


def test_kalasarpa_dosha_flagged_when_all_planets_on_one_side() -> None:
    # Rahu house 1, Ketu house 7; all 7 classical planets in houses 2-6 -
    # entirely on Rahu's forward side.
    planets = [_planet(p, house=2 + i % 5) for i, p in enumerate(_SEVEN_CLASSICAL)]
    planets.append(_planet(Planet.RAHU, house=1))
    planets.append(_planet(Planet.KETU, house=7))
    result = compute_kalasarpa_dosha(planets)
    assert result.has_dosha is True
    assert result.dosha_type == "Anant Kalasarpa Dosha"
    assert result.rahu_house == 1


def test_kalasarpa_dosha_not_flagged_when_a_planet_is_outside_the_axis() -> None:
    planets = [_planet(p, house=2 + i % 5) for i, p in enumerate(_SEVEN_CLASSICAL)]
    planets[-1] = _planet(Planet.SATURN, house=8)  # Ketu's side, breaks the axis
    planets.append(_planet(Planet.RAHU, house=1))
    planets.append(_planet(Planet.KETU, house=7))
    result = compute_kalasarpa_dosha(planets)
    assert result.has_dosha is False
    assert result.dosha_type is None


def test_kalasarpa_dosha_type_matches_rahus_house() -> None:
    planets = [_planet(p, house=6 + i % 5) for i, p in enumerate(_SEVEN_CLASSICAL)]
    planets.append(_planet(Planet.RAHU, house=5))
    planets.append(_planet(Planet.KETU, house=11))
    result = compute_kalasarpa_dosha(planets)
    assert result.has_dosha is True
    assert result.dosha_type == "Padma Kalasarpa Dosha"


# ---- Kuja Dosha (3-reference-point) ----


def test_kuja_dosha_lagna_only_gives_high_manglik() -> None:
    planets = [
        _planet(Planet.MARS, house=1, sign=Sign.CANCER),
        _planet(Planet.MOON, house=1, sign=Sign.TAURUS),
        _planet(Planet.VENUS, house=1, sign=Sign.TAURUS),
    ]
    result = compute_kuja_dosha(planets, ascendant_sign=Sign.ARIES)
    by_reference = {rp.reference: rp for rp in result.reference_points}
    assert by_reference["Lagna"].has_dosha is True
    assert by_reference["Lagna"].mars_house == 4
    assert by_reference["Moon"].has_dosha is False
    assert by_reference["Venus"].has_dosha is False
    assert result.overall_classification == "High/Full Manglik"


def test_kuja_dosha_moon_only_gives_low_manglik() -> None:
    planets = [
        _planet(Planet.MARS, house=1, sign=Sign.CANCER),
        _planet(Planet.MOON, house=1, sign=Sign.ARIES),
        _planet(Planet.VENUS, house=1, sign=Sign.TAURUS),
    ]
    result = compute_kuja_dosha(planets, ascendant_sign=Sign.TAURUS)
    by_reference = {rp.reference: rp for rp in result.reference_points}
    assert by_reference["Lagna"].has_dosha is False
    assert by_reference["Moon"].has_dosha is True
    assert by_reference["Moon"].mars_house == 4
    assert by_reference["Venus"].has_dosha is False
    assert result.overall_classification == "Low/Partial Manglik"


def test_kuja_dosha_none_triggered_gives_not_manglik() -> None:
    planets = [
        _planet(Planet.MARS, house=1, sign=Sign.CANCER),
        _planet(Planet.MOON, house=1, sign=Sign.TAURUS),
        _planet(Planet.VENUS, house=1, sign=Sign.TAURUS),
    ]
    result = compute_kuja_dosha(planets, ascendant_sign=Sign.TAURUS)
    assert all(not rp.has_dosha for rp in result.reference_points)
    assert result.overall_classification == "Not Manglik"


# ---- Guru Chandala Dosha ----


def test_guru_chandala_dosha_flagged_when_conjunct() -> None:
    planets = [_planet(Planet.JUPITER, house=6), _planet(Planet.RAHU, house=6)]
    result = compute_guru_chandala_dosha(planets, aspects=[])
    assert result.has_dosha is True
    assert result.is_conjunction is True


def test_guru_chandala_dosha_flagged_via_jupiters_own_aspect() -> None:
    # Jupiter aspects 5th/7th/9th from itself; house 1 + 6 = 7th aspect.
    planets = [_planet(Planet.JUPITER, house=1), _planet(Planet.RAHU, house=7)]
    aspects = [
        PlanetAspect(
            source_planet=Planet.JUPITER, source_house=1,
            target_planet=Planet.RAHU, target_house=7, is_special=False,
        )
    ]
    result = compute_guru_chandala_dosha(planets, aspects)
    assert result.has_dosha is True
    assert result.is_conjunction is False


def test_guru_chandala_dosha_not_flagged_when_unrelated() -> None:
    planets = [_planet(Planet.JUPITER, house=1), _planet(Planet.RAHU, house=2)]
    result = compute_guru_chandala_dosha(planets, aspects=[])
    assert result.has_dosha is False
