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


def test_rajahmundry_alias_does_not_hide_the_renamed_city() -> None:
    results = search_places("Rajahmundry, Andhra Pradesh")
    assert results[0].name == "Rajamahendravaram"
    assert results[0].latitude == pytest.approx(17.00517)
    assert results[0].longitude == pytest.approx(81.77784)
    # The smaller exact-name settlement stays available for disambiguation.
    assert any(r.name == "Rajahmundry" for r in results)
    assert all(r.state == "Andhra Pradesh" for r in results)


def test_rjy_shorthand_resolves_the_city_with_ist() -> None:
    results = search_places("rjy, Andhra Pradesh")
    assert len(results) == 1
    assert results[0].name == "Rajamahendravaram"
    assert resolve_utc_offset(results[0].latitude, results[0].longitude,
                              date(1998, 9, 4), time(0, 3), results[0].timezone) == 5.5


def test_indian_alternate_names_respect_the_state_filter() -> None:
    assert not search_places("rjy, Tamil Nadu")


def test_nonpositive_result_limit_returns_no_places() -> None:
    assert search_places("Chennai", limit=0) == []
    assert search_places("Chennai", limit=-1) == []


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


def test_misspelt_state_no_longer_discards_a_matching_city() -> None:
    # "Andra" for "Andhra" used to return nothing at all, even though the
    # city itself was spelt perfectly.
    results = search_places("Vijayawada, Andra Pradesh")
    assert results[0].name == "Vijayawada"
    assert results[0].state == "Andhra Pradesh"


def test_state_written_without_its_space_is_understood() -> None:
    results = search_places("Chennai, Tamilnadu")
    assert results[0].name == "Chennai"
    assert results[0].state == "Tamil Nadu"


def test_renamed_state_still_resolves() -> None:
    results = search_places("Cuttack, Orissa")
    assert results[0].state == "Odisha"


def test_city_and_state_without_a_comma() -> None:
    results = search_places("Vijayawada Andhra Pradesh")
    assert results[0].name == "Vijayawada"
    assert results[0].state == "Andhra Pradesh"


def test_typo_correcting_to_an_alternate_name_beats_a_lookalike_village() -> None:
    # "Banglore" is close to the alternate name "Bangalore", and only
    # distantly close to a village called Bangora.
    results = search_places("Banglore")
    assert results[0].name == "Bengaluru"


def test_exact_name_outranks_a_larger_place_matching_by_alternate_name() -> None:
    results = search_places("Visakhapatnam")
    assert results[0].name == "Visakhapatnam"


def test_weak_prefix_match_does_not_suppress_the_spelling_correction() -> None:
    # "Chennia" prefix-matches a village called Chenniahnapalya, which used
    # to be returned as though it settled the query.
    results = search_places("Chennia")
    assert results[0].name == "Chennai"


def test_confident_match_is_picked_for_an_unambiguous_typo() -> None:
    from vedic_astro.geocode import pick_confident_match

    matches = search_places("Chennia")
    chosen = pick_confident_match("Chennia", matches)
    assert chosen is not None and chosen.name == "Chennai"


def test_genuinely_ambiguous_name_is_not_picked_automatically() -> None:
    from vedic_astro.geocode import pick_confident_match

    # Hyderabad exists in Telangana and in Sindh; only the user knows which.
    matches = search_places("Hyderbad")
    assert len(matches) > 1
    assert pick_confident_match("Hyderbad", matches) is None

    # Villages sharing one name across many states stay a real choice.
    assert pick_confident_match("Haripur", search_places("Haripur")) is None


def test_populated_namesake_outranks_a_larger_alternate_name_match() -> None:
    # Delhi lists "New Delhi" among its alternate names and is far larger,
    # but New Delhi is a real city in its own right.
    results = search_places("New Delhi, Delhi")
    assert results[0].name == "New Delhi"


def test_state_repeated_in_the_city_box_still_resolves() -> None:
    # The form has a state dropdown and a city box; people still type the
    # whole "City State" into the city box, which duplicates the state.
    results = search_places("Vijayawada Andhra Pradesh, Andhra Pradesh")
    assert results[0].name == "Vijayawada"
    assert results[0].state == "Andhra Pradesh"
