"""Calculation traces for the Balas workspace, using the existing scoring engine.

Scores are never inferred from rounded UI values. This report keeps the engine's
units, house conventions and scope limitations visible alongside each trace.
"""
from __future__ import annotations

from datetime import timedelta
from math import ceil, floor
from typing import Any

from vedic_astro import bhava_bala as bb, shadbala as sb, vimshopaka_bala as vb
from vedic_astro.dignity import DEEP_DIGNITY_DEGREE, EXALTATION_SIGN
from vedic_astro.divisional_charts import VARGA_REGISTRY
from vedic_astro.ephemeris import ayanamsha_value, declination_degrees, mean_obliquity_degrees, sunrise_sunset
from vedic_astro.hora import hora_interval
from vedic_astro.models import KundaliChart, Planet, Sign
from vedic_astro.planetary_relations import panchadha_relation
from vedic_astro.rashi_bhava import RASHI_LORD, degree_in_sign, sign_for_longitude, whole_sign_house

Report = dict[str, Any]
CLASSICAL = [Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY, Planet.JUPITER, Planet.VENUS, Planet.SATURN]
VARGA_NAMES = {spec.code: spec.name for spec in VARGA_REGISTRY}


def _n(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _detail(name: str, calculation: str, value: float | None, unit: str = "Virupas") -> Report:
    return {"name": name, "calculation": calculation, "value": value, "unit": unit}


def _table(title: str, columns: list[str], rows: list[list[Any]]) -> Report:
    return {"title": title, "columns": columns, "rows": rows}


def _view(identifier: str, name: str, description: str, group: str, unit: str,
          formula: str, notes: list[str] | None = None, maximum: float | None = None) -> Report:
    return {"id": identifier, "name": name, "description": description, "group": group,
            "unit": unit, "formula": formula, "notes": notes or [], "rows": [], "maximum": maximum}


def build_bala_report(chart: KundaliChart) -> Report:
    if chart.shadbala is None or chart.vimshopaka_bala is None or chart.bhava_bala is None:
        raise ValueError("Bala scores must be computed before building their calculation report.")
    views = [
        _view("shadbala", "Shadbala Total", "Six strengths combined", "Shadbala", "Rupas",
              "(Sthana + Dig + Kala + Cheshta + Naisargika + Drik) ÷ 60",
              ["Rahu and Ketu are excluded from these classical planetary strength schemes."]),
        _view("sthana", "Sthana Bala", "Positional strength", "Shadbala", "Virupas",
              "Uccha + Saptavargaja + Ojayugma Rasi Amsa + Kendradi + Drekkana"),
        _view("dig", "Dig Bala", "Directional strength", "Shadbala", "Virupas",
              "Shortest angular distance from the weak cusp ÷ 3; maximum 60", maximum=60),
        _view("kala", "Kala Bala", "Strength from time and declination", "Shadbala", "Virupas",
              "Nathonnata + Paksha + Tribhaga + Dina + Hora + Ayana",
              ["Masa Bala, Varsha Bala and Yuddha Bala are not calculated by the current engine."]),
        _view("cheshta", "Cheshta Bala", "Strength from planetary motion", "Shadbala", "Virupas",
              "Sun: Ayana Bala; Moon: Paksha Bala; other planets: speed classification",
              ["The five non-luminary planets use a simplified speed classification, rather than the full eight classical motion states."], 60),
        _view("naisargika", "Naisargika Bala", "Natural planetary strength", "Shadbala", "Virupas",
              "60 × natural-strength numerator ÷ 7", maximum=60),
        _view("drik", "Drik Bala", "Strength from incoming planetary aspects", "Shadbala", "Virupas",
              "Sum of benefic aspects × 1.25 minus malefic aspects × 0.75",
              ["Uses the app’s discrete Graha Drishti aspects. Negative values reduce Shadbala. Mercury is benefic-weighted; the Moon depends on its waxing or waning phase."]),
    ]
    schemes = [
        ("shadvarga", "Shadvarga · 6 divisions", vb.SHADVARGA_WEIGHTS),
        ("saptavarga", "Saptavarga · 7 divisions", vb.SAPTAVARGA_WEIGHTS),
        ("dashavarga", "Dashavarga · 10 divisions", vb.DASHAVARGA_WEIGHTS),
        ("shodashavarga", "Shodashavarga · 16 divisions", vb.SHODASHAVARGA_WEIGHTS),
    ]
    for identifier, name, _ in schemes:
        views.append(_view(identifier, name, "Vimshopaka Bala", "Vimshopaka Bala", "Points / 20",
                           "Sum of (division weight × relationship points ÷ 20)",
                           ["Relationship points: own 20, great friend 18, friend 15, neutral 10, enemy 7, great enemy 5. Fivefold relationships use natal D1 positions.",
                            "Score bands: below 5 Inauspicious; 5 to below 10 Some Good Effects; 10 to below 15 Mediocre; 15–20 Wholly Favourable."], 20))
    views += [
        _view("bhava", "Bhava Bala · 12 houses", "House strength; colors follow each cusp’s lord", "Bhava Bala", "Rupas",
              "Bhavadhipati + Bhava Dig + Bhava Drishti adjustment + occupancy adjustment",
              ["Uses the app’s Placidus Bhava Chalit cusps, including for aspects and occupancy. House lord is the lord of the cusp sign.",
               "Diurnal bonus is not implemented. Houses are compared with each other; no fixed strong-house threshold is applied."]),
        _view("ishta", "Ishta Phala", "Normalized favourable potential", "Phala", "0–1",
              "√(Uccha Bala × Cheshta Bala) ÷ 60", maximum=1),
        _view("kashta", "Kashta Phala", "Normalized difficult potential", "Phala", "0–1",
              "√((60 − Uccha Bala) × (60 − Cheshta Bala)) ÷ 60", maximum=1),
    ]
    by_view = {view["id"]: view for view in views}
    positions = {p.planet: p for p in chart.planets}
    birth = chart.birth_data
    utc = birth.utc_datetime
    rise, sunset, next_rise = sunrise_sunset(utc, birth.latitude, birth.longitude)
    offset = timedelta(hours=birth.utc_offset_hours)
    clock = birth.birth_time.hour + birth.birth_time.minute / 60 + birth.birth_time.second / 3600
    obliquity = mean_obliquity_degrees(utc)
    ayanamsha = ayanamsha_value(utc, birth.ayanamsha)
    waxing = chart.panchanga.paksha == "Shukla"
    elongation = (positions[Planet.MOON].longitude - positions[Planet.SUN].longitude) % 360
    paksha_raw = min(elongation, 360 - elongation) / 3
    day_birth = rise <= utc < sunset
    start, end = (rise, sunset) if day_birth else (sunset, next_rise)
    interval = (end - start).total_seconds()
    fraction = (utc - start).total_seconds() / interval if interval > 0 else 0
    third = min(2, int(fraction * 3))
    third_lord = (sb._TRIBHAGA_DAY_LORDS if day_birth else sb._TRIBHAGA_NIGHT_LORDS)[third]
    birth_hora = chart.panchanga.hora
    sunrise_lord = sb._DINA_LORD_BY_WEEKDAY[(rise + offset).weekday()]
    if birth_hora is not None:
        hora_index, hora_lord = birth_hora.index - 1, birth_hora.lord
    else:
        selected_hora = hora_interval(utc, rise, sunset, next_rise, (rise + offset).weekday())
        hora_index, hora_lord = selected_hora.index - 1, selected_hora.lord
    weekday_lord = sb._DINA_LORD_BY_WEEKDAY[birth.birth_date.weekday()]
    cusps = chart.bhava_chalit_cusps
    assert cusps is not None

    for planet in CLASSICAL:
        pos, score = positions[planet], chart.shadbala[planet]
        common_inputs = [
            {"name": "Natal D1 position", "value": f"{pos.sign.value} {_n(pos.degree_in_sign)}°; longitude {_n(pos.longitude)}°"},
            {"name": "D9 Navamsa sign", "value": pos.varga_signs["D9"].value},
            {"name": "Birth time", "value": f"{birth.local_datetime.isoformat()} (UTC {_n(birth.utc_offset_hours)})"},
        ]

        def add(identifier: str, value: float, details: list[Report], tables: list[Report] | None = None,
                inputs: list[Report] | None = None, **extra: Any) -> None:
            by_view[identifier]["rows"].append({"key": planet.value, "label": planet.value,
                "planet": planet.value, "value": value, "details": details, "tables": tables or [],
                "inputs": common_inputs + (inputs or []), **extra})

        sthana = score.sthana_bala
        exalt = list(Sign).index(EXALTATION_SIGN[planet]) * 30 + DEEP_DIGNITY_DEGREE[planet]
        distance = sb._angular_distance(pos.longitude, exalt)
        whole_house = whole_sign_house(pos.sign, chart.ascendant.sign)
        wants_odd = planet in sb.MASCULINE or planet in sb.NEUTER
        parity_parts = [(sign.value, 15 if sb._is_odd_sign(sign) == wants_odd else 0)
                        for sign in (pos.sign, pos.varga_signs["D9"])]
        varga_rows: list[list[Any]] = []
        for code in sb._SAPTAVARGAJA_CODES:
            sign = pos.sign if code == "D1" else pos.varga_signs[code]
            lord = RASHI_LORD[sign]
            relation = panchadha_relation(planet, pos.sign, lord, positions[lord].sign)
            low, high = sb.MOOLATRIKONA_RANGE[planet]
            if lord == planet and code == "D1" and sign == sb.MOOLATRIKONA_SIGN[planet] and low <= pos.degree_in_sign < high:
                relation = "own_moolatrikona"
            varga_rows.append([f"{code} {VARGA_NAMES[code]}", sign.value, lord.value,
                               relation.replace("_", " "), sb._SAPTAVARGAJA_POINTS[relation]])
        add("sthana", sthana.total, [
            _detail("Uccha Bala", f"60 − {_n(distance)}° ÷ 3; exaltation longitude {_n(exalt)}°", sthana.uchcha_bala),
            _detail("Saptavargaja Bala", " + ".join(_n(row[-1]) for row in varga_rows), sthana.saptavargaja_bala),
            _detail("Ojayugma Rasi Amsa Bala", f"Prefer {'odd' if wants_odd else 'even'} signs: " + " + ".join(f"{name} ({points})" for name, points in parity_parts), sthana.ojayugmarasyamsa_bala),
            _detail("Kendradi Bala", f"Whole-sign house {whole_house}; angular 60, succedent 30, cadent 15", sthana.kendradi_bala),
            _detail("Drekkana Bala", f"D1 part {min(int(pos.degree_in_sign // 10), 2) + 1}; masculine / feminine / neuter thirds, matching group earns 15", sthana.drekkana_bala),
        ], [_table("Saptavargaja: seven divisional contributions", ["Division", "Sign", "Sign lord", "Relationship", "Virupas"], varga_rows)])
        strong = sb._DIG_BALA_STRONG_CUSP[planet]
        weak = (strong + 6) % 12
        add("dig", score.dig_bala, [_detail("Dig Bala", f"min(60, {_n(sb._angular_distance(pos.longitude, cusps[weak]))}° ÷ 3)", score.dig_bala)],
            inputs=[{"name": "Strong direction", "value": f"House {strong + 1} cusp: {_n(cusps[strong])}°"},
                    {"name": "Weak direction", "value": f"House {weak + 1} cusp: {_n(cusps[weak])}°"}])
        tropical = (pos.longitude + ayanamsha) % 360
        declination = declination_degrees(tropical, pos.ecliptic_latitude, obliquity)
        kala = score.kala_bala
        night_value = min(60, max(0, 2 * (30 - min(clock, 24 - clock) * 2.5)))
        nathonnata_rule = "Mercury receives 60" if planet == Planet.MERCURY else (
            f"Night value {_n(night_value)}" if planet in sb._NIGHT_STRONG else f"60 − night value {_n(night_value)}")
        mode = sb._AYANA_MODE[planet]
        adjusted = declination if mode == "add_north" else -declination if mode == "add_south" else abs(declination)
        add("kala", kala.total, [
            _detail("Nathonnata Bala", nathonnata_rule + f"; local clock {_n(clock)} hours", kala.nathonnata_bala),
            _detail("Paksha Bala", (f"{_n(paksha_raw)}" if planet in sb._BENEFIC_PAKSHA else f"60 − {_n(paksha_raw)}") + f"; Sun–Moon elongation {_n(elongation)}°", kala.paksha_bala),
            _detail("Tribhaga Bala", f"{'Day' if day_birth else 'Night'} third {third + 1}: {third_lord.value}; lord earns 60; Jupiter always 60", kala.tribhaga_bala),
            _detail("Dina Bala", f"Civil-date weekday lord {weekday_lord.value} earns 45; others 0", kala.dina_bala),
            _detail("Hora Bala", f"Sunrise lord {sunrise_lord.value}; hora {hora_index + 1} lord {hora_lord.value} earns 60", kala.hora_bala),
            _detail("Ayana Bala", f"clamp(30 × ({_n(obliquity)} + ({_n(adjusted)})) ÷ {_n(obliquity)}, 0, 60)", kala.ayana_bala),
        ], inputs=[{"name": name, "value": value} for name, value in (
            ("Sunrise / sunset / next sunrise (local)", " / ".join((moment + offset).isoformat() for moment in (rise, sunset, next_rise))),
            ("Sidereal to tropical longitude", f"{_n(pos.longitude)}° + ayanamsha {_n(ayanamsha)}° = {_n(tropical)}°"),
            ("Latitude / declination / obliquity", f"{_n(pos.ecliptic_latitude)}° / {_n(declination)}° / {_n(obliquity)}°"),
            ("Ayana convention", "North positive" if mode == "add_north" else "South positive" if mode == "add_south" else "Absolute declination"),
        )])
        if planet == Planet.SUN:
            motion_rule = "Use the Sun’s Ayana Bala shown in Kala Bala"
        elif planet == Planet.MOON:
            motion_rule = "Use the Moon’s Paksha Bala shown in Kala Bala"
        else:
            speed, mean = pos.speed_longitude, sb.MEAN_DAILY_MOTION[planet]
            ratio = speed / mean
            branch = "retrograde → 60" if speed < 0 else "stationary (below 5% of mean) → 15" if abs(speed) < 0.05 * mean else "near mean (95%–105%) → 7.5" if 0.95 <= ratio <= 1.05 else "slower than mean → 30" if ratio < 0.95 else "faster than mean → 45"
            motion_rule = f"{_n(speed)}°/day ÷ {_n(mean)}°/day = {_n(ratio)}; {branch}"
        add("cheshta", score.chesta_bala, [_detail("Cheshta Bala", motion_rule, score.chesta_bala)])
        natural_order = [Planet.SUN, Planet.MOON, Planet.VENUS, Planet.JUPITER, Planet.MERCURY, Planet.MARS, Planet.SATURN]
        numerator = 7 - natural_order.index(planet)
        add("naisargika", score.naisargika_bala, [_detail("Naisargika Bala", f"60 × {numerator} ÷ 7", score.naisargika_bala)],
            inputs=[{"name": "Natural strength order", "value": "Sun, Moon, Venus, Jupiter, Mercury, Mars, Saturn"}])
        incoming: list[Report] = []
        for aspect in chart.aspects:
            if aspect.target_planet != planet:
                continue
            source = aspect.source_planet
            base = sb._DRIK_SPECIAL_STRENGTH.get(source, 60.0) if aspect.is_special else 60.0
            multiplier = 1.25 if source in sb._DRIK_BENEFIC or (source == Planet.MOON and waxing) else -0.75
            incoming.append(_detail(f"{source.value} aspect", f"{'Special' if aspect.is_special else '7th'} aspect: {_n(base)} × {_n(multiplier)}", base * multiplier))
        add("drik", score.drik_bala, incoming or [_detail("No incoming classical aspects", "No aspect contribution = 0", 0)],
            inputs=[{"name": "Moon phase", "value": "Waxing" if waxing else "Waning"},
                    {"name": "Aspect houses", "value": f"Main chart {birth.house_system.value}; {planet.value} in house {pos.house}"}])
        total_parts = [("Sthana Bala", sthana.total), ("Dig Bala", score.dig_bala), ("Kala Bala", kala.total),
                       ("Cheshta Bala", score.chesta_bala), ("Naisargika Bala", score.naisargika_bala), ("Drik Bala", score.drik_bala)]
        add("shadbala", score.total_rupas, [_detail(name, f"{_n(value)} Virupas ÷ 60", value / 60, "Rupas") for name, value in total_parts],
            required=score.required_rupas, status="Meets required strength" if score.meets_required_strength else "Below required strength")
        add("ishta", score.ishta_phala, [_detail("Ishta Phala", f"√({_n(sthana.uchcha_bala)} × {_n(score.chesta_bala)}) ÷ 60", score.ishta_phala, "0–1")])
        add("kashta", score.kashta_phala, [_detail("Kashta Phala", f"√((60 − {_n(sthana.uchcha_bala)}) × (60 − {_n(score.chesta_bala)})) ÷ 60", score.kashta_phala, "0–1")])
        for identifier, _, weights in schemes:
            division_rows: list[list[Any]] = []
            contributions: list[Report] = []
            for code, weight in weights.items():
                sign = pos.sign if code == "D1" else pos.varga_signs[code]
                lord = RASHI_LORD[sign]
                relation = panchadha_relation(planet, pos.sign, lord, positions[lord].sign)
                points = vb.VARGA_VISWA_POINTS[relation]
                value = weight * points / 20
                contributions.append(_detail(f"{code} {VARGA_NAMES[code]}", f"{_n(weight)} × {_n(points)} ÷ 20; {sign.value}, {lord.value}, {relation.replace('_', ' ')}", value, "Points"))
                division_rows.append([code, sign.value, lord.value, relation.replace("_", " "), weight, points, value])
            vim_score = getattr(chart.vimshopaka_bala[planet], f"{identifier}_score")
            add(identifier, vim_score, contributions,
                [_table("Division weights and relationships", ["Division", "Sign", "Lord", "Relationship", "Weight", "Points", "Contribution"], division_rows)],
                status=getattr(chart.vimshopaka_bala[planet], f"{identifier}_band"))

    for house, score_house in chart.bhava_bala.items():
        cusp = cusps[house - 1]
        sign = sign_for_longitude(cusp)
        lord = RASHI_LORD[sign]
        reference = bb._bhava_reference_cusp_index(sign, degree_in_sign(cusp))
        aspecting = bb._aspecting_planets_for_house(house, chart.planets)
        benefic = any(p in bb._BENEFIC or (p == Planet.MOON and waxing) for p, _ in aspecting)
        malefic = any(p in bb._MALEFIC or (p == Planet.MOON and not waxing) for p, _ in aspecting)
        multiplier = (1.25 if benefic else 1) * (0.75 if malefic else 1)
        bonus = sum(bb._SPECIAL_ASPECT_STRENGTH.get(p, 60.0) if special else 60.0
                    for p, special in aspecting if p in (Planet.JUPITER, Planet.MERCURY))
        occupancy = [p for p in chart.planets if p.bhava_chalit_house == house]
        occupancy_text = " + ".join(f"{p.planet.value} ({1 if p.planet in bb._OCCUPANCY_BONUS else -1 if p.planet in bb._OCCUPANCY_PENALTY else 0:+d})" for p in occupancy) or "No occupants: 0"
        dig_virupas = score_house.bhava_dig_bala * 60
        by_view["bhava"]["rows"].append({
            "key": f"H{house}", "label": f"House {house}", "planet": lord.value, "value": score_house.total_rupas,
            "details": [
                _detail("Bhavadhipati Bala", f"{sign.value} cusp lord {lord.value}: its total Shadbala", score_house.bhavadhipati_bala, "Rupas"),
                _detail("Bhava Dig Bala", f"min(60, {_n(bb._angular_distance(cusp, cusps[reference]))}° ÷ 3) ÷ 60", score_house.bhava_dig_bala, "Rupas"),
                _detail("Bhava Drishti adjustment", f"({_n(dig_virupas)} × {_n(multiplier)} − {_n(dig_virupas)} + {_n(bonus)}) ÷ 60", score_house.bhava_drishti_bala, "Rupas"),
                _detail("Occupancy adjustment", occupancy_text, score_house.occupancy_adjustment, "Rupas"),
                _detail("Diurnal bonus", "Not calculated; excluded from the total", None, "Rupas"),
            ],
            "inputs": [
                {"name": "Bhava Chalit cusp", "value": f"{sign.value} {_n(degree_in_sign(cusp))}°; longitude {_n(cusp)}°"},
                {"name": "Directional reference", "value": f"House {reference + 1} cusp: {_n(cusps[reference])}°"},
                {"name": "Aspect modifiers", "value": f"Benefic present: {'yes' if benefic else 'no'}; malefic present: {'yes' if malefic else 'no'}; Moon {'waxing' if waxing else 'waning'}"},
            ],
            "tables": [_table("Incoming aspects to this Bhava Chalit house", ["Planet", "Source house", "Aspect", "Base Virupas", "Jupiter / Mercury bonus"],
                [[p.value, positions[p].bhava_chalit_house, "Special" if special else "7th",
                  bb._SPECIAL_ASPECT_STRENGTH.get(p, 60.0) if special else 60.0,
                  (bb._SPECIAL_ASPECT_STRENGTH.get(p, 60.0) if special else 60.0) if p in (Planet.JUPITER, Planet.MERCURY) else 0]
                 for p, special in aspecting])],
        })
    for view in views:
        values = [row["value"] for row in view["rows"]]
        step = 25 if view["unit"] == "Virupas" else 2 if view["unit"] == "Rupas" else 1
        view["minimum"] = min(0, floor(min(values) / step) * step)
        view["maximum"] = view["maximum"] or max(step, ceil(max(values + [row.get("required", 0) for row in view["rows"]]) / step) * step)
    return {"views": views, "conversion": "60 Virupas = 1 Rupa"}
