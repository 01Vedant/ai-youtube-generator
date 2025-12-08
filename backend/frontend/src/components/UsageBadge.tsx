import { useNavigate } from 'react-router-dom';
import { type UsageToday } from '@/lib/api';
import { useUsage } from '@/hooks/useUsage';

function formatMMSS(totalSeconds: number): string {
  const m = Math.floor((totalSeconds || 0) / 60);
  const s = Math.floor((totalSeconds || 0) % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

type Props = {
  data?: UsageToday | null;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
};

export const UsageBadge: React.FC<Props> = ({ data, loading, error, onRetry }) => {
  const hook = useUsage();
  const navigate = useNavigate();

  const used = data ?? hook.data;
  const busy = loading ?? hook.loading;
  const err = error ?? hook.error;

  // Hide entirely if unauthenticated (no data and no error)
  if (!busy && !used && !err) return null;

  const title = used?.reset_at
    ? `Resets at ${new Date(used.reset_at).toLocaleTimeString()}`
    : undefined;

  const neutralPill: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '10px',
    padding: '6px 10px',
    borderRadius: '12px',
    background: '#f3f4f6',
    color: '#374151',
    border: '1px solid #e5e7eb',
    fontSize: '12px',
    fontWeight: 500,
    whiteSpace: 'nowrap',
  };

  if (busy) {
    return (
      <div style={neutralPill} aria-live="polite" title="Checking usage">
        Loading...
      </div>
    );
  }

  if (err) {
    return (
      <button
        type="button"
        style={neutralPill}
        onClick={onRetry ?? hook.refetch}
        aria-label="Retry fetching usage"
      >
        Usage unavailable - retry
      </button>
    );
  }

  if (!used) return null;

  return (
    <button
      type="button"
      style={neutralPill}
      title={title}
      onClick={() => navigate('/usage')}
      aria-label="Open usage history"
    >
      Usage: {formatMMSS(used.tts_sec)} TTS · {used.renders}/{used.limit_renders} renders
    </button>
  );
};

export default UsageBadge;
