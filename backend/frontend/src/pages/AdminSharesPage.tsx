import { useEffect, useState } from "react";
const SHARES_ENABLED = (import.meta.env.VITE_PUBLIC_SHARES_ENABLED ?? "true") !== "false";

export default function AdminSharesPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [notAvailable, setNotAvailable] = useState(false);
  useEffect(() => {
    if (!SHARES_ENABLED) return;
    fetch("/admin/shares?limit=200").then(r => {
      if (r.status === 404) { setNotAvailable(true); return []; }
      return r.ok ? r.json() : [];
    }).then(setRows).finally(() => setLoading(false));
  }, []);
  if (!SHARES_ENABLED) return <div className="p-6">Shares not enabled.</div>;
  if (notAvailable) return <div className="p-6">Shares admin not available.</div>;
  if (loading) return <div className="p-6">Loading…</div>;
  if (!rows.length) return <div className="p-6">No shares found.</div>;
  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold mb-4">Recent Shares</h1>
      <button onClick={() => window.open("/admin/shares.csv", "_blank")}>Download CSV</button>
      <table className="w-full text-sm">
        <thead>
          <tr>
            <th>ID</th>
            <th>Created</th>
            <th>Title</th>
            <th>Artifact</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.id}>
              <td>{r.id}</td>
              <td>{r.created_at}</td>
              <td>{r.title}</td>
              <td>{(r.artifact_url || "").slice(0, 32)}…</td>
              <td>
                <button onClick={() => navigator.clipboard.writeText(`/s/${r.id}`)}>Copy Link</button>
                <a href={`/s/${r.id}`} target="_blank" rel="noopener noreferrer" style={{ marginLeft: 8 }}>Open</a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
