from copy import deepcopy
from datetime import date, time

import pytest

from vedic_astro.brihat_jataka import build_brihat_report, lunar_yogas, nabhasa_yogas
from vedic_astro.brihat_predictions import SIGN_READINGS, build_predictions
from vedic_astro.chart import build_kundali_chart
from vedic_astro.models import BirthData, Planet, SIGNS_IN_ORDER, Sign
from vedic_astro.nakshatra import nakshatra_for_longitude
from vedic_astro.rashi_bhava import sign_for_longitude


@pytest.fixture(scope="module")
def natal():
    chart = build_kundali_chart(BirthData(birth_date=date(1998, 9, 4), birth_time=time(0, 3),
                                       latitude=17.00517, longitude=81.77784, utc_offset_hours=5.5))
    return chart, build_brihat_report(chart)


def at(position, longitude):
    return position.model_copy(update={"longitude": longitude, "degree_in_sign": longitude % 30,
                                       "sign": sign_for_longitude(longitude), "nakshatra": nakshatra_for_longitude(longitude)})


def test_known_chart_selects_real_placements_and_distinct_book_references(natal):
    chart, report = natal
    readings = {row["id"]: row for row in report["predictions"]["readings"]}
    assert readings["sign-sun"]["title"] == "Sun in Leo"
    assert readings["sign-sun"]["reference"] == "XVIII.2"
    assert readings["sign-mars"]["title"] == "Mars in Cancer"
    assert "abroad" in readings["sign-mars"]["summary"]
    assert readings["sign-mars"]["reference"] == "XVIII.6"
    assert readings["sign-jupiter"]["title"] == "Jupiter in Pisces"
    assert "Administration" in readings["sign-jupiter"]["summary"]
    assert readings["sign-moon"]["chapter"] == 17
    assert "later addition" in readings["sign-moon"]["note"]
    assert len(readings) == len(report["predictions"]["readings"])
    assert "working away from home" in readings["sign-mars"]["plain_summary"]
    assert all(row["rule"] for row in readings.values())
    assert all(1 <= row["chapter"] <= 28 and row["evidence"] for row in readings.values())
    assert len([row for row in readings.values() if row["category"] == "Work & livelihood"]) == 3
    assert {row["planet"] for row in report["strengths"]} == {p.planet.value for p in chart.planets[:7]}


def test_sign_catalog_covers_all_84_placements_and_no_nodes():
    assert set(SIGN_READINGS) == {p.value for p in list(Planet)[:7]}
    assert all(len(rows) == len(SIGNS_IN_ORDER) for rows in SIGN_READINGS.values())


def test_sun_deep_exaltation_exception_is_not_the_general_aries_reading(natal):
    chart, original = natal
    report = deepcopy(original)
    report["strengths"][0]["sign"] = "Aries"
    special = chart.model_copy(update={"planets": [at(chart.planets[0], 10), *chart.planets[1:]]})
    normal = chart.model_copy(update={"planets": [at(chart.planets[0], 11), *chart.planets[1:]]})
    assert "settled life" in build_predictions(special, report)["readings"][0]["summary"]
    assert "travel" in build_predictions(normal, report)["readings"][0]["summary"]


def test_cancelled_kemadruma_does_not_create_an_adverse_prediction(natal):
    chart, original = natal
    planets = [at(p, 5) for p in chart.planets[:7]]
    report = deepcopy(original)
    report["lunar"] = lunar_yogas(planets, Sign.ARIES)
    row = next(row for row in report["lunar"] if row["name"].startswith("Kemadruma"))
    assert row["matched"] and row["cancellation_present"] and not row["active"]
    predictions = build_predictions(chart, report)
    assert not any(row["title"].startswith("Kemadruma") for row in predictions["readings"])
    # Remove both evaluated cancellation conditions: Moon in a non-kendra,
    # eligible planets elsewhere, and no eligible body on either side of Moon.
    planets = [at(p, 95 if p.planet != Planet.MOON else 5) for p in chart.planets[:7]]
    report["lunar"] = lunar_yogas(planets, Sign.PISCES)
    predictions = build_predictions(chart, report)
    assert any(row["title"].startswith("Kemadruma") for row in predictions["readings"])


def test_both_sides_of_moon_emit_durudhura_without_duplicate_single_side_effects(natal):
    chart, original = natal
    planets = [at(p, {Planet.MOON: 5, Planet.MARS: 35, Planet.VENUS: 335}.get(p.planet, 95)) for p in chart.planets[:7]]
    report = deepcopy(original)
    report["lunar"] = lunar_yogas(planets, Sign.ARIES)
    titles = {row["title"] for row in build_predictions(chart, report)["readings"]}
    assert "Durudhura" in titles and "Sunapha" not in titles and "Anapha" not in titles


def test_superseded_nabhasa_effects_are_excluded(natal):
    chart, original = natal
    planets = [at(p, 65 + i) for i, p in enumerate(chart.planets[:7])]
    report = deepcopy(original)
    report["nabhasa"] = nabhasa_yogas(planets, Sign.GEMINI, {p.planet: 1 for p in planets})
    titles = {row["title"] for row in build_predictions(chart, report)["readings"]}
    assert "Gola" in titles and "Nala" not in titles


def test_bav_reading_handles_four_as_mixed_and_neighbouring_counts(natal):
    chart, original = natal
    report = deepcopy(original)
    for row, count in zip(report["ashtakavarga"], (3, 4, 5, 3, 4, 5, 4)):
        row["bindus"] = count
    readings = {row["id"]: row for row in build_predictions(chart, report)["readings"]}
    assert "difficulty" in readings["bav-sun"]["summary"]
    assert "mixed" in readings["bav-moon"]["summary"]
    assert "favourable" in readings["bav-mars"]["summary"]
    assert "transit" in readings["bav-mars"]["note"]


def test_lagna_period_uses_the_actual_rising_lord_and_all_periods_have_sources(natal):
    _, report = natal
    result = report["predictions"]
    assert result["lagna_lord"] == "Venus"
    themes = {row["lord"]: row for row in result["period_themes"]}
    assert set(themes) == {p.value for p in list(Planet)[:7]} | {"Lagna"}
    assert themes["Lagna"]["supportive"] == themes["Venus"]["supportive"]
    assert themes["Lagna"]["reference"] == "VIII.19; rising lord Venus: VIII.17"
    assert "commencement" in result["timing_note"]


def test_ayurdaya_steps_show_actual_birth_longitude_and_final_result(natal):
    chart, report = natal
    rows = {row["lord"]: row for row in report["dasha"]["worksheet"]["rows"]}
    sun = rows["Sun"]
    assert sun["longitude"] == chart.planets[0].longitude
    assert f"{sun['longitude']:.4f}" in sun["calculation_steps"][0]
    assert "Amsa base:" in sun["calculation_steps"][1]
    assert f"{sun['base']:.4f} years" in sun["calculation_steps"][1]
    assert f"= {sun['final_years']:.4f}" in sun["calculation_steps"][-1]
    assert "Ascendant position: Taurus" in rows["Lagna"]["calculation_steps"][0]
