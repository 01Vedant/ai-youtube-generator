
import { useNavigate } from 'react-router-dom';
import React from 'react';
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
  const used = data ?? hook.data;
  const busy = loading ?? hook.loading; 
  const navigate = useNavigate();

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

  return (
    <button
      type="button"
      className="usage-badge"
      title="See history"
      onClick={() => navigate('/usage')}
      aria-label="Open usage history"
    >
      📊 Usage
    </button>
  );
};

export default UsageBadge;
