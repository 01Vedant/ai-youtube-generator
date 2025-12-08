import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchLibrary, getStatus } from '@/lib/api';
import type { LibraryItem } from '@/types/library';

type Row = {
  id: string;
  title: string;
  state?: string;
  created_at: string;
  project?: string | null;
};

const LEASE_TOTAL_SEC = 600; // 2 * LEASE_SEC as per instructions

export const QueueAdminPage: React.FC = () => {
  const navigate = useNavigate();
  const [rows, setRows] = useState<Row[]>([]);
  const [pageSize, setPageSize] = useState<number>(20);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [liveMap, setLiveMap] = useState<Record<string, { status: string; heartbeat_at?: string; stale?: boolean }>>({});
  const pendingQueue: string[] = useRef<string[]>([]).current;
  const running = useRef<number>(0);
  const MAX_CONCURRENCY = 4;

  const load = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchLibrary({ page: 1, pageSize, sort: 'created_at:desc' });
      const data: Row[] = res.entries.map((e: LibraryItem & { project_name?: string | null }) => ({
        id: e.id,
        title: e.title ?? `Job ${e.id}`,
        state: e.state,
        created_at: e.created_at,
        project: e.project_name ?? null,
      }));
      setRows(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, [pageSize]);

  const enqueueLive = (id: string): void => {
    pendingQueue.push(id);
    pump();
  };

  const pump = (): void => {
    if (running.current >= MAX_CONCURRENCY) return;
    const next = pendingQueue.shift();
    if (!next) return;
    running.current += 1;
    void getStatus(next)
      .then((s) => {
        const hb = (s as any).heartbeat_at as string | undefined;
        let stale = false;
        if (s.status === 'running' && hb) {
          const dt = Date.now() - Date.parse(hb);
          stale = dt > LEASE_TOTAL_SEC * 1000;
        }
        setLiveMap((prev) => ({ ...prev, [next]: { status: s.status, heartbeat_at: hb, stale } }));
      })
      .catch((err) => {
        setLiveMap((prev) => ({ ...prev, [next]: { status: 'error' } }));
      })
      .finally(() => {
        running.current -= 1;
        pump();
      });
  };

  const table = useMemo(() => rows, [rows]);

  return (
    <div className="p-4">
      <header className="flex items-center justify-between mb-3">
        <h1 className="text-lg font-semibold">Queue Admin</h1>
        <div className="flex items-center gap-2">
          <button className="text-sm px-3 py-1 border rounded" onClick={() => void load()} disabled={loading}>Refresh</button>
          <select className="text-sm border rounded px-2 py-1" value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}>
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </header>
      {error && <div className="text-sm text-red-700 border border-red-200 rounded px-3 py-2 mb-3">{error}</div>}
      {loading && <div className="text-sm text-slate-600">Loading…</div>}
      {!loading && table.length === 0 && <div className="text-sm text-slate-600">No recent jobs.</div>}
      {table.length > 0 && (
        <div className="overflow-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left border-b">
                <th className="px-2 py-1">ID</th>
                <th className="px-2 py-1">Title</th>
                <th className="px-2 py-1">State</th>
                <th className="px-2 py-1">Created</th>
                <th className="px-2 py-1">Project</th>
                <th className="px-2 py-1">Actions</th>
              </tr>
            </thead>
            <tbody>
              {table.map((r) => {
                const live = liveMap[r.id];
                const shortId = r.id.slice(0, 8);
                const created = new Date(r.created_at).toLocaleString();
                const stateChip = live
                  ? live.stale
                    ? <span className="px-2 py-0.5 rounded bg-yellow-50 text-yellow-700 border border-yellow-200">STALE</span>
                    : <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">{live.status}</span>
                  : <span className="px-2 py-0.5 rounded bg-slate-50 text-slate-700 border border-slate-200">{r.state ?? '—'}</span>;
                return (
                  <tr key={r.id} className="border-b">
                    <td className="px-2 py-1 font-mono">{shortId}</td>
                    <td className="px-2 py-1 truncate max-w-[24ch]" title={r.title}>{r.title}</td>
                    <td className="px-2 py-1">{stateChip}</td>
                    <td className="px-2 py-1">{created}</td>
                    <td className="px-2 py-1">{r.project ?? '—'}</td>
                    <td className="px-2 py-1 flex items-center gap-2">
                      <button className="text-xs px-2 py-1 border rounded" onClick={() => enqueueLive(r.id)}>Check live</button>
                      <button className="text-xs px-2 py-1 border rounded" onClick={() => navigate(`/render/${r.id}`)}>Open</button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default QueueAdminPage;
