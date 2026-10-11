# Bhrigu Nandi Nadi worksheet conventions

The BNN tab uses chart facts and schematic contacts. It does not automatically
interpret all of the book's combinations or establish actual family counts.

Source checked: R.G. Rao, *Bhrigu Nandi Nadi*,
[scanned book transcription](https://ro.scribd.com/document/348729185/Bhrigu-nandi-nadi-RG-Rao-pdf-pdf).
References use chart numbers because printed pagination differs by edition.

## Sibling correction

Chart 1 reads an elder sister from Moon before Jupiter and younger siblings
from forward contacts, including Rahu. Chart 222 instead reads elder siblings
from Mars and following signs. Charts 44 and 431 treat Ketu differently.
Chart 371 considers retrograde Jupiter's previous-sign influence.

These examples do not establish a universal one-planet-per-sibling equation.
The app therefore shows Moon/Venus positions relative to Jupiter and Mars,
plus previous-sign context for retrograde Jupiter. It does not relabel all
contacts as younger siblings or move Jupiter's actual natal position.

The previous implementation also silently retained only one previous-sign
occupant. The complete list is now preserved and sorted by longitude, with a
stable planet-order tie break. Empty indicators do not establish zero siblings.

In `BnnSiblingCount`, `elder_count` and `younger_count` are now null. The
`*_indicator_count`, planet lists and gender breakdowns count **planetary
markers**, not people. `count_status` is `undetermined`; `sister_indicators`
contains the positions needed to inspect the reading. The legacy Python
`elder_planet` property returns the first marker; use `elder_planets` for all.

The regression case is 4 September 1998, 00:03 IST, Rajamahendravaram, with
two elder sisters reported by the user. Lahiri gives retrograde Jupiter in
Pisces, Moon in Capricorn and Venus in Leo. The old output incorrectly inferred
zero elders and seven younger siblings. The regression prevents that inference;
the supplied family history is not used to manufacture an astrological rule.

## Other corrected calculation behavior

- Saturn's contact list includes the previous sign before completing a round.
  The sibling comparison's previous-sign exclusion no longer leaks into career
  calculations. Contacts within a shared sign follow degree order.
- The approximate Saturn ages retain half years. Contacts beyond the requested
  age horizon are omitted instead of being assigned an invented horizon age.
- Both contact worksheets retain the existing inclusive house-ordinal convention,
  with 12-year Jupiter and 30-year Saturn rounds. They are not actual transit dates
  or predicted counts of marriages/jobs.
- Isolation rows report only the configuration; they do not infer lifespan or wealth.

## Location resolution

Indian city searches now include exact alternate names from the bundled
GeoNames data. A smaller place using an old city name cannot hide the renamed
city. Both candidates remain available for disambiguation, ranked by population.
`rjy` resolves to Rajamahendravaram; coordinates come from the same local database.

The old Rajahmundry-only match was at 17.18144 N, 81.36903 E. The city record is
17.00517 N, 81.77784 E, with IST (+05:30). A place change affects location-dependent
calculations; it does not change the geocentric planetary sign positions here.
