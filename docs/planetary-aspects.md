# Planetary aspect tables

The Aspects view has separate Vedic and Western tabs, full planet names and
planetary text colors. Both tables show Planet, Sign occupied, Aspected planets
and Aspected signs. Each aspected planet also shows its own natal sign. The four
columns scroll inside their panel on small screens. Rows remain uniform,
including special Vedic aspects; there are no highlighted cells or pills.

Vedic connections count **zodiac signs**, independently of the selected house
system. Count the source sign as 1. Sun, Moon, Mercury and Venus reach 7; Mars
reaches 4/7/8, Jupiter 5/7/9, Saturn 3/7/10. The shared ASPECT_OFFSETS constant
supplies these rules. Rahu/Ketu remain targets, with no outgoing Vedic rule.
Aspected signs includes all reached signs, including empty ones. This view
does not use Jaimini rashi drishti or change existing house-based callers.

Western connections use five major angles: conjunction 0°, sextile 60°,
square 90°, trine 120° and opposition 180°. The calculation takes the smaller
longitude separation (0–180°), then its absolute difference from an exact
aspect. The UI defaults to a **6° orb** for all five types, adjustable from 0
to 10°. That is an explicit app setting, not a claim to reproduce another
software's orb defaults. Calculation data includes candidates within 10°;
changing the tolerance filters those results locally without network calls.
Each pair appears in both planets' rows. Western Aspected signs identifies
the target planets' signs, rather than attributing an angular aspect to a
whole sign. Minor aspects, applying/separating classification and cusp
aspects are outside this view.

The native HTML fallback includes both views at the default 6° Western orb.
React adds the adjustable tolerance and keyboard-accessible tabs.

Angle definitions: [Astrodienst's aspect guide](https://www.astro.com/astrology/in_aspect_e.htm).

Validation: `pytest tests/test_aspect_tables.py tests/test_frontend.py`,
`npm run build`, and `node tests/ui-aspects.cjs` from frontend with the local
server running on port 8765.
