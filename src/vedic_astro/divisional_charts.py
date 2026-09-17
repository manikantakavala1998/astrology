"""Divisional (varga) charts beyond D1/D2/D9 (see varga.py for those).

Only implements the charts whose classical starting-sign rule is
cross-source-consistent: D3, D7, D10, D12, D30 (plus the existing D1/D2/D9,
referenced here for a complete registry). The remaining 15 of the classical
"23 varga" list have real, material disagreement across sources on their
exact rule - or, for D81/D108/D144, aren't part of the classical Parashari
system at all (they're modern software-era extensions with no consistent
definition). Those are listed in VARGA_REGISTRY with `sign_fn=None` and a
`held_reason`, so the full 23-chart list a user expects is visibly present
while being honest about what's actually computed versus pending a
confirmed source - the same "flag rather than guess" pattern already used
elsewhere in this app (see matching.py's Vashya/Yoni notes).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from vedic_astro.models import SIGNS_IN_ORDER, Sign
from vedic_astro.rashi_bhava import degree_in_sign, sign_for_longitude
from vedic_astro.varga import hora_sign, navamsa_sign

_EPSILON = 1e-9

_HELD_DISPUTED = (
    "Classical rule for this chart varies across sources; held until a "
    "confirmed source is available, rather than shipping a guess."
)
_HELD_NOT_CLASSICAL = (
    "Not part of the classical Parashari divisional-chart system - a "
    "modern software-era extension with no consistent definition across "
    "sources. Held until a confirmed source is available."
)


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


VARGA_REGISTRY: list[VargaSpec] = [
    VargaSpec("D1", "Rasi Chart (Main Birth Chart)", 1, sign_for_longitude),
    VargaSpec("D2", "Hora (Wealth)", 2, hora_sign),
    VargaSpec("D3", "Drekkana (Siblings & Initiative)", 3, drekkana_sign),
    VargaSpec("D4", "Chaturthamsa / Turyamsa (Fixed Assets & Luck)", 4, None, _HELD_DISPUTED),
    VargaSpec("D5", "Panchamsa (Fame & Spiritual Inclination)", 5, None, _HELD_DISPUTED),
    VargaSpec("D6", "Shashthamsa (Debts, Diseases & Enemies)", 6, None, _HELD_DISPUTED),
    VargaSpec("D7", "Saptamsa (Children & Legacy)", 7, saptamsa_sign),
    VargaSpec("D8", "Ashtamsa (Longevity & Sudden Transformations)", 8, None, _HELD_DISPUTED),
    VargaSpec("D9", "Navamsa (Marriage, Dharma & Inner Strength)", 9, navamsa_sign),
    VargaSpec("D10", "Dasamsa / Mahatamsa (Career & Profession)", 10, dasamsa_sign),
    VargaSpec("D11", "Rudramsa / Ekadasamsa (Gains & Victory)", 11, None, _HELD_DISPUTED),
    VargaSpec("D12", "Dvadasamsa (Parents & Ancestry)", 12, dwadasamsa_sign),
    VargaSpec("D16", "Shodashamsa / Kalamsa (Vehicles & Material Comforts)", 16, None, _HELD_DISPUTED),
    VargaSpec("D20", "Vimsamsa (Spirituality & Religious Devotion)", 20, None, _HELD_DISPUTED),
    VargaSpec("D24", "Chaturvimsamsa / Siddhamsa (Education & Learning)", 24, None, _HELD_DISPUTED),
    VargaSpec("D27", "Nakshatramsa / Bhamsa (Inherent Weaknesses & Strengths)", 27, None, _HELD_DISPUTED),
    VargaSpec("D30", "Trimsamsa (Evils, Miseries & Sickness)", 30, trimsamsa_sign),
    VargaSpec("D40", "Khavedamsa / Swavedamsa (Maternal Lineage & Auspiciousness)", 40, None, _HELD_DISPUTED),
    VargaSpec("D45", "Akshavedamsa (Paternal Lineage & Purity of Character)", 45, None, _HELD_DISPUTED),
    VargaSpec("D60", "Shastiamsamsa (Past Karma & Fine Character Blueprint)", 60, None, _HELD_DISPUTED),
    VargaSpec("D81", "Navanavamsa (Higher Micro-level Research)", 81, None, _HELD_NOT_CLASSICAL),
    VargaSpec("D108", "Ashtottaramsa (Advanced Astrological Research)", 108, None, _HELD_NOT_CLASSICAL),
    VargaSpec("D144", "Dwadasadwadasamsa (Deepest Ancestral & Subtle Karma)", 144, None, _HELD_NOT_CLASSICAL),
]
