from datetime import date, datetime, time

import pytest

from vedic_astro.chart import build_kundali_chart
from vedic_astro.models import BirthData, Planet, PlanetAspect, Sign
from vedic_astro.shadbala import (
    REQUIRED_RUPAS,
    ayana_bala,
    chesta_bala,
    compute_shadbala,
    dig_bala,
    drekkana_bala,
    drik_bala,
    kendradi_bala,
    naisargika_bala,
    nathonnata_bala,
    ojayugmarasyamsa_bala,
    paksha_bala,
    saptavargaja_bala,
    tribhaga_bala,
    uchcha_bala,
)


def _sample_birth_data() -> BirthData:
    return BirthData(
        birth_date=date(1990, 6, 15),
        birth_time=time(8, 30, 0),
        latitude=13.0827,
        longitude=80.2707,
        utc_offset_hours=5.5,
    )


# ---------------------------------------------------------------------------
# Uchcha Bala
# ---------------------------------------------------------------------------


def test_uchcha_bala_is_60_at_exact_deep_exaltation() -> None:
    # Sun exalted at 10 degrees Aries = longitude 10.0.
    assert uchcha_bala(Planet.SUN, 10.0) == pytest.approx(60.0)


def test_uchcha_bala_is_0_at_exact_deep_debilitation() -> None:
    # Sun debilitated at 10 degrees Libra = longitude 190.0.
    assert uchcha_bala(Planet.SUN, 190.0) == pytest.approx(0.0)


def test_uchcha_bala_is_30_at_the_midpoint() -> None:
    # Halfway (90 degrees) between exaltation and debilitation.
    assert uchcha_bala(Planet.SUN, 100.0) == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# Kendradi Bala
# ---------------------------------------------------------------------------


def test_kendradi_bala_60_in_a_kendra() -> None:
    # Aries ascendant, planet in Aries (house 1, a Kendra).
    assert kendradi_bala(Sign.ARIES, Sign.ARIES) == pytest.approx(60.0)


def test_kendradi_bala_30_in_a_panapara() -> None:
    # Aries ascendant, planet in Taurus (house 2, a Panapara).
    assert kendradi_bala(Sign.TAURUS, Sign.ARIES) == pytest.approx(30.0)


def test_kendradi_bala_15_in_an_apoklima() -> None:
    # Aries ascendant, planet in Gemini (house 3, an Apoklima).
    assert kendradi_bala(Sign.GEMINI, Sign.ARIES) == pytest.approx(15.0)


# ---------------------------------------------------------------------------
# Ojayugmarasyamsa Bala
# ---------------------------------------------------------------------------


def test_ojayugma_bala_masculine_planet_scores_in_odd_signs() -> None:
    # Sun (masculine) in Aries (odd) for both D1 and D9 - full 30.
    assert ojayugmarasyamsa_bala(Sign.ARIES, Sign.ARIES, Planet.SUN) == pytest.approx(30.0)


def test_ojayugma_bala_masculine_planet_scores_zero_in_even_signs() -> None:
    assert ojayugmarasyamsa_bala(Sign.TAURUS, Sign.TAURUS, Planet.SUN) == pytest.approx(0.0)


def test_ojayugma_bala_feminine_planet_scores_in_even_signs() -> None:
    # Moon (feminine) in Taurus (even) for both - full 30.
    assert ojayugmarasyamsa_bala(Sign.TAURUS, Sign.TAURUS, Planet.MOON) == pytest.approx(30.0)


def test_ojayugma_bala_mixed_d1_d9_gives_half() -> None:
    # Sun in Aries (odd, scores) for D1 but Taurus (even, doesn't score) for D9.
    assert ojayugmarasyamsa_bala(Sign.ARIES, Sign.TAURUS, Planet.SUN) == pytest.approx(15.0)


# ---------------------------------------------------------------------------
# Drekkana Bala
# ---------------------------------------------------------------------------


def test_drekkana_bala_masculine_planet_scores_in_first_drekkana() -> None:
    assert drekkana_bala(Planet.SUN, 5.0) == pytest.approx(15.0)


def test_drekkana_bala_feminine_planet_scores_in_second_drekkana() -> None:
    assert drekkana_bala(Planet.MOON, 15.0) == pytest.approx(15.0)


def test_drekkana_bala_neuter_planet_scores_in_third_drekkana() -> None:
    assert drekkana_bala(Planet.MERCURY, 25.0) == pytest.approx(15.0)


def test_drekkana_bala_zero_when_gender_does_not_match_drekkana() -> None:
    assert drekkana_bala(Planet.SUN, 15.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Saptavargaja Bala
# ---------------------------------------------------------------------------


def test_saptavargaja_bala_own_sign_in_all_seven_vargas() -> None:
    # Sun occupying Leo (its own sign) in every one of the 7 vargas, at a
    # degree outside its Moolatrikona range (20-30 in Leo) - plain "own"
    # (30) in each, 7*30 = 210.
    varga_signs = {code: Sign.LEO for code in ["D2", "D3", "D7", "D9", "D12", "D30"]}
    d1_signs = {Planet.SUN: Sign.LEO}
    result = saptavargaja_bala(Planet.SUN, 25.0, Sign.LEO, varga_signs, d1_signs)
    assert result == pytest.approx(210.0)


def test_saptavargaja_bala_moolatrikona_in_d1_only() -> None:
    # Sun at 10 degrees Leo (within its 0-20 Moolatrikona range) in D1 - 45
    # for D1, plain "own" (30) for the other 6 = 45 + 6*30 = 225.
    varga_signs = {code: Sign.LEO for code in ["D2", "D3", "D7", "D9", "D12", "D30"]}
    d1_signs = {Planet.SUN: Sign.LEO}
    result = saptavargaja_bala(Planet.SUN, 10.0, Sign.LEO, varga_signs, d1_signs)
    assert result == pytest.approx(45.0 + 6 * 30.0)


def test_saptavargaja_bala_great_friend_relation() -> None:
    # Sun (D1: Leo, its own sign) occupies Scorpio (Mars's sign) in D2.
    # Mars is Sun's natural friend, and Mars's own D1 sign (Scorpio) is
    # house 4 from Sun's D1 sign (Leo) - a temporal-friend house - so this
    # combination should resolve to "great_friend" (20) for D2, with the
    # other 6 vargas scoring "own" (30) since Sun sits in Leo there.
    varga_signs = {
        "D2": Sign.SCORPIO, "D3": Sign.LEO, "D7": Sign.LEO,
        "D9": Sign.LEO, "D12": Sign.LEO, "D30": Sign.LEO,
    }
    d1_signs = {Planet.SUN: Sign.LEO, Planet.MARS: Sign.SCORPIO}
    # Degree 25 in Leo is outside Sun's Moolatrikona range (0-20), so D1
    # itself scores plain "own" (30), not the Moolatrikona bonus (45).
    result = saptavargaja_bala(Planet.SUN, 25.0, Sign.LEO, varga_signs, d1_signs)
    assert result == pytest.approx(20.0 + 6 * 30.0)


# ---------------------------------------------------------------------------
# Dig Bala
# ---------------------------------------------------------------------------


def test_dig_bala_60_at_the_planets_strong_cusp() -> None:
    # Sun is strong at the 10th cusp (MC). Cusps: Asc=0, ..., IC=cusps[3],
    # ..., Desc=cusps[6], ..., MC=cusps[9]. Put Sun exactly at MC.
    cusps = [0.0] * 12
    cusps[9] = 100.0  # MC
    cusps[3] = 280.0  # IC (180 degrees from MC)
    assert dig_bala(Planet.SUN, 100.0, cusps) == pytest.approx(60.0, abs=0.01)


def test_dig_bala_0_at_the_planets_weak_cusp() -> None:
    cusps = [0.0] * 12
    cusps[9] = 100.0  # MC (Sun's strong point)
    cusps[3] = 280.0  # IC (Sun's weak point, 180 degrees away)
    assert dig_bala(Planet.SUN, 280.0, cusps) == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# Kala Bala sub-parts
# ---------------------------------------------------------------------------


def test_nathonnata_bala_mercury_always_60() -> None:
    assert nathonnata_bala(Planet.MERCURY, 0.0) == pytest.approx(60.0)
    assert nathonnata_bala(Planet.MERCURY, 12.0) == pytest.approx(60.0)


def test_nathonnata_bala_night_planet_at_midnight_is_60() -> None:
    assert nathonnata_bala(Planet.MOON, 0.0) == pytest.approx(60.0)


def test_nathonnata_bala_day_planet_at_noon_is_60() -> None:
    assert nathonnata_bala(Planet.SUN, 12.0) == pytest.approx(60.0)


def test_nathonnata_bala_day_and_night_planets_are_complementary() -> None:
    for hour in [1.0, 5.0, 9.0, 15.0, 20.0]:
        night = nathonnata_bala(Planet.MOON, hour)
        day = nathonnata_bala(Planet.SUN, hour)
        assert night + day == pytest.approx(60.0)


def test_paksha_bala_benefic_peaks_at_full_moon() -> None:
    # Full moon: Moon exactly 180 degrees from the Sun.
    assert paksha_bala(Planet.JUPITER, 0.0, 180.0) == pytest.approx(60.0)


def test_paksha_bala_benefic_is_zero_at_new_moon() -> None:
    assert paksha_bala(Planet.JUPITER, 0.0, 0.0) == pytest.approx(0.0)


def test_paksha_bala_malefic_is_the_complement_of_benefic() -> None:
    for elongation in [30.0, 90.0, 150.0, 210.0, 270.0]:
        benefic = paksha_bala(Planet.JUPITER, 0.0, elongation)
        malefic = paksha_bala(Planet.SUN, 0.0, elongation)
        assert benefic + malefic == pytest.approx(60.0)


def test_tribhaga_bala_jupiter_always_60() -> None:
    sunrise = datetime(2024, 6, 15, 0, 12)
    sunset = datetime(2024, 6, 15, 13, 6)
    next_sunrise = datetime(2024, 6, 16, 0, 12)
    assert tribhaga_bala(Planet.JUPITER, datetime(2024, 6, 15, 6, 0), sunrise, sunset, next_sunrise) == 60.0
    assert tribhaga_bala(Planet.JUPITER, datetime(2024, 6, 15, 20, 0), sunrise, sunset, next_sunrise) == 60.0


def test_tribhaga_bala_first_day_third_is_mercury() -> None:
    sunrise = datetime(2024, 6, 15, 0, 0)
    sunset = datetime(2024, 6, 15, 12, 0)
    next_sunrise = datetime(2024, 6, 16, 0, 0)
    # Just after sunrise - first third of the day, ruled by Mercury.
    assert tribhaga_bala(Planet.MERCURY, datetime(2024, 6, 15, 1, 0), sunrise, sunset, next_sunrise) == 60.0
    assert tribhaga_bala(Planet.SUN, datetime(2024, 6, 15, 1, 0), sunrise, sunset, next_sunrise) == 0.0


def test_tribhaga_bala_first_night_third_is_moon() -> None:
    sunrise = datetime(2024, 6, 15, 0, 0)
    sunset = datetime(2024, 6, 15, 12, 0)
    next_sunrise = datetime(2024, 6, 16, 0, 0)
    # Just after sunset - first third of the night, ruled by the Moon.
    assert tribhaga_bala(Planet.MOON, datetime(2024, 6, 15, 13, 0), sunrise, sunset, next_sunrise) == 60.0


def test_ayana_bala_north_group_peaks_at_max_north_declination() -> None:
    obliquity = 23.44
    assert ayana_bala(Planet.SUN, obliquity, obliquity) == pytest.approx(60.0, abs=0.01)


def test_ayana_bala_north_group_is_zero_at_max_south_declination() -> None:
    obliquity = 23.44
    assert ayana_bala(Planet.SUN, -obliquity, obliquity) == pytest.approx(0.0, abs=0.01)


def test_ayana_bala_south_group_is_mirrored() -> None:
    obliquity = 23.44
    assert ayana_bala(Planet.MOON, -obliquity, obliquity) == pytest.approx(60.0, abs=0.01)
    assert ayana_bala(Planet.MOON, obliquity, obliquity) == pytest.approx(0.0, abs=0.01)


def test_ayana_bala_mercury_always_favours_larger_magnitude() -> None:
    obliquity = 23.44
    north = ayana_bala(Planet.MERCURY, obliquity, obliquity)
    south = ayana_bala(Planet.MERCURY, -obliquity, obliquity)
    assert north == pytest.approx(south)
    assert north == pytest.approx(60.0, abs=0.01)


def test_ayana_bala_is_30_at_zero_declination() -> None:
    assert ayana_bala(Planet.SUN, 0.0, 23.44) == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# Chesta Bala
# ---------------------------------------------------------------------------


def test_chesta_bala_sun_reuses_its_own_ayana_bala() -> None:
    assert chesta_bala(Planet.SUN, 1.0, 42.5, 10.0) == pytest.approx(42.5)


def test_chesta_bala_moon_reuses_its_own_paksha_bala() -> None:
    assert chesta_bala(Planet.MOON, 13.0, 42.5, 10.0) == pytest.approx(10.0)


def test_chesta_bala_retrograde_is_60() -> None:
    assert chesta_bala(Planet.MARS, -0.2, 0.0, 0.0) == pytest.approx(60.0)


def test_chesta_bala_stationary_is_15() -> None:
    assert chesta_bala(Planet.MARS, 0.0, 0.0, 0.0) == pytest.approx(15.0)


def test_chesta_bala_faster_than_mean_is_45() -> None:
    mean = 0.524  # Mars mean daily motion
    assert chesta_bala(Planet.MARS, mean * 1.5, 0.0, 0.0) == pytest.approx(45.0)


def test_chesta_bala_slower_than_mean_is_30() -> None:
    mean = 0.524
    assert chesta_bala(Planet.MARS, mean * 0.5, 0.0, 0.0) == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# Naisargika Bala
# ---------------------------------------------------------------------------


def test_naisargika_bala_matches_the_fixed_classical_table() -> None:
    assert naisargika_bala(Planet.SUN) == pytest.approx(60.0)
    assert naisargika_bala(Planet.SATURN) == pytest.approx(60.0 / 7.0)
    assert naisargika_bala(Planet.MOON) == pytest.approx(60.0 * 6 / 7)


# ---------------------------------------------------------------------------
# Drik Bala
# ---------------------------------------------------------------------------


def test_drik_bala_benefic_aspect_adds_positive_strength() -> None:
    aspects = [
        PlanetAspect(
            source_planet=Planet.JUPITER, source_house=1,
            target_planet=Planet.SUN, target_house=7, is_special=False,
        )
    ]
    assert drik_bala(Planet.SUN, aspects, moon_is_waxing=True) == pytest.approx(60.0 * 1.25)


def test_drik_bala_malefic_aspect_subtracts_strength() -> None:
    aspects = [
        PlanetAspect(
            source_planet=Planet.SATURN, source_house=1,
            target_planet=Planet.SUN, target_house=7, is_special=False,
        )
    ]
    assert drik_bala(Planet.SUN, aspects, moon_is_waxing=True) == pytest.approx(-60.0 * 0.75)


def test_drik_bala_special_aspect_uses_the_fixed_fraction() -> None:
    aspects = [
        PlanetAspect(
            source_planet=Planet.JUPITER, source_house=1,
            target_planet=Planet.SUN, target_house=5, is_special=True,
        )
    ]
    assert drik_bala(Planet.SUN, aspects, moon_is_waxing=True) == pytest.approx(30.0 * 1.25)


def test_drik_bala_no_aspects_is_zero() -> None:
    assert drik_bala(Planet.SUN, [], moon_is_waxing=True) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Required strength table
# ---------------------------------------------------------------------------


def test_required_rupas_has_all_seven_classical_planets() -> None:
    for planet in [
        Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY,
        Planet.JUPITER, Planet.VENUS, Planet.SATURN,
    ]:
        assert planet in REQUIRED_RUPAS


# ---------------------------------------------------------------------------
# Orchestrator (integration, on a real chart)
# ---------------------------------------------------------------------------


def test_compute_shadbala_covers_all_seven_classical_planets() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    results = compute_shadbala(
        chart.planets, chart.ascendant.sign, chart.bhava_chalit_cusps,
        chart.aspects, chart.birth_data, chart.panchanga.paksha == "Shukla",
    )
    assert set(results) == {
        Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY,
        Planet.JUPITER, Planet.VENUS, Planet.SATURN,
    }


def test_compute_shadbala_totals_are_internally_consistent() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    results = compute_shadbala(
        chart.planets, chart.ascendant.sign, chart.bhava_chalit_cusps,
        chart.aspects, chart.birth_data, chart.panchanga.paksha == "Shukla",
    )
    for result in results.values():
        expected_total = (
            result.sthana_bala.total + result.dig_bala + result.kala_bala.total
            + result.chesta_bala + result.naisargika_bala + result.drik_bala
        )
        assert result.total_virupas == pytest.approx(expected_total)
        assert result.total_rupas == pytest.approx(result.total_virupas / 60.0)
        assert result.meets_required_strength == (result.total_rupas >= result.required_rupas)
        assert 0.0 <= result.ishta_phala <= 1.0
        assert 0.0 <= result.kashta_phala <= 1.0
