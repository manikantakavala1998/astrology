import pytest

from vedic_astro.models import Sign
from vedic_astro.rashi_bhava import (
    build_ascendant,
    degree_in_sign,
    house_from_cusps,
    sign_for_longitude,
    whole_sign_house,
)


@pytest.mark.parametrize(
    ("longitude", "expected"),
    [
        (0.0, Sign.ARIES),
        (29.99, Sign.ARIES),
        (30.0, Sign.TAURUS),
        (95.5, Sign.CANCER),
        (359.99, Sign.PISCES),
        (360.0, Sign.ARIES),  # wraps
    ],
)
def test_sign_for_longitude(longitude: float, expected: Sign) -> None:
    assert sign_for_longitude(longitude) == expected


def test_degree_in_sign() -> None:
    assert degree_in_sign(95.5) == pytest.approx(5.5)
    assert degree_in_sign(0.0) == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("planet_sign", "ascendant_sign", "expected_house"),
    [
        (Sign.ARIES, Sign.ARIES, 1),
        (Sign.TAURUS, Sign.ARIES, 2),
        (Sign.PISCES, Sign.ARIES, 12),
        (Sign.LEO, Sign.LEO, 1),
        (Sign.VIRGO, Sign.LEO, 2),
        (Sign.CANCER, Sign.LEO, 12),
    ],
)
def test_whole_sign_house(planet_sign: Sign, ascendant_sign: Sign, expected_house: int) -> None:
    assert whole_sign_house(planet_sign, ascendant_sign) == expected_house


def test_build_ascendant() -> None:
    asc = build_ascendant(95.5)
    assert asc.sign == Sign.CANCER
    assert asc.degree_in_sign == pytest.approx(5.5)
    assert asc.longitude == pytest.approx(95.5)


# 12 evenly-spaced cusps starting at 10 degrees, for simple, predictable testing.
_EVEN_CUSPS = [10.0 + 30 * i for i in range(12)]  # [10, 40, 70, ..., 340]


@pytest.mark.parametrize(
    ("longitude", "expected_house"),
    [
        (10.0, 1),  # exactly on cusp 1 -> house 1
        (39.9, 1),  # just before cusp 2
        (40.0, 2),  # exactly on cusp 2 -> house 2
        (9.9, 12),  # just before wrapping back to cusp 1 -> still house 12
    ],
)
def test_house_from_cusps_even_spacing(longitude: float, expected_house: int) -> None:
    assert house_from_cusps(longitude, _EVEN_CUSPS) == expected_house


def test_house_from_cusps_handles_the_360_wraparound_house() -> None:
    # House 12 spans from cusp[11]=340 to cusp[0]=10, crossing 360/0.
    assert house_from_cusps(350.0, _EVEN_CUSPS) == 12
    assert house_from_cusps(5.0, _EVEN_CUSPS) == 12


def test_house_from_cusps_with_unequal_cusps() -> None:
    cusps = [0.0, 20.0, 50.0, 100.0, 130.0, 160.0, 190.0, 210.0, 240.0, 270.0, 300.0, 330.0]
    assert house_from_cusps(10.0, cusps) == 1
    assert house_from_cusps(25.0, cusps) == 2
    assert house_from_cusps(355.0, cusps) == 12  # wraps: cusp[11]=330 to cusp[0]=0
