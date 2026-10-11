import { useState, type CSSProperties } from 'react';
import type { Jaimini2Report } from './jaiminiTypes';
import { degrees, Panel, Planet, Planets, Rules, Table } from './Jaimini';
import { planetColors } from './planetColors';

const signTypes = ['Movable', 'Fixed', 'Dual'];

export function Jaimini2Strength({ report }: { report: Jaimini2Report }) {
  const [selected, setSelected] = useState(report.strengths[0]?.sign);
  const detail = report.strengths.find(row => row.sign === selected) ?? report.strengths[0];
  return <Panel title="📊 Sign Strength">
    <p className="jaimini-intro">Strongest signs first · taller bars show a higher rank. Equal calculation results share the same rank.</p>
    <figure className="jaimini2-strength-graph" aria-label="Jaimini South relative sign strength graph">
      <figcaption><span>Relative rank · 1 is strongest</span><span>Colors follow each sign’s lord</span></figcaption>
      <div className="jaimini2-strength-scroll" role="region" aria-label="Sign strength bars" tabIndex={0}>
        <div className="jaimini2-strength-columns">
          {report.strengths.map(row => <button type="button" key={row.sign} className="jaimini2-strength-column"
            style={{ '--sign-color': planetColors[row.lord] ?? (row.lord === 'Rahu' ? '#b7bdd0' : '#aca2c5') } as CSSProperties}
            aria-label={`${row.sign}, rank ${row.rank} of ${report.strengths.length}; ${row.metrics[0]} planets; highest degree ${degrees(row.metrics[1])}; ${signTypes[row.metrics[2]]}; lord ${row.lord}`}
            aria-pressed={detail?.sign === row.sign} data-sign={row.sign} data-rank={row.rank}
            onClick={() => setSelected(row.sign)}>
            <span className="jaimini2-strength-rank">#{row.rank}</span>
            <span className="jaimini2-strength-track" aria-hidden="true"><span className="jaimini2-strength-bar" style={{ height: `${(report.strengths.length - row.rank + 1) / report.strengths.length * 100}%` }} /></span>
            <span className="jaimini2-strength-sign">{row.sign}</span>
          </button>)}
        </div>
      </div>
      <p className="jaimini-quiet">Bar height represents comparison rank, not a numerical strength score. Select a sign to see its calculation.</p>
    </figure>
    {detail && <section className="jaimini2-strength-detail" aria-label="Selected sign calculation" aria-live="polite">
      <div className="jaimini2-strength-detail-heading"><h3>{detail.sign}</h3><span>Rank {detail.rank} of {report.strengths.length}</span></div>
      <dl>
        <div><dt>Sign lord</dt><dd><Planet name={detail.lord} /></dd></div>
        <div><dt>Planets · {detail.metrics[0]}</dt><dd><Planets names={detail.occupants} /></dd></div>
        <div><dt>Highest occupant degree</dt><dd>{detail.metrics[0] ? degrees(detail.metrics[1]) : 'No planets'}</dd></div>
        <div><dt>Sign type</dt><dd>{signTypes[detail.metrics[2]]}</dd></div>
      </dl>
    </section>}
    <Rules><p>Compare occupation and planet count first, then the highest occupant degree, then sign type. Equal keys have equal graph ranks.</p><p>{report.rules.strength}</p>
      <Table title="Book sign strength hierarchy" headings={['Rank / sign', 'Lord', 'Occupants', 'Count', 'Highest occupant degree', 'Type']} rows={report.strengths.map(row => [`${row.rank}. ${row.sign}`, <Planet name={row.lord} />, <Planets names={row.occupants} />, row.metrics[0], row.metrics[0] ? degrees(row.metrics[1]) : '—', signTypes[row.metrics[2]]])} />
    </Rules>
  </Panel>;
}
