import type { Bootstrap } from './types';
import type { CSSProperties } from 'react';
import { Planet } from './Jaimini';

const names: Record<string, string> = {Su: 'Sun', Mo: 'Moon', Ma: 'Mars', Me: 'Mercury', Ju: 'Jupiter', Ve: 'Venus', Sa: 'Saturn', Ra: 'Rahu', Ke: 'Ketu'};
export function BhriguNatalChart({state}: {state: Bootstrap}) {
  const cells = state.grids?.D1;
  if (!cells) return null;
  const slots = Math.max(...cells.flat().filter(cell => cell !== null).map(cell => cell.planets.length + Number(cell.is_ascendant)));
  return <div className="bhrigu-natal-grid" aria-label="D1 South Indian natal chart" style={{'--natal-slots': slots} as CSSProperties}>
    {cells.flat().map((cell, i) => cell ? <div className="bhrigu-natal-cell" key={cell.sign}>
      <span className="bhrigu-natal-sign chart-sign-header" title={`${cell.sign}, D1 house ${cell.house}`}><span className="chart-sign-name">{cell.sign}</span><span className="chart-house-label">H{cell.house}</span></span>
      {cell.is_ascendant && <strong className="bhrigu-natal-asc" title={`Ascendant ${state.ascendant?.degree_in_sign.toFixed(4)}°`}>ASC</strong>}
      {cell.planets.map((p, n) => <strong key={`${p.code}-${n}`} title={`${p.natal_degree.toFixed(4)}° in ${cell.sign}${p.dignity_suffix ? ` · ${p.dignity_suffix === 'E' ? 'Exalted' : 'Debilitated'}` : ''}`}><Planet name={names[p.code] ?? p.code} />{p.retrograde && <span className="bhrigu-retro"> (R)</span>}</strong>)}
    </div> : <div className="bhrigu-natal-blank" key={i} aria-hidden="true" />)}
    <div className="bhrigu-natal-center"><strong>D1 Rasi Chakra</strong><span>{state.ascendant?.sign} ascendant</span><span>{state.birth_data?.name}</span></div>
  </div>;
}
