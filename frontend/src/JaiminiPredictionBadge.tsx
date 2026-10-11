import type { PredictionTone } from './jaiminiTypes';

export const predictionLabels: Record<PredictionTone, string> = {
  supportive: 'Supportive · good indications', challenging: 'Challenging · difficult indications',
  mixed: 'Mixed indications', neutral: 'No clear indication',
};
export function PredictionBadge({ tone, compact = false }: { tone: PredictionTone; compact?: boolean }) {
  const short = { supportive: 'Supportive', challenging: 'Challenging', mixed: 'Mixed', neutral: 'No clear result' };
  return <span className={`jaimini2-prediction-badge is-${tone}`} title={predictionLabels[tone]}>{compact ? short[tone] : predictionLabels[tone]}</span>;
}
