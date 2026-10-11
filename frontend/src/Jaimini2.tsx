import { useRef, useState, type KeyboardEvent } from 'react';
import type { Bootstrap } from './types';
import type { Jaimini2Report } from './jaiminiTypes';
import { ChartGrid } from './Dashboard';
import { Planet, Planets, degrees, Rules, Table, Panel, Karakas, Readings, chartCells } from './Jaimini';
import { JaiminiDasha } from './JaiminiDasha';
import { Jaimini2Strength } from './Jaimini2Strength';
import { Jaimini2Yogas } from './Jaimini2Yogas';
import { Jaimini2Predictions } from './Jaimini2Predictions';

const signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];
const tabs = [['charts', '🔮', 'Charts & Karakas'], ['argala', '🔗', 'Argala'], ['yogas', '🌟', 'Yogada & Kevala'], ['strength', '📊', 'Sign Strength'], ['dashas', '⏳', 'Dashas'], ['ayurdaya', '💜', 'Ayurdaya'], ['predictions', '📜', 'Predictions'], ['aspects', '🔭', 'Rashi Aspects'], ['padas', '✨', 'Arudha Padas'], ['upapada', '💜', 'Upapada'], ['advanced', '⚙️', 'Advanced']];

export function Jaimini2({ state, report, active }: { state: Bootstrap; report: Jaimini2Report; active: boolean }) {
  const [view, setView] = useState('charts');
  const [chart, setChart] = useState('D1');
  const [workspaceDetail, setWorkspaceDetail] = useState(false);
  const [target, setTarget] = useState(state.ascendant?.sign ?? 'Aries');
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const scheme = report.schemes['7'];
  const advanced = scheme.advanced;
  const up = report.upapada;
  const source = chart === 'D9' || chart === 'Swamsha' ? 'D9' : chart === 'D3' ? 'D3' : 'D1';
  const derived = chart === 'Swamsha' || chart === 'Karakamsha';
  const cells = state.grids?.[source];
  function move(event: KeyboardEvent<HTMLButtonElement>, i: number) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (i + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    setView(tabs[next][0]); refs.current[next]?.focus();
  }
  if (!active) return null;
  const chartPanel = <Panel title="🔮 Your Jaimini South chart">
    <div className="chart-switch jaimini-chart-switch" role="group" aria-label="Jaimini South chart">{['D1', 'D3', 'D9', 'Karakamsha', 'Swamsha'].map(c => <button type="button" key={c} aria-pressed={chart === c} onClick={() => setChart(c)}>{c}</button>)}</div>
    {cells && <ChartGrid cells={derived ? chartCells(cells, scheme.karakamsha) : cells} code={derived ? chart : source} centerTitle={derived ? scheme.karakamsha : undefined} state={state} showAscendantDegree={!derived} />}
    <p className="chart-legend">{derived ? `Houses start from ${scheme.karakamsha}, the Atmakaraka’s D9 sign.` : '(R) Retrograde · (E) Exalted · (D) Debilitated'}<br />Degrees show natal D1 positions.</p>
    <Rules>{report.rules.karakamsha}</Rules>
  </Panel>;
  return <div className="jaimini-workspace jaimini2-workspace">
    <div className="jaimini2-author"><span>🪐 {report.author}</span><span>Seven karakas · book conventions</span></div>
    {report.warnings.map(w => <p role="status" className="app-alert" key={w}>{w}</p>)}
    <div className="jaimini-toolbar"><div role="tablist" className="jaimini-tabs" aria-label="Jaimini South sections">{tabs.map(([id, emoji, label], i) => <button type="button" role="tab" key={id} id={`jaimini2-tab-${id}`} aria-controls={`jaimini2-view-${id}`} aria-selected={view === id} tabIndex={view === id ? 0 : -1} ref={node => { refs.current[i] = node; }} onKeyDown={e => move(e, i)} onClick={() => setView(id)}><span aria-hidden="true">{emoji}</span>{label}</button>)}</div></div>
    <div role="tabpanel" id={`jaimini2-view-${view}`} aria-labelledby={`jaimini2-tab-${view}`}>
      {view === 'charts' && <div className="jaimini-overview-grid">{chartPanel}{workspaceDetail ? <div><button type="button" className="text-action jaimini2-back" onClick={() => setWorkspaceDetail(false)}>← Calculation workspace</button><Karakas scheme={scheme} rule={report.rules.karakas} /></div> : <Panel title="📜 Calculation workspace"><Table title="Jaimini South calculation workspace" headings={['Calculation', 'Uses', 'Open']} rows={[
        ['Chara karakas', 'Unrounded planet longitudes', <button type="button" className="text-action" aria-label="Open Chara karakas" onClick={() => setWorkspaceDetail(true)}>→</button>],
        ['Argala', 'Planets, obstructions & degree checks', <button type="button" className="text-action" aria-label="Open Argala" onClick={() => setView('argala')}>→</button>],
        ['Yogada & Kevala', 'D1, D3 and D9 sign aspects', <button type="button" className="text-action" aria-label="Open Yogada & Kevala" onClick={() => setView('yogas')}>→</button>],
        ['Sign strength', 'Occupants, degrees & sign type', <button type="button" className="text-action" aria-label="Open Sign Strength" onClick={() => setView('strength')}>→</button>],
        ['Karakamsha', 'Atmakaraka in D9', <button type="button" className="text-action" aria-label="Open Karakamsha chart" onClick={() => setChart('Karakamsha')}>→</button>],
        ['Ayurdaya', 'Three pairs & Dwaya Hora Lagna', <button type="button" className="text-action" aria-label="Open Ayurdaya" onClick={() => setView('ayurdaya')}>→</button>],
      ]} /><div className="jaimini2-calculation-steps"><h3>📖 How the result is calculated</h3><ol><li><span>1</span>Read your birth chart</li><li><span>2</span>Apply the selected rule</li><li><span>3</span>Show the arithmetic</li></ol></div></Panel>}</div>}
      {view === 'charts' && <div className="jaimini-bottom-grid"><JaiminiDasha systems={report.dasha_systems} birth={state.birth_data} compact book /><Panel title="📜 Your chart, explained"><Readings scheme={scheme} short /><button type="button" className="text-action" onClick={() => setView('predictions')}>Read your predictions →</button></Panel></div>}
      {view === 'aspects' && <Panel title="🔭 Rashi Drishti · Sign aspects"><Table title="Jaimini South sign aspects" headings={['Planet', 'Occupied sign', 'Aspected planets', 'Aspected signs']} rows={report.aspects.map(p => [<><Planet name={p.planet} />{p.retrograde && ' (R)'}</>, p.sign, p.aspected_planets.length ? p.aspected_planets.map(q => <span className="jaimini-aspect-link" key={q.planet}><Planet name={q.planet} /> ({q.sign})</span>) : '—', p.aspected_signs.join(', ')])} /><Rules>{report.rules.aspects}</Rules></Panel>}
      {view === 'padas' && <Panel title="✨ All 12 Arudha Padas"><Table title="Jaimini South Arudha Padas" headings={['Pada', 'Sign', 'Source sign', 'Lord', 'Lord’s sign', 'Calculation']} rows={report.padas.map(p => [<>{p.code}<small>{p.name}</small></>, p.sign, p.source_sign, <Planet name={p.lord} />, p.lord_sign, p.calculation])} /></Panel>}
      {view === 'upapada' && <>
        <Panel title="💜 Upapada · Relationship worksheet"><p className="jaimini-intro">{up.rule}</p><div className="jaimini-facts"><div><span>Standard Upapada</span><strong>{up.sign}</strong></div><div><span>Lord</span><strong><Planet name={up.lord} /></strong></div><div><span>Second from UL</span><strong>{up.second_sign}</strong></div><div><span>Second-sign lord</span><strong><Planet name={up.second_lord} /></strong></div></div>
          <Table title="Jaimini South Upapada connections" headings={['Factor', 'Your chart']} rows={[
            ['Planets in Upapada', <Planets names={up.occupants} />], ['Planets in second sign', <Planets names={up.second_occupants} />], ['Sign aspects to Upapada', <Planets names={up.aspecting} />], ['Darakaraka', <Planet name={scheme.karakas[6].planet} />], ['Standard UL calculation', report.padas[11].calculation],
          ]} /></Panel>
        <Panel title="🔎 Anuchara & Agrachara · Separate research variants"><p className="jaimini-intro">Both book variants are shown separately. Select the applicable chart convention when interpreting them.</p><Table title="Book Upapada research variants" headings={['Variant', 'Pithru sign', 'Source', 'Lord', 'Upapada', 'Calculation']} rows={report.upapada_variants.map(r => [r.name, r.pithru, r.source, <Planet name={r.lord} />, r.sign, r.calculation])} /></Panel>
      </>}
      {view === 'argala' && <Panel title="🔗 Argala & Virodhargala"><div className="jaimini-panel-heading"><p className="jaimini-intro">Intervention, obstruction and the book’s degree checks.</p><label>Target sign<select aria-label="Jaimini South Argala target" value={target} onChange={e => setTarget(e.target.value)}>{signs.map(s => <option key={s}>{s}</option>)}</select></label></div>
        <Table title={`Book Argala on ${target}`} headings={['Intervention', 'Planets', 'Obstruction', 'Planets', 'Result', 'Calculation']} rows={report.argala.filter(r => r.target === target).map(r => [<>{r.argala_sign}<small>Position {r.argala_house}{r.reverse && ' · reverse'}</small></>, <Planets names={r.argala_planets} />, <>{r.blocking_sign}<small>{r.blocking_house ? `Position ${r.blocking_house}` : 'No paired obstruction'}</small></>, <Planets names={r.blocking_planets} />, r.status, r.calculation])} /><Rules>{report.rules.argala}</Rules></Panel>}
      {view === 'dashas' && <JaiminiDasha systems={report.dasha_systems} birth={state.birth_data} book />}
      {view === 'yogas' && <Jaimini2Yogas report={report} />}
      {view === 'strength' && <Jaimini2Strength report={report} />}
      {view === 'predictions' && <Jaimini2Predictions state={state} report={report} />}
      {view === 'ayurdaya' && <>
        <Panel title="💜 Ayurdaya · Three-pair calculation"><Table title="Book Ayurdaya categories" headings={['Pair', 'First sign', 'Second sign', 'Types', 'Category']} rows={advanced.longevity_pairs.map(p => [p.pair, p.first, p.second, `${p.first_type} / ${p.second_type}`, p.category])} /><p className="jaimini-quiet">Traditional category: <strong>{advanced.traditional_category}</strong>. This worksheet does not calculate a lifespan or death date.</p><Rules>{advanced.category_rule}</Rules></Panel>
        <Panel title="⚙️ Parivritti Dwaya Hora Lagna"><Table title="Book Hora Lagna" headings={['Lagna', 'Sign', 'Progress', 'Calculation']} rows={report.lagnas.map(l => [l.name, l.sign, degrees(l.degree), l.calculation])} /></Panel>
      </>}
      {view === 'advanced' && <>
        <div className="jaimini-advanced-grid"><Panel title="🪐 Sthira Karakas"><Table title="Book fixed significators" headings={['Topic', 'Planet']} rows={advanced.sthira_karakas.map(k => [k.meaning, <Planet name={k.planet} />])} /></Panel><Panel title="⚖️ Brahma, Rudra & Maheshwara"><Table title="Book advanced significators" headings={['Significator', 'Result', 'Rule']} rows={[
          ['Brahma · preceding odd-sign variant', advanced.brahma ? <Planet name={advanced.brahma} /> : 'No candidate', advanced.brahma_rule], ['Rudra · seventh/eighth-lord variant', <Planet name={advanced.rudra} />, advanced.rudra_rule], ['Maheshwara · sixth/eighth/twelfth variant', <Planet name={advanced.maheswara} />, advanced.maheswara_rule], ['Trishoola', advanced.trishoola.join(', '), 'Rudra’s occupied sign and two trines.'],
        ]} /><Rules><p>Brahma seed: {advanced.brahma_seed}.</p><Table title="Book Brahma candidates" headings={['Planet', 'Sign', 'Eligible']} rows={advanced.brahma_candidates.map(p => [<Planet name={p.planet} />, p.sign, p.eligible ? 'Yes' : 'No'])} /></Rules></Panel></div>
      </>}
    </div>
  </div>;
}
