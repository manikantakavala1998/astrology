export interface ChartCell {
  sign: string;
  house: number;
  is_ascendant: boolean;
  direction: string;
  element_symbol: string;
  planets: { code: string; retrograde: boolean; dignity_suffix: string; color_class: string; natal_degree: number }[];
}

export interface PlanetPosition {
  planet: string;
  sign: string;
  degree_in_sign: number;
  house: number;
  nakshatra: { name: string; pada: number };
  dignity: string;
  retrograde: boolean;
}

export interface Lord { house: number; sign: string; lord: string }

export interface VedicAspectLink { target_planet: string; target_sign: string; aspect_number: number }
export interface WesternAspectLink {
  target_planet: string; target_sign: string; aspect_name: string; exact_angle: number; separation: number; orb: number;
}
export interface AspectTables {
  vedic: { planet: string; sign: string; retrograde: boolean; aspects: VedicAspectLink[]; aspected_signs: { sign: string; aspect_number: number }[] }[];
  western: { planet: string; sign: string; retrograde: boolean; aspects: WesternAspectLink[] }[];
  western_default_orb: number;
  western_max_orb: number;
}

export interface VimshottariPeriod {
  planet: string; start: string; end: string; sub_periods: VimshottariPeriod[];
}

export interface Bootstrap {
  laghu_parashari?: import('./LaghuParashari').LaghuReport;
  brihat_jataka?: BrihatReport;
  jaimini?: import('./jaiminiTypes').JaiminiReport;
  jaimini2?: import('./jaiminiTypes').Jaimini2Report;
  balas?: import('./balaTypes').BalaReport;
  bhrigu?: import('./bhriguTypes').BhriguReport;
  vimshottari?: { periods: VimshottariPeriod[] };
  aspect_tables?: AspectTables;
  page: 'workspace' | 'dasha';
  form_values?: Record<string, string>;
  error: string | null;
  has_chart?: boolean;
  has_match?: boolean;
  resolved_place?: string | null;
  dasha_lord?: string | null;
  birth_data?: {
    name: string; birth_date: string; birth_time: string; latitude: number;
    longitude: number; utc_offset_hours: number; ayanamsha: string;
    node_type: string; house_system: string;
  };
  ascendant?: { sign: string; degree_in_sign: number };
  planets?: PlanetPosition[];
  panchanga?: {
    tithi: { name: string }; paksha: string; vara: string;
    nakshatra: { name: string }; yoga: { name: string }; karana: { name: string };
    hora?: { lord: string; index: number; phase: 'Day' | 'Night'; start: string; end: string;
      duration_minutes: number; sunrise: string; sunset: string; next_sunrise: string; sunrise_day_lord: string } | null;
  };
  grids?: Record<string, (ChartCell | null)[][]>;
  current_dasha?: { major: string; minor: string | null; start: string; end: string; as_of: string } | null;
  kendra_lords?: Lord[];
  trikona_lords?: Lord[];
}

export interface Workspace {
  state: Bootstrap;
  formHtml: string;
  sections: Record<string, string>;
  detailHtml: string;
}

export interface Section {
  id: string; label: string; emoji: string; group: 'chart' | 'bhrigu' | 'brihat' | 'jaimini' | 'analysis' | 'more';
  title: string; description: string; pending?: boolean;
}
import type { BrihatReport } from './BrihatJataka';

