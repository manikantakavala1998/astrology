# Jaimini 2

This is a separate engine for Medavarapu Sampath Kumar's *A Comprehensive
Guide for Jaimini Astrologers*, English translation by Dr K. V. Pratap Kumar:
https://www.scribd.com/document/860339057/A-Comprehensive-Guide-for-Jamini-Astrologers

`jaimini2.py` calculates the seven-karaka scheme, sign aspects, house arudhas,
standard and research Upapadas, Argala degree checks, D1/D3/D9 Yogada,
Karakamsha readings and the Parivritti Dwaya Hora three-pair worksheet.
`jaimini2_dasha.py` maintains all 38 catalog entries. Neither module imports
`jaimini`, `jaimini_report` or `jaimini_dasha`. React presentation components
are shared; author calculations are not. No existing calculation is replaced.

## Explicit conventions

- Unrounded natal degrees rank the seven classical planets. Ordinary Rahu/Ketu
  roles are excluded. Exact ties generate a warning and suppress dates until
  the exceptional assignment can be resolved.
- Rashi aspects use the shared classical modality geometry, not graha aspects.
- The sign hierarchy follows the fourfold chapter (occupied, count, greatest
  occupant degree, dual > fixed > movable). This differs from the earlier
  Argala paragraph's fixed/movable ordering. Equal keys retain the first
  candidate in the method's listed set; the UI discloses that convention.
- Co-lords use the book's exclusive exaltation and own-sign exception,
  companions, sign type and duration. Node exaltations are local to this
  engine: Ketu/Leo, Rahu/Aquarius. Ayurdaya uses Saturn alone for Aquarius.
- The arudha mirror uses the common classical first/seventh correction, stated
  alongside each result. The book's standard twelfth-house UL is separate
  from its Anuchara/Agrachara research variants. Both research worksheets are
  shown; no gender is inferred. Research own-sign cases use the illustrated
  fourth-house rule; retrograde adjustments are disclosed.
- Argala implements the explicit first-quarter/last-quarter example. It does
  not invent rules for other quarter correspondences or a numeric strength
  percentage. Kaama and Bhava Argala are separate rows. Only Ketu's specified
  fifth/ninth and sixth/eighth pairs reverse.
- Brahma uses the preceding-occupied-odd-sign variant. Maheshwara uses the
  sixth/eighth/twelfth-lord variant; Rudra uses seventh/eighth lords.
  These are labelled variants, not an undisclosed blend of commentators.
- Chara starts at the stronger Lagna/fourth and counts **lord to sign**.
  Navamsa starts from odd D9 Lagna / opposite even D9 Lagna and reads D9.
  Neither inherits the other engine's footed-sign direction or year corrections.
- Drig reverses each trinal block according to its own parity, matching the
  Ramakrishna example's Libra–Aquarius–Gemini–Scorpio–Cancer–Pisces sequence.
  Its duration uses the prose's modal 7/8/9 rule, not the example's inconsistent
  opening seven-year value for fixed Libra.
- The calendar uses a declared **360-day calculation year**, consistent with
  the book's 12-year/12-month/30-day subdivision arithmetic. Dates start at
  birth; only one documented major cycle is generated. Boundaries are
  start-inclusive and end-exclusive at the birth-place offset.
- Antardasha and Pratyantardasha divide each parent into twelve equal parts,
  matching the book's Navamsa duration table (12 years / 12 months / 30 days).
  **Child ordering is an explicitly labelled explorer convention** wherever
  the book lacks a unique seed/order: start at the parent and apply the local
  method's sequence. It is not presented as a verified author-specific event
  timing rule. Nisarga's seven-planet/twelve-division conflict remains held.
  The independent `/api/jaimini2/subperiods` endpoint validates paths against
  calculated roots and returns exact contiguous parent-bounded intervals.
  It never calls the other tab's endpoint or subdivision engine.
- Keeta and Nakshatra III explicitly label the author's **proposed** modal
  allocations. Gochara is labelled a Trikona timeline alias; it does not claim
  to evaluate transit positions. Shashtashtama labels the first Jayabhavapa
  variant. Bhavapamsha uses the later-body/summary variant and holds its
  ambiguous Moon-in-eighth override.

## Availability and validation

The catalog contains every named method, with either a dated table or an
entry-specific explanation and calculable intermediate worksheet. A missing
formula, contradictory seed/order, or conditional applicability failure never
produces fabricated dates. In particular Yogartha supplies its opening
average while explaining why the rest cannot be completed from this chapter.

Predictions retain the matching condition, reading chart and rule. Chara's
Venus indication is scoped to Chara. D9-based methods use D9 occupants and
aspects; natal arudhas are not silently transplanted into D9. Lifespan/death,
medical diagnoses, criminality and caste claims are not personal predictions.
The Ayurdaya category is an explicitly traditional worksheet, not an age.

The UI exposes separate Yogada & Kevala, Sign Strength and Ayurdaya tabs,
matching the calculation-workspace layout, with D1/D3/D9/Karakamsha/Swamsha.
Sign strength is graphed as relative rank, with equal fourfold keys sharing
the same rank and bar height. Selecting a sign shows its underlying count,
degree and type; all arithmetic remains in the expandable calculation table.
Yogada and Kevala show only qualifying planets, grouped without duplicates.
The other D9 support checks remain in the calculation report and predictions.
Yogada's table exposes D1/D3/D9 matches; Kevala's table exposes target signs
and houses. Moon-dispositor Kevala additionally checks exactly one of Moon
or Lagna, without duplicating a planet already qualified by the house rule.

Detailed predictions contain AL wealth/A7/eleventh-house conditions, all
12 pada connection worksheets, three separate Upapada conventions,
Karakamsha in D1 and Swamsha in D9, and individual Yogada/Kevala companion
and second-house readings. D1 and D9 occupations are never interchanged.
The dated comparison and explorer sign badges evaluate verified Chara,
Navamsa and Trikona/Gochara result conditions. Unknown method-specific
outcomes remain explicitly unclassified. Gochara transit conditions are not
computed. Support plus pressure is labelled mixed; absent support is not
treated as bad. No weighted score, certain event, disease or death prediction
is created. Classical caste/appearance/moral accusations are not repackaged
as personal outcomes.

Tests cover published sequence/Argala examples, half-sign Hora boundaries,
inverse Chara counts, node exaltation, conditional Nisarga, all catalog entries,
calendar continuity, the book's subdivision duration table, validated branch
paths, independent engines and server/desktop/mobile integration.
