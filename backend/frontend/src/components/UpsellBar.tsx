import React, { useEffect, useState } from 'react';
import { useAuth } from '@/state/auth';
import { createCheckoutSession } from '@/lib/api';

export const UpsellBar: React.FC = () => {
  const { user } = useAuth();
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const flag = localStorage.getItem('upsell_dismissed');
    setDismissed(flag === '1');
  }, []);

  if (!user || user.plan_id !== 'free' || dismissed) return null;

  return (
    <div
      className="upsell-bar"
      style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        gap: 12, padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb',
        background: '#f8fafc', color: '#0f172a', marginBottom: 12, fontSize: 14,
      }}
      role="region"
      aria-label="Upsell: Pro plan"
    >
      <div>
        <strong>You're on Free</strong> — Pro gives higher daily limits and YouTube export.
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button
          className="text-sm px-3 py-1 border rounded bg-blue-600 text-white"
          onClick={async () => {
            try {
              const { url } = await createCheckoutSession('pro');
              if (url) window.location.href = url;
            } catch (e) {
              console.error(e);
              alert('Unable to start checkout');
            }
          }}
          aria-label="Go Pro"
        >
          Go Pro
        </button>
        <button
          className="text-sm px-3 py-1 border rounded"
          onClick={() => { localStorage.setItem('upsell_dismissed', '1'); setDismissed(true); }}
          aria-label="Dismiss"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
};
