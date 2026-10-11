import { useEffect, useRef, useState } from 'react';
import type { Bootstrap } from './types';
import type { JaiminiPeriod, JaiminiSystem } from './jaiminiTypes';
import { PredictionBadge } from './JaiminiPredictionBadge';

const levels = ['Mahadasha', 'Antardasha', 'Pratyantardasha', 'Sookshma', 'Prana'];
const stamp = (value: string) => Date.parse(`${value}Z`);
const activeIndex = (rows: JaiminiPeriod[], date: string) => Math.max(0, rows.findIndex(row => stamp(row.start) <= stamp(date) && stamp(date) < stamp(row.end)));
export function civilNow(offset: number) { return new Date(Date.now() + offset * 3600000).toISOString().slice(0, 19); }
function numericDate(value: string) { return `${value.slice(8, 10)}/${value.slice(5, 7)}/${value.slice(2, 4)}`; }
export function exactDate(value: string) { return `${value.slice(8, 10)}/${value.slice(5, 7)}/${value.slice(0, 4)} ${value.slice(11, 19)}`; }
interface Column { periods: JaiminiPeriod[]; selected: number }

export function JaiminiDasha({ systems, birth, compact = false, book = false }: { systems: JaiminiSystem[]; birth: Bootstrap['birth_data']; compact?: boolean; book?: boolean }) {
  const [code, setCode] = useState('chara');
  const [date, setDate] = useState(() => civilNow(birth?.utc_offset_hours ?? 0));
  const [depth, setDepth] = useState(3);
  const [choices, setChoices] = useState<number[]>([]);
  const [columns, setColumns] = useState<Column[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const cache = useRef(new Map<string, JaiminiPeriod[]>());
  const system = systems.find(s => s.code === code) ?? systems[0];
  const visibleLevels = Math.min(compact ? 3 : depth, system.max_levels);
  const pathKey = choices.join(',');

  useEffect(() => {
    const controller = new AbortController();
    let live = true;
    async function load() {
      setLoading(true); setError('');
      let rows = system.periods;
      const next: Column[] = [];
      const path: number[] = [];
      try {
        for (let level = 0; level < visibleLevels && rows.length; level++) {
          const desired = choices[level];
          const selected = desired !== undefined && desired >= 0 && desired < rows.length ? desired : activeIndex(rows, date);
          next.push({ periods: rows, selected }); path.push(selected);
          if (live) setColumns([...next]);
          if (level + 1 === visibleLevels) break;
          const key = `${system.code}/${path.join('/')}`;
          const stored = cache.current.get(key);
          if (stored) { rows = stored; continue; }
          const response = await fetch(book ? '/api/jaimini2/subperiods' : '/api/jaimini/subperiods', { method: 'POST', signal: controller.signal,
            headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ birth_data: birth, system: system.code, path }) });
          if (!response.ok) throw new Error('The subdivision could not be calculated. Please try again.');
          const data = await response.json() as { periods: JaiminiPeriod[] };
          rows = data.periods;
          if (live) cache.current.set(key, rows);
        }
        if (live) setColumns(next);
      } catch (reason) {
        if (live && !controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Unable to load dasha periods.');
      } finally { if (live) setLoading(false); }
    }
    void load();
    return () => { live = false; controller.abort(); };
  // pathKey represents choices without restarting for every array identity.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [system, visibleLevels, pathKey, date, birth, book]);

  const last = columns.at(-1);
  const selected = last?.periods[last.selected];
  const outside = !system.periods.some(row => stamp(row.start) <= stamp(date) && stamp(date) < stamp(row.end));
  return <section className={`astro-panel jaimini-dasha ${compact ? 'is-compact' : ''}`} aria-label={`${book ? 'Jaimini South' : 'Jaimini North'} dasha explorer`}>
    <div className="jaimini-panel-heading"><h2>⏳ {compact ? 'Explore your Chara Dasha' : book ? 'Jaimini South · 38 dasha methods' : 'Jaimini North dashas'}</h2>
      {!compact && <label>Method<select aria-label={`${book ? 'Jaimini South' : 'Jaimini North'} dasha method`} value={code} onChange={event => { setCode(event.target.value); setChoices([]); setColumns([]); }}>
        {systems.map(s => <option key={s.code} value={s.code}>{s.book_number ? `${s.book_number}. ` : ''}{s.name}{book && !s.periods.length ? ' · worksheet' : ''}</option>)}
      </select></label>}
    </div>
    <div className="jaimini-dasha-controls">
      <label>View at birth-place time<input type="datetime-local" step="1" value={date} aria-label="Jaimini dasha date and time" onChange={event => { if (event.target.value) { setDate(event.target.value.length === 16 ? `${event.target.value}:00` : event.target.value); setChoices([]); } }} /></label>
      <button type="button" className="secondary-button" onClick={() => { setDate(civilNow(birth?.utc_offset_hours ?? 0)); setChoices([]); }}>Today</button>
      {!compact && system.max_levels > 1 && <label>Levels<select aria-label="Jaimini dasha levels" value={Math.min(depth, system.max_levels)} onChange={event => setDepth(Number(event.target.value))}>
        {Array.from({ length: system.max_levels }, (_, i) => <option key={i} value={i + 1}>{i + 1} {levels[i]}</option>)}
      </select></label>}
      <span className="jaimini-quiet" role="status">{loading ? 'Calculating…' : `${system.periods.length} major periods`}</span>
    </div>
    {system.unavailable && <p className="hint">{system.unavailable}</p>}
    {book && system.max_levels > 1 && <p className="jaimini-quiet">Antardasha &amp; Pratyantardasha: 12 equal divisions at each level. Subdivision order uses the declared explorer convention; see Rules &amp; calculations.</p>}
    {book && <p className="jaimini-quiet">Reading chart: {system.basis}. {systems.filter(s => s.periods.length).length} of 38 methods have dated major periods for these inputs. The remaining entries explain the missing rule or applicability condition.</p>}
    {!!system.worksheet?.length && <details className="jaimini-rules"><summary>Calculated worksheet</summary><div className="table-scroll"><table><thead><tr><th>Factor</th><th>Calculation result</th></tr></thead><tbody>{system.worksheet.map(row => <tr key={row.factor}><th>{row.factor}</th><td>{row.value}</td></tr>)}</tbody></table></div></details>}
    {error && <p role="alert" className="app-alert">{error}</p>}
    {!!system.periods.length && <>
      {outside && <p className="jaimini-quiet">The chosen time is outside this method’s calculated cycle. Select a period below to explore it.</p>}
      <div className="jaimini-dasha-columns" style={{ '--jaimini-levels': visibleLevels } as React.CSSProperties} aria-busy={loading}>
        {Array.from({ length: visibleLevels }, (_, level) => <div key={`${system.code}-${level}`} className="jaimini-dasha-column">
          <h3>{levels[level]}</h3><div className="jaimini-dasha-table" tabIndex={0} role="region" aria-label={`${system.name} ${levels[level]} periods`}>
            <table><thead><tr><th scope="col">Sign</th><th scope="col">Start</th><th scope="col">End</th></tr></thead>
              <tbody>{columns[level]?.periods.map((row, index) => <tr key={`${row.start}-${row.sign}`} className={columns[level].selected === index ? 'is-selected' : ''}>
                <th scope="row"><button type="button" aria-pressed={columns[level].selected === index} title={`${row.sign}: ${exactDate(row.start)} – ${exactDate(row.end)}`}
                  onClick={() => setChoices([...columns.slice(0, level).map(c => c.selected), index])}>{row.sign}<small>{row.cycle > 1 ? 'Cycle 2' : ''}</small>{book && !compact && system.predictions?.[row.sign] && <small><PredictionBadge tone={system.predictions[row.sign].tone} compact /></small>}</button></th>
                <td>{numericDate(row.start)}{level >= 3 && <small>{row.start.slice(11, 19)}</small>}</td><td>{numericDate(row.end)}{level >= 3 && <small>{row.end.slice(11, 19)}</small>}</td>
              </tr>)}</tbody></table>
          </div>
        </div>)}
      </div>
      {visibleLevels > 1 && <p className="jaimini-scroll-hint">Scroll sideways to see all dasha levels on smaller screens.</p>}
      {selected && <div className="jaimini-selected-period"><strong>{columns.map(c => c.periods[c.selected].sign).join(' › ')}</strong>
        <span>Start {exactDate(selected.start)}</span><span>End {exactDate(selected.end)}</span>
        {book && system.predictions?.[selected.sign] && <details className="jaimini2-selected-prediction"><summary>Selected sign prediction · <PredictionBadge tone={system.predictions[selected.sign].tone} compact /></summary>
          <p>{system.predictions[selected.sign].summary}</p><p>{system.predictions[selected.sign].scope}</p>
          {system.predictions[selected.sign].conditions.filter(row => row.present).map(row => <p key={row.code}><strong>{row.topic}:</strong> {row.summary}<br />{row.evidence}</p>)}
        </details>}
        <details><summary>Period calculation</summary><p>{selected.rule} {selected.years.toFixed(8)} years × {system.year_days} days.</p></details>
      </div>}
    </>}
    <details className="jaimini-rules"><summary>Rules &amp; calculations</summary><p>{system.method}</p><p>One year = {system.year_days} days. Dates use your birth-place UTC offset. Boundaries are start-inclusive and end-exclusive.</p>
      {book && system.subdivision_status && <p>{system.subdivision_status}</p>}
      {book && system.subdivision_rule && <p>{system.subdivision_rule}</p>}
      {system.max_levels === 1 && <p>This convention defines the major-period worksheet shown here; subdivisions are not substituted from a different method.</p>}
      <div className="table-scroll"><table><thead><tr><th>Sign</th><th>Years</th><th>Calculation</th></tr></thead><tbody>{system.duration_rows.map((row, i) => <tr key={`${row.sign}-${i}`}><th>{row.sign}</th><td>{row.years.toFixed(6).replace(/0+$/, '').replace(/\.$/, '')}</td><td>{row.rule}</td></tr>)}</tbody></table></div>
    </details>
  </section>;
}
