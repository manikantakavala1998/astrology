import { useEffect, useRef, useState } from 'react';
import { ChartGrid, PanelTitle } from './Dashboard';
import type { Bootstrap } from './types';

type Role = { planet: string; houses: number[]; role: string; tone: string; trines: number[]; adverse: number[];
  kendras: number[]; maraka_houses: number[]; yogakaraka: boolean; calculation: string; sign?: string;
  natal_house?: number; dignity?: string; retrograde?: boolean; lord?: string; companions?: string[] };
type Rule = { number: number; group: string; name: string; condition: string; status: string; calculation: string; result: string };
type Reading = { major: string; minor: string; tone: string; result: string; relationship: string[]; rules: number[]; notes: string[] };
type Minor = { planet: string; start: string; end: string; reading: Reading };
export type LaghuReport = { ascendant: string; roles: Role[]; nodes: Role[]; houses: { house: number; sign: string; lord: string }[];
  all_ascendants: { ascendant: string; roles: Role[] }[]; connections: { planets: string[]; links: string[] }[];
  yogas: { planets: string[]; links: string[]; status: string; calculation: string }[];
  rules: Rule[]; aspects: { planet: string; sign: string; house: number; aspect: number; target_sign: string; target_house: number; targets: string[] }[];
  maraka_candidates: { planet: string; reasons: string[] }[]; saturn_maraka_links: string[];
  periods: { planet: string; start: string; end: string; sub_periods: Minor[] }[]; conventions: string[] };
const views = ['Your Lagna', 'All 12 ascendants', 'Yogakaraka & Raja Yoga', 'Dasha & Antardasha', 'Maraka rules', 'All rules'];
const icons = ['◈', '▦', '✨', '⌛', '◇', '📖'];
const color = (planet: string) => `planet-color-${planet.toLowerCase()}`;
const houses = (values: number[]) => values.map(value => `H${value}`).join(', ') || '—';
function Badge({ tone, children }: { tone: string; children: React.ReactNode }) { return <span className={`lp-badge ${tone}`}>{children}</span>; }
function RuleDetail({ rule }: { rule: Rule }) {
  return <details className="lp-rule-detail"><summary>{rule.number}. {rule.name}<span>{rule.status}</span></summary>
    <div><p><strong>Rule</strong> {rule.condition}</p>{rule.calculation && <p><strong>Calculation</strong> {rule.calculation}</p>}<p><strong>Result</strong> {rule.result}</p></div></details>;
}
function RoleTable({ rows, selected, choose }: { rows: Role[]; selected?: string; choose?: (name: string) => void }) {
  return <div className="table-scroll"><table className="lp-table"><thead><tr><th>Planet / position</th><th>Owns</th><th>Functional role</th><th>Why this role applies</th></tr></thead>
    <tbody>{rows.map(row => <tr key={row.planet}>
      <td>{choose ? <button className={`lp-planet-button ${color(row.planet)}`} aria-pressed={selected === row.planet} onClick={() => choose(row.planet)}>{row.planet}</button> : <strong className={color(row.planet)}>{row.planet}</strong>}
        {row.sign && <small>{row.sign} · H{row.natal_house}</small>}</td><td>{houses(row.houses)}</td>
      <td><Badge tone={row.tone}>{row.role}</Badge>{row.maraka_houses.length > 0 && <small>Maraka role: {houses(row.maraka_houses)}</small>}</td>
      <td>{row.calculation}</td></tr>)}</tbody></table></div>;
}
function stamp(value: string) { return Date.parse(`${value.replace(/\.\d+$/, '')}Z`); }
function periodDate(value: string) { return value.slice(0, 10).split('-').reverse().join('/'); }

export function LaghuParashari({ report, state }: { report: LaghuReport; state: Bootstrap }) {
  const [view, setView] = useState(views[0]);
  const [asc, setAsc] = useState(report.ascendant);
  const [planet, setPlanet] = useState(report.roles.find(row => row.yogakaraka)?.planet ?? report.roles[0].planet);
  const [asOf, setAsOf] = useState((state.current_dasha?.as_of ?? `${state.birth_data!.birth_date}T${state.birth_data!.birth_time}`).slice(0, 19));
  const firstIndex = report.periods.findIndex(period => stamp(period.start) <= stamp(asOf) && stamp(asOf) < stamp(period.end));
  const [majorIndex, setMajorIndex] = useState(firstIndex);
  const initialMinor = firstIndex < 0 ? -1 : report.periods[firstIndex].sub_periods.findIndex(period => stamp(period.start) <= stamp(asOf) && stamp(asOf) < stamp(period.end));
  const [minorIndex, setMinorIndex] = useState(initialMinor);
  const majorScroll = useRef<HTMLDivElement>(null);
  const minorScroll = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (view !== 'Dasha & Antardasha') return;
    for (const ref of [majorScroll, minorScroll]) {
      const container = ref.current;
      const row = container?.querySelector<HTMLTableRowElement>('tr[aria-selected="true"]');
      if (!container || !row) continue;
      const bounds = container.getBoundingClientRect();
      const selectedBounds = row.getBoundingClientRect();
      const headerHeight = container.querySelector('thead')?.getBoundingClientRect().height ?? 0;
      if (selectedBounds.top < bounds.top + headerHeight || selectedBounds.bottom > bounds.bottom) {
        container.scrollTop += selectedBounds.top - bounds.top - headerHeight;
      }
    }
  }, [view, majorIndex, minorIndex]);
  const selected = report.roles.find(row => row.planet === planet)!;
  const currentMajor = report.periods[majorIndex];
  const currentMinor = currentMajor?.sub_periods[minorIndex];
  const trineSupport = report.roles.filter(row => row.tone === 'good' || row.yogakaraka).map(row => row.planet);
  function selectTime(value: string) {
    setAsOf(value.slice(0, 19));
    const index = report.periods.findIndex(period => stamp(period.start) <= stamp(value) && stamp(value) < stamp(period.end));
    setMajorIndex(index);
    setMinorIndex(index < 0 ? -1 : report.periods[index].sub_periods.findIndex(period => stamp(period.start) <= stamp(value) && stamp(value) < stamp(period.end)));
  }
  const rules = (numbers: number[]) => report.rules.filter(rule => numbers.includes(rule.number)).map(rule => <RuleDetail key={rule.number} rule={rule} />);
  return <div className="laghu-workspace">
    <div className="lp-tabs" role="tablist" aria-label="Laghu Parashari views">{views.map((name, index) => <button key={name} role="tab" aria-selected={view === name} aria-controls={`lp-view-${index}`} id={`lp-tab-${index}`} onClick={() => setView(name)}><span aria-hidden="true">{icons[index]}</span> &nbsp; {name}</button>)}</div>
    <section role="tabpanel" id={`lp-view-${views.indexOf(view)}`} aria-labelledby={`lp-tab-${views.indexOf(view)}`}>
    {view === 'Your Lagna' && <>
      <div className="lp-metrics">
        <div><span>Your ascendant</span><strong>{report.ascendant}</strong></div>
        <div><span>Standalone Yogakaraka</span><strong>{report.roles.filter(row => row.yogakaraka).map(row => row.planet).join(', ') || 'None'}</strong></div>
        <div><span>Benefic ownership support</span><strong>{trineSupport.join(' · ') || 'Conditional'}</strong></div>
        <div><span>Lagna lord</span><strong className={color(report.houses[0].lord)}>{report.houses[0].lord}</strong></div>
      </div>
      <div className="lp-overview">
        <section className="astro-panel lp-chart"><PanelTitle emoji="🔮">Your natal chart · D1</PanelTitle><ChartGrid cells={state.grids!.D1} code="D1" state={state} />
          <p className="chart-legend">(R) Retrograde · (E) Exalted · (D) Debilitated</p>
          <div className="lp-house-lords"><span>Kendra lords · H1, H4, H7, H10</span><p>{report.houses.filter(row => [1, 4, 7, 10].includes(row.house)).map(row => <span key={row.house}>H{row.house} <strong className={color(row.lord)}>{row.lord}</strong></span>)}</p></div>
        </section>
        <section className="astro-panel"><PanelTitle emoji="⚖️">Benefic & malefic for your Lagna</PanelTitle><p className="hint">Functional role follows house ownership. Select a planet for its complete calculation.</p><RoleTable rows={report.roles} selected={planet} choose={setPlanet} /></section>
      </div>
      <div className="lp-bottom">
        <section className="astro-panel"><PanelTitle emoji="✨">{selected.planet} · rules & calculation</PanelTitle><p className="lp-selected"><Badge tone={selected.tone}>{selected.role}</Badge> Owns {houses(selected.houses)}</p><p className="hint">{selected.calculation}</p><p className="hint">Natal placement: {selected.sign} · H{selected.natal_house} · {selected.dignity}{selected.retrograde ? ' · Retrograde' : ''}</p>{rules([selected.yogakaraka ? 20 : 6, 8])}</section>
        <section className="astro-panel"><PanelTitle emoji="☊">Rahu & Ketu · chart connections</PanelTitle><div className="lp-node-grid">{report.nodes.map(node => <div key={node.planet}><strong className={color(node.planet)}>{node.planet} · {node.sign} · H{node.natal_house}</strong><p>Sign lord: <span className={color(node.lord!)}>{node.lord}</span></p><p>Companions: {node.companions!.join(', ') || 'None'}</p></div>)}</div>{rules([13, 21])}</section>
      </div>
    </>}
    {view === 'All 12 ascendants' && <section className="astro-panel"><PanelTitle emoji="▦">Lordship for every ascendant</PanelTitle><label className="lp-asc-picker">Ascendant <select value={asc} onChange={event => setAsc(event.target.value)}>{report.all_ascendants.map(row => <option key={row.ascendant}>{row.ascendant}</option>)}</select></label><RoleTable rows={report.all_ascendants.find(row => row.ascendant === asc)!.roles} />{rules([6, 7, 8, 9, 10, 11, 12])}</section>}
    {view === 'Yogakaraka & Raja Yoga' && <>
      <section className="astro-panel"><PanelTitle emoji="✨">Yoga conditions in your chart</PanelTitle>{report.roles.filter(row => row.yogakaraka).map(row => <p key={row.planet}><strong className={color(row.planet)}>{row.planet}</strong> owns {houses(row.houses)} · Standalone Yogakaraka</p>)}
        {!report.yogas.length && <p className="hint">No direct Kendra–trine planet pair is formed.</p>}
        <div className="table-scroll"><table><thead><tr><th>Planets</th><th>Relationship</th><th>House ownership</th><th>Result</th></tr></thead><tbody>{report.yogas.map(row => <tr key={row.planets.join('-')}><td>{row.planets.join(' + ')}</td><td>{row.links.join(', ')}</td><td>{row.calculation}</td><td>{row.status}</td></tr>)}</tbody></table></div>{rules([14, 15, 16, 17, 20, 21, 22, 41, 42])}</section>
      <section className="astro-panel lp-aspects"><PanelTitle emoji="🔭">Classical planetary aspects</PanelTitle><div className="table-scroll"><table><thead><tr><th>Planet</th><th>Planet sign / house</th><th>Aspect</th><th>Aspected sign / house</th><th>Planets reached</th></tr></thead><tbody>{report.aspects.map(row => <tr key={`${row.planet}-${row.aspect}`}><td className={color(row.planet)}>{row.planet}</td><td>{row.sign} · H{row.house}</td><td>{row.aspect}th</td><td>{row.target_sign} · H{row.target_house}</td><td>{row.targets.join(', ') || 'None'}</td></tr>)}</tbody></table></div></section>
    </>}
    {view === 'Dasha & Antardasha' && <section className="astro-panel"><PanelTitle emoji="⌛">Vimshottari · period rules</PanelTitle><div className="lp-date-control"><label>View at birth-place time<input type="datetime-local" step="1" value={asOf} onChange={event => selectTime(event.target.value)} /></label><button className="secondary-button" onClick={() => selectTime(new Date(Date.now() + state.birth_data!.utc_offset_hours * 3600000).toISOString().slice(0, 19))}>Today</button></div>
      {majorIndex < 0 && <p className="hint">The selected date falls outside the calculated Vimshottari timeline.</p>}
      <div className="lp-period-grid"><div><h3>Mahadasha</h3><div className="lp-period-scroll" ref={majorScroll}><table><thead><tr><th>Planet</th><th>Start</th><th>End</th></tr></thead><tbody>{report.periods.map((row, index) => <tr key={`${row.planet}-${row.start}`} aria-selected={index === majorIndex}><td><button className={color(row.planet)} onClick={() => selectTime(row.start.slice(0, 19))}>{row.planet}</button></td><td>{periodDate(row.start)}</td><td>{periodDate(row.end)}</td></tr>)}</tbody></table></div></div>
        <div><h3>Antardasha</h3><div className="lp-period-scroll" ref={minorScroll}><table><thead><tr><th>Planet</th><th>Start</th><th>End</th></tr></thead><tbody>{currentMajor?.sub_periods.map((row, index) => <tr key={row.start} aria-selected={index === minorIndex}><td><button className={color(row.planet)} onClick={() => { setMinorIndex(index); setAsOf(row.start.slice(0, 19)); }}>{row.planet}</button></td><td>{periodDate(row.start)}</td><td>{periodDate(row.end)}</td></tr>)}</tbody></table></div></div></div>
      {currentMinor && <div className="lp-reading"><h3><span className={color(currentMajor.planet)}>{currentMajor.planet}</span> / <span className={color(currentMinor.planet)}>{currentMinor.planet}</span></h3><Badge tone={currentMinor.reading.tone}>{currentMinor.reading.tone === 'good' ? 'Supportive tendency' : currentMinor.reading.tone === 'bad' ? 'Challenging tendency' : 'Mixed / conditional'}</Badge><p>{currentMinor.reading.result}</p><p>Relationship: {currentMinor.reading.relationship.join(', ') || (currentMajor.planet === currentMinor.planet ? 'Same lord' : 'No direct conjunction, mutual aspect or exchange')}</p><ul>{currentMinor.reading.notes.map(note => <li key={note}>{note}</li>)}</ul><details><summary>Period rules & calculations</summary>{rules(currentMinor.reading.rules)}</details></div>}
      {rules([3, 18, 19, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40])}
    </section>}
    {view === 'Maraka rules' && <section className="astro-panel"><PanelTitle emoji="◇">Maraka roles & conditions</PanelTitle><p className="hint">Maraka role is shown separately from favorable ownership and strength.</p><table><thead><tr><th>Planet</th><th>Calculation</th></tr></thead><tbody>{report.maraka_candidates.map(row => <tr key={row.planet}><td className={color(row.planet)}>{row.planet}</td><td>{row.reasons.join(' · ')}</td></tr>)}</tbody></table>{rules([23, 24, 25, 26, 27, 28, 39])}</section>}
    {view === 'All rules' && <><div className="lp-catalogue-heading"><PanelTitle emoji="📖">All 42 topics · rules & calculations</PanelTitle><span className="quiet-label">Four parts</span></div><div className="lp-rule-groups">{['Foundations', 'Raja Yoga', 'Maraka', 'Dasha'].map(group => <section key={group} className="astro-panel"><h3>{group}</h3>{report.rules.filter(rule => rule.group === group).map(rule => <RuleDetail key={rule.number} rule={rule} />)}</section>)}</div></>}
    </section><details className="lp-conventions"><summary>Calculation conventions</summary><ul>{report.conventions.map(note => <li key={note}>{note}</li>)}</ul></details>
  </div>;
}

