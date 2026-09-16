"""Offline place-name -> coordinates + UTC offset resolution. No network calls.

Two local data sources, both bundled with the app - nothing is fetched at
runtime:

- `data/india_places.db`: a SQLite database (built once by
  scripts/build_india_places_db.py from GeoNames' public India dump) holding
  ~558,000 Indian populated places - cities down to small villages - each
  with its state already resolved, searched via SQLite's FTS5 full-text
  index. This is the primary source, since this app is India-focused.
- `geonamescache` + `reverse_geocoder`: a ~235,000-place global dataset (used
  as a fallback for non-India places), with `reverse_geocoder` resolving the
  state/region name for any country from its own bundled dataset.

If neither finds an exact or prefix match, `difflib` suggests close spellings
as a last resort (for genuine typos - a place with no match anywhere nearby
in spelling simply isn't in either dataset, most often a very small hamlet
GeoNames itself doesn't track).
"""

from __future__ import annotations

import difflib
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import geonamescache
import reverse_geocoder
from timezonefinder import TimezoneFinder

_CityRecord = dict[str, Any]

_INDIA_DB_PATH = Path(__file__).resolve().parent / "data" / "india_places.db"

# min_city_population=500 selects geonamescache's most granular bundled
# dataset (~235,000 places instead of the ~34,000-place default cutoff of
# 15,000), used only as the non-India fallback now that India itself is
# covered by the much more complete india_places.db above.
_cache = geonamescache.GeonamesCache(min_city_population=500)
_timezone_finder = TimezoneFinder()

_ALL_CITIES: list[_CityRecord] = list(_cache.get_cities().values())
_CITIES_WITH_LOWER_NAME: list[tuple[_CityRecord, str]] = [
    (city, str(city["name"]).lower()) for city in _ALL_CITIES
]
_ALTERNATE_NAME_INDEX: dict[str, list[_CityRecord]] = {}
for _city in _ALL_CITIES:
    for _alt in _city.get("alternatenames", []):
        _ALTERNATE_NAME_INDEX.setdefault(str(_alt).lower(), []).append(_city)
_UNIQUE_GLOBAL_NAMES: list[str] = list({name for _, name in _CITIES_WITH_LOWER_NAME})


@dataclass(frozen=True)
class PlaceMatch:
    name: str
    state: str
    country: str
    latitude: float
    longitude: float
    timezone: str


def _country_name(country_code: str) -> str:
    countries = _cache.get_countries()
    return str(countries.get(country_code, {}).get("name", country_code))


_RESOLVE_CAP = 50  # cap how many name-matches get a state lookup, for broad queries


def _prefer_exact(matches: list[PlaceMatch], city_lower: str) -> list[PlaceMatch]:
    """If any result's name exactly matches the query, keep only those -
    otherwise a query like "Chennai" would also drag in unrelated prefix
    matches like "Chennaikan Koppal" into needless disambiguation, even
    though there's really only one clear answer.
    """
    exact = [m for m in matches if m.name.lower() == city_lower]
    return exact if exact else matches


def _search_india_db(city_lower: str, region_lower: str, limit: int) -> list[PlaceMatch]:
    if not _INDIA_DB_PATH.exists():
        return []
    fts_term = '"' + city_lower.replace('"', '""') + '"*'
    conn = sqlite3.connect(_INDIA_DB_PATH)
    try:
        rows = conn.execute(
            """
            SELECT p.name, p.state, p.latitude, p.longitude, p.timezone
            FROM places_fts f JOIN places p ON p.geonameid = f.rowid
            WHERE places_fts MATCH ?
            ORDER BY (LOWER(p.name) != ?), p.population DESC
            LIMIT ?
            """,
            (fts_term, city_lower, max(limit * 10, 200)),
        ).fetchall()
    except sqlite3.OperationalError:
        # A query with FTS5-special characters (e.g. bare quotes) that still
        # fails to parse - treat as no matches rather than error the request.
        return []
    finally:
        conn.close()

    results: list[PlaceMatch] = []
    for name, state, lat, lon, tz in rows:
        if region_lower and region_lower not in state.lower() and region_lower not in "india":
            continue
        results.append(PlaceMatch(name=name, state=state, country="India", latitude=lat, longitude=lon, timezone=tz))

    return _prefer_exact(results, city_lower)[:limit]


def _global_name_matches(city_lower: str) -> list[_CityRecord]:
    # Primary-name substring matches and exact alternate-name/spelling matches
    # (e.g. "Madras" for Chennai), combined rather than one as a fallback for
    # the other - a real place that happens to share an alternate name's exact
    # spelling elsewhere shouldn't hide a better-known match either way.
    name_substring_matches = (city for city, name_lower in _CITIES_WITH_LOWER_NAME if city_lower in name_lower)
    alternate_matches = _ALTERNATE_NAME_INDEX.get(city_lower, [])
    combined = {id(city): city for city in name_substring_matches}
    combined.update({id(city): city for city in alternate_matches})
    matches = list(combined.values())
    matches.sort(key=lambda c: (str(c["name"]).lower() != city_lower, -int(c["population"])))
    return matches


def _search_global(city_lower: str, region_lower: str, limit: int) -> list[PlaceMatch]:
    name_matches = _global_name_matches(city_lower)
    if not name_matches:
        return []

    # Resolve state names for a capped, population-ranked slice - resolving
    # every match for a very broad query would be needlessly slow, and the
    # true target is essentially always among the most populous matches.
    capped = name_matches[:_RESOLVE_CAP]
    coords = [(float(city["latitude"]), float(city["longitude"])) for city in capped]
    # mode=1 (single-process, in-memory) - safer than the default multiprocessing
    # mode when called from inside a running web server.
    geo_results = reverse_geocoder.search(coords, mode=1, verbose=False)

    resolved = [
        (city, str(geo["admin1"]), _country_name(str(city["countrycode"])))
        for city, geo in zip(capped, geo_results)
    ]
    if region_lower:
        resolved = [
            (city, state, country)
            for city, state, country in resolved
            if region_lower in state.lower() or region_lower in country.lower()
        ]

    results = [
        PlaceMatch(
            name=str(city["name"]),
            state=state,
            country=country,
            latitude=float(city["latitude"]),
            longitude=float(city["longitude"]),
            timezone=str(city["timezone"]),
        )
        for city, state, country in resolved
    ]
    return _prefer_exact(results, city_lower)[:limit]


def _fuzzy_suggestions(city_lower: str, region_lower: str, limit: int) -> list[PlaceMatch]:
    """Last-resort typo tolerance: suggest close spellings from the global
    name list, then search each of those corrected spellings for real
    results. Only reached when both exact-ish searches above find nothing.
    """
    close_names = difflib.get_close_matches(city_lower, _UNIQUE_GLOBAL_NAMES, n=3, cutoff=0.72)
    suggestions: list[PlaceMatch] = []
    seen: set[tuple[str, str]] = set()
    for name in close_names:
        for match in _search_india_db(name, region_lower, limit) + _search_global(name, region_lower, limit):
            key = (match.name, match.state)
            if key not in seen:
                seen.add(key)
                suggestions.append(match)
    return suggestions[:limit]


def search_places(query: str, limit: int = 8) -> list[PlaceMatch]:
    """Find candidate places for free-text like "Chennai", "Chennai, Tamil
    Nadu", or "Chennai, India" - the part after the comma may be either a
    state/region or a country, matched either way. India is searched first
    (and in far more village-level detail); other countries fall back to a
    smaller global dataset. If nothing matches directly, close spellings are
    suggested as a typo-tolerant fallback.

    Returns the largest-population, most-exact matches first. Empty if the
    query is blank or matches nothing at all, even fuzzily.
    """
    query = query.strip()
    if not query:
        return []

    if "," in query:
        city_part, region_part = (part.strip() for part in query.split(",", 1))
    else:
        city_part, region_part = query, ""
    city_lower = city_part.lower()
    region_lower = region_part.lower()

    india_results = _search_india_db(city_lower, region_lower, limit)
    if india_results:
        return india_results

    global_results = _search_global(city_lower, region_lower, limit)
    if global_results:
        return global_results

    return _fuzzy_suggestions(city_lower, region_lower, limit)


def resolve_utc_offset(
    latitude: float,
    longitude: float,
    local_date: date,
    local_time: time,
    timezone_name: str | None = None,
) -> float:
    """UTC offset in effect at this place on this specific date (accounts for
    historical DST rules) - derived from local IANA tzdata, not a network call.
    """
    tz_name = timezone_name or _timezone_finder.timezone_at(lat=latitude, lng=longitude)
    if tz_name is None:
        raise ValueError(f"Could not resolve a timezone for coordinates ({latitude}, {longitude})")
    zone = ZoneInfo(tz_name)
    aware_local = datetime.combine(local_date, local_time, tzinfo=zone)
    offset = aware_local.utcoffset()
    if offset is None:
        raise ValueError(f"Could not resolve a UTC offset for timezone {tz_name!r}")
    return offset.total_seconds() / 3600
