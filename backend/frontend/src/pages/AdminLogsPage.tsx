import React, { useMemo, useState } from 'react';
import { useAuth } from '@/state/auth';
import { downloadLogsBundle, saveBlob, type LogInclude } from '@/lib/api';
import { downloadAuditCsv } from '@/lib/api';
import { toast } from '@/lib/toast';

const adminEmails = (import.meta.env.VITE_ADMIN_EMAILS || '').split(',').map((s: string) => s.trim()).filter(Boolean);

export default function AdminLogsPage(): React.JSX.Element {
  const FLAG = (import.meta.env.VITE_PUBLIC_ENABLED ?? "true") !== "false";
  if (!FLAG) return <div className="p-6">This page is behind a feature flag or not yet configured.</div>;
  const { user } = useAuth();
  const isAdmin = !!user && ((user.roles?.includes('admin')) || (user.email && adminEmails.includes(user.email)));
  if (!isAdmin) {
    return <div style={{ padding: 16 }}><h2>403</h2><p>Admins only.</p></div>;
  }

  const today = useMemo(() => new Date().toISOString().slice(0,10), []);
  const [from, setFrom] = useState<string>(today);
  const [to, setTo] = useState<string>(today);
  const [includeStructured, setIncludeStructured] = useState(true);
  const [includeActivity, setIncludeActivity] = useState(true);
  const [loading, setLoading] = useState(false);

  async function handleDownload() {
    setLoading(true);
    try {
      const inc: LogInclude[] = [];
      if (includeStructured) inc.push('structured');
      if (includeActivity) inc.push('activity');
      const blob = await downloadLogsBundle({ from, to, include: inc.length ? inc : undefined });
      await saveBlob(blob, `logs-${from || today}_to_${to || today}.zip`);
      toast.success('Logs bundle downloaded');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to download logs';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h1>Admin Logs</h1>
      <div className="empty-state-card" style={{ maxWidth: 520 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <label className="text-xs">From
            <input type="date" value={from} onChange={e => setFrom(e.target.value)} className="text-xs px-2 py-1 border rounded w-full" />
          </label>
          <label className="text-xs">To
            <input type="date" value={to} onChange={e => setTo(e.target.value)} className="text-xs px-2 py-1 border rounded w-full" />
          </label>
        </div>
        <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
          <label className="text-xs"><input type="checkbox" checked={includeStructured} onChange={e => setIncludeStructured(e.target.checked)} /> Structured JSONL</label>
          <label className="text-xs"><input type="checkbox" checked={includeActivity} onChange={e => setIncludeActivity(e.target.checked)} /> Activity file</label>
        </div>
        <div style={{ marginTop: 12 }}>
          <button className="btn-primary" disabled={loading} onClick={handleDownload}>{loading ? 'Preparing…' : 'Download ZIP'}</button>
          <button
            className="btn-secondary"
            disabled={loading}
            style={{ marginLeft: 8 }}
            onClick={async () => {
              setLoading(true);
              try {
                const blob = await downloadAuditCsv({ from: from, to: to });
                await saveBlob(blob, `audit-${from || today}_to_${to || today}.csv`);
                toast.success('Audit CSV downloaded');
              } catch (err) {
                const msg = err instanceof Error ? err.message : 'Failed to download audit CSV';
                if (msg.includes('No audit')) toast.success(msg); else toast.error(msg);
              } finally {
                setLoading(false);
              }
            }}
          >
            Download Audit CSV
          </button>
        </div>
      </div>
    </div>
  );
}
