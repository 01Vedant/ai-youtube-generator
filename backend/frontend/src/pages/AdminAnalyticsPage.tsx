export default function AdminAnalyticsPage() {
  return <div style={{ padding: 24 }}>Admin Analytics is not configured in this build.</div>;
}
export default function AdminAnalyticsPage() {
  return <div style={{ padding: 24 }}>Admin Analytics is not configured in this build.</div>;
}
import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/state/auth';
import { getAnalyticsSummary, getAnalyticsDaily, type AnalyticsSummary, type AnalyticsDaily } from '@/lib/api';

const adminEmails = (import.meta.env.VITE_ADMIN_EMAILS || '').split(',').map(s => s.trim()).filter(Boolean);

type KPI = {
  label: string;
  value: string | number;
};

const BarRow: React.FC<{ data: number[] }> = ({ data }) => {
  const max = Math.max(1, ...data);
  return (
    <div style={{ display: 'flex', gap: 2, alignItems: 'flex-end', height: 32 }}>
      {data.map((v, i) => (
        <div key={i} style={{ width: 10, background: '#cbd5e1', height: Math.max(2, Math.round((v / max) * 32)) }} />
      ))}
    </div>
  );
};

export default function AdminAnalyticsPage(): JSX.Element {
  const { user } = useAuth();
  const isAdmin = !!user && ((user.roles?.includes('admin')) || (user.email && adminEmails.includes(user.email)));
  if (!isAdmin) {
    return <div style={{ padding: 16 }}><h2>403</h2><p>Admins only.</p></div>;
  }

  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const FLAG = (import.meta.env.VITE_PUBLIC_ENABLED ?? "true") !== "false";
  if (!FLAG) return <div className="p-6">This page is behind a feature flag or not yet configured.</div>;
  const [daily, setDaily] = useState<AnalyticsDaily | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const s = await getAnalyticsSummary();
        const d = await getAnalyticsDaily(14);
        setSummary(s);
        setDaily(d);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const kpis: KPI[] = summary ? [
    { label: 'Users', value: summary.users_total },
    { label: 'Paying', value: summary.paying_users },
    { label: 'Renders Today', value: summary.renders_today },
    { label: 'Renders 7d', value: summary.renders_7d },
    { label: 'TTS Today', value: (() => { const s = summary.tts_sec_today; const m = Math.floor(s/60); const sec = s%60; return `${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`; })() },
    { label: 'Exports', value: summary.exports_total },
    { label: 'Shares', value: summary.shares_total },
    { label: `MRR (${(import.meta.env.VITE_CURRENCY || '$')})`, value: summary.mrr },
  ] : [];

  const renders14d = daily?.renders ?? Array.from({ length: 14 }, () => 0);
  const tts14d = daily?.tts_sec ?? Array.from({ length: 14 }, () => 0);
  const users14d = daily?.new_users ?? Array.from({ length: 14 }, () => 0);

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1>Admin Analytics</h1>
        <div style={{ display: 'flex', gap: 10 }}>
          <a href="/admin/logs" className="text-xs underline">Download Logs</a>
          <a href="/admin/flags" className="text-xs underline">Feature Flags</a>
        </div>
      </div>
      {loading && <div>Loading…</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 8, marginBottom: 16 }}>
        {kpis.map(k => (
          <div key={k.label} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 8, background: '#fff' }}>
            <div style={{ fontSize: 12, color: '#475569' }}>{k.label}</div>
            <div style={{ fontSize: 20, fontWeight: 600 }}>{k.value}</div>
          </div>
        ))}
      </div>
      <section style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 12 }}>
        <div>
          <div style={{ fontSize: 12, color: '#475569', marginBottom: 4 }}>Renders (14d)</div>
          <BarRow data={renders14d} />
        </div>
        <div>
          <div style={{ fontSize: 12, color: '#475569', marginBottom: 4 }}>TTS seconds (14d)</div>
          <BarRow data={tts14d} />
        </div>
        <div>
          <div style={{ fontSize: 12, color: '#475569', marginBottom: 4 }}>New users (14d)</div>
          <BarRow data={users14d} />
        </div>
      </section>
    </div>
  );
}
