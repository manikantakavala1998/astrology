import pytest

from vedic_astro.dignity import planet_dignity
from vedic_astro.models import Planet, PlanetDignity, Sign


@pytest.mark.parametrize(
    ("planet", "sign", "expected"),
    [
        (Planet.SUN, Sign.ARIES, PlanetDignity.EXALTED),
        (Planet.SUN, Sign.LIBRA, PlanetDignity.DEBILITATED),
        (Planet.MOON, Sign.TAURUS, PlanetDignity.EXALTED),
        (Planet.MOON, Sign.SCORPIO, PlanetDignity.DEBILITATED),
        (Planet.MARS, Sign.CAPRICORN, PlanetDignity.EXALTED),
        (Planet.MARS, Sign.CANCER, PlanetDignity.DEBILITATED),
        (Planet.MERCURY, Sign.VIRGO, PlanetDignity.EXALTED),
        (Planet.MERCURY, Sign.PISCES, PlanetDignity.DEBILITATED),
        (Planet.JUPITER, Sign.CANCER, PlanetDignity.EXALTED),
        (Planet.JUPITER, Sign.CAPRICORN, PlanetDignity.DEBILITATED),
        (Planet.VENUS, Sign.PISCES, PlanetDignity.EXALTED),
        (Planet.VENUS, Sign.VIRGO, PlanetDignity.DEBILITATED),
        (Planet.SATURN, Sign.LIBRA, PlanetDignity.EXALTED),
        (Planet.SATURN, Sign.ARIES, PlanetDignity.DEBILITATED),
    ],
)
def test_exaltation_and_debilitation(planet: Planet, sign: Sign, expected: PlanetDignity) -> None:
    assert planet_dignity(planet, sign) == expected


@pytest.mark.parametrize(
    ("planet", "sign"),
    [
        (Planet.SUN, Sign.LEO),
        (Planet.MOON, Sign.CANCER),
        (Planet.MARS, Sign.ARIES),
        (Planet.MARS, Sign.SCORPIO),
        (Planet.MERCURY, Sign.GEMINI),
        (Planet.JUPITER, Sign.SAGITTARIUS),
        (Planet.JUPITER, Sign.PISCES),
        (Planet.VENUS, Sign.TAURUS),
        (Planet.VENUS, Sign.LIBRA),
        (Planet.SATURN, Sign.CAPRICORN),
        (Planet.SATURN, Sign.AQUARIUS),
    ],
)
def test_own_sign(planet: Planet, sign: Sign) -> None:
    assert planet_dignity(planet, sign) == PlanetDignity.OWN_SIGN


def test_neutral_when_neither_exalted_debilitated_nor_own_sign() -> None:
    assert planet_dignity(Planet.SUN, Sign.TAURUS) == PlanetDignity.NEUTRAL
    assert planet_dignity(Planet.SATURN, Sign.GEMINI) == PlanetDignity.NEUTRAL


@pytest.mark.parametrize("sign", list(Sign))
def test_rahu_and_ketu_always_neutral(sign: Sign) -> None:
    # Genuinely disputed across classical sources - not guessed here.
    assert planet_dignity(Planet.RAHU, sign) == PlanetDignity.NEUTRAL
    assert planet_dignity(Planet.KETU, sign) == PlanetDignity.NEUTRAL
