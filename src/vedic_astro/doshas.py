"""Standalone, single-person dosha rules - no aggregate Doshas/Yogas tab yet
(that stays deferred, same as the Yoga tab). Saturn-specific doshas live
here (natal Shani Dosha/Neech Dosha, plus the 3 Saturn-conjunction
doshas); Kalasarpa/Kuja/Guru Chandala live in general_doshas.py; Mangal
Dosha lives in matching.py since it's specific to the two-person
Ashtakoot marriage-matching context.
"""

from __future__ import annotations

from vedic_astro.models import (
    Planet,
    PlanetAspect,
    PlanetPosition,
    SaturnAfflictionDoshas,
    SaturnPairDosha,
    ShaniDoshaResult,
    Sign,
)

_HOUSE_DOSHA_REASONS: dict[int, str] = {
    1: (
        "Saturn in the 1st House (Lagna): a highly serious childhood, "
        "delayed personal identity, and early health struggles."
    ),
    4: (
        "Saturn in the 4th House: disrupts Sukha Bhava (domestic happiness) "
        "- strain with the mother, or a perpetual struggle to feel settled "
        "at home."
    ),
    7: (
        "Saturn in the 7th House: heavily delays marriage (often past age "
        "30-32) and causes friction in business partnerships."
    ),
    8: (
        "Ashtama Shani (Saturn in the 8th House): sudden crises, "
        "inheritance disputes, ongoing chronic health issues, and hidden "
        "emotional burdens."
    ),
    12: (
        "Saturn in the 12th House: unexpected medical or hidden expenses, "
        "severe sleep disorders, and isolation."
    ),
}

_NEECH_DOSHA_REASON = (
    "Shani Neech Dosha: Saturn is debilitated in Aries - poor "
    "decision-making, a lack of patience, and a sense that genuine hard "
    "work is going unrewarded."
)


def compute_shani_dosha(planets: list[PlanetPosition]) -> ShaniDoshaResult:
    saturn = next(p for p in planets if p.planet == Planet.SATURN)

    house_reason = _HOUSE_DOSHA_REASONS.get(
        saturn.house,
        f"Saturn is in House {saturn.house} - no permanent natal Shani "
        "Dosha from house position.",
    )
    has_neech_dosha = saturn.sign == Sign.ARIES
    neech_reason = (
        _NEECH_DOSHA_REASON
        if has_neech_dosha
        else f"Saturn is in {saturn.sign.value} - not debilitated (would need to be in Aries)."
    )
    return ShaniDoshaResult(
        has_house_dosha=saturn.house in _HOUSE_DOSHA_REASONS,
        house_reason=house_reason,
        has_neech_dosha=has_neech_dosha,
        neech_reason=neech_reason,
    )


def planets_conjunct_or_aspecting(
    planet_a: Planet,
    planet_b: Planet,
    planets: list[PlanetPosition],
    aspects: list[PlanetAspect],
) -> tuple[bool, bool]:
    """(has_dosha, is_conjunction). Same house is a symmetric conjunction
    check; otherwise checks whether either planet's Graha Drishti aspect
    (chart.aspects, already computed) reaches the other's house. Since
    aspects.py never emits Rahu/Ketu as an aspect *source* (a pre-existing,
    documented limitation - disputed across classical sources), any dosha
    built on this helper involving Rahu/Ketu is naturally one-directional
    (e.g. Saturn aspecting Rahu, never Rahu aspecting Saturn) without any
    special-casing here - same-house conjunction stays fully symmetric
    regardless."""
    a = next(p for p in planets if p.planet == planet_a)
    b = next(p for p in planets if p.planet == planet_b)
    if a.house == b.house:
        return True, True
    is_aspecting = any(
        (asp.source_planet == planet_a and asp.target_planet == planet_b)
        or (asp.source_planet == planet_b and asp.target_planet == planet_a)
        for asp in aspects
    )
    return is_aspecting, False


def pair_dosha_reason(name: str, a: Planet, b: Planet, has_dosha: bool, is_conjunction: bool) -> str:
    if not has_dosha:
        return f"No conjunction or mutual aspect between {a.value} and {b.value} - no {name}."
    relation = "share the same house (conjunction)" if is_conjunction else "aspect each other"
    return f"{a.value} and {b.value} {relation} - {name} applies."


def compute_saturn_afflictions(
    planets: list[PlanetPosition], aspects: list[PlanetAspect]
) -> SaturnAfflictionDoshas:
    """Vish Dosha (Saturn-Moon), Shani Mangal Dosha (Saturn-Mars), and Shani
    Rahu Dosha / Shapit Yoga (Saturn-Rahu, one-directional - see
    planets_conjunct_or_aspecting). Scope note: only Saturn+Rahu is
    implemented for Shapit Yoga, not Saturn+Ketu - not requested."""
    vish_has, vish_conj = planets_conjunct_or_aspecting(Planet.SATURN, Planet.MOON, planets, aspects)
    mangal_has, mangal_conj = planets_conjunct_or_aspecting(
        Planet.SATURN, Planet.MARS, planets, aspects
    )
    rahu_has, rahu_conj = planets_conjunct_or_aspecting(Planet.SATURN, Planet.RAHU, planets, aspects)
    return SaturnAfflictionDoshas(
        vish_dosha=SaturnPairDosha(
            name="Vish Dosha",
            has_dosha=vish_has,
            is_conjunction=vish_conj,
            reason=pair_dosha_reason("Vish Dosha", Planet.SATURN, Planet.MOON, vish_has, vish_conj),
        ),
        shani_mangal_dosha=SaturnPairDosha(
            name="Shani Mangal Dosha",
            has_dosha=mangal_has,
            is_conjunction=mangal_conj,
            reason=pair_dosha_reason(
                "Shani Mangal Dosha", Planet.SATURN, Planet.MARS, mangal_has, mangal_conj
            ),
        ),
        shani_rahu_dosha=SaturnPairDosha(
            name="Shani Rahu Dosha (Shapit Yoga)",
            has_dosha=rahu_has,
            is_conjunction=rahu_conj,
            reason=pair_dosha_reason(
                "Shani Rahu Dosha (Shapit Yoga)", Planet.SATURN, Planet.RAHU, rahu_has, rahu_conj
            ),
        ),
    )
