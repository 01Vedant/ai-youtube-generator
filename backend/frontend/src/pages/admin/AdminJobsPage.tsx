import { useEffect, useState } from 'react';
import { getAdminJobs, exportAdminJobsCsv } from '@/lib/api';
import type { AdminJobEntry } from '@/types/admin';

export default function AdminJobsPage() {
  const [q, setQ] = useState('');
  const [status, setStatus] = useState<string>('');
  const [from, setFrom] = useState<string>('');
  const [to, setTo] = useState<string>('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [entries, setEntries] = useState<AdminJobEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    getAdminJobs({ page, pageSize, q, status, from, to }).then((res) => { setEntries(res.entries); setTotal(res.total); }).catch((e) => setErr(String(e)));
  }, [page, pageSize, q, status, from, to]);
  const exportCsv = async () => {
    try { const csv = await exportAdminJobsCsv({ q, status, from, to }); const blob = new Blob([csv], { type: 'text/csv' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'jobs.csv'; a.click(); URL.revokeObjectURL(url); } catch (e) { setErr(String(e)); }
  };
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search title…" className="border rounded px-2 py-1" />
        <select value={status} onChange={(e)=>setStatus(e.target.value)} className="border rounded px-2 py-1">
          <option value="">All statuses</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="failed">Failed</option>
          <option value="completed">Completed</option>
        </select>
        <input type="date" value={from} onChange={(e)=>setFrom(e.target.value)} className="border rounded px-2 py-1" />
        <input type="date" value={to} onChange={(e)=>setTo(e.target.value)} className="border rounded px-2 py-1" />
        <button onClick={exportCsv} className="text-sm text-indigo-600">Export CSV</button>
      </div>
      {err && <div className="text-red-600 mb-2">{err}</div>}
      <table className="w-full text-sm" data-testid="admin-jobs-table">
        <thead><tr><th>Title</th><th>Status</th><th>User</th><th>Created</th><th>Completed</th><th>Duration</th><th>Error</th></tr></thead>
        <tbody>
          {entries.length === 0 ? <tr><td colSpan={7} className="text-gray-500">No jobs</td></tr> : entries.map((j) => (
            <tr key={j.id}><td>{j.title ?? ''}</td><td>{j.status}</td><td>{j.user_id}</td><td>{j.created_at}</td><td>{j.completed_at ?? ''}</td><td>{j.duration_ms ?? ''}</td><td>{j.error_code ?? ''}</td></tr>
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
