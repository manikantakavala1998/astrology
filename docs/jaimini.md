# Jaimini dashboard calculation conventions

The Jaimini tab uses the existing sidereal ephemeris, selected ayanamsha and
mean/true-node setting. All combinatorial rules use whole signs, including when
the main chart uses a different house system. No personal information or
illustrative preview values are substituted into calculations.

The implementation is in `jaimini.py`, `jaimini_report.py` and
`jaimini_dasha.py`; React renders the same report returned in the page bootstrap.
The native HTML report retains the calculation tables without JavaScript.

## Declared conventions

Different Jaimini commentators use different starts, counting directions,
co-lords and subdivisions. The app names its chosen convention for each dasha.
It does not claim that every school or every named Jaimini dasha is identical.

| Method | Displayed depth |
| --- | --- |
| Chara, K. N. Rao convention | Major, antar, pratyantar, sookshma, prana |
| Narayana, PVR convention | Major and antar; two complementary cycles |
| Lagna Kendradi Rasi | Major and antar; Narayana subdivision convention |
| Shoola | Major and antar |
| Niryana Shoola | Major and antar; PVR's suggested Narayana subdivision |
| Sudasha | Major worksheet, first-period remainder |
| Drig | Major worksheet |
| Navamsa | Classical Abhimukha major worksheet |
| Sthira | Classical Brahma-seeded major worksheet |
| Brahma | Classical sixth-lord major worksheet |
| Mandooka | K. N. Rao quadrant major worksheet |

One dasha year is **365.2425 days**. All dates are civil times at the birth input's
UTC offset, with start-inclusive/end-exclusive boundaries. A method exposing
major periods only does not receive invented subdivisions. Zero-year transitions
are retained in the duration worksheet and skipped in the chronological timeline.

Chara starts at Lagna, takes direction from the ninth sign's odd/even-footed
group, and uses seven classical lords. Duration is directed inclusive count
minus one; own sign receives twelve years. No dignity-year adjustment is applied.
Every subdivision covers all twelve signs in equal parts, with the parent's sign
last. Its direction follows the same ninth-sign grouping.

The odd-footed signs are Aries, Taurus, Gemini, Libra, Scorpio and Sagittarius.
This classification is distinct from zodiacal odd/even parity. Narayana counts
duration using footed groups, but its antar sequence uses ordinary sign parity.
For Narayana-derived durations, an own-sign lord receives exactly twelve years;
otherwise exaltation adds one and debilitation subtracts one. Nodes retain the
existing neutral dignity convention. The own-sign exception takes precedence
over Mercury's simultaneous Virgo exaltation to keep complementary cycles
nonnegative. The worksheet prints every adjustment.

Narayana sequence exceptions prefer Saturn over Ketu when both occupy the seed.
Co-lord selection for Aquarius/Scorpio compares companions, Jupiter/Mercury/
dispositor connections, exaltation, occupied-sign modality, then either duration
or unrounded advancement. Equal comparisons retain the classical lord.
Sign comparisons use the separate, ordered criteria printed under Yogas;
they are comparisons, not an invented summed strength score.

## Report rules and limits

Karakas rank full unrounded advancement, not displayed minutes. Seven excludes
the nodes; eight includes Rahu with `30 - degree` and adds Pitrikaraka.
Ketu is excluded. Exact degree ties share a role and leave the next role vacant.
The report shows every tied assignment; derived worksheets use the first tied
Atmakaraka deterministically. Normal ephemeris charts almost never have exact
ties, but a tied assignment is not silently converted to unique karakas.

Karakamsha uses D1 occupants with houses counted from AK's D9 sign. Swamsha uses
D9 occupants with houses counted from that same sign. Derived lagna labels do
not display the natal ascendant degree. All displayed planet degrees remain
natal D1 degrees, as in the rest of this app.

Arudha repeats the inclusive sign-to-lord count. A raw result in the source sign
or its seventh is moved to the tenth **from the raw result**. All twelve padas
include the source sign, selected lord, lord's sign and actual arithmetic.
Upapada is the twelfth-house Arudha.

Argala compares 2/12, 4/10, 11/3 and secondary 5/9. Counting reverses when Ketu
occupies the target. Three or more malefics in the third supply special Argala
instead of obstruction. Equal counts are explicitly held for strength judgement;
the app does not fabricate an automatic cancellation or numeric aggregate.

Bhava/Hora/Ghati Lagna use the most recent sunrise **before** birth, the Sun at
that sunrise, and rates of 15/30/75 degrees per hour. This follows the stated
astronomical rates; the textbook's Bhava Lagna arithmetic example contains a
minutes/divisor inconsistency. Sree Lagna adds the Moon's nakshatra fraction
times 360 degrees to the natal ascendant.

Brahma uses the classical translation's odd-sign, opposite-six-sign eligibility
rule, followed by the strongest eligible candidate among sixth/eighth/twelfth
lords. The Saturn/node replacement uses inclusive sixth-planet counting.
No eligible candidate is a calculation result: Sthira and Brahma timelines then
explain why they cannot choose a seed. The app never invents a seed to unlock
these methods. Rudra uses the special eighth-sign table and its Saturn exception;
Maheshwara follows the PVR eighth-from-AK rule, node exception and stated
replacement. These are named worksheets, not universally interchangeable rules.

Raja/Yogada checks currently use D1 conditions and the computed Hora/Ghati
Lagnas. Predictions describe actual karaka placements, connections, and Chara
period activation. They do not infer an exact sibling count from a single
significator. The traditional three-pair category is displayed as a classical
classification, not as a numerical lifespan or death-date estimate.

## Primary verification sources

- P. V. R. Narasimha Rao, [Vedic Astrology: An Integrated Approach](https://www.vedicastrologer.org/articles/vedic_astro_textbook.pdf): special lagnas, karakas, Arudha, Argala, strengths, advanced significators and the named PVR dasha conventions.
- B. Suryanarayana Rao, [Jaimini Sutras, English translation](https://www.shanti-ganesha.com/classic/jaimini-sutras.pdf): Adhyaya 2, Brahma eligibility and Navamsa/Sthira/Brahma major-period conventions.
- K. N. Rao's [seven-step Chara Dasha approach](https://www.journalofastrology.com/article.php?article_id=312&category_id=1&hot_page=2) and worked examples in the author's journal.
- [PyJHora, maintained by its author](https://github.com/naturalstupid/PyJHora/tree/main/src/jhora/horoscope/dhasa/raasi): independent cross-check of named Chara antar sequences and the quadrant Mandooka convention. No runtime dependency or imported implementation.

The implementation follows declared arithmetic rather than copying a third-party
astrology program. The calculation rules remain available offline in the app.

## Verification

`tests/test_jaimini_report.py` checks reversal and precision of Rahu ranking,
ties, footed duration arithmetic, Arudha exceptions, co-lords, published Narayana
orders, Argala reversal/special cases, sunrise formulas, complementary cycles,
exact subdivision boundaries through Prana and API input/path validation.

`frontend/tests/ui-jaimini.cjs` exercises all nine sections, all eleven method
selectors, four chart modes, seven/eight karakas, a US browser timezone, laptop
chart fit, mobile widths, retained full data, and blocked external requests.
