import { useEffect, useState } from 'react';
import { getAdminUsage, exportAdminUsageCsv } from '@/lib/api';
import type { AdminUsageEntry } from '@/types/admin';

export default function AdminUsagePage() {
  const [userId, setUserId] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [entries, setEntries] = useState<AdminUsageEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    getAdminUsage({ page, pageSize, userId: userId || undefined }).then((res) => { setEntries(res.entries); setTotal(res.total); }).catch((e) => setErr(String(e)));
  }, [page, pageSize, userId]);
  const exportCsv = async () => {
    try { const csv = await exportAdminUsageCsv({ userId: userId || undefined }); const blob = new Blob([csv], { type: 'text/csv' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'usage.csv'; a.click(); URL.revokeObjectURL(url); } catch (e) { setErr(String(e)); }
  };
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="Filter by user_id…" className="border rounded px-2 py-1" />
        <button onClick={exportCsv} className="text-sm text-indigo-600">Export CSV</button>
      </div>
      {err && <div className="text-red-600 mb-2">{err}</div>}
      <table className="w-full text-sm" data-testid="admin-usage-table">
        <thead><tr><th>User</th><th>Day</th><th>Renders</th><th>TTS sec</th></tr></thead>
        <tbody>
          {entries.length === 0 ? <tr><td colSpan={4} className="text-gray-500">No usage</td></tr> : entries.map((u) => (
            <tr key={`${u.user_id}-${u.day}`}><td>{u.user_id}</td><td>{u.day}</td><td>{u.renders}</td><td>{u.tts_sec}</td></tr>
          ))}
        </tbody>
      </table>
      <div className="flex items-center gap-2 mt-3">
        <button disabled={page<=1} onClick={() => setPage((p)=>p-1)} className="border rounded px-2">Prev</button>
        <span>{page}</span>
        <button disabled={(page*pageSize)>=total} onClick={() => setPage((p)=>p+1)} className="border rounded px-2">Next</button>
        <select value={pageSize} onChange={(e)=>setPageSize(Number(e.target.value))} className="border rounded px-2"><option value={20}>20</option><option value={50}>50</option></select>
      </div>
    </div>
  );
}
