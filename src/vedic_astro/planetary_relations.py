"""Planetary friendship (graha maitri) - shared by matching.py's Graha
Maitri koota and by the Balas engines (shadbala.py's Saptavargaja Bala,
vimshopaka_bala.py's Varga Viswa).

Two independent layers combine into the classical 5-fold Panchadha
Sambandha (compound relationship):

- Natural (Naisargika) friendship: a fixed table, standard BPHS values,
  the same one matching.py has always used.
- Temporal (Tatkalika) friendship: computed from a specific chart - a
  planet occupying the 2nd/3rd/4th/10th/11th/12th house *from another
  planet's own position* is that planet's temporal friend, otherwise its
  temporal enemy. Per BPHS, this is evaluated once from the D1/Rasi
  positions only, never recomputed per divisional chart.

The compound grid (natural x temporal -> one of 5 grades) is exactly what
BPHS's own worked Vimshopaka Bala example verifies - see vimshopaka_bala.py.
"""

from __future__ import annotations

from vedic_astro.models import Planet, Sign
from vedic_astro.rashi_bhava import whole_sign_house

# Standard BPHS natural (naisargika) friendship table - unchanged from what
# matching.py has always used, just promoted here so both matching.py and
# the Balas engines share one source of truth instead of two copies that
# could silently drift apart.
NATURAL_FRIENDS: dict[Planet, set[Planet]] = {
    Planet.SUN: {Planet.MOON, Planet.MARS, Planet.JUPITER},
    Planet.MOON: {Planet.SUN, Planet.MERCURY},
    Planet.MARS: {Planet.SUN, Planet.MOON, Planet.JUPITER},
    Planet.MERCURY: {Planet.SUN, Planet.VENUS},
    Planet.JUPITER: {Planet.SUN, Planet.MOON, Planet.MARS},
    Planet.VENUS: {Planet.MERCURY, Planet.SATURN},
    Planet.SATURN: {Planet.MERCURY, Planet.VENUS},
}
NATURAL_ENEMIES: dict[Planet, set[Planet]] = {
    Planet.SUN: {Planet.VENUS, Planet.SATURN},
    Planet.MOON: set(),
    Planet.MARS: {Planet.MERCURY},
    Planet.MERCURY: {Planet.MOON},
    Planet.JUPITER: {Planet.MERCURY, Planet.VENUS},
    Planet.VENUS: {Planet.SUN, Planet.MOON},
    Planet.SATURN: {Planet.SUN, Planet.MOON, Planet.MARS},
}

_TEMPORAL_FRIEND_HOUSES = {2, 3, 4, 10, 11, 12}

# (natural, temporal) -> compound grade, per BPHS Ch.3 v.57-58.
_PANCHADHA_GRID: dict[tuple[str, str], str] = {
    ("friend", "friend"): "great_friend",
    ("neutral", "friend"): "friend",
    ("friend", "enemy"): "neutral",
    ("enemy", "friend"): "neutral",
    ("neutral", "enemy"): "enemy",
    ("enemy", "enemy"): "great_enemy",
}


def natural_relation(subject: Planet, other: Planet) -> str:
    if subject == other:
        return "same"
    if other in NATURAL_FRIENDS[subject]:
        return "friend"
    if other in NATURAL_ENEMIES[subject]:
        return "enemy"
    return "neutral"


def temporal_relation(subject_sign: Sign, other_sign: Sign) -> str:
    """Friend if `other_sign` falls in the 2nd/3rd/4th/10th/11th/12th house
    counted from `subject_sign` as house 1 (whole-sign), otherwise enemy -
    a strict binary, no temporal-neutral tier."""
    house = whole_sign_house(other_sign, subject_sign)
    return "friend" if house in _TEMPORAL_FRIEND_HOUSES else "enemy"


def panchadha_relation(subject: Planet, subject_sign: Sign, other: Planet, other_sign: Sign) -> str:
    """The 5-fold compound relationship of `other` as seen from `subject`,
    combining natural + temporal friendship. Returns "own" when subject
    and other are the same planet (own-sign case - callers typically only
    invoke this for subject != the sign's own lord, but the same-planet
    case is handled here for completeness)."""
    if subject == other:
        return "own"
    natural = natural_relation(subject, other)
    temporal = temporal_relation(subject_sign, other_sign)
    return _PANCHADHA_GRID[(natural, temporal)]
