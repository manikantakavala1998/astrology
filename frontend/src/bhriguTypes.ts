import type { PlanetPosition, VimshottariPeriod } from './types';
export interface BcpYear {
  age: number; start: string; end: string; cycle_number: number; position_in_cycle: number;
  house_from_lagna: number; sign_from_lagna: string; planets_from_lagna: string[]; year_lord: string;
  cycle_ruler: string | null; house_from_cycle_ruler: number | null; sign_from_cycle_ruler: string | null;
  planets_from_cycle_ruler: string[]; cycle_d1_house: number | null;
  cycle_sign_lord: string | null;
}
export interface PadmaYear {
  age: number; start_date: string; end_date: string; house_from_lagna: number; sign: string;
  year_lord: string; year_lord_dwadasamsa_sign: string; superimposed_house_from_lagna: number; is_badhaka: boolean;
}
export interface BhriguTarget { offset: number; house: number; sign: string; planets: string[]; role: string }
export interface BspRule {
  rule_number: number; planet: string; age: number; house_offset: number; special_status: boolean;
  special_status_reasons: string[]; targets: BhriguTarget[]; summary: string;
}
export interface BhriguReport {
  bcp: BcpYear[]; bsp: BspRule[]; padma: PadmaYear[];
  planets: PlanetPosition[];
  permanent: {rule_number: number; title: string; house_from_lagna: number; sign: string; planets_in_house: string[]; note: string}[];
  aries: {house_from_lagna: number; planets_in_house: string[]} | null;
  venus: {venus_house_from_lagna: number; venus_sign: string; conjunct_planets: string[]; conjunct_planet_lordships: Record<string, number[]>;
    twelfth_from_venus_house_from_lagna: number; twelfth_from_venus_sign: string};
  longevity: {rule: string; reason: string; flagged_houses: {label: string; house_from_lagna: number; sign: string; ages: number[]}[]};
  badhakas: {chart: string; ascendant_sign: string; modality: string; badhaka_house_from_lagna: number; badhaka_sign: string; badhakesh: string; d1_house: number}[];
  badhaka_connections: {sign: string; house: number; kind: string; reason: string; planet: string}[];
  aspects: (BhriguTarget & {planet: string; source_sign: string; source_house: number})[];
  vimshottari: {periods: VimshottariPeriod[]}; dasha_year_days: number; dasha_years: Record<string, number>;
  padma_year_rule: string; coverage: string;
}
