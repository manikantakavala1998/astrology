"""Planet-to-planet tables for the Vedic and Western aspects views.

The Vedic table counts natal zodiac signs, independently of bhava placement.
Western major aspects use the shortest separation in ecliptic longitude.
The existing house-based graha-drishti engine is left to its current callers.
"""

from __future__ import annotations

from typing import TypedDict

from vedic_astro.aspects import ASPECT_OFFSETS
from vedic_astro.models import SIGNS_IN_ORDER, PlanetPosition

WESTERN_MAJOR_ASPECTS = (
    ("Conjunction", 0), ("Sextile", 60), ("Square", 90),
    ("Trine", 120), ("Opposition", 180),
)
WESTERN_DEFAULT_ORB = 6.0
WESTERN_MAX_ORB = 10.0


class VedicLink(TypedDict):
    target_planet: str
    target_sign: str
    aspect_number: int


class AspectedSign(TypedDict):
    sign: str
    aspect_number: int


class WesternLink(TypedDict):
    target_planet: str
    target_sign: str
    aspect_name: str
    exact_angle: int
    separation: float
    orb: float


class VedicRow(TypedDict):
    planet: str
    sign: str
    retrograde: bool
    aspects: list[VedicLink]
    aspected_signs: list[AspectedSign]


class WesternRow(TypedDict):
    planet: str
    sign: str
    retrograde: bool
    aspects: list[WesternLink]


class AspectTables(TypedDict):
    vedic: list[VedicRow]
    western: list[WesternRow]
    western_default_orb: float
    western_max_orb: float


def build_aspect_tables(planets: list[PlanetPosition]) -> AspectTables:
    vedic_rows: list[VedicRow] = []
    western_rows: list[WesternRow] = []
    for source in planets:
        source_sign = SIGNS_IN_ORDER.index(source.sign)
        offsets = ASPECT_OFFSETS.get(source.planet, [])
        vedic: VedicRow = {
            "planet": source.planet.value, "sign": source.sign.value,
            "retrograde": source.retrograde, "aspects": [],
            "aspected_signs": [
                {"sign": SIGNS_IN_ORDER[(source_sign + offset - 1) % 12].value, "aspect_number": offset}
                for offset in offsets
            ],
        }
        western: WesternRow = {"planet": source.planet.value, "sign": source.sign.value, "retrograde": source.retrograde, "aspects": []}
        for target in planets:
            if target.planet == source.planet:
                continue
            offset = (SIGNS_IN_ORDER.index(target.sign) - source_sign) % 12 + 1
            if offset in offsets:
                vedic["aspects"].append({"target_planet": target.planet.value,
                                       "target_sign": target.sign.value, "aspect_number": offset})

            difference = abs(source.longitude - target.longitude) % 360
            separation = min(difference, 360 - difference)
            name, angle = min(WESTERN_MAJOR_ASPECTS, key=lambda aspect: abs(separation - aspect[1]))
            orb = abs(separation - angle)
            if orb <= WESTERN_MAX_ORB + 1e-9:
                western["aspects"].append({
                    "target_planet": target.planet.value, "target_sign": target.sign.value, "aspect_name": name,
                    "exact_angle": angle, "separation": separation, "orb": orb,
                })
        vedic_rows.append(vedic)
        western_rows.append(western)
    return {
        "vedic": vedic_rows, "western": western_rows,
        "western_default_orb": WESTERN_DEFAULT_ORB, "western_max_orb": WESTERN_MAX_ORB,
    }
