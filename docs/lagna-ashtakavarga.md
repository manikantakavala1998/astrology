# Lagna Ashtakavarga

The Ascendant tile previously contained a placeholder. It now shows Lagna's
own unreduced Bhinnashtakavarga, using the favorable positions in Brihat
Parasara Hora Shastra, chapter 66, verses 65–68. The positions were checked
against the primary text on PDF page 129 of [this English translation](https://www.lakshminarayanlenasia.com/articles/BrihatParasaraHoraSastra.pdf#page=129).
They also match the independently published Lagna table in the [Jyotish
calculation library](https://github.com/kunjara/jyotish/blob/master/src/Bala/AshtakaVarga.php).
Only the Lagna recipient table was added; the existing planetary tables
were preserved.

| Contributor | Favorable positions counted from its natal sign | Points |
| --- | --- | --- |
| Sun | 3, 4, 6, 10, 11, 12 | 6 |
| Moon | 3, 6, 10, 11, 12 | 5 |
| Mars | 1, 3, 6, 10, 11 | 5 |
| Mercury | 1, 2, 4, 6, 8, 10, 11 | 7 |
| Jupiter | 1, 2, 4, 5, 6, 7, 9, 10, 11 | 9 |
| Venus | 1, 2, 3, 4, 5, 8, 9 | 7 |
| Saturn | 1, 3, 4, 6, 10, 11 | 6 |
| Lagna | 3, 6, 10, 11 | 4 |

Count the contributor's occupied sign as position 1, then move forward
through the zodiac, wrapping after Pisces. Each contributor adds at most
one favorable point to each sign. Sum the eight contributions: each sign
has 0–8 points, and the twelve-sign total is always 49.

The translation uses rekha/sthana for favorable marks. The application
continues to call favorable points bindus, following its existing South
Indian terminology. It does not count the adverse positions as support.

Lagna is already one of the eight contributors to each planetary BAV.
Its own recipient chart is a separate calculation, not the transposed
Lagna contributor column. For example, the Moon gives five points to
Lagna's chart, while Lagna gives four to the Moon's chart.

The seven planetary BAVs alone form SAV (337); the separate Lagna BAV
is excluded from SAV and from the Bhava redistribution. Brihat Jataka's
seven-planet report retains its existing calculation.

The UI includes each contributor's actual natal sign, its favorable
positions, and the contributors that produced every sign's final score.
For 04/09/1998 00:03, 17.00517 N / 81.77784 E, UTC +05:30, Lahiri and mean
nodes, Lagna is Taurus and the Lagna BAV scores from Aries through Pisces
are **5, 3, 4, 6, 3, 4, 5, 4, 5, 3, 3, 4**.
