"""Bhava Bala: house/bhava strength, in Rupas (same units as Shadbala's
totals). Depends on shadbala.py's per-planet totals being computed first -
Bhavadhipati Bala is literally the house lord's own Shadbala, a hard BPHS
dependency (Ch.27), not an independent calculation.

Three core components (Bhavadhipati + Bhava Dig + Bhava Drishti), plus
BPHS's own separately-stated "special rules": an occupancy adjustment
(+1 Rupa per Jupiter/Mercury occupant, -1 per Saturn/Mars/Sun occupant).

NOT implemented: the diurnal bonus (+15 Virupas to bhavas in Seershodaya/
dual/Prishtodaya signs depending on day/twilight/night birth) - the
Seershodaya/Prishtodaya sign classification found during research had a
gap (Cancer wasn't classified by any category) and wasn't cross-verified,
so nothing is guessed here; `diurnal_bonus` is always 0.0.
NOT implemented: a fixed "strong bhava" threshold - no BPHS-stated number
was found for Bhava Bala specifically (only Shadbala has one). Houses are
meant to be ranked relative to each other within a chart instead.
"""

from __future__ import annotations

from vedic_astro.aspects import SPECIAL_OFFSETS, aspected_houses
from vedic_astro.models import BhavaBalaResult, Planet, PlanetPosition, ShadbalaResult, Sign
from vedic_astro.rashi_bhava import RASHI_LORD, degree_in_sign, sign_for_longitude

_CLASSICAL_PLANETS: list[Planet] = [
    Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY,
    Planet.JUPITER, Planet.VENUS, Planet.SATURN,
]

_BENEFIC: set[Planet] = {Planet.JUPITER, Planet.VENUS}
_MALEFIC: set[Planet] = {Planet.SUN, Planet.MARS, Planet.SATURN}
_SPECIAL_ASPECT_STRENGTH: dict[Planet, float] = {
    Planet.MARS: 45.0, Planet.JUPITER: 30.0, Planet.SATURN: 15.0,
}

_OCCUPANCY_BONUS: set[Planet] = {Planet.JUPITER, Planet.MERCURY}
_OCCUPANCY_PENALTY: set[Planet] = {Planet.SATURN, Planet.MARS, Planet.SUN}

# Cusp index (0-based) of each cardinal point.
_ASC, _IC, _DESC, _MC = 0, 3, 6, 9


def _angular_distance(a: float, b: float) -> float:
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


def _bhava_reference_cusp_index(sign: Sign, degree: float) -> int:
    if sign in (Sign.VIRGO, Sign.GEMINI, Sign.LIBRA, Sign.AQUARIUS):
        return _DESC
    if sign == Sign.SAGITTARIUS:
        return _DESC if degree < 15.0 else _IC
    if sign in (Sign.ARIES, Sign.TAURUS, Sign.LEO):
        return _IC
    if sign == Sign.CAPRICORN:
        return _IC if degree < 15.0 else _MC
    if sign in (Sign.CANCER, Sign.SCORPIO):
        return _ASC
    return _MC  # Pisces


def bhava_dig_bala(bhava_longitude: float, cusps: list[float]) -> float:
    sign = sign_for_longitude(bhava_longitude)
    degree = degree_in_sign(bhava_longitude)
    reference_index = _bhava_reference_cusp_index(sign, degree)
    reference_longitude = cusps[reference_index]
    return min(60.0, _angular_distance(bhava_longitude, reference_longitude) / 3.0)


def _aspecting_planets_for_house(house: int, planets: list[PlanetPosition]) -> list[tuple[Planet, bool]]:
    """(planet, is_special) for every classical planet whose Graha Drishti
    reaches `house`, based on each planet's own Bhava Chalit house
    position (the same cusp-based system Bhava Bala itself uses)."""
    results: list[tuple[Planet, bool]] = []
    for pos in planets:
        if pos.planet not in _CLASSICAL_PLANETS:
            continue
        reached = aspected_houses(pos.planet, pos.bhava_chalit_house)
        if house not in reached:
            continue
        offset = ((house - pos.bhava_chalit_house) % 12) + 1
        is_special = offset in set(SPECIAL_OFFSETS.get(pos.planet, []))
        results.append((pos.planet, is_special))
    return results


def bhava_drishti_bala(
    house: int, dig_bala_value: float, planets: list[PlanetPosition], moon_is_waxing: bool
) -> float:
    """The +-1/4 adjustment to Bhava Dig Bala from benefic/malefic aspects,
    plus a flat addition when Jupiter and/or Mercury aspect the bhava
    (their own aspectual strength, reusing the same discrete strength
    model as shadbala.py's Drik Bala) - returns the DELTA from
    dig_bala_value (i.e. how much Bhava Drishti Bala changes the total),
    not an absolute value."""
    aspecting = _aspecting_planets_for_house(house, planets)
    benefics_present = False
    malefics_present = False
    jupiter_mercury_bonus = 0.0

    for planet, is_special in aspecting:
        strength = _SPECIAL_ASPECT_STRENGTH.get(planet, 60.0) if is_special else 60.0
        if planet in _BENEFIC:
            benefics_present = True
        elif planet in _MALEFIC:
            malefics_present = True
        elif planet == Planet.MOON:
            if moon_is_waxing:
                benefics_present = True
            else:
                malefics_present = True
        if planet in (Planet.JUPITER, Planet.MERCURY):
            jupiter_mercury_bonus += strength

    adjusted = dig_bala_value
    if benefics_present:
        adjusted *= 1.25
    if malefics_present:
        adjusted *= 0.75

    return (adjusted - dig_bala_value) + jupiter_mercury_bonus


def occupancy_adjustment_rupas(house: int, planets: list[PlanetPosition]) -> float:
    total = 0.0
    for pos in planets:
        if pos.bhava_chalit_house != house:
            continue
        if pos.planet in _OCCUPANCY_BONUS:
            total += 1.0
        elif pos.planet in _OCCUPANCY_PENALTY:
            total -= 1.0
    return total


def compute_bhava_bala(
    planets: list[PlanetPosition],
    cusps: list[float],
    ascendant_sign: Sign,
    shadbala_by_planet: dict[Planet, ShadbalaResult],
    moon_is_waxing: bool,
) -> dict[int, BhavaBalaResult]:
    results: dict[int, BhavaBalaResult] = {}
    for house in range(1, 13):
        bhava_longitude = cusps[house - 1]
        sign = sign_for_longitude(bhava_longitude)
        lord = RASHI_LORD[sign]
        bhavadhipati_rupas = shadbala_by_planet[lord].total_rupas

        dig_virupas = bhava_dig_bala(bhava_longitude, cusps)
        drishti_delta_virupas = bhava_drishti_bala(house, dig_virupas, planets, moon_is_waxing)
        occupancy_rupas = occupancy_adjustment_rupas(house, planets)

        dig_rupas = dig_virupas / 60.0
        drishti_rupas = drishti_delta_virupas / 60.0
        diurnal_bonus_rupas = 0.0  # not implemented - see module docstring

        total_rupas = bhavadhipati_rupas + dig_rupas + drishti_rupas + occupancy_rupas + diurnal_bonus_rupas

        results[house] = BhavaBalaResult(
            house=house,
            bhavadhipati_bala=bhavadhipati_rupas,
            bhava_dig_bala=dig_rupas,
            bhava_drishti_bala=drishti_rupas,
            occupancy_adjustment=occupancy_rupas,
            diurnal_bonus=diurnal_bonus_rupas,
            total_rupas=total_rupas,
        )
    return results
