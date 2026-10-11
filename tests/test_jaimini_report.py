"""Independent arithmetic cases and published sequence examples."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from vedic_astro.chart import build_kundali_chart
from vedic_astro.jaimini import _sign_duration_years, compute_chara_karakas, compute_chara_dasha
from vedic_astro.jaimini_dasha import narayana_order, subdivide_period
from vedic_astro.jaimini_report import arudha, argala_rows, build_jaimini_report, primary_lord, special_lagnas
from vedic_astro.models import BirthData, NakshatraPlacement, Planet, PlanetPosition, Sign
from vedic_astro.web.app import app, _jaimini_for_birth


def position(planet: Planet, sign: Sign, degree: float = 10) -> PlanetPosition:
    return PlanetPosition(planet=planet, sign=sign, longitude=list(Sign).index(sign) * 30 + degree,
                          degree_in_sign=degree, house=1, retrograde=planet in (Planet.RAHU, Planet.KETU),
                          nakshatra=NakshatraPlacement(name="Ashwini", index=1, pada=1, lord=Planet.KETU))


@pytest.fixture(scope="module")
def chart():
    return build_kundali_chart(BirthData(birth_date="1998-09-04", birth_time="00:03:00",
                              latitude=17.00517, longitude=81.77784, utc_offset_hours=5.5))


@pytest.fixture(scope="module")
def report(chart):
    return build_jaimini_report(chart)


def test_eight_karakas_reverse_rahu_and_keep_unrounded_precision():
    rows = [position(p, Sign.ARIES, d) for p, d in zip(list(Planet), [29.001, 28, 27, 26, 25, 24, 23, .5, .5])]
    result = compute_chara_karakas(rows, 8)
    assert result[0].planet == Planet.RAHU
    assert result[0].degree_in_sign == .5
    assert result[1].planet == Planet.SUN
    assert len(result) == 8 and all(k.planet != Planet.KETU for k in result)
    assert result[4].karaka == "Pitrikaraka"


def test_exact_karaka_ties_share_role_and_leave_next_role_empty():
    rows = [position(p, Sign.ARIES, d) for p, d in zip(list(Planet), [28, 28, 27, 26, 25, 24, 23, .5, .5])]
    result = compute_chara_karakas(rows)
    assert result[0].karaka == result[1].karaka == "Atmakaraka"
    assert result[2].karaka == "Bhratrikaraka"
    assert "Amatyakaraka" not in [k.karaka for k in result]


@pytest.mark.parametrize("source,lord,years", [
    (Sign.ARIES, Sign.CANCER, 3), (Sign.TAURUS, Sign.LEO, 3),
    (Sign.CANCER, Sign.LEO, 11), (Sign.VIRGO, Sign.LEO, 1),
    (Sign.AQUARIUS, Sign.AQUARIUS, 12), (Sign.PISCES, Sign.CAPRICORN, 2),
])
def test_chara_duration_is_count_minus_one_using_footed_groups(source, lord, years):
    assert _sign_duration_years(source, lord) == years


def test_chara_taurus_runs_backwards_and_ignores_dignity_year_corrections():
    planets = [position(p, Sign.ARIES) for p in list(Planet)[:7]]
    rows = compute_chara_dasha(Sign.TAURUS, planets, datetime(2000, 1, 1))
    assert [p.sign for p in rows[:3]] == [Sign.TAURUS, Sign.ARIES, Sign.PISCES]
    # Leo is even-footed: Leo → Cancer → Gemini → Taurus → Aries, minus 1 = 4.
    assert next(p.years for p in rows if p.sign == Sign.LEO) == 4  # Sun exalted, no +1.


@pytest.mark.parametrize("lord,result,count,exception", [
    (Sign.ARIES, Sign.CAPRICORN, 1, True), (Sign.TAURUS, Sign.GEMINI, 2, False),
    (Sign.CANCER, Sign.CANCER, 4, True), (Sign.LIBRA, Sign.CAPRICORN, 7, True),
    (Sign.CAPRICORN, Sign.CANCER, 10, True), (Sign.PISCES, Sign.AQUARIUS, 12, False),
])
def test_arudha_repeated_inclusive_count_and_tenth_from_raw_exception(lord, result, count, exception):
    assert arudha(Sign.ARIES, lord) == (result, count, exception)


def test_co_lord_in_own_sign_yields_to_other_and_nodes_reverse_advancement():
    planets = [position(Planet.SATURN, Sign.AQUARIUS), position(Planet.RAHU, Sign.ARIES)]
    assert primary_lord(Sign.AQUARIUS, planets) == Planet.RAHU
    planets = [position(Planet.MARS, Sign.GEMINI, 23), position(Planet.KETU, Sign.SAGITTARIUS, 5)]
    assert primary_lord(Sign.SCORPIO, planets) == Planet.KETU


def test_narayana_published_dual_order_and_saturn_ketu_exceptions():
    assert narayana_order(Sign.GEMINI) == [Sign.GEMINI, Sign.AQUARIUS, Sign.LIBRA, Sign.VIRGO,
        Sign.TAURUS, Sign.CAPRICORN, Sign.SAGITTARIUS, Sign.LEO, Sign.ARIES, Sign.PISCES, Sign.SCORPIO, Sign.CANCER]
    assert narayana_order(Sign.TAURUS)[:3] == [Sign.TAURUS, Sign.SAGITTARIUS, Sign.CANCER]
    assert narayana_order(Sign.TAURUS, saturn=True)[:3] == [Sign.TAURUS, Sign.GEMINI, Sign.CANCER]
    assert narayana_order(Sign.TAURUS, ketu=True)[:3] == [Sign.TAURUS, Sign.LIBRA, Sign.PISCES]


def test_co_lord_duration_tiebreak_includes_debilitation_adjustment():
    planets = [position(p, Sign.PISCES) for p in list(Planet) if p not in (Planet.SATURN, Planet.RAHU)]
    planets += [position(Planet.SATURN, Sign.ARIES, 25), position(Planet.RAHU, Sign.ARIES, 20)]
    assert primary_lord(Sign.AQUARIUS, planets) == Planet.SATURN  # 25 versus reversed 10 degrees.
    assert primary_lord(Sign.AQUARIUS, planets, for_dasha=True) == Planet.RAHU  # 10 versus 10 - 1 years.


def test_argala_ketu_reversal_equal_counts_and_special_third():
    rows = [position(Planet.KETU, Sign.ARIES), position(Planet.VENUS, Sign.PISCES), position(Planet.MOON, Sign.TAURUS),
            position(Planet.MARS, Sign.AQUARIUS), position(Planet.SATURN, Sign.AQUARIUS), position(Planet.SUN, Sign.AQUARIUS)]
    output = [r for r in argala_rows(rows) if r["target"] == "Aries"]
    assert output[0]["argala_sign"] == "Pisces" and output[0]["blocking_sign"] == "Taurus"
    assert output[0]["status"] == "Equal count — compare strength"
    assert output[2]["special"] is True
    assert "0 effective blockers" in output[2]["calculation"]


def test_sunrise_lagnas_use_previous_sunrise_at_midnight_and_exact_rates(chart, monkeypatch):
    rise = chart.birth_data.utc_datetime - timedelta(minutes=766)
    monkeypatch.setattr("vedic_astro.jaimini_report.sunrise_sunset", lambda *args: (rise, rise, rise))
    monkeypatch.setattr("vedic_astro.jaimini_report.planet_positions", lambda *args: {Planet.SUN: position(Planet.SUN, Sign.CAPRICORN, 24 + 17 / 60)})
    rows = special_lagnas(chart)
    assert rows[0]["longitude"] == pytest.approx(125 + 47 / 60)
    assert rows[1]["longitude"] == pytest.approx(317 + 17 / 60)
    assert rows[2]["longitude"] == pytest.approx(171 + 47 / 60)
    moon = next(p for p in chart.planets if p.planet == Planet.MOON)
    expected = (chart.ascendant.longitude + (moon.longitude % (360 / 27)) * 27) % 360
    assert rows[3]["longitude"] == pytest.approx(expected)


def test_report_covers_every_house_planet_scheme_and_declared_system(report, chart):
    assert len(report["aspects"]) == 9 and len(report["padas"]) == 12 and len(report["argala"]) == 48
    assert [p["house"] for p in report["padas"]] == list(range(1, 13))
    assert report["upapada"]["sign"] == report["padas"][11]["sign"]
    assert len(report["schemes"]["7"]["karakas"]) == 7
    assert len(report["schemes"]["8"]["karakas"]) == 8
    assert len(report["strengths"]) == 12
    assert len(report["dasha_systems"]) == 11
    assert datetime.fromisoformat(report["lagnas"][0]["sunrise"]).date() < chart.birth_data.birth_date
    assert sum(p["years"] for s in report["dasha_systems"] if s["code"] == "narayana" for p in s["periods"]) == pytest.approx(144)
    for system in report["dasha_systems"]:
        for i, period in enumerate(system["periods"]):
            assert datetime.fromisoformat(period["end"]) > datetime.fromisoformat(period["start"])
            if i:
                assert period["start"] == system["periods"][i - 1]["end"]
        if system["unavailable"]:
            assert system["periods"] == []


@pytest.mark.parametrize("parent", list(Sign))
def test_chara_subperiods_end_with_parent_and_cover_exact_parent(report, parent):
    system = next(s for s in report["dasha_systems"] if s["code"] == "chara")
    start, end = datetime(2000, 1, 1, 0, 3), datetime(2000, 9, 3, 8, 42, 7, 123456)
    rows = subdivide_period(system, parent, start, end)
    assert len(rows) == 12 and rows[-1]["sign"] == parent.value
    assert {p["sign"] for p in rows} == {s.value for s in Sign}
    assert datetime.fromisoformat(rows[0]["start"]) == start
    assert datetime.fromisoformat(rows[-1]["end"]) == end
    for i, row in enumerate(rows):
        span = datetime.fromisoformat(row["end"]) - datetime.fromisoformat(row["start"])
        assert span.total_seconds() == pytest.approx((end - start).total_seconds() / 12, abs=.00001)
        if i:
            assert row["start"] == rows[i - 1]["end"]


def test_branch_api_reaches_prana_and_rejects_unsupported_paths(report, chart, monkeypatch):
    monkeypatch.setattr("vedic_astro.web.app._jaimini_for_birth", lambda birth: report)
    client = TestClient(app)
    birth = chart.birth_data.model_dump(mode="json")
    system = next(s for s in report["dasha_systems"] if s["code"] == "chara")
    parent = system["periods"][2]
    path = [2]
    for _ in range(4):
        response = client.post("/api/jaimini/subperiods", json={"birth_data": birth, "system": "chara", "path": path})
        assert response.status_code == 200
        rows = response.json()["periods"]
        assert rows[0]["start"] == parent["start"] and rows[-1]["end"] == parent["end"]
        parent = rows[4]; path.append(4)
    for code, invalid, status in [("chara", [-1], 400), ("chara", [500], 400), ("unknown", [0], 400),
                                   ("sudasha", [0], 400), ("narayana", [0, 0], 400), ("chara", [], 422),
                                   ("chara", [0] * 5, 422)]:
        assert client.post("/api/jaimini/subperiods", json={"birth_data": birth, "system": code, "path": invalid}).status_code == status
    assert client.post("/api/jaimini/subperiods", json={"birth_data": {**birth, "latitude": 100}, "system": "chara", "path": [0]}).status_code == 422


def test_report_cache_uses_entire_birth_input(chart):
    _jaimini_for_birth.cache_clear()
    first = _jaimini_for_birth(chart.birth_data.model_dump_json())
    modified = chart.birth_data.model_copy(update={"birth_time": datetime(2000, 1, 1, 12, 3).time()})
    second = _jaimini_for_birth(modified.model_dump_json())
    assert first["lagnas"] != second["lagnas"]
    assert _jaimini_for_birth.cache_info().currsize == 2
