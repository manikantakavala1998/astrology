import { useEffect, useState } from 'react';
import type { Bootstrap } from './types';
import { formatDate } from './workspace';
import { StrengthGraphs } from './StrengthGraphs';
import { BrihatPredictions, type Predictions } from './BrihatPredictions';
import { BrihatAshtakavarga } from './BrihatAshtakavarga';
import { BrihatDashaPeriods } from './BrihatDashaPeriods';
import { durationLabel, qualityLabel } from './brihatPeriods';

type Yoga = { name: string; matched: boolean; active?: boolean; condition: string; reference: string; group?: string };
export type Strength = {
  planet: string; sign: string; navamsa: string; nature: string; sthana: string[];
  dig: boolean; dig_house: number; bhava: number; chesta: string; kala: boolean; paksha: boolean;
  combust: boolean | null; dignity: string; good_fraction: string; bad_fraction: string; natural_rank: number;
  sthana_checks: { label: string; supported: boolean }[]; chesta_supported: boolean;
  relations: { planet: string; relation: string }[];
};
export type Period = { lord: string; years: number; start: string; end: string; quality?: string;
  sub_periods?: { lord: string; start: string; end: string; weight: string; share: string }[] };
type Options = { model: 'pinda' | 'amsa'; seed: 'Sun' | 'Moon' | 'Lagna'; priority: string[];
  lagna_years: 'navamsas' | 'signs'; vakra_exemption: 'retrograde' | 'mars'; krurodaya: 'zodiac' | 'rising_sign' };
export type Dasha = { worksheet: { rows: { lord: string; house: number; base: number; multiplier: number;
  enemy_loss: string; combust_loss: string; chakra_loss: string; years: number; final_years: number; quality: string; calculation_steps: string[] }[];
  krurodaya_loss: number; total: number; options: Options }; periods: Period[]; conventions: string };
export type BrihatReport = {
  strengths: Strength[]; aspects: { source: string; target: string; fraction: string; reference: string }[];
  lunar: Yoga[]; nabhasa: Yoga[]; raja: Yoga[];
  conjunctions: { planets: string[]; sign: string; reference: string }[];
  career: { base: string; tenth: string; lord: string; navamsa: string; career_lord: string; themes: string; reference: string }[];
  ashtakavarga: { planet: string; sign: string; bindus: number; reading: string; scores: number[] }[];
  natural_dasha: Period[];
  placements: { planet: string; sign: string; house: number; d9: string; d3: string; d30: string; drekkana_verse: number }[];
  own_counts: { own: number; exalted: number }; moon_nakshatra: { name: string; index: number; pada: number };
  moon_sign: string; lagna_drekkana_verse: number; dasha: Dasha; predictions: Predictions;
};
const views = [['strengths', '⚖️', 'Strengths'], ['dashas', '⏳', 'Dashas'],
  ['yogas', '✨', 'Yogas'], ['readings', '🔭', 'Chart readings'], ['ashtaka', '📊', 'Ashtakavarga'], ['predictions', '🔮', 'Predictions']];
const signNames = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];

function Table({ heads, children, name }: { heads: string[]; children: React.ReactNode; name: string }) {
  return <div className="table-scroll" role="region" aria-label={name} tabIndex={0}><table className="bj-table"><thead><tr>{heads.map(h => <th key={h}>{h}</th>)}</tr></thead><tbody>{children}</tbody></table></div>;
}

export function BrihatJataka({ report, birthData, ascendantSign }: { report: BrihatReport; birthData: Bootstrap['birth_data']; ascendantSign: string; active: boolean }) {
  const [view, setView] = useState('strengths');
  const [dashaView, setDashaView] = useState('ayurdaya');
  const [options, setOptions] = useState<Options>(report.dasha.worksheet.options);
  const [dasha, setDasha] = useState(report.dasha);
  const [calculating, setCalculating] = useState(false);
  const [calculationError, setCalculationError] = useState('');
  const [onlyMatched, setOnlyMatched] = useState(false);

  useEffect(() => { setOptions(report.dasha.worksheet.options); setDasha(report.dasha); setCalculationError(''); }, [report]);


  const used = dasha.worksheet.options;
  const changed = options.model !== used.model || options.seed !== used.seed ||
    options.lagna_years !== used.lagna_years || options.vakra_exemption !== used.vakra_exemption ||
    options.krurodaya !== used.krurodaya || options.priority.join(',') !== used.priority.join(',');
  function priority(index: number, value: string) {
    const order = options.priority.slice();
    const other = order.indexOf(value);
    [order[index], order[other]] = [order[other], order[index]];
    setOptions({ ...options, priority: order });
  }
  async function calculate() {
    setCalculating(true); setCalculationError('');
    try {
      const response = await fetch('/api/brihat-jataka/dasha', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ birth_data: birthData, options }) });
      if (!response.ok) throw new Error('The worksheet could not be calculated. Check your selected settings.');
      setDasha(await response.json() as Dasha);
    } catch (error) { setCalculationError(error instanceof Error ? error.message : 'Please try again.'); }
    finally { setCalculating(false); }
  }
  function yogaTable(rows: Yoga[], name: string) {
    const shown = rows.filter(r => !onlyMatched || r.matched);
    return <Table name={name} heads={['Yoga / configuration', 'Result', 'Rule applied']}>
      {shown.map((r, i) => <tr key={`${r.name}-${i}`}><td><strong>{r.name.replace(/XI\.\d+\s*/g, '')}</strong>{r.group && <small className="bj-small">{r.group}</small>}</td><td>{r.matched ? r.active === false ? r.name.startsWith('Kemadruma') ? 'Present · cancelled' : 'Present · superseded' : 'Condition present' : 'Absent'}</td><td>{r.condition.replace('commentary cancellation', 'cancellation')}</td></tr>)}
      {!shown.length && <tr><td colSpan={3}>No matching configurations in this group.</td></tr>}
    </Table>;
  }
  function timeline(periods: Period[], name: string) {
    return <Table heads={['Planet / point', 'Duration · 360-day years', 'Starts', 'Ends', 'Shorter periods']} name={name}>
      {periods.map((p, i) => <tr key={`${p.lord}-${i}`}><td><strong>{p.lord}</strong></td><td>{durationLabel(p.years)}<small className="bj-small">{p.years.toFixed(4)} calculation years</small></td><td>{formatDate(p.start)}</td><td>{formatDate(p.end)}</td><td>{p.quality && <span>{qualityLabel(p.quality)}</span>}{p.sub_periods && <details><summary>{p.sub_periods.length} shorter periods (antardashas)</summary><ol className="bj-subperiods">{p.sub_periods.map(sub => <li key={sub.lord}><strong>{sub.lord}</strong> · {formatDate(sub.start)} → {formatDate(sub.end)}<small>Position weight {sub.weight} · normalized share {sub.share}</small></li>)}</ol></details>}</td></tr>)}
    </Table>;
  }

  return <div className="bj-workspace">
    <nav className="bj-tabs" aria-label="Brihat Jataka views">{views.map(([id, emoji, label]) => <button key={id} type="button" className={view === id ? 'is-active' : ''} aria-pressed={view === id} onClick={() => setView(id)}><span aria-hidden="true">{emoji}</span> {label}</button>)}</nav>
    {view === 'strengths' && <>
      <section className="astro-panel bj-strength-panel"><h2>⚖️ Planetary strengths</h2><p>See which conditions support each planet.</p>
        <StrengthGraphs strengths={report.strengths} />
        <details className="bj-strength-details"><summary>View rules &amp; calculations</summary>
        <p className="hint">Each supported condition counts as 1. Placement checks five conditions; direction checks the preferred Bhava; motion checks the Sun/Moon’s Capricorn–Gemini condition or retrograde motion for the other planets; time and phase check day/night and Paksha separately.</p>
        <Table name="Classical planetary strengths" heads={['Planet', 'Sthana support', 'Dig support', 'Chesta evaluated', 'Kala / Paksha', 'Natural order']}>
          {report.strengths.map(r => <tr key={r.planet}><td><strong>{r.planet}</strong><small className="bj-small">{r.nature} · {r.sign}</small></td><td>{r.sthana.join(', ') || 'No listed support'}</td><td>{r.dig ? 'Supported' : 'No'}<small className="bj-small">Bhava {r.bhava}; preferred {r.dig_house}</small></td><td>{r.chesta}</td><td>{r.kala ? 'Day/night supported' : 'Day/night unsupported'}<small className="bj-small">{r.paksha ? 'Paksha supported' : 'Paksha unsupported'}</small></td><td>{r.natural_rank}</td></tr>)}
        </Table>
        <p className="hint">Brightness, planetary war and year/month/hour strength need additional calculations in this Brihat Jataka view. The natural order is shown separately; there is no combined strength score.</p>
        </details>
      </section>
      <section className="astro-panel"><h2>Good and adverse effect proportions</h2><p>These fractions show how sign dignity and closeness to the Sun qualify house effects.</p>
        <Table name="House effect proportions" heads={['Planet', 'Dignity', 'Combust', 'Good effects', 'Adverse effects']}>
          {report.strengths.map(r => <tr key={r.planet}><td>{r.planet}</td><td>{r.dignity}</td><td>{r.combust === null ? 'Threshold needs verification' : r.combust ? 'Yes' : 'No'}</td><td>{r.good_fraction}</td><td>{r.bad_fraction}</td></tr>)}
        </Table><p className="hint">The near-Sun threshold for retrograde Venus is unconfirmed. A neutral sign has no fixed fraction in this calculation.</p>
      </section>
      <section className="astro-panel"><h2>Fivefold friendship</h2><Table name="Fivefold friendship" heads={['From / to', ...report.strengths.map(r => r.planet)]}>{report.strengths.map(r => <tr key={r.planet}><th>{r.planet}</th>{r.relations.map(other => <td key={other.planet}>{other.relation.replaceAll('_', ' ')}</td>)}</tr>)}</Table></section>
    </>}
    {view === 'dashas' && <>
      <nav className="bj-dasha-modes" aria-label="Brihat dasha methods"><button type="button" aria-pressed={dashaView === 'ayurdaya'} onClick={() => setDashaView('ayurdaya')}>Ayurdaya dasha · from your chart</button><button type="button" aria-pressed={dashaView === 'natural'} onClick={() => setDashaView('natural')}>Naisargika dasha · natural ages</button></nav>
      {dashaView === 'ayurdaya' && <>
      <BrihatDashaPeriods predictions={report.predictions} dasha={dasha} birthData={birthData} settingsChanged={changed} />
      <section className="astro-panel"><h2>Ayurdaya dasha settings</h2><p>Your planetary degrees determine the duration of each period. Choose Amsa or Pinda and the starting point.  </p>
        <div className="bj-controls">
          <label>Year method<select value={options.model} onChange={e => setOptions({ ...options, model: e.target.value as Options['model'] })}><option value="amsa">Amsa · divisional placement</option><option value="pinda">Pinda · distance from exaltation</option></select></label>
          <label>Starting point<select value={options.seed} onChange={e => setOptions({ ...options, seed: e.target.value as Options['seed'] })}>{['Lagna', 'Sun', 'Moon'].map(p => <option key={p}>{p}</option>)}</select></label>
          <label>Lagna contribution<select value={options.lagna_years} onChange={e => setOptions({ ...options, lagna_years: e.target.value as Options['lagna_years'] })}><option value="navamsas">Navamsas passed · primary rule</option><option value="signs">Signs passed · powerful Lagna variant</option></select></label>
          <label>Enemy-sign reduction exemption<select value={options.vakra_exemption} onChange={e => setOptions({ ...options, vakra_exemption: e.target.value as Options['vakra_exemption'] })}><option value="retrograde">Retrograde planets</option><option value="mars">Mars only · alternative rule</option></select></label>
          {options.model === 'pinda' && <label>Krurodaya variant<select value={options.krurodaya} onChange={e => setOptions({ ...options, krurodaya: e.target.value as Options['krurodaya'] })}><option value="zodiac">From Aries · primary text</option><option value="rising_sign">Within the rising sign · alternative rule</option></select></label>}
        </div>
        <details className="bj-order"><summary>Review strength order · strongest first</summary><p className="hint">The default uses natural planetary order, placing Lagna last for ties. It does not determine the strongest of Sun, Moon and Lagna from all five strength conditions. Set the starting point and order after reviewing Strengths. Equal-power reappearance ties can be resolved here too.</p><div className="bj-controls">{options.priority.map((p, i) => <label key={i}>Priority {i+1}<select value={p} onChange={e => priority(i, e.target.value)}>{options.priority.map(name => <option key={name}>{name}</option>)}</select></label>)}</div></details>
        <div className="bj-actions"><button type="button" className="primary-button" onClick={calculate} disabled={calculating}>{calculating ? 'Calculating…' : 'Calculate worksheet'}</button>{changed && <span role="status">Settings changed. Calculate to update the report.</span>}</div>
        {calculationError && <p className="app-alert" role="alert">{calculationError}</p>}
      </section>
      <section className="astro-panel" aria-busy={calculating}><h2>{dasha.worksheet.options.model === 'amsa' ? 'Amsayurdaya' : 'Pindayurdaya'} · {dasha.worksheet.options.seed} first</h2><p className="hint">These calculated years set dasha durations. They do not predict lifespan. One calculation year equals 360 days.</p>
        <Table name="Ayurdaya calculation steps" heads={['Planet / point', 'Starting years', 'Strength multiplier', 'Enemy-sign reduction', 'Near-Sun reduction', 'House reduction', 'Final years', 'Calculation']}>
          {dasha.worksheet.rows.map(r => <tr key={r.lord}><td>{r.lord}</td><td>{r.base.toFixed(4)}</td><td>×{r.multiplier}</td><td>{r.enemy_loss}</td><td>{r.combust_loss}</td><td>{r.chakra_loss}</td><td>{r.final_years.toFixed(4)}</td><td><details><summary>Show steps</summary><ol className="bj-calculation-steps">{r.calculation_steps?.map((step, i) => <li key={i}>{step}</li>)}</ol></details></td></tr>)}
        </Table><details className="bj-order"><summary>Calculation rules</summary><ol className="bj-calculation-steps"><li>Amsa base = (full zodiac longitude × 0.3) remainder 12. Use the largest applicable strength multiplier once.</li><li>Pinda base = the planet’s maximum years × (1 − angular distance from deep exaltation / 360).</li><li>Apply the larger of enemy-sign and near-Sun reductions. Apply the house-position reduction next.</li><li>Final Ascendant-related reduction: {(dasha.worksheet.krurodaya_loss * 100).toFixed(3)}%, allocated proportionally across the periods.</li><li>Order: selected starting point first; then angular houses, following houses, and remaining houses, with the chosen strength order resolving ties.</li></ol></details>
        <h3>Complete Ayurdaya dasha timeline</h3><p>Open a planet’s shorter periods to see all its antardashas.</p>{timeline(dasha.periods, 'Brihat Jataka dashas and antardashas')}
      </section>
      </>}
      {dashaView === 'natural' && <>
        <BrihatDashaPeriods predictions={report.predictions} dasha={dasha} birthData={birthData} settingsChanged={false} mode="natural" naturalPeriods={report.natural_dasha} />
        <section className="astro-panel"><h2>🌱 Naisargika dasha · natural age periods</h2><p>Moon → Mars → Mercury → Venus → Jupiter → Sun → Saturn. This sequence totals 120 calculation years and does not use planetary degrees or strength.</p>
        <Table name="Natural dashas" heads={['Planet', 'Age range · calculation years', 'Duration', 'Starts', 'Ends']}>
          {report.natural_dasha.map((period, index) => {
            const age = report.natural_dasha.slice(0, index).reduce((sum, row) => sum + row.years, 0);
            return <tr key={period.lord} data-natural-lord={period.lord}><td><strong>{period.lord}</strong></td><td>{age}–{age + period.years}</td><td>{period.years} {period.years === 1 ? 'year' : 'years'}</td><td>{formatDate(period.start)}</td><td>{formatDate(period.end)}</td></tr>;
          })}
        </Table><p className="hint">Age ranges use 360-day calculation years. The dates above are calculated from your birth input.</p></section>
      </>}
    </>}
    {view === 'yogas' && <>
      <section className="astro-panel"><h2>✨ Planetary combinations</h2><label className="bj-check"><input type="checkbox" checked={onlyMatched} onChange={e => setOnlyMatched(e.target.checked)} /> Show matching conditions only</label><p className="hint">Conditions are checked against the seven classical planets. Rahu and Ketu do not enter these seven-body rules. A matching combination still depends on planetary strength and other chart conditions.</p></section>
      <section className="astro-panel"><h2>Lunar yogas</h2>{yogaTable(report.lunar, 'Lunar yogas')}</section>
      <section className="astro-panel"><h2>Nabhasa · all 32 forms</h2><p className="hint">Sign patterns use D1. House patterns divide the four quadrants into three and place the Ascendant at the centre of house 1. Superseded patterns remain visible. </p>{yogaTable(report.nabhasa, 'All 32 Nabhasa forms')}</section>
      <section className="astro-panel"><h2>Raja configurations </h2><p className="hint">These exact configurations are calculated. Only the implemented placement rules are checked; their final strength still requires judgment.</p>{yogaTable(report.raja, 'Raja configurations')}</section>
      <section className="astro-panel"><h2>Two-planet combinations</h2><Table name="Two-planet combinations" heads={['Planets together', 'Sign']}>{report.conjunctions.map(r => <tr key={r.planets.join('-')}><td>{r.planets.join(' + ')}</td><td>{r.sign}</td></tr>)}{!report.conjunctions.length && <tr><td colSpan={2}>No classical planets share a sign.</td></tr>}</Table><p className="hint">Planets sharing a sign are grouped into pairs. This table shows the calculated combinations.</p></section>
    </>}
    {view === 'readings' && <>
      <section className="astro-panel"><h2>🔭 Your birth chart</h2><div className="bj-reading-grid"><div><span className="quiet-label">MOON’S NAKSHATRA</span><h3>{report.moon_nakshatra.name}</h3><p>Pada {report.moon_nakshatra.pada}</p></div><div><span className="quiet-label">MOON’S SIGN</span><h3>{report.moon_sign}</h3></div><div><span className="quiet-label">ASCENDANT’S 10° DIVISION</span><h3>Part {(report.lagna_drekkana_verse - 1) % 3 + 1} of 3</h3></div></div></section>
      <section className="astro-panel"><h2>Sign, Bhava and Varga placements</h2><p className="hint">Houses use quadrant divisions. D3, D9 and D30 are calculated from each planet’s natal longitude.</p><Table name="Classical chart placements" heads={['Planet', 'D1 sign', 'Bhava', 'D3', 'D9', 'D30']}>
        {report.placements.map(p => <tr key={p.planet}><td><strong>{p.planet}</strong></td><td>{p.sign}</td><td>{p.house}</td><td>{p.d3}</td><td>{p.d9}</td><td>{p.d30}</td></tr>)}
      </Table><p>Own signs: {report.own_counts.own} planets · Exalted signs: {report.own_counts.exalted} planets. </p></section>
      <section className="astro-panel"><h2>Work calculation · from Ascendant, Moon and Sun</h2><p>Find the 10th sign, its ruling planet, that planet’s D9 sign, and the D9 sign’s ruler. The final planet gives the work theme. </p><Table name="Avocation chains" heads={['From', 'Tenth sign', 'Tenth lord', 'Its D9', 'D9 lord', 'Traditional themes']}>{report.career.map(r => <tr key={r.base}><td>{r.base}</td><td>{r.tenth}</td><td>{r.lord}</td><td>{r.navamsa}</td><td>{r.career_lord}</td><td>{r.themes}</td></tr>)}</Table></section>
      <section className="astro-panel"><h2>Fractional planetary aspects</h2><p>Aspect bands span ±15° around the specified middle points.  </p><Table name="Fractional aspects" heads={['From', 'To', 'Aspect strength']}>{report.aspects.map(r => <tr key={`${r.source}-${r.target}`}><td>{r.source}</td><td>{r.target}</td><td>{r.fraction}</td></tr>)}</Table></section>
    </>}
    {view === 'ashtaka' && <section className="astro-panel"><h2>📊 Brihat Jataka Ashtakavarga</h2><p>Each planet’s chart shows support across the 12 signs. More than four bindus means more support; fewer than four means less support; four gives a mixed result. The combined chart adds all seven planets. </p>
      <BrihatAshtakavarga rows={report.ashtakavarga} ascendantSign={ascendantSign} />
      <details className="bj-strength-details"><summary>View the full Ashtakavarga table</summary>
      <Table name="Brihat Jataka Ashtakavarga" heads={['Planet', 'Natal sign', 'Bindus', 'Result', ...signNames]}>{report.ashtakavarga.map(r => <tr key={r.planet}><td>{r.planet}</td><td>{r.sign}</td><td>{r.bindus}</td><td>{r.reading}</td>{r.scores.map((score, i) => <td key={i}>{score}</td>)}</tr>)}</Table><p className="hint">These are the unreduced seven BAV calculations. Shodhana reductions and pindas are not calculated yet.</p>
      </details>
    </section>}
    {view === 'predictions' && <BrihatPredictions predictions={report.predictions} dasha={dasha} birthData={birthData} settingsChanged={changed} onTimeline={() => { setView('dashas'); setDashaView('ayurdaya'); }} />}
  </div>;
}
