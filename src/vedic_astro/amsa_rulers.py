"""Amsa deities/designations in BPHS chapter 6, from natal longitudes.

Deity order is independent of the sign-map order. In particular D24 and D60
reverse deity names in even natal signs without reversing chart placement.
D30 has five unequal spans, not thirty one-degree deity subdivisions.
"""
from __future__ import annotations

from dataclasses import dataclass

from vedic_astro.divisional_charts import VARGA_REGISTRY, _part_index
from vedic_astro.models import KundaliChart, SIGNS_IN_ORDER
from vedic_astro.rashi_bhava import degree_in_sign, sign_for_longitude

SOURCE_URL = "https://vedic-astro.s3.amazonaws.com/books/bhrihat_parasara_hora_shastra.pdf#page=9"
TRANSCRIPTION_URL = "https://divyachadhava.com/en/sanatan-sahitya/bphs-chapter-6-the-sixteen-divisions-of-a-r-i"

D20_ODD = ("Kali", "Gauri", "Jaya", "Lakshmi", "Vijaya", "Vimala", "Sati", "Tara", "Jvalamukhi", "Shveta",
           "Lalita", "Bagalamukhi", "Pratyangira", "Shachi", "Raudri", "Bhavani", "Varada", "Jaya", "Tripura", "Sumukhi")
D20_EVEN = ("Daya", "Megha", "Chinnashirsha", "Pishachini", "Dhumavati", "Matangi", "Bala", "Bhadra", "Aruna", "Anala",
            "Pingala", "Chuchchuka", "Ghora", "Varahi", "Vaishnavi", "Sita", "Bhuvaneshvari", "Bhairavi", "Mangala", "Aparajita")
D27 = ("Ashvini Kumara", "Yama", "Agni", "Brahma", "Chandra", "Isha", "Aditi", "Jiva", "Ahi", "Pitris", "Bhaga",
       "Aryaman", "Surya", "Tvashta", "Marut", "Indragni", "Mitra", "Vasava", "Rakshasa", "Apas", "Vishvadeva",
       "Govinda", "Vasu", "Varuna", "Ajapada", "Ahirbudhnya", "Pushan")
D60 = ("Ghora", "Rakshasa", "Deva", "Kubera", "Yaksha", "Kinnara", "Bhrashta", "Kulaghna", "Garala", "Vahni",
       "Maya", "Purishaka", "Apampati", "Marutvan", "Kala", "Sarpa", "Amrita", "Indu", "Mridu", "Komala",
       "Heramba", "Brahma", "Vishnu", "Maheshvara", "Deva", "Ardra", "Kalinasha", "Kshitisha", "Kamalakara", "Gulika",
       "Mrityu", "Kala", "Davagni", "Ghora", "Yama", "Kantaka", "Shuddha", "Amrita", "Purnachandra", "Vishadagdha",
       "Kulanasha", "Vamshakshaya", "Utpata", "Kala", "Saumya", "Komala", "Shitala", "Karaladamshtra", "Chandramukhi", "Pravina",
       "Kalapavaka", "Dandayudha", "Nirmala", "Saumya", "Krura", "Atishitala", "Amrita", "Payodhi", "Bhramana", "Chandrarekha")

SEQUENCES: dict[str, tuple[str, ...]] = {
    "D3": ("Narada", "Agastya", "Durvasa"),
    "D4": ("Sanaka", "Sananda", "Sanatkumara", "Sanatana"),
    "D7": ("Kshara", "Kshira", "Dadhi", "Ghrita", "Ikshu Rasa", "Madya", "Shuddha Jala"),
    "D10": ("Indra", "Agni", "Yama", "Nirriti (Rakshasa)", "Varuna", "Vayu", "Kubera", "Ishana", "Brahma", "Ananta"),
    "D12": ("Ganesha", "Ashvini Kumara", "Yama", "Sarpa"),
    "D16": ("Brahma", "Vishnu", "Shiva", "Surya"),
    "D24": ("Skanda", "Parashudhara", "Anala", "Vishvakarma", "Bhaga", "Mitra", "Maya", "Antaka", "Vrishadhvaja", "Govinda", "Madana", "Bhima"),
    "D27": D27,
    "D40": ("Vishnu", "Chandra", "Marichi", "Tvashta", "Dhata", "Shiva", "Surya", "Yama", "Yaksha", "Gandharva", "Kala", "Varuna"),
    "D60": D60,
}
REVERSED_EVEN = {"D7", "D10", "D16", "D24", "D27", "D60"}
REFERENCES = {"D2": "6.5–6", "D3": "6.7–8", "D4": "6.9", "D7": "6.10–11", "D9": "6.12", "D10": "6.13–14",
              "D12": "6.15", "D16": "6.16", "D20": "6.17–21", "D24": "6.22–23", "D27": "6.24–26",
              "D30": "6.27–28", "D40": "6.29–30", "D45": "6.31–32", "D60": "6.33–41"}
COMPOSITES = {"D81": ("D9", "D9"), "D108": ("D9", "D12"), "D144": ("D12", "D12")}


@dataclass(frozen=True)
class AmsaRuler:
    part: int
    divisions: int
    start_degree: float
    end_degree: float
    deity: str | None
    reference: str
    status: str = "defined"


def amsa_ruler(longitude: float, code: str) -> AmsaRuler:
    spec = next((entry for entry in VARGA_REGISTRY if entry.code == code), None)
    if spec is None:
        raise ValueError(f"Unknown divisional chart: {code}")
    longitude %= 360
    sign = sign_for_longitude(longitude)
    sign_index = SIGNS_IN_ORDER.index(sign)
    odd = sign_index % 2 == 0
    part = _part_index(longitude, spec.divisions)
    start, end = part * 30 / spec.divisions, (part + 1) * 30 / spec.divisions
    reference = "BPHS " + REFERENCES[code] if code in REFERENCES else ""
    deity: str | None = None
    status = "defined"
    if code == "D1":
        status = "not_applicable"  # A whole Rasi, not an amsa subdivision.
    elif code == "D2":
        deity = ("Surya (Sun)", "Chandra (Moon)")[part if odd else 1 - part]
    elif code == "D9":
        orders = (("Deva", "Manushya", "Rakshasa"), ("Manushya", "Rakshasa", "Deva"),
                  ("Rakshasa", "Manushya", "Deva"))
        deity = orders[sign_index % 3][part % 3]
    elif code == "D20":
        deity = (D20_ODD if odd else D20_EVEN)[part]
    elif code == "D30":
        # Keep the app's established unequal boundaries. The even order
        # reverses the planetary spans AND their associated deities.
        bounds = (0, 5, 10, 18, 25, 30) if odd else (0, 5, 12, 20, 25, 30)
        degree = degree_in_sign(longitude)
        part = next((i for i in range(5) if degree + 1e-9 < bounds[i + 1]), 4)
        start, end = bounds[part], bounds[part + 1]
        sequence: tuple[str, ...] = ("Agni", "Vayu", "Indra", "Kubera", "Varuna")
        deity = (sequence if odd else sequence[::-1])[part]
    elif code == "D45":
        deity = (("Brahma", "Shiva", "Vishnu"), ("Shiva", "Vishnu", "Brahma"),
                 ("Vishnu", "Brahma", "Shiva"))[sign_index % 3][part % 3]
    elif code in COMPOSITES:
        first, second = COMPOSITES[code]
        first_spec = next(entry for entry in VARGA_REGISTRY if entry.code == first)
        second_spec = next(entry for entry in VARGA_REGISTRY if entry.code == second)
        assert first_spec.sign_fn is not None
        # Use the same integer partitions as the composite sign map. Carry
        # a point inside the second-stage span, avoiding float-boundary drift.
        _, second_part = divmod(part, second_spec.divisions)
        intermediate = SIGNS_IN_ORDER.index(first_spec.sign_fn(longitude)) * 30 + (second_part + .5) * 30 / second_spec.divisions
        first_ruler, second_ruler = amsa_ruler(longitude, first), amsa_ruler(intermediate, second)
        deity = f"{first}: {first_ruler.deity} → {second}: {second_ruler.deity}"
        reference = f"Component rules: {first_ruler.reference}; {second_ruler.reference}"
        status = "composite"
    elif code in SEQUENCES:
        sequence = SEQUENCES[code]
        if code in REVERSED_EVEN and not odd:
            sequence = sequence[::-1]
        deity = sequence[part % len(sequence)]
    else:
        status = "unconfirmed"  # D5, D6, D8 and D11 are outside this chapter.
    return AmsaRuler(part + 1, 5 if code == "D30" else spec.divisions, start, end, deity, reference, status)


def chart_amsa_rulers(chart: KundaliChart, code: str) -> dict[str, object]:
    rows = []
    for name, longitude in [("Ascendant", chart.ascendant.longitude)] + [(p.planet.value, p.longitude) for p in chart.planets]:
        result = amsa_ruler(longitude, code)
        rows.append({"body": name, "sign": sign_for_longitude(longitude).value, "degree": degree_in_sign(longitude),
                     "part": result.part, "divisions": result.divisions, "start": result.start_degree, "end": result.end_degree,
                     "deity": result.deity, "reference": result.reference, "status": result.status})
    status = rows[0]["status"]
    note = ("D1 is the natal Rasi; a separate amsa deity is not assigned in this rule set." if status == "not_applicable" else
            "A traditional deity sequence for this supplementary division is not confirmed in the selected source." if status == "unconfirmed" else
            "Component designations follow the chart's two-stage calculation. They are not an independently attested deity sequence for this composite division." if status == "composite" else
            "Names follow the natal sign's subdivision. D7 uses traditional substance names; D9 uses Deva / Manushya / Rakshasa designations." if code in ("D7", "D9") else
            "Deities are calculated from natal D1 degrees; reversing deity names does not reverse divisional chart signs.")
    return {"rows": rows, "note": note, "source_url": SOURCE_URL}
