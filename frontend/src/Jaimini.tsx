import { useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import type { Bootstrap, ChartCell } from './types';
import type { JaiminiReport, JaiminiScheme } from './jaiminiTypes';
import { ChartGrid } from './Dashboard';
import { civilNow, exactDate, JaiminiDasha } from './JaiminiDasha';

const signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];
const tabs = [ ['charts', '🔮', 'Charts & Karakas'], ['aspects', '🔭', 'Rashi Aspects'], ['padas', '✨', 'Arudha Padas'], ['upapada', '💜', 'Upapada'], ['argala', '🔗', 'Argala'], ['dashas', '⏳', 'Dashas'], ['yogas', '🌟', 'Yogas'], ['predictions', '📜', 'Predictions'], ['advanced', '⚙️', 'Advanced'] ];
function Planet({ name }: { name: string }) { return <span className={`planet-color-${name.toLowerCase()}`}>{name}</span>; }
function Planets({ names }: { names: string[] }) { return names.length ? <>{names.map((name, i) => <span key={`${name}-${i}`}>{i > 0 && ', '}<Planet name={name} /></span>)}</> : <>—</>; }
function degrees(value: number) {
  const seconds = Math.floor(value * 3600 + 1e-6);
  return `${Math.floor(seconds / 3600)}°${String(Math.floor(seconds / 60) % 60).padStart(2, '0')}′${String(seconds % 60).padStart(2, '0')}″`;
}
function Rules({ children, label = 'Rules & calculations' }: { children: ReactNode; label?: string }) { return <details className="jaimini-rules"><summary>{label}</summary>{typeof children === 'string' ? <p>{children}</p> : children}</details>; }
function Table({ title, headings, rows }: { title: string; headings: string[]; rows: ReactNode[][] }) {
  return <div className="table-scroll jaimini-table-scroll" tabIndex={0} role="region" aria-label={title}><table className="jaimini-table"><caption className="sr-only">{title}</caption>
    <thead><tr>{headings.map(h => <th key={h} scope="col">{h}</th>)}</tr></thead><tbody>{rows.map((row, i) => <tr key={i}>{row.map((cell, j) => j === 0 ? <th key={j} scope="row">{cell}</th> : <td key={j}>{cell}</td>)}</tr>)}</tbody>
  </table></div>;
}
function Panel({ title, children }: { title: string; children: ReactNode }) { return <section className="astro-panel jaimini-panel"><h2>{title}</h2>{children}</section>; }
function Karakas({ scheme, rule }: { scheme: JaiminiScheme; rule: string }) {
  return <Panel title="🪐 Chara Karakas">
    <Table title="Chara Karakas" headings={['Karaka', 'Planet', 'Degree', 'D1 sign', 'D9 sign']} rows={scheme.karakas.map(k => [<><strong>{k.name}</strong><small>{k.role} · {k.meaning}</small></>, <Planet name={k.planet} />, <span title={k.calculation}>{degrees(k.degree)}{k.planet === 'Rahu' && <small>Rank: {degrees(k.effective_degree)}</small>}</span>, k.sign, k.navamsa_sign])} />
    <Rules>{rule}</Rules>
  </Panel>;
}
function Readings({ scheme, short = false }: { scheme: JaiminiScheme; short?: boolean }) {
  return <div className="jaimini-readings">{scheme.readings.slice(0, short ? 3 : undefined).map(r => <article key={r.topic}>
    <h3>{r.topic} <Planet name={r.planet} /></h3><p>{r.summary}</p><p className="jaimini-evidence">{r.evidence}</p>{!short && <Rules>{r.rule}</Rules>}
  </article>)}</div>;
}
function chartCells(cells: (ChartCell | null)[][], lagna: string): (ChartCell | null)[][] {
  return cells.map(row => row.map(cell => cell && ({ ...cell, house: (signs.indexOf(cell.sign) - signs.indexOf(lagna) + 12) % 12 + 1, is_ascendant: cell.sign === lagna })));
}

// Shared presentation only; Jaimini 2 supplies its own independent report.
export { Planet, Planets, degrees, Rules, Table, Panel, Karakas, Readings, chartCells };

export function Jaimini({ state, report, active }: { state: Bootstrap; report: JaiminiReport; active: boolean }) {
  const [view, setView] = useState('charts');
  const [count, setCount] = useState('7');
  const [chart, setChart] = useState('D1');
  const [argalaTarget, setArgalaTarget] = useState(state.ascendant?.sign ?? 'Aries');
  const [predictionDate, setPredictionDate] = useState(() => civilNow(state.birth_data?.utc_offset_hours ?? 0).slice(0, 10));
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const scheme = report.schemes[count];
  const advanced = scheme.advanced;
  const up = report.upapada;
  const source = chart === 'Swamsha' || chart === 'D9' ? 'D9' : 'D1';
  const derived = chart === 'Karakamsha' || chart === 'Swamsha';
  const cells = state.grids?.[source];
  const chara = report.dasha_systems.find(s => s.code === 'chara')!;
  const point = `${predictionDate}T12:00:00`;
  const current = chara.periods.find(p => p.start <= point && point < p.end);
  const currentSign = current?.sign;
  const currentPlanets = report.aspects.filter(p => p.sign === currentSign).map(p => p.planet);
  const currentConnections = report.aspects.filter(p => currentSign && p.aspected_signs.includes(currentSign)).map(p => p.planet);
  function moveTab(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    setView(tabs[next][0]); tabRefs.current[next]?.focus();
  }
  // Keep navigation choices across sidebar changes without rendering duplicate charts.
  if (!active) return null;
  return <div className="jaimini-workspace">
    <div className="jaimini-toolbar"><div className="jaimini-tabs" role="tablist" aria-label="Jaimini North sections">{tabs.map(([id, emoji, label], i) =>
      <button key={id} type="button" role="tab" id={`jaimini-tab-${id}`} aria-controls={`jaimini-view-${id}`} aria-selected={view === id} tabIndex={view === id ? 0 : -1}
        ref={node => { tabRefs.current[i] = node; }} onClick={() => setView(id)} onKeyDown={e => moveTab(e, i)}><span aria-hidden="true">{emoji}</span>{label}</button>)}</div>
      <div className="chart-switch jaimini-karaka-switch" role="group" aria-label="Chara Karaka scheme">{['7', '8'].map(n => <button type="button" key={n} aria-pressed={count === n} onClick={() => setCount(n)}>{n} karakas</button>)}</div>
    </div>
    <div role="tabpanel" id={`jaimini-view-${view}`} aria-labelledby={`jaimini-tab-${view}`}>
      {view === 'charts' && <>
        <div className="jaimini-overview-grid">
          <Panel title="🔮 Your Jaimini North chart"><div className="chart-switch jaimini-chart-switch" role="group" aria-label="Jaimini North chart">{['D1', 'D9', 'Karakamsha', 'Swamsha'].map(c => <button key={c} type="button" aria-pressed={chart === c} onClick={() => setChart(c)}>{c}</button>)}</div>
            {cells && <ChartGrid cells={derived ? chartCells(cells, scheme.karakamsha) : cells} code={derived ? chart : source} centerTitle={derived ? scheme.karakamsha : undefined} state={state} showAscendantDegree={!derived} />}
            <p className="chart-legend">{derived ? `Houses start from ${scheme.karakamsha}, the Atmakaraka’s D9 sign.` : '(R) Retrograde · (E) Exalted · (D) Debilitated'}<br />Degrees show natal D1 positions.</p>
            <Rules>{report.rules.karakamsha}</Rules>
          </Panel>
          <Karakas scheme={scheme} rule={report.rules.karakas} />
        </div>
        <div className="jaimini-bottom-grid"><JaiminiDasha systems={report.dasha_systems} birth={state.birth_data} compact />
          <Panel title="📜 Your chart, explained"><Readings scheme={scheme} short /><button type="button" className="text-action" onClick={() => setView('predictions')}>Read all chart indications →</button></Panel>
        </div>
      </>}
      {view === 'aspects' && <Panel title="🔭 Rashi Drishti · Sign aspects"><p className="jaimini-intro">Read the planets and signs connected to each of your planets.</p>
        <Table title="Jaimini sign aspects" headings={['Planet', 'Occupied sign', 'Aspected planets', 'Aspected signs']} rows={report.aspects.map(p => [<><Planet name={p.planet} />{p.retrograde && ' (R)'}</>, p.sign, p.aspected_planets.length ? p.aspected_planets.map((q, i) => <span className="jaimini-aspect-link" key={q.planet}>{i > 0 && ' · '}<Planet name={q.planet} /> ({q.sign})</span>) : '—', p.aspected_signs.join(', ')])} /><Rules>{report.rules.aspects}</Rules>
      </Panel>}
      {view === 'padas' && <Panel title="✨ All 12 Arudha Padas"><p className="jaimini-intro">Arudha shows the projected image of a house. Every pada is calculated from its house sign and lord.</p>
        <Table title="Arudha Padas" headings={['Pada', 'Result sign', 'House sign', 'Lord', 'Lord’s sign', 'Calculation']} rows={report.padas.map(p => [<>{p.code}<small>{p.name}</small></>, p.sign, p.source_sign, <Planet name={p.lord} />, p.lord_sign, p.calculation])} />
      </Panel>}
      {view === 'upapada' && <>
        <Panel title="💜 Upapada Lagna · Relationship worksheet"><p className="jaimini-intro">{up.rule}</p>
          <div className="jaimini-facts"><div><span>Upapada</span><strong>{up.sign}</strong></div><div><span>Upapada lord</span><strong><Planet name={up.lord} /></strong></div><div><span>Second from Upapada</span><strong>{up.second_sign}</strong></div><div><span>Second-sign lord</span><strong><Planet name={up.second_lord} /></strong></div></div>
          <Table title="Upapada connections" headings={['Factor', 'Your chart']} rows={[
            ['Planets in Upapada', <Planets names={up.occupants} />], ['Planets in its second sign', <Planets names={up.second_occupants} />], ['Sign aspects to Upapada', <Planets names={up.aspecting} />],
            ['Darakaraka', <Planets names={scheme.karakas.filter(k => k.role === 'DK').map(k => k.planet)} />],
            ['Upapada calculation', report.padas[11].calculation],
          ]} />
          <p className="jaimini-quiet">These factors are read together. A single placement does not determine a marriage event or date.</p>
        </Panel><Karakas scheme={scheme} rule={report.rules.karakas} />
      </>}
      {view === 'argala' && <Panel title="🔗 Argala & Virodhargala"><div className="jaimini-panel-heading"><p className="jaimini-intro">See which planets intervene and which planets obstruct them.</p>
        <label>Target sign<select aria-label="Argala target sign" value={argalaTarget} onChange={e => setArgalaTarget(e.target.value)}>{signs.map(s => <option key={s}>{s}</option>)}</select></label></div>
        <Table title={`Argala on ${argalaTarget}`} headings={['Intervention', 'Planets', 'Obstruction', 'Planets', 'Result', 'Calculation']} rows={report.argala.filter(r => r.target === argalaTarget).map(r => [<>{r.argala_sign}<small>Position {r.argala_house}{r.reverse && ' · reversed'}</small></>, <Planets names={r.argala_planets} />, <>{r.blocking_sign}<small>Position {r.blocking_house}{r.special && ' · special Argala'}</small></>, <Planets names={r.blocking_planets} />, r.status, r.calculation])} /><Rules>{report.rules.argala}</Rules>
      </Panel>}
      {view === 'dashas' && <JaiminiDasha systems={report.dasha_systems} birth={state.birth_data} />}
      {view === 'yogas' && <><Panel title="🌟 Raja Yoga & Yogada conditions"><p className="jaimini-intro">Each condition includes the planets and sign connections that produced the result.</p>
        <Table title="Jaimini yoga conditions" headings={['Condition', 'Detected', 'Your chart', 'Rule']} rows={scheme.yogas.map(y => [y.name, y.present ? 'Yes' : 'No', y.evidence, y.rule])} />
        <p className="jaimini-quiet">Yogada checks use D1 here; no condition is presented as a guaranteed outcome.</p>
      </Panel><Panel title="⚖️ Relative sign strengths">
        <Table title="Jaimini relative sign strengths" headings={['Rank / sign', 'Lord', 'Occupants', 'Connections', 'Exalted', 'Opposite parity', 'Type rank', 'Lord advancement']} rows={report.strengths.map((s, i) => [`${i + 1}. ${s.sign}`, <Planet name={s.lord} />, <Planets names={s.occupants} />, s.metrics[1], s.metrics[2] ? 'Yes' : 'No', s.metrics[3] ? 'Yes' : 'No', ['Movable', 'Fixed', 'Dual'][s.metrics[4]], degrees(s.metrics[5])])} /><Rules>{report.rules.strength}</Rules>
      </Panel></>}
      {view === 'predictions' && <>
        <Panel title="📜 Your Jaimini North chart, in plain language"><p className="jaimini-intro">Your karakas identify the planets to examine for each part of life. The placements and connections below explain why.</p><Readings scheme={scheme} /></Panel>
        <Panel title="⏳ What your Chara Dasha activates"><label className="jaimini-date-label">Choose a date<input type="date" value={predictionDate} onChange={e => { if (e.target.value) setPredictionDate(e.target.value); }} /></label>
          {current ? <><h3>{current.sign} period</h3><p>{exactDate(current.start)} – {exactDate(current.end)}</p>
            <Table title="Dasha activation" headings={['Factor', 'Activated in your chart']} rows={[
              ['Planets occupying the period sign', <Planets names={currentPlanets} />], ['Planets sign-aspecting the period sign', <Planets names={currentConnections} />],
              ['Connected karaka topics', scheme.karakas.filter(k => currentPlanets.includes(k.planet) || currentConnections.includes(k.planet)).map(k => `${k.meaning} (${k.planet})`).join('; ') || 'No direct karaka connection'],
              ['Padas in the period sign', report.padas.filter(p => p.sign === current.sign).map(p => `${p.code} — ${p.name}`).join('; ') || 'None'],
            ]} /><Rules><p>{current.rule}</p><p>A sign period directs attention to its occupants, sign aspects and Arudha padas. This identifies topics to examine; it does not by itself establish that an event will occur. Date lookup uses noon at your birth-place offset.</p></Rules>
          </> : <p className="hint">This date falls outside the calculated Chara Dasha cycle.</p>}
        </Panel>
      </>}
      {view === 'advanced' && <>
        <Panel title="⚙️ Special Lagnas"><Table title="Special Lagnas" headings={['Lagna', 'Sign', 'Degree', 'Calculation']} rows={report.lagnas.map(l => [<>{l.name}<small>{l.code}</small></>, l.sign, degrees(l.degree), <>{l.calculation}{l.sunrise && <small>Sunrise {exactDate(l.sunrise)}</small>}</>])} />
          <p className="jaimini-quiet">Bhava, Hora and Ghati Lagna use the most recent sunrise before birth. Sree Lagna uses the Moon’s progress through its nakshatra.</p>
        </Panel>
        <div className="jaimini-advanced-grid"><Panel title="🪐 Sthira Karakas"><Table title="Sthira Karakas" headings={['Topic', 'Fixed significator']} rows={advanced.sthira_karakas.map(k => [k.meaning, <Planet name={k.planet} />])} /></Panel>
          <Panel title="⚖️ Brahma, Rudra & Maheshwara"><Table title="Advanced significators" headings={['Significator', 'Planet', 'Calculation']} rows={[
            ['Brahma', advanced.brahma ? <Planet name={advanced.brahma} /> : 'No eligible candidate', advanced.brahma_rule], ['Rudra', <Planet name={advanced.rudra} />, advanced.rudra_rule],
            ['Secondary Rudra', <Planets names={advanced.secondary_rudra} />, 'Weaker candidate in debilitation or an enemy sign, connected to malefics.'], ['Maheshwara', <Planet name={advanced.maheswara} />, advanced.maheswara_rule], ['Trishoola signs', advanced.trishoola.join(', '), 'Rudra’s sign and its two trines.'],
          ]} /><Rules><p>Brahma seed: {advanced.brahma_seed}.</p><Table title="Brahma candidates" headings={['Planet', 'Occupied sign', 'Eligible']} rows={advanced.brahma_candidates.map(p => [<Planet name={p.planet} />, p.sign, p.eligible ? 'Yes' : 'No'])} /></Rules></Panel></div>
        <Panel title="📐 Traditional three-pair worksheet"><Table title="Traditional three-pair categories" headings={['Pair', 'First sign', 'Second sign', 'Types', 'Category']} rows={advanced.longevity_pairs.map(p => [p.pair, p.first, p.second, `${p.first_type} / ${p.second_type}`, p.category])} />
          <p className="jaimini-quiet">Calculated traditional category: <strong>{advanced.traditional_category}</strong>. This is a classical classification, not a lifespan estimate.</p><Rules>{advanced.category_rule}</Rules>
        </Panel>
      </>}
    </div>
  </div>;
}
