import { useEffect, useState } from 'react';
import { getOnboardingState, sendOnboardingEvent, renderFromTemplate, type OnboardingState } from '@/lib/api';
import { useNavigate } from 'react-router-dom';

type Props = { open: boolean; onClose: () => void };

const ONBOARDING_ENABLED = (import.meta.env.VITE_ONBOARDING_ENABLED ?? 'true') === 'true';

export function OnboardingWelcome({ open, onClose }: Props) {
  const [state, setState] = useState<OnboardingState | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!ONBOARDING_ENABLED || !open) return;
    getOnboardingState().then(setState).catch(() => {});
  }, [open]);

  if (!ONBOARDING_ENABLED || !open) return null;

  const start = async () => {
    try { await sendOnboardingEvent('welcome_seen'); } catch {}
    onClose();
  };
  const skip = async () => {
    try { await sendOnboardingEvent('welcome_seen'); } catch {}
    onClose();
  };
  const quickStart = async () => {
    try {
      if (state?.recommended_template_id) {
        const r = await renderFromTemplate(String(state.recommended_template_id), { overrides: { title: 'My first video' } });
        navigate(`/render/${r.job_id}`);
      } else {
        navigate('/templates', { state: { quickStart: true } });
      }
      onClose();
    } catch {}
  };

  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div style={{ background: '#fff', padding: 24, borderRadius: 8, width: 520, maxWidth: '90%' }}>
        <h2>Make your first video in 3 quick steps</h2>
        <p>We’ll guide you through creating a project, rendering it, and exporting or sharing it.</p>
        <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
          <button onClick={start}>Start now</button>
          <button onClick={skip}>Skip</button>
          {state?.recommended_template_id && (
            <button onClick={quickStart}>Quick Start</button>
          )}
        </div>
      </div>
    </div>
  );
}
