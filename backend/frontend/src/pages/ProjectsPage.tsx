// Moved to _disabled
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listProjects, createProject, sendOnboardingEvent } from '@/lib/api';
import type { Project } from '@/types/projects';

export default function ProjectsPage(): JSX.Element {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await listProjects();
        setProjects(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load projects');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    if (!loading && projects.length === 0) {
      sendOnboardingEvent('empty_projects_seen').catch(() => {});
    }
  }, [loading, projects.length]);

  const handleCreate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!title.trim()) return;
    try {
      const p = await createProject({ title: title.trim(), description: description || undefined });
      setProjects(prev => [p, ...prev]);
      try { await sendOnboardingEvent('created_project'); } catch {}
      setShowNew(false);
      setTitle('');
      setDescription('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed');
    }
  };

  return (
    <div className="container" style={{ padding: '1rem' }}>
      <h1>Projects</h1>
      <div style={{ margin: '0.5rem 0 1rem' }}>
        <button onClick={() => setShowNew(s => !s)} className="btn btn-primary">New Project</button>
      </div>

      {showNew && (
        <form onSubmit={handleCreate} style={{ marginBottom: '1rem' }}>
          <label htmlFor="p-title">Title</label>
          <input id="p-title" type="text" value={title} onChange={(e) => setTitle(e.target.value)} required />
          <label htmlFor="p-desc">Description</label>
          <input id="p-desc" type="text" value={description} onChange={(e) => setDescription(e.target.value)} />
          <button type="submit" className="btn btn-primary" style={{ marginTop: 8 }}>Create</button>
        </form>
      )}

      {error && <div role="alert" style={{ color: '#b00020' }}>{error}</div>}
      {projects.length === 0 && !loading && (
        <div className="empty-state-card" style={{ marginTop: 12 }}>
          <h3 className="text-sm font-semibold">Create your first project</h3>
          <p className="text-xs text-gray-600">Start by creating a project, then render and export your first video.</p>
          <button className="btn btn-primary" onClick={() => setShowNew(true)}>Create</button>
        </div>
      )}
      {loading ? (
        <div>Loading…</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {projects.map(p => (
            <div key={p.id} className="card" role="button" onClick={() => navigate(`/projects/${p.id}`)}>
              {p.cover_thumb ? (
                <img src={p.cover_thumb} alt="cover" style={{ width: '100%', height: 120, objectFit: 'cover' }} />
              ) : (
                <div style={{ width: '100%', height: 120, background: '#eee', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>No cover</div>
              )}
              <div style={{ padding: '0.5rem' }}>
                <div style={{ fontWeight: 600 }}>{p.title}</div>
                <div style={{ fontSize: 12, color: '#666' }}>{new Date(p.created_at).toLocaleString()}</div>
                <div style={{ marginTop: 4 }}>
                  <span className="badge">{p.video_count ?? 0} videos</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
