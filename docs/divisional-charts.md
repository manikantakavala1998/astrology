# Divisional chart conventions

All 23 entries calculate signs for the ascendant and all nine planets from the
same sidereal natal longitudes. Houses in each square chart count from its own
ascendant. The displayed planet degrees and dignity markers retain their natal
D1 meaning, as stated in the chart legend.

`p` below is the zero-based part within a 30° natal sign; sign offsets wrap at 12.
Parts include their lower boundary and exclude their upper boundary. D30 uses
unequal segments; every other division uses equal parts. Longitudes wrap at 360°.

## Sixteen Parashari divisions

The rules follow [Brihat Parashara Hora Shastra, chapter 6](https://divyachadhava.com/en/sanatan-sahitya/bphs-chapter-6-the-sixteen-divisions-of-a-r-i).

| Chart | Sign rule |
| --- | --- |
| D1 Rasi | Natal sign |
| D2 Hora | Odd: Leo/Cancer; even: Cancer/Leo |
| D3 Drekkana | Natal sign + 4p |
| D4 Chaturthamsa | Natal sign + 3p |
| D7 Saptamsa | Odd: natal; even: seventh; then + p |
| D9 Navamsa | Movable: natal; fixed: ninth; dual: fifth; then + p |
| D10 Dasamsa | Odd: natal; even: ninth; then + p |
| D12 Dvadasamsa | Natal sign + p |
| D16 Shodashamsa | Movable/fixed/dual: Aries/Leo/Sagittarius + p |
| D20 Vimsamsa | Movable/fixed/dual: Aries/Sagittarius/Leo + p |
| D24 Siddhamsa | Odd/even: Leo/Cancer + p, forward |
| D27 Bhamsa | Fire/earth/air/water: Aries/Cancer/Libra/Capricorn + p |
| D30 Trimsamsa | Odd: Aries/Aquarius/Sagittarius/Gemini/Libra, spans 5/5/8/7/5°. Even: Taurus/Virgo/Pisces/Capricorn/Scorpio, spans 5/7/8/5/5° |
| D40 Khavedamsa | Odd/even: Aries/Libra + p |
| D45 Akshavedamsa | Movable/fixed/dual: Aries/Leo/Sagittarius + p |
| D60 Shashtiamsa | Aries + p, using degrees within the natal sign |

D24 uses forward sign counting for both parities. D60 follows the literal
degree-only instruction in verses 33–41; reversing the deity names for even
signs does not reverse this sign count. Other software may offer other choices.

## Supplementary and composite divisions

The selected conventions are corroborated by the documented chart methods in
the [official PyJHora implementation](https://github.com/naturalstupid/PyJHora/blob/main/src/jhora/horoscope/chart/charts.py)
and its [Panchamsa sign tables](https://github.com/naturalstupid/PyJHora/blob/main/src/jhora/const.py).
These seven entries are additional to the sixteen divisions of BPHS chapter 6.

| Chart | Selected convention |
| --- | --- |
| D5 Panchamsa | Five equal 6° parts: odd Aries/Aquarius/Sagittarius/Gemini/Libra; even Taurus/Virgo/Pisces/Capricorn/Scorpio |
| D6 Shashthamsa | Odd/even: Aries/Libra + p |
| D8 Ashtamsa | Movable/fixed/dual: Aries/Sagittarius/Leo + p |
| D11 Rudramsa | Reverse natal-sign seed from Aries, then forward + p; excludes the reversed Raman variant |
| D81 Navanavamsa | D9 followed by D9; cyclic convention |
| D108 Ashtottaramsa | D9 followed by D12 |
| D144 Dwadasadwadasamsa | D12 followed by D12 |

Composition carries the first chart's fractional degree into the second chart.
D108 and D144 are not replaced by simple harmonic multiplication. Integer
subdivision indices avoid intermediate longitude rounding. The selected
method appears below each chart so comparisons with other applications can
account for different conventions. No PyJHora runtime dependency is required.

## Amsa rulers and designations

Each division has a table for the ascendant and all nine planets, computed
from sidereal natal D1 longitude. It shows the natal sign/degree, one-based
part, its degree span, full deity/designation and source stanza. This does
not move chart placements or change the natal degree labels.

On desktop, the amsa-ruler table appears to the right of every division except
D1. Compact charts and their legends occupy the left column; the table stacks
below them on smaller screens. D1 retains its existing layout and Bhava Chalit
has no subdivision deity table. All ten entries and five table columns remain
available.

Deity order follows [BPHS chapter 6, verses 5–41](https://vedic-astro.s3.amazonaws.com/books/bhrihat_parasara_hora_shastra.pdf#page=9),
cross-checked against the [chapter transcription](https://divyachadhava.com/en/sanatan-sahitya/bphs-chapter-6-the-sixteen-divisions-of-a-r-i).
Names use readable Roman transliteration. Familiar alternate spellings in the
[official PyJHora name resource](https://github.com/naturalstupid/PyJHora/blob/main/src/jhora/lang/amsa_rulers_en.json)
help resolve OCR artifacts such as Dandayudha; no source code was copied.

- D2 displays Surya/Chandra Hora rulership (6.5–6).
- D3 and D4 use their three/four named rulers (6.7–9).
- D7's seven traditional substance names reverse in even natal signs (6.10–11).
- D9 repeats the movable/fixed/dual designation orders in 6.12, including
  the selected translation's dual order Rakshasa, Manushya, Deva.
- D10, D16, D24, D27 and D60 reverse their deity order in even natal signs.
- D12 repeats Ganesha, Ashvini Kumara, Yama, Sarpa three times for either parity.
- D20 uses two distinct 20-name odd/even sequences, not a reversal. The
  source's two Jaya entries in the odd sequence are retained.
- D30 applies deities to its five unequal segments and reverses the complete
  segment order for even signs; it is not treated as 30 equal subdivisions.
- D40 repeats the same 12 names for either parity; Dhata is retained.
- D45 repeats its three names in movable/fixed/dual orders.
- D81, D108 and D144 display both component designations using the actual
  intermediate sign and fractional subdivision. They are labelled component
  rules, not an independently attested deity sequence for the composite.

D1 has no separate amsa subdivision deity in this rule set. D5, D6, D8 and
D11 remain fully available charts, with deity names marked **Not confirmed**
because the selected classical chapter supplies no sequence for them.
