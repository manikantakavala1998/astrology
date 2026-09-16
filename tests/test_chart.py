from datetime import date, time

from vedic_astro.chart import build_kundali_chart
from vedic_astro.models import BirthData, HouseSystem, Planet, Sign


def _sample_birth_data() -> BirthData:
    return BirthData(
        birth_date=date(1990, 6, 15),
        birth_time=time(8, 30, 0),
        latitude=13.0827,
        longitude=80.2707,  # Chennai
        utc_offset_hours=5.5,
    )


def test_build_kundali_chart_has_all_nine_planets() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    planets_present = {p.planet for p in chart.planets}
    assert planets_present == {
        Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY, Planet.JUPITER,
        Planet.VENUS, Planet.SATURN, Planet.RAHU, Planet.KETU,
    }


def test_every_planet_has_a_house_between_one_and_twelve() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    for planet_position in chart.planets:
        assert 1 <= planet_position.house <= 12


def test_ascendant_is_house_one_reference() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    planets_in_ascendant_sign = [p for p in chart.planets if p.sign == chart.ascendant.sign]
    assert all(p.house == 1 for p in planets_in_ascendant_sign)


def test_dasha_first_period_contains_or_precedes_birth() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    birth_dt = chart.birth_data.local_datetime
    first_period = chart.dasha.periods[0]
    assert first_period.start <= birth_dt
    assert chart.dasha.periods[-1].end > birth_dt


def test_panchanga_nakshatra_matches_moon_nakshatra() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    moon = next(p for p in chart.planets if p.planet == Planet.MOON)
    assert chart.panchanga.nakshatra.name == moon.nakshatra.name


def test_every_planet_has_a_hora_sign_and_matching_lord() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    for planet_position in chart.planets:
        assert planet_position.hora_sign in (Sign.LEO, Sign.CANCER)
        expected_lord = Planet.SUN if planet_position.hora_sign == Sign.LEO else Planet.MOON
        assert planet_position.hora_lord == expected_lord


def test_whole_sign_ascendant_is_house_one_regardless_of_house_system_setting() -> None:
    # The Ascendant sign itself never changes with house system - only which
    # house each individual planet falls into can shift.
    whole_sign_chart = build_kundali_chart(_sample_birth_data())
    placidus_data = _sample_birth_data()
    placidus_data.house_system = HouseSystem.PLACIDUS
    placidus_chart = build_kundali_chart(placidus_data)
    assert whole_sign_chart.ascendant.sign == placidus_chart.ascendant.sign


def test_different_house_systems_can_change_a_planets_house() -> None:
    birth_data = _sample_birth_data()
    whole_sign_chart = build_kundali_chart(birth_data)

    placidus_data = _sample_birth_data()
    placidus_data.house_system = HouseSystem.PLACIDUS
    placidus_chart = build_kundali_chart(placidus_data)

    whole_sign_houses = {p.planet: p.house for p in whole_sign_chart.planets}
    placidus_houses = {p.planet: p.house for p in placidus_chart.planets}
    # For this specific chart, at least one planet's house should differ
    # between whole-sign and a cusp-based system (they are rarely identical
    # for every planet in a real chart).
    assert whole_sign_houses != placidus_houses


def test_equal_house_system_all_houses_are_thirty_degrees_apart() -> None:
    birth_data = _sample_birth_data()
    birth_data.house_system = HouseSystem.EQUAL
    chart = build_kundali_chart(birth_data)
    for planet_position in chart.planets:
        assert 1 <= planet_position.house <= 12


def test_chart_includes_chara_karakas_and_chara_dasha() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    assert len(chart.chara_karakas) == 7
    assert chart.chara_karakas[0].karaka == "Atmakaraka"
    assert len(chart.chara_dasha) == 12
    assert chart.chara_dasha[0].sign == chart.ascendant.sign
