export interface Karaka {
  role: string; name: string; planet: string; degree: number; effective_degree: number;
  sign: string; navamsa_sign: string; meaning: string; calculation: string;
}
export interface JaiminiPeriod { sign: string; start: string; end: string; years: number; cycle: number; rule: string }
export type PredictionTone = 'supportive' | 'challenging' | 'mixed' | 'neutral';
export interface PredictionCondition { code: string; topic: string; present: boolean; tone: PredictionTone; summary: string; evidence: string; rule: string }
export interface PredictionAssessment { tone: PredictionTone; summary: string; supportive: number; challenging: number; conditions: PredictionCondition[] }
export interface Jaimini2PredictionModule extends PredictionAssessment {
  id: string; title: string; basis: 'D1' | 'D9'; anchor: string; facts: { label: string; value: string }[];
  notes?: string; calculation?: string;
  groups?: (PredictionAssessment & { planet: string; sign: string })[];
  houses?: { house: number; sign: string; occupants: string }[];
  padas?: (JaiminiReport['padas'][number] & { occupants: string; aspecting: string })[];
}
export interface JaiminiSystem {
  code: string; name: string; method: string; year_days: number; periods: JaiminiPeriod[];
  max_levels: number; child_orders: Record<string, string[]>; unavailable: string | null;
  duration_rows: { sign: string; years: number; rule: string }[];
  book_number?: number; basis?: 'D1' | 'D9'; worksheet?: { factor: string; value: string }[];
  activation_rules?: Record<string, { topic: string; present: boolean; summary: string; evidence: string; rule: string }[]>;
  subdivision_rule?: string; subdivision_status?: string;
  predictions?: Record<string, PredictionAssessment & { basis: 'D1' | 'D9'; scope: string }>;
}
export interface JaiminiAdvanced {
  brahma: string | null; brahma_seed: string; brahma_candidates: { planet: string; sign: string; eligible: boolean }[];
  brahma_rule: string; rudra: string; secondary_rudra: string[]; rudra_rule: string;
  trishoola: string[]; maheswara: string; maheswara_rule: string;
  longevity_pairs: { pair: string; first: string; second: string; first_type: string; second_type: string; category: string }[];
  traditional_category: string; category_rule: string; sthira_karakas: { meaning: string; planet: string }[];
}
export interface JaiminiScheme {
  karakas: Karaka[]; karakamsha: string; swamsha: string; advanced: JaiminiAdvanced;
  yogas: { name: string; present: boolean; rule: string; evidence: string }[];
  readings: { topic: string; planet: string; summary: string; evidence: string; rule: string }[];
}
export interface JaiminiReport {
  schemes: Record<string, JaiminiScheme>;
  aspects: { planet: string; sign: string; retrograde: boolean; aspected_signs: string[]; aspected_planets: { planet: string; sign: string }[] }[];
  padas: { house: number; code: string; name: string; sign: string; source_sign: string; lord: string; lord_sign: string; count: number; exception: boolean; calculation: string }[];
  argala: { target: string; argala_house: number; argala_sign: string; argala_planets: string[]; blocking_house: number; blocking_sign: string; blocking_planets: string[]; status: string; reverse: boolean; special: boolean; calculation: string }[];
  strengths: { sign: string; lord: string; metrics: number[]; occupants: string[] }[];
  lagnas: { code: string; name: string; longitude: number; sign: string; degree: number; calculation: string; sunrise?: string }[];
  dasha_systems: JaiminiSystem[];
  upapada: { sign: string; lord: string; second_sign: string; second_lord: string; occupants: string[]; second_occupants: string[]; aspecting: string[]; rule: string };
  rules: Record<string, string>;
}

export interface Jaimini2Report extends JaiminiReport {
  schemes: Record<string, Omit<JaiminiScheme, 'yogas'> & { yogas: (JaiminiScheme['yogas'][number] & {
    kind: 'yogada' | 'kevala' | 'other'; planets: string[];
    variant?: 'multi_chart' | 'sign_aspect' | 'moon_dispositor';
    matched_charts?: string[];
    connections?: { sign: string; house: number; target: string }[];
  })[] }>;
  strengths: (JaiminiReport['strengths'][number] & { rank: number })[];
  author: string; edition: string; warnings: string[];
  navamsa_aspects: { planet: string; sign: string; aspected_signs: string[] }[];
  upapada_variants: { name: string; pithru: string; source: string; lord: string; sign: string; calculation: string }[];
  predictions: { modules: Jaimini2PredictionModule[]; upapada_readings: Jaimini2PredictionModule[]; assessment_rule: string };
}
