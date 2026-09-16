import pytest

from vedic_astro.models import Planet, Sign
from vedic_astro.varga import hora_lord, hora_sign, navamsa_sign


@pytest.mark.parametrize(
    ("longitude", "expected"),
    [
        (0.0, Sign.ARIES),  # movable sign: navamsa count starts at itself
        (30.0, Sign.CAPRICORN),  # fixed sign (Taurus): starts at 9th sign from it
        (60.0, Sign.LIBRA),  # dual sign (Gemini): starts at 5th sign from it
        (5.0, Sign.TAURUS),  # Aries, 2nd pada -> next sign forward
    ],
)
def test_navamsa_sign(longitude: float, expected: Sign) -> None:
    assert navamsa_sign(longitude) == expected


def test_navamsa_cycles_nine_times_per_sign() -> None:
    # Each 30-degree sign contains exactly 9 navamsa divisions of 3d20' each.
    signs_seen = {navamsa_sign(i * (10 / 3)) for i in range(9)}
    assert len(signs_seen) == 9


def test_wraps_at_360() -> None:
    assert navamsa_sign(360.0) == navamsa_sign(0.0)


@pytest.mark.parametrize(
    ("longitude", "expected"),
    [
        (5.0, Sign.LEO),  # Aries (odd sign), 1st half -> Leo
        (20.0, Sign.CANCER),  # Aries (odd sign), 2nd half -> Cancer
        (35.0, Sign.CANCER),  # Taurus (even sign), 1st half -> Cancer
        (50.0, Sign.LEO),  # Taurus (even sign), 2nd half -> Leo
        (125.0, Sign.LEO),  # Leo itself (odd sign), 1st half -> Leo
        (95.0, Sign.CANCER),  # Cancer itself (even sign), 1st half -> Cancer
    ],
)
def test_hora_sign(longitude: float, expected: Sign) -> None:
    assert hora_sign(longitude) == expected


def test_hora_sign_only_ever_leo_or_cancer() -> None:
    seen = {hora_sign(i * 7.3) for i in range(50)}
    assert seen <= {Sign.LEO, Sign.CANCER}


def test_hora_lord_matches_sign() -> None:
    assert hora_lord(5.0) == Planet.SUN  # Leo hora -> Sun
    assert hora_lord(20.0) == Planet.MOON  # Cancer hora -> Moon


def test_hora_sign_wraps_at_360() -> None:
    assert hora_sign(360.0) == hora_sign(0.0)
