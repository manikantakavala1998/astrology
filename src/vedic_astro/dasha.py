"""Vimshottari Dasha: the 120-year planetary period timeline.

The mahadasha (major period) in effect at birth is determined by the Moon's
nakshatra lord and how far the Moon already was through that nakshatra; the
remaining 8 mahadashas follow in the fixed cycle, each subdivided into 9
antardashas (sub-periods) using the standard proportional formula.

The full classical system actually has 5 levels - Mahadasha, Antardasha,
Pratyantardasha, Sookshma Dasha, Prana Dasha - each subdividing its parent
with the exact same rule. Only Mahadasha+Antardasha are computed eagerly for
a whole chart (9x9 = 81 periods, reasonable); a full 5-level tree would be
9^5 = 59,049 Prana-level periods, impractical to compute/render at once.
Deeper levels (compute_deeper_sub_periods) are therefore computed on demand,
scoped to one specific Mahadasha branch at a time - see web/app.py's
/dasha-detail route.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from vedic_astro.models import DashaPeriod, DashaSubPeriod, Planet, VimshottariDasha
from vedic_astro.nakshatra import DASHA_LORD_CYCLE, NAKSHATRA_SPAN, nakshatra_for_longitude

DAYS_PER_YEAR = 365.2425  # average Gregorian year

DASHA_YEARS: dict[Planet, float] = {
    Planet.KETU: 7, Planet.VENUS: 20, Planet.SUN: 6, Planet.MOON: 10,
    Planet.MARS: 7, Planet.RAHU: 18, Planet.JUPITER: 16, Planet.SATURN: 19,
    Planet.MERCURY: 17,
}

TOTAL_CYCLE_YEARS = sum(DASHA_YEARS.values())  # 120


def _years_to_timedelta(years: float) -> timedelta:
    return timedelta(days=years * DAYS_PER_YEAR)


def _subdivide(lord: Planet, start: datetime, years: float) -> list[DashaSubPeriod]:
    """One level of subdivision: 9 sub-periods starting from `lord`'s own
    position in the cycle, each proportional to its lord's classical years
    out of the parent period's total - the same rule at every dasha level.
    """
    start_index = DASHA_LORD_CYCLE.index(lord)
    sub_periods: list[DashaSubPeriod] = []
    cursor = start
    for offset in range(9):
        sub_lord = DASHA_LORD_CYCLE[(start_index + offset) % 9]
        sub_years = years * DASHA_YEARS[sub_lord] / TOTAL_CYCLE_YEARS
        sub_end = cursor + _years_to_timedelta(sub_years)
        sub_periods.append(DashaSubPeriod(planet=sub_lord, start=cursor, end=sub_end))
        cursor = sub_end
    return sub_periods


def compute_deeper_sub_periods(
    lord: Planet, start: datetime, years: float, levels: int
) -> list[DashaSubPeriod]:
    """Recursively subdivide `levels` levels deep - e.g. starting from an
    Antardasha (lord, start, years) with levels=3 gives Pratyantardasha,
    each holding its own Sookshma, each of those holding its own Prana.
    Computed on demand for one branch at a time (see module docstring).
    """
    sub_periods = _subdivide(lord, start, years)
    if levels > 1:
        for period in sub_periods:
            period_years = (period.end - period.start).total_seconds() / (DAYS_PER_YEAR * 86400)
            period.sub_periods = compute_deeper_sub_periods(
                period.planet, period.start, period_years, levels - 1
            )
    return sub_periods


def compute_vimshottari_dasha(moon_longitude: float, birth_datetime: datetime) -> VimshottariDasha:
    moon_longitude = moon_longitude % 360
    nakshatra = nakshatra_for_longitude(moon_longitude)
    elapsed_within_nakshatra = moon_longitude - (nakshatra.index - 1) * NAKSHATRA_SPAN
    elapsed_fraction = max(0.0, min(1.0, elapsed_within_nakshatra / NAKSHATRA_SPAN))

    first_lord = nakshatra.lord
    first_lord_years = DASHA_YEARS[first_lord]
    elapsed_years = elapsed_fraction * first_lord_years
    first_start = birth_datetime - _years_to_timedelta(elapsed_years)

    start_index = DASHA_LORD_CYCLE.index(first_lord)
    periods: list[DashaPeriod] = []
    cursor = first_start
    for offset in range(9):
        lord = DASHA_LORD_CYCLE[(start_index + offset) % 9]
        lord_years = DASHA_YEARS[lord]
        period_end = cursor + _years_to_timedelta(lord_years)
        periods.append(
            DashaPeriod(
                planet=lord,
                start=cursor,
                end=period_end,
                sub_periods=_subdivide(lord, cursor, lord_years),
            )
        )
        cursor = period_end

    return VimshottariDasha(periods=periods)
