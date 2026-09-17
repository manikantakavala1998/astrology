"""Lays out a computed chart into the fixed South Indian grid structure.

North/East Indian layouts are a later phase - only the `chart_style` field on
BirthData reserves the option; this module currently implements South Indian
only, since that's the style requested for Phase 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vedic_astro.models import SIGNS_IN_ORDER, KundaliChart, PlanetPosition, Sign
from vedic_astro.rashi_bhava import house_from_cusps, whole_sign_house
from vedic_astro.varga import navamsa_sign

# Fixed South Indian layout: each cell's sign never changes chart to chart -
# only which cell is marked as the ascendant changes. The 4 center cells are
# blank (traditionally left for chart title/notes).
SOUTH_INDIAN_GRID: list[list[Sign | None]] = [
    [Sign.PISCES, Sign.ARIES, Sign.TAURUS, Sign.GEMINI],
    [Sign.AQUARIUS, None, None, Sign.CANCER],
    [Sign.CAPRICORN, None, None, Sign.LEO],
    [Sign.SAGITTARIUS, Sign.SCORPIO, Sign.LIBRA, Sign.VIRGO],
]


@dataclass
class ChartCell:
    sign: Sign
    house: int
    is_ascendant: bool
    planet_labels: list[str] = field(default_factory=list)


@dataclass
class AshtakavargaCell:
    sign: Sign
    bindus: int
    is_natal_occupied: bool


def _planet_label(planet_position: PlanetPosition) -> str:
    short_code = planet_position.planet.value[:2]
    return f"{short_code}(R)" if planet_position.retrograde else short_code


def south_indian_layout(chart: KundaliChart) -> list[list[ChartCell | None]]:
    planets_by_sign: dict[Sign, list[str]] = {}
    for planet_position in chart.planets:
        planets_by_sign.setdefault(planet_position.sign, []).append(
            _planet_label(planet_position)
        )

    grid: list[list[ChartCell | None]] = []
    for row in SOUTH_INDIAN_GRID:
        rendered_row: list[ChartCell | None] = []
        for sign in row:
            if sign is None:
                rendered_row.append(None)
                continue
            rendered_row.append(
                ChartCell(
                    sign=sign,
                    house=whole_sign_house(sign, chart.ascendant.sign),
                    is_ascendant=(sign == chart.ascendant.sign),
                    planet_labels=planets_by_sign.get(sign, []),
                )
            )
        grid.append(rendered_row)
    return grid


def navamsa_layout(chart: KundaliChart) -> list[list[ChartCell | None]]:
    """Same fixed South Indian grid, but for the Navamsa (D9) chart: each
    planet placed by its D9 sign instead of its D1 (Rashi) sign, and the D9
    Lagna (the Ascendant's own D9 sign) marking house 1 instead of the D1
    Ascendant.
    """
    navamsa_ascendant_sign = navamsa_sign(chart.ascendant.longitude)

    planets_by_sign: dict[Sign, list[str]] = {}
    for planet_position in chart.planets:
        if planet_position.navamsa_sign is None:
            continue
        planets_by_sign.setdefault(planet_position.navamsa_sign, []).append(
            _planet_label(planet_position)
        )

    grid: list[list[ChartCell | None]] = []
    for row in SOUTH_INDIAN_GRID:
        rendered_row: list[ChartCell | None] = []
        for sign in row:
            if sign is None:
                rendered_row.append(None)
                continue
            rendered_row.append(
                ChartCell(
                    sign=sign,
                    house=whole_sign_house(sign, navamsa_ascendant_sign),
                    is_ascendant=(sign == navamsa_ascendant_sign),
                    planet_labels=planets_by_sign.get(sign, []),
                )
            )
        grid.append(rendered_row)
    return grid


def varga_layout(chart: KundaliChart, code: str) -> list[list[ChartCell | None]]:
    """Same fixed South Indian grid, generalized to any divisional chart
    code present in PlanetPosition.varga_signs / Ascendant.varga_signs (see
    divisional_charts.VARGA_REGISTRY) - the parametrized version of the
    south_indian_layout/navamsa_layout pattern above. Those two functions
    are kept as-is (D1/D9 are logically `varga_layout(chart, "D1"/"D9")`,
    but stay separate and stable since other code references them by name).
    """
    varga_ascendant_sign = chart.ascendant.varga_signs[code]

    planets_by_sign: dict[Sign, list[str]] = {}
    for planet_position in chart.planets:
        sign = planet_position.varga_signs.get(code)
        if sign is None:
            continue
        planets_by_sign.setdefault(sign, []).append(_planet_label(planet_position))

    grid: list[list[ChartCell | None]] = []
    for row in SOUTH_INDIAN_GRID:
        rendered_row: list[ChartCell | None] = []
        for sign in row:
            if sign is None:
                rendered_row.append(None)
                continue
            rendered_row.append(
                ChartCell(
                    sign=sign,
                    house=whole_sign_house(sign, varga_ascendant_sign),
                    is_ascendant=(sign == varga_ascendant_sign),
                    planet_labels=planets_by_sign.get(sign, []),
                )
            )
        grid.append(rendered_row)
    return grid


def bhava_chalit_layout(chart: KundaliChart) -> list[list[ChartCell | None]]:
    """Bhava Chalit: planets keep their D1 sign (house cusps don't move a
    planet's sign, only its house number) - but each sign cell's house
    number comes from where that sign's own midpoint (15 degrees in) falls
    among the Bhava Chalit (Placidus) cusps, instead of whole-sign counting
    from the Ascendant.
    """
    planets_by_sign: dict[Sign, list[str]] = {}
    for planet_position in chart.planets:
        planets_by_sign.setdefault(planet_position.sign, []).append(
            _planet_label(planet_position)
        )

    grid: list[list[ChartCell | None]] = []
    for row in SOUTH_INDIAN_GRID:
        rendered_row: list[ChartCell | None] = []
        for sign in row:
            if sign is None:
                rendered_row.append(None)
                continue
            sign_index = SIGNS_IN_ORDER.index(sign)
            midpoint_longitude = sign_index * 30 + 15
            house = house_from_cusps(midpoint_longitude, chart.bhava_chalit_cusps)
            rendered_row.append(
                ChartCell(
                    sign=sign,
                    house=house,
                    is_ascendant=(house == 1),
                    planet_labels=planets_by_sign.get(sign, []),
                )
            )
        grid.append(rendered_row)
    return grid


def ashtakavarga_mini_grid(
    bindus_by_sign: dict[Sign, int], natal_signs: set[Sign]
) -> list[list[AshtakavargaCell | None]]:
    """One of the 3x3 screenshot-style Ashtakavarga mini-charts: the same
    fixed South Indian grid, showing a bindu count per sign instead of
    planet labels, with signs occupied in the natal D1 chart highlighted."""
    grid: list[list[AshtakavargaCell | None]] = []
    for row in SOUTH_INDIAN_GRID:
        rendered_row: list[AshtakavargaCell | None] = []
        for sign in row:
            if sign is None:
                rendered_row.append(None)
                continue
            rendered_row.append(
                AshtakavargaCell(
                    sign=sign,
                    bindus=bindus_by_sign[sign],
                    is_natal_occupied=sign in natal_signs,
                )
            )
        grid.append(rendered_row)
    return grid
