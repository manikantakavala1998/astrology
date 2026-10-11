from datetime import date, time

import pytest

from vedic_astro.bala_report import build_bala_report
from vedic_astro.chart import build_kundali_chart
from vedic_astro.models import BirthData, HouseSystem, Planet
from vedic_astro.rashi_bhava import RASHI_LORD, sign_for_longitude


@pytest.fixture(scope="module", params=["user", "chennai", "chennai_placidus"])
def chart(request):
    user = request.param == "user"
    return build_kundali_chart(BirthData(
        birth_date=date(1998, 9, 4) if user else date(1990, 6, 15),
        birth_time=time(0, 3) if user else time(8, 30),
        latitude=17.00517 if user else 13.0827, longitude=81.77784 if user else 80.2707,
        utc_offset_hours=5.5,
        house_system=HouseSystem.PLACIDUS if request.param == "chennai_placidus" else HouseSystem.WHOLE_SIGN,
    ))


def test_all_views_keep_engine_values_and_reconcile_unrounded_arithmetic(chart):
    report = build_bala_report(chart)
    views = {v["id"]: v for v in report["views"]}
    assert list(views) == ["shadbala", "sthana", "dig", "kala", "cheshta", "naisargika", "drik",
                           "shadvarga", "saptavarga", "dashavarga", "shodashavarga", "bhava", "ishta", "kashta"]
    for identifier, view in views.items():
        assert len(view["rows"]) == (12 if identifier == "bhava" else 7)
        for row in view["rows"]:
            assert sum(d["value"] for d in row["details"] if d["value"] is not None) == pytest.approx(row["value"], abs=1e-10)
            assert view["minimum"] <= row["value"] <= view["maximum"]
            if identifier == "bhava":
                assert row["value"] == chart.bhava_bala[int(row["key"][1:])].total_rupas
                continue
            planet = Planet(row["key"])
            result = chart.shadbala[planet]
            expected = {"shadbala": result.total_rupas, "sthana": result.sthana_bala.total,
                        "kala": result.kala_bala.total, "dig": result.dig_bala,
                        "cheshta": result.chesta_bala, "naisargika": result.naisargika_bala,
                        "drik": result.drik_bala, "ishta": result.ishta_phala, "kashta": result.kashta_phala}
            if identifier in expected:
                assert row["value"] == expected[identifier]
            else:
                assert row["value"] == getattr(chart.vimshopaka_bala[planet], f"{identifier}_score")


def test_division_contributions_and_house_lords_are_auditable(chart):
    views = {v["id"]: v for v in build_bala_report(chart)["views"]}
    for scheme, count in [("shadvarga", 6), ("saptavarga", 7), ("dashavarga", 10), ("shodashavarga", 16)]:
        for row in views[scheme]["rows"]:
            contributions = row["tables"][0]["rows"]
            assert len(contributions) == count
            assert sum(c[4] for c in contributions) == 20
            assert sum(c[6] for c in contributions) == pytest.approx(row["value"])
            assert all(c[6] == c[4] * c[5] / 20 for c in contributions)
            assert all(detail["name"].startswith("D") and "(" in detail["name"] for detail in row["details"])
    for row in views["sthana"]["rows"]:
        assert sum(c[-1] for c in row["tables"][0]["rows"]) == row["details"][1]["value"]
    for index, row in enumerate(views["bhava"]["rows"]):
        lord = RASHI_LORD[sign_for_longitude(chart.bhava_chalit_cusps[index])]
        assert row["planet"] == lord.value
        assert row["details"][0]["value"] == chart.shadbala[lord].total_rupas
        assert row["details"][-1]["value"] is None
        assert "Not calculated" in row["details"][-1]["calculation"]
    assert "not calculated" in views["kala"]["notes"][0]
    assert "simplified" in views["cheshta"]["notes"][0]


def test_report_retains_known_user_calculation_and_negative_aspects(chart):
    views = {v["id"]: v for v in build_bala_report(chart)["views"]}
    if chart.birth_data.birth_date == date(1998, 9, 4):
        sun = views["sthana"]["rows"][0]
        assert sun["value"] == pytest.approx(194.5942538152409, abs=1e-7)
        assert [d["value"] for d in sun["details"]][1:] == [102, 15, 60, 0]
    else:
        assert views["drik"]["minimum"] < 0
        assert any(row["value"] < 0 for row in views["drik"]["rows"])
    # Natural strength is fixed, independent of input date and house system.
    assert [row["value"] for row in views["naisargika"]["rows"]] == pytest.approx(
        [60, 360/7, 120/7, 180/7, 240/7, 300/7, 60/7])
