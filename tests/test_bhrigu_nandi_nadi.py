from vedic_astro.bhrigu_nandi_nadi import (
    compute_bhrigu_nandi_nadi,
    compute_bnn_career_sequence,
    compute_bnn_karaka_readings,
    compute_bnn_marriage_timing,
    compute_bnn_short_life_indication,
    compute_bnn_sibling_count,
)
from vedic_astro.models import NakshatraPlacement, Planet, PlanetPosition, Sign

_DUMMY_NAKSHATRA = NakshatraPlacement(name="Ashwini", index=1, pada=1, lord=Planet.KETU)
_SIGN_INDEX = {s: i for i, s in enumerate(Sign)}


def _planet(planet: Planet, sign: Sign, degree_in_sign: float = 15.0, retrograde: bool = False) -> PlanetPosition:
    return PlanetPosition(
        planet=planet,
        longitude=_SIGN_INDEX[sign] * 30 + degree_in_sign,
        sign=sign,
        degree_in_sign=degree_in_sign,
        house=1,
        nakshatra=_DUMMY_NAKSHATRA,
        retrograde=retrograde,
    )


def _chart1_planets() -> list[PlanetPosition]:
    """R.G. Rao's "Bhrigu Nandi Nadi", Chart 1 (PAGE 6): Jupiter alone in
    Capricorn, Moon in the previous sign (Sagittarius, elder sister), and
    Jupiter's forward transit in its first round crosses Mars, Rahu, Sun,
    Saturn, Mercury (five younger brothers) then Venus (one younger
    sister) - verified against the book's own text, not guessed. Ketu is
    placed conjunct Jupiter (its position isn't given in the text, and Rahu/
    Ketu must be exactly opposite each other, so it's placed outside both
    the elder-slot and the crossing sweep to avoid asserting an unverified
    answer to whether Ketu itself would count as a sibling)."""
    return [
        _planet(Planet.JUPITER, Sign.CAPRICORN),
        _planet(Planet.KETU, Sign.CAPRICORN),
        _planet(Planet.MOON, Sign.SAGITTARIUS),
        _planet(Planet.MARS, Sign.AQUARIUS),
        _planet(Planet.RAHU, Sign.PISCES),
        _planet(Planet.SUN, Sign.ARIES),
        _planet(Planet.SATURN, Sign.TAURUS),
        _planet(Planet.MERCURY, Sign.GEMINI),
        _planet(Planet.VENUS, Sign.CANCER),
    ]


def test_sibling_count_matches_chart_1() -> None:
    result = compute_bnn_sibling_count(_chart1_planets())

    assert result.elder_planet == Planet.MOON
    assert result.elder_count == 1
    assert result.elder_gender_breakdown == {"brothers": 0, "sisters": 1}

    assert result.younger_planets == [
        Planet.MARS, Planet.RAHU, Planet.SUN, Planet.SATURN, Planet.MERCURY, Planet.VENUS,
    ]
    assert result.younger_count == 6
    # Mars/Rahu/Sun/Saturn/Mercury = brothers, Venus = sister - matches the
    # book's own count of "five younger brothers... one younger sister".
    assert result.younger_gender_breakdown == {"brothers": 5, "sisters": 1}


def test_sibling_count_no_elder_when_previous_sign_empty() -> None:
    planets = _chart1_planets()
    planets = [p for p in planets if p.planet != Planet.MOON] + [_planet(Planet.MOON, Sign.LIBRA)]
    result = compute_bnn_sibling_count(planets)
    assert result.elder_planet is None
    assert result.elder_count == 0


def test_karaka_readings_cover_all_nine_planets() -> None:
    readings = compute_bnn_karaka_readings(_chart1_planets())
    assert {r.karaka for r in readings} == set(Planet)

    jupiter_reading = next(r for r in readings if r.karaka == Planet.JUPITER)
    assert jupiter_reading.sign == Sign.CAPRICORN
    assert jupiter_reading.dispositor == Planet.SATURN
    # Saturn (Jupiter's dispositor) sits in Taurus, which is house 5 counted
    # forward from Jupiter's own sign (Capricorn=1, Aquarius=2, ... Taurus=5).
    assert jupiter_reading.dispositor_house_from_karaka == 5


def test_marriage_timing_round_arithmetic() -> None:
    result = compute_bnn_marriage_timing(_chart1_planets(), max_age=50)
    # Jupiter (Capricorn) to Venus (Cancer) is 7 signs forward -> first
    # occurrence age 7, recurring every 12 years.
    assert result.male_native.spouse_karaka == Planet.VENUS
    assert result.male_native.ages == [7, 19, 31, 43]
    # Jupiter (Capricorn) to Mars (Aquarius) is 2 signs forward.
    assert result.female_native.spouse_karaka == Planet.MARS
    assert result.female_native.ages == [2, 14, 26, 38, 50]


def test_short_life_indication_false_when_jupiter_has_neighbors() -> None:
    result = compute_bnn_short_life_indication(_chart1_planets())
    # Jupiter's 2nd (Aquarius/Mars), 12th (Sagittarius/Moon) and 7th
    # (Cancer/Venus) are all occupied here, so it is not "bare".
    assert result.jupiter_bare is False


def test_short_life_indication_true_when_jupiter_isolated() -> None:
    planets = [
        _planet(Planet.JUPITER, Sign.CAPRICORN),
        _planet(Planet.SATURN, Sign.CAPRICORN),
        _planet(Planet.SUN, Sign.VIRGO),
        _planet(Planet.MOON, Sign.VIRGO),
        _planet(Planet.MARS, Sign.VIRGO),
        _planet(Planet.MERCURY, Sign.VIRGO),
        _planet(Planet.VENUS, Sign.VIRGO),
        _planet(Planet.RAHU, Sign.VIRGO),
        _planet(Planet.KETU, Sign.PISCES),
    ]
    result = compute_bnn_short_life_indication(planets)
    assert result.jupiter_bare is True
    assert result.saturn_bare is True


def test_career_sequence_orders_planets_by_forward_crossing() -> None:
    result = compute_bnn_career_sequence(_chart1_planets(), max_age=50)
    # Saturn is in Taurus; forward crossing (excluding only the 12th/
    # previous sign, Aries/Sun, and Saturn itself) reaches Gemini(Mercury),
    # Cancer(Venus), Sagittarius(Moon), Capricorn(Jupiter, Ketu),
    # Aquarius(Mars), Pisces(Rahu) in that order.
    assert result.planets_in_order == [
        Planet.MERCURY, Planet.VENUS, Planet.MOON,
        Planet.JUPITER, Planet.KETU, Planet.MARS, Planet.RAHU,
    ]
    assert len(result.ages) == len(result.planets_in_order)


def test_compute_bhrigu_nandi_nadi_wires_everything_together() -> None:
    result = compute_bhrigu_nandi_nadi(_chart1_planets())
    assert result.jupiter_as_lagna_houses[1] == Sign.CAPRICORN
    assert result.jupiter_as_lagna_houses[2] == Sign.AQUARIUS
    assert len(result.karaka_readings) == 9
    assert result.sibling_count.elder_planet == Planet.MOON
