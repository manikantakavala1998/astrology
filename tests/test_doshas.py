import pytest

from vedic_astro.doshas import compute_punarphoo_dosha, compute_saturn_afflictions, compute_shani_dosha
from vedic_astro.models import NakshatraPlacement, Planet, PlanetAspect, PlanetPosition, Sign

_DUMMY_NAKSHATRA = NakshatraPlacement(name="Ashwini", index=1, pada=1, lord=Planet.KETU)


def _planet(
    planet: Planet,
    house: int,
    sign: Sign = Sign.CAPRICORN,
    nakshatra_lord: Planet = Planet.KETU,
) -> PlanetPosition:
    return PlanetPosition(
        planet=planet,
        longitude=0.0,
        sign=sign,
        degree_in_sign=0.0,
        house=house,
        nakshatra=NakshatraPlacement(name="Ashwini", index=1, pada=1, lord=nakshatra_lord),
        retrograde=False,
    )


def _chart_with_saturn(house: int, sign: Sign = Sign.CAPRICORN) -> list[PlanetPosition]:
    return [_planet(Planet.SATURN, house, sign)]


@pytest.mark.parametrize("house", [1, 4, 7, 8, 12])
def test_shani_dosha_flags_afflicted_houses(house: int) -> None:
    result = compute_shani_dosha(_chart_with_saturn(house))
    assert result.has_house_dosha is True
    assert result.house_reason  # non-empty, house-specific text


@pytest.mark.parametrize("house", [2, 3, 5, 6, 9, 10, 11])
def test_shani_dosha_does_not_flag_other_houses(house: int) -> None:
    result = compute_shani_dosha(_chart_with_saturn(house))
    assert result.has_house_dosha is False
    assert result.house_reason  # still always populated


def test_ashtama_shani_reason_mentions_ashtama_shani() -> None:
    result = compute_shani_dosha(_chart_with_saturn(8))
    assert "Ashtama Shani" in result.house_reason


def test_shani_neech_dosha_flagged_when_saturn_in_aries() -> None:
    result = compute_shani_dosha(_chart_with_saturn(house=5, sign=Sign.ARIES))
    assert result.has_neech_dosha is True
    assert "Neech" in result.neech_reason


def test_shani_neech_dosha_not_flagged_in_own_sign() -> None:
    result = compute_shani_dosha(_chart_with_saturn(house=5, sign=Sign.CAPRICORN))
    assert result.has_neech_dosha is False


def test_shani_neech_dosha_reason_names_the_actual_sign_when_not_flagged() -> None:
    # Regression test: the non-debilitated message used to be fixed
    # boilerplate ("Saturn is not debilitated (not in Aries)") with no
    # indication it was computed from this chart's actual data - two
    # different people whose Saturn just happens to not be in Aries would
    # see byte-identical text, which read as suspicious/copy-pasted even
    # though the underlying flag was correctly computed either way.
    result = compute_shani_dosha(_chart_with_saturn(house=5, sign=Sign.CAPRICORN))
    assert "Capricorn" in result.neech_reason


def test_both_doshas_can_apply_simultaneously() -> None:
    # Saturn in the 1st house AND in Aries - both findings should be
    # independently flagged, not mutually exclusive.
    result = compute_shani_dosha(_chart_with_saturn(house=1, sign=Sign.ARIES))
    assert result.has_house_dosha is True
    assert result.has_neech_dosha is True


def test_vish_dosha_flagged_when_saturn_and_moon_share_a_house() -> None:
    planets = [
        _planet(Planet.SATURN, house=5), _planet(Planet.MOON, house=5),
        _planet(Planet.MARS, house=9), _planet(Planet.RAHU, house=11),
    ]
    result = compute_saturn_afflictions(planets, aspects=[])
    assert result.vish_dosha.has_dosha is True
    assert result.vish_dosha.is_conjunction is True


def test_vish_dosha_flagged_via_aspect_not_conjunction() -> None:
    planets = [
        _planet(Planet.SATURN, house=1), _planet(Planet.MOON, house=7),
        _planet(Planet.MARS, house=9), _planet(Planet.RAHU, house=11),
    ]
    aspects = [
        PlanetAspect(
            source_planet=Planet.SATURN, source_house=1,
            target_planet=Planet.MOON, target_house=7, is_special=False,
        )
    ]
    result = compute_saturn_afflictions(planets, aspects)
    assert result.vish_dosha.has_dosha is True
    assert result.vish_dosha.is_conjunction is False


def test_vish_dosha_not_flagged_without_conjunction_or_aspect() -> None:
    planets = [
        _planet(Planet.SATURN, house=1), _planet(Planet.MOON, house=2),
        _planet(Planet.MARS, house=9), _planet(Planet.RAHU, house=11),
    ]
    result = compute_saturn_afflictions(planets, aspects=[])
    assert result.vish_dosha.has_dosha is False
    assert "No conjunction" in result.vish_dosha.reason


def test_shani_mangal_dosha_flagged_when_conjunct() -> None:
    planets = [
        _planet(Planet.SATURN, house=3), _planet(Planet.MARS, house=3),
        _planet(Planet.MOON, house=9), _planet(Planet.RAHU, house=11),
    ]
    result = compute_saturn_afflictions(planets, aspects=[])
    assert result.shani_mangal_dosha.has_dosha is True
    assert result.shani_mangal_dosha.is_conjunction is True


def test_shani_rahu_dosha_flagged_via_saturns_own_aspect_one_directional() -> None:
    # Rahu is never an aspect *source* in this engine (see aspects.py), so
    # this dosha can only trigger via Saturn's own aspect reaching Rahu, or
    # via same-house conjunction - never via a hypothetical Rahu->Saturn
    # aspect. This test confirms the one-directional entry alone is enough.
    planets = [
        _planet(Planet.SATURN, house=1), _planet(Planet.RAHU, house=7),
        _planet(Planet.MOON, house=9), _planet(Planet.MARS, house=11),
    ]
    aspects = [
        PlanetAspect(
            source_planet=Planet.SATURN, source_house=1,
            target_planet=Planet.RAHU, target_house=7, is_special=False,
        )
    ]
    result = compute_saturn_afflictions(planets, aspects)
    assert result.shani_rahu_dosha.has_dosha is True
    assert result.shani_rahu_dosha.is_conjunction is False


def test_shani_rahu_dosha_not_flagged_when_unrelated() -> None:
    planets = [
        _planet(Planet.SATURN, house=1), _planet(Planet.RAHU, house=2),
        _planet(Planet.MOON, house=9), _planet(Planet.MARS, house=11),
    ]
    result = compute_saturn_afflictions(planets, aspects=[])
    assert result.shani_rahu_dosha.has_dosha is False


def test_all_three_pair_doshas_always_populated_with_a_reason() -> None:
    planets = [
        _planet(Planet.SATURN, house=1), _planet(Planet.MOON, house=2),
        _planet(Planet.MARS, house=3), _planet(Planet.RAHU, house=4),
    ]
    result = compute_saturn_afflictions(planets, aspects=[])
    assert result.vish_dosha.reason
    assert result.shani_mangal_dosha.reason
    assert result.shani_rahu_dosha.reason


def _punarphoo_planets(
    saturn_house: int = 1,
    moon_house: int = 5,
    sun_house: int = 9,
    saturn_nakshatra_lord: Planet = Planet.KETU,
    moon_nakshatra_lord: Planet = Planet.KETU,
) -> list[PlanetPosition]:
    return [
        _planet(Planet.SATURN, house=saturn_house, nakshatra_lord=saturn_nakshatra_lord),
        _planet(Planet.MOON, house=moon_house, nakshatra_lord=moon_nakshatra_lord),
        _planet(Planet.SUN, house=sun_house),
        _planet(Planet.MARS, house=11),
    ]


def test_punarphoo_dosha_flagged_when_saturn_and_moon_conjunct() -> None:
    planets = _punarphoo_planets(saturn_house=5, moon_house=5, sun_house=9)
    result = compute_punarphoo_dosha(planets, aspects=[])
    assert result.has_dosha is True
    assert result.conjunction_or_aspect is True
    assert result.is_conjunction is True
    assert result.is_cancelled is False


def test_punarphoo_dosha_flagged_via_saturns_aspect_not_conjunction() -> None:
    planets = _punarphoo_planets(saturn_house=1, moon_house=7, sun_house=9)
    aspects = [
        PlanetAspect(
            source_planet=Planet.SATURN, source_house=1,
            target_planet=Planet.MOON, target_house=7, is_special=False,
        )
    ]
    result = compute_punarphoo_dosha(planets, aspects)
    assert result.has_dosha is True
    assert result.conjunction_or_aspect is True
    assert result.is_conjunction is False


def test_punarphoo_dosha_flagged_when_moon_in_saturn_ruled_nakshatra() -> None:
    planets = _punarphoo_planets(
        saturn_house=1, moon_house=2, sun_house=9, moon_nakshatra_lord=Planet.SATURN
    )
    result = compute_punarphoo_dosha(planets, aspects=[])
    assert result.has_dosha is True
    assert result.moon_in_saturn_nakshatra is True
    assert result.conjunction_or_aspect is False


def test_punarphoo_dosha_flagged_when_saturn_in_moon_ruled_nakshatra() -> None:
    planets = _punarphoo_planets(
        saturn_house=1, moon_house=2, sun_house=9, saturn_nakshatra_lord=Planet.MOON
    )
    result = compute_punarphoo_dosha(planets, aspects=[])
    assert result.has_dosha is True
    assert result.saturn_in_moon_nakshatra is True


def test_punarphoo_dosha_not_flagged_when_unrelated() -> None:
    planets = _punarphoo_planets(saturn_house=1, moon_house=2, sun_house=9)
    result = compute_punarphoo_dosha(planets, aspects=[])
    assert result.has_dosha is False
    assert "No conjunction" in result.reason


def test_punarphoo_dosha_cancelled_when_sun_conjoins_both() -> None:
    # Rule A: Sun sits with both Saturn and the Moon (all three conjunct).
    planets = _punarphoo_planets(saturn_house=5, moon_house=5, sun_house=5)
    result = compute_punarphoo_dosha(planets, aspects=[])
    assert result.has_dosha is True
    assert result.cancelled_by_conjunction is True
    assert result.is_cancelled is True
    assert "cancelled" in result.reason.lower()


def test_punarphoo_dosha_not_cancelled_by_sun_alone_without_saturn_moon_link() -> None:
    # Sun conjunct Moon only (not Saturn) shouldn't cancel anything, since
    # there is no dosha to cancel in the first place.
    planets = _punarphoo_planets(saturn_house=1, moon_house=5, sun_house=5)
    result = compute_punarphoo_dosha(planets, aspects=[])
    assert result.has_dosha is False
    assert result.is_cancelled is False


def test_punarphoo_dosha_cancelled_via_sun_ruled_nakshatra() -> None:
    # Rule B: the Moon is in a Sun-ruled Nakshatra, while the dosha itself
    # formed via Saturn-Moon conjunction.
    planets = _punarphoo_planets(
        saturn_house=5, moon_house=5, sun_house=9, moon_nakshatra_lord=Planet.SUN
    )
    result = compute_punarphoo_dosha(planets, aspects=[])
    assert result.has_dosha is True
    assert result.cancelled_by_nakshatra is True
    assert result.is_cancelled is True


def test_punarphoo_dosha_reason_always_populated() -> None:
    for planets in [
        _punarphoo_planets(saturn_house=1, moon_house=2, sun_house=9),
        _punarphoo_planets(saturn_house=5, moon_house=5, sun_house=9),
        _punarphoo_planets(saturn_house=5, moon_house=5, sun_house=5),
    ]:
        result = compute_punarphoo_dosha(planets, aspects=[])
        assert result.reason
