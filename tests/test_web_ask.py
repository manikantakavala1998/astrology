from fastapi.testclient import TestClient

from vedic_astro.web.app import app

client = TestClient(app)

_PERSON_A = {
    "a_date": "1995-03-10",
    "a_time": "06:15:00",
    "a_lat": "13.0827",
    "a_lon": "80.2707",
    "a_utc_offset": "5.5",
    "ayanamsha": "lahiri",
    "node_type": "mean",
}


def test_ask_renders_chart_and_answer() -> None:
    response = client.post("/ask", data={**_PERSON_A, "question": "What is my ascendant sign?"})
    assert response.status_code == 200
    assert 'id="panel-chart"' in response.text
    assert "What is my ascendant sign?" in response.text
    assert 'class="answer-text"' in response.text


def test_ask_without_question_shows_error() -> None:
    response = client.post("/ask", data={**_PERSON_A, "question": ""})
    assert response.status_code == 400
    assert "Enter a question" in response.text


def test_ask_with_invalid_birth_data_shows_error() -> None:
    data = {**_PERSON_A, "a_date": "not-a-date", "question": "test"}
    response = client.post("/ask", data=data)
    assert response.status_code == 400
    assert "Could not rebuild the chart" in response.text


def test_ask_with_second_person_includes_match_report() -> None:
    data = {
        **_PERSON_A,
        "question": "Are we compatible?",
        "b_date": "1992-11-22",
        "b_time": "14:45:00",
        "b_lat": "12.9716",
        "b_lon": "77.5946",
        "b_utc_offset": "5.5",
    }
    response = client.post("/ask", data=data)
    assert response.status_code == 200
    assert "Marriage compatibility (Ashtakoot Guna Milan)" in response.text
    assert 'class="answer-text"' in response.text


def test_chart_page_includes_ask_form_hidden_fields() -> None:
    response = client.post(
        "/",
        data={
            "birth_date": "1995-03-10",
            "birth_hour": "6",
            "birth_minute": "15",
            "birth_meridiem": "AM",
            "manual_latitude": "13.0827",
            "manual_longitude": "80.2707",
            "manual_utc_offset_hours": "5.5",
            "ayanamsha": "lahiri",
            "node_type": "mean",
        },
    )
    assert response.status_code == 200
    assert 'action="/ask"' in response.text
    assert 'name="a_lat" value="13.0827"' in response.text
