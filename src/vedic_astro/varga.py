"""Navamsa (D9) and Hora (D2); see divisional_charts.py for the full registry."""

from __future__ import annotations

from vedic_astro.models import SIGNS_IN_ORDER, Planet, Sign

NAVAMSA_DIVISIONS = 108  # 12 signs x 9 navamsas per sign
NAVAMSA_SPAN = 360 / NAVAMSA_DIVISIONS  # 3d20', same width as a nakshatra pada
_EPSILON = 1e-9


def navamsa_sign(longitude: float) -> Sign:
    """D9 sign for a given sidereal longitude.

    Equivalent to the classical movable/fixed/dual starting-sign rule, but
    expressed as one continuous 108-division cycle around the whole zodiac -
    the two are mathematically the same, this form is just easier to get
    right in code.
    """
    longitude = longitude % 360
    division_index = min(int((longitude + _EPSILON) // NAVAMSA_SPAN), NAVAMSA_DIVISIONS - 1)
    return SIGNS_IN_ORDER[division_index % 12]


def hora_sign(longitude: float) -> Sign:
    """D2 (Hora) sign - used for assessing wealth. Unlike the other vargas,
    Hora only ever resolves to Leo (Sun's hora) or Cancer (Moon's hora).

    Classical (Parashari) rule: split each 30-degree sign into two 15-degree
    halves. For an odd sign (Aries, Gemini, Leo, Libra, Sagittarius,
    Aquarius) the first half is Leo's hora and the second is Cancer's; for
    an even sign (Taurus, Cancer, Virgo, Scorpio, Capricorn, Pisces) it's
    the other way around.
    """
    longitude = longitude % 360
    sign_index = min(int((longitude + _EPSILON) // 30), 11)
    degree_in_sign = longitude - sign_index * 30
    is_odd_sign = sign_index % 2 == 0  # 0-indexed even position = 1-indexed odd sign
    first_half = degree_in_sign < 15

    if is_odd_sign:
        return Sign.LEO if first_half else Sign.CANCER
    return Sign.CANCER if first_half else Sign.LEO


def hora_lord(longitude: float) -> Planet:
    """Ruling planet of the D2 Hora sign - always Sun (Leo hora) or Moon (Cancer hora)."""
    return Planet.SUN if hora_sign(longitude) == Sign.LEO else Planet.MOON
