from datetime import date, time

import pytest

from vedic_astro.chart import build_kundali_chart
from vedic_astro.models import BirthData, Planet, Sign
from vedic_astro.vimshopaka_bala import (
    SAPTAVARGA_WEIGHTS,
    SHADVARGA_WEIGHTS,
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
