import html
import importlib
import json
import re

import pytest
from fastapi.testclient import TestClient

from vedic_astro.geocode import PlaceMatch
from vedic_astro.web.app import app
from vedic_astro.web.birth_place import prepare_birth_place

client = TestClient(app)
web = importlib.import_module("vedic_astro.web.app")
BASE = {"birth_date": "04/09/1998", "birth_hour": "12", "birth_minute": "3", "birth_meridiem": "AM"}


def bootstrap(response):
    return json.loads(re.search(r'<script id="astro-state" type="application/json">(.*?)</script>', response.text, re.S).group(1))


def test_selected_state_resolves_city_and_survives_editing():
    response = client.post("/", data=BASE | {"place_name": "rjy", "birth_state": "Andhra Pradesh"})
    assert response.status_code == 200
    state = bootstrap(response)
    assert state["resolved_place"] == "Rajamahendravaram, Andhra Pradesh, India"
    assert state["birth_data"]["latitude"] == pytest.approx(17.00517)
    assert state["form_values"]["place_name"] == "rjy"
    assert state["form_values"]["birth_state"] == "Andhra Pradesh"


def test_wrong_state_does_not_fall_back_to_another_state():
    response = client.post("/", data=BASE | {"place_name": "rjy", "birth_state": "Tamil Nadu"})
    assert response.status_code == 400
    assert "No place found" in response.text
    assert not bootstrap(response)["has_chart"]


def test_indian_dropdown_cannot_resolve_foreign_same_region(monkeypatch):
    monkeypatch.setattr(web, "search_places", lambda query: [PlaceMatch("Lahore", "Punjab", "Pakistan", 31.55, 74.34, "Asia/Karachi")])
    response = client.post("/", data=BASE | {"place_name": "Lahore", "birth_state": "Punjab"})
    assert response.status_code == 400
    assert not bootstrap(response)["has_chart"]


def test_state_form_validation_and_manual_coordinate_override():
    response = client.post("/", data=BASE | {"place_name": "rjy", "birth_state": "Made-up state"})
    assert response.status_code == 400
    assert "Choose a state or union territory" in response.text
    response = client.post("/", data=BASE | {"birth_state": "Andhra Pradesh", "manual_latitude": "17.00517", "manual_longitude": "81.77784", "manual_utc_offset_hours": "5.5"})
    assert response.status_code == 200
    assert bootstrap(response)["has_chart"]


def test_candidate_choice_preserves_both_city_and_state_pairs(monkeypatch):
    choices = [PlaceMatch("Haripur", "Andhra Pradesh", "India", 17.0, 81.0, "Asia/Kolkata"),
               PlaceMatch("Haripur", "Andhra Pradesh", "India", 16.0, 80.0, "Asia/Kolkata")]
    calls = []
    def search(query):
        calls.append(query)
        return choices if query == "Haripur, Andhra Pradesh" else [PlaceMatch("Chennai", "Tamil Nadu", "India", 13.08784, 80.27847, "Asia/Kolkata")]
    monkeypatch.setattr(web, "search_places", search)
    response = client.post("/", data=BASE | {
        "place_name": "Haripur", "birth_state": "Andhra Pradesh", "include_match": "on",
        "b_birth_date": "15/06/1990", "b_birth_hour": "8", "b_birth_minute": "30", "b_birth_meridiem": "AM",
        "b_place_name": "Chennai", "b_birth_state": "Tamil Nadu",
    })
    assert response.status_code == 200
    candidate = re.search(r'<form[^>]*class="candidate-form"[^>]*>(.*?)</form>', response.text, re.S).group(1)
    fields = {name: html.unescape(value) for name, value in re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]*)">', candidate)}
    assert fields["birth_state"] == "Andhra Pradesh"
    assert fields["place_name"] == "Haripur"
    assert fields["b_birth_state"] == "Tamil Nadu"
    assert fields["b_place_name"] == "Chennai"
    picked = client.post("/", data=fields)
    assert picked.status_code == 200
    state = bootstrap(picked)
    assert state["has_match"]
    assert state["form_values"]["birth_state"] == "Andhra Pradesh"
    assert state["form_values"]["b_birth_state"] == "Tamil Nadu"
    assert set(calls) == {"Haripur, Andhra Pradesh", "Chennai, Tamil Nadu"}


@pytest.mark.parametrize("city,state,expected", [
    (" Chennai ", "Tamil Nadu", ("Chennai", "Tamil Nadu", "Chennai, Tamil Nadu")),
    ("Chennai, India", "Tamil Nadu", ("Chennai", "Tamil Nadu", "Chennai, Tamil Nadu")),
    ("rjy, Andhra Pradesh", "", ("rjy", "Andhra Pradesh", "rjy, Andhra Pradesh")),
    ("Bhubaneswar, Orissa", "", ("Bhubaneswar", "Odisha", "Bhubaneswar, Orissa")),
    ("London, England", "other", ("London, England", "other", "London, England")),
    ("London, England", "", ("London, England", "", "London, England")),
    ("", "Andhra Pradesh", ("", "Andhra Pradesh", "")),
])
def test_location_fields_keep_legacy_and_international_queries(city, state, expected):
    assert prepare_birth_place(city, state) == expected
