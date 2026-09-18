"""Display-only sign attributes (cardinal direction + element symbol) for
the chart grids - not used in any calculation, per the user's own exact
table."""

from __future__ import annotations

from vedic_astro.models import Sign

FIRE = "\U0001F525"  # fire emoji
EARTH = "\U0001F30D"  # earth emoji
AIR = "\U0001F4A8"  # dash/wind emoji
WATER = "\U0001F4A7"  # droplet emoji

# (direction letter, element symbol), per the user's exact spec.
SIGN_DIRECTION: dict[Sign, str] = {
    Sign.ARIES: "E",
    Sign.TAURUS: "S",
    Sign.GEMINI: "W",
    Sign.CANCER: "N",
    Sign.LEO: "E",
    Sign.VIRGO: "S",
    Sign.LIBRA: "W",
    Sign.SCORPIO: "N",
    Sign.SAGITTARIUS: "E",
    Sign.CAPRICORN: "S",
    Sign.AQUARIUS: "W",
    Sign.PISCES: "N",
}

SIGN_ELEMENT_SYMBOL: dict[Sign, str] = {
    Sign.ARIES: FIRE,
    Sign.TAURUS: EARTH,
    Sign.GEMINI: AIR,
    Sign.CANCER: WATER,
    Sign.LEO: FIRE,
    Sign.VIRGO: EARTH,
    Sign.LIBRA: AIR,
    Sign.SCORPIO: WATER,
    Sign.SAGITTARIUS: FIRE,
    Sign.CAPRICORN: EARTH,
    Sign.AQUARIUS: AIR,
    Sign.PISCES: WATER,
}

SIGN_ELEMENT_NAME: dict[Sign, str] = {
    Sign.ARIES: "Fire",
    Sign.TAURUS: "Earth",
    Sign.GEMINI: "Air",
    Sign.CANCER: "Water",
    Sign.LEO: "Fire",
    Sign.VIRGO: "Earth",
    Sign.LIBRA: "Air",
    Sign.SCORPIO: "Water",
    Sign.SAGITTARIUS: "Fire",
    Sign.CAPRICORN: "Earth",
    Sign.AQUARIUS: "Air",
    Sign.PISCES: "Water",
}
