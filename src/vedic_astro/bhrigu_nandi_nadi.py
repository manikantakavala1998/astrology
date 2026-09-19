"""Bhrigu Nandi Nadi (BNN) - a no-Lagna, Jupiter-as-reference-point Nadi
system, read from two source texts:

- "Bhrigu Nandi Nadi" by R.G. Rao (~500 worked charts).
- "Brighu Naadi Sangraha" by N. Srinivasan Shastry (a companion text in the
  same tradition).

Both texts were OCR-extracted and read in full (not summarized from memory)
before this module was written. Both state, in their own introductions,
the same core reading method for any karaka (significator) planet: the sign
it occupies, its dispositor (sign lord), planets conjunct it, planets in
the signs adjacent to it (2nd/next and 12th/previous) and in the 7th from
it, sign-exchange (parivartana) with its dispositor, natural friendship
with its dispositor, its dignity, and its retrograde status. That general
procedure is implemented once here (`_read_karaka`) and applied to all nine
grahas.

KARAKAS - stated in both introductions, applied throughout both books:
Sun=father, Moon=mother, Mars=siblings (general) / husband (female native),
Mercury=education, Jupiter=children (per the karaka table) *and* the
native's own self (for the sibling-count and transit-timing algorithms -
the source texts use Jupiter both ways without reconciling them), Venus=
wife (male native) / wealth, Saturn=profession/karma, Rahu&Ketu=family
circle, travel, obstruction. This app does not record the native's sex, so
wherever a rule depends on it (marriage timing), both variants are
returned rather than guessed.

TRANSIT-ROUND TIMING: both texts use a simplified, non-ephemeris model -
Jupiter moves 1 sign per year, completing a 12-year round; the book itself
repeatedly shows the arithmetic "12 x rounds_completed + signs_forward =
age" (e.g. R.G. Rao PAGE 274: "Jupiter completes three rounds and contacts
Rahu after four years (12 x 3 = 36 and 36 + 4 = 40)"). This is implemented
directly as `_round_ages()`. Saturn gets a parallel model at 30 years per
round (2.5 years/sign) - both texts state this round length, though R.G.
Rao's own single worked example of the arithmetic ("30 + 4 x 2 + 2 = 40",
PAGE 231) does not cleanly reduce to a 2.5-years/sign formula; that specific
example is not reproduced here, only the stated round length.

SIBLING COUNT: R.G. Rao Chart 1 (PAGE 6) gives the clearest worked example
- "Jupiter represents the native"; a planet in the sign immediately before
Jupiter (its 12th) is an elder sibling; every planet Jupiter's forward
transit crosses before returning to its own sign is a younger sibling, in
crossing order; Rahu/Ketu are excluded from the count (explicit in Chart
44, PAGE 39: "there are no planets behind Jupiter except Ketu... he was the
eldest born"); gender is Moon/Venus=sister, Sun/Mars/Saturn/Mercury=brother
(per Chart 1 and Chart 8). NOTE: the source is not fully self-consistent -
Chart 431 (PAGE 279) reads a lone Ketu behind Jupiter as making the native
the *youngest*, contradicting Chart 44's exclusion rule, and Chart 222
(PAGE 150) derives seniority from planets' position relative to Mars (the
siblings-karaka) rather than Jupiter, with the elder/younger sense
reversed. This module implements the Chart 1 version and does not attempt
to reconcile those contradictions.

SHORT-LIFE / POVERTY INDICATION: R.G. Rao PAGE 193-194, stated as a direct
general conclusion (not one chart's narrative): "when Jupiter has no planet
either in the adjacent houses or in the 7th house, the native of such a
horoscope will be short-lived. If Saturn is similarly disposed, the native
of such a horoscope will experience poverty and difficulties in life."

CAREER SEQUENCE: both texts read Saturn's transit contacts (in forward
order from its natal sign) as the sequence of career stages/jobs, the same
structural device as the sibling-crossing algorithm, applied to Saturn
instead of Jupiter. Nodes are excluded here too, for consistency with the
one place (siblings) where the source is explicit about node exclusion.

NOT IMPLEMENTED: the hundreds of multi-condition combination-dictionary
entries scattered through both books (e.g. "Jupiter in Cancer having Venus
with him and Mars in the 7th house to Jupiter with Moon in the 4th house to
Jupiter -> first wife will not have children", R.G. Rao PAGE 37). Both
texts' own worked material shows these almost never fire on an exact match
in practice and would need a scoring/partial-match approach to be
meaningful - building them as strict rule matches risks confidently wrong
output, so they are left out rather than guessed at. Also not implemented:
the birth-environment lookup tables (temple type, house door-facing
direction keyed to Rahu/Ketu/Sun sign) from Brighu Naadi Sangraha, and any
chart-specific narrative (curse/remedy stories, physiognomic name
derivation) that both texts themselves flag as non-general.
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
    Planet,
    PlanetPosition,
    Sign,
    SIGNS_IN_ORDER,
)
from vedic_astro.planetary_relations import natural_relation
from vedic_astro.rashi_bhava import RASHI_LORD

JUPITER_ROUND_LENGTH = 12
SATURN_ROUND_LENGTH = 30
_YEARS_PER_SATURN_SIGN = SATURN_ROUND_LENGTH / 12

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

# Sun/Mars/Saturn/Mercury=brother, Moon/Venus=sister - per R.G. Rao Chart 1
# (PAGE 6) and Chart 8 (PAGE 18-19). Chart 1 itself counts Rahu among the
# "five younger brothers" (crossing order: Mars, Rahu, Sun, Saturn,
# Mercury), so Rahu is classified as a brother here too, on that one
# example's authority - Ketu's gender is not demonstrated anywhere in
# either source and is deliberately left unclassified (counted in
# younger_count/elder_count but contributing to neither gender breakdown).
_BROTHER_PLANETS = {Planet.SUN, Planet.MARS, Planet.SATURN, Planet.MERCURY, Planet.RAHU}
_SISTER_PLANETS = {Planet.MOON, Planet.VENUS}
# Only Ketu is excluded from the elder-sibling test itself (R.G. Rao Chart
# 44, PAGE 39: a lone Ketu behind Jupiter still leaves the native "the
# eldest born") - nodes are NOT excluded from the younger-sibling crossing
# count, since Chart 1 explicitly counts Rahu there.
_ELDER_TEST_EXCLUDED = {Planet.KETU}
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


def _round_ages(signs_forward: int, round_length: int, max_age: int) -> list[int]:
    """The book's own repeated arithmetic: age = round_length * rounds_completed
    + years_into_current_round, where years_into_current_round is
    signs_forward (1-12) scaled to the round's own year-per-sign rate."""
    years_per_sign = round_length / 12
    first_age = round(signs_forward * years_per_sign)
    return [age for age in range(first_age, max_age + 1, round_length) if age >= 1]


def _planets_crossed_forward(
    base_sign: Sign, planets_by_sign: dict[Sign, list[Planet]], exclude: set[Planet]
) -> list[Planet]:
    """Planets encountered going forward sign-by-sign from `base_sign`
    (exclusive), stopping short of the 12th/previous sign - the shared
    'transit-contact sequence' primitive used for both the sibling count
    (from Jupiter) and the career sequence (from Saturn).

    The 12th/previous sign is deliberately excluded here: R.G. Rao's Chart 1
    (PAGE 6) places the Moon there and reads it as the *elder* sibling, and
    explicitly does not include it among the five/six planets "crossed" for
    younger siblings - i.e. the 12th sign is reserved for the separate
    elder-sibling test (see compute_bnn_sibling_count), not swept here.
    """
    crossed: list[Planet] = []
    for houses_ahead in range(2, 12):
        sign = _sign_at_offset(base_sign, houses_ahead)
        for planet in planets_by_sign[sign]:
            if planet not in exclude:
                crossed.append(planet)
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
    planets_by_sign: dict[Sign, list[Planet]] = {sign: [] for sign in SIGNS_IN_ORDER}
    for p in planets:
        planets_by_sign[p.sign].append(p.planet)
    dispositor_sign_of: dict[Planet, Sign] = {p.planet: p.sign for p in planets}

    return [
        _read_karaka(karaka, planets, planets_by_sign, dispositor_sign_of)
        for karaka in (
            Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY, Planet.JUPITER,
            Planet.VENUS, Planet.SATURN, Planet.RAHU, Planet.KETU,
        )
    ]


def compute_bnn_sibling_count(planets: list[PlanetPosition]) -> BnnSiblingCount:
    """See module docstring for the source (R.G. Rao Chart 1) and its own
    acknowledged inconsistencies elsewhere in the book."""
    planets_by_sign: dict[Sign, list[Planet]] = {sign: [] for sign in SIGNS_IN_ORDER}
    for p in planets:
        planets_by_sign[p.sign].append(p.planet)

    jupiter = next(p for p in planets if p.planet == Planet.JUPITER)
    previous_sign = _sign_at_offset(jupiter.sign, 12)
    elder_candidates = [p for p in planets_by_sign[previous_sign] if p not in _ELDER_TEST_EXCLUDED]
    elder_planet = elder_candidates[0] if elder_candidates else None

    younger_planets = _planets_crossed_forward(jupiter.sign, planets_by_sign, exclude={Planet.JUPITER})

    def _gender_breakdown(planet_list: list[Planet]) -> dict[str, int]:
        return {
            "brothers": sum(1 for p in planet_list if p in _BROTHER_PLANETS),
            "sisters": sum(1 for p in planet_list if p in _SISTER_PLANETS),
        }

    elder_list = [elder_planet] if elder_planet else []
    return BnnSiblingCount(
        elder_planet=elder_planet,
        younger_planets=younger_planets,
        elder_count=len(elder_list),
        younger_count=len(younger_planets),
        elder_gender_breakdown=_gender_breakdown(elder_list),
        younger_gender_breakdown=_gender_breakdown(younger_planets),
    )


def compute_bnn_marriage_timing(planets: list[PlanetPosition], max_age: int = 100) -> BnnMarriageTiming:
    """Marriage occurs when transiting Jupiter reaches the spouse-karaka's
    natal sign - Venus for a male native, Mars for a female native (both
    texts). See module docstring for why both variants are returned."""
    jupiter = next(p for p in planets if p.planet == Planet.JUPITER)
    venus = next(p for p in planets if p.planet == Planet.VENUS)
    mars = next(p for p in planets if p.planet == Planet.MARS)

    def _variant(spouse_karaka: Planet, spouse_sign: Sign) -> BnnMarriageTimingVariant:
        signs_forward = _house_offset(jupiter.sign, spouse_sign)
        return BnnMarriageTimingVariant(
            spouse_karaka=spouse_karaka,
            spouse_karaka_sign=spouse_sign,
            ages=_round_ages(signs_forward, JUPITER_ROUND_LENGTH, max_age),
        )

    return BnnMarriageTiming(
        male_native=_variant(Planet.VENUS, venus.sign),
        female_native=_variant(Planet.MARS, mars.sign),
    )


def compute_bnn_short_life_indication(planets: list[PlanetPosition]) -> BnnShortLifeIndication:
    """See module docstring - R.G. Rao PAGE 193-194."""
    planets_by_sign: dict[Sign, list[Planet]] = {sign: [] for sign in SIGNS_IN_ORDER}
    for p in planets:
        planets_by_sign[p.sign].append(p.planet)

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
    planets_by_sign: dict[Sign, list[Planet]] = {sign: [] for sign in SIGNS_IN_ORDER}
    for p in planets:
        planets_by_sign[p.sign].append(p.planet)

    saturn = next(p for p in planets if p.planet == Planet.SATURN)
    crossed = _planets_crossed_forward(saturn.sign, planets_by_sign, exclude={Planet.SATURN})

    ages: list[int] = []
    for planet in crossed:
        pos = next(p for p in planets if p.planet == planet)
        signs_forward = _house_offset(saturn.sign, pos.sign)
        first_age_ages = _round_ages(signs_forward, SATURN_ROUND_LENGTH, max_age)
        ages.append(first_age_ages[0] if first_age_ages else max_age)

    return BnnCareerSequence(planets_in_order=crossed, ages=ages)


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
