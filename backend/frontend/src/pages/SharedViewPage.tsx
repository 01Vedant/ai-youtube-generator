import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getSharedView } from '@/lib/api';

type SharedView = {
  job_id: string;
  title: string;
  created_at: string;
  artifacts: { video?: string; thumbnail?: string; audio?: string };
};

export default function SharedViewPage() {
  const { shareId } = useParams<{ shareId: string }>();
  const [data, setData] = useState<SharedView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        if (!shareId) return;
        const res = await getSharedView(shareId);
        if (mounted) setData(res);
      } catch (e) {
        if (mounted) setError('Not found');
      }
    }
    load();
    // Fire-and-forget share hit recording
    if (shareId) {
      try { fetch(`/s/${shareId}/hit`, { method: 'POST' }); } catch { /* ignore */ }
    }
    return () => { mounted = false; };
  }, [shareId]);

  if (error) return <div className="p-4 text-center">{error}</div>;
  if (!data) return <div className="p-4 text-center">Loading…</div>;

  const created = new Date(data.created_at).toLocaleString();
  const { video, thumbnail } = data.artifacts || {};

  return (
    <div className="max-w-xl mx-auto p-4">
      <div className="mb-3">
        <h1 className="text-lg font-semibold">{data.title || data.job_id}</h1>
        <div className="text-xs text-gray-600">{created}</div>
      </div>
      <div className="mb-3">
        {thumbnail ? (
          <img src={thumbnail} alt={data.title} className="w-full rounded" />
        ) : (
          <div className="w-full h-40 bg-gray-100 rounded" />
        )}
      </div>
      {video ? (
        <video src={video} controls className="w-full rounded" />
      ) : (
        <div className="text-sm">Video unavailable</div>
      )}
    </div>
  );
}
