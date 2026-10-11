"""Planetary horas: twelve daylight and twelve nighttime intervals.

All boundaries use the same local sunrise/sunset events as Hora Bala. UTC is
used during interval selection; presentation datetimes use the birth offset.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from vedic_astro.ephemeris import sunrise_sunset
from vedic_astro.models import BirthData, BirthHora, Planet

HORA_ORDER = [Planet.SATURN, Planet.JUPITER, Planet.MARS, Planet.SUN,
              Planet.VENUS, Planet.MERCURY, Planet.MOON]
WEEKDAY_LORDS = {0: Planet.MOON, 1: Planet.MARS, 2: Planet.MERCURY,
                 3: Planet.JUPITER, 4: Planet.VENUS, 5: Planet.SATURN, 6: Planet.SUN}


@dataclass(frozen=True)
class HoraInterval:
    lord: Planet
    index: int
    phase: Literal["Day", "Night"]
    start: datetime
    end: datetime


def hora_interval(birth_utc: datetime, sunrise: datetime, sunset: datetime,
                  next_sunrise: datetime, sunrise_local_weekday: int) -> HoraInterval:
    """Select a half-open hora interval: start <= birth < end.

    Rounded datetime boundaries are also used for selection, so a birth exactly
    on an internal boundary always belongs to the new hora, including when the
    daylight/nighttime length is not divisible into whole seconds.
    """
    if not sunrise < sunset < next_sunrise or not sunrise <= birth_utc < next_sunrise:
        raise ValueError("Sunrise and sunset must bracket the birth time.")
    daytime = birth_utc < sunset
    start, end = (sunrise, sunset) if daytime else (sunset, next_sunrise)
    boundaries = [start + (end - start) * (part / 12) for part in range(13)]
    part = bisect_right(boundaries, birth_utc) - 1
    index = part + (0 if daytime else 12)
    day_lord = WEEKDAY_LORDS[sunrise_local_weekday]
    lord = HORA_ORDER[(HORA_ORDER.index(day_lord) + index) % 7]
    return HoraInterval(lord, index + 1, "Day" if daytime else "Night",
                        boundaries[part], boundaries[part + 1])


def compute_birth_hora(birth: BirthData) -> BirthHora:
    rise, sunset, next_rise = sunrise_sunset(birth.utc_datetime, birth.latitude, birth.longitude)
    offset = timedelta(hours=birth.utc_offset_hours)
    local_rise = rise + offset
    interval = hora_interval(birth.utc_datetime, rise, sunset, next_rise, local_rise.weekday())
    return BirthHora(
        lord=interval.lord, index=interval.index, phase=interval.phase,
        start=interval.start + offset, end=interval.end + offset,
        duration_minutes=(interval.end - interval.start).total_seconds() / 60,
        sunrise=local_rise, sunset=sunset + offset, next_sunrise=next_rise + offset,
        sunrise_day_lord=WEEKDAY_LORDS[local_rise.weekday()],
    )
