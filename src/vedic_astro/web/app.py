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

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from vedic_astro.aspects import sign_aspects
from vedic_astro.chart import build_kundali_chart
from vedic_astro.chart_render import navamsa_layout, south_indian_layout
from vedic_astro.dasha import compute_deeper_sub_periods
from vedic_astro.geocode import PlaceMatch, resolve_utc_offset, search_places
from vedic_astro.matching import compute_match_report
from vedic_astro.models import BirthData, HouseSystem, KundaliChart, NavataraEntry, NodeType, Planet, Sign
from vedic_astro.nakshatra import compute_navatara_chakra
from vedic_astro.rag.qa import answer_question

_BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="vedic-astro")
app.mount("/static", StaticFiles(directory=_BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=_BASE_DIR / "templates")

_AYANAMSHA_CHOICES = ["lahiri", "raman", "krishnamurti"]
_HOUSE_SYSTEM_CHOICES = [hs.value for hs in HouseSystem]


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


def _navatara_chakra_for_chart(chart: KundaliChart) -> list[NavataraEntry]:
    """Navatara Chakra (Tools tab): all 27 nakshatras classified by their Tara
    relationship to this chart's own Moon (Chandra) nakshatra."""
    moon = next(p for p in chart.planets if p.planet == Planet.MOON)
    return compute_navatara_chakra(moon.nakshatra.index)


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
        "navatara_chakra": None,
        "current_mahadasha": None,
        "current_antardasha": None,
        "resolved_place": None,
        "resolved_place_b": None,
        "candidates": None,
        "candidates_b": None,
        "match_report": None,
        "question": None,
        "answer": None,
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
    context["chart"] = chart_a
    context["grid"] = south_indian_layout(chart_a)
    context["navamsa_grid"] = navamsa_layout(chart_a)
    context["rashi_drishti"] = _rashi_drishti_rows(chart_a)
    context["navatara_chakra"] = _navatara_chakra_for_chart(chart_a)
    context["current_mahadasha"] = chart_a.dasha.current_mahadasha(now_local)
    context["current_antardasha"] = chart_a.dasha.current_antardasha(now_local)
    context["resolved_place"] = a_location.label

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


@app.post("/ask", response_class=HTMLResponse)
def ask_question(
    request: Request,
    question: str = Form(""),
    name: str = Form(""),
    a_date: str = Form(""),
    a_time: str = Form(""),
    a_lat: str = Form(""),
    a_lon: str = Form(""),
    a_utc_offset: str = Form(""),
    ayanamsha: str = Form("lahiri"),
    node_type: str = Form("mean"),
    house_system: str = Form("whole_sign"),
    b_name: str = Form(""),
    b_date: str = Form(""),
    b_time: str = Form(""),
    b_lat: str = Form(""),
    b_lon: str = Form(""),
    b_utc_offset: str = Form(""),
) -> HTMLResponse:
    """Rebuilds the already-resolved chart(s) directly from exact coordinates
    carried as hidden fields on the chart page - no place search needed here,
    since the user already resolved their place(s) to get to this point."""
    context = _empty_form_context()

    try:
        birth_data_a = BirthData(
            name=name,
            birth_date=date.fromisoformat(a_date),
            birth_time=time.fromisoformat(a_time),
            latitude=float(a_lat),
            longitude=float(a_lon),
            utc_offset_hours=float(a_utc_offset),
            ayanamsha=ayanamsha,
            node_type=NodeType(node_type),
            house_system=HouseSystem(house_system),
        )
        chart_a = build_kundali_chart(birth_data_a)
    except (ValueError, ValidationError) as exc:
        context["error"] = f"Could not rebuild the chart: {exc}"
        return _render(request, context, status_code=400)

    match_report = None
    if b_date and b_time and b_lat and b_lon:
        try:
            birth_data_b = BirthData(
                name=b_name,
                birth_date=date.fromisoformat(b_date),
                birth_time=time.fromisoformat(b_time),
                latitude=float(b_lat),
                longitude=float(b_lon),
                utc_offset_hours=float(b_utc_offset),
                ayanamsha=ayanamsha,
                node_type=NodeType(node_type),
                house_system=HouseSystem(house_system),
            )
            chart_b = build_kundali_chart(birth_data_b)
        except (ValueError, ValidationError) as exc:
            context["error"] = f"Could not rebuild the second person's chart: {exc}"
            return _render(request, context, status_code=400)
        context["chart_b"] = chart_b
        match_report = compute_match_report(chart_a, chart_b)

    now_local = _current_local_datetime(birth_data_a.utc_offset_hours)
    context["chart"] = chart_a
    context["grid"] = south_indian_layout(chart_a)
    context["navamsa_grid"] = navamsa_layout(chart_a)
    context["rashi_drishti"] = _rashi_drishti_rows(chart_a)
    context["navatara_chakra"] = _navatara_chakra_for_chart(chart_a)
    context["current_mahadasha"] = chart_a.dasha.current_mahadasha(now_local)
    context["current_antardasha"] = chart_a.dasha.current_antardasha(now_local)
    context["match_report"] = match_report
    context["question"] = question

    if not question.strip():
        context["error"] = "Enter a question to ask."
        return _render(request, context, status_code=400)

    try:
        context["answer"] = answer_question(
            question, chart_a, match_report=match_report, reference_datetime=now_local
        )
    except (httpx.HTTPError, RuntimeError) as exc:
        context["error"] = (
            f"Could not get an answer from the local AI model (is Ollama running?): {exc}"
        )
        return _render(request, context, status_code=502)

    return _render(request, context)


@app.post("/dasha-detail", response_class=HTMLResponse)
def dasha_detail(
    request: Request,
    lord: str = Form(""),
    start: str = Form(""),
    years: str = Form(""),
) -> HTMLResponse:
    """Computes Pratyantardasha -> Sookshma -> Prana for one specific
    Antardasha branch, on demand - see dasha.py's module docstring for why
    this isn't computed eagerly for the whole chart."""
    try:
        lord_planet = Planet(lord)
        start_dt = datetime.fromisoformat(start)
        years_float = float(years)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "dasha_detail.html",
            {"error": f"Could not compute sub-periods: {exc}", "pratyantardasha": None},
            status_code=400,
        )

    pratyantardasha = compute_deeper_sub_periods(lord_planet, start_dt, years_float, levels=3)
    return templates.TemplateResponse(
        request,
        "dasha_detail.html",
        {
            "error": None,
            "antardasha_lord": lord_planet,
            "antardasha_start": start_dt,
            "pratyantardasha": pratyantardasha,
        },
    )
