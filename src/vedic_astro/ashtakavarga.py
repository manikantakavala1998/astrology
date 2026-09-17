"""Ashtakavarga: the Parasara Bhinnashtakavarga (BAV) / Samudaya
Ashtakavarga (SAV) / Bhava Ashtakavarga scoring system.

Only the Parasara method is implemented - the user will supply a source
before any "Varahamihira" method (a claimed alternate contribution table)
is attempted; no such table is guessed here.

The BAV contribution table below was cross-checked cell-by-cell (all 8x7
contributor/scored-planet house-lists) against two independent sources,
and against the well-known fixed per-planet totals (Sun 48, Moon 49, Mars
39, Mercury 54, Jupiter 56, Venus 52, Saturn 39, summing to 337 - the SAV
invariant this module's tests check) before being treated as final.

The Ascendant/Lagna's OWN individual BAV chart (a common addition in
modern software, shown as a "pending a source" placeholder in the UI) has
no verified contribution table and is intentionally NOT computed here -
only Lagna acting as a *contributor* to the 7 planets' charts (which is
solid, and is in the table below) is implemented.
"""

from __future__ import annotations

from vedic_astro.models import SIGNS_IN_ORDER, AshtakavargaSet, Planet, PlanetPosition, Sign

LAGNA = "Lagna"

Contributor = Planet | str  # a Planet, or the LAGNA sentinel

ASHTAKAVARGA_PLANETS: list[Planet] = [
    Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY,
    Planet.JUPITER, Planet.VENUS, Planet.SATURN,
]

# scored planet -> contributor -> houses (counted from the contributor's
# own sign) that earn a bindu for the scored planet.
_BAV_CONTRIBUTION_TABLE: dict[Planet, dict[Contributor, frozenset[int]]] = {
    Planet.SUN: {
        Planet.SUN: frozenset({1, 2, 4, 7, 8, 9, 10, 11}),
        Planet.MOON: frozenset({3, 6, 10, 11}),
        Planet.MARS: frozenset({1, 2, 4, 7, 8, 9, 10, 11}),
        Planet.MERCURY: frozenset({3, 5, 6, 9, 10, 11, 12}),
        Planet.JUPITER: frozenset({5, 6, 9, 11}),
        Planet.VENUS: frozenset({6, 7, 12}),
        Planet.SATURN: frozenset({1, 2, 4, 7, 8, 9, 10, 11}),
        LAGNA: frozenset({3, 4, 6, 10, 11, 12}),
    },
    Planet.MOON: {
        Planet.SUN: frozenset({3, 6, 7, 8, 10, 11}),
        Planet.MOON: frozenset({1, 3, 6, 7, 10, 11}),
        Planet.MARS: frozenset({2, 3, 5, 6, 9, 10, 11}),
        Planet.MERCURY: frozenset({1, 3, 4, 5, 7, 8, 10, 11}),
        Planet.JUPITER: frozenset({1, 4, 7, 8, 10, 11, 12}),
        Planet.VENUS: frozenset({3, 4, 5, 7, 9, 10, 11}),
        Planet.SATURN: frozenset({3, 5, 6, 11}),
        LAGNA: frozenset({3, 6, 10, 11}),
    },
    Planet.MARS: {
        Planet.SUN: frozenset({3, 5, 6, 10, 11}),
        Planet.MOON: frozenset({3, 6, 11}),
        Planet.MARS: frozenset({1, 2, 4, 7, 8, 10, 11}),
        Planet.MERCURY: frozenset({3, 5, 6, 11}),
        Planet.JUPITER: frozenset({6, 10, 11, 12}),
        Planet.VENUS: frozenset({6, 8, 11, 12}),
        Planet.SATURN: frozenset({1, 4, 7, 8, 9, 10, 11}),
        LAGNA: frozenset({1, 3, 6, 10, 11}),
    },
    Planet.MERCURY: {
        Planet.SUN: frozenset({5, 6, 9, 11, 12}),
        Planet.MOON: frozenset({2, 4, 6, 8, 10, 11}),
        Planet.MARS: frozenset({1, 2, 4, 7, 8, 9, 10, 11}),
        Planet.MERCURY: frozenset({1, 3, 5, 6, 9, 10, 11, 12}),
        Planet.JUPITER: frozenset({6, 8, 11, 12}),
        Planet.VENUS: frozenset({1, 2, 3, 4, 5, 8, 9, 11}),
        Planet.SATURN: frozenset({1, 2, 4, 7, 8, 9, 10, 11}),
        LAGNA: frozenset({1, 2, 4, 6, 8, 10, 11}),
    },
    Planet.JUPITER: {
        Planet.SUN: frozenset({1, 2, 3, 4, 7, 8, 9, 10, 11}),
        Planet.MOON: frozenset({2, 5, 7, 9, 11}),
        Planet.MARS: frozenset({1, 2, 4, 7, 8, 10, 11}),
        Planet.MERCURY: frozenset({1, 2, 4, 5, 6, 9, 10, 11}),
        Planet.JUPITER: frozenset({1, 2, 3, 4, 7, 8, 10, 11}),
        Planet.VENUS: frozenset({2, 5, 6, 9, 10, 11}),
        Planet.SATURN: frozenset({3, 5, 6, 12}),
        LAGNA: frozenset({1, 2, 4, 5, 6, 7, 9, 10, 11}),
    },
    Planet.VENUS: {
        Planet.SUN: frozenset({8, 11, 12}),
        Planet.MOON: frozenset({1, 2, 3, 4, 5, 8, 9, 11, 12}),
        Planet.MARS: frozenset({3, 5, 6, 9, 11, 12}),
        Planet.MERCURY: frozenset({3, 5, 6, 9, 11}),
        Planet.JUPITER: frozenset({5, 8, 9, 10, 11}),
        Planet.VENUS: frozenset({1, 2, 3, 4, 5, 8, 9, 10, 11}),
        Planet.SATURN: frozenset({3, 4, 5, 8, 9, 10, 11}),
        LAGNA: frozenset({1, 2, 3, 4, 5, 8, 9, 11}),
    },
    Planet.SATURN: {
        Planet.SUN: frozenset({1, 2, 4, 7, 8, 10, 11}),
        Planet.MOON: frozenset({3, 6, 11}),
        Planet.MARS: frozenset({3, 5, 6, 10, 11, 12}),
        Planet.MERCURY: frozenset({6, 8, 9, 10, 11, 12}),
        Planet.JUPITER: frozenset({5, 6, 11, 12}),
        Planet.VENUS: frozenset({6, 11, 12}),
        Planet.SATURN: frozenset({3, 5, 6, 11}),
        LAGNA: frozenset({1, 3, 4, 6, 10, 11}),
    },
}

# The well-known fixed per-planet BAV totals - a strong independent check
# on the table above, verified in test_ashtakavarga.py.
BAV_FIXED_TOTALS: dict[Planet, int] = {
    Planet.SUN: 48, Planet.MOON: 49, Planet.MARS: 39, Planet.MERCURY: 54,
    Planet.JUPITER: 56, Planet.VENUS: 52, Planet.SATURN: 39,
}


def _sign_at_house_offset(from_sign: Sign, house: int) -> Sign:
    start_index = SIGNS_IN_ORDER.index(from_sign)
    return SIGNS_IN_ORDER[(start_index + house - 1) % 12]


def _contributor_signs(planets: list[PlanetPosition], ascendant_sign: Sign) -> dict[Contributor, Sign]:
    signs: dict[Contributor, Sign] = {LAGNA: ascendant_sign}
    for planet_position in planets:
        if planet_position.planet in ASHTAKAVARGA_PLANETS:
            signs[planet_position.planet] = planet_position.sign
    return signs


def bhinnashtakavarga(
    planets: list[PlanetPosition], ascendant_sign: Sign, scored_planet: Planet
) -> dict[Sign, int]:
    """Bindu count per sign (0-8) for one planet's own Bhinnashtakavarga."""
    contributor_signs = _contributor_signs(planets, ascendant_sign)
    bindus: dict[Sign, int] = dict.fromkeys(SIGNS_IN_ORDER, 0)
    for contributor, houses in _BAV_CONTRIBUTION_TABLE[scored_planet].items():
        contributor_sign = contributor_signs[contributor]
        for house in houses:
            bindus[_sign_at_house_offset(contributor_sign, house)] += 1
    return bindus


def samudaya_ashtakavarga(planets: list[PlanetPosition], ascendant_sign: Sign) -> dict[Sign, int]:
    """SAV: sum of the 7 planets' BAV per sign (Lagna's own BAV, not
    computed here, is excluded - matches the classical 337-point total)."""
    sav: dict[Sign, int] = dict.fromkeys(SIGNS_IN_ORDER, 0)
    for planet in ASHTAKAVARGA_PLANETS:
        for sign, bindus in bhinnashtakavarga(planets, ascendant_sign, planet).items():
            sav[sign] += bindus
    return sav


def _interval_overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _house_subintervals(start: float, end: float) -> list[tuple[float, float]]:
    """A house's [start, end) cusp span as one or two non-wrapping degree
    intervals (two if the span crosses the 360/0 boundary)."""
    if start <= end:
        return [(start, end)]
    return [(start, 360.0), (0.0, end)]


def _round_preserving_total(values: dict[int, float], target_total: int) -> dict[int, int]:
    """Largest-remainder rounding: floor every value, then hand the
    leftover whole units to the entries with the biggest fractional part,
    so the result is all whole bindus that still sum to `target_total`
    exactly - the same apportionment method used for splitting fixed
    totals (e.g. election seats) fairly across fractional shares."""
    floors = {key: int(value) for key, value in values.items()}
    remainder = target_total - sum(floors.values())
    by_fractional_part = sorted(values, key=lambda key: values[key] - floors[key], reverse=True)
    result = dict(floors)
    for key in by_fractional_part[:remainder]:
        result[key] += 1
    return result


def bhava_ashtakavarga(sav: dict[Sign, int], bhava_chalit_cusps: list[float]) -> dict[int, int]:
    """Redistributes each sign's SAV total across houses proportionally to
    how much of the sign's 30-degree span actually falls in each house
    (Bhava Chalit / Placidus cusps) - not a simple "whichever house
    contains the sign's midpoint" assignment. That simpler method has a
    real, visible flaw: whenever a house's cusp span is narrow enough to
    miss every sign's midpoint, it shows a spurious 0 while a neighboring
    wide house absorbs an entire extra sign's worth of bindus - caught via
    live testing with real birth data. Degree-overlap redistribution never
    produces a spurious 0 (every house has positive width, so it always
    overlaps at least one sign) and still preserves the classical 337-point
    total exactly, since each sign's full 30 degrees is partitioned exactly
    across whichever houses it overlaps."""
    raw: dict[int, float] = dict.fromkeys(range(1, 13), 0.0)
    for sign in SIGNS_IN_ORDER:
        sign_index = SIGNS_IN_ORDER.index(sign)
        sign_start, sign_end = sign_index * 30.0, sign_index * 30.0 + 30.0
        for house in range(1, 13):
            house_start = bhava_chalit_cusps[house - 1]
            house_end = bhava_chalit_cusps[house % 12]
            overlap = sum(
                _interval_overlap(sub_start, sub_end, sign_start, sign_end)
                for sub_start, sub_end in _house_subintervals(house_start, house_end)
            )
            raw[house] += sav[sign] * overlap / 30.0
    return _round_preserving_total(raw, target_total=sum(sav.values()))


def compute_ashtakavarga(
    planets: list[PlanetPosition], ascendant_sign: Sign, bhava_chalit_cusps: list[float]
) -> AshtakavargaSet:
    bav_by_planet = {
        planet: bhinnashtakavarga(planets, ascendant_sign, planet) for planet in ASHTAKAVARGA_PLANETS
    }
    sav = samudaya_ashtakavarga(planets, ascendant_sign)
    return AshtakavargaSet(
        bav_by_planet=bav_by_planet,
        sav=sav,
        bhava_ashtakavarga=bhava_ashtakavarga(sav, bhava_chalit_cusps),
    )
