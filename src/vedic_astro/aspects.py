"""Vedic planetary aspects (graha drishti).

Every planet aspects the 7th house from its own position (180 degrees) - a
universal rule. Mars, Jupiter, and Saturn additionally cast "special"
aspects beyond the 7th:
- Mars: 4th and 8th
- Jupiter: 5th and 9th
- Saturn: 3rd and 10th
Sun, Moon, Mercury, and Venus have only the 7th aspect.

Rahu/Ketu are deliberately NOT given aspect rules here as a source (their
drishti is genuinely disputed across classical sources, unlike the 7
classical grahas above) - they can still be the TARGET of another planet's
aspect, just never the source of one.
"""

from __future__ import annotations

from vedic_astro.models import SIGNS_IN_ORDER, Planet, PlanetAspect, PlanetPosition, Sign

SIGN_MODALITY: dict[Sign, str] = {
    Sign.ARIES: "movable", Sign.CANCER: "movable", Sign.LIBRA: "movable", Sign.CAPRICORN: "movable",
    Sign.TAURUS: "fixed", Sign.LEO: "fixed", Sign.SCORPIO: "fixed", Sign.AQUARIUS: "fixed",
    Sign.GEMINI: "dual", Sign.VIRGO: "dual", Sign.SAGITTARIUS: "dual", Sign.PISCES: "dual",
}


def sign_aspects(sign: Sign) -> list[Sign]:
    """Rashi Drishti (sign-to-sign aspect) - a separate classical system from
    graha drishti above: which SIGNS aspect which, independent of which
    planets occupy them. Movable signs aspect all fixed signs except the one
    immediately adjacent (and vice versa); dual signs aspect the other three
    dual signs.
    """
    modality = SIGN_MODALITY[sign]
    index = SIGNS_IN_ORDER.index(sign)
    adjacent = {SIGNS_IN_ORDER[(index - 1) % 12], SIGNS_IN_ORDER[(index + 1) % 12]}

    if modality == "movable":
        return [s for s in SIGNS_IN_ORDER if SIGN_MODALITY[s] == "fixed" and s not in adjacent]
    if modality == "fixed":
        return [s for s in SIGNS_IN_ORDER if SIGN_MODALITY[s] == "movable" and s not in adjacent]
    return [s for s in SIGNS_IN_ORDER if SIGN_MODALITY[s] == "dual" and s != sign]

# House offsets (counted inclusively from the planet's own house) that each
# planet aspects. The 7th is universal; entries beyond [7] are the "special"
# aspects unique to that planet.
ASPECT_OFFSETS: dict[Planet, list[int]] = {
    Planet.SUN: [7],
    Planet.MOON: [7],
    Planet.MERCURY: [7],
    Planet.VENUS: [7],
    Planet.MARS: [4, 7, 8],
    Planet.JUPITER: [5, 7, 9],
    Planet.SATURN: [3, 7, 10],
}

SPECIAL_OFFSETS: dict[Planet, list[int]] = {
    Planet.MARS: [4, 8],
    Planet.JUPITER: [5, 9],
    Planet.SATURN: [3, 10],
}


def aspected_houses(planet: Planet, from_house: int) -> list[int]:
    """Which houses (1-12) this planet aspects, given its own house position.
    Rahu/Ketu (and anything else with no defined rule) aspect nothing here.
    """
    offsets = ASPECT_OFFSETS.get(planet, [])
    return sorted({((from_house - 1 + offset - 1) % 12) + 1 for offset in offsets})


def compute_aspects(planets: list[PlanetPosition]) -> list[PlanetAspect]:
    """All planet-to-planet aspects among the given planets, based on house
    position - i.e. which planets sit in a house that another planet's
    sign-to-sign (rashi) drishti reaches.
    """
    results: list[PlanetAspect] = []
    for source in planets:
        houses_reached = aspected_houses(source.planet, source.house)
        if not houses_reached:
            continue
        special_offsets = set(SPECIAL_OFFSETS.get(source.planet, []))
        for target in planets:
            if target.house not in houses_reached:
                continue
            offset = ((target.house - source.house) % 12) + 1
            results.append(
                PlanetAspect(
                    source_planet=source.planet,
                    source_house=source.house,
                    target_planet=target.planet,
                    target_house=target.house,
                    is_special=offset in special_offsets,
                )
            )
    return results
