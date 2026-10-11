from fastapi.testclient import TestClient

from vedic_astro.web.app import app

client = TestClient(app)

_PERSON_A = {
    "birth_date": "1995-03-10",
    "birth_hour": "6",
    "birth_minute": "15",
    "birth_meridiem": "AM",
    "place_name": "Chennai, Tamil Nadu",
}
_PERSON_B = {
    "b_birth_date": "1992-11-22",
    "b_birth_hour": "2",
    "b_birth_minute": "45",
    "b_birth_meridiem": "PM",
    "b_place_name": "Bengaluru, Karnataka",
}
_COMMON = {"ayanamsha": "lahiri", "node_type": "mean"}


def test_single_person_flow_unaffected_when_match_not_requested() -> None:
    response = client.post("/", data={**_PERSON_A, **_COMMON})
    assert response.status_code == 200
    assert 'id="panel-chart"' in response.text
    assert "Marriage compatibility" not in response.text


def test_two_person_match_renders_compatibility_report() -> None:
    response = client.post(
        "/", data={**_PERSON_A, **_PERSON_B, **_COMMON, "include_match": "on"}
    )
    assert response.status_code == 200
    assert 'id="panel-chart"' in response.text
    assert "Marriage compatibility (Ashtakoot Guna Milan)" in response.text
    assert "Nadi" in response.text
    assert "Mangal Dosha" in response.text


def test_match_requested_but_person_a_ambiguous_preserves_person_b() -> None:
    data = {**_PERSON_A, **_PERSON_B, **_COMMON, "include_match": "on"}
    data["place_name"] = "Haripur"  # ambiguous within India
    response = client.post("/", data=data)
    assert response.status_code == 200
    assert "Which place did you mean?" in response.text
    # Person B's already-valid place must still be present in the form. The
    # city and the state live in separate fields now, so the text is split
    # across the city input and the selected option of the state dropdown.
    assert 'value="Bengaluru"' in response.text
    # Assert the state is *selected*, not merely present: every state is an
    # option, so checking for the option alone would pass regardless.
    assert '<option value="Karnataka" selected>' in response.text


def test_match_requested_but_person_b_ambiguous_shows_candidates_b() -> None:
    data = {**_PERSON_A, **_PERSON_B, **_COMMON, "include_match": "on"}
    data["b_place_name"] = "Haripur"  # ambiguous within India
    response = client.post("/", data=data)
    assert response.status_code == 200
    assert "Which place did you mean for the second person?" in response.text
    assert 'id="panel-chart"' not in response.text


def test_match_requested_with_invalid_second_person_time_shows_error() -> None:
    data = {**_PERSON_A, **_PERSON_B, **_COMMON, "include_match": "on"}
    data["b_birth_hour"] = ""
    data["b_birth_minute"] = ""
    response = client.post("/", data=data)
    assert response.status_code == 400
    assert "Second person" in response.text


def test_selecting_person_b_candidate_completes_match() -> None:
    data = {
        **_PERSON_A,
        **_COMMON,
        "include_match": "on",
        "b_birth_date": "1992-11-22",
        "b_birth_hour": "2",
        "b_birth_minute": "45",
        "b_birth_meridiem": "PM",
        "b_selected_latitude": "12.9716",
        "b_selected_longitude": "77.5946",
        "b_selected_timezone": "Asia/Kolkata",
        "b_selected_label": "Bengaluru, Karnataka, India",
    }
    response = client.post("/", data=data)
    assert response.status_code == 200
    assert "Marriage compatibility (Ashtakoot Guna Milan)" in response.text
    assert "Bengaluru, Karnataka, India" in response.text
