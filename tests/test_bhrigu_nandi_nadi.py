from datetime import date, time

from vedic_astro.bhrigu_nandi_nadi import (
    compute_bhrigu_nandi_nadi,
    compute_bnn_career_sequence,
    compute_bnn_karaka_readings,
    compute_bnn_marriage_timing,
    compute_bnn_short_life_indication,
    compute_bnn_sibling_count,
)
from vedic_astro.models import BirthData, NakshatraPlacement, NodeType, Planet, PlanetPosition, Sign
from vedic_astro.ephemeris import planet_positions

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
    """Chart 1's actual sign placements, printed pages 9-13.

    The source does not give degrees; 15 degrees is a test placeholder,
    so within-sign ordering here is not a claim about the original chart.
    Rahu/Gemini and Ketu/Sagittarius are opposite. Sun/Venus are in Virgo,
    Saturn/Mercury in Libra, Mars in Aries, Jupiter alone in Capricorn.
    """
    return [
        _planet(Planet.JUPITER, Sign.CAPRICORN),
        _planet(Planet.KETU, Sign.SAGITTARIUS),
        _planet(Planet.MOON, Sign.SAGITTARIUS),
        _planet(Planet.MARS, Sign.ARIES),
        _planet(Planet.RAHU, Sign.GEMINI),
        _planet(Planet.SUN, Sign.VIRGO),
        _planet(Planet.SATURN, Sign.LIBRA),
        _planet(Planet.MERCURY, Sign.LIBRA),
        _planet(Planet.VENUS, Sign.VIRGO),
    ]


def test_sibling_count_matches_chart_1() -> None:
    result = compute_bnn_sibling_count(_chart1_planets())

    assert result.elder_planet == Planet.MOON
    assert result.elder_indicator_count == 1
    assert result.elder_planets == [Planet.MOON]
    assert result.elder_count is None
    assert result.younger_count is None
    assert result.elder_gender_breakdown == {"brothers": 0, "sisters": 1, "unclassified": 0}

    assert result.younger_planets == [
        Planet.MARS, Planet.RAHU, Planet.SUN, Planet.VENUS, Planet.MERCURY, Planet.SATURN,
    ]
    assert result.younger_indicator_count == 6
    # Mars/Rahu/Sun/Saturn/Mercury = brothers, Venus = sister - matches the
    # book's own count of "five younger brothers... one younger sister".
    assert result.younger_gender_breakdown == {"brothers": 5, "sisters": 1, "unclassified": 0}


def test_sibling_count_no_elder_when_previous_sign_empty() -> None:
    planets = _chart1_planets()
    planets = [p for p in planets if p.planet != Planet.MOON] + [_planet(Planet.MOON, Sign.LIBRA)]
    result = compute_bnn_sibling_count(planets)
    assert result.elder_planet is None
    assert result.elder_indicator_count == 0
    assert result.elder_count is None


def test_karaka_readings_cover_all_nine_planets() -> None:
    readings = compute_bnn_karaka_readings(_chart1_planets())
    assert {r.karaka for r in readings} == set(Planet)

    jupiter_reading = next(r for r in readings if r.karaka == Planet.JUPITER)
    assert jupiter_reading.sign == Sign.CAPRICORN
    assert jupiter_reading.dispositor == Planet.SATURN
    # Saturn, Jupiter's dispositor, is in Libra: house 10 from Capricorn.
    assert jupiter_reading.dispositor_house_from_karaka == 10


def test_marriage_timing_round_arithmetic() -> None:
    result = compute_bnn_marriage_timing(_chart1_planets(), max_age=50)
    # Inclusive house ordinals: Capricorn to Virgo is 9, recurring every 12 years.
    assert result.male_native.spouse_karaka == Planet.VENUS
    assert result.male_native.ages == [9, 21, 33, 45]
    # Capricorn to Aries is house 4 in the schematic convention.
    assert result.female_native.spouse_karaka == Planet.MARS
    assert result.female_native.ages == [4, 16, 28, 40]


def test_short_life_indication_false_when_jupiter_has_neighbors() -> None:
    result = compute_bnn_short_life_indication(_chart1_planets())
    # Jupiter's previous sign contains Moon/Ketu, so it is not isolated.
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
    # Saturn/Libra must also contact Sun/Venus in its previous sign, Virgo.
    assert result.planets_in_order == [
        Planet.MOON, Planet.KETU, Planet.JUPITER, Planet.MARS,
        Planet.RAHU, Planet.SUN, Planet.VENUS,
    ]
    assert result.ages == [7.5, 7.5, 10.0, 17.5, 22.5, 30.0, 30.0]


def test_compute_bhrigu_nandi_nadi_wires_everything_together() -> None:
    result = compute_bhrigu_nandi_nadi(_chart1_planets())
    assert result.jupiter_as_lagna_houses[1] == Sign.CAPRICORN
    assert result.jupiter_as_lagna_houses[2] == Sign.AQUARIUS
    assert len(result.karaka_readings) == 9
    assert result.sibling_count.elder_planet == Planet.MOON



def test_multiple_previous_sign_indicators_are_all_preserved() -> None:
    planets = [p for p in _chart1_planets() if p.planet != Planet.VENUS]
    planets.append(_planet(Planet.VENUS, Sign.SAGITTARIUS, degree_in_sign=20))
    result = compute_bnn_sibling_count(planets)
    assert result.elder_planets == [Planet.MOON, Planet.VENUS]
    assert result.elder_indicator_count == 2
    assert result.elder_gender_breakdown["sisters"] == 2
    assert result.elder_count is None  # Planetary markers are not people.


def test_bnn_readings_do_not_depend_on_input_list_order() -> None:
    planets = _chart1_planets()
    assert compute_bhrigu_nandi_nadi(planets) == compute_bhrigu_nandi_nadi(list(reversed(planets)))


def test_same_sign_contacts_follow_degree_order() -> None:
    planets = [p for p in _chart1_planets() if p.planet not in {Planet.MERCURY, Planet.SATURN}]
    planets.extend([
        _planet(Planet.MERCURY, Sign.LIBRA, 25),
        _planet(Planet.SATURN, Sign.LIBRA, 5),
    ])
    result = compute_bnn_sibling_count(planets)
    assert result.younger_planets[-2:] == [Planet.SATURN, Planet.MERCURY]


def test_ketu_contact_has_no_invented_gender() -> None:
    planets = [p for p in _chart1_planets() if p.planet != Planet.KETU]
    planets.append(_planet(Planet.KETU, Sign.PISCES))
    result = compute_bnn_sibling_count(planets)
    assert Planet.KETU in result.younger_planets
    assert result.younger_gender_breakdown["unclassified"] == 1
    assert sum(result.younger_gender_breakdown.values()) == result.younger_indicator_count


def test_career_contacts_outside_horizon_have_no_fabricated_age() -> None:
    result = compute_bnn_career_sequence(_chart1_planets(), max_age=8)
    assert result.planets_in_order == [Planet.MOON, Planet.KETU]
    assert result.ages == [7.5, 7.5]
    assert compute_bnn_career_sequence(_chart1_planets(), max_age=1).ages == []


def test_september_1998_regression_does_not_mislabel_sisters_as_younger() -> None:
    # Reported counterexample: two ELDER sisters. The previous implementation
    # said 0 elders and 7 younger siblings. Never fit an unverified rule to this
    # birth: report unknown birth order and expose the actual planetary evidence.
    birth = BirthData(
        birth_date=date(1998, 9, 4), birth_time=time(0, 3),
        latitude=17.00517, longitude=81.77784, utc_offset_hours=5.5,
    )
    assert birth.utc_datetime.isoformat() == '1998-09-03T18:33:00'
    raw = planet_positions(birth.utc_datetime, 'lahiri', NodeType.MEAN)
    planets = [
        _planet(planet, list(Sign)[int(pos.longitude // 30)], pos.longitude % 30, pos.retrograde)
        for planet, pos in raw.items()
    ]
    result = compute_bnn_sibling_count(planets)
    assert result.jupiter_sign == Sign.PISCES
    assert result.jupiter_retrograde is True
    assert result.retrograde_context_sign == Sign.AQUARIUS
    assert result.count_status == 'undetermined'
    assert result.elder_count is None and result.younger_count is None
    assert [(p.planet, p.sign, p.house_from_jupiter, p.house_from_mars,
             p.house_from_retrograde_context) for p in result.sister_indicators] == [
        (Planet.MOON, Sign.CAPRICORN, 11, 7, 12),
        (Planet.VENUS, Sign.LEO, 6, 2, 7),
    ]
    serialized = result.model_dump(mode='json')
    assert serialized['elder_count'] is None and serialized['younger_count'] is None
    assert 'two significators do not prove two sisters' in ' '.join(result.notes)


def test_direct_jupiter_has_no_previous_sign_projection() -> None:
    result = compute_bnn_sibling_count(_chart1_planets())
    assert result.retrograde_context_sign is None
    assert all(p.house_from_retrograde_context is None for p in result.sister_indicators)
