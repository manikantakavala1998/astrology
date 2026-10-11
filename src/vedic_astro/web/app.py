"""Single-screen local web UI: birth chart, plus an optional second person for
marriage-compatibility (Ashtakoot) matching.

Runs entirely on localhost via uvicorn - the browser only ever talks to this
process on your own machine, never the internet. Place-of-birth lookup and
timezone resolution are both offline (see geocode.py) - only exact
coordinates under "Advanced" bypass them entirely.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from math import ceil
from functools import lru_cache
import re

from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, ValidationError
from typing import Any

from vedic_astro.ashtakavarga import (
    ASHTAKAVARGA_PLANETS, LAGNA, LAGNA_BAV_CONTRIBUTION_TABLE,
    lagna_ashtakavarga_contributions,
)
from vedic_astro.aspects import sign_aspects
from vedic_astro.aspect_tables import build_aspect_tables
from vedic_astro.bala_report import build_bala_report
from vedic_astro.laghu_parashari import build_laghu_report
from vedic_astro.bhrigu_report import build_bhrigu_report
from vedic_astro.chart import build_kundali_chart
from vedic_astro.jaimini_report import build_jaimini_report
from vedic_astro.jaimini2 import build_jaimini2_report
from vedic_astro.jaimini2_dasha import subdivide_book_period
from vedic_astro.jaimini_dasha import subdivide_period
from vedic_astro.brihat_jataka import book_source, build_brihat_report, DashaOptions, dasha_timeline
from vedic_astro.ephemeris import ascendant_longitude, planet_positions
from vedic_astro.nakshatra import nakshatra_for_longitude
from vedic_astro.chart_render import (
    ChartCell,
    ashtakavarga_mini_grid,
    bhava_chalit_layout,
    navamsa_layout,
    south_indian_layout,
    varga_layout,
)
from vedic_astro.dasha import DAYS_PER_YEAR, compute_deeper_sub_periods
from vedic_astro.divisional_charts import VARGA_REGISTRY
from vedic_astro.amsa_rulers import chart_amsa_rulers
from vedic_astro.geocode import (
    PlaceMatch,
    pick_confident_match,
    resolve_utc_offset,
    search_places,
)
from vedic_astro.matching import compute_match_report
from vedic_astro.models import (
    SIGNS_IN_ORDER, BirthData, DashaPeriod, DashaSubPeriod, HouseSystem,
    KundaliChart, NodeType, Planet, PlanetPosition, Sign,
)
from vedic_astro.rashi_bhava import RASHI_LORD, sign_for_longitude, whole_sign_house
from vedic_astro.vimshopaka_bala import SHADVARGA_WEIGHTS, SAPTAVARGA_WEIGHTS, DASHAVARGA_WEIGHTS, SHODASHAVARGA_WEIGHTS
from vedic_astro.web.birth_place import INDIA_STATE_CHOICES, prepare_birth_place

_BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="vedic-astro")
app.mount("/static", StaticFiles(directory=_BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=_BASE_DIR / "templates")

_AYANAMSHA_CHOICES = ["lahiri", "raman", "krishnamurti"]
_HOUSE_SYSTEM_CHOICES = [hs.value for hs in HouseSystem]


class BrihatDashaRequest(BaseModel):
    birth_data: BirthData
    options: DashaOptions


class VimshottariBranchRequest(BaseModel):
    planet: Planet
    start: datetime
    end: datetime


class JaiminiBranchRequest(BaseModel):
    birth_data: BirthData
    system: str = Field(min_length=1, max_length=24)
    path: list[int] = Field(min_length=1, max_length=4)


class Jaimini2BranchRequest(BaseModel):
    birth_data: BirthData
    system: str = Field(min_length=1, max_length=24)
    path: list[int] = Field(min_length=1, max_length=2)


@lru_cache(maxsize=16)
def _jaimini2_for_birth(birth_json: str) -> dict[str, Any]:
    return build_jaimini2_report(build_kundali_chart(BirthData.model_validate_json(birth_json)))


@app.post("/api/jaimini2/subperiods")
def jaimini2_subperiods(payload: Jaimini2BranchRequest) -> dict[str, Any]:
    report = _jaimini2_for_birth(payload.birth_data.model_dump_json())
    system = next((s for s in report["dasha_systems"] if s["code"] == payload.system), None)
    if system is None:
        raise HTTPException(400, "Unknown Jaimini 2 dasha method.")
    if not system["periods"] or len(payload.path) >= system["max_levels"]:
        raise HTTPException(400, system.get("unavailable") or system.get("subdivision_status") or "Subdivision is not defined.")
    periods = system["periods"]
    for index in payload.path:
        if not 0 <= index < len(periods):
            raise HTTPException(400, "Period index is outside the Jaimini 2 sequence.")
        periods = subdivide_book_period(system, periods[index])
    return {"periods": periods, "convention": system["subdivision_status"]}


@lru_cache(maxsize=16)
def _jaimini_for_birth(birth_json: str) -> dict[str, Any]:
    return build_jaimini_report(build_kundali_chart(BirthData.model_validate_json(birth_json)))


@app.post("/api/jaimini/subperiods")
def jaimini_subperiods(payload: JaiminiBranchRequest) -> dict[str, Any]:
    """Resolve a validated index path from calculated roots, never client dates."""
    report = _jaimini_for_birth(payload.birth_data.model_dump_json())
    system = next((s for s in report["dasha_systems"] if s["code"] == payload.system), None)
    if system is None:
        raise HTTPException(400, "Unknown Jaimini dasha system.")
    if len(payload.path) >= system["max_levels"]:
        raise HTTPException(400, "This method does not define that subdivision level.")
    periods = system["periods"]
    for index in payload.path:
        if not 0 <= index < len(periods):
            raise HTTPException(400, "Period index is outside the calculated sequence.")
        parent = periods[index]
        periods = subdivide_period(system, Sign(parent["sign"]), datetime.fromisoformat(parent["start"]), datetime.fromisoformat(parent["end"]))
    return {"periods": periods}


@app.post("/api/vimshottari/subperiods")
def vimshottari_subperiods(payload: VimshottariBranchRequest) -> dict[str, Any]:
    """Return one subdivision only; the UI opens the five levels on demand."""
    if payload.start.tzinfo is not None or payload.end.tzinfo is not None:
        raise HTTPException(400, "Use the chart's local civil times without a timezone suffix.")
    seconds = (payload.end - payload.start).total_seconds()
    if not 0 < seconds <= 120 * DAYS_PER_YEAR * 86400:
        raise HTTPException(400, "The parent period must have a positive duration of at most 120 years.")
    periods = compute_deeper_sub_periods(
        payload.planet, payload.start, seconds / (DAYS_PER_YEAR * 86400), levels=1,
    )
    # Preserve the parent's exact endpoint after microsecond rounding in the
    # existing proportional calculation. Adjacent periods remain contiguous.
    periods[-1].end = payload.end
    return {"periods": [period.model_dump(mode="json") for period in periods]}


@app.get("/api/brihat-jataka/book")
def brihat_book() -> dict[str, Any]:
    return book_source()


@app.get("/brihat-jataka/source.txt", response_class=PlainTextResponse)
def brihat_source_download() -> PlainTextResponse:
    source = book_source()
    raw = source["front_matter"] + "".join(c["text"] for c in source["chapters"]) + source["appendix"]
    return PlainTextResponse(raw, headers={"Content-Disposition": 'attachment; filename="brihat-jataka-1905.txt"'})


@app.get("/brihat-jataka/book/{chapter}", response_class=HTMLResponse)
def brihat_chapter(request: Request, chapter: int) -> HTMLResponse:
    if not 1 <= chapter <= 28:
        raise HTTPException(404, "Chapter must be between 1 and 28.")
    return templates.TemplateResponse(request, "brihat_chapter.html", {
        "book": book_source(), "chapter": book_source()["chapters"][chapter-1],
    })


@app.post("/api/brihat-jataka/dasha")
def brihat_dasha(payload: BrihatDashaRequest) -> dict[str, Any]:
    # Only the natal ephemeris is needed here. Avoid recalculating the app's
    # unrelated transit timelines every time a worksheet option changes.
    b = payload.birth_data
    try:
        asc = ascendant_longitude(b.utc_datetime, b.latitude, b.longitude, b.ayanamsha)
        raw = planet_positions(b.utc_datetime, b.ayanamsha, b.node_type)
        planets = [PlanetPosition(
            planet=p, longitude=r.longitude, sign=sign_for_longitude(r.longitude),
            degree_in_sign=r.longitude % 30, house=whole_sign_house(sign_for_longitude(r.longitude), sign_for_longitude(asc)),
            nakshatra=nakshatra_for_longitude(r.longitude), retrograde=r.retrograde,
            ecliptic_latitude=r.latitude, speed_longitude=r.speed_longitude,
        ) for p, r in raw.items()]
        return dasha_timeline(planets, asc, b.local_datetime, payload.options)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

def _current_local_datetime(utc_offset_hours: float) -> datetime:
    """'Now', expressed as a naive datetime in the birth place's local time -
    consistent with the naive local datetimes used throughout the dasha math."""
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    return now_utc + timedelta(hours=utc_offset_hours)


def _to_24_hour_time(hour_12: int, minute: int, meridiem: str) -> time:
    if not (1 <= hour_12 <= 12):
        raise ValueError("Hour must be between 1 and 12.")
    if not (0 <= minute <= 59):
        raise ValueError("Minute must be between 0 and 59.")
    meridiem = meridiem.upper()
    if meridiem not in ("AM", "PM"):
        raise ValueError("Choose AM or PM.")
    hour_24 = (hour_12 % 12) + (12 if meridiem == "PM" else 0)
    return time(hour_24, minute)


def _parse_birth_date(value: str) -> date:
    value = value.strip()
    try:
        if re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", value):
            day, month, year = map(int, value.split("/"))
            return date(year, month, day)
        # Existing hidden forms and programmatic callers may still use ISO.
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            return date.fromisoformat(value)
    except ValueError:
        pass
    raise ValueError("Enter a valid date as DD/MM/YYYY, for example 04/09/1998.")


def _birth_date_input(value: str) -> str:
    try:
        parsed = _parse_birth_date(value)
        return f"{parsed.day:02d}/{parsed.month:02d}/{parsed.year:04d}"
    except ValueError:
        return value


templates.env.filters["birth_date_input"] = _birth_date_input


def _parse_birth_datetime(date_str: str, hour_str: str, minute_str: str, meridiem: str) -> tuple[date, time]:
    parsed_date = _parse_birth_date(date_str)
    parsed_time = _to_24_hour_time(int(hour_str), int(minute_str), meridiem)
    return parsed_date, parsed_time


@dataclass(frozen=True)
class ResolvedLocation:
    latitude: float
    longitude: float
    utc_offset: float
    label: str | None


class PlaceNeedsDisambiguation(Exception):
    def __init__(self, candidates: list[PlaceMatch]) -> None:
        self.candidates = candidates


def _resolve_location(
    parsed_date: date,
    parsed_time: time,
    place_name: str,
    manual_latitude: str,
    manual_longitude: str,
    manual_utc_offset_hours: str,
    selected_latitude: str,
    selected_longitude: str,
    selected_timezone: str,
    selected_label: str,
    birth_state: str = "",
) -> ResolvedLocation:
    """Raises ValueError on a hard input error, or PlaceNeedsDisambiguation
    when the place name matches more than one candidate."""
    resolved_timezone: str | None = None
    label: str | None = None

    if selected_latitude and selected_longitude:
        # A candidate from a previous disambiguation list was clicked.
        latitude = float(selected_latitude)
        longitude = float(selected_longitude)
        resolved_timezone = selected_timezone or None
        label = selected_label or None
    elif manual_latitude.strip() and manual_longitude.strip():
        try:
            latitude = float(manual_latitude)
            longitude = float(manual_longitude)
        except ValueError as exc:
            raise ValueError("Latitude/longitude must be numbers.") from exc
    elif place_name.strip():
        matches = search_places(place_name)
        if birth_state and birth_state != "other":
            matches = [match for match in matches if match.country == "India"]
        if not matches:
            raise ValueError(
                f'No place found matching "{place_name}". Try a nearby larger city, '
                "or enter exact coordinates under Advanced below."
            )
        # A typo with one sensible reading is corrected and used; a name that
        # genuinely matches several places still asks, because guessing a
        # birthplace produces a wrong chart that looks perfectly normal.
        chosen = pick_confident_match(place_name, matches)
        if chosen is None:
            raise PlaceNeedsDisambiguation(matches)
        latitude, longitude, resolved_timezone = chosen.latitude, chosen.longitude, chosen.timezone
        label = f"{chosen.name}, {chosen.state}, {chosen.country}"
    else:
        raise ValueError("Enter a place of birth, or exact coordinates under Advanced.")

    if manual_utc_offset_hours.strip():
        utc_offset = float(manual_utc_offset_hours)
    else:
        utc_offset = resolve_utc_offset(latitude, longitude, parsed_date, parsed_time, resolved_timezone)

    return ResolvedLocation(latitude=latitude, longitude=longitude, utc_offset=utc_offset, label=label)


def _build_chart(
    parsed_date: date,
    parsed_time: time,
    location: ResolvedLocation,
    ayanamsha: str,
    node_type: str,
    house_system: str = "whole_sign",
    name: str = "",
) -> KundaliChart:
    birth_data = BirthData(
        name=name,
        birth_date=parsed_date,
        birth_time=parsed_time,
        latitude=location.latitude,
        longitude=location.longitude,
        utc_offset_hours=location.utc_offset,
        ayanamsha=ayanamsha,
        node_type=NodeType(node_type),
        house_system=HouseSystem(house_system),
    )
    return build_kundali_chart(birth_data)


def _rashi_drishti_rows(chart: KundaliChart) -> list[dict[str, object]]:
    """Rashi Drishti (sign-to-sign aspect) for the Aspects tab: only signs
    actually occupied in this chart, and which of their aspected signs are
    also occupied - independent of graha_drishti, a separate classical
    system (see aspects.sign_aspects)."""
    planets_by_sign: dict[Sign, list[str]] = {}
    for p in chart.planets:
        planets_by_sign.setdefault(p.sign, []).append(p.planet.value)

    rows: list[dict[str, object]] = []
    for sign, planet_names in planets_by_sign.items():
        aspected = [
            {"sign": s, "planets": planets_by_sign[s]}
            for s in sign_aspects(sign)
            if s in planets_by_sign
        ]
        rows.append({"sign": sign, "planets": planet_names, "aspects": aspected})
    return rows


def _sade_sati_status(cycle_start: date, cycle_end: date, today: date) -> str:
    if today < cycle_start:
        return "Upcoming"
    if today >= cycle_end:
        return "Past"
    return "Current"


def _sade_sati_rows(chart: KundaliChart) -> list[dict[str, object]]:
    assert chart.saturn_transit is not None
    today = date.today()
    return [
        {
            "cycle": cycle,
            "status": _sade_sati_status(cycle.start.date(), cycle.end.date(), today),
        }
        for cycle in chart.saturn_transit.sade_sati_cycles
    ]


def _sign_lords_for_houses(chart: KundaliChart, houses: list[int]) -> list[dict[str, object]]:
    """For each house number (whole-sign, counted from the Ascendant), the
    sign occupying it and that sign's classical lord."""
    asc_index = SIGNS_IN_ORDER.index(chart.ascendant.sign)
    rows: list[dict[str, object]] = []
    for house in houses:
        sign = SIGNS_IN_ORDER[(asc_index + house - 1) % 12]
        rows.append({"house": house, "sign": sign.value, "lord": RASHI_LORD[sign].value})
    return rows


def _ashtakavarga_tiles(chart: KundaliChart) -> list[dict[str, object]]:
    """Computed SAV, seven planetary BAVs, and Lagna's own BAV."""
    assert chart.ashtakavarga is not None
    natal_signs = {p.sign for p in chart.planets}
    tiles: list[dict[str, object]] = [
        {
            "label": "SAV (Samudaya Ashtakavarga)",
            "key": "SAV",
            "grid": ashtakavarga_mini_grid(
                chart.ashtakavarga.sav, natal_signs, _sav_band, ascendant_sign=chart.ascendant.sign
            ),
        }
    ]
    for planet in ASHTAKAVARGA_PLANETS:
        tiles.append(
            {
                "label": planet.value,
                "key": planet.value,
                "grid": ashtakavarga_mini_grid(
                    chart.ashtakavarga.bav_by_planet[planet], natal_signs, _bav_band,
                    ascendant_sign=chart.ascendant.sign,
                ),
            }
        )
    tiles.append(
        {
            "label": "Ascendant (Lagna)",
            "key": LAGNA,
            "grid": ashtakavarga_mini_grid(
                chart.ashtakavarga.lagna_bav, natal_signs, _bav_band,
                ascendant_sign=chart.ascendant.sign,
            ),
            "caption": (
                f"Natal {chart.ascendant.sign.value}: "
                f"{chart.ashtakavarga.lagna_bav[chart.ascendant.sign]} bindus "
                f"· Total {sum(chart.ashtakavarga.lagna_bav.values())}"
            ),
        }
    )
    return tiles


def _lagna_ashtakavarga_calculation(chart: KundaliChart) -> dict[str, object]:
    assert chart.ashtakavarga is not None
    natal_signs: dict[Planet | str, Sign] = {p.planet: p.sign for p in chart.planets}
    natal_signs[LAGNA] = chart.ascendant.sign
    contributions = lagna_ashtakavarga_contributions(chart.planets, chart.ascendant.sign)
    rules = [{
        "contributor": contributor.value if isinstance(contributor, Planet) else contributor,
        "sign": natal_signs[contributor].value,
        "houses": ", ".join(str(house) for house in sorted(houses)),
        "points": len(houses),
    } for contributor, houses in LAGNA_BAV_CONTRIBUTION_TABLE.items()]
    scores = [{
        "sign": sign.value,
        "house": (SIGNS_IN_ORDER.index(sign) - SIGNS_IN_ORDER.index(chart.ascendant.sign)) % 12 + 1,
        "contributors": ", ".join(
            contributor.value if isinstance(contributor, Planet) else contributor
            for contributor, row in contributions.items() if row[sign]
        ) or "None",
        "score": chart.ashtakavarga.lagna_bav[sign],
    } for sign in SIGNS_IN_ORDER]
    return {"rules": rules, "scores": scores, "total": sum(chart.ashtakavarga.lagna_bav.values())}


_SAV_SCORE_BANDS: list[tuple[int, str, str]] = [
    (20, "critically-weak", "Critically Weak"),
    (25, "below-average", "Below Average"),
    (28, "average", "Average / Neutral"),
    (32, "strong", "Strong"),
]


def _sav_band(score: int) -> tuple[str, str]:
    """(css_class, label) for a SAV/Bhava Ashtakavarga house total, per the
    classical reading bands (Below 20 = Critically Weak, ... Above 32 =
    Exceptionally Powerful)."""
    for threshold, css_class, label in _SAV_SCORE_BANDS:
        if score < threshold:
            return css_class, label
    return "exceptional", "Exceptionally Powerful"


def _bav_band(bindus: int) -> tuple[str, str]:
    """(css_class, label) for a single planet's per-sign BAV bindu count
    (0-8 scale, not the 0-56 SAV scale above) - a simpler 3-tier reading
    (0-3 weak, 4 average, 5-8 strong), reusing the SAV bands' red/yellow/
    green classes since the color meaning (weak -> strong) is the same,
    just a coarser split appropriate to the smaller range."""
    if bindus <= 3:
        return "critically-weak", "Weak"
    if bindus == 4:
        return "average", "Average"
    return "strong", "Strong"


def _divisional_chart_entries(
    chart: KundaliChart,
    grid: list[list[ChartCell | None]],
    navamsa_grid: list[list[ChartCell | None]],
) -> list[dict[str, object]]:
    """Bhava Chalit and all 23 divisional charts, with their chosen methods."""
    entries: list[dict[str, object]] = [
        {"code": "bhava_chalit", "name": "Bhava Chalit", "grid": bhava_chalit_layout(chart),
         "held_reason": None, "method": "Placidus house cusps"}
    ]
    for spec in VARGA_REGISTRY:
        if spec.code == "D1":
            chart_grid: list[list[ChartCell | None]] | None = grid
        elif spec.code == "D9":
            chart_grid = navamsa_grid
        elif spec.sign_fn is not None:
            chart_grid = varga_layout(chart, spec.code)
        else:
            chart_grid = None
        entries.append(
            {
                "code": spec.code,
                "name": f"{spec.code} {spec.name}",
                "grid": chart_grid,
                "held_reason": spec.held_reason,
                "method": spec.method,
                "amsa_rulers": chart_amsa_rulers(chart, spec.code),
            }
        )
    return entries


def _bhava_ashtakavarga_rows(chart: KundaliChart) -> list[dict[str, object]]:
    assert chart.ashtakavarga is not None
    rows: list[dict[str, object]] = []
    for house in range(1, 13):
        score = chart.ashtakavarga.bhava_ashtakavarga[house]
        css_class, label = _sav_band(score)
        rows.append({"house": house, "score": score, "band_class": css_class, "band_label": label})
    return rows


def _shadbala_rows(chart: KundaliChart) -> list[dict[str, object]]:
    assert chart.shadbala is not None
    rows: list[dict[str, object]] = []
    for planet in ASHTAKAVARGA_PLANETS:
        r = chart.shadbala[planet]
        rows.append(
            {
                "planet": planet.value,
                "sthana": round(r.sthana_bala.total, 1),
                "dig": round(r.dig_bala, 1),
                "kala": round(r.kala_bala.total, 1),
                "chesta": round(r.chesta_bala, 1),
                "naisargika": round(r.naisargika_bala, 1),
                "drik": round(r.drik_bala, 1),
                "total_rupas": round(r.total_rupas, 2),
                "required_rupas": r.required_rupas,
                "meets": r.meets_required_strength,
                "ishta_phala": round(r.ishta_phala, 2),
                "kashta_phala": round(r.kashta_phala, 2),
            }
        )
    return rows


def _vimshopaka_rows(chart: KundaliChart) -> list[dict[str, object]]:
    assert chart.vimshopaka_bala is not None
    rows: list[dict[str, object]] = []
    for planet in ASHTAKAVARGA_PLANETS:
        r = chart.vimshopaka_bala[planet]
        rows.append(
            {
                "planet": planet.value,
                "shadvarga_score": round(r.shadvarga_score, 2),
                "shadvarga_band": r.shadvarga_band,
                "saptavarga_score": round(r.saptavarga_score, 2),
                "saptavarga_band": r.saptavarga_band,
                "dashavarga_score": round(r.dashavarga_score, 2),
                "dashavarga_band": r.dashavarga_band,
                "shodashavarga_score": round(r.shodashavarga_score, 2),
                "shodashavarga_band": r.shodashavarga_band,
            }
        )
    return rows


def _bhava_bala_rows(chart: KundaliChart) -> list[dict[str, object]]:
    assert chart.bhava_bala is not None
    max_total = max(r.total_rupas for r in chart.bhava_bala.values())
    rows: list[dict[str, object]] = []
    for house in range(1, 13):
        r = chart.bhava_bala[house]
        lord = RASHI_LORD[sign_for_longitude(chart.bhava_chalit_cusps[house - 1])]
        width_pct = (r.total_rupas / max_total * 100) if max_total > 0 else 0.0
        rows.append(
            {
                "house": house,
                "lord": lord.value,
                "bhavadhipati": round(r.bhavadhipati_bala, 2),
                "dig": round(r.bhava_dig_bala, 2),
                "drishti": round(r.bhava_drishti_bala, 2),
                "occupancy": round(r.occupancy_adjustment, 2),
                "total_rupas": round(r.total_rupas, 2),
                "width_pct": round(width_pct, 1),
            }
        )
    return rows


def _empty_form_context() -> dict[str, object]:
    person_defaults = {
        "name": "",
        "birth_date": "",
        "birth_hour": "",
        "birth_minute": "",
        "birth_meridiem": "AM",
        "place_name": "",
        "birth_state": "",
        "manual_latitude": "",
        "manual_longitude": "",
        "manual_utc_offset_hours": "",
        "selected_latitude": "",
        "selected_longitude": "",
        "selected_timezone": "",
        "selected_label": "",
    }
    b_defaults = {f"b_{key}": value for key, value in person_defaults.items()}
    return {
        "ayanamsha_choices": _AYANAMSHA_CHOICES,
        "house_system_choices": _HOUSE_SYSTEM_CHOICES,
        "birth_state_choices": INDIA_STATE_CHOICES,
        "form_values": {
            **person_defaults,
            **b_defaults,
            "ayanamsha": "lahiri",
            "node_type": "mean",
            "house_system": "whole_sign",
            "include_match": "",
        },
        "chart": None,
        "brihat_report": None,
        "jaimini_report": None,
        "jaimini2_report": None,
        "chart_b": None,
        "grid": None,
        "navamsa_grid": None,
        "rashi_drishti": None,
        "aspect_tables": None,
        "sade_sati_rows": None,
        "ashtakavarga_tiles": None,
        "bhava_ashtakavarga_rows": None,
        "divisional_chart_entries": None,
        "current_mahadasha": None,
        "current_antardasha": None,
        "kendra_lords": None,
        "trikona_lords": None,
        "shadbala_rows": None,
        "bala_report": None,
        "laghu_report": None,
        "vimshopaka_rows": None,
        "bhava_bala_rows": None,
        "resolved_place": None,
        "resolved_place_b": None,
        "candidates": None,
        "candidates_b": None,
        "match_report": None,
        "error": None,
    }


def _frontend_grid(grid: list[list[ChartCell | None]]) -> list[list[dict[str, object] | None]]:
    """Expose the existing rendered cells; React does not recalculate placements."""
    return [
        [
            {
                "sign": cell.sign.value,
                "house": cell.house,
                "is_ascendant": cell.is_ascendant,
                "direction": cell.direction,
                "element_symbol": cell.element_symbol,
                "planets": [
                    {
                        "code": label.code,
                        "retrograde": label.retrograde,
                        "dignity_suffix": label.dignity_suffix,
                        "color_class": label.color_class,
                        "natal_degree": label.natal_degree,
                    }
                    for label in cell.planet_labels
                ],
            } if cell is not None else None
            for cell in row
        ]
        for row in grid
    ]


def _frontend_state(context: dict[str, object]) -> dict[str, object]:
    """Bootstrap the React shell while retaining every server-rendered report.

    Analysis templates remain the source of truth, including held-chart notices
    and reference notes. All placements and scores come from the Python engine.
    """
    chart = context.get("chart")
    state: dict[str, object] = {
        "page": "workspace",
        "form_values": context["form_values"],
        "error": context.get("error"),
        "has_chart": isinstance(chart, KundaliChart),
        "has_match": context.get("match_report") is not None,
        "resolved_place": context.get("resolved_place"),
    }
    if not isinstance(chart, KundaliChart):
        return state

    grids = {code: _frontend_grid(varga_layout(chart, code)) for code in ("D1", "D3", "D9", "D10")}
    major = context.get("current_mahadasha")
    minor = context.get("current_antardasha")
    current_dasha = None
    if isinstance(major, DashaPeriod):
        period = minor if isinstance(minor, DashaSubPeriod) else major
        current_dasha = {
            "major": major.planet.value,
            "minor": minor.planet.value if isinstance(minor, DashaSubPeriod) else None,
            "start": period.start.isoformat(),
            "end": period.end.isoformat(),
            "as_of": _current_local_datetime(chart.birth_data.utc_offset_hours).isoformat(),
        }

    state.update({
        "birth_data": chart.birth_data.model_dump(mode="json"),
        "ascendant": chart.ascendant.model_dump(mode="json"),
        "planets": [planet.model_dump(mode="json") for planet in chart.planets],
        "panchanga": chart.panchanga.model_dump(mode="json"),
        "grids": grids,
        "current_dasha": current_dasha,
        "kendra_lords": context["kendra_lords"],
        "trikona_lords": context["trikona_lords"],
        "brihat_jataka": context.get("brihat_report"),
        "jaimini": context.get("jaimini_report"),
        "jaimini2": context.get("jaimini2_report"),
        "balas": context.get("bala_report"),
        "laghu_parashari": context.get("laghu_report"),
        "bhrigu": build_bhrigu_report(chart),
        "vimshottari": chart.dasha.model_dump(mode="json"),
        "aspect_tables": context.get("aspect_tables"),
    })
    return state


def _render(request: Request, context: dict[str, object], status_code: int = 200) -> HTMLResponse:
    context["frontend_state"] = _frontend_state(context)
    return templates.TemplateResponse(request, "index.html", context, status_code=status_code)


@app.get("/", response_class=HTMLResponse)
def show_form(request: Request) -> HTMLResponse:
    return _render(request, _empty_form_context())


@app.post("/", response_class=HTMLResponse)
def compute_chart(
    request: Request,
    # Same "everything defaults to empty string, never Form(...)" reasoning as
    # before: Starlette's form parser drops empty-valued fields, making a
    # required Form(...) field indistinguishable from an absent one and
    # surfacing as a raw, unstyled 422. All requiredness is enforced below.
    name: str = Form(""),
    birth_date: str = Form(""),
    birth_hour: str = Form(""),
    birth_minute: str = Form(""),
    birth_meridiem: str = Form("AM"),
    place_name: str = Form(""),
    birth_state: str = Form(""),
    manual_latitude: str = Form(""),
    manual_longitude: str = Form(""),
    manual_utc_offset_hours: str = Form(""),
    selected_latitude: str = Form(""),
    selected_longitude: str = Form(""),
    selected_timezone: str = Form(""),
    selected_label: str = Form(""),
    include_match: str = Form(""),
    b_name: str = Form(""),
    b_birth_date: str = Form(""),
    b_birth_hour: str = Form(""),
    b_birth_minute: str = Form(""),
    b_birth_meridiem: str = Form("AM"),
    b_place_name: str = Form(""),
    b_birth_state: str = Form(""),
    b_manual_latitude: str = Form(""),
    b_manual_longitude: str = Form(""),
    b_manual_utc_offset_hours: str = Form(""),
    b_selected_latitude: str = Form(""),
    b_selected_longitude: str = Form(""),
    b_selected_timezone: str = Form(""),
    b_selected_label: str = Form(""),
    ayanamsha: str = Form("lahiri"),
    node_type: str = Form("mean"),
    house_system: str = Form("whole_sign"),
) -> HTMLResponse:
    context = _empty_form_context()
    context["form_values"] = {
        "name": name,
        "birth_date": birth_date,
        "birth_hour": birth_hour,
        "birth_minute": birth_minute,
        "birth_meridiem": birth_meridiem,
        "place_name": place_name,
        "birth_state": birth_state,
        "manual_latitude": manual_latitude,
        "manual_longitude": manual_longitude,
        "manual_utc_offset_hours": manual_utc_offset_hours,
        "selected_latitude": selected_latitude,
        "selected_longitude": selected_longitude,
        "selected_timezone": selected_timezone,
        "selected_label": selected_label,
        "include_match": include_match,
        "b_name": b_name,
        "b_birth_date": b_birth_date,
        "b_birth_hour": b_birth_hour,
        "b_birth_minute": b_birth_minute,
        "b_birth_meridiem": b_birth_meridiem,
        "b_place_name": b_place_name,
        "b_birth_state": b_birth_state,
        "b_manual_latitude": b_manual_latitude,
        "b_manual_longitude": b_manual_longitude,
        "b_manual_utc_offset_hours": b_manual_utc_offset_hours,
        "b_selected_latitude": b_selected_latitude,
        "b_selected_longitude": b_selected_longitude,
        "b_selected_timezone": b_selected_timezone,
        "b_selected_label": b_selected_label,
        "house_system": house_system,
        "ayanamsha": ayanamsha,
        "node_type": node_type,
    }
    want_match = include_match == "on"

    try:
        city, state, place_query = prepare_birth_place(place_name, birth_state)
        context["form_values"].update(place_name=city, birth_state=state)
        b_place_query = b_place_name
        if want_match:
            b_city, b_state, b_place_query = prepare_birth_place(b_place_name, b_birth_state)
            context["form_values"].update(b_place_name=b_city, b_birth_state=b_state)
    except ValueError as exc:
        context["error"] = str(exc)
        return _render(request, context, status_code=400)

    try:
        a_date, a_time = _parse_birth_datetime(birth_date, birth_hour, birth_minute, birth_meridiem)
    except ValueError as exc:
        context["error"] = f"Invalid date or time: {exc}"
        return _render(request, context, status_code=400)

    b_date: date | None = None
    b_time: time | None = None
    if want_match:
        try:
            b_date, b_time = _parse_birth_datetime(b_birth_date, b_birth_hour, b_birth_minute, b_birth_meridiem)
        except ValueError as exc:
            context["error"] = f"Invalid date or time for the second person: {exc}"
            return _render(request, context, status_code=400)

    a_location: ResolvedLocation | None = None
    try:
        a_location = _resolve_location(
            a_date, a_time, place_query, manual_latitude, manual_longitude, manual_utc_offset_hours,
            selected_latitude, selected_longitude, selected_timezone, selected_label,
            birth_state=state,
        )
    except PlaceNeedsDisambiguation as exc:
        context["candidates"] = exc.candidates
    except ValueError as exc:
        context["error"] = str(exc)
        return _render(request, context, status_code=400)

    b_location: ResolvedLocation | None = None
    if want_match:
        assert b_date is not None and b_time is not None
        try:
            b_location = _resolve_location(
                b_date, b_time, b_place_query, b_manual_latitude, b_manual_longitude, b_manual_utc_offset_hours,
                b_selected_latitude, b_selected_longitude, b_selected_timezone, b_selected_label,
                birth_state=b_state,
            )
        except PlaceNeedsDisambiguation as exc:
            context["candidates_b"] = exc.candidates
        except ValueError as exc:
            context["error"] = f"Second person: {exc}"
            return _render(request, context, status_code=400)

    if context["candidates"] or context["candidates_b"]:
        return _render(request, context)

    assert a_location is not None
    try:
        chart_a = _build_chart(a_date, a_time, a_location, ayanamsha, node_type, house_system, name)
    except (ValueError, ValidationError) as exc:
        context["error"] = str(exc)
        return _render(request, context, status_code=400)

    now_local = _current_local_datetime(a_location.utc_offset)
    grid = south_indian_layout(chart_a)
    navamsa_grid = navamsa_layout(chart_a)
    context["chart"] = chart_a
    context["brihat_report"] = build_brihat_report(chart_a)
    context["jaimini_report"] = build_jaimini_report(chart_a)
    context["jaimini2_report"] = build_jaimini2_report(chart_a)
    context["grid"] = grid
    context["navamsa_grid"] = navamsa_grid
    context["rashi_drishti"] = _rashi_drishti_rows(chart_a)
    context["aspect_tables"] = build_aspect_tables(chart_a.planets)
    context["sade_sati_rows"] = _sade_sati_rows(chart_a)
    context["ashtakavarga_tiles"] = _ashtakavarga_tiles(chart_a)
    context["lagna_ashtakavarga_calculation"] = _lagna_ashtakavarga_calculation(chart_a)
    context["bhava_ashtakavarga_rows"] = _bhava_ashtakavarga_rows(chart_a)
    context["divisional_chart_entries"] = _divisional_chart_entries(chart_a, grid, navamsa_grid)
    context["current_mahadasha"] = chart_a.dasha.current_mahadasha(now_local)
    context["current_antardasha"] = chart_a.dasha.current_antardasha(now_local)
    context["resolved_place"] = a_location.label
    context["kendra_lords"] = _sign_lords_for_houses(chart_a, [1, 4, 7])
    context["trikona_lords"] = _sign_lords_for_houses(chart_a, [1, 5, 9])
    context["shadbala_rows"] = _shadbala_rows(chart_a)
    context["bala_report"] = build_bala_report(chart_a)
    context["laghu_report"] = build_laghu_report(chart_a)
    context["vimshopaka_rows"] = _vimshopaka_rows(chart_a)
    context["vimshopaka_weights"] = [
        {"code": code, "shadvarga": SHADVARGA_WEIGHTS.get(code, 0), "saptavarga": SAPTAVARGA_WEIGHTS.get(code, 0),
         "dashavarga": DASHAVARGA_WEIGHTS.get(code, 0), "shodashavarga": SHODASHAVARGA_WEIGHTS[code]}
        for code in SHODASHAVARGA_WEIGHTS
    ]
    context["bhava_bala_rows"] = _bhava_bala_rows(chart_a)
    assert chart_a.shadbala is not None and chart_a.bhava_bala is not None
    context["shadbala_graph_max"] = max(2, ceil(max(
        max(r.total_rupas, r.required_rupas) for r in chart_a.shadbala.values()
    ) / 2) * 2)
    context["bhava_bala_graph_max"] = max(2, ceil(max(
        r.total_rupas for r in chart_a.bhava_bala.values()
    ) / 2) * 2)

    if want_match and b_location is not None:
        assert b_date is not None and b_time is not None
        try:
            chart_b = _build_chart(b_date, b_time, b_location, ayanamsha, node_type, house_system, b_name)
        except (ValueError, ValidationError) as exc:
            context["error"] = f"Second person: {exc}"
            return _render(request, context, status_code=400)
        context["chart_b"] = chart_b
        context["resolved_place_b"] = b_location.label
        context["match_report"] = compute_match_report(chart_a, chart_b)

    return _render(request, context)


@app.post("/dasha-detail", response_class=HTMLResponse)
def dasha_detail(
    request: Request,
    lord: str = Form(""),
    start: str = Form(""),
    years: str = Form(""),
) -> HTMLResponse:
    """Computes Antardasha -> Pratyantardasha -> Sookshma -> Prana for one
    specific Mahadasha branch, on demand - see dasha.py's module docstring
    for why this isn't computed eagerly for the whole chart."""
    try:
        lord_planet = Planet(lord)
        start_dt = datetime.fromisoformat(start)
        years_float = float(years)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "dasha_detail.html",
            {"error": f"Could not compute sub-periods: {exc}", "antardasha": None},
            status_code=400,
        )

    antardasha = compute_deeper_sub_periods(lord_planet, start_dt, years_float, levels=4)
    return templates.TemplateResponse(
        request,
        "dasha_detail.html",
        {
            "error": None,
            "mahadasha_lord": lord_planet,
            "mahadasha_start": start_dt,
            "antardasha": antardasha,
        },
    )
