import re
from datetime import date

import pytest

from fastapi.testclient import TestClient

from vedic_astro.web.app import _birth_date_input, _parse_birth_date, _to_24_hour_time, app

client = TestClient(app)


@pytest.mark.parametrize('value,expected', [
    ('04/09/1998', date(1998, 9, 4)), ('09/04/1998', date(1998, 4, 9)),
    ('29/02/2000', date(2000, 2, 29)), ('1998-09-04', date(1998, 9, 4)),
])
def test_birth_date_is_day_first_with_iso_compatibility(value, expected):
    assert _parse_birth_date(value) == expected
    assert _birth_date_input(value) == f'{expected.day:02d}/{expected.month:02d}/{expected.year:04d}'


@pytest.mark.parametrize('value', ['31/04/1998', '29/02/1900', '29/02/2023', '04/13/1998', '00/09/1998', '04/09/0000', '1998/09/04', 'invalid'])
def test_invalid_birth_date_is_rejected_and_preserved(value):
    with pytest.raises(ValueError, match='DD/MM/YYYY'):
        _parse_birth_date(value)
    assert _birth_date_input(value) == value


def test_to_24_hour_time_conversions() -> None:
    from datetime import time

    assert _to_24_hour_time(12, 0, "AM") == time(0, 0)  # midnight
    assert _to_24_hour_time(12, 0, "PM") == time(12, 0)  # noon
    assert _to_24_hour_time(1, 30, "AM") == time(1, 30)
    assert _to_24_hour_time(1, 30, "PM") == time(13, 30)
    assert _to_24_hour_time(11, 59, "PM") == time(23, 59)


def test_rjy_midnight_birth_keeps_city_and_removes_nadi_interface() -> None:
    response = client.post("/", data={
        "birth_date": "1998-09-04", "birth_hour": "12", "birth_minute": "3",
        "birth_meridiem": "AM", "place_name": "rjy, Andhra Pradesh",
        "ayanamsha": "lahiri", "node_type": "mean",
    })
    assert response.status_code == 200
    assert "Rajamahendravaram, Andhra Pradesh, India" in response.text
    assert 'id="panel-bnn"' not in response.text
    assert 'id="tab-bnn"' not in response.text
    assert "Bhrigu Nandi Nadi" not in response.text


def test_post_missing_hour_shows_friendly_error_not_422() -> None:
    # Regression: the hour/minute <select> placeholder options must submit an
    # empty string, not be entirely absent from the POST body - otherwise
    # FastAPI's own Form(...) validation rejects the request with a raw 422
    # before our error-handling ever runs (seen when a real browser somehow
    # posts without a value selected).
    response = client.post(
        "/",
        data={
            "birth_date": "1990-06-15",
            "birth_hour": "",
            "birth_minute": "",
            "birth_meridiem": "AM",
            "place_name": "Chennai, India",
            "ayanamsha": "lahiri",
            "node_type": "mean",
        },
    )
    assert response.status_code == 400
    assert "Invalid date or time" in response.text


def test_get_root_shows_empty_form() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Place of birth" in response.text
    assert "Generate chart" in response.text


def test_place_name_field_is_not_html_required() -> None:
    # Manual coordinates under Advanced are a documented, fully-supported
    # alternative to place search (_resolve_location prioritizes them over
    # place_name) - a hard HTML `required` on place_name would silently
    # block that path in a real browser (curl-based POSTs never exercise
    # client-side HTML5 validation, so this regressed unnoticed once).
    response = client.get("/")
    match = re.search(r'<input[^>]*id="place_name"[^>]*>', response.text, re.DOTALL)
    assert match is not None
    assert "required" not in match.group()


def test_post_with_place_name_renders_chart() -> None:
    response = client.post(
        "/",
        data={
            "birth_date": "1990-06-15",
            "birth_hour": "8",
            "birth_minute": "30",
            "birth_meridiem": "AM",
            "place_name": "Chennai, India",
            "ayanamsha": "lahiri",
            "node_type": "mean",
        },
    )
    assert response.status_code == 200
    assert 'id="panel-chart"' in response.text
    assert "Ascendant (Lagna)" in response.text


def test_post_with_place_name_renders_bcp_tab() -> None:
    response = client.post(
        "/",
        data={
            "birth_date": "1990-06-15",
            "birth_hour": "8",
            "birth_minute": "30",
            "birth_meridiem": "AM",
            "place_name": "Chennai, India",
            "ayanamsha": "lahiri",
            "node_type": "mean",
        },
    )
    assert response.status_code == 200
    assert 'id="panel-bcp"' in response.text
    assert "Bhrigu Chakra Paddhati" in response.text
    assert 'id="bcp-year-1"' in response.text
    assert 'id="bcp-year-108"' in response.text
    # Year 109 has no defined cycle ruler in the source (only 9 grahas).
    assert 'id="bcp-year-109"' in response.text
    assert "Not defined by this source past age 108" in response.text
    assert "BCP Longevity Indication" in response.text
    assert "Sampath Kumar Medavarapu" in response.text
    assert ("Rule 1 applies" in response.text) or ("Rule 2 applies" in response.text)
    assert 'id="panel-bsp"' in response.text
    assert 'id="panel-padma"' in response.text
    assert 'id="tab-bsp"' in response.text
    assert 'id="tab-padma"' in response.text


def test_post_with_place_name_renders_bsp_subtab() -> None:
    response = client.post(
        "/",
        data={
            "birth_date": "1990-06-15",
            "birth_hour": "8",
            "birth_minute": "30",
            "birth_meridiem": "AM",
            "place_name": "Chennai, India",
            "ayanamsha": "lahiri",
            "node_type": "mean",
        },
    )
    assert response.status_code == 200
    assert "Bhrigu Sarala Paddhati" in response.text
    assert "#6" in response.text and "#13" in response.text
    assert "Permanent House Notes" in response.text
    assert "#1" in response.text and "#2" in response.text and "#14" in response.text
    assert "Aries Spoilt" in response.text
    assert "Shukra (Venus) Reveals" in response.text


def test_post_with_place_name_renders_padma_chakra_subtab() -> None:
    response = client.post(
        "/",
        data={
            "birth_date": "1990-06-15",
            "birth_hour": "8",
            "birth_minute": "30",
            "birth_meridiem": "AM",
            "place_name": "Chennai, India",
            "ayanamsha": "lahiri",
            "node_type": "mean",
        },
    )
    assert response.status_code == 200
    assert "Padma Chakra Paddhati" in response.text
    assert "Gautam Dave" in response.text
    assert 'id="padma-year-1"' in response.text
    assert 'id="padma-year-120"' in response.text
    assert "Badhaka" in response.text
    assert "Vimshottari Dasha" in response.text
    assert "Chennai" in response.text


def test_post_renders_classic_predictions_tab_before_yogas() -> None:
    response = client.post(
        "/",
        data={
            "birth_date": "1990-06-15",
            "birth_hour": "8",
            "birth_minute": "30",
            "birth_meridiem": "AM",
            "place_name": "Chennai, India",
            "ayanamsha": "lahiri",
            "node_type": "mean",
        },
    )
    assert response.status_code == 200
    assert 'id="panel-classic-predictions"' in response.text
    assert "Classic Predictions" in response.text
    classic_index = response.text.index('id="tab-classic-predictions"')
    yogas_index = response.text.index('id="tab-yogas"')
    assert classic_index < yogas_index


def test_post_renders_shani_dosha_yogas_tabs_and_dignity_column() -> None:
    response = client.post(
        "/",
        data={
            "birth_date": "1990-06-15",
            "birth_hour": "8",
            "birth_minute": "30",
            "birth_meridiem": "AM",
            "manual_latitude": "13.0827",
            "manual_longitude": "80.2707",
            "manual_utc_offset_hours": "5.5",
            "ayanamsha": "lahiri",
            "node_type": "mean",
        },
    )
    assert response.status_code == 200
    assert 'id="panel-shani"' in response.text
    assert 'id="panel-dosha"' in response.text
    assert 'id="panel-yogas"' in response.text
    assert "Sade Sati" in response.text
    assert "Kantaka Shani" in response.text
    assert "Kalasarpa Dosha" in response.text
    assert "Kuja Dosha" in response.text
    assert "Guru Chandala Dosha" in response.text
    assert "Content coming soon" in response.text
    assert "Dignity" in response.text


def test_post_renders_balas_tab_with_all_three_subtabs() -> None:
    response = client.post(
        "/",
        data={
            "birth_date": "1990-06-15",
            "birth_hour": "8",
            "birth_minute": "30",
            "birth_meridiem": "AM",
            "manual_latitude": "13.0827",
            "manual_longitude": "80.2707",
            "manual_utc_offset_hours": "5.5",
            "ayanamsha": "lahiri",
            "node_type": "mean",
        },
    )
    assert response.status_code == 200
    assert 'id="panel-balas"' in response.text
    assert "Shadbala" in response.text
    assert "Vimshopaka Bala" in response.text
    assert "Bhava Bala" in response.text
    assert "Strong Enough" in response.text or "Below Required" in response.text
    assert "Dashavarga · 10 charts" in response.text
    assert "Shodashavarga · 16 charts" in response.text
    assert "strength scores are not yet implemented" not in response.text
    assert 'id="panel-jaimini"' in response.text
    assert "Janma Navaka" not in response.text


def test_post_with_manual_coordinates_renders_chart() -> None:
    response = client.post(
        "/",
        data={
            "birth_date": "1990-06-15",
            "birth_hour": "8",
            "birth_minute": "30",
            "birth_meridiem": "AM",
            "manual_latitude": "13.0827",
            "manual_longitude": "80.2707",
            "manual_utc_offset_hours": "5.5",
            "ayanamsha": "lahiri",
            "node_type": "mean",
        },
    )
    assert response.status_code == 200
    assert 'id="panel-chart"' in response.text


def test_post_ambiguous_place_shows_candidates() -> None:
    response = client.post(
        "/",
        data={
            "birth_date": "1990-06-15",
            "birth_hour": "8",
            "birth_minute": "30",
            "birth_meridiem": "AM",
            "place_name": "Haripur",  # ambiguous within India: villages across 16+ states
            "ayanamsha": "lahiri",
            "node_type": "mean",
        },
    )
    assert response.status_code == 200
    assert "Which place did you mean" in response.text
    assert 'id="panel-chart"' not in response.text


def test_post_unknown_place_shows_error() -> None:
    response = client.post(
        "/",
        data={
            "birth_date": "1990-06-15",
            "birth_hour": "8",
            "birth_minute": "30",
            "birth_meridiem": "AM",
            "place_name": "Zzzznotarealplacexyz123",
            "ayanamsha": "lahiri",
            "node_type": "mean",
        },
    )
    assert response.status_code == 400
    assert "No place found" in response.text


def test_post_no_place_or_coordinates_shows_error() -> None:
    response = client.post(
        "/",
        data={
            "birth_date": "1990-06-15",
            "birth_hour": "8",
            "birth_minute": "30",
            "birth_meridiem": "AM",
            "ayanamsha": "lahiri",
            "node_type": "mean",
        },
    )
    assert response.status_code == 400


def test_post_invalid_manual_latitude_shows_error() -> None:
    response = client.post(
        "/",
        data={
            "birth_date": "1990-06-15",
            "birth_hour": "8",
            "birth_minute": "30",
            "birth_meridiem": "AM",
            "manual_latitude": "200",  # out of range
            "manual_longitude": "80.2707",
            "manual_utc_offset_hours": "5.5",
            "ayanamsha": "lahiri",
            "node_type": "mean",
        },
    )
    assert response.status_code == 400


def test_post_unparseable_date_shows_error() -> None:
    response = client.post(
        "/",
        data={
            "birth_date": "not-a-date",
            "birth_hour": "8",
            "birth_minute": "30",
            "birth_meridiem": "AM",
            "place_name": "Chennai, India",
            "ayanamsha": "lahiri",
            "node_type": "mean",
        },
    )
    assert response.status_code == 400


def test_post_selected_candidate_renders_chart() -> None:
    response = client.post(
        "/",
        data={
            "birth_date": "1990-06-15",
            "birth_hour": "8",
            "birth_minute": "30",
            "birth_meridiem": "AM",
            "ayanamsha": "lahiri",
            "node_type": "mean",
            "selected_latitude": "13.08784",
            "selected_longitude": "80.27847",
            "selected_timezone": "Asia/Kolkata",
            "selected_label": "Chennai, Tamil Nadu, India",
        },
    )
    assert response.status_code == 200
    assert 'id="panel-chart"' in response.text
    assert "Chennai, Tamil Nadu, India" in response.text
