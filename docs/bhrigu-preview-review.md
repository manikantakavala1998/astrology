# Bhrigu methods: calculation review and preview brief

Reviewed and implemented 11 October 2026 following approval of the preview.

The three separate pages now use `bhrigu_report.py` and `BhriguExplorer.tsx`. They open at current birth-place civil time, resolve their own annual intervals, show signs/occupants/lords/aspects, and highlight the independently calculated five-level Vimshottari path. Selection of another year opens its exact start; selection of the current year returns to Now. Date edits remain inside the selected year, and Today resets both controls. The cycle-ruler extension ends at year 108 while Lagna progression and timing cover all 120 years.

Implemented corrections: aspects to an empty Lagna qualify in the optional BSP research variant; original BSP age rules are the application default; Jupiter's additional targets retain separate roles; Padma Badhaka signs are mapped into D1 by sign; Badhakesh placements are separate connections. All method houses use D1 whole-sign geometry. The dasha tree is loaded only along the active branch, with retry and stale-request cancellation.

Padma retains the declared approximate calendar convention and its documented one-day difference from the published worked date. Missing BSP articles/refinements have not been fabricated. Review source URLs and numerical examples below document the available rule set.

The final layout includes every functional element from the approved reference: name/birth ribbon, separate year/date/time controls, Today/current-time state, full-name South Indian chart, three activation cards, Lagna/cycle comparison, full-width aspects, connected five-level dasha cards, highlighted timing rows, arithmetic disclosure, and a full-explorer link carrying the selected time. DD/MM/YYYY and 24-hour inputs are independent of the browser locale. Chart cells remain unhighlighted.

`BhriguPredictions.tsx` adds plain-language selected-year readings to all three pages. BCP reads the annual house, natal year-lord placement and separate cycle-ruler target. BSP retains primary, occupied, occasional and controlling roles, with permanent themes separate from fixed age triggers. A year without a qualifying age rule says so; missing rules are not filled with BCP progression. Padma reads the annual house, year-lord D12 mapping, direct Badhaka and Badhakesh connections. It does not rate its results from exaltation/debilitation or Vimshottari. Occupants and incoming aspects carry their calculated reasons. Expandable timing readings show all five Vimshottari lords, natal house, classical lordships and occupation/lordship/aspect connections to the displayed method targets. These are qualitative themes, not event guarantees or an invented combined score. Changing the selected year, BSP interpretation or exact time updates the readings.

Final validation: production TypeScript/Vite build passed; all three browser suites (`ui-bhrigu.cjs`, `ui-vimshottari.cjs`, `ui-smoke.cjs`) passed. The Bhrigu suite verifies year 1/29/40 readings, BSP conditional roles, separate Padma connection checks, all five timing readings, a Prana boundary change, recovery from a branch failure, year 120 coverage, selected-date handoff, and collapsed/expanded mobile views at 390/320px. No browser runtime errors or external browser requests were observed. The earlier affected Python calculation/bootstrap suite passed 114 tests; the final prediction addition changes only the frontend interpretation and presentation. Actual desktop/mobile screenshots and the prediction-panel preview are saved under `frontend/test-results`.

## Requested behavior

Keep Bhrigu Chakra Paddhati, Bhrigu Sarala Paddhati and Padma Chakra Paddhati as separate sidebar pages. Use the existing navy, gold, lavender and planetary colors. Open each page at the present birth-place local date/time. Show its active year, natal houses, signs, occupants, lords, aspects and a separate five-level Vimshottari context.

An annual interval contains several short dashas. A year selector sets the interval; an explicit date/time within it selects the current Mahadasha, Antardasha, Pratyantardasha, Sookshma and Prana. Returning to the current year uses the current time. Selecting another year initially uses its exact start, and the chosen instant must stay inside that method's year interval. A Today button resets both. Highlight the five active dasha rows and show full planet names, natal house/sign and exact start/end. Do not highlight chart cells.

## Review findings to address during implementation

1. **BCP:** the one-house-per-running-year arithmetic, 12-year repetition and M. Imran's nine cycle-ruler order match the published source. Keep classical Lagna progression separate from the cycle-ruler extension. Compute actual birthday intervals, including leap-day handling. The cycle extension stops at year 108; classical progression continues. Distinguish the house relative to the cycle ruler from that sign's house in D1.
2. **BSP aspects:** `_shared_special_status` currently searches `PlanetAspect` records for house 1. `compute_aspects` only returns planet-to-planet links, so an aspect to an unoccupied Lagna cannot appear there. Compute house reach using `aspected_houses` for this check and for display; use planet links only for the occupants actually reached.
3. **BSP rule scope:** compare each original article with the separate special-status research interpretation. The original age rules state the activation, whereas the current module applies a shared gate to every one. Do not silently treat the extra gate as a universal original rule. In particular, mean nodes are always retrograde, so the current retrograde precondition cannot independently distinguish node eligibility.
4. **BSP coverage:** BSP-10 includes Jupiter's occupied house as well as the ninth from it; BSP-11 includes fifth-house activation, an occasional occupied-house result, and seventh-house control/influence. The current single-target record omits these distinctions. Preserve primary, conditional and influencing targets as separate reasons. BSP-1/2/14 and qualitative BSP-15 are permanent notes, not annual activations. A year with no age-timed rule must say so, instead of borrowing BCP's active house. The app currently lacks BSP-3/4, BSP-7/12 and the later series; verify primary source availability before adding them.
5. **Padma Badhaka mapping:** current `is_badhaka` compares a D1 superimposed house to the numeric Badhaka house offsets for both D1 and D12. These are different bases. The source's example explicitly maps the D12 Badhaka sign back into D1. For Taurus D1 and Pisces D12, D12 H7 is Virgo, which maps to D1 H5, not D1 H7. Compare signs or explicitly mapped D1 houses. Show direct Badhaka signs separately from the Badhakesh's natal and D12 placements.
6. **Padma year dates:** keep the documented author-style calendar drift convention distinct from a literal 360-day timedelta and from BCP/BSP birthday intervals. The source's worked hand calculation differs from the current reproduction by one day. Disclose the selected convention in the calculation details and test it, including rounding and leap/calendar boundaries. Default Padma year must be selected from its actual computed start/end interval, rather than ordinary completed age.
7. **Vimshottari:** the engine uses Moon nakshatra balance, the standard nine-lord order and recursive parent-duration × lord-years/120 at all five levels, with a declared 365.2425-day year. Existing tests cover proportionality, contiguity, lord order and branch nesting. Select periods with start <= instant < end, in the birth-place offset; show exact times for Sookshma/Prana. Padma's year convention must not change this dasha convention. If year navigation reaches outside the currently computed nine major periods, explicitly extend the repeating sequence or explain the unavailable interval.

42 existing tests passed: `test_bcp.py`, `test_bsp.py`, `test_padma_chakra.py`, `test_dasha.py`, `test_vimshottari_api.py`. These tests do not establish that the missing source conditions above have been implemented correctly.

## Numerically calculated preview sample

Birth: 04/09/1998, 00:03, 17.00517 N, 81.77784 E, UTC +05:30. Preview instant: 11/10/2026 13:30 at birth-place time. Taurus ascendant.

- BCP running year 29, 04/09/2026 00:03 to 04/09/2027 00:03: D1 H5 Virgo, lord Mercury, no occupants. Cycle 3 Venus: fifth from natal Venus in Leo is Sagittarius, D1 H8, no occupants. Jupiter in Pisces D1 H11 aspects Virgo H5 by its seventh aspect.
- BSP: no implemented age-timed activation for running year 29. Permanent targets remain: Saturn's fourth = Cancer H3; Jupiter's tenth = Sagittarius H8; Jupiter's sixth = Leo H4; Taurus natural-number Bhava = Gemini H2.
- Padma current computed year 29: 08/04/2026 00:03 to 03/04/2027 00:03 under the current author-style approximation. H5 Virgo; year lord Mercury; Mercury D12 Gemini maps to D1 H2. D1 Badhaka Capricorn H9; D12 Badhaka Virgo maps to D1 H5. Show the activated sign's connection and the year-lord's superimposed placement as separate checks.

| Level | Lord | Natal sign / house | Start (birth-place local) | End (birth-place local) |
| --- | --- | --- | --- | --- |
| Mahadasha | Rahu | Leo / H4 | 18/08/2014 03:12:11 | 17/08/2032 11:57:47 |
| Antardasha | Venus | Leo / H4 | 06/03/2026 16:25:27 | 06/03/2029 09:53:03 |
| Pratyantardasha | Sun | Leo / H4 | 05/09/2026 07:20:03 | 30/10/2026 02:12:25 |
| Sookshma | Mercury | Cancer / H3 | 10/10/2026 00:05:13 | 17/10/2026 18:21:38 |
| Prana | Venus | Leo / H4 | 11/10/2026 13:20:30 | 12/10/2026 20:23:14 |

## Primary sources checked

- https://saptarishisastrology.com/bhrigu-chakra-with-cycle-rulers-by-m-imran/
- https://saptarishisastrology.com/bhrighu-chakra-paddathi-2-by-saptarishis-astrology/
- https://saptarishisastrology.com/bhrighu-saral-paddathi-6-by-venkat-ramana/
- https://saptarishisastrology.com/wp-content/uploads/2023/01/Bhrighu-Saral-Paddathi-8-by-Venkat-Ramana-Saptarishis-Astrology-Research-Team.pdf
- https://saptarishisastrology.com/wp-content/uploads/2023/01/Bhrighu-Saral-Paddathi-9-by-Venkat-Ramana-Saptarishis-Astrology-Research-Team.pdf
- https://saptarishisastrology.com/wp-content/uploads/2023/01/Bhrighu-Saral-Paddathi-10-by-Venkat-Ramana-Saptarishis-Astrology-Research-Team.pdf
- https://saptarishisastrology.com/wp-content/uploads/2023/01/Bhrighu-Saral-Paddathi-11-by-Venkat-Ramana-Saptarishis-Astrology-Research-Team.pdf
- https://saptarishisastrology.com/wp-content/uploads/2023/01/Bhrighu-Saral-Paddathi-13-by-Venkat-Ramana-Saptarishis-Astrology-Research-Team.pdf
- https://saptarishisastrology.com/wp-content/uploads/2023/02/padma-chakra-paddhati-method-explained-part-1-by-gautam-dave.pdf
- https://saptarishisastrology.com/use-of-dwadasamsa-chart-in-prediction-by-pramod-bhavasar/
