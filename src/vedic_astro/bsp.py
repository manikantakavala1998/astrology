"""Bhrigu Sarala Paddhati (BSP) - a numbered series of individual rules
originally published one-at-a-time in Saptarishis Astrology magazine
(2008-2010), each verified directly against its own dedicated article (not
summarized from memory, and not guessed for the ones left out below):

- BSP-1 (Saptarishis Astrology): Saturn's Karmic House - permanent, not
  age-timed - is the 4th house from wherever Saturn sits natally.
- BSP-2 (Saptarishis Astrology): Jupiter's Karmic House - permanent - is
  both the 10th AND 6th house from wherever Jupiter sits natally.
- BSP-5 (Saptarishis Astrology): when Jupiter and Saturn are conjunct (same
  house), whichever house holds Aries is "spoilt/activated."
- BSP-6, 8, 9, 10, 11, 13 (Venkat Ramana / Saptarishis Astrology): six
  age-timed rules (Mars/Rahu/Ketu/Jupiter/Jupiter/Saturn) - see
  compute_bsp_rules() below for the "special status" precondition system.
- BSP-14 (Saptarishis Astrology, "Bhava Sutra Series"): Past Life Bhava
  (Bhrighu Bhava) - permanent - count forward from the Ascendant by the
  Ascendant sign's own natural zodiac number (Aries=1, ... Pisces=12);
  verified exactly against all 9 of the article's own worked charts (Sri
  Ram, MJ, B.V. Raman, JFK, Gandhi, Obama, Bill Gates, and two private
  charts).
- BSP-15 (Saptarishis Astrology, "Graha Sutra Series - Shukra Reveals"):
  Venus's own house (or a planet it conjoins, and that planet's house
  lordships) "can, not will" indicate disease/medical expense, death, or
  dramatic trouble; Venus can also afflict the 12th house from itself. This
  one is explicitly qualitative in the source ("all the above results...
  would affect it at least mildly irrespective of the conditions") - not a
  strict prediction, so it's returned as a lookup, not a special-status gate.

NOT implemented: BSP-3/4 (the source's own official free-download page lists
them but the download links are broken, and no accessible mirror exists -
not guessed rather than fabricated); BSP-7/12 (a Kakshya/Ashtakavarga-slot
refinement layer that further narrows BSP-6/10 to one specific planet or
signification - a real, well-specified technique, just not yet built here);
BSP-22 (a separate paid article, not part of the free series).

Each of the 6 age-timed rules only applies to a chart at all if its planet
has "special status" - the source lists several alternative preconditions
per rule (being in the Ascendant, being the Ascendant lord for specific
rising signs, exalted/moolatrikona/own-sign/retrograde/debilitated, in a
kendra/trikona house, "influencing" the Ascendant or its lord). Two
INTERPRETATION NOTES on ambiguous wording in the source:

1. "Influencing the Ascendant / Ascendant Lord" is implemented here as
   "aspects the Ascendant's house / the Ascendant lord's house" (Graha
   Drishti, already computed by aspects.py) - the source does not define
   "influencing" more precisely than that.
2. Rules 8/9 state the trigger sign pair as "Aquarian/Scorpio Ascendant" for
   Rahu/Ketu - this is the source's own wording, following the alternate
   co-lordship convention (Rahu with Aquarius, Ketu with Scorpio) used in
   some Jyotish traditions, not a typo for the nodes' own signs.

If special status holds, the rule flags a single fixed age (not a repeating
cycle, unlike bcp.py) and a house offset from that planet's own natal house
- both taken directly from the source's own rule table.
"""

from __future__ import annotations

from vedic_astro.dignity import planet_dignity
from vedic_astro.models import (
    BspAriesSpoilt, BspHouseNote, BspRuleResult, BspVenusReveals,
    Planet, PlanetAspect, PlanetDignity, PlanetPosition, Sign, SIGNS_IN_ORDER,
)
from vedic_astro.rashi_bhava import RASHI_LORD
from vedic_astro.shadbala import MOOLATRIKONA_RANGE, MOOLATRIKONA_SIGN

_KENDRA_TRIKONA_HOUSES = {1, 4, 5, 7, 9, 10}


def _sign_at_offset(base_sign: Sign, houses_ahead: int) -> Sign:
    base_index = SIGNS_IN_ORDER.index(base_sign)
    return SIGNS_IN_ORDER[(base_index + houses_ahead - 1) % 12]


def _house_offset(from_house: int, offset: int) -> int:
    return ((from_house - 1 + offset - 1) % 12) + 1


def _has_dignity_status(planet: Planet, sign: Sign, degree_in_sign: float, retrograde: bool) -> bool:
    if retrograde:
        return True
    dignity = planet_dignity(planet, sign)
    if dignity in (PlanetDignity.EXALTED, PlanetDignity.DEBILITATED, PlanetDignity.OWN_SIGN):
        return True
    if planet in MOOLATRIKONA_SIGN:
        lo, hi = MOOLATRIKONA_RANGE[planet]
        if MOOLATRIKONA_SIGN[planet] == sign and lo <= degree_in_sign < hi:
            return True
    return False


def _shared_special_status(
    planet: Planet,
    planet_pos: PlanetPosition,
    ascendant_sign: Sign,
    planets: list[PlanetPosition],
    aspects: list[PlanetAspect],
) -> list[str]:
    """The precondition bullets common to every BSP rule in this module,
    minus the rule-specific "as Ascendant/Ascendant-lord for sign X" bullet
    (added separately per rule)."""
    reasons: list[str] = []
    asc_lord = RASHI_LORD[ascendant_sign]
    asc_lord_pos = next((p for p in planets if p.planet == asc_lord), None)

    if planet_pos.house == 1:
        reasons.append(f"{planet.value} is in the Ascendant")

    if any(a.source_planet == planet and a.target_house == 1 for a in aspects):
        reasons.append(f"{planet.value} aspects (influences) the Ascendant")

    if asc_lord_pos is not None and any(
        a.source_planet == planet and a.target_house == asc_lord_pos.house for a in aspects
    ):
        reasons.append(f"{planet.value} aspects (influences) the Ascendant lord ({asc_lord.value})")

    if _has_dignity_status(planet, planet_pos.sign, planet_pos.degree_in_sign, planet_pos.retrograde):
        reasons.append(f"{planet.value} has a strong/weak dignity status (exalted/moolatrikona/own/retrograde/debilitated)")

    if planet_pos.house in _KENDRA_TRIKONA_HOUSES:
        reasons.append(f"{planet.value} is in a kendra or trikona house (house {planet_pos.house})")

    return reasons


def _rule(
    rule_number: int,
    planet: Planet,
    ascendant_sign: Sign,
    planets: list[PlanetPosition],
    aspects: list[PlanetAspect],
    age: int,
    house_offset: int,
    aspect_used: int | None,
    trigger_signs: tuple[Sign, Sign],
    trigger_description: str,
    extra_check: bool = True,
    check_luminary_conjunction: bool = False,
    additional_own_houses: tuple[int, ...] = (),
) -> BspRuleResult:
    planet_pos = next(p for p in planets if p.planet == planet)
    reasons = _shared_special_status(planet, planet_pos, ascendant_sign, planets, aspects)

    if ascendant_sign in trigger_signs and extra_check:
        reasons.append(trigger_description)

    if planet_pos.house in additional_own_houses:
        reasons.append(f"{planet.value} is in house {planet_pos.house} from Lagna")

    if check_luminary_conjunction and any(
        p.house == planet_pos.house and p.planet in (Planet.SUN, Planet.MOON) for p in planets
    ):
        reasons.append(f"{planet.value} is conjunct a luminary (Sun/Moon)")

    special_status = len(reasons) > 0
    affected_house = _house_offset(planet_pos.house, house_offset) if special_status else None
    affected_sign = SIGNS_IN_ORDER[(SIGNS_IN_ORDER.index(ascendant_sign) + affected_house - 1) % 12] if affected_house else None

    summary = (
        f"BSP Rule #{rule_number}: {planet.value} has special status in this chart - "
        f"watch age {age} (house {affected_house} from Lagna)."
        if special_status
        else f"BSP Rule #{rule_number}: {planet.value} has no special status in this chart - rule does not apply."
    )

    return BspRuleResult(
        rule_number=rule_number,
        planet=planet,
        special_status=special_status,
        special_status_reasons=reasons,
        age=age,
        house_offset=house_offset,
        aspect_used=aspect_used,
        affected_house_from_lagna=affected_house,
        affected_sign=affected_sign,
        summary=summary,
    )


def compute_bsp_rules(
    ascendant_sign: Sign, planets: list[PlanetPosition], aspects: list[PlanetAspect]
) -> list[BspRuleResult]:
    no_planets_in_lagna = not any(p.house == 1 for p in planets)
    rahu_ketu_only_in_lagna = all(
        p.planet in (Planet.RAHU, Planet.KETU) for p in planets if p.house == 1
    )

    return [
        _rule(
            6, Planet.MARS, ascendant_sign, planets, aspects, age=27, house_offset=10, aspect_used=None,
            trigger_signs=(Sign.ARIES, Sign.SCORPIO),
            trigger_description="Martian Ascendant (Aries/Scorpio rising) with no planets in the Ascendant",
            extra_check=no_planets_in_lagna,
        ),
        _rule(
            8, Planet.RAHU, ascendant_sign, planets, aspects, age=38, house_offset=6, aspect_used=None,
            trigger_signs=(Sign.AQUARIUS, Sign.SCORPIO),
            trigger_description="Aquarian/Scorpio Ascendant with no planets other than the nodes in the Ascendant",
            extra_check=rahu_ketu_only_in_lagna,
            check_luminary_conjunction=True,
        ),
        _rule(
            9, Planet.KETU, ascendant_sign, planets, aspects, age=24, house_offset=12, aspect_used=None,
            trigger_signs=(Sign.AQUARIUS, Sign.SCORPIO),
            trigger_description="Aquarian/Scorpio Ascendant with no planets other than the nodes in the Ascendant",
            extra_check=rahu_ketu_only_in_lagna,
            check_luminary_conjunction=True,
            additional_own_houses=(2, 8),
        ),
        _rule(
            10, Planet.JUPITER, ascendant_sign, planets, aspects, age=40, house_offset=9, aspect_used=9,
            trigger_signs=(Sign.SAGITTARIUS, Sign.PISCES),
            trigger_description="Jupiter is the Ascendant lord (Sagittarius/Pisces rising)",
        ),
        _rule(
            11, Planet.JUPITER, ascendant_sign, planets, aspects, age=32, house_offset=5, aspect_used=5,
            trigger_signs=(Sign.SAGITTARIUS, Sign.PISCES),
            trigger_description="Jupiter is the Ascendant lord (Sagittarius/Pisces rising)",
        ),
        _rule(
            13, Planet.SATURN, ascendant_sign, planets, aspects, age=20, house_offset=3, aspect_used=3,
            trigger_signs=(Sign.CAPRICORN, Sign.AQUARIUS),
            trigger_description="Saturn is the Ascendant lord (Capricorn/Aquarius rising)",
        ),
    ]


def _house_note(
    rule_number: int, title: str, ascendant_sign: Sign, planets: list[PlanetPosition], house_from_lagna: int, note: str
) -> BspHouseNote:
    sign = SIGNS_IN_ORDER[(SIGNS_IN_ORDER.index(ascendant_sign) + house_from_lagna - 1) % 12]
    return BspHouseNote(
        rule_number=rule_number,
        title=title,
        house_from_lagna=house_from_lagna,
        sign=sign,
        planets_in_house=[p.planet for p in planets if p.sign == sign],
        note=note,
    )


def compute_bsp_house_notes(ascendant_sign: Sign, planets: list[PlanetPosition]) -> list[BspHouseNote]:
    """BSP-1, BSP-2, BSP-14 - permanent house notes, not age-timed. See this
    module's docstring for each rule's source and exact wording."""
    saturn = next(p for p in planets if p.planet == Planet.SATURN)
    jupiter = next(p for p in planets if p.planet == Planet.JUPITER)

    notes = [
        _house_note(
            1, "Saturn's Karmic House", ascendant_sign, planets,
            _house_offset(saturn.house, 4),
            "Saturn creates lifelong ups and downs (fluctuations) in at least one signification of this house.",
        ),
        _house_note(
            2, "Jupiter's Karmic House (10th)", ascendant_sign, planets,
            _house_offset(jupiter.house, 10),
            "Jupiter creates lifelong ups and downs in at least one signification of this house.",
        ),
        _house_note(
            2, "Jupiter's Karmic House (6th)", ascendant_sign, planets,
            _house_offset(jupiter.house, 6),
            "Jupiter creates lifelong ups and downs in at least one signification of this house.",
        ),
    ]

    ascendant_zodiac_number = SIGNS_IN_ORDER.index(ascendant_sign) + 1
    notes.append(
        _house_note(
            14, "Past Life Bhava (Bhrighu Bhava)", ascendant_sign, planets,
            ascendant_zodiac_number,
            "The most important karma carried into this life from past lives - see this house's "
            "significations, its lord's placement, and aspects/conjunctions on both.",
        )
    )
    return notes


def compute_bsp_aries_spoilt(ascendant_sign: Sign, planets: list[PlanetPosition]) -> BspAriesSpoilt | None:
    """BSP-5: Jupiter and Saturn conjunct (same house) spoils/activates
    whichever house holds Aries. None if the condition doesn't hold."""
    jupiter = next(p for p in planets if p.planet == Planet.JUPITER)
    saturn = next(p for p in planets if p.planet == Planet.SATURN)
    if jupiter.house != saturn.house:
        return None

    aries_house = _house_from_lagna_for_sign(ascendant_sign, Sign.ARIES)
    return BspAriesSpoilt(
        house_from_lagna=aries_house,
        planets_in_house=[p.planet for p in planets if p.sign == Sign.ARIES],
    )


def _house_from_lagna_for_sign(ascendant_sign: Sign, sign: Sign) -> int:
    asc_index = SIGNS_IN_ORDER.index(ascendant_sign)
    sign_index = SIGNS_IN_ORDER.index(sign)
    return ((sign_index - asc_index) % 12) + 1


def compute_bsp_venus_reveals(ascendant_sign: Sign, planets: list[PlanetPosition]) -> BspVenusReveals:
    """BSP-15 - see this module's docstring: qualitative, not a strict rule."""
    venus = next(p for p in planets if p.planet == Planet.VENUS)
    conjunct: list[Planet] = [p.planet for p in planets if p.sign == venus.sign and p.planet != Planet.VENUS]

    lordships: dict[str, list[int]] = {}
    for planet in conjunct:
        lordships[planet.value] = [
            house for house in range(1, 13)
            if RASHI_LORD[SIGNS_IN_ORDER[(SIGNS_IN_ORDER.index(ascendant_sign) + house - 1) % 12]] == planet
        ]

    twelfth_sign = _sign_at_offset(venus.sign, 12)
    return BspVenusReveals(
        venus_house_from_lagna=venus.house,
        venus_sign=venus.sign,
        conjunct_planets=conjunct,
        conjunct_planet_lordships=lordships,
        twelfth_from_venus_house_from_lagna=_house_from_lagna_for_sign(ascendant_sign, twelfth_sign),
        twelfth_from_venus_sign=twelfth_sign,
    )
