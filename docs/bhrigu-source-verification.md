# Padma Chakra and BCP cycle-lord verification

Checked on 11 October 2026 against the publicly readable slide text supplied by the user:

- [PadmaChakra-calculation-and-result](https://www.scribd.com/document/549426388/PadmaChakra-calculation-and-result), 31 slides.
- [BCP-CycleLords](https://www.scribd.com/document/549460315/BCP-CycleLords), 17 slides.

## Padma calculations

The implemented progression agrees with the slides: running year `y` activates house `((y - 1) % 12) + 1` from natal Lagna. Take that sign's lord, find its D12 sign, and locate that **sign** in D1. A D12 house number is not copied into D1.

All 16 declared year-lord/D12-sign/overlay combinations across the six worked examples are covered by parameterized regressions in `tests/test_padma_chakra.py`. The fixtures supply the slides' declared D12 signs using synthetic natal degrees. They check the mapping arithmetic, rather than reconstructing unpublished birth details or testing the events described in the slides.

The existing ephemeris-based Bhavasar example and the separate D1/D12 Badhaka sign checks remain covered.

## BCP calculations and prediction correction

The nine consecutive 12-year rulers agree: Moon, Mercury, Venus, Sun, Mars, Jupiter, Saturn, Rahu, Ketu. Use the ruler's occupied natal sign as a second Lagna. The cycle-relative house and its natal D1 mapping are different reference frames.

The engine already counts correctly. The prediction card previously interpreted the mapped D1 house as the cycle's primary theme. It now reads the **relative cycle house**, displays both labels, and calculates the target lord's placement/lordships and incoming aspects from the cycle Lagna. Natal connections and Vimshottari timing retain their explicit D1 frame.

Seven sign/count cases from examples 3 and 6 supplement the existing cycle-boundary tests. Some starting signs are inferred from the examples' listed placements and lordships. The source ends at year 108; the app continues natal progression for years 109–120 without inventing further cycle rulers.

## Birth sample

04/09/1998, 00:03, Rajahmundry coordinates 17.00517 N, 81.77784 E, UTC +05:30, Lahiri. At 11/10/2026:

| Calculation | Result |
| --- | --- |
| Running year | 29 |
| Natal annual target | Virgo, H5, Mercury |
| Cycle | Venus, years 25–36; natal Venus in Leo |
| Cycle target | Sagittarius, H5 from Venus, D1 H8 |
| Cycle target lord | Jupiter in Pisces, H8 from Venus, D1 H11 |
| Padma overlay | Mercury D12 Gemini maps to D1 H2 |

## Scope and remaining conventions

The supplied slides do not define an exact year-boundary formula. BCP uses birthday intervals. Padma retains the previously documented Bhavasar calendar-drift approximation; it is neither an exact 360-day timedelta nor a birthday year. Its older published hand-worked example differs from the app by one day. The calculation panel states this convention, and these new slides do not resolve that difference.

Some slide interpretations use nodal aspects/co-lordships and Arudha relationships. They do not provide a complete consistent algorithm for these additions. The app's current aspect panel explicitly uses the seven classical planets' aspect rules; this review does not silently add a global Rahu/Ketu convention. Consequently, the slide interpretations are not reproduced in full.

The automated checks establish arithmetic and displayed reference frames, not the accuracy of predicted life events.

## Validation

- 75 Python checks passed for BCP, Padma, Bhrigu reports, chart rendering and the frontend template.
- TypeScript and the production UI build passed.
- Browser checks passed for all three Bhrigu pages, year selection, five dasha levels, prediction calculations, error recovery and mobile layouts.
- Whole-app chart checks passed at 1366, 390 and 320 pixels: 2,016 sign/house labels and 1,332 direction/element labels, with no overlaps. Element symbols now share the top row with sign, direction and house.
