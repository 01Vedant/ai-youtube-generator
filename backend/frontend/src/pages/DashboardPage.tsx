import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  claimReferral,
  createReferralCode,
  debugEcho,
  fetchLibrary,
  getOnboardingState,
  postRender,
  renderFromTemplate,
  sendOnboardingEvent,
} from '@/lib/api';
import { useOnboardingState } from '@/hooks/useOnboardingState';
import { useAuth } from '@/state/auth';
import type { LibraryItem } from '@/types/library';
import ArtifactCard from '@/components/ArtifactCard';
import './DashboardPage.css';
import { demoPlan } from '@/lib/demoPlan';
import { toast } from '@/lib/toast';

type DashboardState = {
  entries: LibraryItem[];
  total: number;
  loading: boolean;
  page: number;
  pageSize: number;
  query?: string;
  error?: string;
  scheduleModalOpen: boolean;
  selectedJob: LibraryItem | null;
};

const adminEmails = (import.meta.env.VITE_ADMIN_EMAILS || '').split(',').map((s: string) => s.trim()).filter(Boolean);

export default function DashboardPage(): JSX.Element {
  const { events } = useOnboardingState();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [invite, setInvite] = useState<{ code: string; url: string } | null>(null);
  const [claimInput, setClaimInput] = useState('');
  const [state, setState] = useState<DashboardState>({
    entries: [],
    total: 0,
    page: 1,
    pageSize: 20,
    loading: true,
    query: '',
    error: undefined,
    scheduleModalOpen: false,
    selectedJob: null,
  });

  const isAdmin = !!user && (user.roles?.includes('admin') || (user.email && adminEmails.includes(user.email)));

  const handleDebugEcho = async () => {
    try {
      const result = await debugEcho();
      console.log('Debug Echo:', result);
      alert(`Debug Echo: ok=${result.ok}, env=${result.env}`);
    } catch (err) {
      console.error('Debug Echo failed:', err);
      alert('Debug Echo failed');
    }
  };

  const loadJobs = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: undefined }));

    try {
      const data = await fetchLibrary({
        page: state.page,
        pageSize: state.pageSize,
        query: state.query,
        sort: 'created_at:desc',
      });

      setState((prev) => ({
        ...prev,
        entries: data.entries,
        total: data.total,
        loading: false,
      }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Failed to load jobs',
        loading: false,
      }));
    }
  }, [state.page, state.pageSize, state.query]);

  useEffect(() => {
    loadJobs();
    (async () => {
      try {
        const onboarding = await getOnboardingState();
        const dismissed = localStorage.getItem('onboarding:dismissed') === '1';
        const shouldShow =
          !dismissed && (!onboarding.has_render || (onboarding.seed_job_id && !onboarding.has_render));
        setState((prev) => ({
          ...prev,
          error: prev.error,
          scheduleModalOpen: prev.scheduleModalOpen,
          selectedJob: prev.selectedJob,
          // storing onboarding in window to reuse existing inline logic
        }));
        (window as any).__ONBOARDING_STATE = onboarding;
        (window as any).__ONBOARDING_SHOULD_SHOW = shouldShow;
      } catch {
        // ignore onboarding fetch errors
      }
    })();
  }, [loadJobs]);

  useEffect(() => {
    if (!state.loading && state.entries.length === 0 && (!events || events.length === 0)) {
      sendOnboardingEvent('empty_library_seen').catch(() => {});
    }
  }, [state.loading, state.entries.length, events]);

  const handleSearch = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setState((prev) => ({ ...prev, page: 1 }));
  };

  const totalPages = Math.ceil(state.total / state.pageSize);

  return (
    <div className="dashboard-page">
      <button style={{ position: 'absolute', top: 8, right: 8, zIndex: 1000 }} onClick={handleDebugEcho}>
        Debug Echo
      </button>
      <header className="dashboard-header">
        <h1>Dashboard</h1>
        <p>Manage your video generation jobs</p>
        {isAdmin && (
          <a href="/admin/analytics" className="text-xs underline" style={{ marginLeft: 8 }}>
            Analytics
          </a>
        )}
      </header>

      {(() => {
        const ONBOARDING_ENABLED = (import.meta.env.VITE_ONBOARDING_ENABLED ?? 'true') === 'true';
        const s: any = (window as any).__ONBOARDING_STATE;
        const stepsDone = Boolean(s?.steps?.created_project) && Boolean(s?.steps?.rendered_video) && Boolean(s?.steps?.exported_video);
        if (!ONBOARDING_ENABLED || !s || stepsDone) return null;
        return (
          <div className="empty-state-card" style={{ marginTop: 12, border: '1px solid #eee' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 className="text-sm font-semibold">Activation Checklist</h3>
              <button className="text-xs underline" onClick={() => { (window as any).__SHOW_ONBOARDING_MODAL?.(); }}>Onboarding</button>
            </div>
            <ul style={{ listStyle: 'none', padding: 0, marginTop: 8 }}>
              <li style={{ marginBottom: 6 }}>
                <span>{s?.steps?.created_project ? '[x]' : '[ ]'} Create your first project</span>
                <button className="btn-secondary" style={{ marginLeft: 8 }} onClick={() => navigate('/projects')}>Create</button>
              </li>
              <li style={{ marginBottom: 6 }}>
                <span>{s?.steps?.rendered_video ? '[x]' : '[ ]'} Render your first video</span>
                <button
                  className="btn-secondary"
                  style={{ marginLeft: 8 }}
                  onClick={async () => {
                    try {
                      if (s?.recommended_template_id) {
                        const res = await renderFromTemplate(s.recommended_template_id, { overrides: { title: 'My first video' } });
                        navigate(`/render/${res.job_id}`);
                      } else {
                        navigate('/templates', { state: { quickStart: true } });
                      }
                    } catch {
                      // ignore
                    }
                  }}
                >
                  Quick Start
                </button>
              </li>
              <li>
                <span>{s?.steps?.exported_video ? '[x]' : '[ ]'} Export or share it</span>
                <button className="btn-secondary" style={{ marginLeft: 8 }} disabled={!s?.steps?.rendered_video} onClick={() => navigate('/library')}>Open latest</button>
              </li>
            </ul>
          </div>
        );
      })()}

      <div className="dashboard-controls">
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            placeholder="Search by topic..."
            value={state.query || ''}
            onChange={(e) => setState((prev) => ({ ...prev, query: e.target.value }))}
            className="search-input"
          />
          <button type="submit" className="btn-primary">
            Search
          </button>
        </form>

        <div className="dashboard-stats">
          <span className="stat">Total: {state.total}</span>
          <span className="stat">
            Page {state.page} of {totalPages}
          </span>
        </div>
      </div>

      {user && (
        <div className="empty-state-card" style={{ marginTop: 12 }}>
          <h3 className="text-sm font-semibold">Invite friends</h3>
          <p className="text-xs text-gray-600">Share your referral link to help grow BhaktiGen.</p>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 6 }}>
            <button
              className="btn-secondary"
              onClick={async () => {
                try {
                  if (invite) {
                    await navigator.clipboard.writeText(invite.url);
                    toast.success('Copied link');
                    return;
                  }
                  const res = await createReferralCode();
                  setInvite(res);
                  await navigator.clipboard.writeText(res.url);
                  toast.success('Copied link');
                } catch (err) {
                  toast.error('Could not copy link');
                }
              }}
            >
              Create referral link
            </button>
            <input
              type="text"
              placeholder="Have a code?"
              value={claimInput}
              onChange={(e) => setClaimInput(e.target.value)}
              className="text-xs px-2 py-1 border rounded"
              style={{ minWidth: 160 }}
            />
            <button
              className="btn-secondary"
              onClick={async () => {
                const code = claimInput.trim();
                if (!code) return;
                try {
                  const res = await claimReferral(code);
                  if (res?.ok) {
                    toast.success('Referral claimed');
                    setClaimInput('');
                  } else {
                    toast.error('Invalid code');
                  }
                } catch (err) {
                  toast.error('Could not claim');
                }
              }}
            >
              Claim
            </button>
          </div>
        </div>
      )}

      {state.error && <div className="error-banner">{state.error}</div>}

      {state.loading ? (
        <div className="loading">Loading jobs...</div>
      ) : (
        <>
          {state.entries.length === 0 ? (
            <div className="empty-state-card">
              <div className="empty-icon">[library]</div>
              <h2>No videos yet</h2>
              <p>Start by creating a demo video or upload a prompt.</p>
              <div className="empty-actions" style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
                <button
                  className="btn-primary"
                  onClick={async () => {
                    try {
                      const res = await postRender(demoPlan);
                      navigate(`/render/${res.job_id}`);
                    } catch (err) {
                      const e = err as { code?: string };
                      if (e.code === 'QUOTA_EXCEEDED') {
                        alert('Quota exceeded. Please try after reset.');
                      }
                    }
                  }}
                >
                  Create demo video
                </button>
                <button className="btn-secondary" data-testid="create-story-cta" onClick={() => navigate('/create')}>
                  Open Create Video
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {state.entries.map((entry) => (
                <ArtifactCard
                  key={entry.id}
                  id={entry.id}
                  title={entry.title || `Job ${entry.id.slice(0, 8)}`}
                  thumbnailUrl={entry.thumbnail_url || `/artifacts/${entry.id}/thumb.png`}
                  videoUrl={entry.video_url || undefined}
                  createdAt={entry.created_at}
                  durationSec={entry.duration_sec || undefined}
                  voice={entry.voice as 'Swara' | 'Diya' | undefined}
                  template={entry.template}
                  onClick={() => navigate(`/render/${entry.id}`)}
                />
              ))}
            </div>
          )}

          {events && (
            <div className="empty-state-card" aria-label="Activation Checklist">
              <h3>Your progress</h3>
              <ul style={{ textAlign: 'left', margin: '0 auto', maxWidth: 520 }}>
                <li>
                  <input type="checkbox" readOnly checked={events.includes('created_first_project')} /> Create your first project
                  {!events.includes('created_first_project') && (
                    <button className="btn-link" onClick={() => { window.location.href = '/projects'; }}>
                      Create
                    </button>
                  )}
                </li>
                <li>
                  <input type="checkbox" readOnly checked={events.includes('rendered_first_video')} /> Render a video
                  {!events.includes('rendered_first_video') && (
                    <button className="btn-link" onClick={() => { window.location.href = '/create'; }}>
                      Render
                    </button>
                  )}
                </li>
                <li>
                  <input type="checkbox" readOnly checked={events.includes('exported_first_video')} /> Export a video
                </li>
              </ul>
            </div>
          )}

          {(() => {
            const ob = (window as any).__ONBOARDING_STATE as undefined | { has_render: boolean; seed_job_id: string | null };
            const dismissed = localStorage.getItem('onboarding:dismissed') === '1';
            const show = !dismissed && ob && (ob.has_render === false || (ob.seed_job_id && state.entries.length === 0));
            return show;
          })() && (
            <div className="empty-state-card" data-testid="getting-started-card">
              <div className="empty-icon">[launch]</div>
              <h2>Getting Started</h2>
              <ul style={{ textAlign: 'left', margin: '0 auto', maxWidth: 520 }}>
                <li>- Create your first video</li>
                <li>- Preview Hindi TTS</li>
                <li>- Track render status</li>
              </ul>
              <div className="empty-actions" style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
                <button className="btn-primary" onClick={() => navigate('/create')}>
                  Create your first video
                </button>
                {(() => {
                  const ob = (window as any).__ONBOARDING_STATE as any;
                  return ob?.seed_job_id ? (
                    <button className="btn-secondary" onClick={() => navigate(`/render/${ob.seed_job_id}`)}>
                      View sample
                    </button>
                  ) : null;
                })()}
                <button className="btn-secondary" onClick={() => { localStorage.setItem('onboarding:dismissed', '1'); }}>
                  Dismiss
                </button>
              </div>
            </div>
          )}

          <div className="pagination">
            <button
              className="btn-secondary"
              disabled={state.page === 1}
              onClick={() => setState((prev) => ({ ...prev, page: prev.page - 1 }))}
            >
              Previous
            </button>
            <span className="page-info">
              Page {state.page} of {totalPages}
            </span>
            <button
              className="btn-secondary"
              disabled={state.page >= totalPages}
              onClick={() => setState((prev) => ({ ...prev, page: prev.page + 1 }))}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
