"""Panchanga: the 5 daily almanac elements, computed at the birth moment.

Tithi/yoga/karana/nakshatra are derived from the birth-moment Sun and Moon
longitudes (the standard approach for a natal chart's panchanga, as opposed
to a general daily almanac which is anchored to sunrise). Vara (weekday) is
taken from the civil calendar date - a known simplification versus the
traditional sunrise-to-sunrise day boundary, acceptable for Phase 1.
"""

from __future__ import annotations

from datetime import date

from vedic_astro.models import PanchangaElement, PanchangaResult
from vedic_astro.nakshatra import nakshatra_for_longitude

TITHI_SPAN = 12.0
KARANA_SPAN = 6.0
YOGA_SPAN = 360 / 27
_EPSILON = 1e-9

TITHI_NAMES: list[str] = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi",
    "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi",
    "Trayodashi", "Chaturdashi",
]

YOGA_NAMES: list[str] = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda",
    "Sukarma", "Dhriti", "Shula", "Ganda", "Vriddhi", "Dhruva", "Vyaghata",
    "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyana", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma", "Indra", "Vaidhriti",
]

MOVABLE_KARANA_NAMES: list[str] = [
    "Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti",
]

# Indexed by date.weekday() (Monday=0 ... Sunday=6).
VARA_NAMES: list[str] = [
    "Somavara", "Mangalavara", "Budhavara", "Guruvara", "Shukravara", "Shanivara", "Ravivara",
]


def _tithi(sun_longitude: float, moon_longitude: float) -> tuple[PanchangaElement, str]:
    diff = (moon_longitude - sun_longitude) % 360
    index = min(int((diff + _EPSILON) // TITHI_SPAN), 29)
    paksha = "Shukla" if index < 15 else "Krishna"
    within_paksha = (index % 15) + 1
    name = TITHI_NAMES[within_paksha - 1] if within_paksha <= 14 else (
        "Purnima" if paksha == "Shukla" else "Amavasya"
    )
    return PanchangaElement(name=name, index=index + 1), paksha


def _karana(sun_longitude: float, moon_longitude: float) -> PanchangaElement:
    diff = (moon_longitude - sun_longitude) % 360
    index = min(int((diff + _EPSILON) // KARANA_SPAN), 59)
    if index == 0:
        name = "Kimstughna"
    elif index <= 56:
        name = MOVABLE_KARANA_NAMES[(index - 1) % 7]
    elif index == 57:
        name = "Shakuni"
    elif index == 58:
        name = "Chatushpada"
    else:
        name = "Naga"
    return PanchangaElement(name=name, index=index + 1)


def _yoga(sun_longitude: float, moon_longitude: float) -> PanchangaElement:
    diff = (sun_longitude + moon_longitude) % 360
    index = min(int((diff + _EPSILON) // YOGA_SPAN), 26)
    return PanchangaElement(name=YOGA_NAMES[index], index=index + 1)


def _vara(local_date: date) -> str:
    return VARA_NAMES[local_date.weekday()]


def compute_panchanga(
    sun_longitude: float, moon_longitude: float, local_date: date
) -> PanchangaResult:
    tithi, paksha = _tithi(sun_longitude, moon_longitude)
    moon_nakshatra = nakshatra_for_longitude(moon_longitude)
    return PanchangaResult(
        tithi=tithi,
        paksha=paksha,
        vara=_vara(local_date),
        nakshatra=PanchangaElement(name=moon_nakshatra.name, index=moon_nakshatra.index),
        yoga=_yoga(sun_longitude, moon_longitude),
        karana=_karana(sun_longitude, moon_longitude),
    )
