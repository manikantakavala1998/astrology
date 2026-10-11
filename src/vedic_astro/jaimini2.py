"""Sampath Kumar worksheets, independent of the app's other Jaimini engine.

Conventions and unresolved passages are recorded in docs/jaimini2.md.
Only astronomical positions and common zodiac arithmetic are shared.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from vedic_astro.aspects import SIGN_MODALITY, sign_aspects
from vedic_astro.dignity import EXALTATION_SIGN
from vedic_astro.divisional_charts import drekkana_sign
from vedic_astro.models import KundaliChart, Planet, PlanetPosition, Sign, SIGNS_IN_ORDER
from vedic_astro.rashi_bhava import RASHI_LORD
from vedic_astro.varga import navamsa_sign

Row = dict[str, Any]
CLASSICAL = tuple(list(Planet)[:7])
TYPE_RANK = {"movable": 0, "fixed": 1, "dual": 2}
SPECIAL_EIGHTH = [Sign.SCORPIO, Sign.GEMINI, Sign.CAPRICORN, Sign.SAGITTARIUS,
                 Sign.CANCER, Sign.AQUARIUS, Sign.TAURUS, Sign.SAGITTARIUS,
                 Sign.CANCER, Sign.GEMINI, Sign.CAPRICORN, Sign.LEO]
PADAKRAMA_EIGHTH = [Sign.SCORPIO, Sign.GEMINI, Sign.ARIES, Sign.SAGITTARIUS,
                   Sign.CANCER, Sign.SCORPIO, Sign.TAURUS, Sign.SAGITTARIUS,
                   Sign.LIBRA, Sign.GEMINI, Sign.CAPRICORN, Sign.TAURUS]
KARAKAS = [
    ("AK", "Atmakaraka", "Self & direction"), ("AmK", "Amatyakaraka", "Work & education"),
    ("BK", "Bhratrikaraka", "Siblings"), ("MK", "Matrikaraka", "Mother & home"),
    ("PK", "Putrakaraka", "Children & followers"), ("GK", "Gnatikaraka", "Relatives & obstacles"),
    ("DK", "Darakaraka", "Relationships"),
]
PADA_NAMES = ["Arudha Lagna", "Dhana Pada", "Bhratri Pada", "Matri Pada", "Putra Pada",
              "Shatru Pada", "Dara Pada", "Randhra Pada", "Bhagya Pada", "Rajya Pada",
              "Labha Pada", "Upapada Lagna"]


def step(sign: Sign, offset: int) -> Sign:
    return SIGNS_IN_ORDER[(SIGNS_IN_ORDER.index(sign) + offset) % 12]


def parity(sign: Sign) -> int:
    return 1 if SIGNS_IN_ORDER.index(sign) % 2 == 0 else -1


def passed(first: Sign, second: Sign, direction: int) -> int:
    return (direction * (SIGNS_IN_ORDER.index(second) - SIGNS_IN_ORDER.index(first))) % 12


def exalted(p: PlanetPosition) -> bool:
    signs = {**EXALTATION_SIGN, Planet.KETU: Sign.LEO, Planet.RAHU: Sign.AQUARIUS}
    return p.sign == signs.get(p.planet)


def planet_key(p: PlanetPosition, planets: list[PlanetPosition]) -> tuple[float, ...]:
    return (sum(q.sign == p.sign and q.planet != p.planet for q in planets),
            int(exalted(p)), TYPE_RANK[SIGN_MODALITY[p.sign]], p.degree_in_sign)


def lord(sign: Sign, planets: list[PlanetPosition]) -> Planet:
    classic = RASHI_LORD[sign]
    node = {Sign.SCORPIO: Planet.KETU, Sign.AQUARIUS: Planet.RAHU}.get(sign)
    by = {p.planet: p for p in planets}
    if node is None:
        return classic
    if exalted(by[node]) != exalted(by[classic]):
        return node if exalted(by[node]) else classic
    if by[classic].sign == sign and by[node].sign != sign:
        return node
    # After the exclusive exaltation/own-sign rules, compare conjunction count,
    # sign type, and duration. Exact remaining ties keep the classical lord.
    def key(p: PlanetPosition) -> tuple[int, ...]:
        return (sum(q.sign == p.sign and q.planet != p.planet for q in planets),
                TYPE_RANK[SIGN_MODALITY[p.sign]], passed(sign, p.sign, parity(sign)) or 12,
                int(exalted(p)))
    return node if key(by[node]) > key(by[classic]) else classic


def sign_key(sign: Sign, planets: list[PlanetPosition]) -> tuple[float, ...]:
    occupants = [p for p in planets if p.sign == sign]
    return (len(occupants), max((p.degree_in_sign for p in occupants), default=0),
            TYPE_RANK[SIGN_MODALITY[sign]])


def sign_strength_rows(planets: list[PlanetPosition]) -> list[Row]:
    rows: list[Row] = []
    previous: tuple[float, ...] | None = None
    rank = 0
    for index, sign in enumerate(sorted(SIGNS_IN_ORDER, key=lambda s: sign_key(s, planets), reverse=True)):
        key = sign_key(sign, planets)
        if key != previous:
            rank = index + 1
        rows.append({"sign": sign.value, "rank": rank, "lord": lord(sign, planets).value,
                     "metrics": list(key), "occupants": [p.planet.value for p in planets if p.sign == sign]})
        previous = key
    return rows


def strongest(signs: list[Sign], planets: list[PlanetPosition]) -> Sign:
    # Exact equal keys retain the first listed candidate, disclosed in the UI.
    return max(signs, key=lambda s: sign_key(s, planets))


def dwaya_hora(longitude: float) -> Sign:
    """Successive 15-degree portions cycle twice through the zodiac."""
    return SIGNS_IN_ORDER[int((longitude % 360) / 15) % 12]


def karakas(planets: list[PlanetPosition]) -> tuple[list[Row], list[str]]:
    ranked = sorted((p for p in planets if p.planet in CLASSICAL),
                    key=lambda p: p.degree_in_sign, reverse=True)
    warnings = []
    for a, b in zip(ranked, ranked[1:]):
        if abs(a.degree_in_sign - b.degree_in_sign) < 1e-10:
            warnings.append(f"Exact degree tie: {a.planet.value} / {b.planet.value}. "
                            "The book's exceptional Rahu assignment is not fully specified; tied roles need review.")
    return [{"role": role, "name": name, "meaning": meaning, "planet": p.planet.value,
             "degree": p.degree_in_sign, "effective_degree": p.degree_in_sign,
             "sign": p.sign.value, "navamsa_sign": navamsa_sign(p.longitude).value,
             "calculation": f"Rank {i + 1} of seven by unrounded longitude within the natal sign."}
            for i, (p, (role, name, meaning)) in enumerate(zip(ranked, KARAKAS))], warnings


def mirror(source: Sign, lord_sign: Sign) -> tuple[Sign, int, bool]:
    count = passed(source, lord_sign, 1) + 1
    raw = step(lord_sign, count - 1)
    correction = raw in (source, step(source, 6))
    return (step(raw, 9) if correction else raw), count, correction


def pada_rows(asc: Sign, planets: list[PlanetPosition]) -> list[Row]:
    by = {p.planet: p for p in planets}
    rows = []
    for h in range(1, 13):
        source = step(asc, h - 1)
        owner = lord(source, planets)
        result, count, correction = mirror(source, by[owner].sign)
        rows.append({"house": h, "code": "AL" if h == 1 else "UL" if h == 12 else f"A{h}",
                     "name": PADA_NAMES[h - 1], "sign": result.value, "source_sign": source.value,
                     "lord": owner.value, "lord_sign": by[owner].sign.value, "count": count,
                     "exception": correction,
                     "calculation": f"{source.value} → {by[owner].sign.value}: {count} signs inclusive; "
                     f"repeat from the lord → {result.value}. "
                     + ("Apply the classical 1st/7th mirror correction (10th from raw result)." if correction else "No mirror correction.")})
    return rows


def argala_rows(planets: list[PlanetPosition]) -> list[Row]:
    by = {p.planet: p for p in planets}
    malefics = {Planet.SUN, Planet.MARS, Planet.SATURN, Planet.RAHU}
    if (by[Planet.MOON].longitude - by[Planet.SUN].longitude) % 360 >= 180:
        malefics.add(Planet.MOON)
    if any(p.sign == by[Planet.MERCURY].sign and p.planet in malefics for p in planets):
        malefics.add(Planet.MERCURY)
    rows = []
    for target in SIGNS_IN_ORDER:
        reverse = by[Planet.KETU].sign == target
        for opening, blocking in ((2, 12), (4, 10), (11, 3), (5, 9), (6, 8)):
            if opening == 6 and not reverse:
                continue
            direction = -1 if reverse and opening in (5, 6) else 1
            a, b = step(target, direction * (opening - 1)), step(target, direction * (blocking - 1))
            contributors = [p for p in planets if p.sign == a]
            blockers = [p for p in planets if p.sign == b]
            degree_matches = [(p, q) for p in contributors for q in blockers
                              if p.degree_in_sign < 7.5 and q.degree_in_sign >= 22.5]
            if not contributors:
                status = "No Argala"
            elif not blockers:
                status = "Unobstructed · no blocker"
            elif len(contributors) > len(blockers):
                status = "Unobstructed · more contributors"
            elif all(p.degree_in_sign < 7.5 for p in contributors) and not degree_matches:
                status = "Unobstructed · degree condition not met"
            elif degree_matches and len(contributors) == len(blockers) == 1:
                status = "Degree obstruction · compare strength"
            else:
                status = "Needs degree / strength judgement"
            rows.append({"target": target.value, "argala_house": opening, "argala_sign": a.value,
                         "argala_planets": [p.planet.value for p in contributors],
                         "blocking_house": blocking, "blocking_sign": b.value,
                         "blocking_planets": [p.planet.value for p in blockers], "status": status,
                         "reverse": direction == -1, "special": opening == 6,
                         "calculation": f"{len(contributors)} contributors; {len(blockers)} blockers. "
                         f"First-quarter contributor / last-quarter blocker matches: {len(degree_matches)}. "
                         "Other degree-quarter correspondences are not specified by this rule."})
        third = step(target, 2)
        kama = [p.planet.value for p in planets if p.sign == third and p.planet in malefics]
        rows.append({"target": target.value, "argala_house": 3, "argala_sign": third.value,
                     "argala_planets": kama, "blocking_house": 0, "blocking_sign": "—",
                     "blocking_planets": [], "status": "Kaama Argala · unobstructed" if len(kama) >= 3 else "Kaama condition absent",
                     "reverse": False, "special": True, "calculation": f"{len(kama)} evaluated malefics in the third; at least three required."})
        benefics = {Planet.JUPITER, Planet.VENUS}
        if Planet.MOON not in malefics:
            benefics.add(Planet.MOON)
        if Planet.MERCURY not in malefics:
            benefics.add(Planet.MERCURY)
        support = [p.planet.value for p in planets if p.sign in (target, step(target, 6)) and p.planet in benefics]
        rows.append({"target": target.value, "argala_house": 1, "argala_sign": f"{target.value} / {step(target, 6).value}",
                     "argala_planets": support, "blocking_house": 0, "blocking_sign": "—", "blocking_planets": [],
                     "status": "Bhava Argala · unobstructed" if support else "Bhava condition absent",
                     "reverse": False, "special": True, "calculation": "Benefics in the target or its seventh create Bhava Argala."})
    return rows


def advanced_rows(chart: KundaliChart, ak: PlanetPosition) -> Row:
    planets = chart.planets
    by = {p.planet: p for p in planets}
    asc = chart.ascendant.sign
    hl = dwaya_hora(chart.ascendant.longitude)
    # The Ayurdaya chapter uses Saturn alone for Aquarius (Somanatha convention).
    def ayur_lord(s: Sign) -> Planet:
        return Planet.SATURN if s == Sign.AQUARIUS else lord(s, planets)
    a = ayur_lord(asc)
    eighth = SPECIAL_EIGHTH[SIGNS_IN_ORDER.index(asc)]
    b = ayur_lord(eighth)
    if a == b:
        eighth = SPECIAL_EIGHTH[SIGNS_IN_ORDER.index(by[a].sign)]
        b = ayur_lord(eighth)
    raw_pairs = [("Lagna lord / special eighth lord", by[a].sign, by[b].sign),
                 ("Lagna / Moon", asc, by[Planet.MOON].sign), ("Lagna / Dwaya Hora Lagna", asc, hl)]
    categories = {("movable", "movable"): "Long", ("dual", "fixed"): "Long", ("fixed", "dual"): "Long",
                  ("dual", "dual"): "Middle", ("fixed", "movable"): "Middle", ("movable", "fixed"): "Middle"}
    pairs = [{"pair": name, "first": x.value, "second": y.value, "first_type": SIGN_MODALITY[x],
              "second_type": SIGN_MODALITY[y], "category": categories.get((SIGN_MODALITY[x], SIGN_MODALITY[y]), "Short")}
             for name, x, y in raw_pairs]
    counts = Counter(p["category"] for p in pairs)
    category = counts.most_common(1)[0][0]
    if len(counts) == 3:
        category = pairs[1 if by[Planet.MOON].sign in (asc, step(asc, 6)) else 2]["category"]
    seed = strongest([asc, step(asc, 6)], planets)
    eligible: list[PlanetPosition] = []
    for offset in range(1, 13):
        candidate = step(seed, -offset)
        eligible = [p for p in planets if p.sign == candidate and p.planet != Planet.KETU] if parity(candidate) == 1 else []
        if eligible:
            break
    brahma = max(eligible, key=lambda p: p.degree_in_sign) if eligible else None
    rahu = by[Planet.RAHU]
    if len(eligible) > 1 and rahu in eligible and rahu.degree_in_sign == min(p.degree_in_sign for p in eligible):
        brahma = rahu
    rudra_candidates = [by[lord(step(asc, h - 1), planets)] for h in (7, 8)]
    rudra = max(rudra_candidates, key=lambda p: planet_key(p, planets))
    ma_candidates = [by[lord(step(ak.sign, h - 1), planets)] for h in (6, 8, 12)]
    maheswara = max(ma_candidates, key=lambda p: planet_key(p, planets))
    return {"brahma": brahma.planet.value if brahma else None, "brahma_seed": seed.value,
            "brahma_candidates": [{"planet": p.planet.value, "sign": p.sign.value, "eligible": p in eligible} for p in planets],
            "brahma_rule": "Preceding odd-sign variant: search backwards from the stronger Lagna/seventh for an occupied odd sign; highest natal degree wins. Ketu excluded; lowest-degree Rahu in a conjunction takes precedence.",
            "rudra": rudra.planet.value, "secondary_rudra": [],
            "rudra_rule": "Compare the seventh and eighth lords by companions, exaltation, sign type, then natal degree. Exact ties retain the seventh-lord candidate.",
            "trishoola": [step(rudra.sign, i).value for i in (0, 4, 8)], "maheswara": maheswara.planet.value,
            "maheswara_rule": "Sixth/eighth/twelfth-lord variant from the AK's natal sign; compare companions, exaltation, sign type, then degree. Other Maheshwara variants are kept separate.",
            "longevity_pairs": pairs, "traditional_category": category,
            "category_rule": f"Special eighth: {eighth.value}, lord {b.value}; Lagna lord {a.value}. Aquarius uses Saturn here. Two matching categories decide; if all differ use Lagna/Hora, except Moon in Lagna/seventh uses Lagna/Moon. No numerical lifespan is inferred.",
            "sthira_karakas": [{"meaning": name, "planet": p.value} for name, p in
                               [("Father · daytime", Planet.SUN), ("Father · night", Planet.SATURN),
                                ("Mother", Planet.MOON), ("Younger siblings", Planet.MARS),
                                ("Elder siblings & children", Planet.JUPITER), ("Spouse", Planet.VENUS)]]}


def yoga_rows(chart: KundaliChart, ks: list[Row]) -> list[Row]:
    by = {p.planet: p for p in chart.planets}
    asc = chart.ascendant.sign
    lagnas = [asc, drekkana_sign(chart.ascendant.longitude), navamsa_sign(chart.ascendant.longitude)]
    rows = []
    for p in chart.planets:
        positions = [p.sign, drekkana_sign(p.longitude), navamsa_sign(p.longitude)]
        hit = [code for code, ps, lag in zip(("D1", "D3", "D9"), positions, lagnas) if lag in sign_aspects(ps)]
        rows.append({"name": f"{p.planet.value} · multi-chart Yogada", "present": len(hit) >= 2,
                     "kind": "yogada", "planets": [p.planet.value],
                     "variant": "multi_chart", "matched_charts": hit,
                     "rule": "A planet sign-aspecting the corresponding Lagna in at least two of D1, D3 and D9 qualifies.",
                     "evidence": "Matching charts: " + (", ".join(hit) or "none")})
        targets = [step(asc, h - 1) for h in (1, 5, 7, 9)]
        connections = [s.value for s in targets if s in sign_aspects(p.sign)]
        rows.append({"name": f"{p.planet.value} · Kevala", "present": bool(connections),
                     "kind": "kevala", "planets": [p.planet.value],
                     "variant": "sign_aspect", "connections": [
                         {"sign": target.value, "house": house, "target": "Lagna" if house == 1 else f"H{house}"}
                         for house, target in zip((1, 5, 7, 9), targets) if target.value in connections],
                     "rule": "Rashi aspect to Lagna, fifth, seventh or ninth. Occupation alone is not counted as an aspect.",
                     "evidence": "Connected signs: " + (", ".join(connections) or "none")})
    moon = by[Planet.MOON]
    owner = by[lord(moon.sign, chart.planets)]
    hits = [s.value for s in (moon.sign, asc) if s in sign_aspects(owner.sign)]
    rows.append({"name": "Moon-dispositor Yogada", "present": len(hits) == 2,
                 "kind": "yogada", "planets": [owner.planet.value],
                 "variant": "moon_dispositor", "connections": [
                     {"sign": sign.value, "house": passed(asc, sign, 1) + 1, "target": target}
                     for target, sign in (("Moon", moon.sign), ("Lagna", asc)) if sign in sign_aspects(owner.sign)],
                 "rule": "Moon's sign lord sign-aspects both Moon and Lagna.",
                 "evidence": f"{owner.planet.value} in {owner.sign.value}; targets matched: {', '.join(hits) or 'none'}."})
    rows.append({"name": "Moon-dispositor Kevala", "present": len(hits) == 1,
                 "kind": "kevala", "planets": [owner.planet.value], "variant": "moon_dispositor",
                 "connections": [
                     {"sign": sign.value, "house": passed(asc, sign, 1) + 1, "target": target}
                     for target, sign in (("Moon", moon.sign), ("Lagna", asc)) if sign in sign_aspects(owner.sign)],
                 "rule": "Moon's sign lord sign-aspects exactly one of Moon or Lagna.",
                 "evidence": f"{owner.planet.value} in {owner.sign.value}; targets matched: {', '.join(hits) or 'none'}."})
    ak9, am9 = Sign(ks[0]["navamsa_sign"]), Sign(ks[1]["navamsa_sign"])
    house = passed(ak9, am9, 1) + 1
    rows.append({"name": "Amatyakaraka support from AK · D9", "present": house in (1, 4, 5, 7, 9, 10, 11),
                 "kind": "other", "planets": [ks[0]["planet"], ks[1]["planet"]],
                 "rule": "AmK in a kendra, trine or eleventh from AK in D9.",
                 "evidence": f"{ks[1]['planet']} in {am9.value} is H{house} from {ak9.value}."})
    moon9, venus9 = navamsa_sign(moon.longitude), navamsa_sign(by[Planet.VENUS].longitude)
    rows.append({"name": "Moon–Venus connection · D9", "present": moon9 == venus9 or venus9 in sign_aspects(moon9),
                 "kind": "other", "planets": [Planet.MOON.value, Planet.VENUS.value],
                 "rule": "Moon and Venus conjunct or connected by mutual rashi aspects in D9.",
                 "evidence": f"Moon {moon9.value}; Venus {venus9.value}."})
    return rows


def readings(chart: KundaliChart, ks: list[Row], padas: list[Row], yogas: list[Row]) -> list[Row]:
    kl = Sign(ks[0]["navamsa_sign"])
    in_kl = [p for p in chart.planets if navamsa_sign(p.longitude) == kl]
    occupations = {Planet.SUN: "public administration", Planet.MOON: "property and construction",
                   Planet.MARS: "technical, defence or legal work", Planet.MERCURY: "commerce, distribution and mediation",
                   Planet.JUPITER: "teaching, law and academic study", Planet.VENUS: "creative arts and media",
                   Planet.SATURN: "independent work and leadership", Planet.RAHU: "industry and media",
                   Planet.KETU: "philosophy and commission-based trade"}
    self_text = {Sign.PISCES: "The book connects Pisces Karakamsha with spiritual interests and philosophical study.",
                 Sign.AQUARIUS: "The book connects Aquarius Karakamsha with service and social contribution.",
                 Sign.LIBRA: "The book connects Libra Karakamsha with trade and business.",
                 Sign.TAURUS: "The book connects Taurus Karakamsha with vehicles, animals and cleanliness."}
    am_support = next(y for y in yogas if y["name"] == "Amatyakaraka support from AK · D9")
    dk = ks[-1]
    ul = Sign(padas[11]["sign"])
    benefics = [p.planet.value for p in chart.planets if p.planet in (Planet.JUPITER, Planet.VENUS, Planet.MERCURY)
                and ul in sign_aspects(p.sign)]
    al = Sign(padas[0]["sign"])
    wealth = [p.planet.value for p in chart.planets if p.planet in (Planet.JUPITER, Planet.VENUS, Planet.MERCURY)
              and (p.sign == al or al in sign_aspects(p.sign))]
    return [
        {"topic": "Self & spiritual direction", "planet": ks[0]["planet"],
         "summary": self_text.get(kl, "Read the planets in your Karakamsha together. A sign alone does not establish a personal outcome."),
         "evidence": f"Your Atmakaraka is {ks[0]['planet']}; its D9 sign is {kl.value}. D9 occupants: {', '.join(p.planet.value for p in in_kl) or 'none'}.",
         "rule": "Karakamsha is the AK's Navamsa sign. D9 occupation and D1 connections are separate checks."},
        {"topic": "Work & education", "planet": ks[1]["planet"],
         "summary": ("Your D9 placements meet the book's AmK support condition. " if am_support["present"] else "Your D9 placements do not meet the AmK support condition. ")
         + ("Planets in Karakamsha point to " + "; ".join(occupations[p.planet] for p in in_kl) + "." if in_kl else "Check your Amatyakaraka and the fifth/ninth signs for education."),
         "evidence": am_support["evidence"], "rule": am_support["rule"] + " Karakamsha occupations are traditional indications, not a prescribed career."},
        {"topic": "Relationships", "planet": dk["planet"],
         "summary": ("Benefic sign aspects reach your Upapada, a supportive relationship condition in this method." if benefics else "No Jupiter, Venus or Mercury sign aspect reaches the standard Upapada. Check its lord and Darakaraka together."),
         "evidence": f"Darakaraka: {dk['planet']}, D9 {dk['navamsa_sign']}. Standard UL: {ul.value}. Benefic aspects: {', '.join(benefics) or 'none'}.",
         "rule": "This reading uses the twelfth-house Upapada described in the book. Its separate Anuchara/Agrachara research variants are shown in Upapada; no marriage date or count follows from this single condition."},
        {"topic": "Wealth & public image", "planet": Planet.VENUS.value,
         "summary": ("Benefic planets connect with your Arudha Lagna, supporting the book's wealth/public-image indication." if wealth else "The benefic-to-Arudha condition is absent. Read income and Venus connections in the chosen dasha separately."),
         "evidence": f"Arudha Lagna: {al.value}. Connected benefics: {', '.join(wealth) or 'none'}.",
         "rule": "Benefic occupation/aspect to AL is a chart condition. Chara periods connected to Venus add a wealth/comfort indication; they do not calculate an amount of money."},
    ]


def upapada_variants(chart: KundaliChart) -> list[Row]:
    by = {p.planet: p for p in chart.planets}
    owner = by[lord(chart.ascendant.sign, chart.planets)]
    base = step(owner.sign, -1) if owner.retrograde else owner.sign
    rows = []
    for name, direction in (("Anuchara · male-chart research variant", parity(base)),
                            ("Agrachara · female-chart research variant", -parity(base))):
        source = step(base, direction)
        source_owner = by[lord(source, chart.planets)]
        effective_sign = step(source_owner.sign, -1) if source_owner.retrograde else source_owner.sign
        # The research chapter's own-sign example uses fourth, rather than
        # substituting the ordinary tenth-house arudha correction.
        count = passed(source, effective_sign, 1) + 1
        result = step(effective_sign, count - 1) if count != 1 else step(source, 3)
        rows.append({"name": name, "pithru": owner.sign.value, "source": source.value, "lord": source_owner.planet.value,
                     "sign": result.value, "calculation": f"Pithru {owner.sign.value}" + (f" → previous {base.value} for retrograde lord" if owner.retrograde else "")
                     + f"; source {source.value}, effective lord sign {effective_sign.value}; count {count} twice. "
                     + ("Own-sign case uses fourth." if count == 1 else "Research variant shown separately from the standard UL.")})
    return rows


def period_readings(chart: KundaliChart, ks: list[Row], systems: list[Row]) -> None:
    """Attach method-specific conditions; do not transplant one school's rules."""
    by = {p.planet: p for p in chart.planets}
    ak = by[Planet(ks[0]["planet"])]
    am = by[Planet(ks[1]["planet"])]
    gk = by[Planet(ks[5]["planet"])]
    venus = by[Planet.VENUS]
    for system in systems:
        system["activation_rules"] = {}
        for sign in SIGNS_IN_ORDER:
            conditions = []
            if system["code"] == "chara":
                connected = sign == venus.sign or sign in sign_aspects(venus.sign)
                conditions.append({"topic": "Money & comforts", "present": connected,
                                   "summary": "Venus connects with this Chara period; the book associates this with money, comforts and creative interests.",
                                   "evidence": f"Venus in {venus.sign.value}; period {sign.value}; occupation or rashi aspect: {'yes' if connected else 'no'}.",
                                   "rule": "Evaluate Venus occupation/aspect to the running Chara sign. This condition alone does not establish a financial event."})
            elif system["code"] == "navamsa":
                am9, ak9 = navamsa_sign(am.longitude), navamsa_sign(ak.longitude)
                am_house, ak_house = passed(sign, am9, 1) + 1, passed(sign, ak9, 1) + 1
                conditions.extend([
                    {"topic": "Work support", "present": am_house == 11,
                     "summary": "Your Amatyakaraka is eleventh from this D9 period sign, meeting the book's supportive dasha condition.",
                     "evidence": f"{am.planet.value} in D9 {am9.value} is H{am_house} from {sign.value}.",
                     "rule": "AmK in the eleventh from the running Navamsa dasha sign is a supportive condition."},
                    {"topic": "Change of place", "present": ak_house in (3, 9, 12),
                     "summary": "The AK's D9 position meets the book's change-of-place or transfer condition for this period.",
                     "evidence": f"{ak.planet.value} in D9 {ak9.value} is H{ak_house} from {sign.value}.",
                     "rule": "AK in third, ninth or twelfth from the running D9 dasha sign is a relocation/transfer indication, not a confirmed move."},
                ])
            elif system["code"] == "sthira":
                connected = am.sign == gk.sign or gk.sign in sign_aspects(am.sign)
                period_connected = any(p.sign == sign or sign in sign_aspects(p.sign) for p in (am, gk))
                conditions.append({"topic": "Work changes", "present": connected and period_connected,
                                   "summary": "Amatyakaraka and Gnatikaraka connect, and this period connects to them. The book treats this as a condition for changes in work.",
                                   "evidence": f"AmK {am.planet.value} in {am.sign.value}; GK {gk.planet.value} in {gk.sign.value}; mutual connection {'yes' if connected else 'no'}; period connection {'yes' if period_connected else 'no'}.",
                                   "rule": "The Sthira chapter examines GK–AmK connections during the periods of their connected signs."})
            if conditions:
                system["activation_rules"][sign.value] = conditions


def build_jaimini2_report(chart: KundaliChart) -> Row:
    from vedic_astro.jaimini2_dasha import build_catalog
    from vedic_astro.jaimini2_predictions import build_detailed_predictions

    planets = chart.planets
    by = {p.planet: p for p in planets}
    ks, warnings = karakas(planets)
    ak = by[Planet(ks[0]["planet"])]
    padas = pada_rows(chart.ascendant.sign, planets)
    advanced = advanced_rows(chart, ak)
    yogas = yoga_rows(chart, ks)
    ul = Sign(padas[-1]["sign"])
    second = step(ul, 1)
    systems = build_catalog(chart, ks, advanced, padas)
    period_readings(chart, ks, systems)
    variants = upapada_variants(chart)
    predictions = build_detailed_predictions(chart, ks, padas, yogas, variants, systems)
    if warnings:
        # Do not date an AK-dependent method using an arbitrarily ordered tie.
        for system in systems:
            system["periods"] = []
            system["unavailable"] = "Exact Chara-karaka tie requires a resolved assignment before this worksheet can be dated."
    return {"author": "Medavarapu Sampath Kumar", "edition": "English translation by Dr K. V. Pratap Kumar",
            "warnings": warnings, "schemes": {"7": {"karakas": ks, "karakamsha": navamsa_sign(ak.longitude).value,
            "swamsha": navamsa_sign(ak.longitude).value, "advanced": advanced, "yogas": yogas,
            "readings": readings(chart, ks, padas, yogas)}},
            "aspects": [{"planet": p.planet.value, "sign": p.sign.value, "retrograde": p.retrograde,
                         "aspected_signs": [s.value for s in sign_aspects(p.sign)],
                         "aspected_planets": [{"planet": q.planet.value, "sign": q.sign.value} for q in planets if q.sign in sign_aspects(p.sign)]} for p in planets],
            "navamsa_aspects": [{"planet": p.planet.value, "sign": navamsa_sign(p.longitude).value,
                                 "aspected_signs": [s.value for s in sign_aspects(navamsa_sign(p.longitude))]} for p in planets],
            "padas": padas, "argala": argala_rows(planets),
            "strengths": sign_strength_rows(planets),
            "lagnas": [{"code": "PDHL", "name": "Parivritti Dwaya Hora Lagna", "longitude": SIGNS_IN_ORDER.index(dwaya_hora(chart.ascendant.longitude)) * 30 + (chart.ascendant.longitude % 15) * 2,
                         "sign": dwaya_hora(chart.ascendant.longitude).value, "degree": (chart.ascendant.longitude % 15) * 2,
                         "calculation": f"floor(Lagna longitude {chart.ascendant.longitude:.8f}° / 15) mod 12 selects the sign. Degree shown is progress within that 15° portion × 2."}],
            "dasha_systems": systems, "upapada_variants": variants, "predictions": predictions,
            "upapada": {"sign": ul.value, "lord": lord(ul, planets).value, "second_sign": second.value,
                        "second_lord": lord(second, planets).value, "occupants": [p.planet.value for p in planets if p.sign == ul],
                        "second_occupants": [p.planet.value for p in planets if p.sign == second],
                        "aspecting": [p.planet.value for p in planets if ul in sign_aspects(p.sign)],
                        "rule": "Standard UL mirrors the twelfth-house sign through its lord. The book also gives distinct Anuchara/Agrachara research variants, calculated separately below."},
            "rules": {"karakas": "Rank the seven classical planets by unrounded natal degree within their signs. Rahu and Ketu are excluded from the ordinary scheme. Exact ties are flagged for the book's exceptional assignment rather than silently resolved.",
                      "karakamsha": "Karakamsha uses the AK's D9 sign as the starting house in D1; Swamsha uses the same starting sign in D9. Planet degrees displayed are natal D1 degrees.",
                      "aspects": "Movable signs aspect non-adjacent fixed signs; fixed signs aspect non-adjacent movable signs; dual signs aspect the other dual signs. Occupants inherit the sign's aspects.",
                      "argala": "Primary pairs are 2/12, 4/10 and 11/3; secondary 5/9. Ketu reverses 5/9 and adds reverse 6/8. First-quarter contributors require last-quarter blockers; other quarters need judgement. Three malefics in third give Kaama Argala; benefics in first/seventh give Bhava Argala.",
                      "strength": "Fourfold chapter hierarchy: occupied over empty, more occupants, greatest occupant degree, then dual > fixed > movable. Earlier Argala prose reverses fixed/movable priority; this table explicitly uses the fourfold chapter. Exact equal keys retain the first candidate in each method's listed seed set."}}
