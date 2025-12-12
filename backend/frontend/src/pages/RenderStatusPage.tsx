import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getRender, type RenderJob as ApiRenderJob } from '@/lib/api';

type Artifacts = { video?: string; audio?: string; thumbnail?: string } | null | undefined;
type RenderJob = { id: string; status: ApiRenderJob['status']; artifacts?: Artifacts; error?: string | null };

export function RenderStatusPage(): JSX.Element {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<RenderJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  const stopPolling = () => {
    if (timer.current) {
      clearInterval(timer.current);
      timer.current = null;
    }
  };

  const poll = async (id: string) => {
    setLoading(true);
    try {
      const res = await getRender(id);
      setJob({
        id: res.id,
        status: res.status,
        error: res.error ?? null,
        artifacts: (() => {
          const acc: Artifacts = {};
          res.artifacts?.forEach((a) => {
            if (a.type === 'video') acc.video = a.url;
            if (a.type === 'audio') acc.audio = a.url;
            if (a.type === 'image') acc.thumbnail = a.url;
          });
          return acc;
        })(),
      });
      setErr(null);
      if (res.status === 'success' || res.status === 'error' || res.status === 'cancelled') {
        stopPolling();
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!jobId) return;
    void poll(jobId);
    timer.current = window.setInterval(() => void poll(jobId), 4000);
    return () => stopPolling();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  const artifacts = job?.artifacts;
  const isDone = job?.status === 'success';
  const isError = job?.status === 'error';
  const isCancelled = job?.status === 'cancelled';

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Render Status</h1>
        <Link to="/" className="text-sm underline">Home</Link>
      </div>

      {!jobId && (
        <div className="rounded-lg border p-4">
          <p className="text-red-600">Missing jobId in URL.</p>
        </div>
      )}

      {jobId && (
        <div className="rounded-lg border p-4 space-y-3">
          <div>
            <div className="text-sm text-gray-500">Job ID</div>
            <div className="font-mono text-sm break-all">{jobId}</div>
          </div>

          <div>
            <div className="text-sm text-gray-500">Status</div>
            <div className="font-medium">{loading ? 'loading...' : job?.status ?? 'unknown'}</div>
          </div>

          {isCancelled && <div className="text-gray-600">This render was cancelled.</div>}

          {isError && <div className="text-red-600">{job?.error || 'Render failed'}</div>}

          {isDone && (
            <div className="space-y-3">
              {artifacts?.thumbnail && (
                <img src={artifacts.thumbnail} alt="thumbnail" className="w-full rounded-lg border" />
              )}
              {artifacts?.video && (
                <video src={artifacts.video} controls className="w-full rounded-lg border" />
              )}
              {!artifacts?.video && artifacts?.audio && (
                <audio src={artifacts.audio} controls className="w-full" />
              )}
            </div>
          )}

          {err && (
            <div role="alert" aria-live="polite" className="text-red-600 space-y-1">
              <div className="font-medium">Failed to load render</div>
              <div className="text-sm opacity-80">{String(err)}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default RenderStatusPage;
