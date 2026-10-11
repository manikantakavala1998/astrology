import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Clock3, RotateCcw } from 'lucide-react';
import { ChartGrid, PanelTitle } from './Dashboard';
import type { Bootstrap, VimshottariPeriod } from './types';
import { civilTime, nowAtOffset } from './brihatPeriods';
import { formatDate, formatOffset } from './workspace';

const LEVELS = ['Mahadasha', 'Antardasha', 'Pratyantardasha', 'Sookshma', 'Prana'];
const LEVEL_HINTS = ['Main period', 'Bhukti · subperiod', 'Antara · smaller period', 'Fine period', 'Finest period'];
const PLANET_YEARS: Record<string, number> = { Ketu: 7, Venus: 20, Sun: 6, Moon: 10, Mars: 7, Rahu: 18, Jupiter: 16, Saturn: 19, Mercury: 17 };
const DAY_MS = 86400000;
const periodKey = (period: VimshottariPeriod) => `${period.planet}|${period.start}|${period.end}`;
const includes = (period: VimshottariPeriod, date: number) => civilTime(period.start) <= date && date < civilTime(period.end);
const exactStamp = (value: string) => `${formatDate(value.slice(0, 10))} · ${value.slice(11, 19)}`;
const stamp = (value: string, showTime: boolean) => <time dateTime={value} title={exactStamp(value)}>
  <span>{`${value.slice(8, 10)}/${value.slice(5, 7)}/${value.slice(0, 4)}`}</span>
  {showTime && <small>{value.slice(11, 19)}</small>}
</time>;
function durationText(period: VimshottariPeriod) {
  const days = (civilTime(period.end) - civilTime(period.start)) / DAY_MS;
  const [value, unit]: [number, string] = days >= 365.2425 ? [days / 365.2425, 'years'] : days >= 1 ? [days, 'days']
    : days * 24 >= 1 ? [days * 24, 'hours'] : days * 1440 >= 1 ? [days * 1440, 'minutes'] : [days * 86400, 'seconds'];
  return `${value.toFixed(2)} ${unit}`;
}

export function VimshottariDasha({ state, active, requestedDate }: { state: Bootstrap; active: boolean; requestedDate?: {value: string; sequence: number} | null }) {
  const standardPeriods = state.vimshottari?.periods ?? [];
  const periods = requestedDate && !standardPeriods.some(p => includes(p, civilTime(requestedDate.value)))
    ? state.bhrigu?.vimshottari.periods ?? standardPeriods : standardPeriods;
  const offset = state.birth_data?.utc_offset_hours ?? 0;
  const [date, setDate] = useState(() => state.current_dasha?.as_of.slice(0, 19) ?? nowAtOffset(offset));
  const [choices, setChoices] = useState<string[]>([]);
  const [branches, setBranches] = useState<Record<string, VimshottariPeriod[]>>({});
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [detailLevel, setDetailLevel] = useState(4);
  const asOf = civilTime(date);
  useEffect(() => {
    if (!requestedDate || !active) return;
    setDate(requestedDate.value); setChoices([]); setDetailLevel(4);
  }, [requestedDate, active]);

  const plan = useMemo(() => {
    const columns: { rows: VimshottariPeriod[]; selected: VimshottariPeriod }[] = [];
    let rows = periods;
    let missing: VimshottariPeriod | null = null;
    for (let level = 0; level < LEVELS.length && rows.length; level++) {
      const selected = rows.find(period => periodKey(period) === choices[level]) ?? rows.find(period => includes(period, asOf)) ?? rows[0];
      columns.push({ rows, selected });
      if (level === LEVELS.length - 1) break;
      const children = selected.sub_periods.length ? selected.sub_periods : branches[periodKey(selected)];
      if (!children) { missing = selected; break; }
      rows = children;
    }
    return { columns, missing };
  }, [periods, choices, branches, asOf]);
  const missingKey = plan.missing ? periodKey(plan.missing) : '';

  useEffect(() => {
    if (!active || !plan.missing) return;
    const parent = plan.missing;
    const key = periodKey(parent);
    const controller = new AbortController();
    setLoading(key);
    setError('');
    (async () => {
      try {
        const response = await fetch('/api/vimshottari/subperiods', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
          body: JSON.stringify({ planet: parent.planet, start: parent.start, end: parent.end }),
        });
        if (!response.ok) throw new Error('The next dasha level could not be calculated. Please retry.');
        const data = await response.json() as { periods: VimshottariPeriod[] };
        if (!controller.signal.aborted) setBranches(previous => ({ ...previous, [key]: data.periods }));
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Could not load this branch.');
      } finally {
        if (!controller.signal.aborted) setLoading(previous => previous === key ? null : previous);
      }
    })();
    return () => controller.abort();
    // The key fully identifies the parent; cached branches need no request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, missingKey, retry]);

  if (!active || !periods.length) return null;
  const moon = state.planets?.find(planet => planet.planet === 'Moon');
  const birth = state.birth_data;
  const birthTime = birth ? civilTime(`${birth.birth_date}T${birth.birth_time}`) : NaN;
  const balance = (civilTime(periods[0].end) - birthTime) / (365.2425 * 86400000);
  const outside = !periods.some(period => includes(period, asOf));
  const shownLevel = Math.min(detailLevel, plan.columns.length - 1);
  const shownPeriod = plan.columns[shownLevel].selected;
  const shownParent = shownLevel > 0 ? plan.columns[shownLevel - 1].selected : null;

  function returnToDate() {
    setChoices([]);
    setDetailLevel(4);
  }

  function select(level: number, period: VimshottariPeriod) {
    setChoices([...plan.columns.slice(0, level).map(column => periodKey(column.selected)), periodKey(period)]);
    setDetailLevel(level);
  }

  return <div className="vimshottari-workspace">
    <div className="vimshottari-overview">
      <section className="astro-panel chart-panel vimshottari-chart">
        <div className="panel-heading"><PanelTitle emoji="🔮">Birth chart <span className="subtle-code">D1</span></PanelTitle></div>
        {state.grids?.D1 && <ChartGrid cells={state.grids.D1} code="D1" state={state} />}
        <p className="chart-legend">(R) Retrograde · (E) Exalted · (D) Debilitated</p>
      </section>
      <section className="astro-panel vimshottari-context">
        <PanelTitle emoji="⏳">Vimshottari dashas</PanelTitle>
        <p className="vimshottari-intro">Select a period to see its smaller dashas and exact times.</p>
        <dl className="vimshottari-birth-facts">
          <div><dt>Moon’s nakshatra</dt><dd>{moon?.nakshatra.name ?? '—'} · Pada {moon?.nakshatra.pada ?? '—'}</dd></div>
          <div><dt>Dasha at birth</dt><dd className={`planet-color-${periods[0].planet.toLowerCase()}`}>{periods[0].planet}</dd></div>
          <div><dt>Balance at birth</dt><dd>{balance.toFixed(4)} years <small>ends {formatDate(periods[0].end.slice(0, 10))}</small></dd></div>
        </dl>
        <div className="vimshottari-date-controls">
          <label htmlFor="vimshottari-date"><Clock3 size={14} aria-hidden="true" />Dasha viewing date &amp; time</label>
          <div><input id="vimshottari-date" type="datetime-local" step="1" value={date} onChange={event => { setDate(event.target.value); returnToDate(); }} /><button type="button" className="text-action" onClick={() => { setDate(nowAtOffset(offset)); returnToDate(); }}><RotateCcw size={13} aria-hidden="true" />Now</button></div>
          <p>All times use the birth location’s {formatOffset(offset)} · 24-hour clock.</p>
        </div>
        <details className="vimshottari-calculation"><summary>How these dates are calculated</summary><p>Birth balance = remaining Moon nakshatra fraction × planet’s years. Smaller period = parent duration × planet’s years ÷ 120. One year = 365.2425 days.</p><p>Ketu 7 · Venus 20 · Sun 6 · Moon 10 · Mars 7 · Rahu 18 · Jupiter 16 · Saturn 19 · Mercury 17 years.</p></details>
      </section>
    </div>
    <section className="astro-panel vimshottari-explorer" aria-label="Five-level dasha explorer">
      <div className="vimshottari-branch-heading"><h2>Explore your dasha sequence</h2><button className="text-action" type="button" onClick={returnToDate}>Return to date’s sequence</button></div>
      <div className="vimshottari-path" aria-label="Selected dasha sequence">{plan.columns.map((column, index) => <span key={index}>{index > 0 && <ArrowRight size={13} aria-hidden="true" />}<strong className={`planet-color-${column.selected.planet.toLowerCase()}`}>{column.selected.planet}</strong></span>)}</div>
      {outside && <p className="vimshottari-notice" role="status">This date falls outside the calculated timeline. You can still browse any listed branch.</p>}
      {error && <div role="alert" className="vimshottari-notice">{error} <button className="text-action" type="button" onClick={() => setRetry(previous => previous + 1)}>Retry</button></div>}
      <div className="vimshottari-columns-scroll" role="region" aria-label="Dasha columns, scroll horizontally for all five levels" tabIndex={0}>
        <div className="vimshottari-columns">
          {LEVELS.map((name, level) => <section className="vimshottari-level" key={name} data-level={level} aria-label={`${name} periods`}>
            <header><h3 title={LEVEL_HINTS[level]}>{name}</h3></header>
            <div className="vimshottari-date-head" aria-hidden="true"><span>Planet</span><span>Start</span><span>End</span></div>
            {plan.columns[level] ? <div className="vimshottari-period-list">{plan.columns[level].rows.map(period => {
              const selected = periodKey(period) === periodKey(plan.columns[level].selected);
              return <button type="button" key={periodKey(period)} className={`vimshottari-period ${selected ? 'is-selected' : ''}`} aria-pressed={selected}
                aria-label={`${name}: ${period.planet}, starts ${exactStamp(period.start)}, ends ${exactStamp(period.end)}`}
                data-planet={period.planet} data-start={period.start} data-end={period.end} onClick={() => select(level, period)}>
                <span className="vimshottari-period-name"><strong className={`planet-color-${period.planet.toLowerCase()}`}>{period.planet}</strong>{includes(period, asOf) && <small title="At viewing date" aria-label="At viewing date">•</small>}</span>
                <span className="vimshottari-period-dates"><span>{stamp(period.start, level >= 3)}</span><span>{stamp(period.end, level >= 3)}</span></span>
              </button>;
            })}</div> : <p className="vimshottari-level-empty" role="status">{loading && level === plan.columns.length ? 'Calculating periods…' : 'Choose the preceding period to view this level.'}</p>}
          </section>)}
        </div>
      </div>
      <div className="vimshottari-selected-details" role="region" aria-label="Selected dasha period details" data-level={shownLevel} data-start={shownPeriod.start} data-end={shownPeriod.end}>
        <h3>{LEVELS[shownLevel]} · <span className={`planet-color-${shownPeriod.planet.toLowerCase()}`}>{shownPeriod.planet}</span></h3>
        <dl>
          <div><dt>Start</dt><dd><time dateTime={shownPeriod.start}>{exactStamp(shownPeriod.start)}</time></dd></div>
          <div><dt>End</dt><dd><time dateTime={shownPeriod.end}>{exactStamp(shownPeriod.end)}</time></dd></div>
          <div><dt>Duration (approx.)</dt><dd>{durationText(shownPeriod)}</dd></div>
        </dl>
        <details className="vimshottari-calculation" key={periodKey(shownPeriod)}><summary>Calculation</summary>
          <p>{shownParent
            ? <>Parent {( (civilTime(shownParent.end) - civilTime(shownParent.start)) / DAY_MS ).toFixed(6)} days × {PLANET_YEARS[shownPeriod.planet]} / 120 ≈ {( (civilTime(shownPeriod.end) - civilTime(shownPeriod.start)) / DAY_MS ).toFixed(6)} days.</>
            : <>{shownPeriod.planet}: {PLANET_YEARS[shownPeriod.planet]} years × 365.2425 days per year.
                {shownPeriod === periods[0] && <> Remaining at birth: {balance.toFixed(6)} years.</>}
              </>}
          </p>
        </details>
      </div>
      <p className="vimshottari-bottom-note">Dates: DD/MM/YYYY · • At viewing date · Exact times use {formatOffset(offset)}. Start included; end belongs to the next period.</p>
    </section>
  </div>;
}
