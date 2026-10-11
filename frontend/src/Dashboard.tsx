import { useState, type CSSProperties } from 'react';
import { ArrowLeftRight, ArrowRight } from 'lucide-react';
import type { Bootstrap, ChartCell, Lord } from './types';
import { formatDate, formatOffset, formatTime } from './workspace';

export function PanelTitle({ emoji, children }: { emoji: string; children: React.ReactNode }) {
  return <h2 className="panel-title"><span aria-hidden="true" className="heading-emoji">{emoji}</span>{children}</h2>;
}

function degreeLabel(value: number) {
  const degrees = Math.floor(value);
  const minutes = Math.floor((value - degrees) * 60);
  return `${degrees}°${String(minutes).padStart(2, '0')}′`;
}

export function ChartGrid({ cells, code, state, centerTitle, showAscendantDegree = true }: { cells: (ChartCell | null)[][]; code: string; state: Bootstrap; centerTitle?: string; showAscendantDegree?: boolean }) {
  const birth = state.birth_data;
  const slots = Math.max(...cells.flat().filter((cell): cell is ChartCell => cell !== null).map((cell) => cell.planets.length + Number(cell.is_ascendant)));
  return <div className="rasi-grid" aria-label={`${code} South Indian chart`} style={{ '--chart-slots': slots } as CSSProperties}>
    {cells.flat().map((cell, index) => cell ? <div key={cell.sign} className={`rasi-cell ${cell.is_ascendant ? 'is-ascendant' : ''}`}>
      <span className="rasi-sign chart-sign-header has-direction" title={`${cell.sign}, house ${cell.house}`}><span className="chart-sign-name"><span className="chart-sign-full">{cell.sign}</span><span className="chart-sign-short" aria-hidden="true">{cell.sign.slice(0, 3)}</span></span><span className="chart-element-label" aria-label={cell.element_symbol}>{cell.element_symbol}</span><span className="chart-direction-label" title={`Direction: ${cell.direction}`}>{cell.direction}</span><span className="rasi-house chart-house-label">H{cell.house}</span></span>
      <span className="rasi-planets">
        {cell.is_ascendant && <span className="chart-planet-row rasi-asc"><strong>{showAscendantDegree ? 'ASC' : 'LAGNA'}</strong>{showAscendantDegree && birth && state.ascendant && <small className="planet-degree" title="Natal ascendant degree">{degreeLabel(state.ascendant.degree_in_sign)}</small>}</span>}
        {cell.planets.map((planet, i) => <span key={`${planet.code}-${i}`} className={`chart-planet-row ${planet.color_class}`}>
          <span>{planet.code}{planet.retrograde && '(R)'}
            {planet.dignity_suffix && <span className={`dignity-suffix-${planet.dignity_suffix === 'E' ? 'exalted' : 'debilitated'}`}>({planet.dignity_suffix})</span>}
          </span>
          <small className="planet-degree" title="Natal D1 degree">{degreeLabel(planet.natal_degree)}</small>
        </span>)}
      </span>
    </div> : <div key={`blank-${index}`} className="rasi-blank" aria-hidden="true" />)}
    <div className="rasi-center" aria-hidden="true">
      <span className="chart-center-code">{code}</span>
      <strong className="chart-center-title">{centerTitle || (code === 'D1' ? 'Rasi Chakra' : code === 'D9' ? 'Navamsa' : 'Dasamsa')}</strong>
      {birth && <>
        {birth.name && <span className="chart-center-name" title={birth.name}>{birth.name}</span>}
        <dl className="chart-center-details">
          <div><dt>Date</dt><dd>{formatDate(birth.birth_date)}</dd></div>
          <div><dt>Time</dt><dd>{formatTime(birth.birth_time)}</dd></div>
          <div><dt>Lat</dt><dd>{Math.abs(birth.latitude).toFixed(2)}° {birth.latitude < 0 ? 'S' : 'N'}</dd></div>
          <div><dt>Lon</dt><dd>{Math.abs(birth.longitude).toFixed(2)}° {birth.longitude < 0 ? 'W' : 'E'}</dd></div>
        </dl>
        <span className="chart-center-footer">{birth.ayanamsha} · {formatOffset(birth.utc_offset_hours)}</span>
      </>}
    </div>
  </div>;
}

function localTimestamp(value: string) {
  return Date.parse(`${value.replace(/\.\d+$/, '')}Z`);
}

function LordGroup({ title, houses, lords }: { title: string; houses: string; lords: Lord[] }) {
  return <div className="lord-group">
    <h3>{title} <span>(Houses {houses})</span></h3>
    <ul>{lords.map((entry) => <li key={entry.house}>
      <span>House {entry.house} <span className="lord-sign">· {entry.sign}</span></span>
      <strong className={`planet-color-${entry.lord.toLowerCase()}`}>{entry.lord}</strong>
    </li>)}</ul>
  </div>;
}

export function Dashboard({ state, navigate }: { state: Bootstrap; navigate: (id: string) => void }) {
  const [code, setCode] = useState('D1');
  const dasha = state.current_dasha;
  const progress = dasha ? Math.max(0, Math.min(100,
    (localTimestamp(dasha.as_of) - localTimestamp(dasha.start)) /
    (localTimestamp(dasha.end) - localTimestamp(dasha.start)) * 100)) : 0;

  return <div className="dashboard space-y-5">
    <div className="overview-grid">
      <div className="overview-chart-column">
      <section className="astro-panel chart-panel">
        <div className="panel-heading flex flex-wrap items-center justify-between gap-3">
          <PanelTitle emoji="🔮">{code === 'D1' ? 'Rasi Chakra' : code === 'D9' ? 'Navamsa' : 'Dasamsa'} <span className="subtle-code">({code})</span></PanelTitle>
          <div className="chart-switch" role="group" aria-label="Overview chart">
            {['D1', 'D9', 'D10'].map((item) => <button key={item} type="button" aria-pressed={code === item} onClick={() => setCode(item)}>{item}</button>)}
          </div>
        </div>
        {state.grids?.[code] && <ChartGrid cells={state.grids[code]} code={code} state={state} />}
        <p className="chart-legend">(R) Retrograde <span>·</span> (E) Exalted <span>·</span> (D) Debilitated<br />Degrees show natal D1 positions</p>
      </section>

        <section className="astro-panel dasha-card">
          <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="small-panel-title">Current Dasha</h2>
            <button className="text-action" type="button" onClick={() => navigate('dasha')}>Explore <ArrowRight size={14} aria-hidden="true" /></button>
          </div>
          {dasha ? <>
            <p className="dasha-name">{dasha.major}{dasha.minor && <> <span>/</span> {dasha.minor}</>}</p>
            <p className="dasha-asof">Current period · {formatDate(dasha.as_of)}</p>
            <div className="period-track" role="progressbar" aria-label="Current dasha period elapsed" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress)}>
              <div style={{ width: `${progress}%` }} />
            </div>
            <div className="period-dates"><span>{formatDate(dasha.start)}</span><span>{formatDate(dasha.end)}</span></div>
          </> : <p className="hint">No current period falls within this chart's calculated dasha range.</p>}
        </section>

      </div>

    <section className="astro-panel planets-panel">
      <div className="panel-heading flex flex-wrap items-center justify-between gap-3"><PanelTitle emoji="🔮">Planetary Positions</PanelTitle><span className="quiet-label">All 9 grahas</span></div>
      <p className="mobile-table-hint"><ArrowLeftRight size={14} aria-hidden="true" />Scroll sideways to see all 8 columns</p>
      <div className="table-scroll" role="region" aria-label="Planetary positions table" tabIndex={0}>
        <table className="planet-table"><caption className="sr-only">All nine planets with sign, degree, house, nakshatra, pada, dignity and retrograde status.</caption>
          <thead><tr>{['Planet', 'Sign', 'Degree', 'House', 'Nakshatra', 'Pada', 'Dignity', 'Retrograde'].map((heading) => <th key={heading} scope="col">{heading}</th>)}</tr></thead>
          <tbody>{state.planets?.map((planet) => <tr key={planet.planet}>
            <th scope="row"><span className={`planet-dot planet-color-${planet.planet.toLowerCase()}`} aria-hidden="true" />{planet.planet}</th>
            <td>{planet.sign}</td><td className="number-cell">{planet.degree_in_sign.toFixed(2)}°</td><td className="number-cell">{planet.house}</td>
            <td>{planet.nakshatra.name}</td><td className="number-cell">{planet.nakshatra.pada}</td>
            <td><span className={`dignity-badge ${planet.dignity === 'Own Sign' ? 'is-own' : planet.dignity === 'Exalted' ? 'is-exalted' : planet.dignity === 'Debilitated' ? 'is-debilitated' : ''}`}>{planet.dignity}</span></td>
            <td>{planet.retrograde ? <span className="retrograde-badge">Yes</span> : <span className="muted-text">No</span>}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </section>
      <div className="lords-panel">
        <section className="astro-panel lord-card kendra-card" aria-label="Kendra Lords">
          <LordGroup title="Kendra Lords" houses="1, 4, 7" lords={state.kendra_lords ?? []} />
        </section>
        <section className="astro-panel lord-card trikona-card" aria-label="Trikona Lords">
          <LordGroup title="Trikona Lords" houses="1, 5, 9" lords={state.trikona_lords ?? []} />
        </section>
      </div>
    </div>
    <p className="hint dashboard-analysis-links">Saturn afflictions and transit timelines are in <button type="button" onClick={() => navigate('shani')}>Shani</button>. Kalasarpa, Kuja, Guru Chandala, and Punarphoo are in <button type="button" onClick={() => navigate('dosha')}>Doshas</button>.</p>
  </div>;
}
