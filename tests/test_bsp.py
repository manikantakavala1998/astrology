from vedic_astro.aspects import compute_aspects
from vedic_astro.bsp import (
    compute_bsp_aries_spoilt, compute_bsp_house_notes, compute_bsp_rules, compute_bsp_venus_reveals,
)
from vedic_astro.models import NakshatraPlacement, Planet, PlanetPosition, Sign

_DUMMY_NAKSHATRA = NakshatraPlacement(name="Ashwini", index=1, pada=1, lord=Planet.KETU)
_SIGN_INDEX = {s: i for i, s in enumerate(Sign)}


def _planet(
    planet: Planet, sign: Sign, house: int, degree_in_sign: float = 15.0, retrograde: bool = False
) -> PlanetPosition:
    return PlanetPosition(
        planet=planet,
        longitude=_SIGN_INDEX[sign] * 30 + degree_in_sign,
        sign=sign,
        degree_in_sign=degree_in_sign,
        house=house,
        nakshatra=_DUMMY_NAKSHATRA,
        retrograde=retrograde,
    )


def _by_rule(results: list, number: int):  # type: ignore[no-untyped-def]
    return next(r for r in results if r.rule_number == number)


def _neutral_baseline_planets() -> list[PlanetPosition]:
    """Ascendant Cancer; every rule-relevant planet placed with neutral
    dignity, outside kendra/trikona, and not aspecting house 1 or house 4
    (the Ascendant lord Moon's house) - verified by hand. No BSP rule should
    have special status against this baseline."""
    return [
        _planet(Planet.SUN, Sign.VIRGO, house=3),
        _planet(Planet.MOON, Sign.LIBRA, house=4),
        _planet(Planet.MARS, Sign.TAURUS, house=11),
        _planet(Planet.MERCURY, Sign.VIRGO, house=3),
        _planet(Planet.JUPITER, Sign.TAURUS, house=11),
        _planet(Planet.VENUS, Sign.VIRGO, house=3),
        _planet(Planet.SATURN, Sign.GEMINI, house=12),
        _planet(Planet.RAHU, Sign.GEMINI, house=12),
        _planet(Planet.KETU, Sign.SAGITTARIUS, house=6),
    ]


def test_no_rule_applies_to_the_neutral_baseline() -> None:
    planets = _neutral_baseline_planets()
    aspects = compute_aspects(planets)
    results = compute_bsp_rules(Sign.CANCER, planets, aspects)

    assert len(results) == 6
    assert all(not r.special_status for r in results)
    assert all(r.affected_house_from_lagna is None for r in results)


def test_rule6_applies_when_mars_is_in_the_ascendant() -> None:
    planets = _neutral_baseline_planets()
    planets = [p for p in planets if p.planet != Planet.MARS]
    planets.append(_planet(Planet.MARS, Sign.CANCER, house=1))  # Cancer = house 1 here
    aspects = compute_aspects(planets)
    results = compute_bsp_rules(Sign.CANCER, planets, aspects)

    rule6 = _by_rule(results, 6)
    assert rule6.special_status
    assert any("is in the Ascendant" in r for r in rule6.special_status_reasons)
    assert rule6.age == 27
    # 10th from Mars's own house (1) = house 10.
    assert rule6.affected_house_from_lagna == 10


def test_rule6_does_not_apply_for_martian_ascendant_trigger_when_lagna_is_occupied() -> None:
    # Aries ascendant (a Mars-ruled sign) but with Sun sitting in the Ascendant
    # too - the "no planets in the Ascendant" precondition should then fail,
    # and nothing else here gives Mars special status either.
    planets = [
        _planet(Planet.SUN, Sign.ARIES, house=1),
        _planet(Planet.MOON, Sign.LIBRA, house=7),
        _planet(Planet.MARS, Sign.LEO, house=5),
        _planet(Planet.MERCURY, Sign.PISCES, house=12),
        _planet(Planet.JUPITER, Sign.GEMINI, house=3),
        _planet(Planet.VENUS, Sign.PISCES, house=12),
        _planet(Planet.SATURN, Sign.GEMINI, house=3),
        _planet(Planet.RAHU, Sign.CANCER, house=4),
        _planet(Planet.KETU, Sign.CAPRICORN, house=10),
    ]
    aspects = compute_aspects(planets)
    results = compute_bsp_rules(Sign.ARIES, planets, aspects)
    rule6 = _by_rule(results, 6)
    # Mars in Leo/house5 is a trikona house, so this actually DOES trigger
    # special status via the kendra/trikona bullet - a good reminder these
    # bullets are independent ORs. Assert on the specific unwanted reason
    # instead of overall special_status.
    assert not any("no planets in the Ascendant" in r for r in rule6.special_status_reasons)


def test_rule9_applies_via_luminary_conjunction() -> None:
    planets = _neutral_baseline_planets()
    planets = [p for p in planets if p.planet not in (Planet.KETU, Planet.MOON)]
    # Put Ketu conjunct Moon in house 9 (neither kendra/trikona-triggering
    # for Ketu is avoided: 9 IS trikona, so use house 11 instead to isolate
    # the luminary-conjunction bullet specifically).
    planets.append(_planet(Planet.MOON, Sign.LIBRA, house=4))
    planets.append(_planet(Planet.KETU, Sign.TAURUS, house=11))
    planets.append(_planet(Planet.SUN, Sign.TAURUS, house=11))
    planets = [p for p in planets if not (p.planet == Planet.SUN and p.house == 6)]
    aspects = compute_aspects(planets)
    results = compute_bsp_rules(Sign.CANCER, planets, aspects)

    rule9 = _by_rule(results, 9)
    assert rule9.special_status
    assert any("conjunct a luminary" in r for r in rule9.special_status_reasons)
    assert rule9.age == 24
    # 12th from Ketu's own house (11) = house 10.
    assert rule9.affected_house_from_lagna == 10


def test_rule10_applies_when_jupiter_is_ascendant_lord() -> None:
    # Sagittarius ascendant -> Jupiter is Ascendant lord, satisfying rule 10/11's trigger.
    planets = _neutral_baseline_planets()
    planets = [p for p in planets if p.planet != Planet.JUPITER]
    planets.append(_planet(Planet.JUPITER, Sign.TAURUS, house=6))  # Taurus = 6th from Sagittarius
    aspects = compute_aspects(planets)
    results = compute_bsp_rules(Sign.SAGITTARIUS, planets, aspects)

    rule10 = _by_rule(results, 10)
    assert rule10.special_status
    assert any("Ascendant lord" in r for r in rule10.special_status_reasons)
    assert rule10.age == 40
    # 9th from Jupiter's own house (6) = house 2.
    assert rule10.affected_house_from_lagna == 2
    assert rule10.aspect_used == 9


def test_bsp1_saturns_karmic_house_is_4th_from_saturn() -> None:
    planets = [
        _planet(Planet.SATURN, Sign.LEO, house=5),
        _planet(Planet.JUPITER, Sign.GEMINI, house=3),
    ]
    notes = compute_bsp_house_notes(Sign.ARIES, planets)
    saturn_note = next(n for n in notes if n.rule_number == 1)
    assert saturn_note.house_from_lagna == 8  # 4th from house 5


def test_bsp2_jupiters_karmic_houses_are_10th_and_6th_from_jupiter() -> None:
    planets = [
        _planet(Planet.SATURN, Sign.LEO, house=5),
        _planet(Planet.JUPITER, Sign.GEMINI, house=3),
    ]
    notes = compute_bsp_house_notes(Sign.ARIES, planets)
    jupiter_notes = [n for n in notes if n.rule_number == 2]
    houses = {n.house_from_lagna for n in jupiter_notes}
    assert houses == {12, 8}  # 10th and 6th from house 3


def _dummy_saturn_jupiter() -> list[PlanetPosition]:
    return [
        _planet(Planet.SATURN, Sign.ARIES, house=10),
        _planet(Planet.JUPITER, Sign.GEMINI, house=12),
    ]


def test_bsp14_past_life_bhava_matches_the_articles_own_worked_examples() -> None:
    # Sri Ram: Cancer ascendant (zodiac number 4) -> Past Life House is house 4.
    notes = compute_bsp_house_notes(Sign.CANCER, _dummy_saturn_jupiter())
    plh = next(n for n in notes if n.rule_number == 14)
    assert plh.house_from_lagna == 4

    # Michael Jackson: Aquarius ascendant (zodiac number 11) -> house 11.
    notes = compute_bsp_house_notes(Sign.AQUARIUS, _dummy_saturn_jupiter())
    plh = next(n for n in notes if n.rule_number == 14)
    assert plh.house_from_lagna == 11

    # JFK: Virgo ascendant (zodiac number 6) -> house 6.
    notes = compute_bsp_house_notes(Sign.VIRGO, _dummy_saturn_jupiter())
    plh = next(n for n in notes if n.rule_number == 14)
    assert plh.house_from_lagna == 6


def test_bsp5_aries_spoilt_when_jupiter_and_saturn_are_conjunct() -> None:
    planets = [
        _planet(Planet.JUPITER, Sign.SAGITTARIUS, house=6),
        _planet(Planet.SATURN, Sign.SAGITTARIUS, house=6),
    ]
    # Ascendant Cancer: Aries is the 10th house from Cancer.
    result = compute_bsp_aries_spoilt(Sign.CANCER, planets)
    assert result is not None
    assert result.house_from_lagna == 10


def test_bsp5_none_when_jupiter_and_saturn_are_not_conjunct() -> None:
    planets = [
        _planet(Planet.JUPITER, Sign.SAGITTARIUS, house=6),
        _planet(Planet.SATURN, Sign.CAPRICORN, house=7),
    ]
    assert compute_bsp_aries_spoilt(Sign.CANCER, planets) is None


def test_bsp15_venus_reveals_conjunction_and_twelfth_house() -> None:
    planets = [
        _planet(Planet.VENUS, Sign.LEO, house=5),
        _planet(Planet.SUN, Sign.LEO, house=5),
    ]
    result = compute_bsp_venus_reveals(Sign.ARIES, planets)
    assert result.venus_house_from_lagna == 5
    assert result.conjunct_planets == [Planet.SUN]
    # Sun rules Leo, which is house 5 from Aries ascendant.
    assert result.conjunct_planet_lordships["Sun"] == [5]
    # 12th from Venus's sign (Leo) is Cancer, which is house 4 from Aries ascendant.
    assert result.twelfth_from_venus_sign == Sign.CANCER
    assert result.twelfth_from_venus_house_from_lagna == 4


def test_rule13_applies_when_saturn_is_exalted() -> None:
    planets = _neutral_baseline_planets()
    planets = [p for p in planets if p.planet != Planet.SATURN]
    planets.append(_planet(Planet.SATURN, Sign.LIBRA, house=11))  # exalted, non-kendra/trikona house
    aspects = compute_aspects(planets)
    results = compute_bsp_rules(Sign.CANCER, planets, aspects)

    rule13 = _by_rule(results, 13)
    assert rule13.special_status
    assert any("dignity" in r for r in rule13.special_status_reasons)
    assert rule13.age == 20
    assert rule13.aspect_used == 3
    # 3rd from Saturn's own house (11) = house 1.
    assert rule13.affected_house_from_lagna == 1
