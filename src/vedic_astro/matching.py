"""Ashtakoot Guna Milan (8-factor, 36-point marriage compatibility) + Mangal Dosha.

Classical rule-based scoring, same as the rest of this engine - no AI/model
involved. Every koota is derived from just two facts per person: Moon's
Rashi (sign) and Moon's Nakshatra, both already computed by chart.py.

IMPORTANT ACCURACY NOTE: Varna, Nadi, Gana, Tara, and Graha Maitri use
well-established, largely uncontested classical tables. Vashya and Yoni have
some genuine variation across classical sources (Vashya's dual/split signs,
Yoni's full 14x14 friend/neutral/enemy matrix) - this module uses documented,
commonly-cited simplifications for those two rather than risk silently wrong
fine-grained values. Bhakoot's classical exception/cancellation rules are not
implemented (base rule only). Cross-check results against a trusted existing
Kundali-matching source before relying on this for a real decision.
"""

from __future__ import annotations

from vedic_astro.models import SIGNS_IN_ORDER, KootaResult, KundaliChart, MangalDoshaResult, MatchReport, Planet, Sign
from vedic_astro.nakshatra import NAKSHATRA_NAMES, TARA_FAVORABLE, tara_category
from vedic_astro.planetary_relations import natural_relation
from vedic_astro.rashi_bhava import RASHI_LORD

# ---------------------------------------------------------------------------
# Varna (1 point): rashi -> varna hierarchy (Brahmin > Kshatriya > Vaishya > Shudra)
# ---------------------------------------------------------------------------

_VARNA_RANK: dict[Sign, int] = {
    Sign.CANCER: 4, Sign.SCORPIO: 4, Sign.PISCES: 4,  # Brahmin
    Sign.ARIES: 3, Sign.LEO: 3, Sign.SAGITTARIUS: 3,  # Kshatriya
    Sign.TAURUS: 2, Sign.VIRGO: 2, Sign.CAPRICORN: 2,  # Vaishya
    Sign.GEMINI: 1, Sign.LIBRA: 1, Sign.AQUARIUS: 1,  # Shudra
}
_VARNA_NAME: dict[int, str] = {4: "Brahmin", 3: "Kshatriya", 2: "Vaishya", 1: "Shudra"}


def varna_koota(bride_sign: Sign, groom_sign: Sign) -> KootaResult:
    bride_rank = _VARNA_RANK[bride_sign]
    groom_rank = _VARNA_RANK[groom_sign]
    compatible = groom_rank >= bride_rank
    return KootaResult(
        name="Varna",
        points_earned=1 if compatible else 0,
        max_points=1,
        reason=(
            f"Groom's varna {_VARNA_NAME[groom_rank]} "
            f"{'is at or above' if compatible else 'is below'} bride's varna {_VARNA_NAME[bride_rank]}"
        ),
    )


# ---------------------------------------------------------------------------
# Vashya (2 points): rashi -> vashya group. SIMPLIFIED whole-sign table -
# the two dual-bodied signs (Sagittarius, Capricorn) are classically split by
# degree into two groups; here each is assigned its single most commonly
# cited group instead.
# ---------------------------------------------------------------------------

_VASHYA_GROUP: dict[Sign, str] = {
    Sign.ARIES: "Chatushpada", Sign.TAURUS: "Chatushpada",
    Sign.GEMINI: "Manava", Sign.VIRGO: "Manava", Sign.LIBRA: "Manava", Sign.AQUARIUS: "Manava",
    Sign.CANCER: "Jalachara", Sign.PISCES: "Jalachara",
    Sign.LEO: "Vanachara",
    Sign.SCORPIO: "Keeta",
    Sign.SAGITTARIUS: "Manava",
    Sign.CAPRICORN: "Chatushpada",
}


def vashya_koota(bride_sign: Sign, groom_sign: Sign) -> KootaResult:
    bride_group = _VASHYA_GROUP[bride_sign]
    groom_group = _VASHYA_GROUP[groom_sign]
    points = 2.0 if bride_group == groom_group else 0.0
    return KootaResult(
        name="Vashya",
        points_earned=points,
        max_points=2,
        reason=f"Bride's vashya group {bride_group}, groom's {groom_group}",
    )


# ---------------------------------------------------------------------------
# Tara (3 points): nakshatra count (mod 9) in both directions -> named category.
# See nakshatra.py's tara_category/TARA_NAMES/TARA_FAVORABLE for the shared logic.
# ---------------------------------------------------------------------------


def tara_koota(bride_nakshatra_index: int, groom_nakshatra_index: int) -> KootaResult:
    bride_to_groom = tara_category(bride_nakshatra_index, groom_nakshatra_index)
    groom_to_bride = tara_category(groom_nakshatra_index, bride_nakshatra_index)
    favorable_count = sum(
        cat in TARA_FAVORABLE for cat in (bride_to_groom, groom_to_bride)
    )
    points = {0: 0.0, 1: 1.5, 2: 3.0}[favorable_count]
    return KootaResult(
        name="Tara",
        points_earned=points,
        max_points=3,
        reason=f"Bride->groom: {bride_to_groom}, groom->bride: {groom_to_bride}",
    )


# ---------------------------------------------------------------------------
# Yoni (4 points): nakshatra -> animal symbol + gender -> compatibility.
# SIMPLIFIED: full points for the same animal, zero for a classically-known
# "natural enemy" pair, a neutral middle value otherwise (the full classical
# table also has intermediate values for specific non-enemy, non-identical
# pairs, not reproduced here).
# ---------------------------------------------------------------------------

_YONI_ANIMAL: list[tuple[str, str]] = [  # (animal, gender), indexed 0-26 by nakshatra index-1
    ("Horse", "M"), ("Elephant", "M"), ("Sheep", "F"), ("Serpent", "M"), ("Serpent", "F"),
    ("Dog", "M"), ("Cat", "F"), ("Sheep", "M"), ("Cat", "M"), ("Rat", "M"),
    ("Rat", "F"), ("Cow", "M"), ("Buffalo", "F"), ("Tiger", "F"), ("Buffalo", "M"),
    ("Tiger", "M"), ("Deer", "F"), ("Deer", "M"), ("Dog", "F"), ("Monkey", "M"),
    ("Mongoose", "M"), ("Monkey", "F"), ("Lion", "F"), ("Horse", "F"), ("Lion", "M"),
    ("Cow", "F"), ("Elephant", "F"),
]
_YONI_ENEMIES: set[frozenset[str]] = {
    frozenset({"Cow", "Tiger"}), frozenset({"Elephant", "Lion"}), frozenset({"Horse", "Buffalo"}),
    frozenset({"Serpent", "Mongoose"}), frozenset({"Dog", "Deer"}), frozenset({"Cat", "Rat"}),
    frozenset({"Sheep", "Monkey"}),
}


def yoni_koota(bride_nakshatra_index: int, groom_nakshatra_index: int) -> KootaResult:
    bride_animal, _bride_gender = _YONI_ANIMAL[bride_nakshatra_index - 1]
    groom_animal, _groom_gender = _YONI_ANIMAL[groom_nakshatra_index - 1]
    if bride_animal == groom_animal:
        points, reason = 4.0, f"Same yoni animal ({bride_animal})"
    elif frozenset({bride_animal, groom_animal}) in _YONI_ENEMIES:
        points, reason = 0.0, f"Natural enemy yonis ({bride_animal} vs {groom_animal})"
    else:
        points, reason = 2.0, f"Different, non-enemy yonis ({bride_animal} vs {groom_animal})"
    return KootaResult(name="Yoni", points_earned=points, max_points=4, reason=reason)


# ---------------------------------------------------------------------------
# Graha Maitri (5 points): rashi lord -> classical planetary friendship
# ---------------------------------------------------------------------------


def graha_maitri_koota(bride_sign: Sign, groom_sign: Sign) -> KootaResult:
    bride_lord = RASHI_LORD[bride_sign]
    groom_lord = RASHI_LORD[groom_sign]
    a_to_b = natural_relation(bride_lord, groom_lord)
    b_to_a = natural_relation(groom_lord, bride_lord)
    tiers = {a_to_b, b_to_a}

    if bride_lord == groom_lord:
        points = 5.0
    elif tiers == {"friend"}:
        points = 5.0
    elif "friend" in tiers and "neutral" in tiers:
        points = 4.0
    elif tiers == {"neutral"}:
        points = 3.0
    elif "friend" in tiers and "enemy" in tiers:
        points = 1.0
    elif "neutral" in tiers and "enemy" in tiers:
        points = 0.5
    else:  # both enemy
        points = 0.0

    return KootaResult(
        name="Graha Maitri",
        points_earned=points,
        max_points=5,
        reason=f"Rashi lords {bride_lord.value} and {groom_lord.value}: {a_to_b}/{b_to_a}",
    )


# ---------------------------------------------------------------------------
# Gana (6 points): nakshatra -> gana (Deva/Manushya/Rakshasa). SIMPLIFIED
# symmetric scoring (some classical tables give directional asymmetry).
# ---------------------------------------------------------------------------

_GANA_BY_NAKSHATRA: dict[str, str] = {
    "Ashwini": "Deva", "Mrigashira": "Deva", "Punarvasu": "Deva", "Pushya": "Deva", "Hasta": "Deva",
    "Swati": "Deva", "Anuradha": "Deva", "Shravana": "Deva", "Revati": "Deva",
    "Bharani": "Manushya", "Rohini": "Manushya", "Purva Phalguni": "Manushya",
    "Uttara Phalguni": "Manushya", "Purva Ashadha": "Manushya", "Uttara Ashadha": "Manushya",
    "Purva Bhadrapada": "Manushya", "Uttara Bhadrapada": "Manushya",
    "Krittika": "Rakshasa", "Ardra": "Rakshasa", "Ashlesha": "Rakshasa", "Magha": "Rakshasa",
    "Chitra": "Rakshasa", "Vishakha": "Rakshasa", "Jyeshtha": "Rakshasa", "Mula": "Rakshasa",
    "Dhanishta": "Rakshasa", "Shatabhisha": "Rakshasa",
}


def gana_koota(bride_nakshatra_index: int, groom_nakshatra_index: int) -> KootaResult:
    bride_gana = _GANA_BY_NAKSHATRA[NAKSHATRA_NAMES[bride_nakshatra_index - 1]]
    groom_gana = _GANA_BY_NAKSHATRA[NAKSHATRA_NAMES[groom_nakshatra_index - 1]]
    if bride_gana == groom_gana:
        points = 6.0
    elif {bride_gana, groom_gana} == {"Rakshasa", "Deva"} or {bride_gana, groom_gana} == {"Rakshasa", "Manushya"}:
        points = 0.0
    else:  # Deva-Manushya mix
        points = 5.0
    return KootaResult(
        name="Gana", points_earned=points, max_points=6,
        reason=f"Bride's gana {bride_gana}, groom's {groom_gana}",
    )


# ---------------------------------------------------------------------------
# Bhakoot (7 points): rashi-to-rashi counting distance -> inauspicious combos.
# Classical exception/cancellation rules are NOT applied - base rule only.
# ---------------------------------------------------------------------------

_BHAKOOT_DOSHA_DISTANCES = {2, 12, 5, 9, 6, 8}


def bhakoot_koota(bride_sign: Sign, groom_sign: Sign) -> KootaResult:
    bride_index = SIGNS_IN_ORDER.index(bride_sign)
    groom_index = SIGNS_IN_ORDER.index(groom_sign)
    distance = ((groom_index - bride_index) % 12) + 1
    has_dosha = distance in _BHAKOOT_DOSHA_DISTANCES
    return KootaResult(
        name="Bhakoot",
        points_earned=0 if has_dosha else 7,
        max_points=7,
        reason=f"Rashi count {distance} ({'Bhakoot Dosha' if has_dosha else 'no dosha'})",
    )


# ---------------------------------------------------------------------------
# Nadi (8 points): nakshatra -> nadi (Aadi/Madhya/Antya). Same nadi = 0.
# ---------------------------------------------------------------------------

_NADI_BY_NAKSHATRA: dict[str, str] = {
    "Ashwini": "Aadi", "Ardra": "Aadi", "Punarvasu": "Aadi", "Uttara Phalguni": "Aadi",
    "Hasta": "Aadi", "Jyeshtha": "Aadi", "Mula": "Aadi", "Shatabhisha": "Aadi",
    "Purva Bhadrapada": "Aadi",
    "Bharani": "Madhya", "Mrigashira": "Madhya", "Pushya": "Madhya", "Purva Phalguni": "Madhya",
    "Chitra": "Madhya", "Anuradha": "Madhya", "Purva Ashadha": "Madhya", "Dhanishta": "Madhya",
    "Uttara Bhadrapada": "Madhya",
    "Krittika": "Antya", "Rohini": "Antya", "Ashlesha": "Antya", "Magha": "Antya",
    "Swati": "Antya", "Vishakha": "Antya", "Uttara Ashadha": "Antya", "Shravana": "Antya",
    "Revati": "Antya",
}


def nadi_koota(bride_nakshatra_index: int, groom_nakshatra_index: int) -> KootaResult:
    bride_nadi = _NADI_BY_NAKSHATRA[NAKSHATRA_NAMES[bride_nakshatra_index - 1]]
    groom_nadi = _NADI_BY_NAKSHATRA[NAKSHATRA_NAMES[groom_nakshatra_index - 1]]
    same = bride_nadi == groom_nadi
    return KootaResult(
        name="Nadi",
        points_earned=0 if same else 8,
        max_points=8,
        reason=f"Both {bride_nadi} Nadi (Nadi Dosha)" if same else f"{bride_nadi} vs {groom_nadi} Nadi",
    )


# ---------------------------------------------------------------------------
# Mangal Dosha: Mars in house 1, 2, 4, 7, 8, or 12 from the Ascendant.
# ---------------------------------------------------------------------------

_MANGAL_DOSHA_HOUSES = {1, 2, 4, 7, 8, 12}


def mangal_dosha(mars_house: int) -> MangalDoshaResult:
    has_dosha = mars_house in _MANGAL_DOSHA_HOUSES
    return MangalDoshaResult(
        has_dosha=has_dosha,
        mars_house=mars_house,
        reason=(
            f"Mars in house {mars_house} from Ascendant "
            f"({'Mangal Dosha present' if has_dosha else 'no Mangal Dosha'})"
        ),
    )


_VERDICT_THRESHOLDS: list[tuple[float, str]] = [
    (32, "Excellent match"),
    (24, "Good match"),
    (18, "Acceptable match"),
    (0, "Not recommended (below traditional 18-point minimum)"),
]


def _verdict(total_points: float) -> str:
    for threshold, label in _VERDICT_THRESHOLDS:
        if total_points >= threshold:
            return label
    return _VERDICT_THRESHOLDS[-1][1]


def compute_match_report(bride_chart: KundaliChart, groom_chart: KundaliChart) -> MatchReport:
    bride_moon = next(p for p in bride_chart.planets if p.planet == Planet.MOON)
    groom_moon = next(p for p in groom_chart.planets if p.planet == Planet.MOON)
    bride_mars = next(p for p in bride_chart.planets if p.planet == Planet.MARS)
    groom_mars = next(p for p in groom_chart.planets if p.planet == Planet.MARS)

    bride_nak = bride_moon.nakshatra.index
    groom_nak = groom_moon.nakshatra.index
    bride_sign = bride_moon.sign
    groom_sign = groom_moon.sign

    kootas = [
        varna_koota(bride_sign, groom_sign),
        vashya_koota(bride_sign, groom_sign),
        tara_koota(bride_nak, groom_nak),
        yoni_koota(bride_nak, groom_nak),
        graha_maitri_koota(bride_sign, groom_sign),
        gana_koota(bride_nak, groom_nak),
        bhakoot_koota(bride_sign, groom_sign),
        nadi_koota(bride_nak, groom_nak),
    ]
    total_points = sum(k.points_earned for k in kootas)

    bride_dosha = mangal_dosha(bride_mars.house)
    groom_dosha = mangal_dosha(groom_mars.house)
    mangal_compatible = bride_dosha.has_dosha == groom_dosha.has_dosha

    return MatchReport(
        bride_moon_sign=bride_sign,
        groom_moon_sign=groom_sign,
        bride_nakshatra=bride_moon.nakshatra.name,
        groom_nakshatra=groom_moon.nakshatra.name,
        kootas=kootas,
        total_points=total_points,
        verdict=_verdict(total_points),
        bride_mangal_dosha=bride_dosha,
        groom_mangal_dosha=groom_dosha,
        mangal_dosha_compatible=mangal_compatible,
    )
