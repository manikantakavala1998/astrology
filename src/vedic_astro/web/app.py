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

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from vedic_astro.ashtakavarga import ASHTAKAVARGA_PLANETS
from vedic_astro.aspects import sign_aspects
from vedic_astro.chart import build_kundali_chart
from vedic_astro.chart_render import (
    ChartCell,
    ashtakavarga_mini_grid,
    bhava_chalit_layout,
    navamsa_layout,
    south_indian_layout,
    varga_layout,
)
from vedic_astro.dasha import compute_deeper_sub_periods
from vedic_astro.divisional_charts import VARGA_REGISTRY
from vedic_astro.geocode import PlaceMatch, resolve_utc_offset, search_places
from vedic_astro.matching import compute_match_report
from vedic_astro.models import SIGNS_IN_ORDER, BirthData, HouseSystem, KundaliChart, NodeType, Planet, Sign
from vedic_astro.rashi_bhava import RASHI_LORD
from vedic_astro.sign_attributes import SIGN_DIRECTION, SIGN_ELEMENT_NAME, SIGN_ELEMENT_SYMBOL

_BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="vedic-astro")
app.mount("/static", StaticFiles(directory=_BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=_BASE_DIR / "templates")

_AYANAMSHA_CHOICES = ["lahiri", "raman", "krishnamurti"]
_HOUSE_SYSTEM_CHOICES = [hs.value for hs in HouseSystem]

templates.env.globals["sign_attribute_reference"] = [
    {
        "sign": sign.value,
        "direction": SIGN_DIRECTION[sign],
        "element_symbol": SIGN_ELEMENT_SYMBOL[sign],
        "element_name": SIGN_ELEMENT_NAME[sign],
    }
    for sign in SIGNS_IN_ORDER
]


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


def _parse_birth_datetime(date_str: str, hour_str: str, minute_str: str, meridiem: str) -> tuple[date, time]:
    parsed_date = date.fromisoformat(date_str)
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
        if not matches:
            raise ValueError(
                f'No place found matching "{place_name}". Try a nearby larger city, '
                "or enter exact coordinates under Advanced below."
            )
        if len(matches) > 1:
            raise PlaceNeedsDisambiguation(matches)
        latitude, longitude, resolved_timezone = matches[0].latitude, matches[0].longitude, matches[0].timezone
        label = f"{matches[0].name}, {matches[0].state}, {matches[0].country}"
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
    """The 3x3 screenshot-style tile list for the Ashtakavarga tab: SAV +
    the 7 planets' BAV (all computed), plus a Lagna/Ascendant tile shown as
    a pending placeholder - see ashtakavarga.py's module docstring for why."""
    assert chart.ashtakavarga is not None
    natal_signs = {p.sign for p in chart.planets}
    tiles: list[dict[str, object]] = [
        {
            "label": "SAV (Samudaya Ashtakavarga)",
            "grid": ashtakavarga_mini_grid(chart.ashtakavarga.sav, natal_signs, _sav_band),
            "pending": False,
        }
    ]
    for planet in ASHTAKAVARGA_PLANETS:
        tiles.append(
            {
                "label": planet.value,
                "grid": ashtakavarga_mini_grid(
                    chart.ashtakavarga.bav_by_planet[planet], natal_signs, _bav_band
                ),
                "pending": False,
            }
        )
    tiles.append(
        {
            "label": "Ascendant (Lagna)",
            "grid": None,
            "pending": True,
        }
    )
    return tiles


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
    """Bhava Chalit + all 23 registry entries, in order, for the Divisional
    Charts tab's sub-tab list - held (unbuilt) charts get a None grid and
    their held_reason, so the tab shows the full intended list."""
    entries: list[dict[str, object]] = [
        {"code": "bhava_chalit", "name": "Bhava Chalit", "grid": bhava_chalit_layout(chart), "held_reason": None}
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
            }
        )
    return rows


def _bhava_bala_rows(chart: KundaliChart) -> list[dict[str, object]]:
    assert chart.bhava_bala is not None
    max_total = max(r.total_rupas for r in chart.bhava_bala.values())
    rows: list[dict[str, object]] = []
    for house in range(1, 13):
        r = chart.bhava_bala[house]
        width_pct = (r.total_rupas / max_total * 100) if max_total > 0 else 0.0
        rows.append(
            {
                "house": house,
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
        "form_values": {
            **person_defaults,
            **b_defaults,
            "ayanamsha": "lahiri",
            "node_type": "mean",
            "house_system": "whole_sign",
            "include_match": "",
        },
        "chart": None,
        "chart_b": None,
        "grid": None,
        "navamsa_grid": None,
        "rashi_drishti": None,
        "sade_sati_rows": None,
        "ashtakavarga_tiles": None,
        "bhava_ashtakavarga_rows": None,
        "divisional_chart_entries": None,
        "current_mahadasha": None,
        "current_antardasha": None,
        "kendra_lords": None,
        "trikona_lords": None,
        "shadbala_rows": None,
        "vimshopaka_rows": None,
        "bhava_bala_rows": None,
        "resolved_place": None,
        "resolved_place_b": None,
        "candidates": None,
        "candidates_b": None,
        "match_report": None,
        "error": None,
    }


def _render(request: Request, context: dict[str, object], status_code: int = 200) -> HTMLResponse:
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
            a_date, a_time, place_name, manual_latitude, manual_longitude, manual_utc_offset_hours,
            selected_latitude, selected_longitude, selected_timezone, selected_label,
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
                b_date, b_time, b_place_name, b_manual_latitude, b_manual_longitude, b_manual_utc_offset_hours,
                b_selected_latitude, b_selected_longitude, b_selected_timezone, b_selected_label,
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
    context["grid"] = grid
    context["navamsa_grid"] = navamsa_grid
    context["rashi_drishti"] = _rashi_drishti_rows(chart_a)
    context["sade_sati_rows"] = _sade_sati_rows(chart_a)
    context["ashtakavarga_tiles"] = _ashtakavarga_tiles(chart_a)
    context["bhava_ashtakavarga_rows"] = _bhava_ashtakavarga_rows(chart_a)
    context["divisional_chart_entries"] = _divisional_chart_entries(chart_a, grid, navamsa_grid)
    context["current_mahadasha"] = chart_a.dasha.current_mahadasha(now_local)
    context["current_antardasha"] = chart_a.dasha.current_antardasha(now_local)
    context["resolved_place"] = a_location.label
    context["kendra_lords"] = _sign_lords_for_houses(chart_a, [1, 4, 7])
    context["trikona_lords"] = _sign_lords_for_houses(chart_a, [1, 5, 9])
    context["shadbala_rows"] = _shadbala_rows(chart_a)
    context["vimshopaka_rows"] = _vimshopaka_rows(chart_a)
    context["bhava_bala_rows"] = _bhava_bala_rows(chart_a)

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
