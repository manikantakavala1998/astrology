import pytest

from vedic_astro.divisional_charts import (
    VARGA_REGISTRY,
    dasamsa_sign,
    drekkana_sign,
    dwadasamsa_sign,
    saptamsa_sign,
    trimsamsa_sign,
)
from vedic_astro.models import Sign


@pytest.mark.parametrize(
    ("longitude", "expected"),
    [
        (0.0, Sign.ARIES),  # Aries, part 0 -> same sign
        (15.0, Sign.LEO),  # Aries, part 1 -> 5th sign from Aries
        (25.0, Sign.SAGITTARIUS),  # Aries, part 2 -> 9th sign from Aries
        (45.0, Sign.VIRGO),  # Taurus, part 1 -> 5th sign from Taurus
        (55.0, Sign.CAPRICORN),  # Taurus, part 2 -> 9th sign from Taurus
    ],
)
def test_drekkana_sign(longitude: float, expected: Sign) -> None:
    assert drekkana_sign(longitude) == expected


def test_drekkana_wraps_at_360() -> None:
    assert drekkana_sign(360.0) == drekkana_sign(0.0)


@pytest.mark.parametrize(
    ("longitude", "expected"),
    [
        (0.0, Sign.ARIES),  # Aries (odd), part 0 -> anchor is Aries itself
        (30.0, Sign.SCORPIO),  # Taurus (even), part 0 -> anchor is its 7th (opposite) sign
    ],
)
def test_saptamsa_sign(longitude: float, expected: Sign) -> None:
    assert saptamsa_sign(longitude) == expected


def test_saptamsa_wraps_at_360() -> None:
    assert saptamsa_sign(360.0) == saptamsa_sign(0.0)


@pytest.mark.parametrize(
    ("longitude", "expected"),
    [
        (0.0, Sign.ARIES),  # Aries (odd), part 0 -> anchor is Aries itself
        (30.0, Sign.CAPRICORN),  # Taurus (even), part 0 -> anchor is its 9th sign
    ],
)
def test_dasamsa_sign(longitude: float, expected: Sign) -> None:
    assert dasamsa_sign(longitude) == expected


def test_dasamsa_wraps_at_360() -> None:
    assert dasamsa_sign(360.0) == dasamsa_sign(0.0)


@pytest.mark.parametrize(
    ("longitude", "expected"),
    [
        (0.0, Sign.ARIES),  # Aries, part 0 -> same sign
        (2.5, Sign.TAURUS),  # Aries, part 1 -> next sign forward
    ],
)
def test_dwadasamsa_sign(longitude: float, expected: Sign) -> None:
    assert dwadasamsa_sign(longitude) == expected


def test_dwadasamsa_cycles_twelve_times_per_sign() -> None:
    signs_seen = {dwadasamsa_sign(i * 2.5) for i in range(12)}
    assert len(signs_seen) == 12


def test_dwadasamsa_wraps_at_360() -> None:
    assert dwadasamsa_sign(360.0) == dwadasamsa_sign(0.0)


@pytest.mark.parametrize(
    ("longitude", "expected"),
    [
        (2.0, Sign.ARIES),  # Gemini (odd), degree 2 -> Mars segment -> Aries
        (22.0, Sign.GEMINI),  # Gemini (odd), degree 22 -> Mercury segment -> Gemini (own sign)
        (5.0, Sign.AQUARIUS),  # Aries (odd), degree 5 (boundary) -> Saturn segment, not Mars
        (98.0, Sign.VIRGO),  # Cancer (even), degree 8 -> Mercury segment -> Virgo
        (90.0, Sign.TAURUS),  # Cancer (even), degree 0 -> Venus segment -> Taurus
    ],
)
def test_trimsamsa_sign(longitude: float, expected: Sign) -> None:
    assert trimsamsa_sign(longitude) == expected


def test_trimsamsa_wraps_at_360() -> None:
    assert trimsamsa_sign(360.0) == trimsamsa_sign(0.0)


def test_varga_registry_has_all_23_standard_charts() -> None:
    assert len(VARGA_REGISTRY) == 23
    codes = [spec.code for spec in VARGA_REGISTRY]
    assert len(set(codes)) == 23  # no duplicates
    assert codes[0] == "D1"
    assert codes[-1] == "D144"


def test_varga_registry_confidently_built_charts_have_a_sign_fn() -> None:
    built_codes = {"D1", "D2", "D3", "D7", "D9", "D10", "D12", "D30"}
    for spec in VARGA_REGISTRY:
        if spec.code in built_codes:
            assert spec.sign_fn is not None, spec.code
            assert spec.held_reason is None, spec.code


def test_varga_registry_held_charts_have_no_sign_fn_and_a_reason() -> None:
    built_codes = {"D1", "D2", "D3", "D7", "D9", "D10", "D12", "D30"}
    for spec in VARGA_REGISTRY:
        if spec.code not in built_codes:
            assert spec.sign_fn is None, spec.code
            assert spec.held_reason, spec.code
