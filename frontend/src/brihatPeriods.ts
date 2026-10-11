// Worksheet times are civil times at the birth location. Representing them
// numerically must not apply the browser's timezone or daylight-saving rules.
export function civilTime(value: string) {
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d+))?)?$/);
  return match ? Date.UTC(+match[1], +match[2] - 1, +match[3], +match[4], +match[5], +(match[6] ?? 0)) + Number(`0.${match[7] ?? '0'}`) * 1000 : NaN;
}
export function nowAtOffset(offset: number) {
  return new Date(Date.now() + offset * 3600000).toISOString().slice(0, 16);
}
export function qualityLabel(value: string) {
  const labels: Record<string, string> = { Uttama: 'Higher positional support', Madhyama: 'Medium positional support',
    Adhama: 'Lower positional support', Arohini: 'Moving toward exaltation', Avarohini: 'Moving away from exaltation',
    Anishta: 'Adverse positional condition', 'Misraphala (mixed)': 'Mixed sign and D9 support',
    'At deep exaltation; Sampurna if powerful': 'At the strongest exaltation point; full result requires sufficient strength',
    'At deep debilitation; Rikta if weak': 'At the weakest debilitation point; the result also depends on strength' };
  return labels[value] ?? value;
}
export function durationLabel(years: number) {
  const days = Math.round(years * 360);
  const parts = [[Math.floor(days / 360), 'year'], [Math.floor(days % 360 / 30), 'month'], [days % 30, 'day']] as const;
  return parts.filter(([value]) => value > 0).map(([value, unit]) => `${value} ${unit}${value === 1 ? '' : 's'}`).join(', ') || 'Less than one day';
}
export function simpleTerms(value: string) {
  return value.replaceAll('ministerial', 'advisory').replaceAll('command', 'leadership').replaceAll('state work', 'government-related work')
    .replaceAll('ritual service', 'religious service').replaceAll('ingenuity', 'problem-solving skill').replaceAll('Bhava', 'house')
    .replaceAll('Sthana', 'Placement support').replaceAll('Dig:', 'Direction support:').replaceAll('Chesta:', 'Motion support:')
    .replaceAll('Paksha', 'Moon phase').replaceAll('commentary cancellation', 'cancellation');
}
