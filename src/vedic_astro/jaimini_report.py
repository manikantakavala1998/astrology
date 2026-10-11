"""Auditable Jaimini worksheets. All results derive from a natal chart.

No ephemeris calls in the combinatorial rules. Astronomical special lagnas
are calculated once from the most recent local sunrise. See docs/jaimini.md.
"""
from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Any

from vedic_astro.aspects import SIGN_MODALITY, sign_aspects
from vedic_astro.dignity import DEBILITATION_SIGN, EXALTATION_SIGN, planet_dignity
from vedic_astro.ephemeris import planet_positions, sunrise_sunset
from vedic_astro.jaimini import _sign_duration_years, compute_chara_karakas, step
from vedic_astro.models import KundaliChart, Planet, PlanetPosition, Sign, SIGNS_IN_ORDER
from vedic_astro.rashi_bhava import RASHI_LORD, sign_for_longitude, whole_sign_house
from vedic_astro.varga import navamsa_sign
from vedic_astro.planetary_relations import NATURAL_ENEMIES

Row = dict[str, Any]
CLASSICAL = tuple(list(Planet)[:7])
NATURAL_RANK = {"movable": 0, "fixed": 1, "dual": 2}
KARAKA_INFO = {
    "Atmakaraka": ("AK", "Self & direction"), "Amatyakaraka": ("AmK", "Work & advisors"),
    "Bhratrikaraka": ("BK", "Siblings"), "Matrikaraka": ("MK", "Mother"),
    "Pitrikaraka": ("PiK", "Father"), "Putrikaraka": ("PuK", "Children & followers"),
    "Gnatikaraka": ("GK", "Relatives & obstacles"), "Darakaraka": ("DK", "Spouse"),
}
PADA_NAMES = ["Arudha Lagna", "Dhana Pada", "Bhratri Pada", "Matri Pada", "Putra Pada", "Shatru Pada",
              "Dara Pada", "Randhra Pada", "Bhagya Pada", "Rajya Pada", "Labha Pada", "Upapada Lagna"]
RUDRA_EIGHTH = [Sign.SCORPIO, Sign.GEMINI, Sign.CAPRICORN, Sign.SAGITTARIUS, Sign.CANCER, Sign.AQUARIUS,
                Sign.TAURUS, Sign.SAGITTARIUS, Sign.CANCER, Sign.GEMINI, Sign.CAPRICORN, Sign.LEO]


def advancement(p: PlanetPosition) -> float:
    return 30 - p.degree_in_sign if p.planet in (Planet.RAHU, Planet.KETU) else p.degree_in_sign


def touches(source: Sign, target: Sign) -> bool:
    return source == target or target in sign_aspects(source)


def dignity_rank(p: PlanetPosition) -> int:
    return {"Exalted": 3, "Own Sign": 2, "Debilitated": -1}.get(planet_dignity(p.planet, p.sign).value, 0)


def planet_strength(p: PlanetPosition, planets: list[PlanetPosition]) -> tuple[float, ...]:
    by = {q.planet: q for q in planets}
    companions = sum(q.planet != p.planet and q.sign == p.sign for q in planets)
    support = sum(q in by and touches(by[q].sign, p.sign) for q in (Planet.JUPITER, Planet.MERCURY, RASHI_LORD[p.sign]))
    return (companions, support, int(p.sign == EXALTATION_SIGN.get(p.planet)), NATURAL_RANK[SIGN_MODALITY[p.sign]], advancement(p))


def primary_lord(sign: Sign, planets: list[PlanetPosition], for_dasha: bool = False) -> Planet:
    """PVR co-lord hierarchy; an isolated own-sign co-lord yields to the other."""
    classic = RASHI_LORD[sign]
    node = {Sign.SCORPIO: Planet.KETU, Sign.AQUARIUS: Planet.RAHU}.get(sign)
    by = {p.planet: p for p in planets}
    if node is None or node not in by:
        return classic
    a, b = by[classic], by[node]
    if (a.sign == sign) != (b.sign == sign):
        return node if a.sign == sign else classic
    def key(p: PlanetPosition) -> tuple[float, ...]:
        base = planet_strength(p, planets)
        if not for_dasha:
            return base
        correction = 0 if p.sign == sign else 1 if p.sign == EXALTATION_SIGN.get(p.planet) else -1 if p.sign == DEBILITATION_SIGN.get(p.planet) else 0
        return (*base[:4], _sign_duration_years(sign, p.sign) + correction)
    return node if key(b) > key(a) else classic


def sign_strength(sign: Sign, planets: list[PlanetPosition]) -> tuple[float, ...]:
    by = {p.planet: p for p in planets}
    lord = primary_lord(sign, planets)
    support = sum(touches(by[p].sign, sign) for p in (Planet.JUPITER, Planet.MERCURY, lord))
    occupants = [p for p in planets if p.sign == sign]
    return (len(occupants), support, int(any(p.sign == EXALTATION_SIGN.get(p.planet) for p in occupants)),
            int(SIGNS_IN_ORDER.index(sign) % 2 != SIGNS_IN_ORDER.index(by[lord].sign) % 2),
            NATURAL_RANK[SIGN_MODALITY[sign]], advancement(by[lord]))


def stronger_sign(a: Sign, b: Sign, planets: list[PlanetPosition]) -> Sign:
    return b if sign_strength(b, planets) > sign_strength(a, planets) else a


def arudha(sign: Sign, lord_sign: Sign) -> tuple[Sign, int, bool]:
    distance = whole_sign_house(lord_sign, sign)
    raw = step(lord_sign, distance - 1)
    exception = raw in (sign, step(sign, 6))
    return (step(raw, 9) if exception else raw), distance, exception


def arudha_rows(asc: Sign, planets: list[PlanetPosition]) -> list[Row]:
    by = {p.planet: p for p in planets}
    rows = []
    for house in range(1, 13):
        sign = step(asc, house - 1)
        lord = primary_lord(sign, planets)
        result, count, exception = arudha(sign, by[lord].sign)
        rows.append({"house": house, "code": "AL" if house == 1 else "UL" if house == 12 else f"A{house}",
                     "name": PADA_NAMES[house - 1], "sign": result.value, "source_sign": sign.value,
                     "lord": lord.value, "lord_sign": by[lord].sign.value, "count": count, "exception": exception,
                     "calculation": f"{sign.value} → {by[lord].sign.value}: {count} signs; count {count} again from the lord."
                     + (" Result is 1st/7th from the source: move 10th from that result." if exception else " No exception.")})
    return rows


def argala_rows(planets: list[PlanetPosition]) -> list[Row]:
    rows = []
    malefics = {Planet.SUN, Planet.MARS, Planet.SATURN, Planet.RAHU, Planet.KETU}
    for target in SIGNS_IN_ORDER:
        reverse = any(p.planet == Planet.KETU and p.sign == target for p in planets)
        direction = -1 if reverse else 1
        for opening, blocking in ((2, 12), (4, 10), (11, 3), (5, 9)):
            a, b = step(target, direction * (opening - 1)), step(target, direction * (blocking - 1))
            contributors = [p for p in planets if p.sign == a]
            blockers = [p for p in planets if p.sign == b]
            special = blocking == 3 and sum(p.planet in malefics for p in blockers) >= 3
            effective_blockers = [] if special else blockers
            if not contributors:
                status = "No Argala"
            elif len(contributors) > len(effective_blockers):
                status = "Unobstructed"
            elif len(contributors) < len(effective_blockers):
                status = "Obstructed"
            else:
                # Equal counts require a strength judgement; don't turn it into
                # a fabricated numerical score or assume automatic cancellation.
                status = "Equal count — compare strength"
            rows.append({"target": target.value, "argala_house": opening, "argala_sign": a.value,
                         "argala_planets": [p.planet.value for p in contributors], "blocking_house": blocking,
                         "blocking_sign": b.value, "blocking_planets": [p.planet.value for p in blockers],
                         "status": status, "reverse": reverse, "special": special,
                         "calculation": f"{len(contributors)} intervention planets / {len(effective_blockers)} effective blockers."
                         + (" Count backwards because Ketu occupies the target." if reverse else "")
                         + (" Three or more malefics in the 3rd create special Argala rather than obstruction." if special else "")})
    return rows


def special_lagnas(chart: KundaliChart) -> list[Row]:
    birth = chart.birth_data
    rise, _, _ = sunrise_sunset(birth.utc_datetime, birth.latitude, birth.longitude)
    sun = planet_positions(rise, birth.ayanamsha, birth.node_type)[Planet.SUN].longitude
    minutes = (birth.utc_datetime - rise).total_seconds() / 60
    rows = []
    for code, name, rate in (("BL", "Bhava Lagna", .25), ("HL", "Hora Lagna", .5), ("GL", "Ghati Lagna", 1.25)):
        longitude = (sun + minutes * rate) % 360
        rows.append({"code": code, "name": name, "longitude": longitude, "sign": sign_for_longitude(longitude).value,
                     "degree": longitude % 30, "calculation": f"({sun:.6f}° sunrise Sun + {minutes:.6f} minutes × {rate}°/minute) mod 360°",
                     "sunrise": (rise + timedelta(hours=birth.utc_offset_hours)).isoformat()})
    moon = next(p for p in chart.planets if p.planet == Planet.MOON)
    fraction = (moon.longitude % (360 / 27)) / (360 / 27)
    sl = (chart.ascendant.longitude + fraction * 360) % 360
    rows.append({"code": "SL", "name": "Sree Lagna", "longitude": sl, "sign": sign_for_longitude(sl).value,
                 "degree": sl % 30, "calculation": f"({chart.ascendant.longitude:.6f}° Lagna + {fraction:.8f} Moon nakshatra fraction × 360°) mod 360°"})
    return rows


def rudra_strength(p: PlanetPosition, planets: list[PlanetPosition]) -> tuple[float, ...]:
    return (sum(q.planet != p.planet and q.sign == p.sign for q in planets),
            int(dignity_rank(p) >= 2), int(any(q.sign == p.sign and dignity_rank(q) == 3 for q in planets)),
            sum(p.sign in sign_aspects(q.sign) for q in planets), advancement(p))


def advanced_rows(chart: KundaliChart, karakas: list[Row], lagnas: list[Row]) -> Row:
    planets, asc = chart.planets, chart.ascendant.sign
    by = {p.planet: p for p in planets}
    seed = stronger_sign(asc, step(asc, 6), planets)
    candidates = list(dict.fromkeys(primary_lord(step(seed, h - 1), planets) for h in (6, 8, 12)))
    eligible = [p for p in candidates if SIGNS_IN_ORDER.index(by[p].sign) % 2 == 0
                and whole_sign_house(by[p].sign, seed) >= 7]
    brahma = max(eligible, key=lambda p: rudra_strength(by[p], planets)) if eligible else None
    if brahma in (Planet.SATURN, Planet.RAHU, Planet.KETU):
        brahma = list(Planet)[(list(Planet).index(brahma) + 5) % 9]
    special_eighth = RUDRA_EIGHTH[SIGNS_IN_ORDER.index(asc)]
    opposite_eighth = RUDRA_EIGHTH[SIGNS_IN_ORDER.index(step(asc, 6))]
    # Saturn in Lagna/7th uses ordinary eighth houses in this convention.
    if by[Planet.SATURN].sign in (asc, step(asc, 6)):
        special_eighth, opposite_eighth = step(asc, 7), step(asc, 1)
    r_candidates = list(dict.fromkeys(primary_lord(s, planets) for s in (special_eighth, opposite_eighth)))
    rudra = max(r_candidates, key=lambda p: rudra_strength(by[p], planets))
    secondary = [p.value for p in r_candidates if p != rudra
                 and (dignity_rank(by[p]) == -1 or RASHI_LORD[by[p].sign] in NATURAL_ENEMIES.get(p, set()))
                 and any(q.planet in (Planet.MARS, Planet.SATURN, Planet.RAHU, Planet.KETU)
                         and q.planet != p and touches(q.sign, by[p].sign) for q in planets)]
    ak = by[Planet(karakas[0]["planet"])]
    eighth = step(ak.sign, 7)
    node_exception = any(p.planet in (Planet.RAHU, Planet.KETU) and p.sign in (ak.sign, eighth) for p in planets)
    m_house = step(ak.sign, 5) if node_exception else eighth
    maheswara = primary_lord(m_house, planets)
    m_rule = f"Lord of {'6th (node exception)' if node_exception else '8th'} from Atmakaraka in {ak.sign.value}."
    if not node_exception and dignity_rank(by[maheswara]) >= 2:
        initial = by[maheswara]
        choices = list(dict.fromkeys(primary_lord(step(initial.sign, h - 1), planets) for h in (8, 12)))
        maheswara = max(choices, key=lambda p: rudra_strength(by[p], planets))
        m_rule += f" Initial lord is own/exalted: compare 8th/12th lords from {initial.sign.value}."
    maheswara = {Planet.RAHU: Planet.MERCURY, Planet.KETU: Planet.JUPITER}.get(maheswara, maheswara)
    hl = Sign(next(x["sign"] for x in lagnas if x["code"] == "HL"))
    pairs = [("Lagna lord / special eighth lord", by[primary_lord(asc, planets)].sign,
              by[primary_lord(special_eighth, planets)].sign), ("Moon / Saturn", by[Planet.MOON].sign, by[Planet.SATURN].sign),
             ("Lagna / Hora Lagna", asc, hl)]
    categories = {("movable", "movable"): "Long", ("dual", "fixed"): "Long", ("fixed", "dual"): "Long",
                  ("dual", "dual"): "Middle", ("fixed", "movable"): "Middle", ("movable", "fixed"): "Middle",
                  ("fixed", "fixed"): "Short", ("movable", "dual"): "Short", ("dual", "movable"): "Short"}
    pair_rows = [{"pair": name, "first": a.value, "second": b.value, "first_type": SIGN_MODALITY[a],
                  "second_type": SIGN_MODALITY[b], "category": categories[(SIGN_MODALITY[a], SIGN_MODALITY[b])]}
                 for name, a, b in pairs]
    counts = Counter(p["category"] for p in pair_rows)
    category = counts.most_common(1)[0][0] if counts.most_common(1)[0][1] >= 2 else pair_rows[1 if by[Planet.MOON].sign in (asc, step(asc, 6)) else 2]["category"]
    return {"brahma": brahma.value if brahma else None, "brahma_seed": seed.value,
            "brahma_candidates": [{"planet": p.value, "sign": by[p].sign.value, "eligible": p in eligible} for p in candidates],
            "brahma_rule": "6th/8th/12th lords from stronger Lagna/7th; odd sign in the opposite six signs (7th–12th). No eligible candidate means no forced result.",
            "rudra": rudra.value, "secondary_rudra": secondary,
            "rudra_rule": f"Compare lords of {special_eighth.value} and {opposite_eighth.value}: companions, dignity, exalted companions, sign aspects, advancement.",
            "trishoola": [step(by[rudra].sign, offset).value for offset in (0, 4, 8)],
            "maheswara": maheswara.value, "maheswara_rule": m_rule,
            "longevity_pairs": pair_rows, "traditional_category": category,
            "category_rule": "Two agreeing pairs prevail. Three different results: Moon/Saturn if Moon is in Lagna/7th, otherwise Lagna/Hora Lagna.",
            "sthira_karakas": [{"meaning": meaning, "planet": p.value} for meaning, p in (
                ("Father", max((Planet.SUN, Planet.VENUS), key=lambda q: rudra_strength(by[q], planets))),
                ("Mother", max((Planet.MOON, Planet.MARS), key=lambda q: rudra_strength(by[q], planets))),
                ("Younger siblings", Planet.MARS), ("Maternal relatives", Planet.MERCURY),
                ("Children / husband", Planet.JUPITER), ("Wife / in-laws", Planet.VENUS), ("Elder siblings", Planet.SATURN))]}


def build_jaimini_report(chart: KundaliChart) -> Row:
    from vedic_astro.jaimini_dasha import build_dasha_systems
    planets, asc = chart.planets, chart.ascendant.sign
    by = {p.planet: p for p in planets}
    lagnas = special_lagnas(chart)
    padas = arudha_rows(asc, planets)
    reports: dict[str, Row] = {}
    for count in (7, 8):
        karakas = [{"role": KARAKA_INFO[k.karaka][0], "name": "Putrakaraka" if k.karaka == "Putrikaraka" else k.karaka, "planet": k.planet.value,
                    "degree": k.degree_in_sign, "effective_degree": advancement(by[k.planet]),
                    "sign": by[k.planet].sign.value, "navamsa_sign": navamsa_sign(by[k.planet].longitude).value,
                    "meaning": KARAKA_INFO[k.karaka][1],
                    "calculation": (f"30° − {k.degree_in_sign:.8f}° = {advancement(by[k.planet]):.8f}°." if k.planet == Planet.RAHU
                                    else f"{k.degree_in_sign:.8f}° advancement within {by[k.planet].sign.value}.")}
                   for k in compute_chara_karakas(planets, count)]
        ak = by[Planet(karakas[0]["planet"])]
        kl = navamsa_sign(ak.longitude)
        relationships = []
        roles = {k["role"]: k for k in karakas}
        for code, label in (("AmK", "Atmakaraka–Amatyakaraka Raja Yoga"), ("PuK", "Atmakaraka–Putrakaraka Raja Yoga")):
            other = roles.get(code)
            if other:
                other_sign = Sign(other["sign"])
                present = touches(ak.sign, other_sign)
                relationships.append({"name": label, "present": present,
                                      "rule": "The two karakas conjoin or connect by Rashi Drishti.",
                                      "evidence": f"{ak.planet.value} ({ak.sign.value}) / {other['planet']} ({other_sign.value}): "
                                      + ("same sign" if ak.sign == other_sign else "sign aspect" if present else "no sign connection")})
        hl, gl = (Sign(next(x["sign"] for x in lagnas if x["code"] == code)) for code in ("HL", "GL"))
        for p in planets:
            def connects(target: Sign) -> bool:
                return touches(p.sign, target) or RASHI_LORD[target] == p.planet
            lagna, wealth, power = connects(asc), connects(hl), connects(gl)
            if lagna and (wealth or power):
                relationships.append({"name": f"{'Mahayogada' if wealth and power else 'Yogada'} — {p.planet.value}", "present": True,
                                      "rule": "Planet occupies, sign-aspects or owns Lagna and Hora Lagna (wealth) / Ghati Lagna (authority).",
                                      "evidence": f"Lagna {asc.value}: {lagna}; Hora Lagna {hl.value}: {wealth}; Ghati Lagna {gl.value}: {power}."})
        readings = []
        for topic, code in (("Self & direction", "AK"), ("Career & skills", "AmK"), ("Siblings", "BK"),
                            ("Mother & home", "MK"), ("Children & learning", "PuK"), ("Relationships", "DK"), ("Challenges", "GK")):
            k = roles.get(code)
            if not k:
                continue
            p = by[Planet(k["planet"])]
            linked = [q.planet.value for q in planets if q.planet != p.planet and touches(q.sign, p.sign)]
            readings.append({"topic": topic, "planet": p.planet.value,
                             "summary": f"{p.planet.value} is your {k['name']}. Its placement in {p.sign.value} is the starting point for this topic.",
                             "evidence": f"D1: {p.sign.value}, house {whole_sign_house(p.sign, asc)}; D9: {navamsa_sign(p.longitude).value}; "
                             f"sign connections: {', '.join(linked) or 'none'}.",
                             "rule": f"Read {k['name']} with its occupied sign, sign aspects and the sign activated by the selected dasha. A single role does not establish an event or a sibling count."})
        advanced = advanced_rows(chart, karakas, lagnas)
        reports[str(count)] = {"karakas": karakas, "karakamsha": kl.value, "swamsha": kl.value,
                               "yogas": relationships, "readings": readings, "advanced": advanced}
    aspects = [{"planet": p.planet.value, "sign": p.sign.value, "retrograde": p.retrograde,
                "aspected_signs": [s.value for s in sign_aspects(p.sign)],
                "aspected_planets": [{"planet": q.planet.value, "sign": q.sign.value} for q in planets if q.sign in sign_aspects(p.sign)]}
               for p in planets]
    strengths = [{"sign": s.value, "lord": primary_lord(s, planets).value,
                  "metrics": list(sign_strength(s, planets)), "occupants": [p.planet.value for p in planets if p.sign == s]}
                 for s in sorted(SIGNS_IN_ORDER, key=lambda s: sign_strength(s, planets), reverse=True)]
    ul = Sign(padas[11]["sign"])
    return {"schemes": reports, "aspects": aspects, "padas": padas, "argala": argala_rows(planets),
            "strengths": strengths, "lagnas": lagnas, "dasha_systems": build_dasha_systems(chart, reports["7"]["advanced"], lagnas),
            "upapada": {"sign": ul.value, "lord": primary_lord(ul, planets).value, "second_sign": step(ul, 1).value,
                         "second_lord": primary_lord(step(ul, 1), planets).value,
                         "occupants": [p.planet.value for p in planets if p.sign == ul],
                         "second_occupants": [p.planet.value for p in planets if p.sign == step(ul, 1)],
                         "aspecting": [p.planet.value for p in planets if ul in sign_aspects(p.sign)],
                         "rule": "Upapada is the Arudha of the 12th sign. Read its lord, Darakaraka, D9 and the 2nd sign from Upapada together."},
            "rules": {"karakas": "Use full degrees, minutes and seconds; descending advancement. Seven excludes nodes. Eight adds Rahu with 30° minus its degree; Ketu is excluded. Exact ties share a role and leave the next role vacant.",
                      "aspects": "Movable signs aspect fixed signs except the adjacent one; fixed signs aspect movable signs except the adjacent one; dual signs aspect the other three dual signs. All occupants, including nodes, participate.",
                      "karakamsha": "Karakamsha view: natal D1 planets, houses counted from the Atmakaraka's D9 sign. Swamsha view: D9 planets, houses counted from that same sign. Degrees displayed are natal D1 degrees.",
                      "strength": "Compare in order: occupancy, Jupiter/Mercury/lord sign connections, exalted occupant, lord in opposite parity, dual > fixed > movable, lord advancement. Stop at the first unequal criterion. Exact ties retain the first sign.",
                      "argala": "Intervention/blocking pairs: 2/12, 4/10, 11/3, secondary 5/9. Compare counts; equal counts require a strength judgement. Reverse counting when Ketu occupies the target. Three or more malefics in the 3rd create special Argala."}}
