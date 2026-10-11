import { useId } from 'react';
import type { BrihatReport } from './BrihatJataka';

const signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];
const layout = [11, 0, 1, 2, 10, null, null, 3, 9, null, null, 4, 8, 7, 6, 5];
function band(score: number, combined: boolean) {
  if (!combined) return score < 4 ? 'critically-weak' : score === 4 ? 'average' : 'strong';
  return score < 20 ? 'critically-weak' : score < 25 ? 'below-average' : score < 28 ? 'average' : score < 32 ? 'strong' : 'exceptional';
}

export function BrihatAshtakavarga({ rows, ascendantSign }: { rows: BrihatReport['ashtakavarga']; ascendantSign: string }) {
  const id = useId();
  const ascendantIndex = signs.indexOf(ascendantSign);
  const houseFor = (signIndex: number) => (signIndex - ascendantIndex + 12) % 12 + 1;
  const combined = signs.map((_, index) => rows.reduce((sum, row) => sum + row.scores[index], 0));
  const tiles = [{ planet: 'SAV', title: 'SAV · Samudaya Ashtakavarga', scores: combined,
    description: `Combined total: ${combined.reduce((sum, count) => sum + count, 0)} bindus across 12 signs`, combined: true },
    ...rows.map(row => ({ ...row, title: row.planet, description: `Natal ${row.sign}: ${row.bindus} bindus · ${row.reading}`, combined: false }))];

  return <div className="server-report bj-ashtaka-charts"><div className="ashtakavarga-tiles">
    {tiles.map(tile => <figure className="ashtakavarga-tile" key={tile.planet} data-ashtaka-planet={tile.planet} aria-labelledby={`${id}-${tile.planet}`}>
      <figcaption><h3 className="mini-chart-title" id={`${id}-${tile.planet}`}>{tile.title}</h3></figcaption>
      <div className="mini-chart-grid" role="group" aria-label={`${tile.planet} South Indian bindu chart`}>
        {layout.map((index, cell) => index === null ? <div className="mini-chart-cell blank" key={`blank-${cell}`} aria-hidden="true" /> :
          <div className="mini-chart-cell" key={index} data-sign={signs[index]} data-bindus={tile.scores[index]} title={`${signs[index]}: ${tile.scores[index]} bindus`}>
            <span className="cell-sign chart-sign-header" title={`${signs[index]}, house ${houseFor(index)}`}><span className="chart-sign-name"><span className="sr-only">{signs[index]}</span><span aria-hidden="true">{signs[index].slice(0, 3)}</span></span><span className="chart-house-label">H{houseFor(index)}</span></span>
            <span className={`cell-bindus sav-band-${band(tile.scores[index], tile.combined)}`}>{tile.scores[index]}</span>
          </div>)}
      </div>
      <p className="hint bj-bindu-caption">{tile.description}</p>
    </figure>)}
  </div></div>;
}
