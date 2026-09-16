"""Jaimini astrology: Chara Karakas and Chara Dasha.

Jaimini is a distinct branch of Vedic astrology from everything else in this
engine (which is all Parashari-based: Vimshottari Dasha, whole-sign houses,
etc.). Only the two most well-established Jaimini techniques are implemented
here - Chara Karakas and Chara Dasha - using the standard classical method.
Several other Jaimini techniques (Sthira Karakas, Sthira Dasha, Yogada
graha, Kevala graha) were deliberately left out: unlike the Ashtakoot kootas
elsewhere in this engine (where the concept was clear and only fine
point-values were uncertain), confidence in the exact definitions of those
four was too low to implement responsibly.

ACCURACY NOTE: Chara Dasha's starting sign is taken here as the Ascendant
(Lagna) - the most common simplification used by most practical Jaimini
software. Some Jaimini methods instead compare the strength of the Lagna
and the 7th house to choose the starting sign; that alternative is not
implemented here. Cross-check against a trusted Jaimini source before
relying on this for a real decision, same as the Ashtakoot matching module.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from vedic_astro.models import SIGNS_IN_ORDER, CharaDashaPeriod, CharaKaraka, Planet, PlanetPosition, Sign
from vedic_astro.rashi_bhava import RASHI_LORD

DAYS_PER_YEAR = 365.2425  # average Gregorian year, same convention as dasha.py

# The 7 classical grahas used for Chara Karakas - Rahu/Ketu are excluded,
# the standard scheme (an 8-karaka scheme including Rahu also exists but is
# not universally used, so it's not implemented here).
_KARAKA_PLANETS = (
    Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY,
    Planet.JUPITER, Planet.VENUS, Planet.SATURN,
)

_KARAKA_NAMES = (
    "Atmakaraka", "Amatyakaraka", "Bhratrikaraka", "Matrikaraka",
    "Putrikaraka", "Gnatikaraka", "Darakaraka",
)


def compute_chara_karakas(planets: list[PlanetPosition]) -> list[CharaKaraka]:
    """Ranks the 7 classical grahas by degree-within-sign, highest first -
    Atmakaraka (highest) through Darakaraka (lowest)."""
    by_degree = sorted(
        (p for p in planets if p.planet in _KARAKA_PLANETS),
        key=lambda p: p.degree_in_sign,
        reverse=True,
    )
    return [
        CharaKaraka(planet=p.planet, karaka=name, degree_in_sign=p.degree_in_sign)
        for p, name in zip(by_degree, _KARAKA_NAMES)
    ]


def _years_to_timedelta(years: float) -> timedelta:
    return timedelta(days=years * DAYS_PER_YEAR)


def _sign_duration_years(sign: Sign, lord_sign: Sign) -> float:
    """Count from `sign` to `lord_sign`: forward if `sign` is odd (1-indexed
    zodiac position), backward if even. The inclusive count (1-12) is the
    duration in years, except a planet in its own sign (count=1) uses the
    classical exception of 12 years instead.
    """
    sign_index = SIGNS_IN_ORDER.index(sign)
    lord_index = SIGNS_IN_ORDER.index(lord_sign)
    is_odd = sign_index % 2 == 0  # 0-indexed even position = 1-indexed odd sign

    if is_odd:
        count = ((lord_index - sign_index) % 12) + 1
    else:
        count = ((sign_index - lord_index) % 12) + 1

    return 12.0 if count == 1 else float(count)


def compute_chara_dasha(
    ascendant_sign: Sign, planets: list[PlanetPosition], birth_datetime: datetime
) -> list[CharaDashaPeriod]:
    """One full 12-sign Chara Dasha cycle, starting from the Ascendant sign,
    proceeding forward through the zodiac. Mahadasha level only (no
    antardasha sub-periods in this pass).
    """
    ascendant_index = SIGNS_IN_ORDER.index(ascendant_sign)
    periods: list[CharaDashaPeriod] = []
    cursor = birth_datetime

    for offset in range(12):
        sign = SIGNS_IN_ORDER[(ascendant_index + offset) % 12]
        lord = RASHI_LORD[sign]
        lord_position = next(p for p in planets if p.planet == lord)
        years = _sign_duration_years(sign, lord_position.sign)
        period_end = cursor + _years_to_timedelta(years)
        periods.append(
            CharaDashaPeriod(sign=sign, lord=lord, years=years, start=cursor, end=period_end)
        )
        cursor = period_end

    return periods
