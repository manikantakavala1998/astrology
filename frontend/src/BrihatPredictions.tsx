import { useState } from 'react';
import type { Dasha } from './BrihatJataka';
import type { Bootstrap } from './types';
import { formatDate, formatTime } from './workspace';
import { BrihatDashaPeriods } from './BrihatDashaPeriods';
import { simpleTerms } from './brihatPeriods';

type Reading = { id: string; category: string; title: string; summary: string; evidence: string[]; chapter: number; reference: string; note: string; plain_summary: string; rule: string };
type PeriodTheme = { lord: string; supportive: string; challenging: string; reference: string };
export type Predictions = { readings: Reading[]; period_themes: PeriodTheme[]; lagna_lord: string; source_edition: string; scope: string; timing_note: string };

export function BrihatPredictions({ predictions, dasha, birthData, settingsChanged, onTimeline }: {
  predictions: Predictions; dasha: Dasha; birthData: Bootstrap['birth_data']; settingsChanged: boolean;
  onTimeline: () => void;
}) {
  const [category, setCategory] = useState('All readings');
  const labels: Record<string, string> = { 'All readings': 'All readings', 'Planetary tendencies': 'Personality & habits', 'Work & livelihood': 'Work & money', 'Matched yogas': 'Planet combinations', Ashtakavarga: 'Planet support' };
  const categories = Object.keys(labels);
  const rows = predictions.readings.filter(row => category === 'All readings' || row.category === category);
  return <>
    <section className="astro-panel bj-prediction-intro"><p className="eyebrow">YOUR BIRTH DETAILS → YOUR CHART → YOUR READING</p><h2>🔮 Your predictions, explained simply</h2><p>Each reading below comes from your own planetary placements. It shows what the result means, the rule applied, and the values used in the calculation.</p>{birthData && <p className="hint">Birth input: {formatDate(birthData.birth_date)} · {formatTime(birthData.birth_time)} · Latitude {birthData.latitude.toFixed(4)}° · Longitude {birthData.longitude.toFixed(4)}°</p>}</section>
    <BrihatDashaPeriods predictions={predictions} dasha={dasha} birthData={birthData} settingsChanged={settingsChanged} onTimeline={onTimeline} />
    <section className="astro-panel bj-prediction-content"><div className="bj-prediction-heading"><h2>✨ Chart-based readings</h2><span className="hint" role="status">{rows.length} readings</span></div>
      <nav className="bj-prediction-filters" aria-label="Prediction categories">{categories.map(name => <button key={name} type="button" aria-pressed={category === name} onClick={() => setCategory(name)}>{labels[name]}</button>)}</nav>
      <div className="bj-prediction-list">{rows.map(row => <article className="bj-prediction-reading" key={row.id} data-reading-id={row.id}>
        <p className="quiet-label">{labels[row.category] ?? row.category}</p><h3>{row.title.replace(/XI\.\d+\s*/g, '')}</h3><p>{row.plain_summary || simpleTerms(row.summary)}</p><div className="bj-reading-rule"><strong>Rule applied</strong><p>{simpleTerms(row.rule ?? 'Use the calculated placements shown below.')}</p></div>
        <details><summary>Your calculation</summary><ul>{row.evidence.filter(text => !text.startsWith('Configuration rule:')).map(text => <li key={text}>{simpleTerms(text)}</li>)}</ul></details>
      </article>)}</div>
      {!rows.length && <p>No active configurations in this category for this chart.</p>}
    </section>
  </>;
}
