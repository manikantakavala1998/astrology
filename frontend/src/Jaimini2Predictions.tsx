import { useState } from 'react';
import type { Bootstrap } from './types';
import type { Jaimini2PredictionModule, Jaimini2Report, PredictionCondition, PredictionTone } from './jaiminiTypes';
import { Panel, Planet, Planets, Rules, Table } from './Jaimini';
import { civilNow, exactDate } from './JaiminiDasha';
import { PredictionBadge, predictionLabels } from './JaiminiPredictionBadge';

function Conditions({ rows, all = false }: { rows: PredictionCondition[]; all?: boolean }) {
  const shown = rows.filter(row => all || row.present);
  return <div className="jaimini2-prediction-conditions">{shown.length ? shown.map(row => <article key={row.code} className={row.present ? '' : 'is-absent'}>
    <div><h3>{row.topic}</h3>{row.present ? <PredictionBadge tone={row.tone} compact /> : <span className="jaimini-quiet">Not present</span>}</div>
    {row.present && <p>{row.summary}</p>}<p className="jaimini-evidence">{row.evidence}</p>
    <details className="jaimini-rules"><summary>Rule and calculation</summary><p>{row.rule}</p></details>
  </article>) : <p className="jaimini-quiet">No checked outcome condition matches this chart. Review the chart facts and rules below.</p>}</div>;
}

export function Jaimini2Predictions({ state, report }: { state: Bootstrap; report: Jaimini2Report }) {
  const [topic, setTopic] = useState('overview');
  const [variant, setVariant] = useState(0);
  const [planet, setPlanet] = useState('all');
  const [all, setAll] = useState(false);
  const [method, setMethod] = useState('chara');
  const [date, setDate] = useState(() => civilNow(state.birth_data?.utc_offset_hours ?? 0));
  const [filter, setFilter] = useState('all');
  const modules = report.predictions.modules;
  const module: Jaimini2PredictionModule | undefined = topic === 'upapada' ? report.predictions.upapada_readings[variant] : modules.find(row => row.id === topic);
  const system = report.dasha_systems.find(row => row.code === method)!;
  const period = system.periods.find(row => row.start <= date && date < row.end);
  const reading = period ? system.predictions?.[period.sign] : undefined;
  const periodRows = system.basis === 'D9' ? report.navamsa_aspects : report.aspects;
  const occupants = periodRows.filter(row => row.sign === period?.sign).map(row => row.planet);
  const aspects = periodRows.filter(row => period && row.aspected_signs.includes(period.sign)).map(row => row.planet);
  function open(id: string) { setTopic(id); setPlanet('all'); setAll(false); }
  return <div className="jaimini2-predictions">
    <Panel title="📜 Detailed predictions">
      <p className="jaimini-intro">Choose a topic to see your result, the matching chart conditions and the calculation behind it.</p>
      <nav className="jaimini2-prediction-topics" aria-label="Jaimini South prediction topics">
        {[{ id: 'overview', title: 'Overview' }, ...modules, { id: 'dasha', title: 'Dasha periods' }].map(row => <button type="button" key={row.id} aria-pressed={topic === row.id} onClick={() => open(row.id)}>{row.title}</button>)}
      </nav>
    </Panel>
    {topic === 'overview' && <>
      <Panel title="✨ Your readings at a glance"><div className="jaimini2-reading-grid">{modules.map(row => <article key={row.id}>
        <h3>{row.title}</h3><p className="jaimini-quiet">{row.basis} · {row.anchor}</p><PredictionBadge tone={row.tone} />
        <p>{row.conditions.find(condition => condition.present)?.summary ?? row.summary}</p>
        <button type="button" className="text-action" onClick={() => open(row.id)}>View detailed reading →</button>
      </article>)}</div><button type="button" className="secondary-button jaimini2-dasha-shortcut" onClick={() => open('dasha')}>See which dasha periods are supportive or challenging →</button></Panel>
    </>}
    {module && <Panel key={`${module.id}-${module.title}`} title={`🔮 ${module.title}`}>
      {topic === 'upapada' && <label className="jaimini2-prediction-selector">Upapada convention<select aria-label="Prediction Upapada convention" value={variant} onChange={event => setVariant(Number(event.target.value))}>{report.predictions.upapada_readings.map((row, index) => <option value={index} key={row.title}>{row.title}</option>)}</select></label>}
      <p className="jaimini-quiet">{module.basis} · Reference sign: {module.anchor}</p>
      <div className="jaimini2-prediction-result"><PredictionBadge tone={module.tone} /><p>{module.summary}</p></div>
      <dl className="jaimini2-prediction-facts">{module.facts.map(row => <div key={row.label}><dt>{row.label}</dt><dd>{row.value}</dd></div>)}</dl>
      <div className="jaimini2-prediction-controls">
        {module.groups && <label>Planet<select aria-label="Prediction planet" value={planet} onChange={event => setPlanet(event.target.value)}><option value="all">All qualifying planets</option>{module.groups.map(row => <option key={row.planet}>{row.planet}</option>)}</select></label>}
        <label className="jaimini2-prediction-toggle"><input type="checkbox" checked={all} onChange={event => setAll(event.target.checked)} />Show all tested rules</label>
      </div>
      {module.groups ? <div className="jaimini2-planet-readings">{module.groups.filter(row => planet === 'all' || row.planet === planet).map(row => <section key={row.planet}>
        <div className="jaimini2-planet-reading-heading"><h3><Planet name={row.planet} /> <small>{row.sign}</small></h3><PredictionBadge tone={row.tone} compact /></div>
        <Conditions rows={row.conditions} all={all} />
      </section>)}{!module.groups.length && <p className="jaimini-quiet">No planet qualifies for this group in your chart.</p>}</div> : <Conditions rows={module.conditions} all={all} />}
      {module.notes && <p className="jaimini-quiet">{module.notes}</p>}
      <Rules><p>{report.predictions.assessment_rule}</p>{module.calculation && <p>{module.calculation}</p>}
        {module.houses && <Table title={`${module.title} house positions`} headings={['House', 'Sign', 'Planets']} rows={module.houses.map(row => [`H${row.house}`, row.sign, row.occupants])} />}
        {module.padas && <><p>Each pada shows its house topic and calculated connections. The wealth assessment above uses AL-specific rules.</p><Table title="All arudha reading connections" headings={['Pada / topic', 'Sign', 'Occupants', 'Aspecting planets', 'Calculation']} rows={module.padas.map(row => [`${row.code} · ${row.name}`, row.sign, row.occupants, row.aspecting, row.calculation])} /></>}
      </Rules>
    </Panel>}
    {topic === 'dasha' && <>
      <Panel title="⏳ Dasha predictions · Good and difficult indications">
        <div className="jaimini2-prediction-controls"><label>Method<select aria-label="Jaimini South prediction method" value={method} onChange={event => { setMethod(event.target.value); setFilter('all'); }}>{report.dasha_systems.map(row => <option key={row.code} value={row.code}>{row.name}</option>)}</select></label>
          <label>Choose date and time<input type="datetime-local" step="1" aria-label="Jaimini South prediction date" value={date} onChange={event => { if (event.target.value) setDate(event.target.value.length === 16 ? `${event.target.value}:00` : event.target.value); }} /></label>
        </div>
        {system.unavailable ? <p className="hint">{system.unavailable}</p> : period && reading ? <>
          <h3>{period.sign} period · {system.basis} reading</h3><p className="jaimini-quiet">{exactDate(period.start)} – {exactDate(period.end)}</p>
          <div className="jaimini2-prediction-result"><PredictionBadge tone={reading.tone} /><p>{reading.summary}</p></div>
          <Conditions rows={reading.conditions} />
          <p className="jaimini-quiet">{reading.scope}</p>
          <details className="jaimini-rules"><summary>Prediction conditions checked</summary><Table title="Book dasha prediction conditions" headings={['Condition', 'Present', 'Your calculation', 'Rule']} rows={reading.conditions.map(row => [row.topic, row.present ? 'Yes' : 'No', row.evidence, row.rule])} /></details>
          <Rules><p>{report.predictions.assessment_rule}</p><p>{system.method}</p><p>{period.rule} Dates use {system.year_days}-day calculation years and your birth-place UTC offset.</p>
            <Table title="Jaimini South dasha activation" headings={['Factor', 'Calculation result']} rows={[
              [`Planets occupying ${period.sign} in ${system.basis}`, <Planets names={occupants} />], [`Planets sign-aspecting ${period.sign} in ${system.basis}`, <Planets names={aspects} />],
              ['Connected karakas', report.schemes['7'].karakas.filter(row => occupants.includes(row.planet) || aspects.includes(row.planet)).map(row => `${row.name} — ${row.planet} (${row.meaning})`).join('; ') || 'None'],
              ...(system.basis === 'D1' ? [['Padas in period sign', report.padas.filter(row => row.sign === period.sign).map(row => `${row.code} — ${row.name}`).join('; ') || 'None']] : []),
            ]} />
          </Rules>
        </> : <p className="hint">This date is outside the calculated cycle. Select a period below.</p>}
      </Panel>
      {!!system.periods.length && <Panel title="📅 Compare all major periods">
        <div className="jaimini2-prediction-topics" role="group" aria-label="Filter dasha indications">{(['all', 'supportive', 'challenging', 'mixed', 'neutral'] as const).map(tone => <button type="button" key={tone} aria-pressed={filter === tone} onClick={() => setFilter(tone)}>{tone === 'all' ? 'All periods' : predictionLabels[tone as PredictionTone]}</button>)}</div>
        <Table title="Jaimini South dasha prediction comparison" headings={['Sign', 'Start', 'End', 'Indication', 'Why']} rows={system.periods.filter(row => filter === 'all' || system.predictions?.[row.sign]?.tone === filter).map(row => {
          const prediction = system.predictions?.[row.sign];
          return [<button type="button" className="text-action" aria-label={`Read ${row.sign} period`} onClick={() => setDate(row.start.slice(0, 19))}>{row.sign}</button>, exactDate(row.start), exactDate(row.end), <PredictionBadge tone={prediction?.tone ?? 'neutral'} compact />, prediction?.conditions.filter(condition => condition.present).map(condition => condition.topic).join('; ') || 'No verified directional rule'];
        })} />
        <p className="jaimini-quiet">Indications summarize matching natal rules. Subperiod dates follow the explorer’s declared convention; they do not establish a certain event.</p>
      </Panel>}
    </>}
  </div>;
}
