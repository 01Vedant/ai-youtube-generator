import { useEffect, useState } from 'react';
import { getFeatureFlags, setFeatureFlag, type FeatureFlags } from '@/lib/api';

export function useFeatureFlags() {
  const [flags, setFlags] = useState<FeatureFlags>({});
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    (async () => {
      try {
        const f = await getFeatureFlags();
        setFlags(f);
      } finally {
        setLoading(false);
      }
    })();
  }, []);
  async function updateFlag(key: string, value: boolean) {
    setFlags(prev => ({ ...prev, [key]: value }));
    try {
      const f = await setFeatureFlag(key, value);
      setFlags(f);
    } catch {
      // revert on error
      setFlags(prev => ({ ...prev, [key]: !value }));
    }
  }
  async function refresh() {
    setLoading(true);
    try {
      const f = await getFeatureFlags();
      setFlags(f);
    } finally {
      setLoading(false);
    }
  }
  return { flags, loading, updateFlag, refresh };
}
