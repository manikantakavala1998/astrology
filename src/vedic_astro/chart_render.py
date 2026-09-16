"""Lays out a computed chart into the fixed South Indian grid structure.

North/East Indian layouts are a later phase - only the `chart_style` field on
BirthData reserves the option; this module currently implements South Indian
only, since that's the style requested for Phase 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vedic_astro.models import KundaliChart, PlanetPosition, Sign
from vedic_astro.rashi_bhava import whole_sign_house
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
