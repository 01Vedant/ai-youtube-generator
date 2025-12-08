// Moved to _disabled

// The original content of DashboardPage.tsx has been moved to the _disabled directory.
export default function DashboardPage() {
  return <div style={{ padding: 24 }}>Dashboard</div>;
}
import { debugEcho } from '../lib/api';
/**
 * DashboardPage.tsx - Complete job management dashboard
 * Features: Pagination, search, row actions (duplicate, delete), job details
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchLibrary, getOnboardingState, sendOnboardingEvent, createReferralCode, claimReferral, renderFromTemplate } from '../lib/api';
import { useOnboardingState } from '@/hooks/useOnboardingState';
import type { LibraryItem } from '../types/library';
// ScheduleModal removed in card view
import { ArtifactCard } from '../components/ArtifactCard';
import './DashboardPage.css';
import { postRender } from '@/lib/api';
import { demoPlan } from '@/lib/demoPlan';

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

export default function DashboardPage() {
      const handleDebugEcho = async () => {
        try {
          const result = await debugEcho();
          // eslint-disable-next-line no-console
          console.log('Debug Echo:', result);
          alert(`Debug Echo: ok=${result.ok}, env=${result.env}`);
        } catch (err) {
          // eslint-disable-next-line no-console
          console.error('Debug Echo failed:', err);
          alert('Debug Echo failed');
        }
      };
    const { events } = useOnboardingState();
  const navigate = useNavigate();
  const { user } = require('@/state/auth').useAuth();
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

  const loadJobs = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: undefined }));
    
    try {
      const data = await fetchLibrary({
        page: state.page,
        pageSize: state.pageSize,
        query: state.query,
        sort: "created_at:desc"
      });
      
      setState(prev => ({
        ...prev,
        entries: data.entries,
        total: data.total,
        loading: false,
      }));
    } catch (err) {
      setState(prev => ({
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
        const state = await getOnboardingState();
        const dismissed = localStorage.getItem('onboarding:dismissed') === '1';
        const shouldShow = !dismissed && (state.has_render === false || (state.seed_job_id && state.seed_job_id.length > 0 && state.has_render === false));
        setState(prev => ({ ...prev, error: prev.error, // keep
          // tuck state into error? keep minimal diffs; we will render card via computed conditions below
        }));
        (window as any).__ONBOARDING_STATE = state; // minimal surface: store globally for card rendering
      } catch {
        // ignore
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
    setState(prev => ({ ...prev, page: 1 }));
  };

  const totalPages = Math.ceil(state.total / state.pageSize);

  return (
    <div className="dashboard-page">
      <button style={{position:'absolute',top:8,right:8,zIndex:1000}} onClick={handleDebugEcho}>Debug Echo</button>
      {(() => {
        const ONBOARDING_ENABLED = (import.meta.env.VITE_ONBOARDING_ENABLED ?? 'true') === 'true';
        const s: any = (window as any).__ONBOARDING_STATE;
        const stepsDone = Boolean(s?.steps?.created_project) && Boolean(s?.steps?.rendered_video) && Boolean(s?.steps?.exported_video);
        const key = 'onboarding:banner:dismissed_until';
        const until = parseInt(localStorage.getItem(key) || '0', 10);
        const now = Date.now();
        const dismissed = Number.isFinite(until) && until > now;
        if (!ONBOARDING_ENABLED || !s || stepsDone || dismissed) return null;
        return (
          <div className="info-banner" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 10px', background: '#fffbe6', borderBottom: '1px solid #f0e6a6' }}>
            <span className="text-xs">Finish setup: Create → Render → Export</span>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn-link text-xs" onClick={() => { (window as any).__SHOW_ONBOARDING_MODAL?.(); }}>Continue</button>
              <button className="btn-link text-xs" onClick={() => { const sevenDays = 7 * 24 * 60 * 60 * 1000; localStorage.setItem(key, String(now + sevenDays)); }}>Dismiss</button>
            </div>
          </div>
        );
      })()}
      <header className="dashboard-header">
        <h1>Dashboard</h1>
        <p>Manage your video generation jobs</p>
        {(() => { const u = (window as any).__APP_USER || null; return null; })()}
        {(() => { try { const { user } = require('@/state/auth').useAuth(); const emails = (import.meta.env.VITE_ADMIN_EMAILS || '').split(',').map((s:string)=>s.trim()).filter(Boolean); const isAdmin = !!user && ((user.roles?.includes('admin')) || (user.email && emails.includes(user.email))); return isAdmin ? (<a href="/admin/analytics" className="text-xs underline" style={{ marginLeft: 8 }}>Analytics</a>) : null; } catch { return null; } })()}
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
                <span>{s?.steps?.created_project ? '✅' : '⬜'} Create your first project</span>
                <button className="btn-secondary" style={{ marginLeft: 8 }} onClick={() => navigate('/projects')}>Create</button>
              </li>
              <li style={{ marginBottom: 6 }}>
                <span>{s?.steps?.rendered_video ? '✅' : '⬜'} Render your first video</span>
                <button className="btn-secondary" style={{ marginLeft: 8 }} onClick={async () => {
                  try {
                    if (s?.recommended_template_id) {
                      const res = await renderFromTemplate(s.recommended_template_id, { overrides: { title: 'My first video' } });
                      navigate(`/render/${res.job_id}`);
                    } else {
                      navigate('/templates', { state: { quickStart: true } });
                    }
                  } catch {}
                }}>Quick Start</button>
              </li>
              <li>
                <span>{s?.steps?.exported_video ? '✅' : '⬜'} Export or share it</span>
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
            onChange={e => setState(prev => ({ ...prev, query: e.target.value }))}
            className="search-input"
          />
          <button type="submit" className="btn-primary">Search</button>
        </form>

        <div className="dashboard-stats">
          <span className="stat">Total: {state.total}</span>
          <span className="stat">Page {state.page} of {totalPages}</span>
        </div>
      </div>

      {/* Invite friends panel */}
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
                    (await import('../lib/toast')).toast.success('Copied link');
                    return;
                  }
                  const res = await createReferralCode();
                  setInvite(res);
                  await navigator.clipboard.writeText(res.url);
                  (await import('../lib/toast')).toast.success('Copied link');
                } catch (err) {
                  (await import('../lib/toast')).toast.error('Could not copy link');
                }
              }}
            >
              Create referral link
            </button>
            <input
              type="text"
              placeholder="Have a code?"
              value={claimInput}
              onChange={e => setClaimInput(e.target.value)}
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
                    (await import('../lib/toast')).toast.success('Referral claimed');
                    setClaimInput('');
                  } else {
                    (await import('../lib/toast')).toast.error('Invalid code');
                  }
                } catch (err) {
                  (await import('../lib/toast')).toast.error('Could not claim');
                }
              }}
            >
              Claim
            </button>
          </div>
        </div>
      )}

      {state.error && (
        <div className="error-banner">
          {state.error}
        </div>
      )}

      {state.loading ? (
        <div className="loading">Loading jobs...</div>
      ) : (
        <>
          {state.entries.length === 0 ? (
            <div className="empty-state-card">
              <div className="empty-icon">📹</div>
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
                <button className="btn-secondary" onClick={() => navigate('/create')}>Open Create Video</button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {state.entries.map(entry => (
                <ArtifactCard
                  key={entry.id}
                  id={entry.id}
                  title={entry.title || `Job ${entry.id.slice(0, 8)}`}
                  thumbnailUrl={entry.thumbnail_url || `/artifacts/${entry.id}/thumb.png`}
                  videoUrl={entry.video_url || undefined}
                  createdAt={entry.created_at}
                  durationSec={entry.duration_sec || undefined}
                  voice={entry.voice as ('Swara' | 'Diya') | undefined}
                  template={entry.template}
                  onClick={() => navigate(`/render/${entry.id}`)}
                />
              ))}
            </div>
          )}

          {/* Activation Checklist card */}
          {events && (
            <div className="empty-state-card" aria-label="Activation Checklist">
              <h3>Your progress</h3>
              <ul style={{ textAlign: 'left', margin: '0 auto', maxWidth: 520 }}>
                <li>
                  <input type="checkbox" readOnly checked={events.includes('created_first_project')} /> Create your first project
                  {!events.includes('created_first_project') && (
                    <button className="btn-link" onClick={() => { window.location.href = '/projects'; }}>Create</button>
                  )}
                </li>
                <li>
                  <input type="checkbox" readOnly checked={events.includes('rendered_first_video')} /> Render a video
                  {!events.includes('rendered_first_video') && (
                    <button className="btn-link" onClick={() => { window.location.href = '/create'; }}>Render</button>
                  )}
                </li>
                <li>
                  <input type="checkbox" readOnly checked={events.includes('exported_first_video')} /> Export a video
                </li>
              </ul>
            </div>
          )}

          {/* Getting Started card (compact, dismissible) */}
          {(() => { const ob = (window as any).__ONBOARDING_STATE as (undefined | { has_render: boolean; seed_job_id: string|null }); const dismissed = localStorage.getItem('onboarding:dismissed') === '1'; const show = !dismissed && (ob && (ob.has_render === false || (ob.seed_job_id && state.entries.length === 0))); return show; })() && (
            <div className="empty-state-card" data-testid="getting-started-card">
              <div className="empty-icon">✨</div>
              <h2>Getting Started</h2>
              <ul style={{ textAlign: 'left', margin: '0 auto', maxWidth: 520 }}>
                <li>• Create your first video</li>
                <li>• Preview Hindi TTS</li>
                <li>• Track render status</li>
              </ul>
              <div className="empty-actions" style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
                <button className="btn-primary" onClick={() => navigate('/create')}>Create your first video</button>
                {(() => { const ob = (window as any).__ONBOARDING_STATE as any; return ob?.seed_job_id ? (
                  <button className="btn-secondary" onClick={() => navigate(`/render/${ob.seed_job_id}`)}>View sample</button>
                ) : null; })()}
                <button className="btn-secondary" onClick={() => { localStorage.setItem('onboarding:dismissed','1'); }}>Dismiss</button>
              </div>
            </div>
          )}

          {/* Schedule modal disabled in card view; re-enable if needed */}

          <div className="pagination">
            <button
              className="btn-secondary"
              disabled={state.page === 1}
              onClick={() => setState(prev => ({ ...prev, page: prev.page - 1 }))}
            >
              Previous
            </button>
            <span className="page-info">
              Page {state.page} of {totalPages}
            </span>
            <button
              className="btn-secondary"
              disabled={state.page >= totalPages}
              onClick={() => setState(prev => ({ ...prev, page: prev.page + 1 }))}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
