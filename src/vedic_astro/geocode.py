"""Offline place-name -> coordinates + UTC offset resolution. No network calls.

Two local data sources, both bundled with the app - nothing is fetched at
runtime:

- `data/india_places.db`: a SQLite database (built once by
  scripts/build_india_places_db.py from GeoNames' public India dump) holding
  ~558,000 Indian populated places - cities down to small villages - each
  with its state already resolved, searched via SQLite's FTS5 full-text
  index. This is the primary source, since this app is India-focused.
- `geonamescache` + `reverse_geocoder`: a ~235,000-place global dataset (also
  supplying alternate names for Indian cities), with `reverse_geocoder` resolving the
  state/region name for any country from its own bundled dataset.

If neither finds an exact or prefix match, `difflib` suggests close spellings
as a last resort (for genuine typos - a place with no match anywhere nearby
in spelling simply isn't in either dataset, most often a very small hamlet
GeoNames itself doesn't track).
"""

from __future__ import annotations

import difflib
import functools
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
# Common local shorthand requested by the user. Resolve the city, not its
# airport or a similarly named village; coordinates still come from GeoNames.
_LOCAL_CITY_ALIASES = {"rjy": "rajamahendravaram"}


def _normalise(text: str) -> str:
    """Reduce a name to comparable characters. Case, spaces and punctuation
    are exactly what people vary - "Tamilnadu" for "Tamil Nadu", "Jammu &
    Kashmir" for "Jammu and Kashmir" - and none of it changes the place
    being named."""
    return "".join(character for character in text.lower() if character.isalnum())


# Spellings people type that are not what the dataset calls the state.
# Renames (Orissa, Pondicherry, Uttaranchal) stay in common use for decades,
# and a birth place is usually recalled by its older name.
_STATE_ALIASES = {
    "orissa": "Odisha",
    "pondicherry": "Puducherry",
    "pondichery": "Puducherry",
    "uttaranchal": "Uttarakhand",
    "newdelhi": "Delhi",
    "nctofdelhi": "Delhi",
    "ap": "Andhra Pradesh",
    "tn": "Tamil Nadu",
    "up": "Uttar Pradesh",
    "mp": "Madhya Pradesh",
    "wb": "West Bengal",
}

_india_state_index: dict[str, str] | None = None


def _india_states() -> dict[str, str]:
    """Normalised spelling -> the state name as the dataset writes it."""
    global _india_state_index
    if _india_state_index is None:
        index: dict[str, str] = {}
        if _INDIA_DB_PATH.exists():
            conn = sqlite3.connect(_INDIA_DB_PATH)
            try:
                for (state,) in conn.execute("SELECT DISTINCT state FROM places"):
                    index[_normalise(state)] = state
            except sqlite3.Error:
                pass
            finally:
                conn.close()
        for alias, canonical in _STATE_ALIASES.items():
            index.setdefault(alias, canonical)
        _india_state_index = index
    return _india_state_index


def _canonical_india_state(region: str) -> str | None:
    """The real Indian state behind a possibly misspelt one, or None when the
    text is not an Indian state at all - a country, or a foreign region.

    Returning None rather than a bad guess is what keeps "Springfield,
    Illinois" and "Chennai, India" working: both fall through to the plain
    substring behaviour below.
    """
    key = _normalise(region)
    if not key:
        return None
    index = _india_states()
    if key in index:
        return index[key]
    close = difflib.get_close_matches(key, list(index), n=1, cutoff=0.82)
    return index[close[0]] if close else None


def _region_matches(region: str, state: str, country: str = "India") -> bool:
    """Whether a place in `state` satisfies what the user typed after the
    comma. A typo in the state used to discard a perfectly matched city:
    "Vijayawada, Andra Pradesh" found nothing at all.
    """
    if not region:
        return True
    canonical = _canonical_india_state(region)
    if canonical is not None:
        return _normalise(state) == _normalise(canonical)
    key = _normalise(region)
    return key in _normalise(state) or key in _normalise(country)


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
    alternate_ids = {
        int(city["geonameid"])
        for city in _ALTERNATE_NAME_INDEX.get(city_lower, [])
        if city["countrycode"] == "IN"
    }
    conn = sqlite3.connect(_INDIA_DB_PATH)
    try:
        rows = conn.execute(
            """
            SELECT p.geonameid, p.population, p.name, p.state, p.latitude, p.longitude, p.timezone
            FROM places_fts f JOIN places p ON p.geonameid = f.rowid
            WHERE places_fts MATCH ?
            ORDER BY (LOWER(p.name) != ?), p.population DESC
            LIMIT ?
            """,
            (fts_term, city_lower, max(limit * 10, 200)),
        ).fetchall()
        if alternate_ids:
            placeholders = ",".join("?" for _ in alternate_ids)
            rows.extend(conn.execute(
                "SELECT geonameid, population, name, state, latitude, longitude, timezone "
                f"FROM places WHERE geonameid IN ({placeholders})",
                tuple(sorted(alternate_ids)),
            ).fetchall())
    except sqlite3.OperationalError:
        # A query with FTS5-special characters (e.g. bare quotes) that still
        # fails to parse - treat as no matches rather than error the request.
        return []
    finally:
        conn.close()

    # A renamed city is an exact alias match even if a small village still
    # bears its old name. Keep both for disambiguation and rank by population.
    rows = list({row[0]: row for row in rows}.values())

    # An exact match on the place's own name should win over a bigger place
    # that merely lists the query among its alternate names - typing
    # "Visakhapatnam" returned a neighbouring suburb, and "New Delhi"
    # returned Delhi, purely because those records are more populous.
    #
    # The exception is a renamed city, where the old name lingers on an
    # uninhabited hamlet while the city itself carries it as an alternate
    # name: "Rajahmundry" is a settlement of recorded population 0 and also
    # the former name of Rajamahendravaram. An unpopulated namesake loses to
    # a populated alternate; anything with recorded inhabitants does not,
    # which is a question about the place rather than a tuned ratio.
    exact_name_population = max(
        (row[1] for row in rows if row[2].lower() == city_lower), default=0
    )
    alternate_population = max(
        (row[1] for row in rows if row[0] in alternate_ids), default=0
    )
    prefer_exact_name = exact_name_population > 0 or alternate_population == 0

    def _rank(row: tuple[Any, ...]) -> tuple[Any, ...]:
        place_id, population, name = row[0], row[1], row[2]
        is_exact_name = name.lower() == city_lower
        return (
            not (is_exact_name or place_id in alternate_ids),
            not (prefer_exact_name and is_exact_name),
            -population,
            place_id,
        )

    rows.sort(key=_rank)
    results: list[PlaceMatch] = []
    exact_results: list[PlaceMatch] = []
    for place_id, _population, name, state, lat, lon, tz in rows:
        if not _region_matches(region_lower, state):
            continue
        match = PlaceMatch(name=name, state=state, country="India", latitude=lat, longitude=lon, timezone=tz)
        results.append(match)
        if name.lower() == city_lower or place_id in alternate_ids:
            exact_results.append(match)

    return (exact_results or results)[:limit]


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
            if _region_matches(region_lower, state, country)
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


_fuzzy_pool: list[str] | None = None


def _fuzzy_name_pool() -> list[str]:
    """Every spelling worth correcting towards, primary names and alternate
    names alike. The alternates matter more than the primaries here: people
    type "Banglore", and the correction that leads anywhere is "Bangalore",
    which is an alternate name of Bengaluru. Matching primary names only
    sent that query to a village called Bangora instead.

    Built on first use, not at import, so a session that never makes a typo
    never pays for it.
    """
    global _fuzzy_pool
    if _fuzzy_pool is None:
        _fuzzy_pool = list({*_UNIQUE_GLOBAL_NAMES, *_ALTERNATE_NAME_INDEX})
    return _fuzzy_pool


@functools.lru_cache(maxsize=256)
def _fuzzy_candidates(city_lower: str) -> tuple[str, ...]:
    """Names worth scoring against the query.

    difflib over the whole million-name pool takes about two and a half
    seconds; restricting it to names of a similar length that start with the
    same letter costs a fraction of that. The trade is real but narrow: a
    typo in the very first letter is no longer corrected.
    """
    shortest, longest = len(city_lower) - 2, len(city_lower) + 2
    initial = city_lower[:1]
    return tuple(
        name
        for name in _fuzzy_name_pool()
        if shortest <= len(name) <= longest and name[:1] == initial
    )


_CLOSE_SPELLING_COUNT = 5
_CLOSE_SPELLING_CUTOFF = 0.72


@functools.lru_cache(maxsize=256)
def _close_spellings(city_lower: str) -> tuple[str, ...]:
    """Close spellings for a query, best first, cached.

    One shared result rather than one per caller: scanning the name pool is
    the expensive part of a typo lookup, and the same query needs it twice -
    once to search, once to judge whether the answer is clear enough to use
    without asking. Callers that want fewer take a slice.
    """
    return tuple(
        difflib.get_close_matches(
            city_lower,
            _fuzzy_candidates(city_lower),
            n=_CLOSE_SPELLING_COUNT,
            cutoff=_CLOSE_SPELLING_CUTOFF,
        )
    )


def _fuzzy_suggestions(city_lower: str, region_lower: str, limit: int) -> list[PlaceMatch]:
    """Last-resort typo tolerance: find close spellings, then search each
    corrected spelling for real places. Only reached when the exact-ish
    searches above find nothing.

    Corrections are tried best-first, so the results of the closest spelling
    lead the list and the app can act on them without asking.
    """
    close_names = _close_spellings(city_lower)[:3]
    suggestions: list[PlaceMatch] = []
    seen: set[tuple[str, str]] = set()
    for name in close_names:
        for match in _search_india_db(name, region_lower, limit) + _search_global(name, region_lower, limit):
            key = (match.name, match.state)
            if key not in seen:
                seen.add(key)
                suggestions.append(match)
    return suggestions[:limit]


def _similarity(query: str, name: str) -> float:
    return difflib.SequenceMatcher(None, query, name.lower()).ratio()


def _is_confident(results: list[PlaceMatch], city_lower: str) -> bool:
    """Whether these results really answer what was typed.

    A full-text prefix search answers "Chennia" with a village called
    Chenniahnapalya: a genuine match on the letters, and plainly not what
    was meant. Treating that as settled is what stopped the typo correction
    from ever running. An exact name - or a known alternate name, which is
    how "Madras" reaches Chennai - is settled; a prefix match alone is not.
    """
    if city_lower in _ALTERNATE_NAME_INDEX:
        return True
    key = _normalise(city_lower)
    return any(_normalise(match.name) == key for match in results)


def _merge_by_similarity(
    primary: list[PlaceMatch], corrected: list[PlaceMatch], city_lower: str, limit: int
) -> list[PlaceMatch]:
    """Rank weak prefix matches and spelling corrections together, closest
    spelling first, so the obvious city beats the obscure village."""
    combined: list[PlaceMatch] = []
    seen: set[tuple[str, str]] = set()
    for match in primary + corrected:
        key = (match.name, match.state)
        if key not in seen:
            seen.add(key)
            combined.append(match)
    combined.sort(key=lambda match: -_similarity(city_lower, match.name))
    return combined[:limit]


def _lookup(city: str, region: str, limit: int) -> list[PlaceMatch]:
    city_lower = _LOCAL_CITY_ALIASES.get(city.lower(), city.lower())
    region_lower = region.lower()
    return (
        _search_india_db(city_lower, region_lower, limit)
        or _search_global(city_lower, region_lower, limit)
    )


def _comma_free_splits(query: str) -> list[tuple[str, str]]:
    """Ways to read "Vijayawada Andhra Pradesh" as a city and a state when
    the comma was left out.

    Only splits whose tail is recognisably an Indian state are offered, so a
    place whose name simply contains a space - New Delhi, Navi Mumbai - is
    never torn in half. Longest city first, because the city is the part
    that identifies the place.
    """
    words = query.split()
    splits = []
    for cut in range(len(words) - 1, 0, -1):
        tail = " ".join(words[cut:])
        if _canonical_india_state(tail) is not None:
            splits.append((" ".join(words[:cut]), tail))
    return splits


def search_places(query: str, limit: int = 8) -> list[PlaceMatch]:
    """Find candidate places for free text like "Chennai", "Chennai, Tamil
    Nadu", "Chennai Tamil Nadu" or "Chennai, India" - the part after the
    comma may be a state or a country, and the comma itself is optional when
    the trailing words name an Indian state. India is searched first (and in
    far more village-level detail); other countries fall back to a smaller
    global dataset.

    Misspellings are tolerated in both halves: the state is matched against
    the real state names allowing for typos and spacing, and an unmatched
    city falls back to close spellings.

    Returns the most-exact, largest-population matches first. Empty only if
    the query is blank or matches nothing at all, even fuzzily.
    """
    query = query.strip()
    if not query or limit <= 0:
        return []

    if "," in query:
        city_part, region_part = (part.strip() for part in query.split(",", 1))
    else:
        city_part, region_part = query, ""

    city_lower = _LOCAL_CITY_ALIASES.get(city_part.lower(), city_part.lower())
    results = _lookup(city_part, region_part, limit)
    if results:
        if _is_confident(results, city_lower):
            return results
        corrected = _fuzzy_suggestions(city_lower, region_part.lower(), limit)
        return _merge_by_similarity(results, corrected, city_lower, limit)

    if not region_part:
        for city_try, region_try in _comma_free_splits(query):
            results = _lookup(city_try, region_try, limit)
            if results:
                return results
    else:
        # The city half sometimes repeats the state: picking a state from the
        # form's dropdown and also typing it produces "Vijayawada Andhra
        # Pradesh, Andhra Pradesh", which matches nothing as written. Tried
        # only after the query as typed fails, so a city that genuinely ends
        # in a state name - New Delhi in Delhi - is never cut short.
        for city_try, _ in _comma_free_splits(city_part):
            results = _lookup(city_try, region_part, limit)
            if results:
                return results

    suggestions = _fuzzy_suggestions(city_lower, region_part.lower(), limit)
    if suggestions or region_part:
        return suggestions

    # A missing comma can also hide a misspelt city: "Vijayawda Andhra
    # Pradesh" matches nothing whole, and nothing split, until the city half
    # is corrected on its own.
    for city_try, region_try in _comma_free_splits(query):
        city_try_lower = _LOCAL_CITY_ALIASES.get(city_try.lower(), city_try.lower())
        suggestions = _fuzzy_suggestions(city_try_lower, region_try.lower(), limit)
        if suggestions:
            return suggestions
    return []


# How alike the query and a candidate must be, and how far ahead of the
# runner-up, before picking one without asking. Both thresholds were set
# against real queries: "Chennia" clears them and means Chennai, while
# "Hyderbad" does not, because Hyderabad in Telangana and Hyderabad in Sindh
# are equally good readings of it and only the user knows which was meant.
_CONFIDENT_SIMILARITY = 0.8
_CONFIDENT_MARGIN = 0.10


def pick_confident_match(query: str, matches: list[PlaceMatch]) -> PlaceMatch | None:
    """The one place this query obviously means, or None to go and ask.

    A misspelling should not cost the user a disambiguation click when there
    is only one sensible reading of it. It should still cost one when there
    is not: silently choosing between two real places would produce a chart
    for the wrong birthplace, and nothing on screen would look wrong.
    """
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    city = query.split(",", 1)[0].strip().lower()
    if _is_clear_winner([_similarity(city, match.name) for match in matches]):
        return matches[0]

    # Compare against the names people actually type, not only the official
    # one. "Banglore" is a poor match for "Bengaluru" and an excellent one
    # for its alternate name "Bangalore", so scoring the official name alone
    # made an obvious correction look like a coin toss.
    if _is_clear_winner(_scores_including_alternate_names(city, matches)):
        return matches[0]
    return None


# A score this high means the query is all but one of that place's own
# names. Exactly one candidate reaching it is as clear as a sole result.
_NEAR_EXACT_SIMILARITY = 0.9


def _is_clear_winner(scores: list[float]) -> bool:
    if len(scores) < 2:
        return bool(scores)
    if scores[0] < _CONFIDENT_SIMILARITY:
        return False
    if scores[0] - max(scores[1:]) >= _CONFIDENT_MARGIN:
        return True
    # "Banglore" is all but exactly Bangalore, and merely similar to Bangor,
    # Bangora and Bangori - which crowd the runner-up slot without any of
    # them being a plausible reading of it.
    near_exact = [score for score in scores if score >= _NEAR_EXACT_SIMILARITY]
    return len(near_exact) == 1 and scores[0] >= _NEAR_EXACT_SIMILARITY


def _scores_including_alternate_names(city: str, matches: list[PlaceMatch]) -> list[float]:
    """Each match scored against the closest of its own names, official or
    alternate. Only the spellings already close to the query are considered,
    so this stays a handful of comparisons rather than a second full scan."""
    close_names = _close_spellings(city)
    names_by_place: dict[str, set[str]] = {}
    for alternate in close_names:
        for record in _ALTERNATE_NAME_INDEX.get(alternate, []):
            names_by_place.setdefault(str(record["name"]).lower(), set()).add(alternate)

    return [
        max(
            [_similarity(city, match.name)]
            + [
                _similarity(city, alternate)
                for alternate in names_by_place.get(match.name.lower(), ())
            ]
        )
        for match in matches
    ]


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
