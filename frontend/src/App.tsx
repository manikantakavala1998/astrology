import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ArrowLeft, ArrowRight, CalendarDays, ChevronRight, Clock3, LoaderCircle, MapPin, Menu, Orbit, Pencil, Settings2, ShieldCheck, Sparkle, UserRound, X } from 'lucide-react';
import type { Workspace } from './types';
import { Dashboard } from './Dashboard';
import { ServerReport } from './ServerReport';
import { BrihatJataka } from './BrihatJataka';
import { VimshottariDasha } from './VimshottariDasha';
import { PlanetaryAspects } from './PlanetaryAspects';
import { Jaimini } from './Jaimini';
import { Jaimini2 } from './Jaimini2';
import { Balas } from './Balas';
import { LaghuParashari } from './LaghuParashari';
import { BhriguExplorer } from './BhriguExplorer';
import { BhriguNavIcon } from './BhriguNavIcon';
import { formatDate, formatOffset, formatTime, navigationGroups, readWorkspace, sections } from './workspace';

function initialView(workspace: Workspace) {
  if (workspace.state.page === 'dasha') return 'dasha-detail';
  if (!workspace.state.has_chart) return 'birth';
  const hash = window.location.hash.slice(1);
  return sections.some((section) => section.id === hash) ? hash : 'chart';
}

export default function App({ initial }: { initial: Workspace }) {
  const [workspace, setWorkspace] = useState(initial);
  const [view, setView] = useState(() => initialView(initial));
  const [detail, setDetail] = useState<Workspace | null>(initial.state.page === 'dasha' ? initial : null);
  const [busy, setBusy] = useState(false);
  const [networkError, setNetworkError] = useState('');
  const [requestedDasha, setRequestedDasha] = useState<{value: string; sequence: number} | null>(null);
  const pending = useRef(false);
  const mobileMenu = useRef<HTMLDialogElement>(null);
  const formContainer = useRef<HTMLDivElement>(null);
  const state = workspace.state;
  const current = sections.find((section) => section.id === view);
  const isBirth = view === 'birth';
  const isDetail = view === 'dasha-detail';
  const isBhrigu = ['bcp', 'bsp', 'padma'].includes(view) && Boolean(state.has_chart);
  const hasCharts = state.has_chart && ['chart', 'dasha', 'divisional', 'ashtakavarga', 'bcp', 'bsp', 'padma', 'brihat-jataka', 'jaimini', 'jaimini2', 'balas', 'laghu-parashari'].includes(view);

  function navigate(id: string) {
    // A directly submitted dasha page has no parent chart/form to return to.
    // Its navigation must load a real workspace rather than an empty panel.
    if (state.page === 'dasha') {
      window.location.assign('/');
      return;
    }
    mobileMenu.current?.close();
    setNetworkError('');
    setView(id);
    window.history.replaceState(window.history.state, '', `#${id}`);
    window.scrollTo({ top: 0, behavior: 'auto' });
  }

  function openBirth(forCompatibility = false) {
    navigate('birth');
    if (forCompatibility) {
      const checkbox = formContainer.current?.querySelector<HTMLInputElement>('#include_match');
      if (checkbox) {
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
  }

  useEffect(() => {
    function restoreView() {
      const id = window.location.hash.slice(1);
      if (id === 'dasha-detail' && detail) setView(id);
      else if (id === 'birth' || sections.some((section) => section.id === id)) setView(id);
      else setView(state.has_chart ? 'chart' : 'birth');
    }
    window.addEventListener('popstate', restoreView);
    window.addEventListener('hashchange', restoreView);
    return () => {
      window.removeEventListener('popstate', restoreView);
      window.removeEventListener('hashchange', restoreView);
    };
  }, [detail, state.has_chart]);

  async function submit(event: FormEvent<HTMLElement>) {
    const form = event.target as HTMLFormElement;
    if (!(form instanceof HTMLFormElement) || form.method.toLowerCase() !== 'post') return;
    event.preventDefault();
    if (pending.current) return;
    const action = new URL(form.action, window.location.href);
    if (action.origin !== window.location.origin) return;
    const body = new FormData(form);
    pending.current = true;
    setBusy(true);
    setNetworkError('');
    try {
      const response = await fetch(action.pathname, { method: 'POST', body });
      const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
      const next = readWorkspace(doc);
      if (next.state.page === 'dasha') {
        setDetail(next);
        setView('dasha-detail');
        window.history.pushState(null, '', '#dasha-detail');
      } else {
        setWorkspace(next);
        setRequestedDasha(null);
        setDetail(null);
        navigate(next.state.has_chart ? (next.state.has_match && body.get('include_match') === 'on' ? 'compat' : 'chart') : 'birth');
      }
      window.scrollTo({ top: 0, behavior: 'auto' });
    } catch (error) {
      setNetworkError(error instanceof Error ? error.message : 'Your chart could not be loaded. Please try again.');
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }

  function backToDasha() {
    if (state.page === 'dasha') {
      if (window.history.length > 1) window.history.back();
      else window.location.assign('/');
    } else navigate('dasha');
  }

  function renderSidebar() {
    return <>
      <a className="brand" href="/" aria-label="Vedic Astro home"><Sparkle aria-hidden="true" /><span>Vedic Astro</span></a>
      <nav aria-label="Astrology sections">
        {navigationGroups.map((group) => <div className="nav-group" data-group={group.id} key={group.id}>
          {group.label && <p className="nav-group-label">{group.label}</p>}
          {sections.filter((section) => section.group === group.id).map((section) => <button key={section.id} type="button" className={`nav-item ${view === section.id || (isBirth && section.id === 'chart') ? 'is-active' : ''}`} aria-current={view === section.id || (isBirth && section.id === 'chart') ? 'page' : undefined} onClick={() => section.id === 'chart' && !state.has_chart ? openBirth() : navigate(section.id)}>
            <span className="nav-emoji" aria-hidden="true"><BhriguNavIcon id={section.id} /></span><span className="nav-label">{section.label}</span>
            {section.pending && <span className="nav-pending">Pending</span>}
            {view === section.id && <ChevronRight size={13} className="nav-chevron" aria-hidden="true" />}
          </button>)}
        </div>)}
      </nav>
      <div className="sidebar-footer"><ShieldCheck size={15} aria-hidden="true" /><div>Private by nature.<span>Computed locally · Works offline</span></div></div>
    </>;
  }

  return <div className={`app-shell ${busy ? 'is-busy' : ''} ${hasCharts ? 'compact-chart-view' : ''} ${isBhrigu ? 'bhrigu-preview-view' : ''}`} onSubmitCapture={submit}>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <aside className="desktop-sidebar">{renderSidebar()}</aside>
    <dialog ref={mobileMenu} className="mobile-dialog" aria-label="Navigation">
      <button className="menu-close" type="button" aria-label="Close navigation" onClick={() => mobileMenu.current?.close()}><X size={20} /></button>
      {renderSidebar()}
    </dialog>

    <div className="app-main min-w-0">
      <div className="mobile-toolbar"><button type="button" className="icon-button" aria-label="Open navigation" onClick={() => mobileMenu.current?.showModal()}><Menu size={21} /></button><span>Vedic Astro</span><button type="button" className="icon-button" aria-label="Edit birth details" onClick={() => openBirth()}><Pencil size={18} /></button></div>

      <header className={`celestial-header ${isBirth ? 'birth-header' : ''}`}>
        <div className="hero-copy"><p className="eyebrow">{isBirth ? 'THE MOMENT THAT MADE YOU' : isDetail ? 'VIMSHOTTARI DASHA' : current?.label.toUpperCase()}</p>
          <h1>{isBirth ? 'Every chart begins with you.' : isDetail ? 'Explore the smaller chapters.' : isBhrigu ? 'Your year & dasha explorer.' : current?.title}</h1>
          <p className="hero-description">{isBirth ? 'Your birth details. A whole sky to discover.' : isDetail ? 'Antardasha → Pratyantardasha → Sookshma → Prana' : isBhrigu ? 'Birth-based houses, signs, aspects and your active five-level dasha.' : current?.description}</p>
        </div>
        {state.birth_data?.name && !isBirth && <span className="profile-label"><span className="profile-avatar">{state.birth_data.name.charAt(0).toUpperCase()}</span>{state.birth_data.name}</span>}
      </header>

      <main id="main-content" className="workspace-content" aria-busy={busy}>
        {state.birth_data && !isBirth && <div className="birth-ribbon">
          {isBhrigu && <span className="bhrigu-name-pill"><UserRound size={17} aria-hidden="true" />{state.birth_data.name || 'Your chart'}</span>}
          <span><CalendarDays size={15} aria-hidden="true" />{isBhrigu ? state.birth_data.birth_date.split('-').reverse().join('/') : formatDate(state.birth_data.birth_date)}</span>
          <span><Clock3 size={15} aria-hidden="true" />{formatTime(state.birth_data.birth_time)}</span>
          <span className="place-ribbon"><MapPin size={15} aria-hidden="true" /><span>{state.resolved_place || `${state.birth_data.latitude.toFixed(4)}°, ${state.birth_data.longitude.toFixed(4)}°`}</span></span>
          <span>{formatOffset(state.birth_data.utc_offset_hours)}</span>
          <span className="setting-ribbon"><Settings2 size={15} aria-hidden="true" />{state.birth_data.ayanamsha}</span>
          <span className="setting-ribbon node-setting"><Orbit size={15} aria-hidden="true" />{state.birth_data.node_type} nodes</span>
          <span className="setting-ribbon house-setting">{state.birth_data.house_system.replaceAll('_', ' ')}</span>
          <button type="button" className="primary-button ribbon-edit" onClick={() => openBirth()}><Pencil size={14} aria-hidden="true" />Edit birth details</button>
        </div>}

        {networkError && <div className="app-alert" role="alert">{networkError}</div>}
        {busy && <div className="busy-notice" role="status"><LoaderCircle size={18} aria-hidden="true" />{isBirth ? 'Calculating your chart locally…' : 'Loading the full breakdown…'}</div>}

        <div ref={formContainer} className="birth-workspace" hidden={!isBirth}>
          {state.page === 'workspace' && <>
            <div className="form-intro"><span className="quiet-label">South Indian birth chart</span><span className="privacy-label"><ShieldCheck size={14} aria-hidden="true" />Your details stay on this device</span></div>
            <ServerReport html={workspace.formHtml} className="birth-report" />
            {state.has_chart && <button className="secondary-button mt-5" type="button" onClick={() => navigate('chart')}><ArrowLeft size={16} aria-hidden="true" />Return to your chart</button>}
          </>}
        </div>

        {state.has_chart && <>
          <div hidden={view !== 'chart'} id="panel-chart"><Dashboard state={state} navigate={navigate} /></div>
          {Object.entries(workspace.sections).filter(([id]) => id !== 'chart').map(([id, html]) => <section key={id} id={`panel-${id}`} className="analysis-section" hidden={view !== id} aria-label={sections.find((section) => section.id === id)?.label}>
                {id === 'dasha' && state.vimshottari
                  ? <VimshottariDasha key={`${state.birth_data?.birth_date}-${state.birth_data?.birth_time}-${state.birth_data?.latitude}-${state.birth_data?.longitude}-${state.birth_data?.ayanamsha}`} state={state} active={view === id} requestedDate={requestedDasha} />
                  : (id === 'bcp' || id === 'bsp' || id === 'padma') && state.bhrigu
                  ? <BhriguExplorer key={`${id}-${JSON.stringify(state.birth_data)}`} method={id} state={state} report={state.bhrigu} active={view === id} openDasha={value => {setRequestedDasha(previous => ({value, sequence: (previous?.sequence ?? 0) + 1})); navigate('dasha');}} />
                  : id === 'brihat-jataka' && state.brihat_jataka
                  ? <BrihatJataka report={state.brihat_jataka} birthData={state.birth_data} ascendantSign={state.ascendant!.sign} active={view === id} />
                  : id === 'jaimini' && state.jaimini
                  ? <Jaimini key={JSON.stringify(state.birth_data)} state={state} report={state.jaimini} active={view === id} />
                  : id === 'jaimini2' && state.jaimini2
                  ? <Jaimini2 key={JSON.stringify(state.birth_data)} state={state} report={state.jaimini2} active={view === id} />
                  : id === 'aspects' && state.aspect_tables
                  ? <PlanetaryAspects report={state.aspect_tables} />
                  : id === 'balas' && state.balas
                  ? <Balas key={JSON.stringify(state.birth_data)} report={state.balas} active={view === id} />
                  : id === 'laghu-parashari' && state.laghu_parashari
                  ? <LaghuParashari key={JSON.stringify(state.birth_data)} report={state.laghu_parashari} state={state} />
                  : <ServerReport html={html} />}
          </section>)}
        </>}

        {!isBirth && !isDetail && (!state.has_chart || (view === 'compat' && !state.has_match)) && <section className="astro-panel empty-section">
          <span className="empty-emoji" aria-hidden="true">{current?.emoji ?? '🔮'}</span>
          <h2>{view === 'compat' ? 'Bring a second chart into the picture.' : 'Your chart comes first.'}</h2>
          <p>{view === 'compat' ? 'Add a second person’s birth details to see the complete Ashtakoot and Mangal Dosha report.' : 'Enter your birth details to explore this part of your chart.'}</p>
          <button type="button" className="primary-button" onClick={() => openBirth(view === 'compat')}>{view === 'compat' ? 'Add second person' : 'Enter birth details'}<ArrowRight size={16} aria-hidden="true" /></button>
        </section>}

        {isDetail && detail && <section className="analysis-section dasha-workspace">
          <button type="button" className="secondary-button mb-5" onClick={backToDasha}><ArrowLeft size={16} aria-hidden="true" />Back to your dasha</button>
          <ServerReport html={detail.detailHtml} />
        </section>}

        <footer className="app-footer"><span><Sparkle size={13} aria-hidden="true" /> Vedic Astro</span><span>South Indian charts <span className="footer-divider">·</span> Local &amp; offline</span></footer>
      </main>
    </div>
  </div>;
}
