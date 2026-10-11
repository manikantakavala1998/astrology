"""Year explorer data. Method rules and Vimshottari timing stay independent.

House labels in these sign-based techniques always refer to D1 whole-sign
houses, including when another house system is selected for the birth chart.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from vedic_astro.aspects import ASPECT_OFFSETS
from vedic_astro.bcp import compute_bhrigu_chakra, compute_bcp_longevity
from vedic_astro.bsp import (
    compute_bsp_rules, compute_bsp_house_notes, compute_bsp_aries_spoilt,
    compute_bsp_venus_reveals,
)
from vedic_astro.dasha import compute_vimshottari_dasha, DAYS_PER_YEAR, DASHA_YEARS
from vedic_astro.divisional_charts import dwadasamsa_sign
from vedic_astro.models import KundaliChart, Planet, Sign, SIGNS_IN_ORDER
from vedic_astro.padma_chakra import compute_badhaka, compute_padma_chakra_years
from vedic_astro.rashi_bhava import RASHI_LORD


def anniversary(birth: datetime, completed: int) -> datetime:
    """Feb 29 anniversaries fall on Feb 28 in non-leap years, at birth time."""
    try:
        return birth.replace(year=birth.year + completed)
    except ValueError:
        return birth.replace(year=birth.year + completed, day=28)


def build_bhrigu_report(chart: KundaliChart) -> dict[str, Any]:
    asc = chart.ascendant.sign
    asc_index = SIGNS_IN_ORDER.index(asc)
    birth = chart.birth_data.local_datetime

    def house(sign: Sign) -> int:
        return (SIGNS_IN_ORDER.index(sign) - asc_index) % 12 + 1

    planets = [p.model_copy(update={"house": house(p.sign)}) for p in chart.planets]
    positions = {p.planet: p for p in planets}

    def target(offset: int, planet: Planet, role: str) -> dict[str, Any]:
        sign = SIGNS_IN_ORDER[(SIGNS_IN_ORDER.index(positions[planet].sign) + offset - 1) % 12]
        return {"offset": offset, "house": house(sign), "sign": sign.value, "role": role,
                "planets": [p.planet.value for p in planets if p.sign == sign]}

    bcp = []
    for row in compute_bhrigu_chakra(asc, planets):
        item = row.model_dump(mode="json")
        item.update(start=anniversary(birth, row.age - 1).isoformat(),
                    end=anniversary(birth, row.age).isoformat(),
                    year_lord=RASHI_LORD[row.sign_from_lagna].value,
                    cycle_sign_lord=RASHI_LORD[row.sign_from_cycle_ruler].value if row.sign_from_cycle_ruler else None,
                    cycle_d1_house=house(row.sign_from_cycle_ruler) if row.sign_from_cycle_ruler else None)
        bcp.append(item)

    bsp = []
    for row in compute_bsp_rules(asc, planets, [], require_special_status=False):
        targets = [target(row.house_offset, row.planet, "Primary activation")]
        if row.rule_number == 10:
            targets.append(target(1, row.planet, "Occupied-house activation"))
        if row.rule_number == 11:
            targets.extend([target(1, row.planet, "Occasional activation"),
                            target(7, row.planet, "Controlling influence")])
        bsp.append({**row.model_dump(mode="json"), "targets": targets})

    d12_asc = dwadasamsa_sign(chart.ascendant.longitude)
    connections = []
    badhakas = []
    for code, base in (("D1", asc), ("D12", d12_asc)):
        badhaka = compute_badhaka(base)
        badhakas.append({**badhaka.model_dump(mode="json"), "chart": code,
                         "d1_house": house(badhaka.badhaka_sign)})
        connections.append({"sign": badhaka.badhaka_sign.value, "house": house(badhaka.badhaka_sign),
                            "kind": "Direct Badhaka sign", "reason": f"{code} {badhaka.modality} ascendant: house {badhaka.badhaka_house_from_lagna}",
                            "planet": badhaka.badhakesh.value})
        lord = positions[badhaka.badhakesh]
        for placement, sign in (("D1", lord.sign), ("D12", dwadasamsa_sign(lord.longitude))):
            connections.append({"sign": sign.value, "house": house(sign), "kind": "Badhakesh placement",
                                "reason": f"{code} Badhakesh {lord.planet.value} in {placement}; mapped to D1",
                                "planet": lord.planet.value})

    padma = [row.model_dump(mode="json") for row in compute_padma_chakra_years(
        asc, chart.ascendant.longitude, planets, birth)]
    aspects = []
    for p in planets:
        for offset in ASPECT_OFFSETS.get(p.planet, []):
            aspects.append({"planet": p.planet.value, "source_sign": p.sign.value, "source_house": p.house,
                            **target(offset, p.planet, "Graha drishti")})

    timeline = compute_vimshottari_dasha(positions[Planet.MOON].longitude, birth,
                                         until=anniversary(birth, 120))
    return {"bcp": bcp, "bsp": bsp, "padma": padma,
            "permanent": [row.model_dump(mode="json") for row in compute_bsp_house_notes(asc, planets)],
            "aries": (row.model_dump(mode="json") if (row := compute_bsp_aries_spoilt(asc, planets)) else None),
            "venus": compute_bsp_venus_reveals(asc, planets).model_dump(mode="json"),
            "longevity": compute_bcp_longevity(asc, planets).model_dump(mode="json"),
            "badhakas": badhakas, "badhaka_connections": connections, "aspects": aspects,
            "planets": [p.model_dump(mode="json") for p in planets],
            "vimshottari": timeline.model_dump(mode="json"),
            "dasha_year_days": DAYS_PER_YEAR,
            "dasha_years": {p.value: y for p, y in DASHA_YEARS.items()},
            "padma_year_rule": "Calendar anniversary minus 5 days per completed year, plus 5 hours per year rounded to whole days; split drift into 30-day months and remaining days before subtraction. This is an approximate calendar convention, not an exact 360-day interval.",
            "coverage": "BSP 1, 2, 5, 6, 8, 9, 10, 11, 13, 14 and 15 are included. Rules 3/4, 7/12 and later extensions remain outside the verified calculation set."}
