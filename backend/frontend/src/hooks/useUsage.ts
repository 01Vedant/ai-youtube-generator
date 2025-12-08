import { useCallback, useEffect, useState } from 'react';
import { getUsageToday, type UsageToday } from '@/lib/api';

type State = {
  data: UsageToday | null;
  loading: boolean;
  error: string | null;
};

export function useUsage() {
  const [state, setState] = useState<State>({ data: null, loading: false, error: null });

  const isAuthenticated = (() => {
    try {
      const tokens = localStorage.getItem('auth_tokens');
      if (!tokens) return false;
      const parsed = JSON.parse(tokens);
      return Boolean(parsed?.access_token || parsed?.refresh_token);
    } catch {
      return false;
    }
  })();

  const fetchUsage = useCallback(async () => {
    if (!isAuthenticated) {
      setState({ data: null, loading: false, error: null });
      return;
    }
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const res = await getUsageToday();
      setState({ data: res, loading: false, error: null });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load usage';
      setState({ data: null, loading: false, error: message });
    }
  }, [isAuthenticated]);

  useEffect(() => {
    fetchUsage();
  }, [fetchUsage]);

  return { ...state, refetch: fetchUsage } as const;
}
