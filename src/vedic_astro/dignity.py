"""Planet dignity (Ucha/Neecha): sign-level exaltation/debilitation only.

Exaltation/debilitation sign + deep-degree cross-verified against two
independent sources, matches classical BPHS consensus - see the plan
that introduced this module. Rahu/Ketu are deliberately excluded (always
NEUTRAL): their exaltation/debilitation is genuinely disputed across at
least 3 incompatible classical traditions (Taurus/Scorpio vs. both-in-
Scorpio vs. Gemini/Sagittarius), so their sign-level dignity stays neutral.

Not implemented (deliberately out of scope, more complex/disputed):
a continuous exaltation-strength score, and Neecha Bhanga (debilitation
cancellation).
"""

from __future__ import annotations

from vedic_astro.models import Planet, PlanetDignity, Sign
from vedic_astro.rashi_bhava import RASHI_LORD

EXALTATION_SIGN: dict[Planet, Sign] = {
    Planet.SUN: Sign.ARIES,
    Planet.MOON: Sign.TAURUS,
    Planet.MARS: Sign.CAPRICORN,
    Planet.MERCURY: Sign.VIRGO,
    Planet.JUPITER: Sign.CANCER,
    Planet.VENUS: Sign.PISCES,
    Planet.SATURN: Sign.LIBRA,
}

# Debilitation is always the opposite (7th) sign from exaltation.
DEBILITATION_SIGN: dict[Planet, Sign] = {
    Planet.SUN: Sign.LIBRA,
    Planet.MOON: Sign.SCORPIO,
    Planet.MARS: Sign.CANCER,
    Planet.MERCURY: Sign.PISCES,
    Planet.JUPITER: Sign.CAPRICORN,
    Planet.VENUS: Sign.VIRGO,
    Planet.SATURN: Sign.ARIES,
}

# The deep-exaltation degree - identical in both the exaltation and
# debilitation sign (a planet exalted at 10 degrees of Aries is debilitated
# at 10 degrees of Libra).
DEEP_DIGNITY_DEGREE: dict[Planet, float] = {
    Planet.SUN: 10.0,
    Planet.MOON: 3.0,
    Planet.MARS: 28.0,
    Planet.MERCURY: 15.0,
    Planet.JUPITER: 5.0,
    Planet.VENUS: 27.0,
    Planet.SATURN: 20.0,
}


def planet_dignity(planet: Planet, sign: Sign) -> PlanetDignity:
    if EXALTATION_SIGN.get(planet) == sign:
        return PlanetDignity.EXALTED
    if DEBILITATION_SIGN.get(planet) == sign:
        return PlanetDignity.DEBILITATED
    if RASHI_LORD.get(sign) == planet:
        return PlanetDignity.OWN_SIGN
    return PlanetDignity.NEUTRAL
