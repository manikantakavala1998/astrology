# Separate Bala views

Balas follows Aspects in the main sidebar. Its local menu has fourteen views:
Shadbala total; Sthana, Dig, Kala, Cheshta, Naisargika and Drik Bala; the
Shadvarga, Saptavarga, Dashavarga and Shodashavarga Vimshopaka schemes; Bhava
Bala; and Ishta and Kashta Phala. A grouped select replaces the menu on mobile.

Each view presents one compact vertical graph, a planet or house selector,
full component names, numeric arithmetic, units and input values. All-result
tables and detailed contribution worksheets open in disclosures. Planet colors
follow the existing palette; the twelve Bhava bars use their cusp lord’s color.
Negative Drik values start at zero and extend downwards. Only Shadbala total
displays required-strength markers.

`bala_report.py` reads existing scores without changing engine calculations.
Sthana and Kala components come from their stored breakdowns. Saptavargaja
contributions reuse the engine’s degree ranges and relationship tiers;
Vimshopaka worksheets reuse all four weight schemes and D1 relationships.
Bhava lord, direction, aspects and occupancy follow the existing Placidus
Bhava Chalit conventions, independent of the main chart’s house selection.
Arithmetic retains full precision, while the default display rounds to two
decimals. Expanded result tables show six decimals.

Current engine limits remain explicit: Kala excludes Masa, Varsha and Yuddha
Bala; Cheshta uses simplified motion states; Drik uses discrete Graha Drishti;
Bhava’s diurnal bonus is unavailable and no fixed house threshold is applied.
Ishta and Kashta retain the engine’s normalized 0–1 scale.

The native HTML fallback retains the existing aggregate Bala views and includes
all fourteen detailed calculation reports without requiring JavaScript.

Validation: `pytest tests/test_bala_report.py tests/test_frontend.py
tests/test_shadbala.py tests/test_bhava_bala.py tests/test_vimshopaka_bala.py
tests/test_web_app.py`; `npm run build`; `node tests/ui-balas.cjs` and
`node tests/ui-smoke.cjs` with the local server running on port 8765.
