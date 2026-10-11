import { useEffect, useRef, useState } from 'react';
import { CalendarDays, ChevronLeft, ChevronRight, Clock3 } from 'lucide-react';
import type { Bootstrap } from './types';
import type { BhriguReport, BcpYear, PadmaYear } from './bhriguTypes';
import { BhriguNatalChart } from './BhriguNatalChart';
import { BhriguPredictions } from './BhriguPredictions';
import { Panel, Planet, Planets, Rules, Table } from './Jaimini';
import { civilTime } from './brihatPeriods';
import { formatOffset } from './workspace';
import { dashaLevels, useBhriguTiming } from './useBhriguTiming';
import './bhrigu.css';

type Method = 'bcp' | 'bsp' | 'padma';
const labels = {bcp: 'Bhrigu Chakra', bsp: 'Bhrigu Sarala', padma: 'Padma Chakra'};
const civilNow = (offset: number) => new Date(Date.now() + offset * 3600000).toISOString().slice(0, 19);
export function bhriguStamp(value: string, time = true) {
  const [date, clock] = value.split('T');
  const [year, month, day] = date.split('-');
  return `${day}/${month}/${year}${time && clock ? ` · ${clock.replace(/\.0+$/, '')}` : ''}`;
}
const range = (row: BcpYear | PadmaYear) => 'start' in row ? {start: row.start, end: row.end} : {start: row.start_date, end: row.end_date};
const contains = (start: string, end: string, instant: string) => civilTime(start) <= civilTime(instant) && civilTime(instant) < civilTime(end);

export function BhriguExplorer({method, state, report, active, openDasha}: {
  method: Method; state: Bootstrap; report: BhriguReport; active: boolean; openDasha: (instant: string) => void;
}) {
  const offset = state.birth_data?.utc_offset_hours ?? 0;
  const [instant, setInstant] = useState(() => civilNow(offset));
  const [dateDraft, setDateDraft] = useState(() => civilNow(offset).slice(0, 10).split('-').reverse().join('/'));
  const [timeDraft, setTimeDraft] = useState(() => civilNow(offset).slice(11, 19));
  const calendarInput = useRef<HTMLInputElement>(null);
  const [live, setLive] = useState(true);
  const [inputError, setInputError] = useState('');
  const [variant, setVariant] = useState('original');
  const [aspectScope, setAspectScope] = useState('connections');
  const years = method === 'padma' ? report.padma : report.bcp;
  const selected = years.find(row => {const r = range(row); return contains(r.start, r.end, instant);});
  const interval = selected ? range(selected) : null;
  const timing = useBhriguTiming(report.vimshottari.periods, instant, active && Boolean(selected));
  useEffect(() => {setDateDraft(instant.slice(0, 10).split('-').reverse().join('/')); setTimeDraft(instant.slice(11, 19));}, [instant]);
  useEffect(() => {
    if (!live || !active) return;
    setInstant(civilNow(offset));
    const timer = window.setInterval(() => setInstant(civilNow(offset)), 10000);
    return () => window.clearInterval(timer);
  }, [active, live, offset]);

  function today() {const now = civilNow(offset); setInstant(now); setDateDraft(now.slice(0, 10).split('-').reverse().join('/')); setTimeDraft(now.slice(11, 19)); setLive(true); setInputError('');}
  function selectYear(age: number) {
    const next = years.find(row => row.age === age);
    if (!next) return;
    const r = range(next), now = civilNow(offset);
    const current = contains(r.start, r.end, now);
    const nextInstant = current ? now : r.start;
    setInstant(nextInstant); setDateDraft(nextInstant.slice(0, 10).split('-').reverse().join('/')); setTimeDraft(nextInstant.slice(11, 19)); setLive(current); setInputError('');
  }
  function selectInstant(value: string) {
    const chosen = value.length === 16 ? `${value}:00` : value;
    if (!interval || !contains(interval.start, interval.end, chosen)) {
      setInputError('Choose a date and time inside the selected year.'); return;
    }
    if (chosen === instant) {setInputError(''); return;}
    setInstant(chosen); setLive(false); setInputError('');
  }
  function editDate(value: string) {
    setDateDraft(value); setLive(false);
    const match = value.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    if (!match) return;
    const iso = `${match[3]}-${match[2]}-${match[1]}`;
    const stamp = civilTime(`${iso}T00:00:00`);
    if (!Number.isFinite(stamp) || new Date(stamp).toISOString().slice(0, 10) !== iso) {setInputError('Enter a valid date as DD/MM/YYYY.'); return;}
    selectInstant(`${iso}T${instant.slice(11, 19)}`);
  }
  function editTime(value: string) {
    setTimeDraft(value); setLive(false);
    if (/^([01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$/.test(value)) selectInstant(`${instant.slice(0, 10)}T${value}`);
  }

  if (!active) return null;
  const bcp = selected as BcpYear | undefined;
  const padma = selected as PadmaYear | undefined;
  const annualSign = selected ? (method === 'padma' ? padma!.sign : bcp!.sign_from_lagna) : '';
  const yearLord = selected && method !== 'bsp' ? selected.year_lord : '';
  const occupants = report.planets.filter(p => p.sign === annualSign).map(p => p.planet);
  const ageRules = report.bsp.filter(rule => rule.age === selected?.age);
  const applicable = ageRules.filter(rule => variant === 'original' || rule.special_status);
  const activatedSigns = method === 'bcp' ? [annualSign, bcp?.sign_from_cycle_ruler].filter(Boolean)
    : method === 'padma' ? [annualSign, padma?.year_lord_dwadasamsa_sign].filter(Boolean)
    : applicable.length ? applicable.flatMap(rule => rule.targets.map(t => t.sign)) : report.permanent.map(row => row.sign);
  const pathPlanets = [...new Set(timing.path.map(p => p.planet))];
  const aspectRows = report.aspects.filter(a => aspectScope === 'all' || (aspectScope === 'connections' ? activatedSigns.includes(a.sign) || a.planet === yearLord || (method === 'bcp' && a.planet === bcp?.cycle_ruler)
    : aspectScope === 'lord' ? a.planet === yearLord
    : aspectScope === 'dasha' ? pathPlanets.includes(a.planet) : activatedSigns.includes(a.sign)));
  aspectRows.sort((a, b) => Number(activatedSigns.includes(b.sign)) - Number(activatedSigns.includes(a.sign)));
  const maxInput = interval ? new Date(civilTime(interval.end) - 1000).toISOString().slice(0, 19) : undefined;
  const first = report.vimshottari.periods[0];
  const birthInstant = state.birth_data ? `${state.birth_data.birth_date}T${state.birth_data.birth_time}` : '';
  const balance = (civilTime(first.end) - civilTime(birthInstant)) / (report.dasha_year_days * 86400000);

  return <div className="bhrigu-workspace" data-method={method}>
    <section className="astro-panel bhrigu-controls" aria-label={`${labels[method]} year controls`}>
      <label>Running year<select aria-label="Running year" value={selected?.age ?? ''} onChange={e => selectYear(+e.target.value)}>
        {!selected && <option value="">Outside years 1–120</option>}
        {years.map(row => <option key={row.age} value={row.age}>Year {row.age} · {range(row).start.slice(0, 4)}–{range(row).end.slice(0, 4)}</option>)}
      </select></label>
      <div className="bhrigu-year-buttons"><button type="button" className="secondary-button" aria-label="Previous year" disabled={!selected || selected.age === 1} onClick={() => selectYear(selected!.age - 1)}><ChevronLeft size={16} /></button>
        <button type="button" className="secondary-button" aria-label="Next year" disabled={!selected || selected.age === years.length} onClick={() => selectYear(selected!.age + 1)}><ChevronRight size={16} /></button></div>
      <div className="bhrigu-date-control"><label htmlFor={`${method}-selected-date`}>Date within year</label><span><button type="button" aria-label="Choose date within year" onClick={() => calendarInput.current?.showPicker()}><CalendarDays size={16} aria-hidden="true" /></button><input id={`${method}-selected-date`} aria-label="Date within year" type="text" inputMode="numeric" placeholder="DD/MM/YYYY" value={dateDraft} onChange={e => editDate(e.target.value)} onBlur={() => {if (!/^\d{2}\/\d{2}\/\d{4}$/.test(dateDraft)) setInputError('Enter a valid date as DD/MM/YYYY.');}} /><input ref={calendarInput} className="bhrigu-calendar-input" type="date" aria-hidden="true" tabIndex={-1} min={interval?.start.slice(0, 10)} max={maxInput?.slice(0, 10)} value={instant.slice(0, 10)} onChange={e => selectInstant(`${e.target.value}T${instant.slice(11, 19)}`)} /></span></div>
      <label className="bhrigu-time-control"><span className="sr-only">Time within year</span><span><Clock3 size={16} aria-hidden="true" /><input aria-label="Time within year" type="text" inputMode="numeric" placeholder="HH:mm:ss" value={timeDraft} onChange={e => editTime(e.target.value)} onBlur={() => {if (!/^([01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$/.test(timeDraft)) setInputError('Enter a valid 24-hour time as HH:mm:ss.');}} /></span></label>
      <button type="button" className="primary-button bhrigu-today" onClick={today}>Today</button>
      <span className={`bhrigu-clock-state ${live ? 'is-live' : ''}`}>{live ? '● Active now' : 'Selected time'}</span>
      {interval && <p className="bhrigu-year-range">Year window: {bhriguStamp(interval.start)} <span>–</span> {bhriguStamp(interval.end)} · Birth-place time {formatOffset(offset)}<small>Year selects the window. Date and time select the exact active dashas.{method === 'padma' && ' Padma calendar convention.'}</small></p>}
      {inputError && <p className="bhrigu-input-error" role="alert">{inputError}</p>}
    </section>

    {!selected ? <Panel title="Choose a running year"><p>The current time falls outside the calculated years 1–120. Select a year to explore its method and dasha results.</p></Panel> : <>
      <div className="bhrigu-overview">
        <Panel title="🔮 Your natal chart · D1">
          <BhriguNatalChart state={state} />
        </Panel>
        <div className="bhrigu-summary-column">
          <Panel title={method === 'bsp' ? `✨ BSP rules for year ${selected.age}` : `✨ Activation for year ${selected.age}`}>
            {method !== 'bsp' ? <>
              <div className="bhrigu-year-summary"><div><span>Active house</span><strong>H{selected.house_from_lagna}</strong></div><div><span>Active sign</span><strong>{annualSign}</strong></div>
                <div><span>Year lord</span><strong><Planet name={yearLord} /></strong></div></div>
              <p className="bhrigu-occupants">Planets in {annualSign}: {occupants.length ? <Planets names={occupants} /> : 'None'}</p>
              {method === 'bcp' ? <>
                <Table title="BCP progression comparison" headings={['Reading', 'Sign / house', 'Lord / occupants']} rows={[
                  ['From Lagna', <>{annualSign} · D1 H{bcp!.house_from_lagna}</>, <><Planet name={yearLord} /> · {occupants.length ? <Planets names={occupants} /> : 'No occupants'}</>],
                  ['From cycle ruler', bcp!.sign_from_cycle_ruler ? <>{bcp!.sign_from_cycle_ruler} · H{bcp!.house_from_cycle_ruler} from {bcp!.cycle_ruler}<small>D1 H{bcp!.cycle_d1_house}</small></> : 'Cycle ruler defined through year 108', bcp!.sign_from_cycle_ruler ? <>{bcp!.cycle_sign_lord && <Planet name={bcp!.cycle_sign_lord} />} · {bcp!.planets_from_cycle_ruler.length ? <Planets names={bcp!.planets_from_cycle_ruler} /> : 'No occupants'}</> : '—'],
                ]} />
                {bcp!.cycle_ruler && <p className="bhrigu-cycle-note">Cycle {bcp!.cycle_number} · <Planet name={bcp!.cycle_ruler} /> · Years {(bcp!.cycle_number - 1) * 12 + 1}–{bcp!.cycle_number * 12}. House {bcp!.house_from_cycle_ruler} from {bcp!.cycle_ruler} in {report.planets.find(p => p.planet === bcp!.cycle_ruler)?.sign} = {bcp!.sign_from_cycle_ruler}.</p>}
                <Rules><p>Running year {selected.age}: (({selected.age} − 1) mod 12) + 1 = house {bcp!.house_from_lagna}. Count inclusively from the natal ascendant.</p>
                  <p>Cycle = floor(({selected.age} − 1) / 12) + 1 = {bcp!.cycle_number}. The cycle-ruler order is Moon, Mercury, Venus, Sun, Mars, Jupiter, Saturn, Rahu, Ketu. Treat that ruler’s natal sign as Lagna, count the same year position and read houses and lordships from there. The D1 house label maps that sign back to the natal chart.</p>
                  <p>Year 1 starts at birth. February 29 anniversaries use February 28 in non-leap years. Years 109–120 retain Lagna progression only.</p>
                  <details><summary>Existing BCP research indications</summary><p>{report.longevity.reason}</p><Table title="BCP research years" headings={['House', 'Sign', 'Running years']} rows={report.longevity.flagged_houses.map(h => [<>H{h.house_from_lagna}<small>{h.label}</small></>, h.sign, h.ages.join(', ')])} /><p>These are candidate research years, not a calculation of an event or a death date.</p></details>
                </Rules>
              </> : <>
                <Table title="Padma year-lord calculation" headings={['Step', 'Your calculation']} rows={[
                  ['Annual house', <>H{padma!.house_from_lagna} · {padma!.sign}<small>((year {selected.age} − 1) mod 12) + 1</small></>],
                  ['Lord in D12', <><Planet name={padma!.year_lord} /> → {padma!.year_lord_dwadasamsa_sign}</>],
                  ['Map D12 sign into D1', <>House {padma!.superimposed_house_from_lagna} · {padma!.year_lord_dwadasamsa_sign}<small>{padma!.is_badhaka ? 'Direct Badhaka sign connection' : 'No direct Badhaka sign connection'}</small></>],
                ]} />
                <Rules><p>{report.padma_year_rule}</p><p>The published worked date and this rounded reproduction differ by one day. Keep this convention separate from birthday years and the Vimshottari year length.</p><p>Year lord = ruler of the annual sign. D12 divides each natal sign into twelve 2°30′ parts, starting from that sign. Map the lord’s D12 sign into D1 by sign, never by copying the D12 house number.</p></Rules>
              </>}
            </> : <>
              <div className="bhrigu-variant"><label>Rule interpretation<select aria-label="BSP rule interpretation" value={variant} onChange={e => setVariant(e.target.value)}><option value="original">Original age rules</option><option value="status">Special-status research variant</option></select></label></div>
              <p className="bhrigu-rule-status">{applicable.length ? `${applicable.length} age rule active in running year ${selected.age}` : `No age-timed rule active in running year ${selected.age}.`}</p>
              {ageRules.length > 0 && <Table title="BSP selected year rules" headings={['Rule & planet', 'Target', 'Planets']} rows={ageRules.flatMap(rule => (variant === 'status' && !rule.special_status) ? [[<>BSP-{rule.rule_number} · <Planet name={rule.planet} /></>, 'Research qualifier not met', '—']] : rule.targets.map(t => [<>BSP-{rule.rule_number} · <Planet name={rule.planet} /><small>{t.role}</small></>, <>H{t.house} · {t.sign}<small>{t.offset}th from {rule.planet}</small></>, t.planets.length ? <Planets names={t.planets} /> : 'No planets']))} />}
              <p className="bhrigu-caption">Permanent house indications remain available in every year. BSP has fixed age rules; it does not assign BCP’s annual house.</p>
              <Rules><p>Use running years, not completed age: year 20 begins at the 19th birthday. Target = ((planet’s D1 house − 1 + offset − 1) mod 12) + 1.</p><p>Original age rules are the default. The optional research variant adds a separate special-status gate. Mean-node retrograde motion always satisfies that variant’s retrograde condition.</p>
                <Table title="BSP rule calculations" headings={['Rule', 'Running year', 'Calculation', 'Research qualifier']} rows={report.bsp.map(rule => [<>BSP-{rule.rule_number} · <Planet name={rule.planet} /></>, rule.age, rule.targets.map(t => `${t.role}: ${t.offset}th → H${t.house} ${t.sign}`).join('; '), rule.special_status ? rule.special_status_reasons.join('; ') : 'Not met'])} />
                <p>{report.coverage}</p><p>BSP-11’s occupied-house target is occasional; its seventh-house target is an influence, not another guaranteed activation. Aspects to an empty sign still count.</p>
              </Rules>
            </>}
          </Panel>
        </div>
      </div>
      <Panel title="🔭 Natal aspects & connections">
        <div className="bhrigu-aspect-controls"><label>Show<select aria-label="Aspect scope" value={aspectScope} onChange={e => setAspectScope(e.target.value)}><option value="connections">Year connections</option><option value="activated">{method === 'bsp' && !applicable.length ? 'To permanent houses' : 'To activated signs'}</option>{method !== 'bsp' && <option value="lord">From year lord</option>}<option value="dasha">From active dasha planets</option><option value="all">All Vedic aspects</option></select></label></div>
        <Table title="Bhrigu aspects" headings={['Planet', 'Planet in sign / house', 'Aspect', 'Aspected sign / house', 'Planets reached']} rows={aspectRows.length ? aspectRows.map(a => [<Planet name={a.planet} />, <>{a.source_sign} · H{a.source_house}</>, `${a.offset}${a.offset === 3 ? 'rd' : 'th'}`, <>{a.sign} · H{a.house}</>, a.planets.length ? <Planets names={a.planets} /> : 'None']) : [['—', '—', '—', 'No matching aspect', '—']]} />
        <details className="bhrigu-aspect-rules"><summary>Aspect rules</summary><p>Seventh for the seven classical planets; Mars also 4/8, Jupiter 5/9, Saturn 3/10. Rahu/Ketu can receive aspects; their outgoing aspects are not assigned here. Houses use D1 whole-sign geometry. Year connections include incoming aspects and outgoing aspects from the year/cycle rulers.</p></details>
      </Panel>

      <Panel title="⏳ Vimshottari · Active at selected time">
        <span className="bhrigu-level-badge">5 levels</span>
        <div className="bhrigu-timing-heading"><p>{bhriguStamp(instant)} · Calculated separately as timing context</p></div>
        <div className="bhrigu-dasha-path" aria-label="Active five-level dasha path" aria-busy={timing.pending}>
          {dashaLevels.map((label, i) => {const period = timing.path[i], planet = report.planets.find(p => p.planet === period?.planet); return <div key={label} className={`bhrigu-dasha-step ${period ? 'is-active' : ''}`} data-level={label}>
            <span>{label}</span><strong>{period ? <Planet name={period.planet} /> : timing.error ? 'Unavailable' : 'Calculating…'}</strong><small>{planet ? `${planet.sign} · House ${planet.house}` : '—'}</small></div>;})}
        </div>
        {timing.pending && !timing.error && <p className="bhrigu-caption" role="status">Calculating the selected dasha branch…</p>}
        {timing.error && <p className="bhrigu-input-error" role="alert">{timing.error} <button type="button" className="text-action" onClick={timing.retry}>Retry</button></p>}
        <div className="table-scroll bhrigu-timing-table" tabIndex={0} role="region" aria-label="Active dasha times"><table><caption className="sr-only">Active dasha times</caption><thead><tr>{['Level', 'Planet', 'Natal sign', 'House', 'Starts', 'Ends'].map(h => <th key={h} scope="col">{h}</th>)}</tr></thead>
          <tbody>{timing.path.map((period, i) => {const planet = report.planets.find(p => p.planet === period.planet); return <tr key={`${period.start}-${i}`} className="bhrigu-active-period" aria-current="true"><th scope="row">{dashaLevels[i]}</th><td><Planet name={period.planet} /></td><td>{planet?.sign}</td><td>H{planet?.house}</td><td><time dateTime={period.start} title={bhriguStamp(period.start)}>{bhriguStamp(period.start, false)} {period.start.slice(11, 16)}</time></td><td><time dateTime={period.end} title={bhriguStamp(period.end)}>{bhriguStamp(period.end, false)} {period.end.slice(11, 16)}</time></td></tr>;})}</tbody></table></div>
        <div className="bhrigu-dasha-footer"><Rules label="Dasha rules & calculations"><p>Moon nakshatra at birth: {state.planets?.find(p => p.planet === 'Moon')?.nakshatra.name}. Balance of <Planet name={first.planet} /> at birth = unelapsed nakshatra fraction × {report.dasha_years[first.planet]} years = {balance.toFixed(6)} years.</p>
          <p>Order: Ketu 7 → Venus 20 → Sun 6 → Moon 10 → Mars 7 → Rahu 18 → Jupiter 16 → Saturn 19 → Mercury 17. One cycle totals 120 years; one year = {report.dasha_year_days} days.</p>
          <Table title="Selected dasha arithmetic" headings={['Level', 'Duration calculation']} rows={timing.path.map((p, i) => {
            const days = (civilTime(p.end) - civilTime(p.start)) / 86400000;
            const parent = timing.path[i - 1];
            const parentDays = parent ? (civilTime(parent.end) - civilTime(parent.start)) / 86400000 : 0;
            return [dashaLevels[i], <>{i === 0 ? `${p.planet}: ${report.dasha_years[p.planet]} years × ${report.dasha_year_days} = ${days.toFixed(8)} days` : `${parentDays.toFixed(8)} parent days × ${p.planet} ${report.dasha_years[p.planet]} / 120 = ${days.toFixed(8)} days`}<small>Start {bhriguStamp(p.start)} · End {bhriguStamp(p.end)}</small></>];
          })} />
          <p>Every child starts with its parent lord. Selection uses start ≤ chosen time &lt; end. The first major period began before birth; the unused balance starts your life’s timeline. The sequence repeats as needed to cover all selectable years.</p>
        </Rules><button type="button" className="text-action" onClick={() => openDasha(instant)}>Open full dasha explorer →</button></div>
      </Panel>

      <BhriguPredictions method={method} selected={selected} report={report} rules={applicable} variant={variant} path={timing.path} instant={instant} pending={timing.pending} error={timing.error} />

      {method === 'bsp' && <Panel title="📜 Permanent BSP house indications">
        <Table title="Permanent BSP houses" headings={['Rule', 'House & sign', 'Planets', 'Indication']} rows={report.permanent.map(row => [<>BSP-{row.rule_number}<small>{row.title}</small></>, <>H{row.house_from_lagna} · {row.sign}</>, row.planets_in_house.length ? <Planets names={row.planets_in_house} /> : 'No planets', row.note])} />
        <Rules><p>BSP-1: fourth from Saturn. BSP-2: tenth and sixth from Jupiter. BSP-14: count from Lagna by its sign’s natural zodiac number (Aries 1 through Pisces 12).</p>
          <p>BSP-5: Jupiter and Saturn must share a natal sign. {report.aries ? `Condition met: Aries is D1 H${report.aries.house_from_lagna}.` : 'No Jupiter–Saturn conjunction in this chart; this condition is not met.'}</p>
          <p>BSP-15 qualitative lookup: Venus occupies {report.venus.venus_sign} H{report.venus.venus_house_from_lagna}; conjunctions: <Planets names={report.venus.conjunct_planets} />. Twelfth from Venus: {report.venus.twelfth_from_venus_sign} H{report.venus.twelfth_from_venus_house_from_lagna}. These placements alone do not calculate a definite event or age.</p>
          {Object.entries(report.venus.conjunct_planet_lordships).map(([planet, houses]) => <p key={planet}><Planet name={planet} /> rules D1 houses {houses.join(', ')}.</p>)}
        </Rules>
      </Panel>}
      {method === 'padma' && <Panel title="🌷 Badhaka signs & Badhakesh placements">
        <Table title="Padma direct Badhaka signs" headings={['Chart', 'Ascendant', 'Badhaka sign', 'Lord']} rows={report.badhakas.map(b => [b.chart, <>{b.ascendant_sign}<small>{b.modality} → H{b.badhaka_house_from_lagna} in {b.chart}</small></>, <>{b.badhaka_sign}<small>Mapped to D1 H{b.d1_house}</small></>, <Planet name={b.badhakesh} />])} />
        <Table title="Padma Badhaka connections" headings={['Connection', 'D1 target', 'This year']} rows={report.badhaka_connections.map(c => [<>{c.kind}<small>{c.reason}</small></>, <>H{c.house} · {c.sign}</>, c.sign === annualSign && c.sign === padma!.year_lord_dwadasamsa_sign ? 'Annual sign + year-lord D12 sign' : c.sign === annualSign ? 'Annual sign matches' : c.sign === padma!.year_lord_dwadasamsa_sign ? 'Year-lord D12 sign matches' : 'No match'])} />
        <Rules><p>Movable ascendant → 11th; fixed → 9th; dual → 7th. Compute separately from D1 and D12, then map both signs into D1. Direct Badhaka signs and the Badhakesh’s D1/D12 placements are shown as different connections.</p></Rules>
      </Panel>}
    </>}
  </div>;
}
