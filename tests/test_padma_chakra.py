from datetime import date, datetime, time

from vedic_astro.chart import build_kundali_chart
from vedic_astro.models import BirthData, NakshatraPlacement, Planet, PlanetPosition, Sign
from vedic_astro.padma_chakra import compute_badhaka, compute_padma_chakra_years

_DUMMY_NAKSHATRA = NakshatraPlacement(name="Ashwini", index=1, pada=1, lord=Planet.KETU)
_SIGN_INDEX = {s: i for i, s in enumerate(Sign)}


def _planet(planet: Planet, sign: Sign, house: int, degree_in_sign: float = 15.0) -> PlanetPosition:
    return PlanetPosition(
        planet=planet,
        longitude=_SIGN_INDEX[sign] * 30 + degree_in_sign,
        sign=sign,
        degree_in_sign=degree_in_sign,
        house=house,
        nakshatra=_DUMMY_NAKSHATRA,
        retrograde=False,
    )


def test_badhaka_house_by_modality() -> None:
    movable = compute_badhaka(Sign.ARIES)
    fixed = compute_badhaka(Sign.TAURUS)
    dual = compute_badhaka(Sign.GEMINI)

    assert movable.modality == "movable"
    assert movable.badhaka_house_from_lagna == 11
    assert fixed.modality == "fixed"
    assert fixed.badhaka_house_from_lagna == 9
    assert dual.modality == "dual"
    assert dual.badhaka_house_from_lagna == 7


def test_real_chart_matches_bhavasars_own_worked_example() -> None:
    """Female, 15-09-1976 22:00, Ahmedabad - from Pramod Bhavasar's "Use of
    Dwadasamsa Chart in Prediction" article. Verified independently against
    every claim the article makes about age 33: Vrishabh (Taurus) lagna,
    Saturn as 9th lord placed in the 3rd house, 9th house active at age 33,
    Saturn's D12 sign Kumbha (Aquarius), and the 10th-house superimposition
    - all reproduced exactly by our own ephemeris + this module."""
    birth = BirthData(
        birth_date=date(1976, 9, 15),
        birth_time=time(22, 0),
        latitude=23.0225,
        longitude=72.5714,
        utc_offset_hours=5.5,
    )
    chart = build_kundali_chart(birth)
    assert chart.ascendant.sign == Sign.TAURUS

    saturn = next(p for p in chart.planets if p.planet == Planet.SATURN)
    assert saturn.house == 3

    years = compute_padma_chakra_years(
        chart.ascendant.sign, chart.ascendant.longitude, chart.planets, datetime(1976, 9, 15, 22, 0)
    )
    year_33 = next(y for y in years if y.age == 33)

    assert year_33.house_from_lagna == 9
    assert year_33.sign == Sign.CAPRICORN
    assert year_33.year_lord == Planet.SATURN
    assert year_33.year_lord_dwadasamsa_sign == Sign.AQUARIUS
    assert year_33.superimposed_house_from_lagna == 10
    # Article's own hand-rounded answer is 28-03-2008; documented ~1-day residual.
    assert year_33.start_date.date() == date(2008, 3, 29)

    badhaka = compute_badhaka(chart.ascendant.sign)
    assert badhaka.badhaka_house_from_lagna == 9
    assert badhaka.badhakesh == Planet.SATURN


def test_is_badhaka_flags_when_superimposed_house_matches_d1_badhaka() -> None:
    # Taurus ascendant (fixed) -> D1 badhaka house is 9 (Capricorn), lord Saturn.
    # Year 1 = house 1 = Taurus, whose lord is Venus. Placing Venus at the
    # very start of Capricorn (degree 1.0) makes its D12 sign Capricorn too
    # (D12 part 0 of a sign maps to that sign itself), landing the
    # superimposed house exactly on the D1 badhaka house.
    planets = [_planet(p, Sign.ARIES, house=1) for p in Planet if p != Planet.VENUS]
    planets.append(_planet(Planet.VENUS, Sign.CAPRICORN, house=9, degree_in_sign=1.0))

    years = compute_padma_chakra_years(Sign.TAURUS, 0.0, planets, datetime(2000, 1, 1), max_age=1)
    year_1 = years[0]

    assert year_1.sign == Sign.TAURUS
    assert year_1.year_lord == Planet.VENUS
    assert year_1.year_lord_dwadasamsa_sign == Sign.CAPRICORN
    assert year_1.superimposed_house_from_lagna == 9
    assert year_1.is_badhaka


def test_house_from_lagna_cycles_every_12_years() -> None:
    planets = [_planet(p, Sign.ARIES, house=1) for p in Planet]
    years = compute_padma_chakra_years(Sign.ARIES, 0.0, planets, datetime(2000, 1, 1), max_age=30)
    by_age = {y.age: y for y in years}

    assert by_age[1].house_from_lagna == 1
    assert by_age[12].house_from_lagna == 12
    assert by_age[13].house_from_lagna == 1
    assert by_age[25].house_from_lagna == 1
