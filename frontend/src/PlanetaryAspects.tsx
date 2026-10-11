import { useRef, useState, type KeyboardEvent } from 'react';
import type { AspectTables } from './types';

const modes = ['vedic', 'western'] as const;
type Mode = typeof modes[number];

function PlanetName({ planet }: { planet: string }) {
  return <span className={`planet-color-${planet.toLowerCase()}`}>{planet}</span>;
}

export function PlanetaryAspects({ report }: { report: AspectTables }) {
  const [mode, setMode] = useState<Mode>('vedic');
  const [orbInput, setOrbInput] = useState(String(report.western_default_orb));
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const orbValue = Number(orbInput);
  const validOrb = orbInput.trim() !== '' && Number.isFinite(orbValue) && orbValue >= 0 && orbValue <= report.western_max_orb;
  const orb = validOrb ? orbValue : report.western_default_orb;

  function moveTab(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? 1 : (index + 1) % 2;
    setMode(modes[next]);
    tabs.current[next]?.focus();
  }

  return <div className="planetary-aspects">
    <div className="aspect-tabs" role="tablist" aria-label="Aspect methods">
      {modes.map((item, index) => <button type="button" role="tab" id={`aspect-tab-${item}`} key={item}
        ref={node => { tabs.current[index] = node; }} aria-selected={mode === item}
        aria-controls={`aspect-view-${item}`} tabIndex={mode === item ? 0 : -1}
        onClick={() => setMode(item)} onKeyDown={event => moveTab(event, index)}>
        {item === 'vedic' ? 'Vedic Aspects' : 'Western Aspects'}
      </button>)}
    </div>
    <section className="astro-panel aspect-panel" id="aspect-view-vedic" role="tabpanel" aria-labelledby="aspect-tab-vedic" hidden={mode !== 'vedic'}>
      <h2>Classical Vedic Aspects · Sign to Sign</h2>
      <p className="aspect-scroll-hint">Swipe the table to see all four columns.</p>
      <div className="aspect-table-scroll" role="region" aria-label="Vedic aspect table" tabIndex={0}>
      <table className="aspect-table vedic-aspect-table">
        <thead><tr><th scope="col">Planet</th><th scope="col">Sign occupied</th><th scope="col">Aspected planets</th><th scope="col">Aspected signs</th></tr></thead>
        <tbody>{report.vedic.map(row => <tr key={row.planet} data-planet={row.planet}>
          <th scope="row"><PlanetName planet={row.planet} />{row.retrograde && <span className="aspect-retrograde"> (R)</span>}</th>
          <td className="aspect-occupied-sign" data-source-sign={row.sign}>{row.sign}</td>
          <td>{row.aspects.length ? <div className="aspect-entries">{row.aspects.map(link =>
            <span className="aspect-entry aspect-planet-entry" key={link.target_planet} data-target={link.target_planet} data-target-sign={link.target_sign} data-aspect={link.aspect_number}>
              <span><PlanetName planet={link.target_planet} /> <span className="aspect-number">[{link.aspect_number}]</span></span>
              <small>{link.target_sign}</small>
            </span>)} </div> : <span className="aspect-empty" aria-label="No outgoing aspects">—</span>}</td>
          <td>{row.aspected_signs.length ? <div className="aspect-entries">{row.aspected_signs.map(sign =>
            <span className="aspect-entry aspect-sign-entry" key={sign.aspect_number} data-sign={sign.sign} data-aspect={sign.aspect_number}>
              {sign.sign} <span className="aspect-number">[{sign.aspect_number}]</span>
            </span>)}</div> : <span className="aspect-empty">—</span>}</td>
        </tr>)}</tbody>
      </table>
      </div>
      <p className="aspect-legend">[7] = 7th aspect · [4] = 4th aspect · [8] = 8th aspect<br />(R) = Retrograde</p>
      <details className="aspect-rules"><summary>Rules &amp; calculations</summary>
        <p>Count zodiac signs from the source planet’s sign as 1. Every classical planet aspects the 7th sign. Mars also aspects the 4th and 8th; Jupiter the 5th and 9th; Saturn the 3rd and 10th.</p>
        <p>Sign occupied shows the source planet’s natal sign. Aspected planets shows each reached planet and its natal sign. Aspected signs includes every reached sign, even when it is empty. House-system selection does not change this sign-based table. Rahu and Ketu can receive aspects; their outgoing Vedic aspects are not enabled.</p>
      </details>
    </section>
    <section className="astro-panel aspect-panel" id="aspect-view-western" role="tabpanel" aria-labelledby="aspect-tab-western" hidden={mode !== 'western'}>
      <div className="aspect-heading"><h2>Western Aspects · Planet to Planet</h2>
        <label className="aspect-orb-control">Orb tolerance (°)<input type="number" min="0" max={report.western_max_orb} step="0.1"
          value={orbInput} onChange={event => setOrbInput(event.target.value)} aria-invalid={!validOrb}
          aria-describedby={!validOrb ? 'aspect-orb-error' : 'western-aspect-rule'} /></label>
      </div>
      {!validOrb && <p id="aspect-orb-error" className="aspect-validation" role="status">Enter 0–{report.western_max_orb}°. Showing the default {report.western_default_orb}° tolerance.</p>}
      <p className="aspect-description" id="western-aspect-rule">Conjunction 0° · Sextile 60° · Square 90° · Trine 120° · Opposition 180°</p>
      <p className="aspect-scroll-hint">Swipe the table to see all four columns.</p>
      <div className="aspect-table-scroll" role="region" aria-label="Western aspect table" tabIndex={0}>
      <table className="aspect-table western-aspect-table">
        <thead><tr><th scope="col">Planet</th><th scope="col">Sign occupied</th><th scope="col">Aspected planets</th><th scope="col">Aspected signs</th></tr></thead>
        <tbody>{report.western.map(row => {
          const links = row.aspects.filter(link => link.orb <= orb + 1e-9);
          return <tr key={row.planet} data-planet={row.planet}>
            <th scope="row"><PlanetName planet={row.planet} />{row.retrograde && <span className="aspect-retrograde"> (R)</span>}</th>
            <td className="aspect-occupied-sign" data-source-sign={row.sign}>{row.sign}</td>
            <td>{links.length ? <div className="aspect-entries">{links.map(link =>
              <span className="aspect-entry aspect-western-entry" key={link.target_planet} data-target={link.target_planet} data-target-sign={link.target_sign} data-aspect={link.exact_angle} data-orb={link.orb}
                title={`Separation ${link.separation.toFixed(4)}°; ${link.aspect_name} ${link.exact_angle}°; orb ${link.orb.toFixed(4)}°`}>
                <span><PlanetName planet={link.target_planet} /> <span className="aspect-number">{link.aspect_name} [{link.exact_angle}°]</span></span>
                <small>{link.target_sign}</small>
                <small>Orb {link.orb.toFixed(2)}°</small>
              </span>)} </div> : <span className="aspect-empty" aria-label="No aspects within the selected orb">—</span>}</td>
            <td>{links.length ? <div className="aspect-entries">{links.map(link =>
              <span className="aspect-entry aspect-western-entry aspect-sign-entry" key={link.target_planet}>
                <span>{link.target_sign} <span className="aspect-number">[{link.exact_angle}°]</span></span>
                <small>{link.target_planet}</small>
              </span>)}</div> : <span className="aspect-empty">—</span>}</td>
          </tr>;
        })}</tbody>
      </table>
      </div>
      <p className="aspect-legend">Numbers in brackets show the exact aspect angle. Orb shows how far the actual angle differs.<br />(R) = Retrograde</p>
      <details className="aspect-rules"><summary>Rules &amp; calculations</summary>
        <p>Separation = the shorter angle between the two planetary longitudes, from 0° to 180°. Orb = |separation − exact aspect angle|. An aspect is shown when its orb is within {orb}°.</p>
        <p>The default tolerance is {report.western_default_orb}° for all five major aspects; you can select 0–{report.western_max_orb}°. These are mutual angular connections, so each pair appears in both planets’ rows. Aspected signs lists the signs occupied by those target planets; Western aspects are measured between planets, rather than entire signs.</p>
      </details>
    </section>
  </div>;
}
