export interface BalaDetail {
  name: string; calculation: string; value: number | null; unit: string;
}
export interface BalaRow {
  key: string; label: string; planet: string; value: number;
  required?: number; status?: string;
  details: BalaDetail[];
  inputs: { name: string; value: string }[];
  tables: { title: string; columns: string[]; rows: (string | number)[][] }[];
}
export interface BalaView {
  id: string; name: string; description: string; group: string; unit: string;
  formula: string; notes: string[]; rows: BalaRow[]; minimum: number; maximum: number;
}
export interface BalaReport { views: BalaView[]; conversion: string }
