from datetime import date, time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from vedic_astro.chart import build_kundali_chart
from vedic_astro.laghu_parashari import build_laghu_report, lordship_rows, relationship
from vedic_astro.models import BirthData, Planet, Sign


@pytest.fixture(scope="module")
def chart():
    return build_kundali_chart(BirthData(birth_date=date(1998, 9, 4), birth_time=time(0, 3),
        latitude=17.00517, longitude=81.77784, utc_offset_hours=5.5))


def test_taurus_roles_keep_mixed_ownership_and_maraka_separate():
    rows = {row["planet"]: row for row in lordship_rows(Sign.TAURUS)}
    assert rows["Saturn"]["houses"] == [9, 10]
    assert rows["Saturn"]["yogakaraka"]
    assert rows["Venus"]["houses"] == [1, 6]
    assert rows["Venus"]["role"] == "Mixed"
    assert rows["Mercury"]["tone"] == "good"
    assert rows["Mercury"]["maraka_houses"] == [2]
    assert rows["Moon"]["adverse"] == [3]
    assert rows["Jupiter"]["adverse"] == [11, 8]
    assert rows["Sun"]["role"] == "Conditional"


@pytest.mark.parametrize("asc,expected", [
    (Sign.ARIES, []), (Sign.TAURUS, ["Saturn"]), (Sign.GEMINI, []), (Sign.CANCER, ["Mars"]),
    (Sign.LEO, ["Mars"]), (Sign.VIRGO, []), (Sign.LIBRA, ["Saturn"]), (Sign.SCORPIO, []),
    (Sign.SAGITTARIUS, []), (Sign.CAPRICORN, ["Venus"]), (Sign.AQUARIUS, ["Venus"]), (Sign.PISCES, []),
])
def test_all_ascendant_lordships_and_six_standalone_yogakarakas(asc, expected):
    rows = lordship_rows(asc)
    assert sorted(h for row in rows for h in row["houses"]) == list(range(1, 13))
    assert [row["planet"] for row in rows if row["yogakaraka"]] == expected


@pytest.mark.parametrize("asc,planet", [(Sign.ARIES, "Mars"), (Sign.LIBRA, "Venus"),
    (Sign.CAPRICORN, "Sun"), (Sign.SAGITTARIUS, "Moon")])
def test_eighth_lord_exceptions(asc, planet):
    row = next(row for row in lordship_rows(asc) if row["planet"] == planet)
    assert row["eighth_exception"]
    assert 8 not in row["adverse"]


def test_relationships_do_not_promote_one_way_aspect_to_mutual():
    a = SimpleNamespace(planet=Planet.JUPITER, sign=Sign.ARIES)
    b = SimpleNamespace(planet=Planet.VENUS, sign=Sign.LEO)
    assert relationship(a, b) == []
    b.sign = Sign.LIBRA
    assert relationship(a, b) == ["Mutual aspect"]
    a.planet, a.sign = Planet.MARS, Sign.TAURUS
    b.planet, b.sign = Planet.VENUS, Sign.ARIES
    assert relationship(a, b) == ["Sign exchange"]


def test_complete_catalogue_and_engine_periods(chart):
    report = build_laghu_report(chart)
    assert [rule["number"] for rule in report["rules"]] == list(range(1, 43))
    assert len(report["all_ascendants"]) == 12
    assert len(report["aspects"]) == 13
    assert all(row["planet"] not in ("Rahu", "Ketu") for row in report["aspects"])
    assert report["rules"][24]["status"] == "Prerequisite"
    assert "lifespan" in report["rules"][24]["result"]
    assert len(report["periods"]) == len(chart.dasha.periods)
    for actual, expected in zip(report["periods"], chart.dasha.periods):
        assert actual["start"] == expected.start.isoformat()
        assert actual["end"] == expected.end.isoformat()
        assert len(actual["sub_periods"]) == len(expected.sub_periods)
        for a, e in zip(actual["sub_periods"], expected.sub_periods):
            assert a["start"] == e.start.isoformat()
            assert a["reading"]["major"] == expected.planet.value
            assert a["reading"]["minor"] == e.planet.value
            if {e.planet, expected.planet} == {Planet.SATURN, Planet.VENUS}:
                assert a["reading"]["tone"] == "mixed"
                assert 40 in a["reading"]["rules"]


def test_whole_sign_rule_positions_ignore_cusp_house_field(chart):
    moved = chart.model_copy(update={"planets": [p.model_copy(update={"house": 1}) for p in chart.planets]})
    original, changed = build_laghu_report(chart), build_laghu_report(moved)
    assert original["roles"] == changed["roles"]
    assert original["aspects"] == changed["aspects"]


def test_report_is_exposed_in_bootstrap_and_native_panel():
    import json
    import re
    from vedic_astro.web.app import app
    response = TestClient(app).post("/", data={"birth_date": "04/09/1998", "birth_hour": "12", "birth_minute": "3",
        "birth_meridiem": "AM", "manual_latitude": "17.00517", "manual_longitude": "81.77784", "manual_utc_offset_hours": "5.5"})
    assert response.status_code == 200
    assert 'id="panel-laghu-parashari"' in response.text
    state = json.loads(re.search(r'<script id="astro-state" type="application/json">([\s\S]*?)</script>', response.text)[1])
    assert state["laghu_parashari"]["ascendant"] == "Taurus"
    assert len(state["laghu_parashari"]["rules"]) == 42
