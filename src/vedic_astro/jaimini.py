"""Degree-ranked karakas and Chara Dasha (K. N. Rao convention).

Sign aspects, arudhas, Argala and other declared conventions are composed
in jaimini_report.py. Jaimini uses whole signs, independent of bhava cusps.
See docs/jaimini.md for calculation conventions and verification sources.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from vedic_astro.models import SIGNS_IN_ORDER, CharaDashaPeriod, CharaKaraka, Planet, PlanetPosition, Sign
from vedic_astro.rashi_bhava import RASHI_LORD

DAYS_PER_YEAR = 365.2425  # average Gregorian year, same convention as dasha.py

# The 7 classical grahas used for Chara Karakas - Rahu/Ketu are excluded,
# An optional eighth role includes Rahu with reversed advancement.
_KARAKA_PLANETS = (
    Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY,
    Planet.JUPITER, Planet.VENUS, Planet.SATURN,
)

_KARAKA_NAMES = (
    "Atmakaraka", "Amatyakaraka", "Bhratrikaraka", "Matrikaraka",
    "Putrikaraka", "Gnatikaraka", "Darakaraka",
)

# Odd-footed is NOT zodiacal odd/even parity.
ODD_FOOTED = {Sign.ARIES, Sign.TAURUS, Sign.GEMINI, Sign.LIBRA, Sign.SCORPIO, Sign.SAGITTARIUS}


def step(sign: Sign, offset: int) -> Sign:
    return SIGNS_IN_ORDER[(SIGNS_IN_ORDER.index(sign) + offset) % 12]


def chara_direction(sign: Sign) -> int:
    """Period order is determined by the ninth sign from the starting sign."""
    return 1 if step(sign, 8) in ODD_FOOTED else -1


def compute_chara_karakas(planets: list[PlanetPosition], count: int = 7) -> list[CharaKaraka]:
    """Seven excludes nodes; eight includes Rahu ranked by 30 - natal degree.

    Exact ties share the preceding rank and leave the next role vacant. Full
    unrounded degrees are used, not displayed arcminute values.
    """
    if count not in (7, 8):
        raise ValueError("Choose seven or eight karakas.")
    names = _KARAKA_NAMES if count == 7 else (*_KARAKA_NAMES[:4], "Pitrikaraka", *_KARAKA_NAMES[4:])
    eligible = (*_KARAKA_PLANETS, Planet.RAHU) if count == 8 else _KARAKA_PLANETS
    def advancement(p: PlanetPosition) -> float:
        return 30 - p.degree_in_sign if p.planet == Planet.RAHU else p.degree_in_sign
    by_degree = sorted(
        (p for p in planets if p.planet in eligible),
        key=advancement,
        reverse=True,
    )
    return [
        CharaKaraka(planet=p.planet, karaka=names[sum(advancement(q) > advancement(p) for q in by_degree)],
                    degree_in_sign=p.degree_in_sign)
        for p in by_degree
    ]


def _years_to_timedelta(years: float) -> timedelta:
    return timedelta(days=years * DAYS_PER_YEAR)


def _sign_duration_years(sign: Sign, lord_sign: Sign) -> float:
    """Directed inclusive count minus one; lord in own sign gives 12 years."""
    sign_index = SIGNS_IN_ORDER.index(sign)
    lord_index = SIGNS_IN_ORDER.index(lord_sign)
    distance = ((lord_index - sign_index) if sign in ODD_FOOTED else (sign_index - lord_index)) % 12
    return float(distance or 12)


def compute_chara_dasha(
    ascendant_sign: Sign, planets: list[PlanetPosition], birth_datetime: datetime
) -> list[CharaDashaPeriod]:
    """One cycle from Lagna, ninth-sign direction, seven classical lords.

    K. N. Rao convention omits exaltation/debilitation duration corrections.
    """
    ascendant_index = SIGNS_IN_ORDER.index(ascendant_sign)
    periods: list[CharaDashaPeriod] = []
    cursor = birth_datetime

    for offset in range(12):
        sign = SIGNS_IN_ORDER[(ascendant_index + chara_direction(ascendant_sign) * offset) % 12]
        lord = RASHI_LORD[sign]
        lord_position = next(p for p in planets if p.planet == lord)
        years = _sign_duration_years(sign, lord_position.sign)
        period_end = cursor + _years_to_timedelta(years)
        periods.append(
            CharaDashaPeriod(sign=sign, lord=lord, years=years, start=cursor, end=period_end)
        )
        cursor = period_end

    return periods
