"""Thin wrapper around pyswisseph: raw sidereal planetary longitudes only.

No astrology concepts (signs, houses, nakshatras) live here - just "where is
this body, in degrees, right now". Runs fully offline: FLG_MOSEPH selects
Swiss Ephemeris' built-in analytical model, which needs no external data
files (no download, no network call, ever).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

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
    """A body's sidereal ecliptic longitude/latitude and daily motion."""

    longitude: float  # degrees, 0-360
    latitude: float  # ecliptic latitude, degrees (0 for Rahu/Ketu - always on the ecliptic)
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
        lon, lat, _dist, lon_speed, _lat_speed, _dist_speed = values
        positions[planet] = RawPosition(longitude=lon % 360, latitude=lat, speed_longitude=lon_speed)

    node_id = swe.MEAN_NODE if node_type == NodeType.MEAN else swe.TRUE_NODE
    node_values, _flags = swe.calc_ut(jd, node_id, _CALC_FLAGS)
    rahu_lon, _lat, _dist, rahu_speed, _lat_speed, _dist_speed = node_values
    # Rahu/Ketu are always treated as exactly on the ecliptic (latitude 0) -
    # the standard convention, regardless of the node's tiny true latitude.
    positions[Planet.RAHU] = RawPosition(longitude=rahu_lon % 360, latitude=0.0, speed_longitude=rahu_speed)
    # Ketu is always exactly opposite Rahu - not an independent body in Swiss Ephemeris.
    positions[Planet.KETU] = RawPosition(
        longitude=(rahu_lon + 180) % 360, latitude=0.0, speed_longitude=rahu_speed
    )

    return positions


def ayanamsha_value(utc_dt: datetime, ayanamsha: str) -> float:
    """Degrees of precession at this moment for the given ayanamsha - the
    offset such that tropical_longitude = sidereal_longitude +
    ayanamsha_value (used by shadbala.py's Ayana Bala, which needs true
    declination and therefore tropical longitude)."""
    configure_ayanamsha(ayanamsha)
    jd = julian_day_ut(utc_dt)
    return float(swe.get_ayanamsa_ut(jd))


def mean_obliquity_degrees(utc_dt: datetime) -> float:
    """Mean obliquity of the ecliptic at the given moment - a standard,
    non-disputed astronomical constant that varies slowly by century (used
    to derive true declination from ecliptic longitude/latitude for Ayana
    Bala - see shadbala.py). IAU 1980 approximation, accurate to well
    within the precision this app needs."""
    jd = julian_day_ut(utc_dt)
    centuries = (jd - 2451545.0) / 36525.0
    return 23.439291 - 0.0130042 * centuries


def declination_degrees(tropical_longitude: float, ecliptic_latitude: float, obliquity: float) -> float:
    """True declination from tropical ecliptic longitude/latitude and
    obliquity - the standard spherical-astronomy conversion. Declination is
    a physical (equatorial) coordinate, independent of ayanamsha, so the
    longitude passed in must be TROPICAL (sidereal longitude + ayanamsha),
    not sidereal."""
    lon_rad = math.radians(tropical_longitude)
    lat_rad = math.radians(ecliptic_latitude)
    obl_rad = math.radians(obliquity)
    sin_dec = math.sin(lat_rad) * math.cos(obl_rad) + math.cos(lat_rad) * math.sin(obl_rad) * math.sin(lon_rad)
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_dec))))


def sunrise_sunset(
    utc_dt: datetime, latitude: float, longitude: float
) -> tuple[datetime, datetime, datetime]:
    """(sunrise, sunset, next_sunrise) bracketing `utc_dt`: the most recent
    sunrise at/before utc_dt, the sunset that follows it, and the sunrise
    that follows that sunset - i.e. utc_dt always falls in [sunrise,
    next_sunrise). Used for Kala Bala's day/night-dependent components
    (Nathonnata, Tribhaga, Hora Bala) - see shadbala.py. Offline (Moshier
    mode), like every other ephemeris call in this module.
    """
    geopos = (longitude, latitude, 0.0)
    start_jd = julian_day_ut(utc_dt) - 2.5
    _res, rise = swe.rise_trans(start_jd, swe.SUN, swe.CALC_RISE, geopos, flags=swe.FLG_MOSEPH)
    rise_jd = rise[0]
    _res, set_ = swe.rise_trans(rise_jd, swe.SUN, swe.CALC_SET, geopos, flags=swe.FLG_MOSEPH)
    set_jd = set_[0]
    _res, next_rise = swe.rise_trans(set_jd, swe.SUN, swe.CALC_RISE, geopos, flags=swe.FLG_MOSEPH)
    next_rise_jd = next_rise[0]

    target_jd = julian_day_ut(utc_dt)
    while next_rise_jd <= target_jd:
        rise_jd = next_rise_jd
        _res, set_ = swe.rise_trans(rise_jd, swe.SUN, swe.CALC_SET, geopos, flags=swe.FLG_MOSEPH)
        set_jd = set_[0]
        _res, next_rise = swe.rise_trans(set_jd, swe.SUN, swe.CALC_RISE, geopos, flags=swe.FLG_MOSEPH)
        next_rise_jd = next_rise[0]

    return _jd_to_utc_datetime(rise_jd), _jd_to_utc_datetime(set_jd), _jd_to_utc_datetime(next_rise_jd)


def _jd_to_utc_datetime(jd: float) -> datetime:
    """Naive datetime (implicit UTC, no tzinfo) - matches this codebase's
    convention everywhere else (BirthData.utc_datetime, TransitSegment,
    etc. are all naive)."""
    year, month, day, hour = swe.revjul(jd)
    total_seconds = round(hour * 3600)
    return datetime(year, month, day) + timedelta(seconds=total_seconds)


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
