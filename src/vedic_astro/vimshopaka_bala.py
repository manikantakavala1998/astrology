"""Vimshopaka Bala: a 20-point divisional-chart strength score, at the
Shadvarga (6-chart) and Saptavarga (7-chart) levels only - Dashavarga and
Shodashavarga need divisional charts this app doesn't have built (D16,
D60, and more), so those two variants aren't offered, same "not guessed"
posture as the held divisional charts.

Formula (BPHS Ch.7, verified by reproducing the text's own worked example
exactly - see tests/test_vimshopaka_bala.py):

    division_strength = varga_weight * varga_viswa(relation) / 20

summed across the scheme's divisions. `varga_viswa` depends only on the
5-fold Panchadha relationship between the planet and the lord of the sign
it occupies in that division (own/great-friend/friend/neutral/enemy/
great-enemy) - notably NOT on exaltation/debilitation/Moolatrikona, which
several secondary sources incorrectly layer on top but the primary text
does not.
"""

from __future__ import annotations

from vedic_astro.models import Planet, PlanetPosition, Sign, VimshopakaBalaResult
from vedic_astro.planetary_relations import panchadha_relation
from vedic_astro.rashi_bhava import RASHI_LORD

_CLASSICAL_PLANETS: list[Planet] = [
    Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY,
    Planet.JUPITER, Planet.VENUS, Planet.SATURN,
]

SHADVARGA_CODES = ["D1", "D2", "D3", "D9", "D12", "D30"]
SHADVARGA_WEIGHTS: dict[str, float] = {"D1": 6.0, "D2": 2.0, "D3": 4.0, "D9": 5.0, "D12": 2.0, "D30": 1.0}

SAPTAVARGA_CODES = ["D1", "D2", "D3", "D7", "D9", "D12", "D30"]
SAPTAVARGA_WEIGHTS: dict[str, float] = {
    "D1": 5.0, "D2": 2.0, "D3": 3.0, "D7": 1.0, "D9": 2.5, "D12": 4.5, "D30": 2.0,
}

# Varga Viswa - HIGH confidence, verified against BPHS's own worked
# example. Deliberately no exaltation/debilitation/Moolatrikona override -
# see the module docstring.
VARGA_VISWA_POINTS: dict[str, float] = {
    "own": 20.0, "great_friend": 18.0, "friend": 15.0,
    "neutral": 10.0, "enemy": 7.0, "great_enemy": 5.0,
}

_BAND_THRESHOLDS: list[tuple[float, str]] = [
    (5.0, "Inauspicious"),
    (10.0, "Some Good Effects"),
    (15.0, "Mediocre"),
]


def strength_band(score: float) -> str:
    """The primary 4-band BPHS reading (Ch.7 v.26-27) - the finer 8-grade
    scale from the same chapter (Atipoorna..Atiheena) exists but isn't
    surfaced here, to keep the UI reading simple."""
    for threshold, label in _BAND_THRESHOLDS:
        if score < threshold:
            return label
    return "Wholly Favourable"


def _varga_score(
    planet: Planet,
    d1_sign: Sign,
    varga_signs: dict[str, Sign],
    d1_signs: dict[Planet, Sign],
    codes: list[str],
    weights: dict[str, float],
) -> float:
    total = 0.0
    for code in codes:
        sign = d1_sign if code == "D1" else varga_signs[code]
        lord = RASHI_LORD[sign]
        relation = panchadha_relation(planet, d1_signs[planet], lord, d1_signs[lord])
        total += weights[code] * VARGA_VISWA_POINTS[relation] / 20.0
    return total


def compute_vimshopaka_bala(planets: list[PlanetPosition]) -> dict[Planet, VimshopakaBalaResult]:
    by_planet = {p.planet: p for p in planets}
    d1_signs = {planet: by_planet[planet].sign for planet in _CLASSICAL_PLANETS}

    results: dict[Planet, VimshopakaBalaResult] = {}
    for planet in _CLASSICAL_PLANETS:
        pos = by_planet[planet]
        shadvarga = _varga_score(planet, pos.sign, pos.varga_signs, d1_signs, SHADVARGA_CODES, SHADVARGA_WEIGHTS)
        saptavarga = _varga_score(
            planet, pos.sign, pos.varga_signs, d1_signs, SAPTAVARGA_CODES, SAPTAVARGA_WEIGHTS
        )
        results[planet] = VimshopakaBalaResult(
            planet=planet,
            shadvarga_score=shadvarga,
            saptavarga_score=saptavarga,
            shadvarga_band=strength_band(shadvarga),
            saptavarga_band=strength_band(saptavarga),
        )
    return results
