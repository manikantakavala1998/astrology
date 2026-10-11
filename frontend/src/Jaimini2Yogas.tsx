import type { Jaimini2Report } from './jaiminiTypes';
import { Planet, Rules, Table } from './Jaimini';

export function Jaimini2Yogas({ report }: { report: Jaimini2Report }) {
  const yogas = report.schemes['7'].yogas;
  return <>
    <div className="jaimini2-yoga-grid">{(['yogada', 'kevala'] as const).map(kind => {
      const conditions = yogas.filter(row => row.kind === kind && row.present);
      const planets = [...new Set(conditions.flatMap(row => row.planets))];
      const name = kind === 'yogada' ? 'Yogada' : 'Kevala';
      const moonLord = yogas.find(row => row.kind === kind && row.variant === 'moon_dispositor');
      return <section className="astro-panel jaimini-panel jaimini2-yoga-panel" key={kind}>
        <div className="jaimini2-yoga-heading"><h2>{kind === 'yogada' ? '🌟' : '✨'} {name} planets</h2><span>{planets.length} {planets.length === 1 ? 'planet' : 'planets'}</span></div>
        <p className="jaimini-intro">{kind === 'yogada' ? 'Aspects the ascendant in at least two charts.' : 'Planets meeting the Kevala aspect rule.'}</p>
        {planets.length ? <Table title={`${name} qualifying planets`}
          headings={kind === 'yogada' ? ['Planet', 'D1', 'D3', 'D9'] : ['Planet', 'Aspected sign', 'House']}
          rows={planets.map(planet => {
            const related = conditions.filter(row => row.planets.includes(planet));
            const moonMatch = related.find(row => row.variant === 'moon_dispositor');
            const label = <><Planet name={planet} />{moonMatch && <small>Moon-dispositor rule</small>}</>;
            if (kind === 'yogada') {
              const charts = yogas.find(row => row.variant === 'multi_chart' && row.planets.includes(planet))?.matched_charts ?? [];
              return [label, ...['D1', 'D3', 'D9'].map(chart => charts.includes(chart)
                ? <span className="jaimini2-yoga-check" aria-label={`${chart} ascendant aspected`}>✓</span>
                : <span className="jaimini2-yoga-no-match" aria-label={`${chart} ascendant not aspected`}>—</span>)];
            }
            const connections = related.flatMap(row => row.connections ?? []);
            const signs = [...new Set(connections.map(connection => connection.sign))];
            const houses = [...new Set(connections.map(connection => connection.house))];
            return [label, signs.join(' · '), houses.map(house => `H${house}`).join(' · ')];
          })} /> : <p className="jaimini-quiet jaimini2-yoga-empty">No planet meets the {name} conditions in this chart.</p>}
        <p className="jaimini2-yoga-rule"><strong>{name} rule:</strong> {kind === 'yogada' ? 'at least 2 of D1, D3 and D9 match.' : 'sign aspect to Lagna, H5, H7 or H9.'}</p>
        <p className="jaimini2-yoga-alternative">Also checked: Moon’s sign lord {kind === 'yogada' ? 'must aspect both Moon and Lagna.' : 'aspects exactly one of Moon or Lagna.'}
          {moonLord?.present ? <><br /><Planet name={moonLord.planets[0]} /> qualifies through this rule.</> : <><br />No additional planet qualifies through this rule.</>}
        </p>
        {!!conditions.length && <Rules>{conditions.map(row => <p key={row.name}><strong>{row.name}</strong><br />{row.evidence}<br />{row.rule}</p>)}</Rules>}
      </section>;
    })}</div>
    <p className="jaimini2-yoga-overlap">A planet can qualify as both Yogada and Kevala. Each rule is checked separately.</p>
  </>;
}
