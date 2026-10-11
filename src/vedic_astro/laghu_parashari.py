"""Laghu Parashari: explicit lordship, sambandha and period worksheets.

Whole-sign lordship is independent of the selected Bhava Chalit system.
Mixed ownership remains mixed: no invented numerical good/bad score is used.
See docs/laghu-parashari.md for conventions and conditional rules.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any

from vedic_astro.aspects import ASPECT_OFFSETS
from vedic_astro.dasha import DASHA_YEARS
from vedic_astro.models import KundaliChart, Planet, Sign, SIGNS_IN_ORDER
from vedic_astro.rashi_bhava import RASHI_LORD, whole_sign_house

CLASSICAL = tuple(list(Planet)[:7])
KENDRAS = {1, 4, 7, 10}
TRINES = {1, 5, 9}
ADVERSE = {3, 6, 11}
Row = dict[str, Any]

# Topic index, not a reproduction of a modern translation.
TOPICS = [
    ("Foundations", "Invocation", "Opening context"),
    ("Foundations", "Method & purpose", "Parashari framework"),
    ("Foundations", "Vimshottari basis", "Moon's nakshatra and balance at birth"),
    ("Foundations", "House meanings", "House meanings underpin the interpretation"),
    ("Foundations", "Graha aspects", "All classical planets: 7th; Mars: 4th/8th; Jupiter: 5th/9th; Saturn: 3rd/10th"),
    ("Foundations", "Trine and adverse lords", "Trine ownership supports; 3rd/6th/11th ownership challenges"),
    ("Foundations", "Kendra ownership", "Angular ownership modifies natural benefic or malefic character"),
    ("Foundations", "2nd and 12th ownership", "Judge other ownership and associations"),
    ("Foundations", "8th-lord exception", "Lagna ownership removes the 8th-lord defect"),
    ("Foundations", "Kendradhipati dosha", "Jupiter and Venus require particular attention, especially with Maraka links"),
    ("Foundations", "Planet-specific exceptions", "Mercury/Moon are less affected; Sun/Moon have an 8th-lord exception"),
    ("Foundations", "Mars as 10th lord", "10th ownership alone is insufficient; trine ownership supports"),
    ("Foundations", "Rahu and Ketu", "Read occupied house, dispositor and associated planets"),
    ("Raja Yoga", "Angle–trine connection", "Connected Kendra and trine lords can produce yoga"),
    ("Raja Yoga", "Yoga despite defects", "A connection can support yoga despite adverse lordships"),
    ("Raja Yoga", "9th–10th connection", "Check conjunction, mutual aspect and exchange"),
    ("Raja Yoga", "Strong angular lord", "Trine connection needs strength context"),
    ("Raja Yoga", "Yoga timing", "Yoga-maker periods and intervening benefic subperiods"),
    ("Raja Yoga", "Associated malefics", "Connected malefics may deliver yoga in their subperiods"),
    ("Raja Yoga", "Single Yogakaraka", "One planet owns a Kendra and a trine"),
    ("Raja Yoga", "Nodes as yoga makers", "Kendra/trine placement plus a relevant lord association"),
    ("Raja Yoga", "8th/11th overlap", "Extra 8th/11th ownership limits a mere 9th–10th connection"),
    ("Maraka", "Longevity and Maraka houses", "3rd/8th are longevity houses; 2nd/7th are Maraka houses"),
    ("Maraka", "Maraka candidates", "2nd before 7th; examine their lords, occupants and malefic associates"),
    ("Maraka", "Period hierarchy", "A lifespan prerequisite precedes the period hierarchy"),
    ("Maraka", "Fallback candidates", "Examine connected benefics and the 8th lord only in the full hierarchy"),
    ("Maraka", "Further fallback", "Malefic fallback requires the preceding conditions"),
    ("Maraka", "Saturn priority", "Saturn connected to Maraka candidates receives special priority"),
    ("Dasha", "Own dasha and bhukti", "An own-lord period alone does not settle the result"),
    ("Dasha", "Related subperiod lord", "Relationship or similar role helps deliver the major lord's results"),
    ("Dasha", "Contrary period roles", "Judge both lords rather than a single label"),
    ("Dasha", "Kendra–trine periods", "A relationship is needed for mutual period support"),
    ("Dasha", "Raja Yoga onset", "Yoga may begin during a Maraka subperiod"),
    ("Dasha", "Continuation of yoga", "Benefic subperiods may continue an established yoga"),
    ("Dasha", "Yogakaraka bhukti", "Yoga-maker subperiod under an associated benefic"),
    ("Dasha", "Node subperiods", "Isolated nodes in supportive positions remain dependent on the subperiod"),
    ("Dasha", "Malefic major period", "Unconnected benefic subperiod can be difficult"),
    ("Dasha", "Mixed and adverse periods", "Connected benefic gives mixed indications; unrelated yoga-maker needs caution"),
    ("Dasha", "Maraka subperiod context", "Benefic and malefic subperiods are judged differently"),
    ("Dasha", "Saturn–Venus exception", "Reciprocal periods have an exception; no automatic good/bad inversion"),
    ("Dasha", "Lagna–10th exchange", "Mutual sign exchange produces a Raja Yoga condition"),
    ("Dasha", "9th–10th exchange", "Mutual sign exchange produces a Raja Yoga condition"),
]


def lordship_rows(asc: Sign) -> list[Row]:
    rows = []
    for planet in CLASSICAL:
        houses = sorted(whole_sign_house(sign, asc) for sign in SIGNS_IN_ORDER if RASHI_LORD[sign] == planet)
        owned = set(houses)
        good = sorted(owned & TRINES)
        bad = sorted(owned & ADVERSE)
        eighth_exception = 8 in owned and (1 in owned or planet in (Planet.SUN, Planet.MOON))
        eighth = 8 in owned and not eighth_exception
        angles = sorted(owned & KENDRAS)
        # Distinguish the six conventional standalone Yogakarakas from the
        # weaker Lagna+angle combinations, which are shown as Lagna support.
        yogakaraka = bool(owned & {5, 9} and owned & {4, 7, 10})
        notes = []
        if good:
            notes.append(f"Trine ownership: {', '.join('H'+str(h) for h in good)}.")
        if bad:
            notes.append(f"Adverse ownership: {', '.join('H'+str(h) for h in bad)}.")
        if eighth:
            notes.append("H8 adds an adverse lordship condition.")
        if eighth_exception:
            notes.append("H8 exception: " + ("also the Lagna lord." if 1 in owned else "Sun/Moon exception."))
        if angles and not good:
            notes.append("Kendra ownership modifies natural character; associations decide the result.")
        if owned & {2, 12}:
            notes.append("H2/H12 results depend on the other owned house and associations.")
        if yogakaraka:
            notes.append(f"{', '.join('H'+str(h) for h in angles)} Kendra + {', '.join('H'+str(h) for h in good)} trine: one lord satisfies both roles.")
            role, tone = "Yogakaraka", "yoga"
        elif good and (bad or eighth):
            role, tone = "Mixed", "mixed"
        elif good:
            role, tone = "Benefic support", "good"
        elif bad or eighth:
            role, tone = "Malefic tendency", "bad"
        else:
            role, tone = "Conditional", "mixed"
        rows.append({"planet": planet.value, "houses": houses, "role": role, "tone": tone,
                     "trines": good, "adverse": bad + ([8] if eighth else []), "kendras": angles,
                     "maraka_houses": sorted(owned & {2, 7}), "yogakaraka": yogakaraka,
                     "eighth_exception": eighth_exception, "calculation": " ".join(notes)})
    return rows


def _reaches(source, target) -> bool:
    return whole_sign_house(target.sign, source.sign) in ASPECT_OFFSETS.get(source.planet, [])


def relationship(a, b) -> list[str]:
    if a.planet == b.planet:
        return []
    links = []
    if a.sign == b.sign:
        links.append("Conjunction")
    if _reaches(a, b) and _reaches(b, a):
        links.append("Mutual aspect")
    if RASHI_LORD[a.sign] == b.planet and RASHI_LORD[b.sign] == a.planet:
        links.append("Sign exchange")
    return links


def period_reading(major: str, minor: str, roles: dict[str, Row], positions: dict[Planet, Any]) -> Row:
    a, b = roles[major], roles[minor]
    links = relationship(positions[Planet(major)], positions[Planet(minor)])
    rule_ids, notes = [29, 30, 31], []
    same = major == minor
    related = bool(links)
    if same:
        tone, result = "mixed", "Own-lord period: judge its ownership and placement together."
    elif {major, minor} == {"Saturn", "Venus"}:
        tone, result = "mixed", "Saturn–Venus exception: a fixed favorable/unfavorable verdict is not applied."
        rule_ids.append(40)
    elif a["tone"] == "bad" and b["tone"] in ("good", "yoga"):
        tone = "mixed" if related else "bad"
        result = "Mixed support: the benefic is connected to the adverse major lord." if related else "Challenging tendency: the supportive subperiod lord has no direct relationship to the adverse major lord."
        rule_ids.extend([37, 38])
    elif related and ((a["kendras"] and b["trines"]) or (b["kendras"] and a["trines"])):
        tone, result = "good", "Supportive Kendra–trine connection in this period pair."
        rule_ids.append(32)
        if a["adverse"] or b["adverse"]:
            tone, result = "mixed", "Kendra–trine support with additional adverse ownership: mixed tendency."
    elif a["tone"] in ("good", "yoga") and b["tone"] in ("good", "yoga"):
        tone, result = "good", "Both lords carry supportive ownership; yoga delivery still needs the natal connection."
    elif a["tone"] == "bad" and b["tone"] == "bad":
        tone, result = "bad", "Both period lords carry adverse ownership: a challenging tendency."
    else:
        tone, result = "mixed", "Conditional or mixed ownership: weigh both lords and their natal links."
    if b["yogakaraka"] and related and a["tone"] == "good":
        rule_ids.append(35)
        notes.append("An associated benefic major lord activates a Yogakaraka subperiod condition.")
    if a["maraka_houses"] or b["maraka_houses"]:
        rule_ids.extend([33, 39])
        notes.append("A Maraka lordship is present; this is a technical role, not a lifespan prediction.")
    if major in ("Rahu", "Ketu") or minor in ("Rahu", "Ketu"):
        rule_ids.extend([13, 21, 36])
        tone, result = "mixed", "Node period: assess its house, sign lord, companions and the other period lord."
    for name in dict.fromkeys([major, minor]):
        p = positions[Planet(name)]
        notes.append(f"{name}: {p.sign.value}, H{roles[name]['natal_house']}; {p.dignity.value}" + ("; retrograde." if p.retrograde else "."))
    return {"major": major, "minor": minor, "tone": tone, "result": result,
            "relationship": links, "rules": sorted(set(rule_ids)), "notes": notes}


def build_laghu_report(chart: KundaliChart) -> Row:
    asc = chart.ascendant.sign
    positions = {p.planet: p for p in chart.planets}
    rows = lordship_rows(asc)
    for row in rows:
        p = positions[Planet(row["planet"])]
        row.update(sign=p.sign.value, natal_house=whole_sign_house(p.sign, asc), dignity=p.dignity.value, retrograde=p.retrograde)
    roles = {r["planet"]: r for r in rows}
    nodes = []
    for node in (Planet.RAHU, Planet.KETU):
        p = positions[node]
        lord = RASHI_LORD[p.sign]
        companions = [q.planet.value for q in chart.planets if q.planet != node and q.sign == p.sign]
        h = whole_sign_house(p.sign, asc)
        row = {"planet": node.value, "houses": [], "trines": [], "kendras": [], "adverse": [], "maraka_houses": [],
               "role": "Association-dependent", "tone": "mixed", "yogakaraka": False,
               "sign": p.sign.value, "natal_house": h, "dignity": p.dignity.value, "retrograde": p.retrograde,
               "lord": lord.value, "companions": companions,
               "yoga_association": h in KENDRAS | TRINES and any(roles.get(q, {}).get("kendras") or roles.get(q, {}).get("trines") for q in companions),
               "calculation": f"{p.sign.value} H{h}; dispositor {lord.value} ({roles[lord.value]['role']}); companions: {', '.join(companions) or 'none'}."}
        nodes.append(row)
        roles[node.value] = row
    house_rows = [{"house": h, "sign": SIGNS_IN_ORDER[(SIGNS_IN_ORDER.index(asc) + h - 1) % 12].value,
                   "lord": RASHI_LORD[SIGNS_IN_ORDER[(SIGNS_IN_ORDER.index(asc) + h - 1) % 12]].value} for h in range(1, 13)]
    connections = [{"planets": [a.value, b.value], "links": links}
                   for a, b in combinations(CLASSICAL, 2) if (links := relationship(positions[a], positions[b]))]
    yogas = []
    for pair in connections:
        a, b = (roles[name] for name in pair["planets"])
        if (a["kendras"] and b["trines"]) or (b["kendras"] and a["trines"]):
            yogas.append({**pair, "status": "Conditional" if a["adverse"] or b["adverse"] else "Formed",
                          "calculation": " · ".join(f"{r['planet']} owns {', '.join('H'+str(h) for h in r['houses'])}" for r in (a, b))})
    aspects = []
    for p in chart.planets:
        for offset in ASPECT_OFFSETS.get(p.planet, []):
            sign = SIGNS_IN_ORDER[(SIGNS_IN_ORDER.index(p.sign) + offset - 1) % 12]
            aspects.append({"planet": p.planet.value, "sign": p.sign.value, "house": whole_sign_house(p.sign, asc), "aspect": offset,
                            "target_sign": sign.value, "target_house": whole_sign_house(sign, asc),
                            "targets": [q.planet.value for q in chart.planets if q.sign == sign]})
    candidates = []
    maraka_lords = {Planet(house_rows[h-1]["lord"]) for h in (2, 7)}
    for p in chart.planets:
        r = roles[p.planet.value]
        reasons = [f"Lord of H{h}" for h in r["maraka_houses"]]
        if r["natal_house"] in (2, 7):
            reasons.append(f"Occupies H{r['natal_house']}")
        if p.planet in (Planet.SUN, Planet.MARS, Planet.SATURN):
            for lord in sorted(maraka_lords, key=lambda x: x.value):
                if lord != p.planet and p.sign == positions[lord].sign:
                    reasons.append(f"Natural malefic conjunct Maraka lord {lord.value}")
        if reasons:
            candidates.append({"planet": p.planet.value, "reasons": reasons})
    maraka_names = {r["planet"] for r in candidates}
    saturn_links = [n for n in sorted(maraka_names - {"Saturn"}) if relationship(positions[Planet.SATURN], positions[Planet(n)])]
    def exchange(h1, h2):
        x, y = house_rows[h1 - 1], house_rows[h2 - 1]
        return x["lord"] != y["lord"] and positions[Planet(x["lord"])].sign.value == y["sign"] and positions[Planet(y["lord"])].sign.value == x["sign"]
    dharma, karma = roles[house_rows[8]["lord"]], roles[house_rows[9]["lord"]]
    dharma_links = relationship(positions[Planet(dharma["planet"])], positions[Planet(karma["planet"])])
    dharma_overlap = 8 in dharma["houses"] or 11 in karma["houses"]
    rules = []
    for number, (group, name, condition) in enumerate(TOPICS, 1):
        status, calculation, result = "Context", "", "Interpret with the chart conditions."
        if number in (1, 2, 4):
            result = "Reading context; no numerical calculation."
        elif number == 3:
            first = chart.dasha.periods[0]
            moon = positions[Planet.MOON]
            width = 360 / 27
            balance = (1 - (moon.longitude % width) / width) * DASHA_YEARS[moon.nakshatra.lord]
            status, calculation, result = "Calculated", f"Moon: {moon.nakshatra.name}; nakshatra lord {moon.nakshatra.lord.value}. (1 − elapsed nakshatra fraction) × {DASHA_YEARS[moon.nakshatra.lord]:g} = {balance:.6f} dasha years remaining.", f"Birth-period balance: {first.start.isoformat()} → {first.end.isoformat()}."
        elif number == 5:
            status, result = "Calculated", f"{len(aspects)} sign-aspect destinations calculated; see Aspects below."
        elif number in (6, 7, 8, 9, 10, 11, 12, 13, 20, 23, 24, 28):
            status = "Calculated"
            applicable = {
                6: [r for r in rows if r["trines"] or r["adverse"]], 7: [r for r in rows if r["kendras"]],
                8: [r for r in rows if set(r["houses"]) & {2, 12}], 9: [r for r in rows if 8 in r["houses"]],
                10: [r for r in rows if r["planet"] in ("Jupiter", "Venus") and r["kendras"] and not r["trines"]],
                11: [r for r in rows if r["planet"] in ("Sun", "Moon", "Mercury") and (r["kendras"] or 8 in r["houses"])],
                12: [roles["Mars"]] if 10 in roles["Mars"]["houses"] else [], 13: nodes,
                20: [r for r in rows if r["yogakaraka"]],
            }.get(number, [])
            if number <= 20:
                calculation = " | ".join(f"{r['planet']}: {r['calculation']}" for r in applicable)
                result = ", ".join(f"{r['planet']} · {r['role']}" for r in applicable) or "No matching lordship in this chart."
            elif number == 23:
                calculation = " | ".join(f"H{h}: {house_rows[h-1]['sign']} · {house_rows[h-1]['lord']}" for h in (3, 8, 2, 7))
                result = "Longevity and Maraka house lords identified."
            elif number == 24:
                calculation = " | ".join(f"{r['planet']}: {', '.join(r['reasons'])}" for r in candidates)
                result = "Technical Maraka candidates; no lifespan interval is inferred."
            else:
                calculation = "Saturn direct connections: " + (", ".join(saturn_links) or "none")
                result = "Priority relationship found." if saturn_links else "No direct Saturn–candidate relationship."
        elif number in (14, 15, 17):
            status = "Formed" if yogas else "Not formed"
            calculation = " | ".join(" + ".join(y["planets"]) + ": " + ", ".join(y["links"]) + "; " + y["calculation"] for y in yogas)
            result = f"{len(yogas)} Kendra–trine relationships. Placement and strength qualify their delivery."
            if number == 17:
                status = "Conditional"
                result = "Relationships calculated. This text gives no numerical strength cutoff; consult Strengths for separate measurements."
        elif number in (16, 22):
            calculation = f"H9 lord {dharma['planet']}; H10 lord {karma['planet']}; links: {', '.join(dharma_links) or 'none'}; extra H8/H11 overlap: {'yes' if dharma_overlap else 'no'}."
            status = "Formed" if dharma_links and not dharma_overlap else "Conditional" if dharma_links else "Not formed"
            result = "Same planet owns H9 and H10; use the single Yogakaraka rule." if dharma["planet"] == karma["planet"] else "Judge the connection with the stated overlap limitation."
        elif number == 21:
            qualifying = [n["planet"] for n in nodes if n["yoga_association"]]
            status = "Conditional" if qualifying else "Not formed"
            calculation = " | ".join(n["calculation"] for n in nodes)
            result = "Node yoga association: " + (", ".join(qualifying) or "none")
        elif number in (25, 26, 27, 39):
            status, result = "Prerequisite", "The text's lifespan prerequisite is not established here. Maraka roles are calculated; a death date or lifespan is not calculated."
            calculation = "Candidate roles: " + ", ".join(sorted(maraka_names))
        elif number in (41, 42):
            h1, h2 = (1, 10) if number == 41 else (9, 10)
            formed = exchange(h1, h2)
            status, result = ("Formed", "Mutual sign exchange found.") if formed else ("Not formed", "No mutual sign exchange.")
            calculation = " | ".join(f"H{h} lord {house_rows[h-1]['lord']} → {positions[Planet(house_rows[h-1]['lord'])].sign.value}" for h in (h1, h2))
        else:
            status, result = "Period-dependent", "Select a mahadasha and antardasha to evaluate the period lords, roles and relationships."
        rules.append({"number": number, "group": group, "name": name, "condition": condition,
                      "status": status, "calculation": calculation, "result": result})
    periods = []
    for major in chart.dasha.periods:
        periods.append({"planet": major.planet.value, "start": major.start.isoformat(), "end": major.end.isoformat(),
                        "sub_periods": [{"planet": minor.planet.value, "start": minor.start.isoformat(), "end": minor.end.isoformat(),
                                         "reading": period_reading(major.planet.value, minor.planet.value, roles, positions)} for minor in major.sub_periods]})
    return {"ascendant": asc.value, "roles": rows, "nodes": nodes, "houses": house_rows,
            "all_ascendants": [{"ascendant": sign.value, "roles": lordship_rows(sign)} for sign in SIGNS_IN_ORDER],
            "aspects": aspects, "connections": connections, "yogas": yogas, "rules": rules,
            "maraka_candidates": candidates, "saturn_maraka_links": saturn_links, "periods": periods,
            "conventions": ["House ownership and aspects use D1 Whole Sign houses.",
                "Natural character, functional role, natal strength and Maraka role are separate conditions.",
                "Direct relationship means conjunction, mutual graha aspect, or mutual sign exchange.",
                "Lagna + another angle is shown as Lagna support; standalone Yogakaraka requires a 5th/9th and 4th/7th/10th lordship.",
                "Conditional rules remain conditional; there is no combined good/bad score."]}
