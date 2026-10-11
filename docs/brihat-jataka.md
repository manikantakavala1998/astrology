# Brihat Jataka reference and calculations

The app uses the public-domain 1905 edition of *The Brihat Jataka*, translated
and annotated by N. Chidambaram Aiyar, printed by Thompson & Co., Madras.
[Original scan and catalogue](https://archive.org/details/brihatjataka00varaiala).

`docs/sources/brihat-jataka-1905.txt` preserves the downloaded OCR. Run
`python scripts/build_brihat_source.py` to package the edition for installation.
The packaged JSON includes all 28 chapters, front matter and appendix. A test
reconstructs the complete source byte-for-byte and checks its SHA-256 hash.
The complete source remains available through the offline download and chapter endpoints. OCR errors are
not silently corrected. The conclusion identifies chapters XVI and XVII as
later additions; the UI labels them as edition additions.

## Implemented scope

- II.5,13,16–21: benefic/malefic classification; directed fractional aspect
  bands; natural, temporal and compound friendship; Sthana and Dig conditions;
  day/night and lunar-half Kala conditions; natural order. Chesta evaluates
  retrograde motion and the specified Sun/Moon sign range.
- VII.1–4: Pindayurdaya interpolation, enemy and combustion reductions,
  Chakrapata, Lagna contribution and Krurodaya.
- VII.10–13: Amsayurdaya, the largest multiplier once, reductions and Lagna
  contribution. The VII.6 worked example gives 120 years and five days, and the
  VII.10 worked example gives 10 years, six months, 23 days and 24 ghatikas.
- VIII.1–8: selectable Sun/Moon/Lagna start; Kendra, Panaphara and Apoklima
  ordering; antardasha weights and normalization; positional period qualities.
- VIII.9: Naisargika periods, totaling 120 Savana years.
- IX.1–8: all seven BAV tables, verified to match the existing contribution
  table; the source's greater-than-four/equal-to-four/less-than-four reading.
- X.1–3: avocation chains from the tenth lord's Navamsa lord, separately from
  Lagna, Moon and Sun.
- XI.4–11: exact named positional Raja configurations, with both XI.7 variants.
- XII.2–10: all 32 Nabhasa forms; supersession follows XII.10,12 and commentary.
- XIII.2–3: lunar yoga conditions, with primary Kemadruma and the commentary's
  cancellation condition distinguished.
- XIV: all classical co-sign pairs identified with their corresponding stanza.
- XIX/XX: fractional aspects and Bhava placements; XX.11 effect fractions.
- XXI/XXVII: varga placements, own/exalted counts and drekkana references.

The tab contains Strengths, Dashas, Yogas, Chart readings, Ashtakavarga and
Predictions. Overview and Complete book navigation were removed. The visible pages use plain rules and calculations; verse references and book links are omitted at the user’s request. Complete source download and
chapter endpoints remain available.
The complete book is included; every rule is **not** automatically interpreted.
Conception, observed birth circumstances, species, consultation-time lost
horoscopes, and other contextual judgments require additional input or rule
verification. Death and Balarishta chapters remain historical reference text.

## Predictions and graphs

The Predictions tab selects internally source-linked paraphrases for all 84 classical
planet/sign combinations (XVII and XVIII), three avocation chains (X.1–3),
active Nabhasa, lunar and exact Raja configurations, and natal BAV scores
(IX.8). Readings include their actual placements and evaluated strength
conditions. These are selected themes, not exhaustive translations. The
Sun's 10° Aries exception is handled separately. Moon readings identify the
edition's addition; cancelled Kemadruma and superseded Nabhasa effects are
excluded. Both-sided Durudhura is not duplicated as two single-sided effects.

A date/time lookup shows main and subperiod themes (VIII.12–19) from the
currently calculated Pinda/Amsa worksheet. Lagna uses the actual rising lord.
The input is civil time at the birth location's supplied UTC offset; browser
timezone changes do not shift period boundaries. A date outside the worksheet
produces no period reading. Changing worksheet settings requires Calculate,
and the Predictions view explicitly shows when the displayed result is stale.
Both favourable and adverse themes retain their contextual qualifications;
a commencement chart and a complete strongest-planet judgment are not inferred.

The four vertical strength plots count evaluated conditions separately (5/1/1/2
maximum). No combined score or invented strength percentage is introduced.
The plots appear in compact cards, with consistent planetary colors shared
with Balas. Zero is shown by an outlined circle centered on the baseline,
never by a positive-height bar. An entirely zero category explains that no
condition is met. The comparison table uses the same checks as the graphs;
hovering, focusing or clicking a planet reveals its supporting conditions.
Full planet names remain visible on mobile; the comparison table scrolls
inside its own container. The original detailed table remains expandable
under **View rules & calculations**.

Dashas has explicit Ayurdaya (Pinda/Amsa) and Naisargika modes. Both offer date lookup, and Naisargika shows the fixed 0–120 calculation-year age sequence. Ayurdaya exposes per-planet longitude, base formula, multiplier, reductions and final-year steps. Brihat Ashtakavarga uses the
same South Indian charts and color bands as the Parasara view, with seven BAV
charts and a combined SAV. Cell borders are uniform, and the full table remains
available below the charts.

## Conventions and variants

The edition does not define a numeric aggregate that chooses the strongest
Sun/Moon/Lagna in every chart. The dasha start and total power order are
editable. The initial order uses II.21's natural order, with Lagna last for
ties; this is disclosed, not presented as a complete strength judgment.
Power ties are resolved by the user's order, including reappearance ties.
Chakrapata selects only one planet in an occupied sign using this order.

The `Vakra` enemy-reduction exemption offers the author's retrograde reading
and the alternative Mars reading. Lagna years offer Navamsas and the
powerful-rising-sign alternative. Krurodaya offers the primary zodiac-wide
fraction and the commentary's within-sign fraction. The primary text reduces
the combined total; distributing that reduction proportionally among dasha
participants is an explicitly disclosed app convention. Lagna participates
as a subperiod owner only in its own dasha; other antar participants are
planets in the listed houses. The Amsa worksheet does not add the additional
Garga debilitation reduction described in commentary.

Savana years are represented as 360 civil days. Actual sunrise-to-sunrise
day lengths are not integrated into the period dates. The worksheet total
is not a lifespan prediction. Event-chart readings require the chart at the
commencement of the dasha and are not substituted with the natal chart.

House effects and Nabhasa shapes use the edition's XII.6 commentary geometry:
trisection of quadrants between angular middle points, then midpoint
boundaries. Porphyry angular points provide the centers; the app shifts their
boundaries accordingly. Signs are used for conjunctions, friendship,
divisional positions and the explicitly sign-based Ayurdaya/dasha worksheets.
This does not change the user's selected house system elsewhere in the app.

Venus's retrograde combustion limit is illegible in this OCR. That condition
returns unknown pending scan verification; Venus is exempt from the
Ayurdaya combustion reduction. Neutral-sign effect fractions are also left
unquantified, consistent with the verse.

## Other analysis views

The Bhrigu Nandi Nadi interface has been removed at the user's request.
Bhrigu Chakra Paddhati, Bhrigu Sarala Paddhati and Padma Chakra Paddhati are
separate entries in the left Analysis menu. Their calculation
rules remain unchanged.
