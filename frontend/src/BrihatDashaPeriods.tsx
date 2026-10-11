import { useState } from 'react';
import type { Dasha, Period } from './BrihatJataka';
import type { Bootstrap } from './types';
import type { Predictions } from './BrihatPredictions';
import { formatDate, formatTime, formatOffset } from './workspace';
import { civilTime, durationLabel, nowAtOffset, qualityLabel, simpleTerms } from './brihatPeriods';

export function BrihatDashaPeriods({ predictions, dasha, birthData, settingsChanged, onTimeline, mode = 'ayurdaya', naturalPeriods = [] }: {
  predictions: Predictions; dasha: Dasha; birthData: Bootstrap['birth_data']; settingsChanged: boolean;
  onTimeline?: () => void;
  mode?: 'ayurdaya' | 'natural'; naturalPeriods?: Period[];
}) {
  const utcOffset = birthData?.utc_offset_hours ?? 0;
  const [when, setWhen] = useState(() => nowAtOffset(utcOffset));
  const time = civilTime(when);
  const periods = mode === 'natural' ? naturalPeriods : dasha.periods;
  const current = periods.find(period => civilTime(period.start) <= time && time < civilTime(period.end));
  const sub = current?.sub_periods?.find(period => civilTime(period.start) <= time && time < civilTime(period.end));
  const used = dasha.worksheet.options;
  const first = periods[0], last = periods.at(-1);
  function periodReading(period: Pick<Period, 'lord' | 'start' | 'end' | 'quality'>, kind: string) {
    const theme = predictions.period_themes.find(row => row.lord === period.lord);
    const years = (civilTime(period.end) - civilTime(period.start)) / (360 * 86400000);
    return <article className="bj-period-reading" data-period-kind={kind} data-lord={period.lord}>
      <p className="quiet-label">{kind === 'Main period' ? 'MAIN DASHA · OVERALL PHASE' : 'ANTARDASHA · SHORTER PHASE'}</p>
      <h3>{period.lord === 'Lagna' ? 'Lagna (Ascendant)' : period.lord}{period.lord === 'Lagna' && <small>{predictions.lagna_lord} rules your rising sign</small>}</h3>
      <div className="bj-period-date-pair"><div><span>Starts</span><strong>{formatDate(period.start)}</strong></div><div><span>Ends</span><strong>{formatDate(period.end)}</strong></div></div>
      <p className="hint">Length: {durationLabel(years)} · calculated with 360-day years</p>
      {period.quality && <p className="hint">Chart condition: {qualityLabel(period.quality)}</p>}
      {theme && <><p><strong>Possible opportunities</strong><br />{simpleTerms(theme.supportive)}</p><p><strong>Things that may need care</strong><br />{simpleTerms(theme.challenging)}</p></>}
    </article>;
  }
  return <section className="astro-panel bj-prediction-timing"><div className="bj-prediction-heading"><div><h2>⏳ {mode === 'natural' ? 'Your Naisargika dasha' : 'Your Brihat Jataka dashas'}</h2><p className="hint">{mode === 'natural' ? 'Natural age sequence · fixed planet durations from birth' : <>{used.model === 'amsa' ? 'Amsa · based on divisional placement' : 'Pinda · based on distance from exaltation'} · starts with {used.seed === 'Lagna' ? 'the Ascendant' : used.seed}</>}</p></div><label className="bj-date-field">Reading date & time<input type="datetime-local" value={when} step="1" onChange={event => setWhen(event.target.value)} /><small>{formatOffset(utcOffset)} · birth-location time</small></label></div>
    <p>{mode === 'natural' ? 'Naisargika dasha follows the natural planet sequence from birth. Choose a date to see its ruling planet.' : 'The main dasha is a longer phase. The antardasha is a shorter phase within it. Choose a date to see which planets rule that time.'}</p>
    {settingsChanged && mode !== 'natural' && <p role="status" className="hint">Dasha settings have changed. Calculate the worksheet in Dashas to update these periods.</p>}
    {current ? <div className="bj-period-readings">{periodReading(current, 'Main period')}{sub && periodReading(sub, 'Subperiod')}</div> : <p className="bj-period-empty" role="status">{when ? 'This date is outside the calculated worksheet.' : 'Choose a date and time to view the period.'} {first && last && <>Available range: {formatDate(first.start)} → {formatDate(last.end)}.</>}</p>}
    <details className="bj-timing-rule"><summary>How these dates are calculated</summary>{mode === 'natural' ? <p>Start at your birth date and time. Use Moon 1, Mars 2, Mercury 9, Venus 20, Jupiter 18, Sun 20, and Saturn 50 years. End date = start date + years × 360 days. Each following planet starts at the previous planet's end date.</p> : <ol><li>Calculate each planet's years from your birth longitude using the selected Amsa or Pinda method.</li><li>Apply the strength multiplier and the relevant reductions.</li><li>Arrange the periods from the selected starting point and planetary order.</li><li>Add each final duration to the previous end date. One calculation year is 360 days.</li><li>Divide each main period into subperiods using the planets' relative positions and normalized shares.</li></ol>}</details>
    <p className="hint">These are conditional chart themes. Exact events require more than the period's ruling planet.</p>
    {onTimeline && <button type="button" className="secondary-button" onClick={onTimeline}>View full dasha timeline →</button>}
    {birthData && <p className="hint bj-dasha-birth">Calculated from {formatDate(birthData.birth_date)}, {formatTime(birthData.birth_time)}.</p>}
  </section>;
}
