import { useRef, useState, type CSSProperties, type KeyboardEvent } from 'react';
import { ChevronDown } from 'lucide-react';
import type { BalaReport, BalaView } from './balaTypes';
import { planetColors as colors } from './planetColors';
const number = (value: number, precision = 2) => value.toLocaleString('en-GB', {
  maximumFractionDigits: precision, minimumFractionDigits: precision,
});

function BalaGraph({ view, selected, select }: { view: BalaView; selected: string; select: (key: string) => void }) {
  const range = view.maximum - view.minimum;
  const zero = (0 - view.minimum) / range * 100;
  const ticks = [view.maximum, (view.maximum + view.minimum) / 2, view.minimum];
  return <figure className="strength-graph" aria-label={`${view.name} vertical graph`} data-minimum={view.minimum} data-maximum={view.maximum}>
    <figcaption><span>{view.unit}</span><span>{view.id === 'shadbala' ? 'Gold marks show required strength' : view.id === 'bhava' ? 'Colors follow house lords' : view.minimum < 0 ? 'Values below zero reduce strength' : 'Select a bar to see its calculation'}</span></figcaption>
    <div className="strength-plot">
      <div className="strength-axis" aria-hidden="true">{ticks.map(tick => <span key={tick}>{number(tick, tick % 1 ? 1 : 0)}</span>)}</div>
      <div className={`strength-columns ${view.rows.length === 12 ? 'strength-houses' : ''}`}>
        <div className="strength-zero" style={{ bottom: `${26 + zero * 1.8}px` }} aria-hidden="true" />
        {view.rows.map(row => {
          const height = Math.abs(row.value) / range * 100;
          const bottom = row.value < 0 ? (row.value - view.minimum) / range * 100 : zero;
          const top = row.value < 0 ? zero : (row.value - view.minimum) / range * 100;
          return <button key={row.key} type="button" className="strength-column" onClick={() => select(row.key)}
            aria-label={`${row.label}: ${number(row.value)} ${view.unit}. Show calculation`} aria-pressed={selected === row.key}
            data-value={row.value} data-planet={row.planet} style={{ '--planet-color': colors[row.planet] } as CSSProperties}>
            <span className="strength-track" aria-hidden="true">
              <span className="strength-bar" style={{ height: `${height}%`, bottom: `${bottom}%` }} />
              {row.required !== undefined && <span className="strength-required" style={{ bottom: `${(row.required - view.minimum) / range * 100}%` }} />}
              <span className="strength-value" style={{ bottom: `calc(${top}% + 7px)` }}>{number(row.value)}</span>
            </span>
            <span className="strength-label">{row.label}</span>
          </button>;
        })}
      </div>
    </div>
  </figure>;
}

export function Balas({ report, active }: { report: BalaReport; active: boolean }) {
  const [viewId, setViewId] = useState('sthana');
  const [planet, setPlanet] = useState('Sun');
  const [house, setHouse] = useState('H1');
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  if (!active) return null;
  const view = report.views.find(item => item.id === viewId) ?? report.views[0];
  const groups = Array.from(new Set(report.views.map(item => item.group)));
  const selectedKey = view.id === 'bhava' ? house : planet;
  const row = view.rows.find(item => item.key === selectedKey) ?? view.rows[0];
  const select = view.id === 'bhava' ? setHouse : setPlanet;
  function keyboard(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const next = event.key === 'ArrowDown' ? (index + 1) % report.views.length
      : event.key === 'ArrowUp' ? (index + report.views.length - 1) % report.views.length
      : event.key === 'Home' ? 0 : event.key === 'End' ? report.views.length - 1 : null;
    if (next === null) return;
    event.preventDefault();
    setViewId(report.views[next].id);
    tabs.current[next]?.focus();
  }
  return <div className="balas-workspace">
    <aside className="bala-navigation astro-panel">
      <label className="bala-mobile-navigation">Strength view
        <select aria-label="Strength view" value={view.id} onChange={event => setViewId(event.target.value)}>
          {groups.map(group => <optgroup label={group} key={group}>{report.views.filter(item => item.group === group).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</optgroup>)}
        </select>
      </label>
      <div className="bala-desktop-navigation" role="tablist" aria-label="Bala strength views" aria-orientation="vertical">
        {groups.map(group => <div className="bala-nav-group" key={group}>
          <p>{group}</p>
          {report.views.filter(item => item.group === group).map(item => {
            const index = report.views.indexOf(item);
            return <button key={item.id} ref={node => { tabs.current[index] = node; }} type="button" role="tab"
              id={`bala-tab-${item.id}`} aria-selected={view.id === item.id} aria-controls="bala-view-content"
              tabIndex={view.id === item.id ? 0 : -1} onClick={() => setViewId(item.id)} onKeyDown={event => keyboard(event, index)}>
              {item.name}<span aria-hidden="true">›</span>
            </button>;
          })}
        </div>)}
      </div>
    </aside>
    <div className="bala-main" role="tabpanel" id="bala-view-content" aria-labelledby={`bala-tab-${view.id}`}>
      <section className="astro-panel bala-detail-panel">
        <div className="bala-heading"><div><p className="bala-eyebrow">{view.group}</p><h2>{view.name}<span> · {view.description}</span></h2></div><span className="bala-unit">{report.conversion}</span></div>
        <BalaGraph view={view} selected={row.key} select={select} />
        <div className="bala-calculation-heading"><div><h3>Calculation breakdown</h3><p>From your birth chart · {row.label}{view.id === 'bhava' ? ` · lord ${row.planet}` : ''}</p></div>
          <label>{view.id === 'bhava' ? 'House' : 'Planet'}<select aria-label={view.id === 'bhava' ? 'House' : 'Planet'} value={row.key} onChange={event => select(event.target.value)}>{view.rows.map(item => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>
        </div>
        <div className="bala-table-scroll"><table className="bala-calculation-table"><thead><tr><th>Component / full name</th><th>Calculation from your inputs</th><th>Result</th></tr></thead><tbody>
          {row.details.map(detail => <tr key={detail.name}><th scope="row">{detail.name}</th><td>{detail.calculation}</td><td>{detail.value === null ? <span className="bala-unavailable">Not calculated</span> : <><strong>{number(detail.value)}</strong><small>{detail.unit}</small></>}</td></tr>)}
        </tbody><tfoot><tr><th scope="row">{view.name} total</th><td>{view.formula}</td><td><strong>{number(row.value)}</strong><small>{view.unit}</small>{view.unit === 'Virupas' && <small>{number(row.value / 60, 3)} Rupas</small>}</td></tr></tfoot></table></div>
        {row.status && <p className="bala-status">{row.status}{row.required !== undefined && ` · Required ${number(row.required)} Rupas · Actual ${number(row.value)} Rupas`}</p>}
        <details className="bala-rules" key={view.id}><summary>Full rules, division contributions &amp; input values<ChevronDown size={16} aria-hidden="true" /></summary>
          <p className="bala-formula">{view.formula}</p>
          {view.notes.map(note => <p key={note} className="bala-method-note">{note}</p>)}
          <dl className="bala-inputs">{row.inputs.map(input => <div key={input.name}><dt>{input.name}</dt><dd>{input.value}</dd></div>)}</dl>
          {row.tables.map(table => <div key={table.title} className="bala-contributions"><h3>{table.title}</h3>{table.rows.length ? <div className="bala-table-scroll"><table><thead><tr>{table.columns.map(column => <th key={column}>{column}</th>)}</tr></thead><tbody>{table.rows.map((values, index) => <tr key={index}>{values.map((value, column) => <td key={column}>{typeof value === 'number' ? number(value, 6) : value}</td>)}</tr>)}</tbody></table></div> : <p>No incoming classical aspects.</p>}</div>)}
        </details>
        <details className="bala-rules"><summary>All {view.id === 'bhava' ? 'house' : 'planet'} results<ChevronDown size={16} aria-hidden="true" /></summary>
          <div className="bala-table-scroll"><table><thead><tr><th>{view.id === 'bhava' ? 'House' : 'Planet'}</th>{view.id === 'bhava' && <th>House lord</th>}<th>{view.unit}</th>{view.unit === 'Virupas' && <th>Rupas</th>}<th>Details</th></tr></thead><tbody>{view.rows.map(item => <tr key={item.key}><th scope="row">{item.label}</th>{view.id === 'bhava' && <td>{item.planet}</td>}<td>{number(item.value, 6)}</td>{view.unit === 'Virupas' && <td>{number(item.value / 60, 6)}</td>}<td>{item.status ?? (view.id === 'bhava' ? 'Compare with the other houses' : view.description)}</td></tr>)}</tbody></table></div>
        </details>
      </section>
      <div className="bala-explain-grid">
        <section className="astro-panel"><h3>How this contributes to Shadbala</h3><p>Sthana + Dig + Kala + Cheshta + Naisargika + Drik</p><p className="bala-formula">Sum in Virupas ÷ 60 = total in Rupas.</p><p>The total view compares each planet with its required strength.</p></section>
        <section className="astro-panel"><h3>Other strength views</h3><p>Vimshopaka: choose 6, 7, 10 or 16 divisions to see every weighted contribution.</p><p>Bhava Bala: house lord + direction + aspect adjustment + occupants.</p><p>Ishta / Kashta Phala: separate normalized results from Uccha and Cheshta.</p></section>
      </div>
    </div>
  </div>;
}
