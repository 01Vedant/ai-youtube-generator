import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getProject, unassignFromProject } from '@/lib/api';
import type { Project } from '@/types/projects';
import ArtifactCard from '@/components/ArtifactCard';

type Entry = { id: string; title: string; created_at: string };

export default function ProjectDetailPage(): JSX.Element {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getProject(id);
        setProject(res.project);
        setEntries(res.entries);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load project');
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  const handleUnassign = async (jobId: string) => {
    if (!id) return;
    try {
      await unassignFromProject(id, jobId);
      setEntries(prev => prev.filter(e => e.id != jobId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unassign failed');
    }
  };

  if (loading) return <div className="container">Loading…</div>;
  if (error) return <div className="container" role="alert">{error}</div>;
  if (!project) return <div className="container">Not found</div>;

  return (
    <div className="container" style={{ padding: '1rem' }}>
      <button className="btn btn-secondary" onClick={() => navigate('/projects')}>Back</button>
      <h1 style={{ marginTop: 8 }}>{project.title}</h1>
      {project.description && <p style={{ color: '#444' }}>{project.description}</p>}

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4" style={{ marginTop: '1rem' }}>
        {entries.map(e => (
          <div key={e.id}>
            <ArtifactCard
              id={e.id}
              title={e.title || `Job ${e.id.slice(0, 8)}`}
              thumbnailUrl={`/artifacts/${e.id}/thumb.png`}
              createdAt={e.created_at}
              onClick={() => navigate(`/render/${e.id}`)}
            />
            <div style={{ marginTop: 6 }}>
              <button className="btn btn-secondary" onClick={() => void handleUnassign(e.id)}>Unassign</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
