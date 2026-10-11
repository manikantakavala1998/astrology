"""Bhrigu Nandi Nadi chart worksheets, based on R.G. Rao's worked charts.

Source audit and conventions are recorded in docs/bhrigu-nandi-nadi.md.
The introductory karaka procedure uses sign, dispositor, co-sign planets,
adjacent/opposite signs, exchanges, dignity and motion. These are chart
facts; converting them into family events needs additional interpretation.

Chart 1, printed page 11 of the scanned edition, uses Jupiter as self,
Moon in its previous sign as an elder sister and forward contacts as younger
siblings. That example counts Rahu as a brother. Chart 44 excludes Ketu
from an elder reading, while Chart 431 associates it with the youngest son.
Chart 222 instead reads elder siblings from Mars and its following signs.
Consequently the Chart 1 comparison below counts planetary indicators only.
It cannot establish an exact sibling count or birth order for a new chart.

Retrograde Jupiter's previous-sign influence is illustrated in Chart 371.
We expose that additional context without moving the actual natal planet,
reversing every transit or inventing a sibling-count equation.

Timing remains a schematic worksheet: Jupiter uses 12 years per round,
Saturn 30, with inclusive house ordinals as in the existing convention.
Saturn retains half years. These ages are neither ephemeris transit dates
nor confirmed marriage or job events. The historical isolation conditions
are likewise configuration flags rather than lifespan/wealth forecasts.
"""

from __future__ import annotations

from vedic_astro.dignity import planet_dignity
from vedic_astro.models import (
    BnnCareerSequence,
    BnnKarakaReading,
    BnnMarriageTiming,
    BnnMarriageTimingVariant,
    BnnResult,
    BnnShortLifeIndication,
    BnnSiblingCount,
    BnnSisterIndicator,
    Planet,
    PlanetPosition,
    Sign,
    SIGNS_IN_ORDER,
)
from vedic_astro.planetary_relations import natural_relation
from vedic_astro.rashi_bhava import RASHI_LORD

JUPITER_ROUND_LENGTH = 12
SATURN_ROUND_LENGTH = 30

_KARAKA_SIGNIFIES: dict[Planet, str] = {
    Planet.SUN: "Father",
    Planet.MOON: "Mother",
    Planet.MARS: "Siblings (brothers); husband, if the native is female",
    Planet.MERCURY: "Education, intellect",
    Planet.JUPITER: "Children; also stands in for the native's own self "
    "in the sibling-count and transit-timing methods below",
    Planet.VENUS: "Wife, if the native is male; wealth and comfort generally",
    Planet.SATURN: "Profession, karma",
    Planet.RAHU: "Family circle, obstruction, foreign places",
    Planet.KETU: "Renunciation, pilgrimage (via Jupiter's transit over its sign)",
}

# These labels describe Chart 1's indicators, not universal sibling genders.
_BROTHER_PLANETS = {Planet.SUN, Planet.MARS, Planet.SATURN, Planet.MERCURY, Planet.RAHU}
_SISTER_PLANETS = {Planet.MOON, Planet.VENUS}
_ELDER_TEST_EXCLUDED = {Planet.KETU}  # Chart 44 convention; Chart 431 differs.
_CLASSICAL_SEVEN = {
    Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY,
    Planet.JUPITER, Planet.VENUS, Planet.SATURN,
}


def _sign_at_offset(base_sign: Sign, houses_ahead: int) -> Sign:
    base_index = SIGNS_IN_ORDER.index(base_sign)
    return SIGNS_IN_ORDER[(base_index + houses_ahead - 1) % 12]


def _house_offset(base_sign: Sign, target_sign: Sign) -> int:
    """1-12: how many signs forward from `base_sign` you reach `target_sign`
    (whole-sign house counting, base_sign itself = house 1)."""
    base_index = SIGNS_IN_ORDER.index(base_sign)
    target_index = SIGNS_IN_ORDER.index(target_sign)
    return ((target_index - base_index) % 12) + 1


def _round_ages(signs_forward: int, round_length: int, max_age: int) -> list[float]:
    """Schematic inclusive-house timing, preserving Saturn's half years."""
    first_age = signs_forward * round_length / 12
    if first_age > max_age:
        return []
    rounds = int((max_age - first_age) // round_length)
    return [first_age + cycle * round_length for cycle in range(rounds + 1)]


def _group_planets(planets: list[PlanetPosition]) -> dict[Sign, list[Planet]]:
    """Stable forward order, including degree order within a shared sign."""
    grouped: dict[Sign, list[Planet]] = {sign: [] for sign in SIGNS_IN_ORDER}
    tie_order = {planet: index for index, planet in enumerate(Planet)}
    for pos in sorted(planets, key=lambda p: (p.longitude, tie_order[p.planet])):
        grouped[pos.sign].append(pos.planet)
    return grouped


def _planets_crossed_forward(
    base_sign: Sign,
    planets_by_sign: dict[Sign, list[Planet]],
    exclude: set[Planet],
    *,
    include_previous_sign: bool = False,
) -> list[Planet]:
    """Forward contacts outside the natal sign.

    Only the Chart 1 sibling comparison reserves the previous sign.
    Saturn's career worksheet must include that sign before completing
    a round; applying the sibling exception there dropped valid contacts.
    """
    crossed: list[Planet] = []
    for houses_ahead in range(2, 13 if include_previous_sign else 12):
        sign = _sign_at_offset(base_sign, houses_ahead)
        crossed.extend(planet for planet in planets_by_sign[sign] if planet not in exclude)
    return crossed


def _read_karaka(
    karaka: Planet,
    planets: list[PlanetPosition],
    planets_by_sign: dict[Sign, list[Planet]],
    dispositor_sign_of: dict[Planet, Sign],
) -> BnnKarakaReading:
    pos = next(p for p in planets if p.planet == karaka)
    dispositor = RASHI_LORD[pos.sign]

    sign_exchange_with: Planet | None = None
    if dispositor != karaka:
        dispositor_sign = dispositor_sign_of[dispositor]
        if RASHI_LORD[dispositor_sign] == karaka:
            sign_exchange_with = dispositor

    dispositor_relation: str | None = None
    if dispositor != karaka and karaka in _CLASSICAL_SEVEN and dispositor in _CLASSICAL_SEVEN:
        dispositor_relation = natural_relation(karaka, dispositor)

    return BnnKarakaReading(
        karaka=karaka,
        signifies=_KARAKA_SIGNIFIES[karaka],
        sign=pos.sign,
        dispositor=dispositor,
        dispositor_house_from_karaka=_house_offset(pos.sign, dispositor_sign_of[dispositor]),
        conjunct_planets=[p for p in planets_by_sign[pos.sign] if p != karaka],
        planets_next_sign=planets_by_sign[_sign_at_offset(pos.sign, 2)],
        planets_previous_sign=planets_by_sign[_sign_at_offset(pos.sign, 12)],
        planets_seventh_sign=planets_by_sign[_sign_at_offset(pos.sign, 7)],
        sign_exchange_with=sign_exchange_with,
        dispositor_relation=dispositor_relation,
        dignity=planet_dignity(karaka, pos.sign),
        retrograde=pos.retrograde,
    )


def compute_bnn_karaka_readings(planets: list[PlanetPosition]) -> list[BnnKarakaReading]:
    planets_by_sign = _group_planets(planets)
    dispositor_sign_of: dict[Planet, Sign] = {p.planet: p.sign for p in planets}

    return [
        _read_karaka(karaka, planets, planets_by_sign, dispositor_sign_of)
        for karaka in (
            Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY, Planet.JUPITER,
            Planet.VENUS, Planet.SATURN, Planet.RAHU, Planet.KETU,
        )
    ]


def compute_bnn_sibling_count(planets: list[PlanetPosition]) -> BnnSiblingCount:
    """Expose the worked-example comparison, with no inferred family count."""
    planets_by_sign = _group_planets(planets)
    jupiter = next(p for p in planets if p.planet == Planet.JUPITER)
    mars = next(p for p in planets if p.planet == Planet.MARS)
    previous_sign = _sign_at_offset(jupiter.sign, 12)
    # Keep EVERY indicator, not just the first occupant of the previous sign.
    elder_planets = [p for p in planets_by_sign[previous_sign] if p not in _ELDER_TEST_EXCLUDED]
    younger_planets = _planets_crossed_forward(jupiter.sign, planets_by_sign, exclude={Planet.JUPITER})
    retrograde_context = previous_sign if jupiter.retrograde else None

    def _gender_breakdown(planet_list: list[Planet]) -> dict[str, int]:
        return {
            "brothers": sum(1 for p in planet_list if p in _BROTHER_PLANETS),
            "sisters": sum(1 for p in planet_list if p in _SISTER_PLANETS),
            "unclassified": sum(1 for p in planet_list if p not in _BROTHER_PLANETS | _SISTER_PLANETS),
        }

    sister_indicators = [
        BnnSisterIndicator(
            planet=planet,
            sign=pos.sign,
            house_from_jupiter=_house_offset(jupiter.sign, pos.sign),
            house_from_mars=_house_offset(mars.sign, pos.sign),
            house_from_retrograde_context=(
                _house_offset(retrograde_context, pos.sign) if retrograde_context else None
            ),
        )
        for planet in (Planet.MOON, Planet.VENUS)
        for pos in planets if pos.planet == planet
    ]
    notes = [
        "Exact sibling count and elder/younger birth order are not determined by this worksheet.",
        "Moon and Venus are sister significators; two significators do not prove two sisters.",
        "Chart 1 is a worked-example comparison, not a universal one-planet-per-sibling rule.",
        "Chart 222 uses Mars and following signs for elder siblings; Charts 44 and 431 differ on Ketu.",
    ]
    if jupiter.retrograde:
        notes.append(
            f"Jupiter is retrograde in {jupiter.sign.value}. Chart 371 also considers its "
            f"previous-sign influence ({previous_sign.value}); this does not establish sibling birth order."
        )
    return BnnSiblingCount(
        elder_planets=elder_planets,
        younger_planets=younger_planets,
        elder_indicator_count=len(elder_planets),
        younger_indicator_count=len(younger_planets),
        elder_gender_breakdown=_gender_breakdown(elder_planets),
        younger_gender_breakdown=_gender_breakdown(younger_planets),
        sister_indicators=sister_indicators,
        jupiter_sign=jupiter.sign,
        jupiter_retrograde=jupiter.retrograde,
        retrograde_context_sign=retrograde_context,
        notes=notes,
    )


def compute_bnn_marriage_timing(planets: list[PlanetPosition], max_age: int = 100) -> BnnMarriageTiming:
    """Schematic Jupiter/spouse-karaka contacts for both traditional variants.

    A contact alone does not predict marriage. Actual transits and other
    conditions are not evaluated by this round worksheet.
    """
    jupiter = next(p for p in planets if p.planet == Planet.JUPITER)
    venus = next(p for p in planets if p.planet == Planet.VENUS)
    mars = next(p for p in planets if p.planet == Planet.MARS)

    def _variant(spouse_karaka: Planet, spouse_sign: Sign) -> BnnMarriageTimingVariant:
        signs_forward = _house_offset(jupiter.sign, spouse_sign)
        return BnnMarriageTimingVariant(
            spouse_karaka=spouse_karaka,
            spouse_karaka_sign=spouse_sign,
            ages=[int(age) for age in _round_ages(signs_forward, JUPITER_ROUND_LENGTH, max_age)],
        )

    return BnnMarriageTiming(
        male_native=_variant(Planet.VENUS, venus.sign),
        female_native=_variant(Planet.MARS, mars.sign),
    )


def compute_bnn_short_life_indication(planets: list[PlanetPosition]) -> BnnShortLifeIndication:
    """Historical isolation conditions; no lifespan/wealth inference."""
    planets_by_sign = _group_planets(planets)

    def _is_bare(reference: Planet) -> bool:
        pos = next(p for p in planets if p.planet == reference)
        neighbor_signs = (
            _sign_at_offset(pos.sign, 2), _sign_at_offset(pos.sign, 12), _sign_at_offset(pos.sign, 7),
        )
        return all(not planets_by_sign[sign] for sign in neighbor_signs)

    return BnnShortLifeIndication(
        jupiter_bare=_is_bare(Planet.JUPITER),
        saturn_bare=_is_bare(Planet.SATURN),
    )


def compute_bnn_career_sequence(planets: list[PlanetPosition], max_age: int = 100) -> BnnCareerSequence:
    """See module docstring - Saturn's transit-contact order, timed via
    Saturn's own round arithmetic (30 years/round, 2.5 years/sign)."""
    planets_by_sign = _group_planets(planets)

    saturn = next(p for p in planets if p.planet == Planet.SATURN)
    crossed = _planets_crossed_forward(
        saturn.sign, planets_by_sign, exclude={Planet.SATURN}, include_previous_sign=True,
    )

    included: list[Planet] = []
    ages: list[float] = []
    for planet in crossed:
        pos = next(p for p in planets if p.planet == planet)
        signs_forward = _house_offset(saturn.sign, pos.sign)
        first_age_ages = _round_ages(signs_forward, SATURN_ROUND_LENGTH, max_age)
        if first_age_ages:
            included.append(planet)
            ages.append(first_age_ages[0])

    return BnnCareerSequence(planets_in_order=included, ages=ages)


def compute_bhrigu_nandi_nadi(planets: list[PlanetPosition]) -> BnnResult:
    jupiter = next(p for p in planets if p.planet == Planet.JUPITER)
    jupiter_as_lagna_houses = {house: _sign_at_offset(jupiter.sign, house) for house in range(1, 13)}

    return BnnResult(
        jupiter_as_lagna_houses=jupiter_as_lagna_houses,
        karaka_readings=compute_bnn_karaka_readings(planets),
        sibling_count=compute_bnn_sibling_count(planets),
        marriage_timing=compute_bnn_marriage_timing(planets),
        short_life_indication=compute_bnn_short_life_indication(planets),
        career_sequence=compute_bnn_career_sequence(planets),
    )
