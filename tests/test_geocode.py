from datetime import date, time

import pytest

from vedic_astro.geocode import resolve_utc_offset, search_places


def test_search_finds_chennai() -> None:
    results = search_places("Chennai")
    assert any(
        r.name == "Chennai" and r.country == "India" and r.state == "Tamil Nadu"
        for r in results
    )


def test_search_by_alternate_name_madras() -> None:
    results = search_places("Madras")
    assert any(r.name == "Chennai" for r in results)


def test_search_with_country_filter() -> None:
    results = search_places("Chennai, India")
    assert all(r.country == "India" for r in results)
    assert len(results) >= 1


def test_search_with_state_filter() -> None:
    # The primary expected usage: "City, State" (not "City, Country").
    results = search_places("Chennai, Tamil Nadu")
    assert len(results) >= 1
    assert all(r.state == "Tamil Nadu" for r in results)
    assert any(r.name == "Chennai" for r in results)


def test_search_empty_query_returns_nothing() -> None:
    assert search_places("") == []
    assert search_places("   ") == []


def test_search_nonexistent_place_returns_nothing() -> None:
    assert search_places("Zzzznotarealplacexyz123") == []


def test_search_typo_suggests_close_spelling() -> None:
    # "chenai" (missing an "n") isn't an exact/prefix match for "Chennai" -
    # the fuzzy fallback should still surface it as a suggestion.
    results = search_places("chenai")
    assert any(r.name == "Chennai" for r in results)




def test_search_ambiguous_name_returns_multiple() -> None:
    # "Haripur" exists in villages across more than a dozen Indian states -
    # a realistic in-scope disambiguation case for this India-focused app.
    results = search_places("Haripur")
    assert len(results) > 1
    # The state name is exactly what lets a user tell these apart.
    states = {r.state for r in results}
    assert len(states) > 1
    assert all(r.state for r in results)


def test_search_falls_back_to_global_when_not_in_india() -> None:
    # "Springfield" also exists in India (Tamil Nadu), so an unqualified
    # search returns that - but explicitly asking for a non-Indian state
    # must still reach the global (non-India) dataset as a fallback.
    results = search_places("Springfield, Illinois")
    assert len(results) >= 1
    assert all(r.state == "Illinois" and r.country == "United States" for r in results)


def test_resolve_utc_offset_chennai_matches_known_ist() -> None:
    # India Standard Time is a fixed UTC+5:30 year-round (no DST).
    offset = resolve_utc_offset(13.0827, 80.2707, date(1990, 6, 15), time(8, 30), "Asia/Kolkata")
    assert offset == pytest.approx(5.5)


def test_resolve_utc_offset_without_timezone_name_uses_coordinates() -> None:
    offset = resolve_utc_offset(13.0827, 80.2707, date(1990, 6, 15), time(8, 30))
    assert offset == pytest.approx(5.5)


def test_resolve_utc_offset_accounts_for_dst() -> None:
    # New York: EST (UTC-5) in January, EDT (UTC-4) in July.
    winter_offset = resolve_utc_offset(40.7128, -74.0060, date(2024, 1, 15), time(12, 0), "America/New_York")
    summer_offset = resolve_utc_offset(40.7128, -74.0060, date(2024, 7, 15), time(12, 0), "America/New_York")
    assert winter_offset == pytest.approx(-5.0)
    assert summer_offset == pytest.approx(-4.0)
