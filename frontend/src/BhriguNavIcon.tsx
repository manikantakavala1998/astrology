import { Home, CalendarDays, Network, ChartNoAxesColumn, PanelsTopLeft, Grip, CircleDot, ScrollText, Flower2, BookOpen, Hourglass, Orbit, Heart, Sparkles, TriangleAlert, NotebookText, Combine, Wrench, Telescope } from 'lucide-react';

// Every nav section in workspace.ts needs an entry here, because the sidebar
// always renders these icons now. A missing key silently falls back to
// Sparkles, which reads as "unstyled" rather than as a deliberate choice.
const icons: Record<string, typeof Home> = {chart: Home, panchanga: CalendarDays, aspects: Telescope, balas: ChartNoAxesColumn,
  divisional: PanelsTopLeft, ashtakavarga: Grip, bcp: CircleDot, bsp: ScrollText, padma: Flower2,
  'laghu-parashari': BookOpen, 'brihat-jataka': BookOpen, jaimini: Network, jaimini2: BookOpen, dasha: Hourglass, shani: Orbit,
  dosha: TriangleAlert, compat: Heart, 'classic-predictions': NotebookText, yogas: Combine, tools: Wrench};
export function BhriguNavIcon({id}: {id: string}) {const Icon = icons[id] ?? Sparkles; return <Icon size={20} aria-hidden="true" />;}
