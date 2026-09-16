# vedic-astro

A local, fully offline Vedic astrology chart engine. Enter a birth date, time,
and location on a single web page and get a South Indian-style kundali:
planets, houses, nakshatras, Navamsa (D9), Panchanga, and Vimshottari Dasha.

No network calls are made at any point — planetary positions are computed
locally via [Swiss Ephemeris](https://www.astro.com/swisseph/) (`pyswisseph`)
in its built-in analytical mode, which needs no external data files.

## Setup

```bash
pip install -e ".[dev]"
```

## Run the web UI

```bash
uvicorn vedic_astro.web.app:app --reload
```

Then open http://127.0.0.1:8000 in a browser.

## Run tests

```bash
pytest
```

## Defaults

- Ayanamsha: Lahiri (Chitrapaksha)
- House system: Whole sign
- Rahu/Ketu: Mean node
- Chart style: South Indian
