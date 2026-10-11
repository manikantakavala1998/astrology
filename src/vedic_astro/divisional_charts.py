"""Sign placements for the app's 23 divisional charts.

The sixteen Parashari divisions follow BPHS chapter 6. Supplementary D5,
D6, D8 and D11 use the traditional conventions documented by PyJHora;
D81 is cyclic D9 of D9, D108 is D12 of D9, and D144 is D12 of D12.
D24 counts forward from Leo/Cancer; D60 counts forward from Aries,
following the literal degree-only rule in BPHS 6.33-41. These choices
are explicit because other schools/software offer alternate methods.
Sources and the complete rule table are in docs/divisional-charts.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from vedic_astro.models import SIGNS_IN_ORDER, Sign
from vedic_astro.rashi_bhava import degree_in_sign, sign_for_longitude
from vedic_astro.varga import hora_sign, navamsa_sign

_EPSILON = 1e-9

def _signs_forward(start: Sign, offset: int) -> Sign:
    start_index = SIGNS_IN_ORDER.index(start)
    return SIGNS_IN_ORDER[(start_index + offset) % 12]


def _is_odd_sign(sign: Sign) -> bool:
    return SIGNS_IN_ORDER.index(sign) % 2 == 0  # 0-indexed even position = 1-indexed odd sign


def _part_index(longitude: float, divisions: int) -> int:
    span = 30 / divisions
    return min(int((degree_in_sign(longitude) + _EPSILON) // span), divisions - 1)


def drekkana_sign(longitude: float) -> Sign:
    """D3 Drekkana (siblings & initiative) - a trine count, no odd/even
    branching: the 3 divisions of a sign map to itself, its 5th sign, and
    its 9th sign."""
    birth_sign = sign_for_longitude(longitude)
    part = _part_index(longitude, 3)
    return _signs_forward(birth_sign, 4 * part)


def chaturthamsa_sign(longitude: float) -> Sign:
    """D4: successive quarters occupy the four kendras of the birth sign."""
    return _signs_forward(sign_for_longitude(longitude), 3 * _part_index(longitude, 4))


def panchamsa_sign(longitude: float) -> Sign:
    """D5: five equal parts in Mars/Saturn/Jupiter/Mercury/Venus order
    for odd signs, Venus/Mercury/Jupiter/Saturn/Mars for even signs."""
    odd = (Sign.ARIES, Sign.AQUARIUS, Sign.SAGITTARIUS, Sign.GEMINI, Sign.LIBRA)
    even = (Sign.TAURUS, Sign.VIRGO, Sign.PISCES, Sign.CAPRICORN, Sign.SCORPIO)
    signs = odd if _is_odd_sign(sign_for_longitude(longitude)) else even
    return signs[_part_index(longitude, 5)]


def shashthamsa_sign(longitude: float) -> Sign:
    """D6: start at Aries for odd signs and Libra for even signs."""
    anchor = Sign.ARIES if _is_odd_sign(sign_for_longitude(longitude)) else Sign.LIBRA
    return _signs_forward(anchor, _part_index(longitude, 6))


def _modal_sign(longitude: float, divisions: int, anchors: tuple[Sign, Sign, Sign]) -> Sign:
    # Aries/Taurus/Gemini are movable/fixed/dual; the pattern repeats.
    mode = SIGNS_IN_ORDER.index(sign_for_longitude(longitude)) % 3
    return _signs_forward(anchors[mode], _part_index(longitude, divisions))


def ashtamsa_sign(longitude: float) -> Sign:
    """D8: movable/fixed/dual signs start at Aries/Sagittarius/Leo."""
    return _modal_sign(longitude, 8, (Sign.ARIES, Sign.SAGITTARIUS, Sign.LEO))


def saptamsa_sign(longitude: float) -> Sign:
    """D7 Saptamsa (children & legacy). Odd birth sign -> divisions start
    from the sign itself; even birth sign -> start from its 7th (opposite)
    sign."""
    birth_sign = sign_for_longitude(longitude)
    anchor = _signs_forward(birth_sign, 0 if _is_odd_sign(birth_sign) else 6)
    part = _part_index(longitude, 7)
    return _signs_forward(anchor, part)


def dasamsa_sign(longitude: float) -> Sign:
    """D10 Dasamsa (career & profession). Odd birth sign -> divisions start
    from the sign itself; even birth sign -> start from its 9th sign (same
    even-sign convention as Navamsa's fixed-sign case)."""
    birth_sign = sign_for_longitude(longitude)
    anchor = _signs_forward(birth_sign, 0 if _is_odd_sign(birth_sign) else 8)
    part = _part_index(longitude, 10)
    return _signs_forward(anchor, part)


def dwadasamsa_sign(longitude: float) -> Sign:
    """D12 Dwadasamsa (parents & ancestry) - no odd/even branching: the 12
    divisions of a sign always start counting from the sign itself."""
    birth_sign = sign_for_longitude(longitude)
    part = _part_index(longitude, 12)
    return _signs_forward(birth_sign, part)


def rudramsa_sign(longitude: float) -> Sign:
    """D11: seeds run Aries, Pisces, Aquarius, ...; parts count forward.
    This is the Rudramsa convention, rather than Raman's reversed variant."""
    birth_index = SIGNS_IN_ORDER.index(sign_for_longitude(longitude))
    return SIGNS_IN_ORDER[(-birth_index + _part_index(longitude, 11)) % 12]


def shodashamsa_sign(longitude: float) -> Sign:
    """D16: movable/fixed/dual signs start at Aries/Leo/Sagittarius."""
    return _modal_sign(longitude, 16, (Sign.ARIES, Sign.LEO, Sign.SAGITTARIUS))


def vimsamsa_sign(longitude: float) -> Sign:
    """D20: movable/fixed/dual signs start at Aries/Sagittarius/Leo."""
    return _modal_sign(longitude, 20, (Sign.ARIES, Sign.SAGITTARIUS, Sign.LEO))


def chaturvimsamsa_sign(longitude: float) -> Sign:
    """D24: count forward from Leo in odd signs and Cancer in even signs."""
    anchor = Sign.LEO if _is_odd_sign(sign_for_longitude(longitude)) else Sign.CANCER
    return _signs_forward(anchor, _part_index(longitude, 24))


def nakshatramsa_sign(longitude: float) -> Sign:
    """D27: fire/earth/air/water start at Aries/Cancer/Libra/Capricorn."""
    element = SIGNS_IN_ORDER.index(sign_for_longitude(longitude)) % 4
    return _signs_forward(SIGNS_IN_ORDER[element * 3], _part_index(longitude, 27))


def khavedamsa_sign(longitude: float) -> Sign:
    """D40: start at Aries for odd signs and Libra for even signs."""
    anchor = Sign.ARIES if _is_odd_sign(sign_for_longitude(longitude)) else Sign.LIBRA
    return _signs_forward(anchor, _part_index(longitude, 40))


def akshavedamsa_sign(longitude: float) -> Sign:
    """D45: movable/fixed/dual signs start at Aries/Leo/Sagittarius."""
    return _modal_sign(longitude, 45, (Sign.ARIES, Sign.LEO, Sign.SAGITTARIUS))


def shashtiamsa_sign(longitude: float) -> Sign:
    """D60: twice the degree within the birth sign, counted from Aries.
    Reversed deity names in even signs do not reverse sign placement."""
    return _signs_forward(Sign.ARIES, _part_index(longitude, 60))


def navanavamsa_sign(longitude: float) -> Sign:
    """D81: Navamsa of Navamsa, equivalent to the cyclic 81-fold map."""
    birth_index = SIGNS_IN_ORDER.index(sign_for_longitude(longitude))
    return SIGNS_IN_ORDER[(birth_index * 81 + _part_index(longitude, 81)) % 12]


def ashtottaramsa_sign(longitude: float) -> Sign:
    """D108: apply D9 first, then D12 to its sign and fractional degree.
    Integer subdivision indices avoid rounding the intermediate longitude."""
    navamsa_part, dwadasamsa_part = divmod(_part_index(longitude, 108), 12)
    birth_index = SIGNS_IN_ORDER.index(sign_for_longitude(longitude))
    navamsa_index = (birth_index * 9 + navamsa_part) % 12
    return SIGNS_IN_ORDER[(navamsa_index + dwadasamsa_part) % 12]


def dwadasadwadasamsa_sign(longitude: float) -> Sign:
    """D144: D12 of D12, retaining the first division's fractional degree."""
    first_part, second_part = divmod(_part_index(longitude, 144), 12)
    birth_index = SIGNS_IN_ORDER.index(sign_for_longitude(longitude))
    return SIGNS_IN_ORDER[(birth_index + first_part + second_part) % 12]


# D30 Trimsamsa (evils, miseries & sickness) is the one chart here that is
# NOT an equal division: the 30 degrees of a sign split into 5 unequal
# segments ruled by Mars/Saturn/Jupiter/Mercury/Venus, in one order for odd
# signs and a different order/boundaries for even signs - each segment
# resolving to that planet's own sign in the matching odd/even polarity.
# Each tuple is (exclusive upper degree boundary, resulting sign).
_TRIMSAMSA_ODD_SEGMENTS: list[tuple[float, Sign]] = [
    (5.0, Sign.ARIES), (10.0, Sign.AQUARIUS), (18.0, Sign.SAGITTARIUS),
    (25.0, Sign.GEMINI), (30.0, Sign.LIBRA),
]
_TRIMSAMSA_EVEN_SEGMENTS: list[tuple[float, Sign]] = [
    (5.0, Sign.TAURUS), (12.0, Sign.VIRGO), (20.0, Sign.PISCES),
    (25.0, Sign.CAPRICORN), (30.0, Sign.SCORPIO),
]


def trimsamsa_sign(longitude: float) -> Sign:
    """D30 Trimsamsa - see the module-level comment above for the rule."""
    birth_sign = sign_for_longitude(longitude)
    degree = degree_in_sign(longitude)
    segments = _TRIMSAMSA_ODD_SEGMENTS if _is_odd_sign(birth_sign) else _TRIMSAMSA_EVEN_SEGMENTS
    for upper_bound, result_sign in segments:
        if degree + _EPSILON < upper_bound:
            return result_sign
    return segments[-1][1]  # unreachable: degree_in_sign is always < 30


@dataclass(frozen=True)
class VargaSpec:
    code: str
    name: str
    divisions: int
    sign_fn: Callable[[float], Sign] | None
    held_reason: str | None = None
    method: str = "Parashari"


VARGA_REGISTRY: list[VargaSpec] = [
    VargaSpec("D1", "Rasi Chart (Main Birth Chart)", 1, sign_for_longitude),
    VargaSpec("D2", "Hora (Wealth)", 2, hora_sign),
    VargaSpec("D3", "Drekkana (Siblings & Initiative)", 3, drekkana_sign),
    VargaSpec("D4", "Chaturthamsa / Turyamsa (Fixed Assets & Luck)", 4, chaturthamsa_sign),
    VargaSpec("D5", "Panchamsa (Fame & Spiritual Inclination)", 5, panchamsa_sign,
              method="Traditional Panchamsa · five equal parts"),
    VargaSpec("D6", "Shashthamsa (Debts, Diseases & Enemies)", 6, shashthamsa_sign,
              method="Traditional Shashthamsa · Aries / Libra starts"),
    VargaSpec("D7", "Saptamsa (Children & Legacy)", 7, saptamsa_sign),
    VargaSpec("D8", "Ashtamsa (Longevity & Sudden Transformations)", 8, ashtamsa_sign,
              method="Traditional Ashtamsa · Aries / Sagittarius / Leo starts"),
    VargaSpec("D9", "Navamsa (Marriage, Dharma & Inner Strength)", 9, navamsa_sign),
    VargaSpec("D10", "Dasamsa / Mahatamsa (Career & Profession)", 10, dasamsa_sign),
    VargaSpec("D11", "Rudramsa / Ekadasamsa (Gains & Victory)", 11, rudramsa_sign,
              method="Rudramsa · reverse sign seeds, forward division count"),
    VargaSpec("D12", "Dvadasamsa (Parents & Ancestry)", 12, dwadasamsa_sign),
    VargaSpec("D16", "Shodashamsa / Kalamsa (Vehicles & Material Comforts)", 16, shodashamsa_sign),
    VargaSpec("D20", "Vimsamsa (Spirituality & Religious Devotion)", 20, vimsamsa_sign),
    VargaSpec("D24", "Chaturvimsamsa / Siddhamsa (Education & Learning)", 24, chaturvimsamsa_sign,
              method="Parashari · forward count from Leo / Cancer"),
    VargaSpec("D27", "Nakshatramsa / Bhamsa (Inherent Weaknesses & Strengths)", 27, nakshatramsa_sign),
    VargaSpec("D30", "Trimsamsa (Evils, Miseries & Sickness)", 30, trimsamsa_sign),
    VargaSpec("D40", "Khavedamsa / Swavedamsa (Maternal Lineage & Auspiciousness)", 40, khavedamsa_sign),
    VargaSpec("D45", "Akshavedamsa (Paternal Lineage & Purity of Character)", 45, akshavedamsa_sign),
    VargaSpec("D60", "Shashtiamsa (Past Karma & Fine Character Blueprint)", 60, shashtiamsa_sign,
              method="BPHS · forward count from Aries using degrees within the natal sign"),
    VargaSpec("D81", "Navanavamsa (Higher Micro-level Research)", 81, navanavamsa_sign,
              method="Composite · Navamsa of Navamsa (D9 → D9, cyclic)"),
    VargaSpec("D108", "Ashtottaramsa (Advanced Astrological Research)", 108, ashtottaramsa_sign,
              method="Composite · Dvadasamsa of Navamsa (D9 → D12)"),
    VargaSpec("D144", "Dwadasa Dwadasamsa (Deepest Ancestral & Subtle Karma)", 144, dwadasadwadasamsa_sign,
              method="Composite · Dvadasamsa of Dvadasamsa (D12 → D12)"),
]
