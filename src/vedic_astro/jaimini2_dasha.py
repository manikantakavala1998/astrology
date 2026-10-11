"""The book's 38-entry catalog; no rules imported from the KN Rao engine."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from vedic_astro.divisional_charts import drekkana_sign
from vedic_astro.jaimini2 import (PADAKRAMA_EIGHTH, TYPE_RANK, exalted, lord, parity,
                                passed, planet_key, sign_key, step, strongest)
from vedic_astro.aspects import SIGN_MODALITY, sign_aspects
from vedic_astro.models import KundaliChart, Planet, PlanetPosition, Sign, SIGNS_IN_ORDER
from vedic_astro.rashi_bhava import RASHI_LORD, sign_for_longitude
from vedic_astro.varga import navamsa_sign

Row = dict[str, Any]
YEAR_DAYS = 360
CATALOG = [
    ("hora", "Hora Dasa"), ("darpana", "Darpana Dasa"), ("nirayana-shoola", "Nirayana Shoola Dasa"),
    ("maheshwara", "Maheshwara Dasa"), ("brahma", "Brahma Dasa"), ("atma-naadi", "Atma Naadi Dasa"),
    ("varnada", "Varnada Dasa"), ("chara-paryaaya", "Chara Paryaaya Dasa"),
    ("atmano-bhavapamsha", "Atmano Bhavapamsha Dasa"), ("jayabhavapa", "Jayabhavapa Dasa"),
    ("drekkana", "Drekkana Dasa"), ("navamsa", "Navamsa Dasa"), ("drig", "Drig Dasa"),
    ("yogartha", "Yogartha Dasa"), ("sthira", "Sthira Dasa"), ("chara", "Chara Dasa"),
    ("kendradi", "Lagna Kendradi Dasa"), ("mandooka", "Mandooka Dasa"),
    ("padanadhamsa", "Padanadhamsa Dasa"), ("trikona", "Trikona Dasa"),
    ("nakshatra-bheda1", "Nakshatra Bheda Dasa I"), ("chandraamsaka", "Chandraamsaka Dasa"),
    ("kheta", "Kheta Dasa"), ("nisarga", "Nisarga Dasa"), ("sampath", "Sampath Dasa"),
    ("thaara", "Thaara Dasa"), ("sthira-paryaaya", "Sthira Paryaaya Dasa"), ("shoola", "Shoola Dasa"),
    ("nakshatra-bheda2", "Nakshatra Bheda Dasa II"), ("upakrama", "Upakrama Dasa"),
    ("nisarga-bheda", "Nisarga Bheda Dasa"), ("keeta", "Keeta Dasa"),
    ("nakshatra3", "Nakshatra Dasa III"), ("shashtashtama", "Shashtashtama Dasa"),
    ("brahma-daasa", "Brahma Daasa"), ("gochara", "Gochara Dasa"),
    ("niryana-chandra", "Niryana Chandra Dasa"), ("bhavapamsha", "Bhavapamsha Dasa"),
]


def sequence(seed: Sign, direction: int | None = None) -> list[Sign]:
    return [step(seed, (parity(seed) if direction is None else direction) * i) for i in range(12)]


def padakrama(seed: Sign) -> list[Sign]:
    kind = SIGN_MODALITY[seed]
    offsets = list(range(12)) if kind == "movable" else [5 * i for i in range(12)] if kind == "fixed" else [
        0, 3, 6, 9, 1, 4, 7, 10, 2, 5, 8, 11]
    return [step(seed, parity(seed) * i) for i in offsets]


def drig_order(seed: Sign) -> list[Sign]:
    # Each trinal block has its own parity, as the Libra → Scorpio example
    # demonstrates: Scorpio is followed by Cancer, then Pisces.
    groups = [step(seed, parity(seed) * i) for i in range(4)]
    return [step(group, parity(group) * offset) for group in groups for offset in (0, 4, 8)]


def duration(sign: Sign, planets: list[PlanetPosition], inverse: bool = False) -> tuple[float, str]:
    by = {p.planet: p for p in planets}
    owner = lord(sign, planets)
    first, second = (by[owner].sign, sign) if inverse else (sign, by[owner].sign)
    years = passed(first, second, parity(sign)) or 12
    return float(years), (f"{owner.value}: {first.value} → {second.value}, "
                         f"{'forward' if parity(sign) == 1 else 'backward'}; signs passed = {years}. "
                         + ("Own sign uses twelve years." if first == second else "Inclusive count minus one."))


def modal_duration(sign: Sign) -> tuple[float, str]:
    years = TYPE_RANK[SIGN_MODALITY[sign]] + 7
    return float(years), f"{SIGN_MODALITY[sign].title()} sign: {years} years."


def d9_positions(planets: list[PlanetPosition]) -> list[PlanetPosition]:
    return [p.model_copy(update={"sign": navamsa_sign(p.longitude), "degree_in_sign": p.longitude * 9 % 30,
                                "longitude": SIGNS_IN_ORDER.index(navamsa_sign(p.longitude)) * 30 + p.longitude * 9 % 30})
            for p in planets]


def kendradi(seed: Sign, planets: list[PlanetPosition]) -> list[Sign]:
    order: list[Sign] = []
    for group in range(3):
        signs = [step(seed, parity(seed) * (group + offset)) for offset in (0, 3, 6, 9)]
        group_seed = seed if group == 0 else strongest(signs, planets)
        order.extend(step(group_seed, parity(group_seed) * offset) for offset in (0, 3, 6, 9))
    return order


def enable_subdivisions(systems: list[Row], planets: list[PlanetPosition]) -> None:
    """Auditable three-level explorer with explicitly declared child ordering.

    The book's duration table establishes /12, then /12. It does not define
    a complete child seed for every catalog method. Those orders are labelled
    application conventions, not attributed to the author or borrowed from KN.
    """
    for system in systems:
        system["subdivision_rule"] = ""
        system["subdivision_status"] = "Unavailable without major periods."
        if not system["periods"]:
            continue
        if system["code"] == "nisarga":
            system["subdivision_status"] = "The book lists seven planetary antars but also division by twelve; this unresolved allocation is not replaced with twelve sign periods."
            continue
        system["max_levels"] = 3
        for parent in SIGNS_IN_ORDER:
            code = system["code"]
            if code in ("navamsa", "sthira", "shoola", "bhavapamsha"):
                order = sequence(parent, 1)
                description = "parent sign followed by the forward zodiac"
            elif code in ("trikona", "gochara"):
                order = padakrama(parent)
                description = "parent sign followed by its modality/parity Padakrama sequence"
            elif code == "drig":
                order = drig_order(parent)
                description = "parent sign followed by parity-controlled trinal blocks"
            elif code == "kendradi":
                order = kendradi(parent, planets)
                description = "parent sign followed by the kendra/panaphara/apoklima groups"
            elif code == "sampath":
                order = padakrama(parent)
                description = "parent sign followed by the Drekkana/modality sequence (the chapter's first antar variant)"
            elif code == "chandraamsaka":
                order = [step(parent, parity(parent) * o) for o in (0, 3, 6, 9, 1, 4, 7, 10, 2, 5, 8, 11)]
                description = "parent sign followed by parity-controlled kendra/panaphara/apoklima groups"
            else:
                order = sequence(parent)
                description = "parent sign followed by odd-sign forward / even-sign backward zodiac order"
            system["child_orders"][parent.value] = [s.value for s in order]
            system["subdivision_rule"] = "Twelve equal sign periods: parent duration ÷ 12 for Antardasha, then Antar duration ÷ 12 for Pratyantardasha. Child order starts at the " + description + ". Exact parent endpoint is preserved."
        system["subdivision_status"] = "Explorer convention: the book supplies the equal-duration scale, but does not fully specify a unique child seed/order for this method. The displayed order is a declared application convention using this engine's sign rules."


def subdivide_book_period(system: Row, parent: Row) -> list[Row]:
    if system["max_levels"] < 2:
        return []
    start, end = datetime.fromisoformat(parent["start"]), datetime.fromisoformat(parent["end"])
    order = system["child_orders"][parent["sign"]]
    span = end - start
    rows = []
    for i, sign in enumerate(order):
        a = start + span * (i / 12)
        b = end if i == 11 else start + span * ((i + 1) / 12)
        rows.append({"sign": sign, "start": a.isoformat(timespec="microseconds"),
                     "end": b.isoformat(timespec="microseconds"),
                     "years": (b - a).total_seconds() / (YEAR_DAYS * 86400), "cycle": 1,
                     "rule": f"{parent['sign']} duration {(end - start).total_seconds():.6f} seconds ÷ 12; part {i + 1}. " + system["subdivision_rule"]})
    return rows


def build_catalog(chart: KundaliChart, ks: list[Row], advanced: Row, padas: list[Row]) -> list[Row]:
    planets = chart.planets
    by = {p.planet: p for p in planets}
    asc = chart.ascendant.sign
    opposite = strongest([asc, step(asc, 6)], planets)
    tri_seed = strongest([step(asc, h) for h in (0, 4, 8)], planets)
    chara_seed = strongest([asc, step(asc, 3)], planets)
    moon = by[Planet.MOON]
    ak = by[Planet(ks[0]["planet"])]
    p9 = d9_positions(planets)
    asc9 = navamsa_sign(chart.ascendant.longitude)
    nav_seed = asc9 if parity(asc9) == 1 else step(asc9, 6)
    eighth = PADAKRAMA_EIGHTH[SIGNS_IN_ORDER.index(asc)]
    eighth_owner = by[lord(eighth, planets)]
    rows: dict[str, Row] = {}
    for number, (code, name) in enumerate(CATALOG, 1):
        rows[code] = {"code": code, "name": name, "book_number": number, "method": "",
                      "year_days": YEAR_DAYS, "periods": [], "max_levels": 1, "child_orders": {},
                      "unavailable": None, "duration_rows": [], "basis": "D1", "worksheet": []}

    def hold(code: str, method: str, reason: str, worksheet: list[Row] | None = None) -> None:
        rows[code].update(method=method, unavailable=reason, worksheet=worksheet or [])

    def fill(code: str, order: list[Sign], values: list[tuple[float, str]], method: str, basis: str = "D1") -> None:
        system = rows[code]
        system.update(method=method, basis=basis)
        cursor = chart.birth_data.local_datetime
        for sign, (years, rule) in zip(order, values):
            end = cursor + timedelta(days=years * YEAR_DAYS)
            system["periods"].append({"sign": sign.value, "start": cursor.isoformat(timespec="seconds"),
                                      "end": end.isoformat(timespec="seconds"), "years": years, "cycle": 1, "rule": rule})
            system["duration_rows"].append({"sign": sign.value, "years": years, "rule": rule})
            cursor = end

    def worksheet(**items: Any) -> list[Row]:
        return [{"factor": key.replace("_", " ").title(), "value": str(value)} for key, value in items.items()]

    order = sequence(asc)
    fill("atma-naadi", order, [duration(s, planets) for s in order],
         f"Seed is natal Lagna {asc.value}; odd signs forward, even backward. Sign-to-lord Naada durations. One cycle from birth.")
    order = sequence(eighth_owner.sign)
    fill("jayabhavapa", order, [duration(s, planets) for s in order],
         f"Padakrama eighth of {asc.value} is {eighth.value}; its lord {eighth_owner.planet.value} occupies {eighth_owner.sign.value}. Start there; parity sequence and sign-to-lord durations.")
    order = sequence(nav_seed, 1)
    fill("navamsa", order, [duration(s, p9) for s in order],
         f"Dedicated D9 chapter convention: D9 Lagna {asc9.value}; odd starts itself, even starts opposite {nav_seed.value}; all sequences forward. Durations use D9 sign/lord placements and sign parity. Other summary variants are not substituted.", "D9")
    seed = step(asc, 8)
    order = drig_order(seed)
    fill("drig", order, [modal_duration(s) for s in order],
         f"Start ninth from Lagna ({seed.value}); trinal blocks follow the seed's parity, and trines within each block follow that block's own parity. Movable/fixed/dual: 7/8/9 years (the prose allocation, even where the example table differs).")
    if advanced["brahma"]:
        seed = by[Planet(advanced["brahma"])].sign
        order = sequence(seed, 1)
        fill("sthira", order, [modal_duration(s) for s in order],
             f"Seed is Brahma's occupied sign {seed.value}. Brahma is selected using the preceding-odd-sign variant shown in Advanced. Forward sequence; movable/fixed/dual 7/8/9 years.")
    else:
        hold("sthira", "Brahma seed, forward sequence, modal 7/8/9 years.", "No Brahma candidate under the selected preceding-odd-sign variant.")
    order = sequence(chara_seed)
    fill("chara", order, [duration(s, planets, inverse=True) for s in order],
         f"Book chapter convention: compare Lagna {asc.value} with fourth {step(asc, 3).value}; seed {chara_seed.value}. Seed parity controls sequence. Duration counts from lord to sign using sign parity; no ninth-house direction or dignity-year adjustment is added.")
    order = kendradi(opposite, planets)
    fill("kendradi", order, [duration(s, planets, inverse=True) for s in order],
         f"Stronger Lagna/seventh ({opposite.value}); quadrants, then panapharas, then apoklimas. Each later group starts at its strongest sign. Dedicated chapter uses Chara durations; the summary's modal allocation is not used.")
    karaka_seed = strongest([step(ak.sign, n) for n in (0, 3, 6, 9)], planets)
    rows["kendradi"]["worksheet"] = worksheet(karaka_kendradi_seed=karaka_seed.value,
                                                       karaka_kendradi_order=" → ".join(s.value for s in kendradi(karaka_seed, planets)))
    order = padakrama(tri_seed)
    fill("trikona", order, [duration(s, planets) for s in order],
         f"Strongest natal Lagna/fifth/ninth ({tri_seed.value}); movable sequential, fixed sixth-step, dual kendra/panaphara/apoklima order; seed parity reverses offsets. Sign-to-lord durations.")
    seed = navamsa_sign(moon.longitude)
    order = [step(seed, parity(seed) * o) for o in (0, 3, 6, 9, 1, 4, 7, 10, 2, 5, 8, 11)]
    fill("chandraamsaka", order, [(9., "Fixed nine-year allocation.") for _ in order],
         f"Moon's D9 sign ({seed.value}); kendra/panaphara/apoklima order with seed parity. Fixed nine years per sign.", "D9")
    conditions = [(Planet.SATURN, Planet.VENUS), (Planet.KETU, Planet.MARS)]
    eligible = any(by[a].sign == by[b].sign for a, b in conditions)
    exchange = [p for p in planets if p.planet not in (Planet.MARS, Planet.RAHU, Planet.KETU)
                and by[Planet.KETU].sign == p.sign and RASHI_LORD[p.sign] == Planet.MARS
                and RASHI_LORD[by[Planet.MARS].sign] == p.planet]
    eligible = eligible or bool(exchange)
    if eligible:
        seed = strongest([asc, step(asc, 6), ak.sign], planets)
        order = sequence(seed)
        years_by_lord = {Planet.MOON: 1, Planet.MARS: 2, Planet.MERCURY: 9, Planet.VENUS: 20,
                         Planet.JUPITER: 18, Planet.SUN: 20, Planet.SATURN: 50}
        fill("nisarga", order, [(float(years_by_lord[RASHI_LORD[s]]), f"{RASHI_LORD[s].value} natural allocation: {years_by_lord[RASHI_LORD[s]]} years.") for s in order],
             "Required Saturn–Venus / Ketu–Mars conjunction or Ketu with a planet exchanging signs with Mars is present. Strongest Lagna/seventh/AK seed; parity sequence. Classical sign-lord allocations; this book's Sun allocation is 20 years.")
    else:
        hold("nisarga", "Conditional method with natural sign-lord allocations.",
             "Not applicable to these inputs: no Saturn–Venus or Ketu–Mars conjunction, and no qualifying Ketu/Mars sign exchange.",
             worksheet(saturn=by[Planet.SATURN].sign.value, venus=by[Planet.VENUS].sign.value,
                       ketu=by[Planet.KETU].sign.value, mars=by[Planet.MARS].sign.value))
    laglord = by[lord(asc, planets)]
    sevenlord = by[lord(step(asc, 6), planets)]
    total = (laglord.longitude + sevenlord.longitude) % 360
    candidate = sign_for_longitude(total)
    seed = strongest([candidate, by[lord(candidate, planets)].sign], planets)
    order = sequence(seed)
    fill("sampath", order, [duration(s, planets) for s in order],
         f"Lagna/seventh lords' full longitudes: {laglord.longitude:.8f} + {sevenlord.longitude:.8f}, mod 360 = {total:.8f}° ({candidate.value}). Compare with that sign lord's occupied sign; seed {seed.value}. Parity sequence; sign-to-lord durations.")
    order = sequence(opposite, 1)
    fill("shoola", order, [(9., "Fixed nine-year allocation.") for _ in order],
         f"Stronger Lagna/seventh ({opposite.value}); forward sequence for all seeds, nine years each.")
    # These allocations are explicitly proposals in the book, labelled as such.
    direction = -1 if by[Planet.RAHU].sign == asc else 1
    sorted_planets = sorted(planets, key=lambda p: (passed(asc, p.sign, direction), p.degree_in_sign))
    order = [p.sign for p in sorted_planets]
    fill("keeta", order, [modal_duration(s) for s in order],
         "Author's proposed 7/8/9-year allocation. Visit nine planets around Lagna; forward except Rahu in Lagna reverses. Co-located planets retain separate periods, ordered by natal degree as a declared tie convention.")
    d3lag = drekkana_sign(chart.ascendant.longitude)
    d3owner = by[lord(d3lag, planets)]
    yogadas = [p.sign for p in planets if sum(lag in sign_aspects(ps) for ps, lag in zip(
        (p.sign, drekkana_sign(p.longitude), navamsa_sign(p.longitude)),
        (asc, d3lag, asc9))) >= 2]
    seed = strongest([d3lag, d3owner.sign, *yogadas, moon.sign], planets)
    order = sequence(seed)
    fill("nakshatra3", order, [modal_duration(s) for s in order],
         f"Author's proposed 7/8/9-year allocation. Strongest D3 Lagna, its lord's natal sign, Yogada signs and Moon sign → {seed.value}. Parity sequence; chapter's proposal is explicit rather than an established duration formula.")
    order = sequence(eighth_owner.sign)
    fill("shashtashtama", order, [duration(s, planets) for s in order],
         "First variant: identical to the book's Jayabhavapa method. Second variant's Moon/node seed overrides need a separate precedence rule and are not combined here.")
    order = padakrama(tri_seed)
    fill("gochara", order, [duration(s, planets) for s in order],
         "The chapter names this Trikona; this is its Trikona timeline alias. Transit positions are not added to natal predictions. Paaka/Bhoga worksheets follow the selected period sign.")
    rows["gochara"]["worksheet"] = [{"factor": f"{s.value} · Paaka / Bhoga", "value":
                                                f"{s.value} / {step(s, passed(tri_seed, s, 1)).value}"} for s in order]
    order = sequence(moon.sign)
    fill("niryana-chandra", order, [(9. + (9. if any(p.sign == s and exalted(p) for p in planets) else 0.),
                                    "Nine years + nine if an exalted planet occupies this sign (book's node exaltations included).") for s in order],
         f"Start natal Moon sign {moon.sign.value}; parity sequence. Nine years, extended to eighteen for an exalted occupant. The separate lifespan-extension statement is not added to a second period.")
    seed = navamsa_sign(by[lord(ak.sign, planets)].longitude)
    if moon.sign == step(asc, 7):
        hold("bhavapamsha", "Later-body/summary variant: AK's D1 dispositor's D9 sign; forward nine years each.",
             "Moon occupies the eighth: the alternate seed statement does not specify whether to use its D1 or D9 sign.", worksheet(ordinary_seed=seed.value))
    else:
        order = sequence(seed, 1)
        fill("bhavapamsha", order, [(9., "Fixed nine-year allocation.") for _ in order],
             f"Later-body/summary convention: D9 sign of AK's D1 dispositor ({seed.value}); forward sequence, nine years. Earlier eighth-lord wording is a different variant.", "D9")

    hold("hora", "Three-pair conditions and Graha Chakra seed worksheet.",
         "The chapter does not supply a complete major-period duration formula; Hora Lagna alone cannot determine dates.",
         worksheet(hora_lagna=advanced["longevity_pairs"][2]["second"], lagna_lord=laglord.planet.value))
    abhi = step(asc, {"movable": 7, "fixed": 5, "dual": 6}[SIGN_MODALITY[asc]])
    hold("darpana", "Odd Lagna seed itself; even Lagna Abhimukha seed; nine-year periods.",
         "The prose's sequential order conflicts with its fixed-sign worked example's sixth-step order. Choose an explicit variant before dating it.",
         worksheet(prose_seed=(asc if parity(asc) == 1 else abhi).value))
    hold("nirayana-shoola", "Strong Lagna/seventh seed with chapter-specific exceptions.",
         "The available chapter gives strength and Rudra conditions without a complete unambiguous duration allocation.", worksheet(seed=opposite.value))
    hold("maheshwara", "Maheshwara candidates are calculated in Advanced.",
         "Multiple Maheshwara selection variants are described; the complete period-duration rule is missing.", worksheet(candidate=advanced["maheswara"]))
    hold("brahma", "Brahma candidates are calculated in Advanced.",
         "Several Brahma definitions and starting-sign statements differ. The book does not settle a complete major-period formula for this entry.", worksheet(candidate=advanced["brahma"]))
    hold("varnada", "Stronger Lagna/Hora seed, with Varnada and node exceptions.",
         "The Varnada construction and override precedence are not fully defined in this chapter; no alternate software formula is substituted.")
    hold("chara-paryaaya", "Trinal seed with Padakrama ordering and Graha Chakra lords.",
         "The mapping of nine Graha Chakra planets to twelve sign lords and count direction are not fully consistent with the worked example.",
         worksheet(seed=tri_seed.value, sign_order=" → ".join(s.value for s in padakrama(tri_seed))))
    hold("atmano-bhavapamsha", "AK and eighth-lord Navamsa conditions.",
         "The example calls the same eighth-lord Navamsa both Aries and Taurus; the resulting seed and duration list disagree.", worksheet(eighth_lord=eighth_owner.planet.value, eighth_lord_d9=navamsa_sign(eighth_owner.longitude).value))
    hold("drekkana", "Seed is D3 sign of the seventh lord; modality Padakrama sequence.",
         "The chapter does not provide the period-duration allocation.", worksheet(seed=drekkana_sign(sevenlord.longitude).value))
    sthira_first = rows["sthira"]["periods"]
    yogartha_first = (rows["chara"]["periods"][0]["years"] + sthira_first[0]["years"]) / 2 if sthira_first else None
    hold("yogartha", "Average the opening Chara and Sthira durations.",
         "Only the opening-period average is described; the book delegates subsequent durations and variants to software.", worksheet(first_period_years=yogartha_first))
    hold("mandooka", "Strong Lagna/seventh seed and movable/fixed/dual jumps.",
         "The dedicated chapter omits a duration allocation; the mentioned KN Rao modifications are excluded.", worksheet(seed=opposite.value))
    al = Sign(padas[0]["sign"])
    hold("padanadhamsa", "D9 sign of the natal Arudha Lagna lord is the seed.",
         "The chapter gives a seed and reading basis but no complete major-period duration rule.", worksheet(seed=navamsa_sign(by[lord(al, planets)].longitude).value))
    hold("nakshatra-bheda1", "Upadasa and Graha Chakra-lord variant.",
         "The Upadasa construction and nine-planet/twelve-sign lord mapping are unspecified.")
    kheta_seed = max([sevenlord, eighth_owner], key=lambda p: planet_key(p, planets))
    hold("kheta", "Select the stronger seventh/eighth significator and divide longitude by an allocation.",
         "The years used as the divisor and the full sequence allocation are not specified.", worksheet(candidate=kheta_seed.planet.value, longitude=kheta_seed.longitude))
    hold("thaara", "Ten temporal portions of the birth nakshatra select a Lagna-relative seed; nine-year periods.",
         "The worked example uses AK parity, while the prose describes seed parity. Dates need that sequence convention resolved; the tenth must use elapsed nakshatra time, not a substituted angle fraction.")
    male_order = [step(opposite, parity(opposite) * o) for o in (0, 6, 1, 7, 2, 8, 3, 9, 4, 10, 5, 11)]
    female_seed = strongest([step(asc, 3), step(asc, 6)], planets)
    hold("sthira-paryaaya", "Separate male and female chart conventions.",
         "The major-period durations are not specified. Both seed/order worksheets are shown; gender is not inferred from the name.",
         worksheet(male_seed=opposite.value, male_order=" → ".join(s.value for s in male_order),
                   female_seed=female_seed.value, female_order=" → ".join(s.value for s in sequence(female_seed, -parity(female_seed)))))
    d3lord = by[lord(d3lag, planets)]
    nak_total = (moon.longitude + sevenlord.longitude + d3lord.longitude) % 360
    nak_lords = [Planet.KETU, Planet.VENUS, Planet.SUN, Planet.MOON, Planet.MARS, Planet.RAHU, Planet.JUPITER, Planet.SATURN, Planet.MERCURY]
    nak_owner = nak_lords[int(nak_total / (360 / 27)) % 9]
    hold("nakshatra-bheda2", "Sum Moon, seventh-lord and D3-Lagna-lord longitudes; find the resulting nakshatra lord.",
         "Seed can be computed, but the subsequent Upadasa duration/sequence formula is missing.",
         worksheet(sum_mod_360=f"{nak_total:.8f}°", nakshatra_lord=nak_owner.value, seed=by[nak_owner].sign.value))
    hold("upakrama", "D3 Dharesha seed and a longitude/three calculation.",
         "Dharesha identity, degree units and the subsequent planet sequence are not fully specified.")
    hold("nisarga-bheda", "Lagna/seventh lords' degree and sign-number arithmetic.",
         "The body and summary disagree on the multiplication and conversion to years/days.",
         worksheet(lagna_lord_degree=laglord.degree_in_sign, seventh_lord_degree=sevenlord.degree_in_sign))
    hold("brahma-daasa", "Male-chart Parshni/Brahma convention.",
         "The prose starts from Brahma while the summary starts from Parshni. The planet identity/sequence and gender-dependent application need an explicit resolved variant.", worksheet(brahma=advanced["brahma"]))
    systems = list(rows.values())
    enable_subdivisions(systems, planets)
    return systems
