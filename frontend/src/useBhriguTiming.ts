import { useEffect, useMemo, useState } from 'react';
import type { VimshottariPeriod } from './types';
import { civilTime } from './brihatPeriods';

export const dashaLevels = ['Mahadasha', 'Antardasha', 'Pratyantardasha', 'Sookshma', 'Prana'];
const keyOf = (p: VimshottariPeriod) => `${p.planet}|${p.start}|${p.end}`;

// Resolve just the active branch, never the full 59,049-period Prana tree.
export function useBhriguTiming(periods: VimshottariPeriod[], instant: string, active: boolean) {
  const [branches, setBranches] = useState<Record<string, VimshottariPeriod[]>>({});
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const plan = useMemo(() => {
    const path: VimshottariPeriod[] = [];
    let rows = periods;
    let missing: VimshottariPeriod | null = null;
    const when = civilTime(instant);
    for (let level = 0; level < 5; level++) {
      const parent = rows.find(p => civilTime(p.start) <= when && when < civilTime(p.end));
      if (!parent) break;
      path.push(parent);
      if (level === 4) break;
      const children = parent.sub_periods.length ? parent.sub_periods : branches[keyOf(parent)];
      if (!children) { missing = parent; break; }
      rows = children;
    }
    return {path, missing};
  }, [periods, instant, branches]);
  const missingKey = plan.missing ? keyOf(plan.missing) : '';
  useEffect(() => {
    if (!active || !plan.missing) return;
    const parent = plan.missing;
    const key = keyOf(parent);
    const controller = new AbortController();
    setError('');
    (async () => {
      try {
        const response = await fetch('/api/vimshottari/subperiods', {
          method: 'POST', headers: {'Content-Type': 'application/json'}, signal: controller.signal,
          body: JSON.stringify({planet: parent.planet, start: parent.start, end: parent.end}),
        });
        if (!response.ok) throw new Error('This dasha branch could not be calculated. Please retry.');
        const data = await response.json() as {periods: VimshottariPeriod[]};
        if (!controller.signal.aborted) setBranches(previous => ({...previous, [key]: data.periods}));
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Could not load the dasha branch.');
      }
    })();
    return () => controller.abort();
    // missingKey identifies all request data; changing the instant within one
    // parent should neither duplicate the request nor reset the branch cache.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, missingKey, retry]);
  return {path: plan.path, pending: Boolean(plan.missing), error: missingKey ? error : '', retry: () => setRetry(n => n + 1)};
}
