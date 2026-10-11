"""Bhrigu Chakra Paddhati (BCP), with M. Imran's Cycle-Ruler extension.

Source: "Bhrigu Chakra with Cycle Rulers" by M. Imran, Saptarishis Astrology
(https://saptarishisastrology.com/bhrigu-chakra-with-cycle-rulers-by-m-imran/).
Verified against the article's own text directly, not summarized from memory.

Classical BCP (the article's "Part A", well-established): 1 sign = 1 year of
life, linear from the Ascendant. Year 1 is ruled by the 1st house, year 2 by
the 2nd house, ... year 12 by the 12th house, then it repeats - year 13 is
the 1st house again, and so on indefinitely.

M. Imran's extension (the article's own proposed thesis, not universally-used
classical BCP): each 12-year block is additionally governed by a "Chakra
Swami" (cycle ruler), in this fixed sequence - one 12-year block per graha,
9 grahas total, cycles 1-9 spanning age 1-108:

    1st cycle (age  1- 12): Moon
    2nd cycle (age 13- 24): Mercury
    3rd cycle (age 25- 36): Venus
    4th cycle (age 37- 48): Sun
    5th cycle (age 49- 60): Mars
    6th cycle (age 61- 72): Jupiter
    7th cycle (age 73- 84): Saturn
    8th cycle (age 85- 96): Rahu
    9th cycle (age 97-108): Ketu

For each year, the same house-position-within-its-cycle (1-12) is counted a
second time, starting from the cycle ruler's own natal sign instead of the
Ascendant - giving two parallel readings per year (from Lagna, and from the
Cycle Ruler), per the article's own worked examples.

ACCURACY NOTE: the article only names 9 cycle rulers (one per graha), so it
does not define a 10th cycle for age 109+. Past age 108, only the classical
Lagna-based house is returned; `cycle_ruler` and the cycle-ruler fields are
None rather than guessed.

LONGEVITY INDICATION: "Bhrigu Chakra Paddhati & Longevity" by Sampath Kumar
Medavarapu (Saptarishis Astrology, edited by M. Imran) proposes two rules on
top of the classical BCP table above, to flag which years' houses are worth
watching for longevity:

    Rule 1: if the Ascendant (1st house) is occupied by any planet, the
            flagged house is wherever Saturn sits (from Lagna).
    Rule 2: if the Ascendant is vacant, the flagged houses are wherever the
            Moon sits (from Lagna), and the 5th/6th/8th house counted from
            the Moon's own natal sign.

Verified against the article's raw text directly (not summarized). The
article is explicit that these two rules are a tentative research proposal,
not an established or reliable technique on their own: "cannot supersede
fundamental longevity approach... astrologers should first determine whether
native is destined to lead a short, middle or long life" - its own worked
examples include a case where the rule does not fit. This module returns
which years the rule flags; it does not claim those years predict death.
"""

# Also checked against the supplied BCP-CycleLords slides:
# https://www.scribd.com/document/549460315/BCP-CycleLords
# Its cycle-ruler sign is a second Lagna; relative houses retain that base.
from __future__ import annotations

from vedic_astro.models import (
    BcpLongevityFlaggedHouse,
    BcpLongevityIndication,
    BhriguChakraYear,
    Planet,
    PlanetPosition,
    Sign,
    SIGNS_IN_ORDER,
)

# The article's own fixed cycle-ruler sequence (9 grahas, 12 years each).
CYCLE_RULERS: tuple[Planet, ...] = (
    Planet.MOON, Planet.MERCURY, Planet.VENUS, Planet.SUN, Planet.MARS,
    Planet.JUPITER, Planet.SATURN, Planet.RAHU, Planet.KETU,
)

MAX_DEFINED_AGE = 12 * len(CYCLE_RULERS)  # 108 - past this, cycle_ruler is None
MAX_CLASSICAL_AGE = 120  # 10 full rounds of the classical Lagna-only table


def _sign_at_offset(base_sign: Sign, houses_ahead: int) -> Sign:
    base_index = SIGNS_IN_ORDER.index(base_sign)
    return SIGNS_IN_ORDER[(base_index + houses_ahead - 1) % 12]


def _house_from_lagna_for_sign(ascendant_sign: Sign, sign: Sign) -> int:
    asc_index = SIGNS_IN_ORDER.index(ascendant_sign)
    sign_index = SIGNS_IN_ORDER.index(sign)
    return ((sign_index - asc_index) % 12) + 1


def _ages_for_house(house_from_lagna: int, max_age: int) -> list[int]:
    return list(range(house_from_lagna, max_age + 1, 12))


def compute_bhrigu_chakra(
    ascendant_sign: Sign, planets: list[PlanetPosition], max_age: int = MAX_CLASSICAL_AGE
) -> list[BhriguChakraYear]:
    planets_by_sign: dict[Sign, list[Planet]] = {sign: [] for sign in SIGNS_IN_ORDER}
    for p in planets:
        planets_by_sign[p.sign].append(p.planet)

    natal_sign_of: dict[Planet, Sign] = {p.planet: p.sign for p in planets}

    rows: list[BhriguChakraYear] = []
    for age in range(1, max_age + 1):
        position_in_cycle = ((age - 1) % 12) + 1
        cycle_number = ((age - 1) // 12) + 1

        sign_from_lagna = _sign_at_offset(ascendant_sign, position_in_cycle)

        cycle_ruler: Planet | None = None
        house_from_cycle_ruler: int | None = None
        sign_from_cycle_ruler: Sign | None = None
        planets_from_cycle_ruler: list[Planet] = []
        if cycle_number <= len(CYCLE_RULERS):
            cycle_ruler = CYCLE_RULERS[cycle_number - 1]
            house_from_cycle_ruler = position_in_cycle
            sign_from_cycle_ruler = _sign_at_offset(natal_sign_of[cycle_ruler], position_in_cycle)
            planets_from_cycle_ruler = planets_by_sign[sign_from_cycle_ruler]

        rows.append(
            BhriguChakraYear(
                age=age,
                cycle_number=cycle_number,
                position_in_cycle=position_in_cycle,
                house_from_lagna=position_in_cycle,
                sign_from_lagna=sign_from_lagna,
                planets_from_lagna=planets_by_sign[sign_from_lagna],
                cycle_ruler=cycle_ruler,
                house_from_cycle_ruler=house_from_cycle_ruler,
                sign_from_cycle_ruler=sign_from_cycle_ruler,
                planets_from_cycle_ruler=planets_from_cycle_ruler,
            )
        )
    return rows


def compute_bcp_longevity(
    ascendant_sign: Sign, planets: list[PlanetPosition], max_age: int = MAX_CLASSICAL_AGE
) -> BcpLongevityIndication:
    """See the LONGEVITY INDICATION section of this module's docstring for
    the source and its own caveats - this flags candidate years, it does not
    predict death."""
    moon = next(p for p in planets if p.planet == Planet.MOON)
    saturn = next(p for p in planets if p.planet == Planet.SATURN)
    lagna_occupied = any(p.house == 1 for p in planets)

    flagged_houses: list[BcpLongevityFlaggedHouse] = []
    if lagna_occupied:
        rule = "Rule 1"
        reason = "Ascendant (1st house) is occupied by at least one planet - watch Saturn's house."
        flagged_houses.append(
            BcpLongevityFlaggedHouse(
                label="Saturn's house from Lagna",
                house_from_lagna=saturn.house,
                sign=saturn.sign,
                ages=_ages_for_house(saturn.house, max_age),
            )
        )
    else:
        rule = "Rule 2"
        reason = "Ascendant (1st house) is vacant - watch the Moon's house, and the 5th/6th/8th house from the Moon."
        flagged_houses.append(
            BcpLongevityFlaggedHouse(
                label="Moon's house from Lagna",
                house_from_lagna=moon.house,
                sign=moon.sign,
                ages=_ages_for_house(moon.house, max_age),
            )
        )
        for offset, ordinal in ((5, "5th"), (6, "6th"), (8, "8th")):
            sign = _sign_at_offset(moon.sign, offset)
            house = _house_from_lagna_for_sign(ascendant_sign, sign)
            flagged_houses.append(
                BcpLongevityFlaggedHouse(
                    label=f"{ordinal} house from the Moon",
                    house_from_lagna=house,
                    sign=sign,
                    ages=_ages_for_house(house, max_age),
                )
            )

    return BcpLongevityIndication(rule=rule, reason=reason, flagged_houses=flagged_houses)
