import { useEffect, useState } from 'react';
import { getOnboardingState } from '@/lib/api';

export function useOnboardingState(){
  const [events, setEvents] = useState<string[] | null>(null);
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const st = await getOnboardingState();
        if (mounted) setEvents(Array.isArray((st as any).events) ? (st as any).events : []);
      } catch {
        if (mounted) setEvents([]);
      }
    })();
    return () => { mounted = false; };
  }, []);
  return { events };
}
