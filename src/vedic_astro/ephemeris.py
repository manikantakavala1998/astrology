"""Thin wrapper around pyswisseph: raw sidereal planetary longitudes only.

No astrology concepts (signs, houses, nakshatras) live here - just "where is
this body, in degrees, right now". Runs fully offline: FLG_MOSEPH selects
Swiss Ephemeris' built-in analytical model, which needs no external data
files (no download, no network call, ever).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import swisseph as swe

from vedic_astro.models import HouseSystem, NodeType, Planet

_HOUSE_SYSTEM_CODES: dict[HouseSystem, bytes] = {
    HouseSystem.WHOLE_SIGN: b"W",
    HouseSystem.EQUAL: b"A",
    HouseSystem.PLACIDUS: b"P",
    HouseSystem.PORPHYRY: b"O",
}

_AYANAMSHA_MODES: dict[str, int] = {
    "lahiri": swe.SIDM_LAHIRI,
    "raman": swe.SIDM_RAMAN,
    "krishnamurti": swe.SIDM_KRISHNAMURTI,
}

_SWE_PLANET_IDS: dict[Planet, int] = {
    Planet.SUN: swe.SUN,
    Planet.MOON: swe.MOON,
    Planet.MARS: swe.MARS,
    Planet.MERCURY: swe.MERCURY,
    Planet.JUPITER: swe.JUPITER,
    Planet.VENUS: swe.VENUS,
    Planet.SATURN: swe.SATURN,
}

_CALC_FLAGS = swe.FLG_SIDEREAL | swe.FLG_SPEED | swe.FLG_MOSEPH


@dataclass(frozen=True)
class RawPosition:
    """A body's sidereal ecliptic longitude and daily motion, nothing else."""

    longitude: float  # degrees, 0-360
    speed_longitude: float  # degrees/day; negative means retrograde

    @property
    def retrograde(self) -> bool:
        return self.speed_longitude < 0


def julian_day_ut(utc_dt: datetime) -> float:
    hour = utc_dt.hour + utc_dt.minute / 60 + utc_dt.second / 3600
    return float(swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, hour))


def configure_ayanamsha(ayanamsha: str) -> None:
    mode = _AYANAMSHA_MODES.get(ayanamsha.lower())
    if mode is None:
        known = ", ".join(sorted(_AYANAMSHA_MODES))
        raise ValueError(f"Unsupported ayanamsha {ayanamsha!r}; known: {known}")
    swe.set_sid_mode(mode)


def planet_positions(
    utc_dt: datetime, ayanamsha: str, node_type: NodeType
) -> dict[Planet, RawPosition]:
    """Sidereal longitude + speed for all 9 grahas at the given UTC moment."""
    configure_ayanamsha(ayanamsha)
    jd = julian_day_ut(utc_dt)

    positions: dict[Planet, RawPosition] = {}
    for planet, swe_id in _SWE_PLANET_IDS.items():
        values, _flags = swe.calc_ut(jd, swe_id, _CALC_FLAGS)
        lon, _lat, _dist, lon_speed, _lat_speed, _dist_speed = values
        positions[planet] = RawPosition(longitude=lon % 360, speed_longitude=lon_speed)

    node_id = swe.MEAN_NODE if node_type == NodeType.MEAN else swe.TRUE_NODE
    node_values, _flags = swe.calc_ut(jd, node_id, _CALC_FLAGS)
    rahu_lon, _lat, _dist, rahu_speed, _lat_speed, _dist_speed = node_values
    positions[Planet.RAHU] = RawPosition(longitude=rahu_lon % 360, speed_longitude=rahu_speed)
    # Ketu is always exactly opposite Rahu - not an independent body in Swiss Ephemeris.
    positions[Planet.KETU] = RawPosition(
        longitude=(rahu_lon + 180) % 360, speed_longitude=rahu_speed
    )

    return positions


def ascendant_longitude(
    utc_dt: datetime, latitude: float, longitude: float, ayanamsha: str
) -> float:
    """Sidereal longitude of the ascendant (lagna), 0-360 degrees. Unaffected
    by house system choice - only the cusps (house_cusps below) differ."""
    configure_ayanamsha(ayanamsha)
    jd = julian_day_ut(utc_dt)
    _cusps, ascmc = swe.houses_ex(jd, latitude, longitude, b"W", swe.FLG_SIDEREAL)
    return float(ascmc[0]) % 360


def house_cusps(
    utc_dt: datetime, latitude: float, longitude: float, ayanamsha: str, house_system: HouseSystem
) -> list[float]:
    """The 12 house-cusp longitudes (degrees, 0-360) for the given house
    system. Not used for whole-sign (whole_sign_house() in rashi_bhava.py
    handles that case directly from the ascendant sign alone).
    """
    configure_ayanamsha(ayanamsha)
    jd = julian_day_ut(utc_dt)
    hsys = _HOUSE_SYSTEM_CODES[house_system]
    cusps, _ascmc = swe.houses_ex(jd, latitude, longitude, hsys, swe.FLG_SIDEREAL)
    return [float(c) % 360 for c in cusps]
