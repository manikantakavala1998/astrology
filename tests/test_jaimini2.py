"""Book examples and arithmetic boundaries, independent of the other engine."""
from datetime import datetime, timedelta
import inspect
import json

import pytest

from vedic_astro.chart import build_kundali_chart
from vedic_astro.jaimini2 import (argala_rows, build_jaimini2_report, dwaya_hora,
                                karakas, lord, mirror, sign_key, sign_strength_rows)
from vedic_astro.jaimini2_dasha import drig_order, duration, padakrama, subdivide_book_period
from fastapi.testclient import TestClient
from vedic_astro.web.app import app
from vedic_astro.models import BirthData, NakshatraPlacement, Planet, PlanetPosition, Sign


def position(p: Planet, sign: Sign, degree: float) -> PlanetPosition:
    return PlanetPosition(planet=p, sign=sign, longitude=list(Sign).index(sign) * 30 + degree,
                          degree_in_sign=degree, house=1, retrograde=False,
                          nakshatra=NakshatraPlacement(name="Ashwini", index=1, pada=1, lord=Planet.KETU))


@pytest.fixture(scope="module")
def chart():
    return build_kundali_chart(BirthData(birth_date="1998-09-04", birth_time="00:03:00",
                                       latitude=17.00517, longitude=81.77784, utc_offset_hours=5.5))


@pytest.fixture(scope="module")
def report(chart):
    return build_jaimini2_report(chart)


@pytest.mark.parametrize("longitude,expected", [(0, Sign.ARIES), (14.999999, Sign.ARIES),
    (15, Sign.TAURUS), (30, Sign.GEMINI), (179.999999, Sign.PISCES),
    (180, Sign.ARIES), (195, Sign.TAURUS), (359.999999, Sign.PISCES)])
def test_parivritti_dwaya_half_sign_boundaries(longitude, expected):
    assert dwaya_hora(longitude) == expected


def test_book_seven_karakas_never_rank_rahu_and_flag_exact_ties():
    ps = [position(p, Sign.ARIES, d) for p, d in zip(list(Planet), [29, 28, 27, 26, 25, 24, 23, .1, .1])]
    rows, warnings = karakas(ps)
    assert [r["role"] for r in rows] == ["AK", "AmK", "BK", "MK", "PK", "GK", "DK"]
    assert len(rows) == 7 and rows[0]["planet"] == "Sun" and not warnings
    ps[1] = position(Planet.MOON, Sign.ARIES, 29)
    assert "Exact degree tie" in karakas(ps)[1][0]


def test_drig_matches_ramakrishna_example_sequence():
    assert drig_order(Sign.LIBRA)[:7] == [Sign.LIBRA, Sign.AQUARIUS, Sign.GEMINI,
        Sign.SCORPIO, Sign.CANCER, Sign.PISCES, Sign.SAGITTARIUS]
    for sign in Sign:
        assert len(set(drig_order(sign))) == 12
        assert len(set(padakrama(sign))) == 12


def test_argala_degree_check_distinguishes_17_from_26_degrees():
    # Book example: Moon in Aquarius (11th from Mercury/Aries),
    # Mars in Gemini (third) only obstructs when in the last quarter.
    ps = [position(p, Sign.CANCER, 12 + i) for i, p in enumerate(Planet)]
    ps[1] = position(Planet.MOON, Sign.AQUARIUS, 5)
    ps[2] = position(Planet.MARS, Sign.GEMINI, 17)
    def result():
        return next(r for r in argala_rows(ps) if r["target"] == "Aries" and r["argala_house"] == 11)
    assert "degree condition not met" in result()["status"]
    ps[2] = position(Planet.MARS, Sign.GEMINI, 26)
    assert "Degree obstruction" in result()["status"]
    # The quarter boundary is 22°30′ inclusive for the blocking planet.
    ps[2] = position(Planet.MARS, Sign.GEMINI, 22.5)
    assert "Degree obstruction" in result()["status"]


def test_chara_inverse_count_and_node_exaltation_are_book_specific():
    ps = [position(p, Sign.GEMINI, 3 + i) for i, p in enumerate(Planet)]
    ps[0] = position(Planet.SUN, Sign.CANCER, 10)
    assert duration(Sign.LEO, ps, inverse=True)[0] == 1
    assert duration(Sign.LEO, ps)[0] == 11
    ps[8] = position(Planet.KETU, Sign.LEO, 2)
    assert lord(Sign.SCORPIO, ps) == Planet.KETU  # Exclusive exaltation beats companions.
    ps[2] = position(Planet.MARS, Sign.CAPRICORN, 20)
    ps[8] = position(Planet.KETU, Sign.GEMINI, 2)
    assert lord(Sign.SCORPIO, ps) == Planet.MARS


def test_arudha_book_distance_example_and_correction():
    assert mirror(Sign.LIBRA, Sign.TAURUS) == (Sign.SAGITTARIUS, 8, False)
    assert mirror(Sign.ARIES, Sign.ARIES) == (Sign.CAPRICORN, 1, True)


def test_independent_report_and_user_chart(report):
    assert list(report["schemes"]) == ["7"]
    scheme = report["schemes"]["7"]
    assert scheme["karakas"][0]["planet"] == "Mercury"
    assert scheme["karakamsha"] == "Pisces"
    assert [p["pair"] for p in scheme["advanced"]["longevity_pairs"]] == [
        "Lagna lord / special eighth lord", "Lagna / Moon", "Lagna / Dwaya Hora Lagna"]
    assert len(report["padas"]) == 12 and len(report["aspects"]) == 9
    assert len(report["upapada_variants"]) == 2
    assert len(scheme["readings"]) == 4
    assert "commerce" in scheme["readings"][1]["summary"]
    assert all(r["evidence"] and r["rule"] for r in scheme["readings"])
    json.dumps(report, allow_nan=False)
    source = inspect.getsource(__import__('vedic_astro.jaimini2', fromlist=['']))
    assert 'from vedic_astro.jaimini_report' not in source
    assert 'from vedic_astro.jaimini import' not in source


def test_all_38_methods_have_rules_and_honest_availability(report, chart):
    systems = report["dasha_systems"]
    assert [s["book_number"] for s in systems] == list(range(1, 39))
    assert len(set(s["code"] for s in systems)) == 38
    for s in systems:
        assert s["method"] and s["max_levels"] == (3 if s['periods'] and s['code'] != 'nisarga' else 1)
        assert bool(s["periods"]) != bool(s["unavailable"])
        assert s["year_days"] == 360
        for i, p in enumerate(s["periods"]):
            start, end = datetime.fromisoformat(p["start"]), datetime.fromisoformat(p["end"])
            assert start == (chart.birth_data.local_datetime if i == 0 else datetime.fromisoformat(s["periods"][i - 1]["end"]))
            assert end - start == timedelta(days=p["years"] * 360)
            assert end > start and p["rule"]
    chara = next(s for s in systems if s["code"] == 'chara')
    assert chara["periods"][0]["sign"] == "Leo"  # More occupants than Taurus Lagna.
    assert next(s for s in systems if s["code"] == 'navamsa')["basis"] == "D9"
    nisarga = next(s for s in systems if s["code"] == 'nisarga')
    assert not nisarga["periods"] and 'Not applicable' in nisarga["unavailable"]


def test_prediction_conditions_use_their_own_method_and_chart(report):
    systems = {s['code']: s for s in report['dasha_systems']}
    navamsa = systems['navamsa']['activation_rules']
    # AmK Sun is Virgo in D9: eleventh from Scorpio.
    work = next(r for r in navamsa['Scorpio'] if r['topic'] == 'Work support')
    assert work['present'] and 'D9 Virgo' in work['evidence']
    # AK Mercury in D9 Pisces is third from Capricorn.
    move = next(r for r in navamsa['Capricorn'] if r['topic'] == 'Change of place')
    assert move['present'] and 'H3' in move['evidence']
    assert not systems['shoola']['activation_rules']
    assert systems['chara']['activation_rules']['Leo'][0]['topic'] == 'Money & comforts'


def test_nisarga_eligible_chart_uses_book_sun_twenty_years(chart):
    changed = chart.model_copy(deep=True)
    ps = {p.planet: p for p in changed.planets}
    ps[Planet.SATURN].sign = ps[Planet.VENUS].sign
    ps[Planet.SATURN].longitude = ps[Planet.VENUS].longitude
    report = build_jaimini2_report(changed)
    nisarga = next(s for s in report["dasha_systems"] if s["code"] == 'nisarga')
    assert nisarga["unavailable"] is None
    assert next(p["years"] for p in nisarga["periods"] if p["sign"] == 'Leo') == 20


def test_strength_is_not_a_fabricated_total():
    ps = [position(Planet.SUN, Sign.LEO, 1), position(Planet.MOON, Sign.CANCER, 29)]
    assert sign_key(Sign.CANCER, ps) > sign_key(Sign.LEO, ps)
    ps.append(position(Planet.MARS, Sign.LEO, 2))
    assert sign_key(Sign.LEO, ps) > sign_key(Sign.CANCER, ps)


def test_sign_strength_graph_ranks_preserve_ties(chart):
    rows = sign_strength_rows(chart.planets)
    assert len(rows) == 12 and rows[0]['rank'] == 1
    for row in rows:
        key = sign_key(Sign(row['sign']), chart.planets)
        assert row['rank'] == 1 + sum(sign_key(sign, chart.planets) > key for sign in Sign)
    tied = [r for r in rows if not r['occupants'] and r['metrics'][2] == 2]
    assert len(tied) > 1 and len({r['rank'] for r in tied}) == 1


def test_yogada_kevala_identify_qualifying_planets_separately(report, chart):
    rows = report['schemes']['7']['yogas']
    assert {row['name'] for row in rows} >= {'Moon-dispositor Yogada', 'Moon-dispositor Kevala'}
    by = {p.planet.value: p for p in chart.planets}
    for row in rows:
        assert row['planets'] and all(p in by for p in row['planets'])
        if row['name'].endswith('multi-chart Yogada'):
            assert row['kind'] == 'yogada' and row['planets'] == [row['name'].split(' · ')[0]]
        elif row['name'].endswith(' · Kevala'):
            assert row['kind'] == 'kevala' and row['planets'] == [row['name'].split(' · ')[0]]
    disposer = next(row for row in rows if row['name'] == 'Moon-dispositor Yogada')
    assert disposer['kind'] == 'yogada'
    assert disposer['planets'] == [lord(by['Moon'].sign, chart.planets).value]
    assert all(row['kind'] == 'other' for row in rows if ' · D9' in row['name'])


def test_moon_dispositor_kevala_can_qualify_without_the_house_rule(chart):
    changed = chart.model_copy(deep=True)
    changed.ascendant.sign = Sign.ARIES
    changed.ascendant.longitude = 0
    changed.planets = [position(p.planet, Sign.GEMINI, 15) if p.planet == Planet.MOON else
                       position(p.planet, Sign.SAGITTARIUS, 9) if p.planet == Planet.MERCURY else p
                       for p in changed.planets]
    rows = build_jaimini2_report(changed)['schemes']['7']['yogas']
    primary = next(row for row in rows if row.get('variant') == 'sign_aspect' and row['planets'] == ['Mercury'])
    alternative = next(row for row in rows if row['name'] == 'Moon-dispositor Kevala')
    assert not primary['present'] and alternative['present']
    assert alternative['planets'] == ['Mercury']
    assert alternative['connections'] == [{'sign': 'Gemini', 'house': 3, 'target': 'Moon'}]


@pytest.mark.parametrize('years,antar_days,praty_days', [(12, 360, 30), (9, 270, 22.5), (1, 30, 2.5)])
def test_book_subdivision_duration_table_and_endpoint_conservation(report, years, antar_days, praty_days):
    system = next(s for s in report['dasha_systems'] if s['code'] == 'navamsa')
    start = datetime(2000, 1, 1, 0, 3)
    end = start + timedelta(days=years * 360)
    parent = {'sign': 'Aries', 'start': start.isoformat(), 'end': end.isoformat()}
    antars = subdivide_book_period(system, parent)
    assert len(antars) == 12 and len({p['sign'] for p in antars}) == 12
    assert datetime.fromisoformat(antars[0]['end']) - start == timedelta(days=antar_days)
    praty = subdivide_book_period(system, antars[0])
    assert datetime.fromisoformat(praty[0]['end']) - start == timedelta(days=praty_days)
    for rows, a, b in ((antars, start, end), (praty, start, datetime.fromisoformat(antars[0]['end']))):
        assert datetime.fromisoformat(rows[0]['start']) == a
        assert datetime.fromisoformat(rows[-1]['end']) == b
        assert all(rows[i]['end'] == rows[i + 1]['start'] for i in range(11))


def test_all_calculated_methods_have_independent_three_level_orders(report):
    for system in report['dasha_systems']:
        if not system['periods'] or system['code'] == 'nisarga':
            continue
        assert 'Explorer convention' in system['subdivision_status']
        for order in system['child_orders'].values():
            assert len(order) == len(set(order)) == 12
        parent = system['periods'][0]
        antars = subdivide_book_period(system, parent)
        praty = subdivide_book_period(system, antars[0])
        assert datetime.fromisoformat(praty[0]['start']) == datetime.fromisoformat(parent['start'])
        assert datetime.fromisoformat(antars[-1]['end']) == datetime.fromisoformat(parent['end'])


def test_book_branch_api_and_invalid_paths(chart):
    client = TestClient(app)
    payload = {'birth_data': chart.birth_data.model_dump(mode='json'), 'system': 'chara', 'path': [0]}
    response = client.post('/api/jaimini2/subperiods', json=payload)
    assert response.status_code == 200
    antars = response.json()['periods']
    assert len(antars) == 12 and antars[0]['sign'] == 'Leo'
    assert 'Explorer convention' in response.json()['convention']
    payload['path'] = [0, 1]
    praty = client.post('/api/jaimini2/subperiods', json=payload)
    assert praty.status_code == 200 and praty.json()['periods'][0]['sign'] == 'Virgo'
    assert praty.json()['periods'][0]['start'] == antars[1]['start']
    for path in ([-1], [999], [0, 999]):
        payload['path'] = path
        assert client.post('/api/jaimini2/subperiods', json=payload).status_code == 400
    payload['path'] = [0, 0, 0]
    assert client.post('/api/jaimini2/subperiods', json=payload).status_code == 422
    payload.update(path=[0], system='hora')
    assert client.post('/api/jaimini2/subperiods', json=payload).status_code == 400
