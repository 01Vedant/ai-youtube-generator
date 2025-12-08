import React, { useEffect, useMemo, useRef, useState } from 'react';
import { getJobActivity } from '@/lib/api';
type ApiEvent = { id: string; type: string; message?: string; created_at?: string };
import { titleFor, detailsFor, ActivityEvent } from '@/lib/activityMap';
import { formatRelative, formatClock } from '@/lib/time';

type Props = {
  jobId: string;
  pollMs?: number;
  className?: string;
};

const DEFAULT_POLL_MS = 3000;

function mergeEvents(existing: ActivityEvent[], incoming: ActivityEvent[]): ActivityEvent[] {
  const key = (e: ActivityEvent) => `${e.ts}|${e.type}`;
  const map = new Map(existing.map((e) => [key(e), e]));
  for (const ev of incoming) {
    const k = key(ev);
    if (!map.has(k)) map.set(k, ev);
  }
  const merged = Array.from(map.values()).sort((a, b) => Date.parse(a.ts) - Date.parse(b.ts));
  return merged;
}

export const JobTimeline: React.FC<Props> = ({ jobId, pollMs = DEFAULT_POLL_MS, className }) => {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  const timerRef = useRef<number | null>(null);

  const clearTimer = (): void => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const fetchOnce = async (): Promise<void> => {
    try {
      const res = await getJobActivity(jobId, 500);
      const incoming: ActivityEvent[] = (res.events || []).map((e: any) => ({
        ts: e.ts_iso ?? e.ts,
        type: String(e.event_type || e.type || ''),
        payload: (e.meta as Record<string, unknown>) || {},
      }));
      setEvents((prev) => mergeEvents(prev, incoming));
      setError(null);
      setLoading(false);
      setLastUpdated(Date.now());
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load activity';
      setError(msg);
      setLoading(false);
    }
  };

  const scheduleNext = (): void => {
    clearTimer();
    timerRef.current = window.setTimeout(() => {
      void fetchOnce().then(scheduleNext);
    }, pollMs);
  };

  useEffect(() => {
    setEvents([]);
    setLoading(true);
    setError(null);
    void fetchOnce().then(scheduleNext);
    return () => clearTimer();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  const hasMany = events.length > 300;

  const list = useMemo(() => events, [events]);

  const renderItem = (ev: ActivityEvent, idx: number): React.ReactNode => {
    const t = ev.type.toLowerCase();
    const title = titleFor(t);
    const details = detailsFor(t, ev.payload);
    // Icon selection via emoji fallback to avoid new deps; lucide-react optional
    let icon = 'ℹ️';
    let color = 'text-slate-700 border-slate-200';
    if (t.includes('started')) { icon = '🎬'; color = 'text-blue-700 border-blue-200'; }
    if (t.includes('completed') || t === 'job_completed') { icon = '✅'; color = 'text-green-700 border-green-200'; }
    if (t === 'job_failed') { icon = '⚠️'; color = 'text-red-700 border-red-200'; }
    if (t === 'artifact_uploaded') { icon = '⤴️'; color = 'text-slate-700 border-slate-200'; }

    return (
      <li key={`${ev.ts}|${ev.type}|${idx}`} className="relative pl-8 py-2">
        <span className={`absolute left-0 top-2 text-sm ${color}`}>{icon}</span>
        <div className={`border rounded px-3 py-2 ${color.replace('text-', 'border-')}`}>
          <div className="flex items-center justify-between">
            <div className="font-medium">{title}</div>
            <div className="text-xs text-slate-500" title={formatClock(ev.ts)}>{formatRelative(ev.ts)}</div>
          </div>
          {details && <div className="text-sm text-slate-600 mt-1">{details}</div>}
        </div>
      </li>
    );
  };

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold">Activity</h3>
        <div className="flex items-center gap-2">
          {lastUpdated && (
            <span className="text-xs text-slate-500">Last updated {new Date(lastUpdated).toLocaleTimeString()}</span>
          )}
          <button className="btn-secondary" onClick={() => void fetchOnce()}>Refresh</button>
        </div>
      </div>
      {loading && <div className="text-sm text-slate-600">Loading activity…</div>}
      {error && (
        <div className="text-sm text-red-700 border border-red-200 rounded px-3 py-2">
          {error} <button className="underline" onClick={() => void fetchOnce()}>Retry</button>
        </div>
      )}
      {!loading && !error && list.length === 0 && (
        <div className="text-sm text-slate-600">No activity yet. This timeline will populate as your render progresses.</div>
      )}
      {list.length > 0 && (
        <div className="relative">
          <div className="absolute left-2 top-0 bottom-0 w-px bg-slate-200" aria-hidden="true"></div>
          <ul className="list-none m-0 p-0">
            {list.map((ev, i) => renderItem(ev, i))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default JobTimeline;