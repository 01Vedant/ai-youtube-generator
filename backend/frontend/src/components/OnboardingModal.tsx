import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { postRender } from '@/lib/api';
import { withStickyToast } from '@/lib/toasts';
import { demoPlan } from '@/lib/demoPlan';

type Props = { open: boolean; onClose: () => void };

export const OnboardingModal: React.FC<Props> = ({ open, onClose }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;
  // Do not show on public share view
  if (location.pathname.startsWith('/s/')) return null;

  const finish = (): void => {
    localStorage.setItem('bhaktigen.onboarded', '1');
    onClose();
  };

  const handleDemo = async (): Promise<void> => {
    setError(null);
    try {
      const res = await withStickyToast(() => postRender(demoPlan), {
        pending: 'Submitting demo render…',
        success: (r) => `Demo render queued: ${r.job_id}`,
        error: (e) => e instanceof Error ? e.message : 'Failed to create demo video',
      });
      finish();
      navigate(`/render/${res.job_id}`);
    } catch (err: unknown) {
      const e = err as { code?: string; payload?: { limit_renders?: number; reset_at?: string } };
      if (e && e.code === 'QUOTA_EXCEEDED') {
        const limit = e.payload?.limit_renders;
        const reset = e.payload?.reset_at;
        setError(`Quota exceeded${limit ? `: ${limit} renders/day` : ''}${reset ? ` — resets ${new Date(reset).toLocaleString()}` : ''}`);
        return;
      }
      setError('Failed to create demo video');
    }
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="welcome-title">
      <div className="modal">
        <h2 id="welcome-title">Welcome to BhaktiGen</h2>
        <p className="subtitle">Create devotional videos in minutes — script, voice, visuals — all automated.</p>
        {error && (
          <div className="alert alert-warning" role="alert" aria-live="polite">
            {error}
          </div>
        )}
        <div className="modal-actions" style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-primary" onClick={() => void handleDemo()} aria-label="Create demo video">
            Create demo video
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => window.open('https://example.com/tour', '_blank', 'noopener')}
            aria-label="Watch 30s tour"
          >
            Watch 30s tour
          </button>
          <button className="btn" onClick={finish} aria-label="Skip onboarding">
            Skip for now
          </button>
        </div>
      </div>
    </div>
  );
};

export default OnboardingModal;