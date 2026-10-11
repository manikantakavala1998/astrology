from datetime import date, time

import pytest

from vedic_astro.chart import build_kundali_chart
from vedic_astro.models import BirthData, Planet, Sign
from vedic_astro.vimshopaka_bala import (
    SAPTAVARGA_WEIGHTS,
    SHADVARGA_WEIGHTS,
    DASHAVARGA_CODES,
    DASHAVARGA_WEIGHTS,
    SHODASHAVARGA_CODES,
    SHODASHAVARGA_WEIGHTS,
    _varga_score,
    compute_vimshopaka_bala,
    strength_band,
)


def _sample_birth_data() -> BirthData:
    return BirthData(
        birth_date=date(1990, 6, 15),
        birth_time=time(8, 30, 0),
        latitude=13.0827,
        longitude=80.2707,
        utc_offset_hours=5.5,
    )


def test_shadvarga_weights_sum_to_20() -> None:
    assert sum(SHADVARGA_WEIGHTS.values()) == pytest.approx(20.0)


def test_saptavarga_weights_sum_to_20() -> None:
    assert sum(SAPTAVARGA_WEIGHTS.values()) == pytest.approx(20.0)


def test_ten_and_sixteen_chart_weights_preserve_classical_fractions() -> None:
    assert len(DASHAVARGA_CODES) == 10 and set(DASHAVARGA_CODES) == set(DASHAVARGA_WEIGHTS)
    assert len(SHODASHAVARGA_CODES) == 16 and set(SHODASHAVARGA_CODES) == set(SHODASHAVARGA_WEIGHTS)
    assert sum(DASHAVARGA_WEIGHTS.values()) == 20
    assert sum(SHODASHAVARGA_WEIGHTS.values()) == 20
    assert DASHAVARGA_WEIGHTS["D1"] == 3 and DASHAVARGA_WEIGHTS["D60"] == 5
    assert all(weight == 1.5 for code, weight in DASHAVARGA_WEIGHTS.items() if code not in ("D1", "D60"))
    assert SHODASHAVARGA_WEIGHTS["D1"] == 3.5
    assert SHODASHAVARGA_WEIGHTS["D60"] == 4
    assert SHODASHAVARGA_WEIGHTS["D16"] == 2
    assert SHODASHAVARGA_WEIGHTS["D9"] == 3


def test_dashavarga_and_shodashavarga_mixed_relationship_totals() -> None:
    # Venus -> Saturn great friend (.9), Moon great enemy (.25), Venus own (1).
    signs = {Planet.VENUS: Sign.CAPRICORN, Planet.SATURN: Sign.LIBRA, Planet.MOON: Sign.CANCER}
    divisions = {
        "D2": Sign.CANCER, "D3": Sign.CAPRICORN, "D4": Sign.CAPRICORN,
        "D7": Sign.TAURUS, "D9": Sign.AQUARIUS, "D10": Sign.TAURUS,
        "D12": Sign.AQUARIUS, "D16": Sign.CANCER, "D20": Sign.TAURUS,
        "D24": Sign.CANCER, "D27": Sign.CAPRICORN, "D30": Sign.TAURUS,
        "D40": Sign.TAURUS, "D45": Sign.CANCER, "D60": Sign.AQUARIUS,
    }
    def score(codes, weights):
        return _varga_score(Planet.VENUS, Sign.CAPRICORN, divisions, signs, codes, weights)
    assert score(DASHAVARGA_CODES, DASHAVARGA_WEIGHTS) == pytest.approx(16.5)
    assert score(SHODASHAVARGA_CODES, SHODASHAVARGA_WEIGHTS) == pytest.approx(15.7)
    old_six = score(list(SHADVARGA_WEIGHTS), SHADVARGA_WEIGHTS)
    old_seven = score(list(SAPTAVARGA_WEIGHTS), SAPTAVARGA_WEIGHTS)
    divisions["D60"] = Sign.CANCER
    assert score(DASHAVARGA_CODES, DASHAVARGA_WEIGHTS) == pytest.approx(13.25)
    assert score(SHODASHAVARGA_CODES, SHODASHAVARGA_WEIGHTS) == pytest.approx(13.1)
    assert score(list(SHADVARGA_WEIGHTS), SHADVARGA_WEIGHTS) == old_six
    assert score(list(SAPTAVARGA_WEIGHTS), SAPTAVARGA_WEIGHTS) == old_seven


def test_shadvarga_reproduces_bphs_worked_example_for_venus() -> None:
    # BPHS Ch.7's own worked example: Venus (ascendant lord in the source
    # chart) at Shadvarga level - Rasi=Capricorn(Saturn, Adhimitra),
    # Hora=Cancer(Moon, Adhishatru), Drekkana=Capricorn(Saturn, Adhimitra),
    # Navamsa=Aquarius(Saturn, Adhimitra), Dvadasamsa=Aquarius(Saturn,
    # Adhimitra), Trimsamsa=Taurus(Venus, Own). The text's own stated
    # total is 16.8 - reproduced here exactly via real D1 placements that
    # yield the same Panchadha relations (Saturn as Venus's natural AND
    # temporal friend -> great_friend/Adhimitra; Moon as Venus's natural
    # AND temporal enemy -> great_enemy/Adhishatru).
    venus_d1_sign = Sign.CAPRICORN
    d1_signs = {
        Planet.VENUS: venus_d1_sign,
        Planet.SATURN: Sign.LIBRA,  # house 10 from Capricorn - temporal friend
        Planet.MOON: Sign.CANCER,  # house 7 from Capricorn - temporal enemy
    }
    varga_signs = {
        "D2": Sign.CANCER,      # Moon's sign -> great_enemy
        "D3": Sign.CAPRICORN,   # Saturn's sign -> great_friend
        "D9": Sign.AQUARIUS,    # Saturn's sign -> great_friend
        "D12": Sign.AQUARIUS,   # Saturn's sign -> great_friend
        "D30": Sign.TAURUS,     # Venus's own sign -> own
    }
    score = _varga_score(
        Planet.VENUS, venus_d1_sign, varga_signs, d1_signs,
        ["D1", "D2", "D3", "D9", "D12", "D30"], SHADVARGA_WEIGHTS,
    )
    assert score == pytest.approx(16.8)


def test_strength_band_matches_the_primary_bphs_4_band_scale() -> None:
    assert strength_band(4.9) == "Inauspicious"
    assert strength_band(5.0) == "Some Good Effects"
    assert strength_band(9.9) == "Some Good Effects"
    assert strength_band(10.0) == "Mediocre"
    assert strength_band(14.9) == "Mediocre"
    assert strength_band(15.0) == "Wholly Favourable"
    assert strength_band(20.0) == "Wholly Favourable"


def test_compute_vimshopaka_bala_covers_all_seven_classical_planets() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    results = compute_vimshopaka_bala(chart.planets)
    assert set(results) == {
        Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY,
        Planet.JUPITER, Planet.VENUS, Planet.SATURN,
    }
    for result in results.values():
        assert 0.0 <= result.shadvarga_score <= 20.0
        assert 0.0 <= result.saptavarga_score <= 20.0
        assert result.shadvarga_band
        assert result.saptavarga_band
        assert 0.0 <= result.dashavarga_score <= 20.0
        assert 0.0 <= result.shodashavarga_score <= 20.0
        assert result.dashavarga_band and result.shodashavarga_band
