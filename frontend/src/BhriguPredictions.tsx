import type { BcpYear, BhriguReport, BspRule, PadmaYear } from './bhriguTypes';
import type { VimshottariPeriod } from './types';
import { Panel, Planet, Planets, Rules, Table } from './Jaimini';
import { dashaLevels } from './useBhriguTiming';

const signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];
const signLords = ['Mars', 'Venus', 'Mercury', 'Moon', 'Sun', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Saturn', 'Jupiter'];
const themes: Record<number, string> = {
  1: 'personal direction and self-expression', 2: 'family resources and speech',
  3: 'skills, initiative, siblings and short journeys', 4: 'home, property and emotional foundations',
  5: 'learning, creativity and children', 6: 'daily work, service and resolving disagreements',
  7: 'relationships, agreements and partnerships', 8: 'shared resources, research and changes',
  9: 'higher learning, mentors and long journeys', 10: 'career, responsibilities and public work',
  11: 'gains, networks and elder siblings', 12: 'expenses, retreat and connections abroad',
};
const periodScopes = ['Long-term focus', 'Within the major period', 'Shorter-term focus', 'Fine timing', 'Shortest timing layer'];
const housesLabel = (houses: number[]) => houses.map(h => `H${h}`).join(', ');
const unique = <T,>(values: T[]) => [...new Set(values)];

interface Reading { title: string; summary: string; calculation: string; houses: number[]; planets: string[]; houseLabels?: string[] }
interface YearReading { overview: Reading[]; details: Reading[]; targetHouses: number[] }

// Interpret only the targets already calculated by the selected method.
// Vimshottari remains a separate timing context, with no invented combined score.
function yearReadings(method: 'bcp' | 'bsp' | 'padma', selected: BcpYear | PadmaYear, report: BhriguReport, rules: BspRule[], variant: string): YearReading {
  const details: Reading[] = [];
  const placement = (name: string) => report.planets.find(p => p.planet === name);
  const annualSign = 'sign_from_lagna' in selected ? selected.sign_from_lagna : selected.sign;
  const annualHouse = selected.house_from_lagna;
  const annual: Reading = {
    title: 'Main focus of this year', houses: [annualHouse], planets: [selected.year_lord],
    summary: `Year ${selected.age} brings ${themes[annualHouse]} into focus. ${selected.year_lord} is the ruler to examine for this ${annualSign} year.`,
    calculation: `((running year ${selected.age} − 1) mod 12) + 1 = H${annualHouse}; count from D1 Lagna → ${annualSign}; sign ruler = ${selected.year_lord}.`,
  };
  if (method === 'bcp') {
    const row = selected as BcpYear;
    details.push(annual);
    const lord = placement(row.year_lord);
    const lordReading: Reading = {
      title: 'How the year lord connects', houses: lord ? [lord.house] : [], planets: [row.year_lord],
      summary: lord ? `${row.year_lord} in ${lord.sign}, H${lord.house}, connects this year's ${themes[annualHouse]} with ${themes[lord.house]}.` : 'Year-lord placement is unavailable.',
      calculation: `Annual sign ${annualSign} → ${row.year_lord} → natal ${lord ? `${lord.sign}, H${lord.house}` : 'placement unavailable'}.`,
    };
    details.push(lordReading);
    const cycleBase = row.cycle_ruler ? placement(row.cycle_ruler) : undefined;
    const cycleHouse = row.house_from_cycle_ruler;
    const fromCycle = (sign: string) => ((signs.indexOf(sign) - signs.indexOf(cycleBase!.sign) + 12) % 12) + 1;
    const cycle: Reading = {
      title: 'Cycle ruler adds a second focus', houses: row.cycle_d1_house ? [row.cycle_d1_house] : [], planets: row.cycle_ruler ? [row.cycle_ruler] : [],
      houseLabels: cycleHouse && row.cycle_d1_house ? [`H${cycleHouse} from ${row.cycle_ruler}`, `D1 H${row.cycle_d1_house}`] : [],
      summary: cycleHouse && cycleBase ? `Treat ${row.cycle_ruler}'s natal sign ${cycleBase.sign} as Lagna. H${cycleHouse} from ${row.cycle_ruler} brings ${themes[cycleHouse]} into focus through ${row.sign_from_cycle_ruler}. That sign maps to D1 H${row.cycle_d1_house}.` : 'This year uses Lagna progression. The nine-ruler cycle extension ends at year 108.',
      calculation: row.cycle_ruler ? `Cycle ${row.cycle_number}; ${row.house_from_cycle_ruler}th from ${row.cycle_ruler} in ${placement(row.cycle_ruler)?.sign} → ${row.sign_from_cycle_ruler} → D1 H${row.cycle_d1_house}.` : 'No cycle-ruler target is calculated for years 109–120.',
    };
    details.push(cycle);
    if (cycleBase && cycleHouse && row.sign_from_cycle_ruler && row.cycle_d1_house) {
      const reference = `from ${row.cycle_ruler}`;
      const cycleLord = row.cycle_sign_lord ? placement(row.cycle_sign_lord) : undefined;
      if (cycleLord) {
        const lordHouse = fromCycle(cycleLord.sign);
        const ruledHouses = Array.from({length: 12}, (_, i) => i + 1).filter(h => signLords[(signs.indexOf(cycleBase.sign) + h - 1) % 12] === cycleLord.planet);
        details.push({title: 'Cycle-house lord connection', houses: [cycleLord.house], planets: [cycleLord.planet],
          houseLabels: [`H${lordHouse} ${reference}`, `D1 H${cycleLord.house}`],
          summary: `${cycleLord.planet} rules ${housesLabel(ruledHouses)} ${reference} and occupies ${cycleLord.sign}, H${lordHouse} ${reference}. This connects the cycle year's ${themes[cycleHouse]} with ${themes[lordHouse]}.`,
          calculation: `Use ${cycleBase.sign} as H1. ${row.sign_from_cycle_ruler} is H${cycleHouse}; its ruler ${cycleLord.planet} occupies ${cycleLord.sign}, H${lordHouse} in this cycle chart (D1 H${cycleLord.house}).`,
        });
      }
      const cycleOccupants = report.planets.filter(p => p.sign === row.sign_from_cycle_ruler);
      if (cycleOccupants.length) details.push({title: 'Planets in the cycle house', houses: [row.cycle_d1_house], planets: cycleOccupants.map(p => p.planet),
        houseLabels: [`H${cycleHouse} ${reference}`, `D1 H${row.cycle_d1_house}`],
        summary: `${cycleOccupants.map(p => p.planet).join(', ')} occupy ${row.sign_from_cycle_ruler}, connecting them with ${themes[cycleHouse]} in the cycle chart.`,
        calculation: `${row.sign_from_cycle_ruler} is H${cycleHouse} ${reference}; natal occupants remain in the same sign.`,
      });
      report.aspects.filter(a => a.sign === row.sign_from_cycle_ruler).forEach(a => {
        const sourceHouse = fromCycle(a.source_sign);
        details.push({title: `${a.planet} aspect in the cycle chart`, houses: [a.source_house, row.cycle_d1_house!], planets: [a.planet, ...a.planets],
          houseLabels: [`H${sourceHouse} → H${cycleHouse} ${reference}`],
          summary: `${a.planet} in H${sourceHouse} ${reference} connects ${themes[sourceHouse]} with ${themes[cycleHouse]} through its ${a.offset}th aspect.`,
          calculation: `${a.planet}: ${a.source_sign}, H${sourceHouse} ${reference} → ${a.offset}th aspect → ${a.sign}, H${cycleHouse} ${reference} (D1 H${a.house}).`,
        });
      });
    }
    return withConnections([annual, lordReading, cycle], details, unique([annualHouse, ...(row.cycle_d1_house ? [row.cycle_d1_house] : [])]), report);
  }
  if (method === 'padma') {
    const row = selected as PadmaYear;
    details.push(annual);
    const mapped: Reading = {
      title: 'Where the D12 connection leads', houses: [row.superimposed_house_from_lagna], planets: [row.year_lord],
      summary: `${row.year_lord}'s D12 sign ${row.year_lord_dwadasamsa_sign} maps to D1 H${row.superimposed_house_from_lagna}. This links the year's focus with ${themes[row.superimposed_house_from_lagna]}.`,
      calculation: `${row.year_lord} → D12 ${row.year_lord_dwadasamsa_sign} → count that sign from D1 Lagna = H${row.superimposed_house_from_lagna}.`,
    };
    details.push(mapped);
    const matches = report.badhaka_connections.filter(c => c.sign === annualSign || c.sign === row.year_lord_dwadasamsa_sign);
    const obstruction: Reading = {
      title: matches.length ? 'Themes that may need extra effort' : 'Badhaka connection check',
      houses: unique(matches.map(c => c.house)), planets: unique(matches.map(c => c.planet)),
      summary: matches.length ? `A Badhaka connection reaches ${unique(matches.map(c => themes[c.house])).join('; ')}. These areas may need patience and closer attention in this year's reading.` : 'Neither the annual sign nor the year lord’s D12 sign matches the calculated Badhaka connections.',
      calculation: matches.length ? matches.map(c => `${c.sign === annualSign ? 'Annual sign' : 'Year-lord D12 sign'} ${c.sign} = ${c.kind}; ${c.reason}.`).join(' ') : `Compare ${annualSign} and ${row.year_lord_dwadasamsa_sign} with the D1/D12 Badhaka signs and Badhakesh placements.`,
    };
    details.push(obstruction);
    matches.forEach(c => details.push({title: c.kind, houses: [c.house], planets: [c.planet],
      summary: `${c.sign}, H${c.house}, connects ${themes[c.house]} with ${c.planet} as Badhakesh. This is an obstruction indication to consider, not a definite event.`,
      calculation: `${c.reason}. ${c.sign === annualSign ? 'Annual sign matches' : 'Year-lord D12 sign matches'}.`,
    }));
    return withConnections([annual, mapped, obstruction], details, unique([annualHouse, row.superimposed_house_from_lagna]), report);
  }

  // BSP fixed ages are not replaced by BCP's annual progression.
  rules.forEach(rule => rule.targets.forEach(t => details.push({
    title: `BSP-${rule.rule_number} · ${t.role}`, houses: [t.house], planets: unique([rule.planet, ...t.planets]),
    summary: t.role === 'Occasional activation' ? `An occasional additional focus is ${themes[t.house]}. This target is conditional in BSP-${rule.rule_number}.`
      : t.role === 'Controlling influence' ? `${rule.planet}'s seventh-house influence connects with ${themes[t.house]}; retain it as an influence alongside the primary target.`
      : `BSP-${rule.rule_number} points to ${themes[t.house]} through ${rule.planet}'s ${t.offset === 1 ? 'occupied house' : `${t.offset}th house`}, ${t.sign} H${t.house}.`,
    calculation: `Running year ${selected.age}; ${rule.planet} in D1 H${placement(rule.planet)?.house}; ((${placement(rule.planet)?.house} − 1 + ${t.offset} − 1) mod 12) + 1 = H${t.house}, ${t.sign}; role = ${t.role}.${variant === 'status' ? ` Research qualifier: ${rule.special_status_reasons.join('; ')}.` : ''}`,
  })));
  const ageDetails = [...details];
  report.permanent.forEach(row => details.push({
    title: `BSP-${row.rule_number} · Recurring theme`, houses: [row.house_from_lagna], planets: row.planets_in_house,
    summary: row.rule_number === 14 ? `A recurring life theme is ${themes[row.house_from_lagna]}. Examine this house's lord and its connections.` : `The permanent rule describes fluctuations in ${themes[row.house_from_lagna]}. This is background to the year, without a specific event date.`,
    calculation: `${row.title} → ${row.sign}, H${row.house_from_lagna}. Permanent indication; no running-year trigger.`,
  }));
  if (report.aries) details.push({title: 'BSP-5 · Aries condition', houses: [report.aries.house_from_lagna], planets: ['Jupiter', 'Saturn'],
    summary: `The Jupiter–Saturn conjunction flags ${themes[report.aries.house_from_lagna]} for closer attention through Aries.`,
    calculation: `Jupiter and Saturn share a natal sign; Aries maps to D1 H${report.aries.house_from_lagna}. No age is assigned to this rule.`,
  });
  const venus = report.venus;
  details.push({title: 'BSP-15 · Venus connections', houses: [venus.venus_house_from_lagna, venus.twelfth_from_venus_house_from_lagna], planets: ['Venus', ...venus.conjunct_planets],
    summary: `The Venus lookup connects ${themes[venus.venus_house_from_lagna]} with its conjunctions and ${themes[venus.twelfth_from_venus_house_from_lagna]} through the twelfth from Venus.`,
    calculation: `Venus in ${venus.venus_sign}, H${venus.venus_house_from_lagna}; conjunctions: ${venus.conjunct_planets.join(', ') || 'none'}; twelfth from Venus = ${venus.twelfth_from_venus_sign}, H${venus.twelfth_from_venus_house_from_lagna}. Qualitative lookup; no dated event calculated.`,
  });
  const focus: Reading = {title: 'Main focus of this year', houses: unique(ageDetails.flatMap(r => r.houses)), planets: rules.map(r => r.planet),
    summary: ageDetails.length ? ageDetails[0].summary : `There is no applicable age-timed BSP rule for running year ${selected.age}${variant === 'status' ? ' under the selected research qualifier' : ' in the implemented rule set'}. Use the recurring themes below as background.`,
    calculation: `Match running year ${selected.age} to the fixed BSP ages${variant === 'status' ? ', then apply the special-status qualifier' : ''}. ${rules.length} rule(s) remain.`,
  };
  const second = ageDetails[1] ?? details.find(r => r.title.startsWith('BSP-1 '))!;
  const third = ageDetails[2] ?? details.find(r => r.title.startsWith('BSP-14 '))!;
  const targetHouses = unique((ageDetails.length ? ageDetails : details.filter(r => r.title.includes('Recurring theme'))).flatMap(r => r.houses));
  return withConnections([focus, second, third], details, targetHouses, report);
}

function withConnections(overview: Reading[], details: Reading[], targetHouses: number[], report: BhriguReport): YearReading {
  targetHouses.forEach(house => {
    const occupants = report.planets.filter(p => p.house === house);
    if (occupants.length) details.push({title: `Planets in H${house}`, houses: [house], planets: occupants.map(p => p.planet),
      summary: `${occupants.map(p => p.planet).join(', ')} occupy this target, connecting them with ${themes[house]}.`,
      calculation: occupants.map(p => `${p.planet}: natal ${p.sign}, D1 H${p.house}`).join('; '),
    });
    report.aspects.filter(a => a.house === house).forEach(a => details.push({title: `${a.planet} aspect to H${house}`, houses: [house, a.source_house], planets: [a.planet, ...a.planets],
      summary: `${a.planet} connects ${themes[a.source_house]} with ${themes[house]} through its ${a.offset}th aspect. ${a.planets.length ? `It reaches ${a.planets.join(', ')}.` : 'The aspected sign has no planets; the house connection still exists.'}`,
      calculation: `${a.planet} in ${a.source_sign}, H${a.source_house}; count ${a.offset} signs inclusively → ${a.sign}, H${house}.`,
    }));
  });
  return {overview, details, targetHouses};
}

export function BhriguPredictions({method, selected, report, rules, variant, path, instant, pending, error}: {
  method: 'bcp' | 'bsp' | 'padma'; selected: BcpYear | PadmaYear; report: BhriguReport; rules: BspRule[]; variant: string;
  path: VimshottariPeriod[]; instant: string; pending: boolean; error: string;
}) {
  const reading = yearReadings(method, selected, report, rules, variant);
  const ascIndex = signs.indexOf(report.bcp[0].sign_from_lagna);
  const lordships = (name: string) => Array.from({length: 12}, (_, i) => i + 1).filter(h => signLords[(ascIndex + h - 1) % 12] === name);
  const timingRows = path.map((period, level) => {
    const position = report.planets.find(p => p.planet === period.planet);
    const ruled = lordships(period.planet);
    const reached = report.aspects.filter(a => a.planet === period.planet && reading.targetHouses.includes(a.house));
    const occupiedTarget = position && reading.targetHouses.includes(position.house);
    const ruledTargets = ruled.filter(h => reading.targetHouses.includes(h));
    const connections = [occupiedTarget ? `occupies target H${position.house}` : '', ...ruledTargets.map(h => `rules target H${h}`), ...reached.map(a => `${a.offset}th aspect to target H${a.house}`)].filter(Boolean);
    return {period, level, position, ruled, connections};
  });
  const last = timingRows.length === 5 ? timingRows[4] : null;
  const [date, time] = instant.split('T');
  return <div className="bhrigu-predictions" data-year={selected.age}>
    <Panel title={`📜 Predictions · Year ${selected.age}`}>
      <p className="bhrigu-prediction-intro">Your selected-year reading, in simple words. These are possible themes from the calculated placements.</p>
      <div className="bhrigu-prediction-cards">{reading.overview.map((row, i) => <article key={`${row.title}-${i}`}>
        <h3>{row.title}</h3><p>{row.summary}</p><div className="bhrigu-prediction-tags">{(row.houseLabels ?? row.houses.map(h => `H${h}`)).map(label => <span key={label}>{label}</span>)}{row.planets.length > 0 && <Planets names={unique(row.planets)} />}</div>
      </article>)}</div>
      <Rules label="Detailed year predictions & calculations">
        <Table title="Year prediction calculations" headings={['Connection', 'Easy reading', 'Calculated reason']} rows={reading.details.map(row => [<>{row.title}<small>{row.houseLabels?.join(' · ') ?? housesLabel(row.houses)}</small><Planets names={unique(row.planets)} /></>, row.summary, row.calculation])} />
        {method === 'bcp' && <p>Cycle houses and lordships are counted from the cycle ruler's natal sign as Lagna. D1 house labels show where those same signs sit in the natal chart; the natal connections and dasha timing below retain that D1 frame.</p>}
        {method === 'padma' && <p>Padma reads the annual house, the year lord's D12 mapping and Badhaka connections. Exaltation, debilitation and dasha ratings are not added to this Padma reading.</p>}
        {method === 'bsp' && <p>{report.coverage} Occasional targets and controlling influences keep their own roles.</p>}
        <p>House themes describe the possible area of experience. A matching placement or aspect alone does not calculate a definite event, a good/bad score or its probability.</p>
      </Rules>
      <div className="bhrigu-prediction-timing" aria-busy={pending}>
        <h3>Dasha reading at your selected time</h3><p className="bhrigu-prediction-date">{date.split('-').reverse().join('/')} · {time} · Birth-place time</p>
        {last?.position ? <p className="bhrigu-prana-reading"><strong>Prana: <Planet name={last.period.planet} /></strong> in {last.position.sign}, H{last.position.house}, brings <strong>{themes[last.position.house]}</strong> into the shortest timing layer.{last.connections.length > 0 && <> Method connection: {last.connections.join('; ')}.</>}</p>
          : <p role="status">{error ? 'The complete timing reading is unavailable until the dasha branch loads. Use Retry in the timing panel.' : 'Resolving all five dasha levels for this time…'}</p>}
        <Rules label="All five dasha readings & calculations">
          <Table title="Dasha prediction calculations" headings={['Level / planet', 'Possible focus', 'Natal placement & lordships', 'Connection to this method']} rows={timingRows.map(({period, level, position, ruled, connections}) => [
            <>{dashaLevels[level]}<small><Planet name={period.planet} /></small></>, <>{periodScopes[level]}: {position ? themes[position.house] : 'Natal placement unavailable'}.</>,
            <>{position ? `${position.sign}, H${position.house}` : '—'}<small>{ruled.length ? `Rules ${housesLabel(ruled)}: ${ruled.map(h => themes[h]).join('; ')}` : 'No classical sign lordship assigned to this node.'}</small></>,
            connections.length ? connections.join('; ') : 'No occupation, lordship or outgoing aspect to the displayed method targets.',
          ])} />
          <p>Resolve each period using start ≤ selected time &lt; end, then read its planet's natal house, sign lordships and aspects to the method targets. The dasha themes are additional timing context{method === 'padma' ? '; they do not change Padma’s result or its annual dates' : ''}. The displayed connections do not form a combined prediction score.</p>
        </Rules>
      </div>
    </Panel>
  </div>;
}
