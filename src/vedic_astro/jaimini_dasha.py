"""Named sign-dasha conventions with exact local-civil period boundaries.

Each system declares its own start, sequence, duration and supported depth.
Do not silently reuse Vimshottari planetary weights for sign dashas.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from vedic_astro.aspects import SIGN_MODALITY, sign_aspects
from vedic_astro.dignity import DEBILITATION_SIGN, EXALTATION_SIGN
from vedic_astro.jaimini import DAYS_PER_YEAR, ODD_FOOTED, _sign_duration_years, chara_direction, compute_chara_dasha, step
from vedic_astro.models import KundaliChart, Planet, Sign, SIGNS_IN_ORDER
from vedic_astro.rashi_bhava import RASHI_LORD, whole_sign_house

Row = dict[str, Any]


def sequence(seed: Sign, direction: int = 1) -> list[Sign]:
    return [step(seed, direction * i) for i in range(12)]


def narayana_order(seed: Sign, saturn: bool = False, ketu: bool = False) -> list[Sign]:
    direction = chara_direction(seed)
    if saturn:
        return sequence(seed)
    if ketu:
        direction *= -1
    modality = SIGN_MODALITY[seed]
    if modality == "movable":
        return sequence(seed, direction)
    if modality == "fixed":
        return [step(seed, direction * 5 * i) for i in range(12)]
    return [step(seed, direction * (quadrant + trine)) for quadrant in (0, 9, 6, 3) for trine in (0, 4, 8)]


def build_dasha_systems(chart: KundaliChart, advanced: Row, lagnas: list[Row]) -> list[Row]:
    from vedic_astro.jaimini_report import primary_lord, stronger_sign
    planets, asc, birth = chart.planets, chart.ascendant.sign, chart.birth_data.local_datetime
    by = {p.planet: p for p in planets}
    seed = stronger_sign(asc, step(asc, 6), planets)

    def duration(sign: Sign) -> Row:
        lord = primary_lord(sign, planets, for_dasha=True)
        p = by[lord]
        base = _sign_duration_years(sign, p.sign)
        correction = 0 if p.sign == sign else 1 if EXALTATION_SIGN.get(lord) == p.sign else -1 if DEBILITATION_SIGN.get(lord) == p.sign else 0
        return {"sign": sign.value, "lord": lord.value, "lord_sign": p.sign.value, "years": base + correction,
                "rule": f"{'Forward' if sign in ODD_FOOTED else 'Backward'} sign-to-lord count − 1 = {base:g} years"
                + (" (own-sign exception: 12)" if p.sign == sign else "")
                + (f"; dignity adjustment {correction:+d}" if correction else "") + "."}

    lengths = {s: duration(s) for s in SIGNS_IN_ORDER}

    def narayana_children(parent: Sign) -> list[Sign]:
        ad_seed = stronger_sign(parent, step(parent, 6), planets)
        lord = primary_lord(ad_seed, planets, for_dasha=True)
        start = by[lord].sign
        direction = 1 if SIGNS_IN_ORDER.index(start) % 2 == 0 else -1
        if by[Planet.SATURN].sign == ad_seed:
            direction = 1
        elif by[Planet.KETU].sign == ad_seed:
            direction *= -1
        return sequence(start, direction)

    narayana_children_map = {s.value: [v.value for v in narayana_children(s)] for s in SIGNS_IN_ORDER}
    chara_children = {s.value: [step(s, chara_direction(s) * i).value for i in range(1, 13)] for s in SIGNS_IN_ORDER}
    shoola_children = {s.value: [v.value for v in sequence(stronger_sign(s, step(s, 6), planets))] for s in SIGNS_IN_ORDER}
    systems = []

    def add(code: str, name: str, method: str, order: list[Sign], years: list[float], calculations: list[str],
            children: dict[str, list[str]] | None = None, levels: int = 1, second_cycle: bool = False,
            unavailable: str | None = None) -> None:
        periods: list[Row] = []
        cursor = birth
        for cycle in range(2 if second_cycle else 1):
            for sign, original, rule in zip(order, years, calculations):
                value = 12 - original if cycle else original
                if value <= 0:
                    continue  # Zero duration is a transition, never a negative/fake period.
                end = cursor + timedelta(days=value * DAYS_PER_YEAR)
                periods.append({"sign": sign.value, "start": cursor.isoformat(), "end": end.isoformat(), "years": value,
                                "cycle": cycle + 1, "rule": rule if not cycle else f"Second cycle: 12 − {original:g} = {value:g} years."})
                cursor = end
        systems.append({"code": code, "name": name, "method": method, "year_days": DAYS_PER_YEAR,
                        "periods": periods, "max_levels": levels, "child_orders": children or {},
                        "unavailable": unavailable,
                        "duration_rows": [{"sign": s.value, "years": y, "rule": r} for s, y, r in zip(order, years, calculations)]})

    chara = compute_chara_dasha(asc, planets, birth)
    add("chara", "Chara Dasha", "K. N. Rao: start at Lagna; direction from its 9th sign. Classical seven lords; no dignity-year adjustment. Each child gets 1/12; the parent's sign is last. Repeat that order rule at each level.",
        [p.sign for p in chara], [p.years for p in chara],
        [f"{p.sign.value} → {by[p.lord].sign.value}, {'forward' if p.sign in ODD_FOOTED else 'backward'} count − 1; own sign = 12. {p.years:g} years." for p in chara],
        chara_children, levels=5)
    n_order = narayana_order(seed, by[Planet.SATURN].sign == seed, by[Planet.KETU].sign == seed)
    add("narayana", "Narayana Dasha", f"PVR convention: stronger Lagna/7th ({seed.value}); movable step 1, fixed step 6, dual trinal blocks; Saturn/Ketu sequence exceptions. Directed count − 1, own sign 12, otherwise dignity +1/−1. Second cycle is 12 minus first-cycle years. Equal antardashas start from the lord of the stronger parent/7th sign.",
        n_order, [lengths[s]["years"] for s in n_order], [lengths[s]["rule"] for s in n_order], narayana_children_map, 2, True)
    direction = 1 if SIGNS_IN_ORDER.index(asc) % 2 == 0 else -1
    if by[Planet.SATURN].sign == seed:
        direction = 1
    elif by[Planet.KETU].sign == seed:
        direction *= -1
    offsets = [i + q for i in range(3) for q in (0, 3, 6, 9)]
    k_order = [step(seed, direction * i) for i in offsets]
    add("kendradi", "Lagna Kendradi Rasi Dasha", f"Start from stronger Lagna/7th ({seed.value}). Direction uses Lagna odd/even parity with Saturn/Ketu exceptions. Cover kendras, panapharas, then apoklimas. Durations and antardashas follow Narayana.",
        k_order, [lengths[s]["years"] for s in k_order], [lengths[s]["rule"] for s in k_order], narayana_children_map, 2)
    sl = next(x for x in lagnas if x["code"] == "SL")
    sl_sign = Sign(sl["sign"])
    sl_direction = 1 if SIGNS_IN_ORDER.index(sl_sign) % 2 == 0 else -1
    sl_order = [step(sl_sign, sl_direction * i) for i in offsets]
    sl_years = [float(lengths[s]["years"]) for s in sl_order]
    sl_rules = [lengths[s]["rule"] for s in sl_order]
    balance = (30 - sl["degree"]) / 30
    sl_rules[0] += f" Birth remainder: {sl_years[0]:g} × (30 − {sl['degree']:.8f})/30 = {sl_years[0] * balance:.8f} years."
    sl_years[0] *= balance
    add("sudasha", "Sudasha", "Sree Lagna Kendradi: begin at Sree Lagna; odd/even direction. Kendras, panapharas, apoklimas. Narayana durations; first period is the remaining fraction (30 − Sree Lagna degree)/30. This worksheet displays major periods.", sl_order, sl_years, sl_rules)
    drig_order: list[Sign] = []
    for offset in (8, 9, 10):
        start = step(asc, offset)
        direction = 1 if start in ODD_FOOTED else -1
        targets = {start, *sign_aspects(start)}
        drig_order.extend(s for s in sequence(start, direction) if s in targets)
    add("drig", "Drig Dasha", "Start with the 9th sign and its three sign aspects, then the 10th and its aspects, then the 11th and its aspects. Each block follows odd-footed/even-footed direction. Narayana durations; major-period worksheet.",
        drig_order, [lengths[s]["years"] for s in drig_order], [lengths[s]["rule"] for s in drig_order])
    sh_order = sequence(seed)
    add("shoola", "Shoola Dasha", f"Stronger Lagna/7th ({seed.value}), then zodiacal order. Every sign receives 9 years. Each antardasha receives 1/12 and starts from the stronger parent sign/7th, proceeding zodiacally.",
        sh_order, [9.0] * 12, ["Fixed allocation: 9 years per sign."] * 12, shoola_children, 2)
    ny_seed = stronger_sign(step(asc, 1), step(asc, 7), planets)
    ny_order = sequence(ny_seed, 1 if SIGNS_IN_ORDER.index(ny_seed) % 2 == 0 else -1)
    modal_years = {"movable": 7.0, "fixed": 8.0, "dual": 9.0}
    add("niryana", "Niryana Shoola Dasha", f"Stronger 2nd/8th ({ny_seed.value}); odd sign forward, even backward. Movable/fixed/dual receive 7/8/9 years. Antardashas use PVR's stated Narayana subdivision convention.",
        ny_order, [modal_years[SIGN_MODALITY[s]] for s in ny_order], [f"{SIGN_MODALITY[s].title()} sign: {modal_years[SIGN_MODALITY[s]]:g} years." for s in ny_order], narayana_children_map, 2)
    # Suryanarayana Rao's classical translation: Navamsa begins at odd
    # Lagna itself; even Lagna uses its Abhimukha (8th/6th/7th by modality).
    nav_seed = asc if SIGNS_IN_ORDER.index(asc) % 2 == 0 else step(asc, {"movable": 7, "fixed": 5, "dual": 6}[SIGN_MODALITY[asc]])
    nav_order = sequence(nav_seed)
    add("navamsa", "Navamsa Dasha", f"Classical Abhimukha convention: odd Lagna starts at Lagna; even movable/fixed/dual Lagna starts at its 8th/6th/7th ({nav_seed.value}). Zodiacal major periods of 9 years. This is a sign dasha, distinct from the D9 chart.",
        nav_order, [9.0] * 12, ["Navamsa major period: 9 years."] * 12)
    brahma = Planet(advanced["brahma"]) if advanced["brahma"] else None
    b_seed = by[brahma].sign if brahma else None
    sth_order = sequence(b_seed) if b_seed else []
    add("sthira", "Sthira Dasha", "Classical Brahma-seeded convention: begin at Brahma's occupied sign and proceed zodiacally; movable/fixed/dual signs receive 7/8/9 years. Major periods only.",
        sth_order, [modal_years[SIGN_MODALITY[s]] for s in sth_order], [f"{SIGN_MODALITY[s].title()} sign: {modal_years[SIGN_MODALITY[s]]:g} years." for s in sth_order],
        unavailable=None if brahma else "No eligible Brahma under the displayed classical rule; a starting sign cannot be forced.")
    b_start = (b_seed if SIGNS_IN_ORDER.index(asc) % 2 == 0 else step(b_seed, 6)) if b_seed else None
    b_order = sequence(b_start) if b_start else []
    b_years, b_rules = [], []
    for s in b_order:
        sixth = step(s, 5)
        lord = primary_lord(sixth, planets)
        years = float(whole_sign_house(by[lord].sign, s))
        b_years.append(years)
        b_rules.append(f"6th sign {sixth.value}, lord {lord.value} in {by[lord].sign.value}; inclusive zodiacal house count from {s.value} = {years:g}.")
    add("brahma", "Brahma Dasha", "Suryanarayana Rao's sixth-lord worksheet: odd natal Lagna starts from Brahma's sign; even Lagna starts from its opposite. Proceed zodiacally. Duration is the inclusive house occupied by the sixth-sign lord from each dasha sign. Major periods only; this convention differs from Grahashrita count-minus-one versions.",
        b_order, b_years, b_rules, unavailable=None if brahma else "No eligible Brahma under this convention; see Advanced for the candidate calculation.")
    # K. N. Rao quadrant Mandooka: cover seed quadrants, then the other
    # modality groups anchored at Aries/Gemini/Taurus. Independently derive
    # the groups rather than importing a third-party program or order table.
    modality = SIGN_MODALITY[seed]
    group_order = {"movable": [0, 2, 1], "dual": [2, 1, 0], "fixed": [1, 0, 2]}[modality]
    m_direction = 1 if SIGNS_IN_ORDER.index(seed) % 2 == 0 else -1
    m_order = [step(seed if i == 0 else SIGNS_IN_ORDER[group], m_direction * q)
               for i, group in enumerate(group_order) for q in (0, 3, 6, 9)]
    m_years, m_rules = [], []
    for s in m_order:
        lord_sign = by[RASHI_LORD[s]].sign
        parity_direction = 1 if SIGNS_IN_ORDER.index(s) % 2 == 0 else -1
        count = ((SIGNS_IN_ORDER.index(lord_sign) - SIGNS_IN_ORDER.index(s)) * parity_direction) % 12 + 1
        years = 12 if lord_sign == s else 10 if lord_sign == step(s, 6) else count
        m_years.append(float(years))
        m_rules.append(f"Inclusive {'forward' if parity_direction == 1 else 'backward'} parity count to classical lord in {lord_sign.value}; own sign 12, opposite lord 10: {years} years.")
    add("mandooka", "Mandooka Dasha", f"K. N. Rao quadrant convention: stronger Lagna/7th ({seed.value}); seed quadrants followed by remaining modality groups. Odd seed forward, even seed backward. Inclusive parity-based lord count with own/opposite exceptions. Major-period worksheet.", m_order, m_years, m_rules)
    return systems


def subdivide_period(system: Row, sign: Sign, start: datetime, end: datetime) -> list[Row]:
    order = system["child_orders"].get(sign.value)
    if not order:
        raise ValueError("This declared dasha convention exposes major periods only.")
    span = end - start
    return [{"sign": s, "start": (start + span * (i / 12)).isoformat(),
             "end": (end if i == 11 else start + span * ((i + 1) / 12)).isoformat(),
             "years": span.total_seconds() / (DAYS_PER_YEAR * 86400 * 12), "cycle": 1,
             "rule": f"Parent duration ÷ 12. Child {i + 1}/12 in the {system['name']} sequence."}
            for i, s in enumerate(order)]
