import { useEffect, useMemo, useState } from 'react';
import { getUsageHistory, type UsageHistory } from '@/lib/api';

const ALLOWED = [14, 30, 90] as const;
export type AllowedDays = typeof ALLOWED[number];

export function useUsageHistory(initialDays: number = 14) {
  const [days, setDaysRaw] = useState<number>(initialDays);
  const [data, setData] = useState<UsageHistory | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const clampedDays: AllowedDays = useMemo(() => (ALLOWED as readonly number[]).includes(days) ? (days as AllowedDays) : 14, [days]) as AllowedDays;

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getUsageHistory(clampedDays);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load usage history');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void refresh(); }, [clampedDays]);

  const setDays = (d: number) => setDaysRaw(ALLOWED.includes(d as any) ? d : 14);

  const totals = useMemo(() => {
    const series = data?.series || [];
    const renders = series.reduce((acc, p) => acc + (p.renders || 0), 0);
    const tts_sec = series.reduce((acc, p) => acc + (p.tts_sec || 0), 0);
    const avg_per_day = series.length ? (renders / series.length) : 0;
    return { renders, tts_sec, avg_per_day };
  }, [data]);

  return { days: clampedDays, data, loading, error, setDays, refresh, totals };
}
