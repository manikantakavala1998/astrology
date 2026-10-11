# vedic-astro

A local, fully offline Vedic astrology chart engine. Enter a birth date in
**DD/MM/YYYY** format (for example, **04/09/1998**), time and location in a React
and Tailwind celestial workspace to get a South Indian-style kundali:
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

The production React/Tailwind bundle is included in the Python package. Normal
use does not need Node.js, an internet connection, external fonts, or a second
server. All astrology calculations, place lookup, historical timezone handling,
and compatibility matching still run in the existing Python engine.

## Develop the UI

```bash
cd frontend
npm ci
npm run build
```

Reload the browser after building. Vite writes the self-contained UI to
`src/vedic_astro/web/static/ui/`, which FastAPI serves on the same origin.
TypeScript is checked as part of every build. Keep the generated bundle in the
repository so Python-only installs continue to work offline.

`npm run dev` rebuilds the bundle when UI source files change. Keep FastAPI
running in another terminal and reload its page to see the updated UI.

Browser regression checks (with FastAPI running on port 8765):

```bash
cd frontend
npx playwright install chromium
npm run test:ui
```

Set `ASTRO_TEST_URL` to use a different local server. These checks exercise all
report navigation, D1/D9/D10, all eight planet-table columns, divisional and Bala
controls, BCP/Padma year 120, the four dasha levels, compatibility, and mobile
layouts. They also block external requests to verify offline operation.

The Aspects section has Vedic and Western tabs with full planet names, planetary
colors, aspect numbers and aspected zodiac signs (including empty signs for
Vedic drishti). Western major aspects have an adjustable 0–10° orb, defaulting
to 6°. All connections are calculated from the birth chart. See
[calculation rules](docs/planetary-aspects.md).

Jaimini calculations are available in a separate dashboard tab after Brihat Jataka:
seven/eight karakas, four compact chart views, sign aspects, all twelve Arudha
padas, Upapada, Argala, eleven named dasha worksheets, yoga conditions, chart
indications and special lagnas. Chara subdivisions open through Prana. Calculation
methods and supported depths are documented in [Jaimini conventions](docs/jaimini.md).
Run `node tests/ui-jaimini.cjs` from `frontend` for its browser checks.

Balas sits directly below Aspects. Fourteen separate views show each strength’s
full name, a compact vertical graph, actual calculation steps and birth-chart
inputs. All four Vimshopaka schemes have individual division worksheets; Bhava
bars follow their house lord’s planetary color. See [Bala calculation views](docs/balas-ui.md).
Run `node tests/ui-balas.cjs` from `frontend` for the focused browser checks.

The React overview uses server-calculated grid cells and full planet data. All
birth-chart views place Current Dasha below the chart, with the complete
Planetary Positions table on the right. Separate Kendra Lords and Trikona Lords
cards sit below the table, aligned with Current Dasha. These cards stack on
smaller screens. Panchanga, including birth hora, remains in its separate
navigation tab. All other analysis sections retain their complete Jinja reports inside the new React
layout: every table, source note, year selector, pending chart, nested dasha
breakdown, and both place-disambiguation flows remain available. Native forms
also remain usable if JavaScript cannot start. Birth details are not stored in
browser storage.

South Indian charts and all report tables share the original dark celestial
palette, with colored planet labels, uniform cell borders, and central birth details.
Degrees inside the charts always show existing natal D1 positions, including
when a divisional chart is selected; the legend states this explicitly.

Divisional Charts offers Bhava Chalit and all 23 listed divisions, with compact
D1–D144 selectors and full names inside the chart. The sixteen Parashari charts,
supplementary divisions, and composite methods are documented in
[Divisional chart conventions](docs/divisional-charts.md).

The **Brihat Jataka** tab provides plain chart-based predictions, separate
vertical strength graphs, Ayurdaya dashas (Pinda/Amsa), Naisargika age periods,
antardashas, yogas and South Indian Ashtakavarga charts. It shows the rules and
actual calculation steps from your birth inputs. The complete 1905 edition
remains available offline through source endpoints; visible book references
were removed at the user's request. See [Brihat Jataka conventions](docs/brihat-jataka.md)
for source attribution, variants and calculation scope. The Bhrigu Nandi Nadi
interface has been removed. Bhrigu Chakra Paddhati, Bhrigu Sarala Paddhati and
Padma Chakra Paddhati each have a separate item in the left Analysis menu.
Balas includes vertical graphs in the existing planet colors for Shadbala,
all four Vimshopaka schemes (6, 7, 10 and 16 charts), and Bhava Bala (colored by house lord).
Vimshottari dashas use a compact five-column explorer in the app's existing
colors, with exact start/end times through Prana and on-demand subdivisions.
The Brihat Jataka strengths view includes separate support-condition graphs
in planetary colors, visible zero markers, a comparison table and expandable
rules and calculations, without a combined strength score.
Panchanga includes the planetary hora active at birth, its local start/end
times and sunrise-based calculation. See [birth hora](docs/panchanga.md).

The locally bundled [celestial header](src/vedic_astro/web/static/celestial-header.png)
was generated with the built-in image generation tool. Prompt: a midnight-navy
starry lake and mountain banner with a warm crescent moon on the right, a dark
empty left half for heading text, and no interface elements or lettering.

## Run tests

```bash
pytest
```

## Defaults

- Ayanamsha: Lahiri (Chitrapaksha)
- House system: Whole sign
- Rahu/Ketu: Mean node
- Chart style: South Indian
