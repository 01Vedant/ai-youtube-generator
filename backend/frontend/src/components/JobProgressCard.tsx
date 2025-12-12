import React, { useEffect, useRef, useState } from 'react';
import { cancelRender, getRender, RenderJob } from '../lib/api';

declare global {
  interface Window {
    __track?: (event: string, data?: Record<string, any>) => void;
  }
}

interface JobProgressCardProps {
  jobId: string;
  onRetry?: () => void;
  showHeader?: boolean;
}

const POLL_INTERVAL = 1500;

export const JobProgressCard: React.FC<JobProgressCardProps> = ({ jobId, onRetry, showHeader = true }: JobProgressCardProps) => {
  const [job, setJob] = useState<RenderJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [shouldPoll, setShouldPoll] = useState(true);
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setShouldPoll(true);
  }, [jobId]);

  useEffect(() => {
    if (!jobId || !shouldPoll) return;
    let active = true;
    const poll = async () => {
      try {
        const res = await getRender(jobId);
        if (!active) return;
        setJob(res);
        if (res.status === 'success') {
          window.__track?.('render_success', { job_id: jobId });
        } else if (res.status === 'error') {
          window.__track?.('render_error', { job_id: jobId });
        } else if (res.status === 'cancelled') {
          window.__track?.('render_cancelled', { job_id: jobId });
        }
        if (res.status === 'success' || res.status === 'error' || res.status === 'cancelled') {
          setShouldPoll(false);
          return;
        }
        pollTimer.current = setTimeout(poll, POLL_INTERVAL);
      } catch (e: any) {
        if (e.message?.includes('404')) {
          setError('This job was not found');
        } else {
          setError(e.message || 'Unknown error');
        }
        window.__track?.('render_error', { job_id: jobId });
      }
    };
    poll();
    return () => {
      active = false;
      if (pollTimer.current) {
        clearTimeout(pollTimer.current);
        pollTimer.current = null;
      }
    };
  }, [jobId, shouldPoll]);

  const handleCancel = async () => {
    setCancelling(true);
    try {
      await cancelRender(jobId);
      setJob((prev) => prev ? { ...prev, status: 'cancelled' } : { id: jobId, status: 'cancelled' as RenderJob['status'] });
      setShouldPoll(true);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to cancel job');
    } finally {
      setCancelling(false);
      if (pollTimer.current) {
        clearTimeout(pollTimer.current);
        pollTimer.current = null;
      }
    }
  };

  if (error) {
    return (
      <div className="job-progress-error">
        <p>{error}</p>
        <button onClick={onRetry}>Back</button>
      </div>
    );
  }
  if (!job) return <div>Loading...</div>;

  return (
    <div className="job-progress-card" data-testid="job-progress-card">
      {showHeader && <h3>Render Status: {job.status}</h3>}
      {job.status === 'queued' && <p>Queued...</p>}
      {job.status === 'running' && <p>Rendering... <span className="spinner" /></p>}
      {job.status === 'cancelled' && <p>Render cancelled.</p>}
      {job.status === 'success' && (
        <div>
          {job.artifacts && Array.isArray(job.artifacts) ? (() => {
            const video = job.artifacts.find(a => a.type === 'video');
            const image = job.artifacts.find(a => a.type === 'image');
            const audio = job.artifacts.find(a => a.type === 'audio');
            if (video) {
              return <video controls src={video.url} style={{ maxWidth: '100%' }} data-testid="scene-thumb-video" />;
            } else if (image) {
              return <img src={image.url} alt="Preview" style={{ maxWidth: '100%' }} data-testid="scene-thumb-image" />;
            } else if (audio) {
              return <audio controls src={audio.url} data-testid="scene-thumb-audio" />;
            } else {
              return (
                <div>
                  <p>No preview available.</p>
                  <details>
                    <summary>Raw job JSON</summary>
                    <pre>{JSON.stringify(job, null, 2)}</pre>
                  </details>
                </div>
              );
            }
          })() : (
            <div>
              <p>No preview available.</p>
              <details>
                <summary>Raw job JSON</summary>
                <pre>{JSON.stringify(job, null, 2)}</pre>
              </details>
            </div>
          )}
        </div>
      )}
      {job.status === 'error' && (
        <div>
          <p>Render failed.</p>
          <button onClick={onRetry}>Retry</button>
        </div>
      )}
      {(job.status === 'queued' || job.status === 'running') && (
        <div style={{ marginTop: 12 }}>
          <button className="btn-secondary" onClick={handleCancel} disabled={cancelling}>
            {cancelling ? 'Cancelling...' : 'Cancel Render'}
          </button>
        </div>
      )}
    </div>
  );
};

export default JobProgressCard;
