"""Sign (rashi) and house (bhava) assignment from ecliptic longitude."""

from __future__ import annotations

from vedic_astro.models import SIGNS_IN_ORDER, Ascendant, Planet, Sign

# Classical rashi (sign) lordships - shared by any module that needs a
# planet's own-sign rulership (matching.py's Graha Maitri koota, jaimini.py's
# Chara Dasha), so this table exists in exactly one place.
RASHI_LORD: dict[Sign, Planet] = {
    Sign.ARIES: Planet.MARS, Sign.SCORPIO: Planet.MARS,
    Sign.TAURUS: Planet.VENUS, Sign.LIBRA: Planet.VENUS,
    Sign.GEMINI: Planet.MERCURY, Sign.VIRGO: Planet.MERCURY,
    Sign.CANCER: Planet.MOON,
    Sign.LEO: Planet.SUN,
    Sign.SAGITTARIUS: Planet.JUPITER, Sign.PISCES: Planet.JUPITER,
    Sign.CAPRICORN: Planet.SATURN, Sign.AQUARIUS: Planet.SATURN,
}


def sign_for_longitude(longitude: float) -> Sign:
    index = int(longitude // 30) % 12
    return SIGNS_IN_ORDER[index]


def degree_in_sign(longitude: float) -> float:
    return longitude % 30


def whole_sign_house(planet_sign: Sign, ascendant_sign: Sign) -> int:
    """House number (1-12) under the whole-sign system.

    The ascendant's sign is house 1 in its entirety; every other sign is
    simply counted forward from there - there is no sub-division by degree.
    """
    asc_index = SIGNS_IN_ORDER.index(ascendant_sign)
    planet_index = SIGNS_IN_ORDER.index(planet_sign)
    return ((planet_index - asc_index) % 12) + 1


def house_from_cusps(longitude: float, cusps: list[float]) -> int:
    """House number (1-12) under a cusp-based system (Equal/Placidus/
    Porphyry): cusps[i] is the start of house i+1. Handles the case where a
    house's span crosses the 360/0 degree boundary.
    """
    longitude = longitude % 360
    for house_index in range(12):
        start = cusps[house_index]
        end = cusps[(house_index + 1) % 12]
        if start <= end:
            if start <= longitude < end:
                return house_index + 1
        else:  # this house's span wraps past 360 -> 0
            if longitude >= start or longitude < end:
                return house_index + 1
    return 12  # unreachable with 12 valid cusps spanning the full circle


def build_ascendant(longitude: float) -> Ascendant:
    return Ascendant(
        longitude=longitude,
        sign=sign_for_longitude(longitude),
        degree_in_sign=degree_in_sign(longitude),
    )
