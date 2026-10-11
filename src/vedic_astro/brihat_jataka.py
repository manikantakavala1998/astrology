"""Brihat Jataka worksheets, explicitly scoped to Aiyar's 1905 edition.

References below are chapter.stanza, including the translator's notes where
stated. No BPHS Shadbala score or Vimshottari period is relabelled here.
Power-dependent choices use an explicit, editable order rather than a made-up
aggregate strength score. The complete edition is separately available offline.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from fractions import Fraction
from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from vedic_astro.ashtakavarga import bhinnashtakavarga
from vedic_astro.brihat_predictions import build_predictions
from vedic_astro.dignity import DEBILITATION_SIGN, DEEP_DIGNITY_DEGREE, EXALTATION_SIGN
from vedic_astro.divisional_charts import VARGA_REGISTRY
from vedic_astro.ephemeris import house_cusps, sunrise_sunset
from vedic_astro.models import HouseSystem, KundaliChart, Planet, PlanetPosition, SIGNS_IN_ORDER, Sign
from vedic_astro.planetary_relations import natural_relation, panchadha_relation
from vedic_astro.rashi_bhava import RASHI_LORD, house_from_cusps, whole_sign_house

CLASSICAL = list(Planet)[:7]
LAGNA = "Lagna"
NATURAL_ORDER = [p.value for p in [Planet.SUN, Planet.MOON, Planet.VENUS, Planet.JUPITER,
                                 Planet.MERCURY, Planet.MARS, Planet.SATURN]] + [LAGNA]
MAX_YEARS = dict(zip(CLASSICAL, [19, 25, 15, 12, 15, 21, 20]))
MOOLATRIKONA = dict(zip(CLASSICAL, [Sign.LEO, Sign.TAURUS, Sign.ARIES, Sign.VIRGO,
                                    Sign.SAGITTARIUS, Sign.LIBRA, Sign.AQUARIUS]))
NATURAL_DASHA = [(Planet.MOON, 1), (Planet.MARS, 2), (Planet.MERCURY, 9),
                (Planet.VENUS, 20), (Planet.JUPITER, 18), (Planet.SUN, 20), (Planet.SATURN, 50)]


def varga_sign(longitude: float, code: str) -> Sign:
    spec = next(s for s in VARGA_REGISTRY if s.code == code)
    assert spec.sign_fn is not None
    return spec.sign_fn(longitude)


class DashaOptions(BaseModel):
    model: Literal["pinda", "amsa"] = "amsa"
    seed: Literal["Sun", "Moon", "Lagna"] = "Lagna"
    priority: list[str] = Field(default_factory=lambda: NATURAL_ORDER.copy())
    lagna_years: Literal["navamsas", "signs"] = "navamsas"
    vakra_exemption: Literal["retrograde", "mars"] = "retrograde"
    krurodaya: Literal["zodiac", "rising_sign"] = "zodiac"

    @model_validator(mode="after")
    def check_priority(self) -> DashaOptions:
        if len(self.priority) != 8 or set(self.priority) != set(NATURAL_ORDER):
            raise ValueError("Strength order must contain the seven classical planets and Lagna exactly once.")
        return self


@lru_cache(maxsize=1)
def book_source() -> dict[str, Any]:
    source: dict[str, Any] = json.loads((Path(__file__).parent / "data/brihat_jataka_1905.json").read_text(encoding="utf-8"))
    return source


def angular_distance(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def exaltation_longitude(planet: Planet) -> float:
    return SIGNS_IN_ORDER.index(EXALTATION_SIGN[planet]) * 30 + DEEP_DIGNITY_DEGREE[planet]


def pinda_base(planet: Planet, longitude: float) -> float:
    """VII.1–2: max at exaltation, half at debilitation; linear between."""
    return MAX_YEARS[planet] * (1 - angular_distance(longitude, exaltation_longitude(planet)) / 360)


def amsa_base(longitude: float) -> float:
    """VII.10: minutes / 200, remainder on division by twelve."""
    return (longitude * 0.3) % 12


def amsa_multiplier(pos: PlanetPosition) -> int:
    """VII.11,13: take the largest applicable multiplier, once."""
    if pos.sign == EXALTATION_SIGN[pos.planet] or pos.retrograde:
        return 3
    d9 = varga_sign(pos.longitude, "D9")
    d3 = varga_sign(pos.longitude, "D3")
    if d9 == pos.sign or any(RASHI_LORD[s] == pos.planet for s in (pos.sign, d9, d3)):
        return 2
    return 1


def combustion(pos: PlanetPosition, sun_longitude: float) -> bool | None:
    """VII.2 note f. Venus retrograde threshold is illegible in this OCR.

    Return unknown there; Venus is exempt from the Ayurdaya reduction anyway.
    """
    if pos.planet == Planet.SUN:
        return False
    if pos.planet == Planet.VENUS and pos.retrograde:
        return None
    limits = {Planet.MOON: 12, Planet.MARS: 17, Planet.MERCURY: 12 if pos.retrograde else 14,
              Planet.JUPITER: 11, Planet.VENUS: 10, Planet.SATURN: 15}
    return angular_distance(pos.longitude, sun_longitude) < limits[pos.planet]


def benefic_set(planets: list[PlanetPosition]) -> set[Planet]:
    """II.5: waning Moon and Mercury with malefics change classification."""
    by = {p.planet: p for p in planets}
    good = {Planet.JUPITER, Planet.VENUS}
    if (by[Planet.MOON].longitude - by[Planet.SUN].longitude) % 360 < 180:
        good.add(Planet.MOON)
    bad = set(CLASSICAL) - good - {Planet.MERCURY}
    if not any(by[p].sign == by[Planet.MERCURY].sign for p in bad):
        good.add(Planet.MERCURY)
    return good


def aspect_fraction(source: PlanetPosition, target_longitude: float) -> float:
    """II.13 notes: ±15° bands about the specified aspect middle points."""
    angle = (target_longitude - source.longitude) % 360
    bands = {60: .25, 270: .25, 120: .5, 240: .5, 90: .75, 210: .75, 180: 1.0}
    for degree in ({Planet.SATURN: (60, 270), Planet.JUPITER: (120, 240),
                    Planet.MARS: (90, 210)}.get(source.planet, ())):
        bands[degree] = 1.0
    return max((power for degree, power in bands.items() if angular_distance(angle, degree) < 15), default=0.0)


def period_quality(pos: PlanetPosition) -> str:
    """VIII.5–7: positional conditions, without assuming 'powerful/weak'."""
    distance = (pos.longitude - exaltation_longitude(pos.planet)) % 360
    d9 = varga_sign(pos.longitude, "D9")
    relation = natural_relation(pos.planet, RASHI_LORD[d9])
    if angular_distance(pos.longitude, exaltation_longitude(pos.planet)) < 1e-8:
        return "At deep exaltation; Sampurna if powerful"
    if abs(distance - 180) < 1e-8:
        return "Anishta" if relation == "enemy" else "At deep debilitation; Rikta if weak"
    adverse_d9 = relation == "enemy" or d9 == DEBILITATION_SIGN[pos.planet]
    good_d1 = (pos.sign in (EXALTATION_SIGN[pos.planet], MOOLATRIKONA[pos.planet])
               or RASHI_LORD[pos.sign] == pos.planet or natural_relation(pos.planet, RASHI_LORD[pos.sign]) == "friend")
    if good_d1 and adverse_d9:
        return "Misraphala (mixed)"
    if distance < 180:
        return "Madhyama" if relation == "friend" or d9 == EXALTATION_SIGN[pos.planet] else "Avarohini"
    return "Adhama" if adverse_d9 else "Arohini"


def lagna_quality(longitude: float) -> str:
    mode = int(longitude // 30) % 3
    part = min(2, int(longitude % 30 // 10))
    return [
        ["Uttama", "Madhyama", "Adhama"],
        ["Adhama", "Uttama", "Madhyama"],
        ["Adhama", "Madhyama", "Uttama"],
    ][mode][part]


def ayurdaya_worksheet(planets: list[PlanetPosition], asc_longitude: float,
                       options: DashaOptions) -> dict[str, Any]:
    """VII.1–4,10–13. All reductions exposed for audit, in Savana years.

    Whole-sign counting implements the 'rising sign' wording of VII.3.
    For co-sign planets the user's explicit power order selects one winner.
    """
    bodies = [p for p in planets if p.planet in CLASSICAL]
    by = {p.planet: p for p in bodies}
    asc_sign = SIGNS_IN_ORDER[int(asc_longitude // 30)]
    ranks = {name: i for i, name in enumerate(options.priority)}
    good = benefic_set(bodies)
    strongest = {sign: min((p for p in bodies if p.sign == sign),
                           key=lambda p: ranks[p.planet.value], default=None) for sign in SIGNS_IN_ORDER}
    rows: list[dict[str, Any]] = []
    for pos in bodies:
        base = pinda_base(pos.planet, pos.longitude) if options.model == "pinda" else amsa_base(pos.longitude)
        mult = 1 if options.model == "pinda" else amsa_multiplier(pos)
        exempt = pos.retrograde if options.vakra_exemption == "retrograde" else pos.planet == Planet.MARS
        enemy_loss = Fraction(1, 3) if natural_relation(pos.planet, RASHI_LORD[pos.sign]) == "enemy" and not exempt else Fraction(0)
        is_combust = combustion(pos, by[Planet.SUN].longitude)
        combust_loss = Fraction(1, 2) if is_combust and pos.planet not in (Planet.VENUS, Planet.SATURN) else Fraction(0)
        house = whole_sign_house(pos.sign, asc_sign)
        chakra_loss = Fraction(0)
        if house >= 7 and strongest[pos.sign] == pos:
            chakra_loss = Fraction(1, 13 - house) / (2 if pos.planet in good else 1)
        retained = base * mult * float(1 - max(enemy_loss, combust_loss)) * float(1 - chakra_loss)
        rows.append({"lord": pos.planet.value, "house": house, "base": base, "multiplier": mult,
                     "enemy_loss": str(enemy_loss), "combust_loss": str(combust_loss),
                     "chakra_loss": str(chakra_loss), "years": retained,
                     "quality": period_quality(pos), "longitude": pos.longitude,
                     "calculation_steps": [
                         f"Birth position: {pos.sign.value} {pos.degree_in_sign:.4f}°; full zodiac longitude {pos.longitude:.4f}°.",
                         (f"Amsa base: ({pos.longitude:.4f} × 0.3) remainder 12 = {base:.4f} years."
                          if options.model == "amsa" else
                          f"Pinda base: {MAX_YEARS[pos.planet]} × (1 − {angular_distance(pos.longitude, exaltation_longitude(pos.planet)):.4f} / 360) = {base:.4f} years; the angle is measured from deep exaltation."),
                         f"Multiplier: ×{mult}. " + ("Exalted sign or retrograde motion." if mult == 3 else
                             "Own sign in D1/D3/D9, or the same D1 and D9 sign." if mult == 2 else "No increase applies."),
                         f"Enemy-sign reduction: {enemy_loss}; near-Sun reduction: {combust_loss}. Use the larger: {max(enemy_loss, combust_loss)}.",
                         f"House-position reduction: {chakra_loss}; natal whole-sign house {house}.",
                         f"Years after these reductions: {base:.4f} × {mult} × (1 − {max(enemy_loss, combust_loss)}) × (1 − {chakra_loss}) = {retained:.4f}.",
                     ]})
    lagna_base = (asc_longitude / 30 if options.lagna_years == "signs" else
                  asc_longitude % 30 * .3 if options.model == "pinda" else amsa_base(asc_longitude))
    rows.append({"lord": LAGNA, "house": 1, "base": lagna_base, "multiplier": 1,
                 "enemy_loss": "0", "combust_loss": "0", "chakra_loss": "0",
                 "years": lagna_base, "quality": lagna_quality(asc_longitude), "longitude": asc_longitude,
                 "calculation_steps": [
                     f"Ascendant position: {asc_sign.value} {asc_longitude % 30:.4f}°; full longitude {asc_longitude:.4f}°.",
                     (f"Signs-passed option: {asc_longitude:.4f} / 30 = {lagna_base:.4f} years."
                      if options.lagna_years == "signs" else
                      f"Navamsas-passed option: {asc_longitude % 30:.4f} × 0.3 = {lagna_base:.4f} years."
                      if options.model == "pinda" else
                      f"Amsa option: ({asc_longitude:.4f} × 0.3) remainder 12 = {lagna_base:.4f} years."),
                     "No planetary multiplier or enemy, near-Sun or house-position reduction applies to the Ascendant.",
                 ]})
    loss = 0.0
    rising = [p for p in bodies if p.sign == asc_sign]
    nearest = min(rising, key=lambda p: angular_distance(p.longitude, asc_longitude), default=None)
    if options.model == "pinda" and nearest and nearest.planet in (Planet.SUN, Planet.MARS, Planet.SATURN):
        loss = (asc_longitude if options.krurodaya == "zodiac" else asc_longitude % 30) / 360
        if any(p.planet in good and aspect_fraction(p, nearest.longitude) > 0 for p in bodies if p != nearest):
            loss /= 2
    # The text reduces the combined total. Proportional allocation to each
    # participant for the timeline is an explicit app convention, not a verse.
    for row in rows:
        row["final_years"] = row["years"] * (1 - loss)
        row["calculation_steps"].append(f"Final years: {row['years']:.4f} × (1 − {loss:.6f}) = {row['final_years']:.4f}. "
                                       "Any final Ascendant-related reduction is allocated proportionally across periods.")
    return {"rows": rows, "krurodaya_loss": loss, "total": sum(r["final_years"] for r in rows),
            "reference": "VII.1–4,10–13", "options": options.model_dump()}


def antardasha_weights(owner: str, signs: dict[str, Sign], priority: list[str]) -> list[tuple[str, Fraction]]:
    """VIII.3–4: strongest body in each qualifying house, normalized later."""
    weights = [(owner, Fraction(1))]
    for house, fraction in [(1, Fraction(1, 2)), (5, Fraction(1, 3)), (9, Fraction(1, 3)),
                            (7, Fraction(1, 7)), (4, Fraction(1, 4)), (8, Fraction(1, 4))]:
        candidates = [name for name in priority if name not in (owner, LAGNA) and whole_sign_house(signs[name], signs[owner]) == house]
        if candidates:
            weights.append((candidates[0], fraction))
    return weights


def dasha_timeline(planets: list[PlanetPosition], asc_longitude: float, start: datetime,
                   options: DashaOptions) -> dict[str, Any]:
    worksheet = ayurdaya_worksheet(planets, asc_longitude, options)
    signs = {p.planet.value: p.sign for p in planets if p.planet in CLASSICAL}
    signs[LAGNA] = SIGNS_IN_ORDER[int(asc_longitude // 30)]
    ranks = {name: i for i, name in enumerate(options.priority)}
    def category(name: str) -> int:
        house = whole_sign_house(signs[name], signs[options.seed])
        return 0 if house in (1, 4, 7, 10) else 1 if house in (2, 5, 8, 11) else 2
    order = [options.seed] + sorted((n for n in options.priority if n != options.seed), key=lambda n: (category(n), ranks[n]))
    years = {row["lord"]: row["final_years"] for row in worksheet["rows"]}
    qualities = {row["lord"]: row["quality"] for row in worksheet["rows"]}
    periods = []
    cursor = start
    for lord in order:
        end = cursor + timedelta(days=years[lord] * 360)
        weights = antardasha_weights(lord, signs, options.priority)
        total_weight = sum((w for _, w in weights), Fraction(0))
        sub = []
        sub_start = cursor
        cumulative = Fraction(0)
        for index, (name, weight) in enumerate(weights):
            cumulative += weight
            sub_end = end if index == len(weights) - 1 else cursor + (end - cursor) * float(cumulative / total_weight)
            sub.append({"lord": name, "start": sub_start.isoformat(), "end": sub_end.isoformat(),
                        "weight": str(weight), "share": str(weight / total_weight)})
            sub_start = sub_end
        periods.append({"lord": lord, "years": years[lord], "start": cursor.isoformat(), "end": end.isoformat(),
                        "quality": qualities[lord], "sub_periods": sub})
        cursor = end
    return {"worksheet": worksheet, "periods": periods,
            "conventions": "360 civil days per Savana year; signs for VIII.1–4; explicit power order. Lagna is a subperiod owner only within its own dasha. Krurodaya reduces the total; proportional allocation among periods is an app convention. Reappearance ties are resolved by your order."}


def brihat_bhavas(chart: KundaliChart) -> dict[Planet, int]:
    """XII.6 commentary: quadrant trisection middle points, bisected boundaries."""
    b = chart.birth_data
    centers = house_cusps(b.utc_datetime, b.latitude, b.longitude, b.ayanamsha, HouseSystem.PORPHYRY)
    boundaries = [(centers[i-1] + ((centers[i] - centers[i-1]) % 360) / 2) % 360 for i in range(12)]
    return {p.planet: house_from_cusps(p.longitude, boundaries) for p in chart.planets if p.planet in CLASSICAL}


def planetary_strengths(chart: KundaliChart) -> list[dict[str, Any]]:
    by = {p.planet: p for p in chart.planets}
    good = benefic_set(chart.planets)
    bhavas = brihat_bhavas(chart)
    b = chart.birth_data
    rise, setting, _ = sunrise_sunset(b.utc_datetime, b.latitude, b.longitude)
    is_day = rise <= b.utc_datetime < setting
    preferred = {Planet.MERCURY: 1, Planet.JUPITER: 1, Planet.SUN: 10, Planet.MARS: 10,
                 Planet.SATURN: 7, Planet.MOON: 4, Planet.VENUS: 4}
    day_planets = {Planet.SUN, Planet.JUPITER, Planet.VENUS}
    result = []
    for planet in CLASSICAL:
        p = by[planet]
        d9 = varga_sign(p.longitude, "D9")
        lord = RASHI_LORD[p.sign]
        relation = natural_relation(planet, lord)
        sthana_checks = [
            {"label": text, "supported": condition}
            for condition, text in [(p.sign == EXALTATION_SIGN[planet], "Exalted sign"),
                                    (p.sign == MOOLATRIKONA[planet], "Moolatrikona sign"),
                                    (lord == planet, "Own sign"), (relation == "friend", "Friendly sign"),
                                    (RASHI_LORD[d9] == planet, "Own navamsa")]
        ]
        sthana = [check["label"] for check in sthana_checks if check["supported"]]
        # Chesta includes other phenomena requiring brightness/war criteria;
        # these two exactly specified conditions are evaluated and named.
        chesta_supported = p.sign in SIGNS_IN_ORDER[9:] + SIGNS_IN_ORDER[:3] if planet in (Planet.SUN, Planet.MOON) else p.retrograde
        chesta = ("Capricorn–Gemini" if chesta_supported else "—") if planet in (Planet.SUN, Planet.MOON) else ("Retrograde" if chesta_supported else "No retrograde support")
        combust = combustion(p, by[Planet.SUN].longitude)
        state = "Debilitated" if p.sign == DEBILITATION_SIGN[planet] else "Exalted" if p.sign == EXALTATION_SIGN[planet] else "Moolatrikona" if p.sign == MOOLATRIKONA[planet] else "Own" if lord == planet else relation.title()
        fractions = {"Exalted": ("1", "0"), "Moolatrikona": ("3/4", "<1/4"), "Own": ("1/2", "1/4"),
                     "Friend": ("1/4", "1/2"), "Enemy": ("<1/4", "3/4"), "Debilitated": ("0", "1")}
        effects = ("0", "1") if combust else fractions.get(state, ("Not quantified", "Not quantified"))
        result.append({"planet": planet.value, "sign": p.sign.value, "navamsa": d9.value,
                       "nature": "Benefic" if planet in good else "Malefic", "sthana": sthana,
                       "sthana_checks": sthana_checks, "chesta_supported": chesta_supported,
                       "dig": bhavas[planet] == preferred[planet], "dig_house": preferred[planet],
                       "bhava": bhavas[planet], "chesta": chesta,
                       "kala": planet == Planet.MERCURY or ((planet in day_planets) == is_day),
                       "paksha": (planet in good) == ((by[Planet.MOON].longitude - by[Planet.SUN].longitude) % 360 < 180),
                       "combust": combust, "dignity": state, "good_fraction": effects[0], "bad_fraction": effects[1],
                       "natural_rank": NATURAL_ORDER.index(planet.value) + 1,
                       "relations": [{"planet": other.value, "relation": panchadha_relation(planet, p.sign, other, by[other].sign)} for other in CLASSICAL]})
    return result


def nabhasa_yogas(planets: list[PlanetPosition], asc_sign: Sign,
                  bhavas: dict[Planet, int]) -> list[dict[str, Any]]:
    """All 32 XII.2–10 forms, seven bodies only; retain supersession metadata."""
    bodies = [p for p in planets if p.planet in CLASSICAL]
    h = set(bhavas.values())
    modes = {SIGNS_IN_ORDER.index(p.sign) % 3 for p in bodies}
    records: list[dict[str, Any]] = []
    def add(name: str, match: bool, rule: str, stanza: int, group: str) -> None:
        records.append({"name": name, "matched": match, "active": match, "condition": rule,
                        "reference": f"XII.{stanza}", "group": group})
    for mode, name in enumerate(["Rajju", "Musala", "Nala"]):
        add(name, modes == {mode}, "All seven planets in " + ["movable", "fixed", "dual"][mode] + " signs", 2, "Asraya")
    benefics = {Planet.MERCURY, Planet.JUPITER, Planet.VENUS}
    malefics = {Planet.SUN, Planet.MARS, Planet.SATURN}
    kendras = {1, 4, 7, 10}
    for name, first, second in [("Srik / Mala", benefics, malefics), ("Sarpa", malefics, benefics)]:
        occupied = {bhavas[p] for p in first}
        add(name, len(occupied) == 3 and occupied <= kendras and all(bhavas[p] not in kendras for p in second),
            "Three kendras occupied by " + ("benefics" if first == benefics else "malefics") + "; opposite group outside kendras", 2, "Dala")
    shapes = [
        ("Gada", [{1,4},{4,7},{7,10},{10,1}], 4), ("Sakata", [{1,7}], 4),
        ("Vihaga", [{4,10}], 4), ("Sringataka", [{1,5,9}], 4),
        ("Hala", [{2,6,10},{3,7,11},{4,8,12}], 4),
        ("Kamala", [{1,4,7,10}], 5), ("Vapi", [{2,5,8,11},{3,6,9,12}], 5),
        ("Yupa", [{1,2,3,4}], 7), ("Ishu / Bana", [{4,5,6,7}], 7),
        ("Sakti", [{7,8,9,10}], 7), ("Danda", [{10,11,12,1}], 7),
        ("Nau", [{1,2,3,4,5,6,7}], 8), ("Kuta", [{4,5,6,7,8,9,10}], 8),
        ("Chhatra", [{7,8,9,10,11,12,1}], 8), ("Chapa", [{10,11,12,1,2,3,4}], 8),
        ("Ardha Chandra", [{(start+i-1)%12+1 for i in range(7)} for start in [2,3,5,6,8,9,11,12]], 8),
        ("Samudra", [{2,4,6,8,10,12}], 9), ("Chakra", [{1,3,5,7,9,11}], 9),
    ]
    for name, patterns, stanza in shapes:
        add(name, any(h == pattern for pattern in patterns), "Seven planets occupy these bhavas: " + " or ".join(",".join(map(str, sorted(p))) for p in patterns), stanza, "Akriti")
    for name, good_h, bad_h in [("Vajra", {1,7}, {4,10}), ("Yava", {4,10}, {1,7})]:
        add(name, all(bhavas[p] in good_h for p in benefics) and all(bhavas[p] in bad_h for p in malefics) and h == kendras,
            f"Benefics in {sorted(good_h)}, malefics in {sorted(bad_h)}, all four kendras occupied", 5, "Akriti")
    distinct = len({p.sign for p in bodies})
    for n, name in enumerate(["Gola", "Yuga", "Sula", "Kedara", "Pasa", "Damini", "Vallaki / Veena"], 1):
        add(name, distinct == n, f"Seven planets occupy {n} distinct signs", 10, "Sankhya")
    higher = any(r["matched"] and r["group"] in ("Akriti", "Dala") for r in records)
    asraya = any(r["matched"] and r["group"] == "Asraya" for r in records)
    for r in records:
        if r["matched"] and ((r["group"] == "Asraya" and (higher or distinct == 1)) or
                             (r["group"] == "Sankhya" and (higher or (asraya and distinct != 1)))):
            r["active"] = False
    assert len(records) == 32
    return records


def lunar_yogas(planets: list[PlanetPosition], asc_sign: Sign) -> list[dict[str, Any]]:
    by = {p.planet: p for p in planets}
    moon = by[Planet.MOON]
    eligible = [by[p] for p in CLASSICAL if p not in (Planet.SUN, Planet.MOON)]
    second = [p.planet.value for p in eligible if whole_sign_house(p.sign, moon.sign) == 2]
    twelfth = [p.planet.value for p in eligible if whole_sign_house(p.sign, moon.sign) == 12]
    cancel = whole_sign_house(moon.sign, asc_sign) in (1,4,7,10) or any(p.sign == moon.sign for p in eligible)
    conditions = [("Sunapha", bool(second), ", ".join(second) or "None in 2nd from Moon", "XIII.3"),
                  ("Anapha", bool(twelfth), ", ".join(twelfth) or "None in 12th from Moon", "XIII.3"),
                  ("Durudhura", bool(second and twelfth), "Both sides of Moon occupied (Sun and nodes excluded)", "XIII.3"),
                  ("Kemadruma — primary condition", not second and not twelfth, "No eligible bodies on either side; commentary cancellation " + ("present" if cancel else "absent"), "XIII.3 notes"),
                  ("Adhi", all(whole_sign_house(by[p].sign, moon.sign) in (6,7,8) for p in [Planet.MERCURY, Planet.JUPITER, Planet.VENUS]), "Mercury, Jupiter and Venus in 6th/7th/8th from Moon; power/combustion qualifiers need review", "XIII.2")]
    return [{"name": name, "matched": matched,
             "active": matched and not (name.startswith("Kemadruma") and cancel),
             "cancellation_present": cancel if name.startswith("Kemadruma") else False,
             "condition": condition, "reference": ref} for name, matched, condition, ref in conditions]


def raja_yogas(planets: list[PlanetPosition], asc_sign: Sign) -> list[dict[str, Any]]:
    s = {p.planet.value: p.sign.value for p in planets if p.planet in CLASSICAL}
    fixtures = [
        (4, ["Aquarius","Aries","Taurus"], {"Saturn":"Aquarius","Sun":"Aries","Moon":"Taurus","Mercury":"Gemini","Jupiter":"Leo","Mars":"Scorpio"}),
        (5, ["Capricorn"], {"Mars":"Capricorn","Sun":"Sagittarius","Moon":"Sagittarius","Saturn":"Capricorn"}),
        (6, ["Taurus"], {"Moon":"Taurus","Sun":"Leo","Jupiter":"Scorpio","Saturn":"Aquarius"}),
        (7, ["Pisces"], {"Moon":"Sagittarius","Jupiter":"Sagittarius","Mars":"Capricorn","Venus":"Pisces"}),
        (7, ["Virgo"], {"Moon":"Sagittarius","Jupiter":"Sagittarius","Mars":"Capricorn","Mercury":"Virgo"}),
        (8, ["Pisces"], {"Moon":"Pisces","Saturn":"Aquarius","Mars":"Capricorn","Sun":"Leo"}),
        (9, ["Cancer"], {"Jupiter":"Cancer","Moon":"Taurus","Venus":"Taurus","Mercury":"Taurus","Sun":"Aries"}),
        (10, ["Capricorn"], {"Saturn":"Capricorn","Mars":"Aries","Moon":"Cancer","Sun":"Leo","Mercury":"Gemini","Venus":"Libra"}),
        (11, ["Virgo"], {"Mercury":"Virgo","Venus":"Gemini","Moon":"Pisces","Jupiter":"Pisces","Mars":"Capricorn","Saturn":"Capricorn"}),
    ]
    return [{"name": f"Raja yoga XI.{verse} ({'/'.join(asc)})", "matched": asc_sign.value in asc and all(s[p] == sign for p, sign in positions.items()),
             "condition": "Lagna " + "/".join(asc) + "; " + ", ".join(f"{p} in {sign}" for p, sign in positions.items()), "reference": f"XI.{verse}"}
            for verse, asc, positions in fixtures]


def avocation(chart: KundaliChart) -> list[dict[str, Any]]:
    by = {p.planet: p for p in chart.planets}
    themes = dict(zip(CLASSICAL, ["Perfumes, gold, wool, medicine", "Agriculture, water products, women",
        "Metals, minerals, fire, weapons", "Writing, accounts, crafts", "Learning, religious service, mines, charity",
        "Gems, silver, metals, cattle", "Labour, carrying burdens"]))
    rows = []
    for label, sign in [(LAGNA, chart.ascendant.sign), ("Moon", by[Planet.MOON].sign), ("Sun", by[Planet.SUN].sign)]:
        tenth = SIGNS_IN_ORDER[(SIGNS_IN_ORDER.index(sign) + 9) % 12]
        lord = RASHI_LORD[tenth]
        navamsa = varga_sign(by[lord].longitude, "D9")
        career_lord = RASHI_LORD[navamsa]
        rows.append({"base": label, "tenth": tenth.value, "lord": lord.value, "navamsa": navamsa.value,
                     "career_lord": career_lord.value, "themes": themes[career_lord], "reference": "X.1–3"})
    return rows


def build_brihat_report(chart: KundaliChart) -> dict[str, Any]:
    by = {p.planet: p for p in chart.planets}
    strengths = planetary_strengths(chart)
    aspects = [{"source": p.planet.value, "target": q.planet.value, "fraction": str(Fraction(aspect_fraction(p, q.longitude))), "reference": "II.13"}
               for p in chart.planets if p.planet in CLASSICAL for q in chart.planets
               if q.planet in CLASSICAL and q != p and aspect_fraction(p, q.longitude)]
    combinations = [{"planets": [a.value, b.value], "sign": by[a].sign.value,
                     "reference": "XIV." + str(1 if a == Planet.SUN else 2 if a == Planet.MOON else 3 if a == Planet.MARS else 5 if a == Planet.VENUS else 4)}
                    for i, a in enumerate(CLASSICAL) for b in CLASSICAL[i+1:] if by[a].sign == by[b].sign]
    bv = {p: bhinnashtakavarga(chart.planets, chart.ascendant.sign, p) for p in CLASSICAL}
    ashtaka = [{"planet": p.value, "sign": by[p].sign.value, "bindus": bv[p][by[p].sign],
               "reading": "Supportive" if bv[p][by[p].sign] > 4 else "Challenging" if bv[p][by[p].sign] < 4 else "Mixed",
               "scores": [bv[p][s] for s in SIGNS_IN_ORDER]} for p in CLASSICAL]
    cursor = chart.birth_data.local_datetime
    natural = []
    for planet, years in NATURAL_DASHA:
        end = cursor + timedelta(days=years * 360)
        natural.append({"lord": planet.value, "years": years, "start": cursor.isoformat(), "end": end.isoformat()})
        cursor = end
    own_counts = {"own": sum(RASHI_LORD[p.sign] == p.planet for p in chart.planets if p.planet in CLASSICAL),
                  "exalted": sum(p.sign == EXALTATION_SIGN[p.planet] for p in chart.planets if p.planet in CLASSICAL)}
    placements = [{"planet": p.value, "sign": by[p].sign.value, "house": next(row["bhava"] for row in strengths if row["planet"] == p.value),
                   "d9": varga_sign(by[p].longitude, "D9").value, "d3": varga_sign(by[p].longitude, "D3").value,
                   "d30": varga_sign(by[p].longitude, "D30").value,
                   "drekkana_verse": SIGNS_IN_ORDER.index(by[p].sign)*3 + int(by[p].degree_in_sign//10)+1} for p in CLASSICAL]
    report = {"strengths": strengths, "aspects": aspects, "lunar": lunar_yogas(chart.planets, chart.ascendant.sign),
            "nabhasa": nabhasa_yogas(chart.planets, chart.ascendant.sign, brihat_bhavas(chart)),
            "raja": raja_yogas(chart.planets, chart.ascendant.sign), "conjunctions": combinations,
            "career": avocation(chart), "ashtakavarga": ashtaka, "natural_dasha": natural,
            "placements": placements, "own_counts": own_counts, "moon_nakshatra": by[Planet.MOON].nakshatra.model_dump(),
            "moon_sign": by[Planet.MOON].sign.value,
            "lagna_drekkana_verse": SIGNS_IN_ORDER.index(chart.ascendant.sign)*3 + int(chart.ascendant.degree_in_sign//10)+1,
            "dasha": dasha_timeline(chart.planets, chart.ascendant.longitude, chart.birth_data.local_datetime, DashaOptions())}
    report["predictions"] = build_predictions(chart, report)
    return report
