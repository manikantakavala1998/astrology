import json
import re

import pytest
from fastapi.testclient import TestClient

from vedic_astro.web.app import app

client = TestClient(app)


def bootstrap(text: str) -> dict:
    match = re.search(r'<script id="astro-state" type="application/json">(.*?)</script>', text, re.DOTALL)
    assert match is not None
    return json.loads(match.group(1))


@pytest.fixture(scope="module")
def chart_response():
    return client.post("/", data={
        "name": "UI regression", "birth_date": "15/06/1990", "birth_hour": "8",
        "birth_minute": "30", "birth_meridiem": "AM", "manual_latitude": "13.0827",
        "manual_longitude": "80.2707", "manual_utc_offset_hours": "5.5",
    })


def test_frontend_assets_are_served_locally() -> None:
    for asset in ("app.js", "app.css"):
        response = client.get(f"/static/ui/{asset}")
        assert response.status_code == 200
        assert len(response.content) > 1000
    assert client.get("/static/celestial-header.png").status_code == 200
    response = client.get("/")
    state = bootstrap(response.text)
    assert state["has_chart"] is False
    assert 'action="/"' in response.text  # Native submission remains a fallback.
    assert state["form_values"]["ayanamsha"] == "lahiri"


def test_bhrigu_explorer_has_independent_years_and_extended_timing(chart_response):
    report = bootstrap(chart_response.text)['bhrigu']
    assert len(report['bcp']) == len(report['padma']) == 120
    assert len(report['bsp']) == 6
    assert report['bcp'][0]['start'] == '1990-06-15T08:30:00'
    assert report['bcp'][-1]['end'] < report['vimshottari']['periods'][-1]['end']
    assert len(report['permanent']) == 4
    assert report['dasha_year_days'] == 365.2425


def test_separate_balas_are_bootstrapped_with_native_calculation_fallback(chart_response):
    state = bootstrap(chart_response.text)
    assert len(state["balas"]["views"]) == 14
    assert state["balas"]["views"][1]["name"] == "Sthana Bala"
    assert "Separate bala names, calculations and input values" in chart_response.text
    assert "Ojayugma Rasi Amsa Bala" in chart_response.text
    labels = re.findall(r'<label for="tab-([^"]+)">', chart_response.text)
    assert labels[:7] == ["chart", "panchanga", "aspects", "balas", "dasha", "divisional", "ashtakavarga"]
    assert labels.count("balas") == 1


def test_overview_preserves_all_planets_and_table_fields(chart_response) -> None:
    assert chart_response.status_code == 200
    state = bootstrap(chart_response.text)
    assert state['birth_data']['birth_date'] == '1990-06-15'
    birth_field = re.search(r'<input[^>]*id="birth_date"[^>]*>', chart_response.text).group()
    assert 'value="15/06/1990"' in birth_field
    assert 'placeholder="DD/MM/YYYY"' in birth_field
    assert len(state["planets"]) == 9
    fields = {"planet", "sign", "degree_in_sign", "house", "nakshatra", "dignity", "retrograde"}
    assert all(fields <= planet.keys() for planet in state["planets"])
    assert all("pada" in planet["nakshatra"] for planet in state["planets"])
    assert [planet["planet"] for planet in state["planets"]] == [
        "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
    ]
    assert state["planets"][6]["dignity"] == "Own Sign"
    assert state["planets"][6]["retrograde"] is True


def test_overview_grids_keep_directions_elements_and_correct_lagnas(chart_response) -> None:
    state = bootstrap(chart_response.text)
    for code, ascendant in (("D1", "Cancer"), ("D9", "Virgo"), ("D10", "Taurus")):
        cells = [cell for row in state["grids"][code] for cell in row if cell]
        assert len(cells) == 12
        assert {cell["element_symbol"] for cell in cells} == {"🔥", "🌍", "💨", "💧"}
        assert {cell["direction"] for cell in cells} == {"N", "E", "S", "W"}
        lagna = next(cell for cell in cells if cell["is_ascendant"])
        assert lagna["sign"] == ascendant and lagna["house"] == 1
        natal_degrees = {planet["planet"][:2]: planet["degree_in_sign"] for planet in state["planets"]}
        labels = [label for cell in cells for label in cell["planets"]]
        assert len(labels) == 9
        assert all(label["natal_degree"] == natal_degrees[label["code"]] for label in labels)
    assert [entry["house"] for entry in state["kendra_lords"]] == [1, 4, 7]
    assert [entry["house"] for entry in state["trikona_lords"]] == [1, 5, 9]
    assert len(state["vimshottari"]["periods"]) == 9
    assert all(len(period["sub_periods"]) == 9 for period in state["vimshottari"]["periods"])


def test_every_existing_report_is_available_to_react(chart_response) -> None:
    expected_sections = {
        "chart", "dasha", "aspects", "classic-predictions", "yogas", "divisional",
        "ashtakavarga", "shani", "dosha", "balas", "bcp", "bsp", "padma", "panchanga", "tools", "brihat-jataka", "jaimini", "jaimini2", "laghu-parashari",
    }
    rendered_sections = set(re.findall(r'class="tab-panel" id="panel-([^"]+)"', chart_response.text))
    assert rendered_sections == expected_sections
    for control in ("bcp-year-120", "padma-year-120", "tab-padma", "tab-bsp", "subtab-balas-bhava"):
        assert f'id="{control}"' in chart_response.text
    assert 'data-chart-code="D144"' in chart_response.text
    assert 'panel-bnn' not in chart_response.text
    assert 'Bhrigu Nandi Nadi' not in chart_response.text


def test_jaimini2_is_separate_and_has_complete_native_catalog(chart_response) -> None:
    state = bootstrap(chart_response.text)
    book = state['jaimini2']
    assert book['author'] == 'Medavarapu Sampath Kumar'
    assert list(book['schemes']) == ['7']
    assert len(book['dasha_systems']) == 38
    assert '8' in state['jaimini']['schemes']
    assert state['jaimini']['dasha_systems'][0]['year_days'] != 360
    assert all(s['year_days'] == 360 for s in book['dasha_systems'])
    assert 'Anuchara' in chart_response.text and 'All 38 dasha methods' in chart_response.text
    assert 'aria-label="Jaimini South sign strength graph"' in chart_response.text
    assert all('rank' in row for row in book['strengths'])
    assert all('kind' in row and 'planets' in row for row in book['schemes']['7']['yogas'])
    assert len(book['predictions']['modules']) == 6
    assert 'Detailed prediction modules' in chart_response.text
    assert all('predictions' in system for system in book['dasha_systems'])


def test_aspect_views_are_calculated_and_available_in_native_fallback(chart_response) -> None:
    state = bootstrap(chart_response.text)
    report = state["aspect_tables"]
    planets = {p["planet"]: p for p in state["planets"]}
    assert [row["planet"] for row in report["vedic"]] == list(planets)
    assert [row["planet"] for row in report["western"]] == list(planets)
    assert report["western_default_orb"] == 6
    assert report["western_max_orb"] == 10
    for row in report["vedic"]:
        assert row["sign"] == planets[row["planet"]]["sign"]
        assert row["retrograde"] == planets[row["planet"]]["retrograde"]
    assert 'id="native-aspect-vedic"' in chart_response.text
    assert 'id="native-aspect-western"' in chart_response.text
    assert '<th scope="col">Aspected signs</th>' in chart_response.text
    assert chart_response.text.count('<th scope="col">Sign occupied</th>') == 2
    assert chart_response.text.count('<th scope="col">Aspected planets</th>') == 2
    for method in ("vedic", "western"):
        for row in report[method]:
            for link in row["aspects"]:
                assert link["target_sign"] == planets[link["target_planet"]]["sign"]
    panel = chart_response.text.split('id="panel-aspects"', 1)[1].split('id="panel-classic-predictions"', 1)[0]
    assert 'current-period' not in panel


def test_brihat_graph_conditions_are_structured_and_keep_the_original_labels(chart_response) -> None:
    strengths = bootstrap(chart_response.text)["brihat_jataka"]["strengths"]
    assert len(strengths) == 7
    for row in strengths:
        assert len(row["sthana_checks"]) == 5
        assert all(isinstance(check["supported"], bool) for check in row["sthana_checks"])
        assert row["sthana"] == [check["label"] for check in row["sthana_checks"] if check["supported"]]
        assert isinstance(row["chesta_supported"], bool)
        if row["planet"] in ("Sun", "Moon"):
            assert row["chesta_supported"] == (row["chesta"] == "Capricorn–Gemini")
        else:
            assert row["chesta_supported"] == (row["chesta"] == "Retrograde")


def test_predictions_and_all_divisional_amsa_tables_are_available(chart_response) -> None:
    report = bootstrap(chart_response.text)["brihat_jataka"]
    assert len(report["predictions"]["period_themes"]) == 8
    assert len([r for r in report["predictions"]["readings"] if r["category"] == "Planetary tendencies"]) == 7
    assert chart_response.text.count('class="compact-table amsa-ruler-table"') == 23
    assert chart_response.text.count('data-body="Ascendant"') == 23
    assert chart_response.text.count('class="divisional-layout with-amsa"') == 22
    for deity in ("Ganesha", "Sarpa", "Not separately defined", "Component rules"):
        assert deity in chart_response.text


def test_ashtakavarga_lagna_has_computed_scores_and_input_based_calculation(chart_response) -> None:
    # Restrict to this report: Brihat Jataka still has its own seven-planet charts.
    section = re.search(r'id="panel-ashtakavarga">(.*?)id="panel-shani"', chart_response.text, re.DOTALL).group(1)
    assert section.count('class="mini-chart-grid"') == 9
    assert 'data-ashtaka-planet="Lagna"' in section
    assert "held-chart-notice" not in section
    assert "Not shown on purpose" not in section
    lagna = re.search(r'data-ashtaka-planet="Lagna">(.*?)</div>\s*</div>\s*<details', section, re.DOTALL).group(1)
    scores = [int(value) for value in re.findall(r'data-bindus="(\d+)"', lagna)]
    assert len(scores) == 12 and sum(scores) == 49
    assert all(0 <= value <= 8 for value in scores)
    assert "Lagna Ashtakavarga contribution rules" in section
    assert "Lagna Ashtakavarga sign calculations" in section
    assert "Count each contributor" in section
    assert "337 bindus" in section


def test_bootstrap_escapes_user_text_at_script_boundary() -> None:
    name = '</script><script>alert("name")</script>'
    response = client.post("/", data={"name": name, "birth_date": "invalid"})
    assert response.status_code == 400
    assert name not in response.text
    assert bootstrap(response.text)["form_values"]["name"] == name


def test_dasha_detail_uses_the_same_app_shell() -> None:
    response = client.post("/dasha-detail", data={"lord": "invalid"})
    assert response.status_code == 400
    assert bootstrap(response.text)["page"] == "dasha"
    assert "Could not compute sub-periods" in response.text
    assert "/static/ui/app.js" in response.text
