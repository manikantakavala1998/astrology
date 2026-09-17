"""Kalasarpa Dosha, Kuja Dosha ("all types"), and Guru Chandala Dosha.

Unlike most classical rules already in this app, the user didn't send
detailed definitions for these - per their explicit choice ("research and
propose, flag my confidence"), these were verified via web search this
session rather than guessed. See the plan that introduced this module for
the full research notes; summary confidence levels are noted per function
below.

Angaraka Dosha is a confirmed regional-name synonym of Kuja/Mangal Dosha
(same rule, different name) - not implemented separately.
"""

from __future__ import annotations

from vedic_astro.ashtakavarga import ASHTAKAVARGA_PLANETS
from vedic_astro.doshas import pair_dosha_reason, planets_conjunct_or_aspecting
from vedic_astro.models import (
    KalasarpaDoshaResult,
    KujaDoshaReferencePoint,
    KujaDoshaResult,
    Planet,
    PlanetAspect,
    PlanetPosition,
    SaturnPairDosha,
    Sign,
)
from vedic_astro.rashi_bhava import whole_sign_house

# House position of Rahu (from Lagna) -> classically-named type. HIGH
# confidence on the base Kalasarpa rule (all 7 classical planets on one
# side of the Rahu-Ketu axis); MODERATE-HIGH on these names specifically -
# spelling varies slightly across sources (Anant/Ananta, Kulik/Kulika,
# etc.), but the underlying house-based classification is consistent.
KALASARPA_TYPE_BY_RAHU_HOUSE: dict[int, str] = {
    1: "Anant Kalasarpa Dosha",
    2: "Kulik Kalasarpa Dosha",
    3: "Vasuki Kalasarpa Dosha",
    4: "Shankhpal Kalasarpa Dosha",
    5: "Padma Kalasarpa Dosha",
    6: "Mahapadma Kalasarpa Dosha",
    7: "Takshak Kalasarpa Dosha",
    8: "Karkotak Kalasarpa Dosha",
    9: "Shankhnaad Kalasarpa Dosha",
    10: "Patak Kalasarpa Dosha",
    11: "Vishdhar Kalasarpa Dosha",
    12: "Sheshnag Kalasarpa Dosha",
}

# The classical Manglik house set, from each of 3 reference points (Lagna/
# Moon/Venus) - the same set already used, Lagna-only, in matching.py's
# mangal_dosha() for two-person matching (left completely untouched by
# this module - this is an additive, separate natal view). Some sources
# also include the 5th house; not applied here, to stay consistent with
# the already-tested set.
KUJA_DOSHA_HOUSES: set[int] = {1, 2, 4, 7, 8, 12}


def compute_kalasarpa_dosha(planets: list[PlanetPosition]) -> KalasarpaDoshaResult:
    """HIGH confidence on the base rule, MODERATE-HIGH on the 12 type
    names (see module docstring)."""
    rahu = next(p for p in planets if p.planet == Planet.RAHU)
    classical_planets = [p for p in planets if p.planet in ASHTAKAVARGA_PLANETS]

    sides = {(p.house - rahu.house) % 12 < 6 for p in classical_planets}
    has_dosha = len(sides) == 1

    dosha_type = KALASARPA_TYPE_BY_RAHU_HOUSE.get(rahu.house) if has_dosha else None
    if has_dosha:
        reason = (
            f"All 7 classical planets fall on one side of the Rahu-Ketu axis "
            f"(Rahu in House {rahu.house}) - {dosha_type} applies."
        )
    else:
        reason = (
            f"At least one classical planet falls outside the Rahu-Ketu axis "
            f"(Rahu in House {rahu.house}) - Kalasarpa Dosha does not apply."
        )
    return KalasarpaDoshaResult(
        has_dosha=has_dosha, dosha_type=dosha_type, rahu_house=rahu.house, reason=reason
    )


def compute_kuja_dosha(planets: list[PlanetPosition], ascendant_sign: Sign) -> KujaDoshaResult:
    """MODERATE-HIGH confidence: the classical 3-reference-point ('all
    types') check - Mars in KUJA_DOSHA_HOUSES from Lagna, Moon, and Venus
    separately. Triggering from Lagna is the strongest ("High/Full
    Manglik"); from Moon or Venus only is weaker ("Low/Partial
    Manglik")."""
    mars = next(p for p in planets if p.planet == Planet.MARS)
    moon = next(p for p in planets if p.planet == Planet.MOON)
    venus = next(p for p in planets if p.planet == Planet.VENUS)

    reference_points = []
    for reference, base_sign in (("Lagna", ascendant_sign), ("Moon", moon.sign), ("Venus", venus.sign)):
        mars_house = whole_sign_house(mars.sign, base_sign)
        has_dosha = mars_house in KUJA_DOSHA_HOUSES
        reason = (
            f"Mars is in House {mars_house} from {reference} - "
            + ("Kuja Dosha applies from this reference point." if has_dosha
               else "no Kuja Dosha from this reference point.")
        )
        reference_points.append(
            KujaDoshaReferencePoint(
                reference=reference, has_dosha=has_dosha, mars_house=mars_house, reason=reason
            )
        )

    lagna_result, moon_result, venus_result = reference_points
    if lagna_result.has_dosha:
        overall = "High/Full Manglik"
    elif moon_result.has_dosha or venus_result.has_dosha:
        overall = "Low/Partial Manglik"
    else:
        overall = "Not Manglik"

    return KujaDoshaResult(reference_points=reference_points, overall_classification=overall)


def compute_guru_chandala_dosha(
    planets: list[PlanetPosition], aspects: list[PlanetAspect]
) -> SaturnPairDosha:
    """HIGH-MODERATE confidence: Jupiter conjunct Rahu (same house), or
    aspected by Rahu - one-directional by construction since Rahu is never
    an aspect source in this engine (see aspects.py), same pattern as
    Shani Rahu Dosha. Scope: Jupiter-Rahu only, not Ketu."""
    has_dosha, is_conjunction = planets_conjunct_or_aspecting(
        Planet.JUPITER, Planet.RAHU, planets, aspects
    )
    reason = pair_dosha_reason(
        "Guru Chandala Dosha", Planet.JUPITER, Planet.RAHU, has_dosha, is_conjunction
    )
    return SaturnPairDosha(
        name="Guru Chandala Dosha", has_dosha=has_dosha, is_conjunction=is_conjunction, reason=reason
    )
