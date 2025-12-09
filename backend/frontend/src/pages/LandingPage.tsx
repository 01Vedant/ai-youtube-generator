import { useEffect, useState, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useSeo } from '@/seo';
import { PublicShell } from '@/components/PublicShell';
import { JobProgressCard } from '@/components/JobProgressCard';
import { startRender } from '@/lib/api';

function Bullet({ title, desc }: { title: string; desc: string }) {
  return (
    <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 16 }}>
      <h3 style={{ marginTop: 0 }}>{title}</h3>
      <p style={{ color: '#555' }}>{desc}</p>
    </div>
  );
}

export default function LandingPage(): JSX.Element {
  useSeo({ title: 'DevotionalAI - Create devotional videos', description: 'Generate educational and devotional short videos.' });
  const [loading, setLoading] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [duration, setDuration] = useState('30');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const PUBLIC_ENABLED = import.meta.env.VITE_PUBLIC_ENABLED === 'true';

  const handleDemo = async () => {
    setLoading(true);
    setDemoError(null);
    try {
      const res = await startRender({ script: 'Sample devotional short', template_id: 'demo', duration_sec: 30 });
      window.__track?.('render_start', { job_id: res.job_id });
      navigate(`/render/${res.job_id}`);
    } catch (e) {
      setDemoError('Failed to start demo. Please try again.');
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateStory = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreating(true);
    setCreateError(null);
    setJobId(null);
    try {
      const parsedDuration = Number(duration);
      const durationSec = Number.isFinite(parsedDuration) && parsedDuration > 0 ? parsedDuration : undefined;
      const res = await startRender({
        script: description || title || 'Untitled story',
        duration_sec: durationSec,
      });
      window.__track?.('render_start', { job_id: res.job_id });
      setJobId(res.job_id);
    } catch (e) {
      setCreateError('Failed to create story. Please try again.');
      console.error(e);
    } finally {
      setCreating(false);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('e2e') === '1') {
      setCreateOpen(true);
    }
  }, [location.search]);

  return (
    <PublicShell>
      <div style={{ padding: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 12 }}>
          <button
            data-testid="create-story"
            style={{ padding: '10px 18px', fontSize: 16 }}
            onClick={() => {
              setCreateOpen(true);
              setCreateError(null);
            }}
          >
            Create Story
          </button>
        </div>
        <header style={{ textAlign: 'center', marginTop: 40 }}>
          <h1 style={{ fontSize: 32, marginBottom: 12 }}>DevotionalAI</h1>
          <p style={{ fontSize: 16, color: '#555' }}>Create beautiful devotional shorts and educational content.</p>
        </header>
        <section style={{ maxWidth: 860, margin: '40px auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            <Bullet title="Templates" desc="Start quickly with curated devotional templates." />
            <Bullet title="Voice options" desc="Pick from clear voices for Hindi and English." />
            <Bullet title="Fast exports" desc="Render and export to MP4 optimized for shorts." />
          </div>
        </section>
        <section style={{ maxWidth: 720, margin: '40px auto', textAlign: 'center' }}>
          {(demoError || createError) && (
            <div style={{ color: 'red', marginBottom: 12 }}>{createError || demoError}</div>
          )}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, justifyContent: 'center' }}>
            <button
              data-testid="create-story"
              style={{ padding: '12px 24px', fontSize: 18 }}
              onClick={() => {
                setCreateOpen(true);
                setCreateError(null);
              }}
            >
              Create Story
            </button>
            <button
              style={{ padding: '12px 24px', fontSize: 18 }}
              onClick={handleDemo}
              disabled={loading || !PUBLIC_ENABLED}
            >
              {loading ? 'Starting...' : 'Try a Sample Video'}
            </button>
          </div>

          {createOpen && (
            <div
              style={{ marginTop: 24, padding: 20, border: '1px solid #eee', borderRadius: 8, textAlign: 'left' }}
              data-testid="create-story-modal"
            >
              <form onSubmit={handleCreateStory} style={{ display: 'grid', gap: 12 }}>
                <div>
                  <label htmlFor="create-title" style={{ fontWeight: 600 }}>Title</label>
                  <input
                    id="create-title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g., Festival of Lights"
                    aria-label="Title"
                    required
                    style={{ width: '100%', padding: 10, marginTop: 6 }}
                  />
                </div>
                <div>
                  <label htmlFor="create-description" style={{ fontWeight: 600 }}>Description</label>
                  <textarea
                    id="create-description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="One-line summary of the story"
                    aria-label="Description"
                    rows={3}
                    style={{ width: '100%', padding: 10, marginTop: 6 }}
                  />
                </div>
                <div>
                  <label htmlFor="create-duration" style={{ fontWeight: 600 }}>Duration (seconds)</label>
                  <input
                    id="create-duration"
                    type="number"
                    min={5}
                    max={300}
                    value={duration}
                    onChange={(e) => setDuration(e.target.value)}
                    placeholder="30"
                    aria-label="Duration"
                    style={{ width: '100%', padding: 10, marginTop: 6 }}
                  />
                </div>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  <button
                    type="submit"
                    data-testid="create-story-submit"
                    disabled={creating}
                    style={{ padding: '10px 18px', fontSize: 16 }}
                  >
                    {creating ? 'Creating...' : 'Create Story'}
                  </button>
                  <span style={{ fontSize: 12, color: '#555' }}>Title and description generate your scenes.</span>
                </div>
              </form>
              {jobId && (
                <div style={{ marginTop: 20 }}>
                  <JobProgressCard jobId={jobId} />
                </div>
              )}
            </div>
          )}
        </section>
        <footer style={{ textAlign: 'center', marginTop: 40 }}>
          <a href="/legal">Legal</a>
        </footer>
      </div>
    </PublicShell>
  );
}
