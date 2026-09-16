"""Nakshatra (lunar mansion) and pada lookup from sidereal ecliptic longitude."""

from __future__ import annotations

from vedic_astro.models import NakshatraPlacement, NavataraEntry, Planet

NAKSHATRA_SPAN = 360 / 27  # 13d20', one nakshatra
PADA_SPAN = NAKSHATRA_SPAN / 4  # 3d20', one pada
_EPSILON = 1e-9  # guards float boundary rounding right at a nakshatra/pada edge

NAKSHATRA_NAMES: list[str] = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

# Vimshottari dasha lord cycle (also used directly by dasha.py for mahadasha
# and antardasha sequencing) - repeated 3x here to cover all 27 nakshatras.
DASHA_LORD_CYCLE: list[Planet] = [
    Planet.KETU, Planet.VENUS, Planet.SUN, Planet.MOON, Planet.MARS,
    Planet.RAHU, Planet.JUPITER, Planet.SATURN, Planet.MERCURY,
]
NAKSHATRA_LORDS: list[Planet] = DASHA_LORD_CYCLE * 3

# Tara (star) categories: counting from one nakshatra to another (mod 9)
# names the relationship - used both for the Ashtakoot Tara koota
# (matching.py, between two people) and the Navatara Chakra tool (one
# person's Moon nakshatra against all 27). Shared here so both use the same
# tested logic. Classical inclusive counting: `from_index` itself is
# position 1 (Janma).
TARA_NAMES: list[str] = [
    "Janma", "Sampat", "Vipat", "Kshema", "Pratyak", "Sadhaka", "Vadha", "Mitra", "Parama Mitra",
]
TARA_FAVORABLE: set[str] = {"Sampat", "Kshema", "Sadhaka", "Mitra", "Parama Mitra"}


def tara_category(from_index: int, to_index: int) -> str:
    """Classical inclusive counting: `from_index` itself is position 1
    (Janma), the next nakshatra is position 2 (Sampat), ..., 9 stars later
    wraps back to position 1. E.g. tara_category(1, 1) == "Janma" (your own
    nakshatra counted from itself), tara_category(1, 2) == "Sampat".
    """
    position = (to_index - from_index) % 9  # 0-8
    return TARA_NAMES[position]


def compute_navatara_chakra(moon_nakshatra_index: int) -> list[NavataraEntry]:
    """All 27 nakshatras classified by their Tara (star) relationship to the
    given Moon nakshatra (1-27) - the Navatara Chakra reference table."""
    return [
        NavataraEntry(
            nakshatra=NAKSHATRA_NAMES[target_index - 1],
            nakshatra_index=target_index,
            tara_category=(category := tara_category(moon_nakshatra_index, target_index)),
            is_favorable=category in TARA_FAVORABLE,
        )
        for target_index in range(1, 28)
    ]


def nakshatra_for_longitude(longitude: float) -> NakshatraPlacement:
    longitude = longitude % 360
    index = min(int((longitude + _EPSILON) // NAKSHATRA_SPAN), 26)
    within_nakshatra = longitude - index * NAKSHATRA_SPAN
    pada = min(int((within_nakshatra + _EPSILON) // PADA_SPAN) + 1, 4)
    return NakshatraPlacement(
        name=NAKSHATRA_NAMES[index],
        index=index + 1,
        pada=pada,
        lord=NAKSHATRA_LORDS[index],
    )
