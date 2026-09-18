"""Shadbala: the six-fold classical planetary strength, in Virupas (60
Virupas = 1 Rupa). Computed only for the 7 classical planets (Sun through
Saturn) - Rahu/Ketu are excluded, matching dignity.py's own exclusion of
the lunar nodes from dignity scoring.

Scope decisions (see the plan that introduced this module for the full
research/reasoning behind each):
- Masa Bala and Varsha Bala (month/year-lord strength, classically part of
  Kala Bala) are NOT implemented - the lord-determination algorithm needs
  an Ahargana epoch-counting scheme that wasn't found in a confirmed
  source, so nothing is guessed here.
- Yuddha Bala (planetary war) is NOT implemented - at least 3 mutually
  incompatible winner-determination rules exist across sources; guessing
  wrong would flip which planet gets a bonus vs. penalty, a real
  correctness risk, not just an omission.
- Chesta Bala for the 5 non-luminary planets uses a flagged 4-state
  simplification (retrograde / stationary / slower-than-mean / faster-
  than-mean) rather than the full classical 8-state scale, since the
  exact speed-ratio thresholds separating the 8 states weren't
  recoverable from any source.
- Ayana Bala uses the true-declination-based formula (not the alternate
  tropical-longitude "3-khanda" method, which is mechanically different
  and whose own khanda totals don't cleanly cap at 60).
- Drik Bala reuses this app's existing `chart.aspects` (discrete Graha
  Drishti, already correctly implementing the classical special-aspect
  house rules) rather than an independently-reconstructed continuous
  angular formula - the continuous-formula reconstruction researched for
  this module had an internal inconsistency around the exact special-
  aspect bonus that couldn't be cleanly resolved, whereas the discrete
  fixed-fraction model (universal aspect = full strength, special aspects
  at fixed fractions) is corroborated by multiple sources and reuses
  already-tested infrastructure.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from vedic_astro.dignity import DEEP_DIGNITY_DEGREE, EXALTATION_SIGN
from vedic_astro.ephemeris import (
    ayanamsha_value,
    declination_degrees,
    mean_obliquity_degrees,
    sunrise_sunset,
)
from vedic_astro.models import (
    BirthData,
    KalaBalaBreakdown,
    Planet,
    PlanetAspect,
    PlanetPosition,
    ShadbalaResult,
    Sign,
    SthanaBalaBreakdown,
)
from vedic_astro.planetary_relations import panchadha_relation
from vedic_astro.rashi_bhava import RASHI_LORD, whole_sign_house

_CLASSICAL_PLANETS: list[Planet] = [
    Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY,
    Planet.JUPITER, Planet.VENUS, Planet.SATURN,
]

MASCULINE: set[Planet] = {Planet.SUN, Planet.MARS, Planet.JUPITER}
FEMININE: set[Planet] = {Planet.MOON, Planet.VENUS}
NEUTER: set[Planet] = {Planet.MERCURY, Planet.SATURN}

# Moolatrikona sign + degree range - HIGH confidence, cross-verified
# against multiple independent sources, standard BPHS table.
MOOLATRIKONA_SIGN: dict[Planet, Sign] = {
    Planet.SUN: Sign.LEO, Planet.MOON: Sign.TAURUS, Planet.MARS: Sign.ARIES,
    Planet.MERCURY: Sign.VIRGO, Planet.JUPITER: Sign.SAGITTARIUS,
    Planet.VENUS: Sign.LIBRA, Planet.SATURN: Sign.AQUARIUS,
}
MOOLATRIKONA_RANGE: dict[Planet, tuple[float, float]] = {
    Planet.SUN: (0.0, 20.0), Planet.MOON: (4.0, 20.0), Planet.MARS: (0.0, 12.0),
    Planet.MERCURY: (16.0, 20.0), Planet.JUPITER: (0.0, 10.0),
    Planet.VENUS: (0.0, 15.0), Planet.SATURN: (0.0, 20.0),
}

_SAPTAVARGAJA_CODES = ["D1", "D2", "D3", "D7", "D9", "D12", "D30"]
_SAPTAVARGAJA_POINTS: dict[str, float] = {
    "own_moolatrikona": 45.0, "own": 30.0, "great_friend": 20.0,
    "friend": 15.0, "neutral": 10.0, "enemy": 4.0, "great_enemy": 2.0,
}

# Mean daily motion (degrees/day) - standard, non-disputed astronomical
# constants, used only as the reference point for Chesta Bala's simplified
# speed classification.
MEAN_DAILY_MOTION: dict[Planet, float] = {
    Planet.SUN: 0.9856, Planet.MOON: 13.1764, Planet.MARS: 0.5240,
    Planet.MERCURY: 1.3833, Planet.JUPITER: 0.0831, Planet.VENUS: 1.2000,
    Planet.SATURN: 0.0334,
}

# Cusp index (0-based, house N cusp at index N-1) of each planet's
# Dig-Bala "full strength" cardinal point.
_DIG_BALA_STRONG_CUSP: dict[Planet, int] = {
    Planet.SUN: 9, Planet.MARS: 9,       # 10th (MC)
    Planet.MOON: 3, Planet.VENUS: 3,     # 4th (IC)
    Planet.JUPITER: 0, Planet.MERCURY: 0,  # 1st (Asc)
    Planet.SATURN: 6,                    # 7th (Desc)
}

# "add_north"/"add_south" per the researched sign convention; Mercury is
# unconditionally favourable ("always_add" - uses |declination|).
_AYANA_MODE: dict[Planet, str] = {
    Planet.SUN: "add_north", Planet.MARS: "add_north", Planet.JUPITER: "add_north",
    Planet.VENUS: "add_north", Planet.MOON: "add_south", Planet.SATURN: "add_south",
    Planet.MERCURY: "always_add",
}

_NIGHT_STRONG: set[Planet] = {Planet.MOON, Planet.MARS, Planet.SATURN}
_DAY_STRONG: set[Planet] = {Planet.SUN, Planet.JUPITER, Planet.VENUS}
_BENEFIC_PAKSHA: set[Planet] = {Planet.JUPITER, Planet.VENUS, Planet.MERCURY, Planet.MOON}

_TRIBHAGA_DAY_LORDS = [Planet.MERCURY, Planet.SUN, Planet.SATURN]
_TRIBHAGA_NIGHT_LORDS = [Planet.MOON, Planet.VENUS, Planet.MARS]

_DINA_LORD_BY_WEEKDAY: dict[int, Planet] = {
    0: Planet.MOON, 1: Planet.MARS, 2: Planet.MERCURY, 3: Planet.JUPITER,
    4: Planet.VENUS, 5: Planet.SATURN, 6: Planet.SUN,
}
_CHALDEAN_ORDER: list[Planet] = [
    Planet.SATURN, Planet.JUPITER, Planet.MARS, Planet.SUN,
    Planet.VENUS, Planet.MERCURY, Planet.MOON,
]

_DRIK_BENEFIC: set[Planet] = {Planet.JUPITER, Planet.VENUS, Planet.MERCURY}
_DRIK_MALEFIC: set[Planet] = {Planet.SUN, Planet.MARS, Planet.SATURN}
_DRIK_SPECIAL_STRENGTH: dict[Planet, float] = {
    Planet.MARS: 45.0, Planet.JUPITER: 30.0, Planet.SATURN: 15.0,
}

REQUIRED_RUPAS: dict[Planet, float] = {
    Planet.SUN: 6.5, Planet.MOON: 6.0, Planet.MARS: 5.0, Planet.MERCURY: 7.0,
    Planet.JUPITER: 6.5, Planet.VENUS: 5.5, Planet.SATURN: 5.0,
}


def _angular_distance(a: float, b: float) -> float:
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


def _is_odd_sign(sign: Sign) -> bool:
    from vedic_astro.models import SIGNS_IN_ORDER

    return (SIGNS_IN_ORDER.index(sign) + 1) % 2 == 1


# ---------------------------------------------------------------------------
# Sthana Bala (positional) sub-parts
# ---------------------------------------------------------------------------


def uchcha_bala(planet: Planet, longitude: float) -> float:
    exalt_index = list(Sign).index(EXALTATION_SIGN[planet])
    exalt_longitude = exalt_index * 30 + DEEP_DIGNITY_DEGREE[planet]
    d = _angular_distance(longitude, exalt_longitude)
    return 60.0 - (d / 180.0) * 60.0


def kendradi_bala(planet_sign: Sign, ascendant_sign: Sign) -> float:
    house = whole_sign_house(planet_sign, ascendant_sign)
    if house in (1, 4, 7, 10):
        return 60.0
    if house in (2, 5, 8, 11):
        return 30.0
    return 15.0


def ojayugmarasyamsa_bala(d1_sign: Sign, d9_sign: Sign, planet: Planet) -> float:
    wants_odd = planet in MASCULINE or planet in NEUTER
    total = 0.0
    for sign in (d1_sign, d9_sign):
        odd = _is_odd_sign(sign)
        if (wants_odd and odd) or (not wants_odd and not odd):
            total += 15.0
    return total


def drekkana_bala(planet: Planet, degree_in_sign: float) -> float:
    drekkana_index = min(int(degree_in_sign // 10), 2)  # 0, 1, or 2
    ruling_gender = [MASCULINE, FEMININE, NEUTER][drekkana_index]
    return 15.0 if planet in ruling_gender else 0.0


def saptavargaja_bala(
    planet: Planet,
    d1_degree_in_sign: float,
    d1_sign: Sign,
    varga_signs: dict[str, Sign],
    d1_signs: dict[Planet, Sign],
) -> float:
    """Dignity-tier scoring (45/30/20/15/10/4/2 virupas) across the 7
    classical Saptavargaja charts (D1,D2,D3,D7,D9,D12,D30). Moolatrikona
    (45) only applies in D1, and only within that planet's exact
    Moolatrikona degree range - see MOOLATRIKONA_RANGE. The 5-fold
    Panchadha relationship used for the non-own-sign tiers is always
    computed from D1 positions (d1_signs), per BPHS, regardless of which
    varga is being scored."""
    total = 0.0
    for code in _SAPTAVARGAJA_CODES:
        sign = d1_sign if code == "D1" else varga_signs[code]
        lord = RASHI_LORD[sign]
        if lord == planet:
            lo, hi = MOOLATRIKONA_RANGE[planet]
            if code == "D1" and MOOLATRIKONA_SIGN[planet] == sign and lo <= d1_degree_in_sign < hi:
                total += _SAPTAVARGAJA_POINTS["own_moolatrikona"]
            else:
                total += _SAPTAVARGAJA_POINTS["own"]
            continue
        relation = panchadha_relation(planet, d1_signs[planet], lord, d1_signs[lord])
        total += _SAPTAVARGAJA_POINTS[relation]
    return total


def sthana_bala(
    planet: Planet,
    longitude: float,
    degree_in_sign: float,
    d1_sign: Sign,
    d9_sign: Sign,
    ascendant_sign: Sign,
    varga_signs: dict[str, Sign],
    d1_signs: dict[Planet, Sign],
) -> SthanaBalaBreakdown:
    uchcha = uchcha_bala(planet, longitude)
    saptavargaja = saptavargaja_bala(planet, degree_in_sign, d1_sign, varga_signs, d1_signs)
    ojayugma = ojayugmarasyamsa_bala(d1_sign, d9_sign, planet)
    kendradi = kendradi_bala(d1_sign, ascendant_sign)
    drekkana = drekkana_bala(planet, degree_in_sign)
    total = uchcha + saptavargaja + ojayugma + kendradi + drekkana
    return SthanaBalaBreakdown(
        uchcha_bala=uchcha,
        saptavargaja_bala=saptavargaja,
        ojayugmarasyamsa_bala=ojayugma,
        kendradi_bala=kendradi,
        drekkana_bala=drekkana,
        total=total,
    )


# ---------------------------------------------------------------------------
# Dig Bala (directional)
# ---------------------------------------------------------------------------


def dig_bala(planet: Planet, longitude: float, cusps: list[float]) -> float:
    strong_index = _DIG_BALA_STRONG_CUSP[planet]
    weak_longitude = cusps[(strong_index + 6) % 12]
    return min(60.0, _angular_distance(longitude, weak_longitude) / 3.0)


# ---------------------------------------------------------------------------
# Kala Bala (temporal) sub-parts
# ---------------------------------------------------------------------------


def nathonnata_bala(planet: Planet, local_clock_hours: float) -> float:
    unnata_hours = min(local_clock_hours, 24.0 - local_clock_hours)
    unnata_ghatikas = unnata_hours * 2.5
    nata_ghatikas = 30.0 - unnata_ghatikas
    night_value = min(60.0, max(0.0, 2.0 * nata_ghatikas))
    if planet == Planet.MERCURY:
        return 60.0
    if planet in _NIGHT_STRONG:
        return night_value
    if planet in _DAY_STRONG:
        return 60.0 - night_value
    return 0.0


def paksha_bala(planet: Planet, sun_longitude: float, moon_longitude: float) -> float:
    elongation = (moon_longitude - sun_longitude) % 360
    raw = elongation / 3.0
    if raw > 60.0:
        raw = 120.0 - raw
    return raw if planet in _BENEFIC_PAKSHA else 60.0 - raw


def tribhaga_bala(
    planet: Planet, birth_utc: datetime, sunrise: datetime, sunset: datetime, next_sunrise: datetime
) -> float:
    if planet == Planet.JUPITER:
        return 60.0
    if sunrise <= birth_utc < sunset:
        day_length = (sunset - sunrise).total_seconds()
        elapsed = (birth_utc - sunrise).total_seconds()
        index = min(2, int(elapsed / (day_length / 3.0))) if day_length > 0 else 0
        lord = _TRIBHAGA_DAY_LORDS[index]
    else:
        night_length = (next_sunrise - sunset).total_seconds()
        elapsed = (birth_utc - sunset).total_seconds()
        index = min(2, int(elapsed / (night_length / 3.0))) if night_length > 0 else 0
        lord = _TRIBHAGA_NIGHT_LORDS[index]
    return 60.0 if planet == lord else 0.0


def dina_bala(planet: Planet, local_weekday: int) -> float:
    return 45.0 if _DINA_LORD_BY_WEEKDAY[local_weekday] == planet else 0.0


def hora_bala(
    planet: Planet,
    birth_utc: datetime,
    sunrise: datetime,
    sunset: datetime,
    next_sunrise: datetime,
    sunrise_local_weekday: int,
) -> float:
    day_lord = _DINA_LORD_BY_WEEKDAY[sunrise_local_weekday]
    start_index = _CHALDEAN_ORDER.index(day_lord)
    lords = [_CHALDEAN_ORDER[(start_index + i) % 7] for i in range(24)]

    if sunrise <= birth_utc < sunset:
        day_length = (sunset - sunrise).total_seconds()
        elapsed = (birth_utc - sunrise).total_seconds()
        hora_index = min(11, int(elapsed / (day_length / 12.0))) if day_length > 0 else 0
    else:
        night_length = (next_sunrise - sunset).total_seconds()
        elapsed = (birth_utc - sunset).total_seconds()
        hora_index = 12 + (min(11, int(elapsed / (night_length / 12.0))) if night_length > 0 else 0)

    return 60.0 if lords[hora_index] == planet else 0.0


def ayana_bala(planet: Planet, declination: float, obliquity: float) -> float:
    mode = _AYANA_MODE[planet]
    if mode == "add_north":
        adjusted = declination
    elif mode == "add_south":
        adjusted = -declination
    else:
        adjusted = abs(declination)
    value = 30.0 * (obliquity + adjusted) / obliquity
    return max(0.0, min(60.0, value))


def kala_bala(
    planet: Planet,
    local_clock_hours: float,
    sun_longitude: float,
    moon_longitude: float,
    birth_utc: datetime,
    sunrise: datetime,
    sunset: datetime,
    next_sunrise: datetime,
    local_weekday: int,
    sunrise_local_weekday: int,
    declination: float,
    obliquity: float,
) -> KalaBalaBreakdown:
    nathonnata = nathonnata_bala(planet, local_clock_hours)
    paksha = paksha_bala(planet, sun_longitude, moon_longitude)
    tribhaga = tribhaga_bala(planet, birth_utc, sunrise, sunset, next_sunrise)
    dina = dina_bala(planet, local_weekday)
    hora = hora_bala(planet, birth_utc, sunrise, sunset, next_sunrise, sunrise_local_weekday)
    ayana = ayana_bala(planet, declination, obliquity)
    total = nathonnata + paksha + tribhaga + dina + hora + ayana
    return KalaBalaBreakdown(
        nathonnata_bala=nathonnata, paksha_bala=paksha, tribhaga_bala=tribhaga,
        dina_bala=dina, hora_bala=hora, ayana_bala=ayana, total=total,
    )


# ---------------------------------------------------------------------------
# Chesta Bala (motional) - Sun/Moon reuse Ayana/Paksha; others use a
# flagged 4-state simplification of the classical 8-state scale.
# ---------------------------------------------------------------------------


def chesta_bala(
    planet: Planet, speed_longitude: float, sun_ayana_bala: float, moon_paksha_bala: float
) -> float:
    if planet == Planet.SUN:
        return sun_ayana_bala
    if planet == Planet.MOON:
        return moon_paksha_bala
    mean_speed = MEAN_DAILY_MOTION[planet]
    if speed_longitude < 0:
        return 60.0  # Vakra (retrograde) - Anuvakra not distinguished
    if abs(speed_longitude) < 0.05 * mean_speed:
        return 15.0  # Vikala (stationary)
    ratio = speed_longitude / mean_speed
    if 0.95 <= ratio <= 1.05:
        return 7.5  # Sama (near mean)
    if ratio < 0.95:
        return 30.0  # slower than mean (Mandatara + Manda merged)
    return 45.0  # faster than mean (Chara + Atichara merged)


# ---------------------------------------------------------------------------
# Naisargika Bala (fixed) and Drik Bala (aspectual)
# ---------------------------------------------------------------------------


def naisargika_bala(planet: Planet) -> float:
    order = [Planet.SUN, Planet.MOON, Planet.VENUS, Planet.JUPITER, Planet.MERCURY, Planet.MARS, Planet.SATURN]
    n = 7 - order.index(planet)
    return 60.0 * n / 7.0


def drik_bala(planet: Planet, aspects: list[PlanetAspect], moon_is_waxing: bool) -> float:
    total = 0.0
    for aspect in aspects:
        if aspect.target_planet != planet:
            continue
        source = aspect.source_planet
        base = _DRIK_SPECIAL_STRENGTH.get(source, 60.0) if aspect.is_special else 60.0
        if source in _DRIK_BENEFIC:
            total += base * 1.25
        elif source in _DRIK_MALEFIC:
            total -= base * 0.75
        elif source == Planet.MOON:
            total += (base * 1.25) if moon_is_waxing else -(base * 0.75)
        # Mercury as an aspect source is treated as benefic-weighted above
        # (included in _DRIK_BENEFIC); any other/unclassified source (there
        # are none among the 7 classical planets) would contribute nothing.
    return total


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def compute_shadbala(
    planets: list[PlanetPosition],
    ascendant_sign: Sign,
    cusps: list[float],
    aspects: list[PlanetAspect],
    birth_data: BirthData,
    moon_is_waxing: bool,
) -> dict[Planet, ShadbalaResult]:
    by_planet = {p.planet: p for p in planets}
    d1_signs = {planet: by_planet[planet].sign for planet in _CLASSICAL_PLANETS}

    utc_dt = birth_data.utc_datetime
    sunrise, sunset, next_sunrise = sunrise_sunset(utc_dt, birth_data.latitude, birth_data.longitude)
    local_clock_hours = (
        birth_data.birth_time.hour + birth_data.birth_time.minute / 60.0 + birth_data.birth_time.second / 3600.0
    )
    local_weekday = birth_data.birth_date.weekday()
    # Hora Bala's day-lord sequence starts fresh at each sunrise (a
    # classical, sunrise-anchored reckoning distinct from Dina Bala's civil-
    # date weekday) - convert the UTC sunrise moment back to local time to
    # find which weekday that specific sunrise falls on.
    sunrise_local_weekday = (sunrise + timedelta(hours=birth_data.utc_offset_hours)).weekday()

    obliquity = mean_obliquity_degrees(utc_dt)
    ayanamsha = ayanamsha_value(utc_dt, birth_data.ayanamsha)

    sun_longitude = by_planet[Planet.SUN].longitude
    moon_longitude = by_planet[Planet.MOON].longitude

    results: dict[Planet, ShadbalaResult] = {}
    sun_ayana_precomputed: float | None = None
    moon_paksha_precomputed: float | None = None

    for planet in _CLASSICAL_PLANETS:
        pos = by_planet[planet]
        tropical_longitude = (pos.longitude + ayanamsha) % 360
        declination = declination_degrees(tropical_longitude, pos.ecliptic_latitude, obliquity)

        sthana = sthana_bala(
            planet=planet,
            longitude=pos.longitude,
            degree_in_sign=pos.degree_in_sign,
            d1_sign=pos.sign,
            d9_sign=pos.varga_signs["D9"],
            ascendant_sign=ascendant_sign,
            varga_signs=pos.varga_signs,
            d1_signs=d1_signs,
        )
        dig = dig_bala(planet, pos.longitude, cusps)
        kala = kala_bala(
            planet=planet,
            local_clock_hours=local_clock_hours,
            sun_longitude=sun_longitude,
            moon_longitude=moon_longitude,
            birth_utc=utc_dt,
            sunrise=sunrise,
            sunset=sunset,
            next_sunrise=next_sunrise,
            local_weekday=local_weekday,
            sunrise_local_weekday=sunrise_local_weekday,
            declination=declination,
            obliquity=obliquity,
        )
        if planet == Planet.SUN:
            sun_ayana_precomputed = kala.ayana_bala
        if planet == Planet.MOON:
            moon_paksha_precomputed = kala.paksha_bala

        chesta = chesta_bala(
            planet, pos.speed_longitude,
            sun_ayana_precomputed or 0.0, moon_paksha_precomputed or 0.0,
        )
        naisargika = naisargika_bala(planet)
        drik = drik_bala(planet, aspects, moon_is_waxing)

        total_virupas = sthana.total + dig + kala.total + chesta + naisargika + drik
        total_rupas = total_virupas / 60.0
        required = REQUIRED_RUPAS[planet]
        ishta = math.sqrt(max(0.0, sthana.uchcha_bala * chesta)) / 60.0
        kashta = math.sqrt(max(0.0, (60.0 - sthana.uchcha_bala) * (60.0 - chesta))) / 60.0

        results[planet] = ShadbalaResult(
            planet=planet,
            sthana_bala=sthana,
            dig_bala=dig,
            kala_bala=kala,
            chesta_bala=chesta,
            naisargika_bala=naisargika,
            drik_bala=drik,
            total_virupas=total_virupas,
            total_rupas=total_rupas,
            required_rupas=required,
            meets_required_strength=total_rupas >= required,
            ishta_phala=ishta,
            kashta_phala=kashta,
        )

    return results
