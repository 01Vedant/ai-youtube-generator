import { useEffect, useState } from 'react';
import { getAdminUsers, exportAdminUsersCsv } from '@/lib/api';
import type { AdminUserEntry } from '@/types/admin';

export default function AdminUsersPage() {
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [entries, setEntries] = useState<AdminUserEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    getAdminUsers({ page, pageSize, q }).then((res) => { setEntries(res.entries); setTotal(res.total); }).catch((e) => setErr(String(e)));
  }, [page, pageSize, q]);
  const exportCsv = async () => {
    try { const csv = await exportAdminUsersCsv({ q }); const blob = new Blob([csv], { type: 'text/csv' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'users.csv'; a.click(); URL.revokeObjectURL(url); } catch (e) { setErr(String(e)); }
  };
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search email…" className="border rounded px-2 py-1" />
        <button onClick={exportCsv} className="text-sm text-indigo-600">Export CSV</button>
      </div>
      {err && <div className="text-red-600 mb-2">{err}</div>}
      <table className="w-full text-sm" data-testid="admin-users-table">
        <thead><tr><th>Email</th><th>Role</th><th>Plan</th><th>Created</th><th>Last Login</th></tr></thead>
        <tbody>
          {entries.length === 0 ? <tr><td colSpan={5} className="text-gray-500">No users</td></tr> : entries.map((u) => (
            <tr key={u.id}><td>{u.email}</td><td>{u.role}</td><td>{u.plan_id ?? ''}</td><td>{u.created_at}</td><td>{u.last_login_at ?? ''}</td></tr>
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
