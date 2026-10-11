import { useId, useState, type CSSProperties } from 'react';
import type { Strength } from './BrihatJataka';
import { planetColors } from './planetColors';

type Check = { label: string; supported: boolean };
type Category = { id: string; title: string; caption: string; checks: (row: Strength) => Check[] };

const categories: Category[] = [
  { id: 'sthana', title: 'Sthana · Placement', caption: '5 placement conditions', checks: row => row.sthana_checks },
  { id: 'dig', title: 'Dig · Direction', caption: 'Preferred Bhava condition', checks: row => [
    { label: `Bhava ${row.bhava}; preferred ${row.dig_house}`, supported: row.dig },
  ] },
  { id: 'chesta', title: 'Cheshta · Motion', caption: '1 motion condition', checks: row => [
    { label: ['Sun', 'Moon'].includes(row.planet) ? 'Capricorn–Gemini condition' : 'Retrograde motion', supported: row.chesta_supported },
  ] },
  { id: 'kala', title: 'Kala · Time & phase', caption: 'Day/night and Paksha conditions', checks: row => [
    { label: 'Day/night', supported: row.kala }, { label: 'Paksha', supported: row.paksha },
  ] },
];

function SupportGraph({ category, strengths }: { category: Category; strengths: Strength[] }) {
  const id = useId();
  const [selected, setSelected] = useState(strengths[0]?.planet ?? '');
  const rows = strengths.map(row => ({ row, checks: category.checks(row) }));
  const maximum = Math.max(1, ...rows.map(row => row.checks.length));
  const detail = rows.find(({ row }) => row.planet === selected) ?? rows[0];
  const allZero = rows.every(({ checks }) => !checks.some(check => check.supported));

  return <figure className="bj-strength-graph" aria-labelledby={id} data-category={category.id}>
    <figcaption><h3 id={id}>{category.title}</h3><p>{allZero
      ? category.id === 'dig' ? 'No planet meets the preferred Bhava condition' : 'No supported conditions for these planets'
      : category.caption}</p></figcaption>
    <div className="bj-strength-plot">
    <div className="bj-strength-scale" aria-hidden="true">
      {Array.from({ length: maximum + 1 }, (_, i) => <span key={i}>{maximum - i}</span>)}
    </div>
    <div className="bj-strength-grid" aria-hidden="true" style={{ backgroundSize: `100% ${100 / maximum}%` }} />
    <div className="bj-strength-rows">
      {rows.map(({ row, checks }) => {
        const count = checks.filter(check => check.supported).length;
        const description = checks.map(check => `${check.label}: ${check.supported ? 'supported' : 'not supported'}`).join('; ');
        return <button type="button" className="bj-strength-row" key={row.planet}
          aria-label={`${row.planet}: ${count} of ${checks.length} evaluated conditions supported. ${description}`}
          onMouseEnter={() => setSelected(row.planet)} onFocus={() => setSelected(row.planet)} onClick={() => setSelected(row.planet)}
          data-planet={row.planet} data-value={count} data-maximum={checks.length}
          style={{ '--planet-color': planetColors[row.planet] } as CSSProperties}>
          <span className="bj-strength-value">{count}<small>/{checks.length}</small></span>
          <span className="bj-strength-track" aria-hidden="true">
            {count ? <span className="bj-strength-bar" style={{ height: `${count / maximum * 100}%` }} />
              : <span className="bj-strength-zero" />}
          </span>
          <span className="bj-strength-planet" aria-hidden="true">{row.planet}</span>
        </button>;
      })}
    </div>
    </div>
    {detail && <p className="bj-strength-description" aria-live="polite"><strong style={{ color: planetColors[detail.row.planet] }}>{detail.row.planet}</strong> · {detail.checks.filter(check => check.supported).map(check => check.label).join(', ') || 'No support from these evaluated conditions'}.</p>}
  </figure>;
}

export function StrengthGraphs({ strengths }: { strengths: Strength[] }) {
  return <div className="bj-strength-visualization">
    <p className="hint bj-strength-key">Counts of supported conditions <span>·</span> <span className="bj-zero-key" aria-hidden="true" /> 0 means the condition is not met. Select a planet to see its conditions.</p>
    <div className="bj-strength-graphs">{categories.map(category => <SupportGraph key={category.id} category={category} strengths={strengths} />)}</div>
    <section className="bj-strength-summary" aria-labelledby="bj-condition-summary">
      <div className="bj-strength-summary-heading"><h3 id="bj-condition-summary">Conditions at a glance</h3><p>Separate condition counts, not a combined strength score.</p></div>
      <div className="table-scroll" role="region" aria-label="Planetary support condition counts" tabIndex={0}>
        <table className="bj-support-table"><thead><tr><th scope="col">Planet</th><th scope="col">Placement (5)</th><th scope="col">Direction (1)</th><th scope="col">Motion (1)</th><th scope="col">Time &amp; phase (2)</th></tr></thead>
          <tbody>{strengths.map(row => <tr key={row.planet} style={{ '--planet-color': planetColors[row.planet] } as CSSProperties}>
            <th scope="row"><span className="bj-summary-dot" aria-hidden="true" />{row.planet}</th>
            {categories.map(category => { const checks = category.checks(row); return <td key={category.id}>{checks.filter(check => check.supported).length}/{checks.length}</td>; })}
          </tr>)}</tbody>
        </table>
      </div>
    </section>
    <p className="bj-natural-order"><span>Natural order · strongest first</span>{[...strengths].sort((a, b) => a.natural_rank - b.natural_rank).map(row => row.planet).join(' → ')}</p>
  </div>;
}
