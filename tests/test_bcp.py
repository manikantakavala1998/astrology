from vedic_astro.bcp import MAX_DEFINED_AGE, compute_bcp_longevity, compute_bhrigu_chakra
from vedic_astro.models import NakshatraPlacement, Planet, PlanetPosition, Sign

_DUMMY_NAKSHATRA = NakshatraPlacement(name="Ashwini", index=1, pada=1, lord=Planet.KETU)
_SIGN_INDEX = {s: i for i, s in enumerate(Sign)}


def _planet(planet: Planet, sign: Sign, degree_in_sign: float = 10.0, house: int = 1) -> PlanetPosition:
    return PlanetPosition(
        planet=planet,
        longitude=_SIGN_INDEX[sign] * 30 + degree_in_sign,
        sign=sign,
        degree_in_sign=degree_in_sign,
        house=house,
        nakshatra=_DUMMY_NAKSHATRA,
        retrograde=False,
    )


def _all_nine_planets(moon_sign: Sign = Sign.ARIES) -> list[PlanetPosition]:
    """One planet per sign starting from Aries, except Moon is placed at
    `moon_sign` (Aries by default) so cycle-ruler-from-Moon tests can vary it."""
    return [
        _planet(Planet.SUN, Sign.LEO),
        _planet(Planet.MOON, moon_sign),
        _planet(Planet.MARS, Sign.SCORPIO),
        _planet(Planet.MERCURY, Sign.GEMINI),
        _planet(Planet.JUPITER, Sign.SAGITTARIUS),
        _planet(Planet.VENUS, Sign.LIBRA),
        _planet(Planet.SATURN, Sign.CAPRICORN),
        _planet(Planet.RAHU, Sign.CANCER),
        _planet(Planet.KETU, Sign.CAPRICORN),
    ]


def test_house_from_lagna_progresses_one_house_per_year_and_repeats_every_12() -> None:
    rows = compute_bhrigu_chakra(Sign.ARIES, _all_nine_planets(), max_age=30)
    by_age = {r.age: r for r in rows}

    assert by_age[1].house_from_lagna == 1
    assert by_age[1].sign_from_lagna == Sign.ARIES
    assert by_age[12].house_from_lagna == 12
    assert by_age[12].sign_from_lagna == Sign.PISCES
    # 13th year starts the 2nd round again from the 1st house (per the article).
    assert by_age[13].house_from_lagna == 1
    assert by_age[13].sign_from_lagna == Sign.ARIES
    assert by_age[25].house_from_lagna == 1  # 3rd round


def test_cycle_ruler_sequence_matches_the_articles_fixed_order() -> None:
    rows = compute_bhrigu_chakra(Sign.ARIES, _all_nine_planets(), max_age=MAX_DEFINED_AGE)
    by_age = {r.age: r for r in rows}

    # cycle 1 (age 1-12) = Moon, cycle 2 (age 13-24) = Mercury, ... cycle 9 (97-108) = Ketu.
    assert by_age[1].cycle_ruler == Planet.MOON
    assert by_age[12].cycle_ruler == Planet.MOON
    assert by_age[13].cycle_ruler == Planet.MERCURY
    assert by_age[36].cycle_ruler == Planet.VENUS
    assert by_age[48].cycle_ruler == Planet.SUN
    assert by_age[60].cycle_ruler == Planet.MARS
    assert by_age[72].cycle_ruler == Planet.JUPITER
    assert by_age[84].cycle_ruler == Planet.SATURN
    assert by_age[96].cycle_ruler == Planet.RAHU
    assert by_age[108].cycle_ruler == Planet.KETU


def test_cycle_ruler_is_none_past_age_108_since_source_defines_only_9_cycles() -> None:
    rows = compute_bhrigu_chakra(Sign.ARIES, _all_nine_planets(), max_age=120)
    by_age = {r.age: r for r in rows}

    assert by_age[108].cycle_ruler == Planet.KETU
    assert by_age[109].cycle_ruler is None
    assert by_age[109].house_from_cycle_ruler is None
    assert by_age[109].sign_from_cycle_ruler is None
    assert by_age[109].planets_from_cycle_ruler == []
    # The classical Lagna-only house still applies past age 108.
    assert by_age[109].house_from_lagna == 1


def test_house_from_cycle_ruler_counts_from_the_rulers_own_natal_sign() -> None:
    # Moon (cycle 1's ruler) is natally in Cancer here, not Aries lagna.
    rows = compute_bhrigu_chakra(Sign.ARIES, _all_nine_planets(moon_sign=Sign.CANCER), max_age=12)
    year_5 = next(r for r in rows if r.age == 5)

    assert year_5.cycle_ruler == Planet.MOON
    assert year_5.house_from_cycle_ruler == 5
    # 5th house counted from Cancer (Moon's own sign) = Cancer, Leo, Virgo, Libra, Scorpio.
    assert year_5.sign_from_cycle_ruler == Sign.SCORPIO
    # Mars (in Scorpio per _all_nine_planets) should show up in that house.
    assert Planet.MARS in year_5.planets_from_cycle_ruler


def test_planets_from_lagna_lists_occupants_of_the_activated_sign() -> None:
    rows = compute_bhrigu_chakra(Sign.ARIES, _all_nine_planets(), max_age=5)
    year_5 = next(r for r in rows if r.age == 5)
    # Year 5 = 5th house from Aries lagna = Leo, where Sun sits.
    assert year_5.sign_from_lagna == Sign.LEO
    assert year_5.planets_from_lagna == [Planet.SUN]


def test_bcp_longevity_rule1_when_ascendant_is_occupied() -> None:
    # Ascendant Aries, occupied by Jupiter -> Rule 1: watch Saturn's house.
    planets = [
        _planet(Planet.JUPITER, Sign.ARIES, house=1),
        _planet(Planet.MOON, Sign.CANCER, house=4),
        _planet(Planet.SATURN, Sign.AQUARIUS, house=11),
    ]
    result = compute_bcp_longevity(Sign.ARIES, planets, max_age=48)

    assert result.rule == "Rule 1"
    assert len(result.flagged_houses) == 1
    saturn_house = result.flagged_houses[0]
    assert saturn_house.house_from_lagna == 11
    assert saturn_house.sign == Sign.AQUARIUS
    assert saturn_house.ages == [11, 23, 35, 47]


def test_bcp_longevity_rule2_when_ascendant_is_vacant() -> None:
    # Ascendant Aries, nothing in house 1 -> Rule 2: Moon's house + 5th/6th/8th from Moon.
    planets = [
        _planet(Planet.MOON, Sign.VIRGO, house=6),
        _planet(Planet.SATURN, Sign.SCORPIO, house=8),
    ]
    result = compute_bcp_longevity(Sign.ARIES, planets, max_age=24)

    assert result.rule == "Rule 2"
    by_label = {h.label: h for h in result.flagged_houses}
    assert set(by_label) == {
        "Moon's house from Lagna", "5th house from the Moon",
        "6th house from the Moon", "8th house from the Moon",
    }

    assert by_label["Moon's house from Lagna"].house_from_lagna == 6
    assert by_label["Moon's house from Lagna"].sign == Sign.VIRGO

    # 5th/6th/8th counted from Moon's own sign (Virgo), not from house 6.
    assert by_label["5th house from the Moon"].sign == Sign.CAPRICORN
    assert by_label["5th house from the Moon"].house_from_lagna == 10
    assert by_label["6th house from the Moon"].sign == Sign.AQUARIUS
    assert by_label["6th house from the Moon"].house_from_lagna == 11
    assert by_label["8th house from the Moon"].sign == Sign.ARIES
    assert by_label["8th house from the Moon"].house_from_lagna == 1
