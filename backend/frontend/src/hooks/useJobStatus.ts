import { useCallback, useEffect, useRef, useState } from 'react';
import { getStatus } from '@/lib/api';
import type { JobStatus } from '@/types/api';

type State = {
  status: JobStatus | null;
  data: JobStatus | null; // alias for clarity
  error: string | null;
  isStale: boolean;
  lastUpdated: number | null;
};

const MIN_DELAY_MS = 2000; // 2s
const MAX_DELAY_MS = 15000; // 15s
const JITTER_PCT = 0.2; // ±20%
const LEASE_SEC = 300; // defaults; used to compute staleness threshold (2 * LEASE_SEC)

function withJitter(ms: number): number {
  const jitter = ms * JITTER_PCT;
  const min = ms - jitter;
  const max = ms + jitter;
  return Math.floor(min + Math.random() * (max - min));
}

export function useJobStatus(jobId: string): {
  status: JobStatus | null;
  data: JobStatus | null;
  error: string | null;
  refresh: () => void;
  isStale: boolean;
  lastUpdated: number | null;
} {
  const [state, setState] = useState<State>({ status: null, data: null, error: null, isStale: false, lastUpdated: null });
  const delayRef = useRef<number>(MIN_DELAY_MS);
  const timerRef = useRef<number | null>(null);
  const prevStateRef = useRef<JobStatus | null>(null);

  const clearTimer = (): void => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const computeIsStale = (payload: JobStatus | null): boolean => {
    try {
      if (!payload) return false;
      if (payload.state !== 'running') return false;
      const hb = (payload as any).heartbeat_at as string | undefined; // present in backend payload
      if (!hb) return false;
      const nowMs = Date.now();
      const hbMs = Date.parse(hb);
      if (!Number.isFinite(hbMs)) return false;
      const thresholdMs = 2 * LEASE_SEC * 1000; // ~600s default
      return nowMs - hbMs > thresholdMs;
    } catch {
      return false;
    }
  };

  const fetchOnce = useCallback(async (): Promise<void> => {
    try {
      const payload = await getStatus(jobId);
      const isStale = computeIsStale(payload);
      const transitioned = (() => {
        const prev = prevStateRef.current;
        if (!prev) return true; // initial load -> reset backoff
        // queued→running, running→completed, running→failed, queued→completed
        return prev.state !== payload.state;
      })();
      setState({ status: payload, data: payload, error: null, isStale, lastUpdated: Date.now() });
      prevStateRef.current = payload;
      // Reset backoff on transition
      if (transitioned) {
        delayRef.current = MIN_DELAY_MS;
      } else {
        // Increase backoff gradually up to max; if stale, bias toward higher delay
        const next = Math.min(MAX_DELAY_MS, Math.floor(delayRef.current * 2));
        delayRef.current = Math.max(MIN_DELAY_MS, isStale ? Math.max(next, 10000) : next);
      }
    } catch (err: unknown) {
      const e = err as Error;
      const msg = e.message || 'Status fetch failed';
      // Stop polling on 429
      if (msg.includes('HTTP 429')) {
        setState((prev) => ({ ...prev, error: 'QUOTA_EXCEEDED', lastUpdated: Date.now() }));
        clearTimer();
        return;
      }
      // Propagate 404 unless already completed
      if (msg.includes('HTTP 404')) {
        setState((prev) => ({ ...prev, error: 'NOT_FOUND', lastUpdated: Date.now() }));
      } else {
        setState((prev) => ({ ...prev, error: msg, lastUpdated: Date.now() }));
      }
    }
  }, [jobId]);

  const scheduleNext = useCallback((): void => {
    clearTimer();
    const d = withJitter(delayRef.current);
    timerRef.current = window.setTimeout(() => {
      void fetchOnce().then(scheduleNext);
    }, d);
  }, [fetchOnce]);

  const refresh = useCallback((): void => {
    delayRef.current = MIN_DELAY_MS;
    void fetchOnce().then(scheduleNext);
  }, [fetchOnce, scheduleNext]);

  useEffect(() => {
    delayRef.current = MIN_DELAY_MS;
    prevStateRef.current = null;
    void fetchOnce().then(scheduleNext);
    return () => clearTimer();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  return {
    status: state.status,
    data: state.data,
    error: state.error,
    refresh,
    isStale: state.isStale,
    lastUpdated: state.lastUpdated,
  };
}

export default useJobStatus;