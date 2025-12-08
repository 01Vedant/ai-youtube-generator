// Moved to _disabled

// The original content of the LandingPage component is no longer available.
export default function LandingPage() {
  return <div style={{ padding: 24 }}>Landing is not configured in this build.</div>;
}

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSeo } from '@/src/seo';
import { PublicShell } from '@/src/components/PublicShell';
import { startRender } from '@/lib/api';

export default function LandingPage() {
  useSeo({ title: 'DevotionalAI — Create devotional videos', description: 'Generate educational and devotional short videos.' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const PUBLIC_ENABLED = import.meta.env.VITE_PUBLIC_ENABLED === 'true';
  const SIMULATE_RENDER = window.__SIMULATE_RENDER === 1 || import.meta.env.SIMULATE_RENDER === '1' || true;

  const handleDemo = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await startRender({ script: 'Sample devotional short', template_id: 'demo', duration_sec: 30 });
      window.__track?.('render_start', { job_id: res.job_id });
      navigate(`/render/${res.job_id}`);
    } catch (e) {
      setError('Failed to start demo. Please try again.');
      // eslint-disable-next-line no-console
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <PublicShell>
      <div style={{ padding: 24 }}>
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
          {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}
          <button
            style={{ marginTop: 24, padding: '12px 24px', fontSize: 18 }}
            onClick={handleDemo}
            disabled={loading || !PUBLIC_ENABLED}
          >
            {loading ? 'Starting…' : 'Try a Sample Video'}
          </button>
        </section>
        <footer style={{ textAlign: 'center', marginTop: 40 }}>
          <a href="/legal">Legal</a>
        </footer>
      </div>
    </PublicShell>
  );
}


function Bullet({ title, desc }: { title: string; desc: string }) {
  return (
    <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 16 }}>
      <h3 style={{ marginTop: 0 }}>{title}</h3>
      <p style={{ color: '#555' }}>{desc}</p>
    </div>
  );
}

async function sha256(text: string): Promise<string> {
  try {
    const enc = new TextEncoder().encode(text);
    const hash = await (window.crypto?.subtle?.digest?.('SHA-256', enc) ?? Promise.reject(new Error('no crypto')));
    return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('');
  } catch { return ''; }
}