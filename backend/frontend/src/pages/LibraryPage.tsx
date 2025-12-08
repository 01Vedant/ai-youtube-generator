import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import ArtifactCard from '@/components/ArtifactCard';
import type { LibraryItem } from '@/types/library';
import { createShare, fetchLibrary, getProject, listProjects } from '@/lib/api';
import { track } from '@/lib/analytics';
import { toast } from '@/lib/toast';
import { showToast } from '@/lib/toasts';
import './LibraryPage.css';

const SHARES_ENABLED = (import.meta.env.VITE_PUBLIC_SHARES_ENABLED ?? 'true') !== 'false';

type SortType = 'created_at:desc' | 'created_at:asc';

export function LibraryPage(): JSX.Element {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [entries, setEntries] = useState<LibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState<number>(0);
  const [query, setQuery] = useState<string>('');
  const [projectId, setProjectId] = useState<string>('');
  const [projects, setProjects] = useState<Array<{ id: string; title: string }>>([]);
  const [sort, setSort] = useState<SortType>('created_at:desc');

  const loadLibrary = useCallback(
    async (pageNum: number, nextQuery?: string, nextSort?: SortType, nextPageSize?: number, nextProjectId?: string): Promise<void> => {
      setLoading(true);
      setError(null);
      try {
        const activeProject = (nextProjectId ?? projectId) || '';
        if (activeProject) {
          const detail = await getProject(activeProject);
          setEntries(
            detail.entries.map((e) => ({
              id: e.id,
              title: e.title,
              created_at: e.created_at,
              duration_sec: 0,
              voice: 'Swara',
              template: 'default',
              thumbnail_url: `/artifacts/${e.id}/thumb.png`,
              video_url: undefined,
            }))
          );
          setTotal(detail.total);
        } else {
          const response = await fetchLibrary({
            page: pageNum,
            pageSize: nextPageSize ?? pageSize,
            query: (nextQuery ?? query) || undefined,
            sort: nextSort ?? sort,
          });
          setEntries(response.entries);
          setTotal(response.total);
        }
        setPage(pageNum);
        track('library_opened', { page: pageNum, total, query: nextQuery ?? query, sort: nextSort ?? sort, projectId: activeProject });
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load library';
        setError(message);
        console.error('Failed to load library:', err);
        toast.error(message);
      } finally {
        setLoading(false);
      }
    },
    [pageSize, query, sort, projectId, total]
  );

  useEffect(() => {
    const urlPage = parseInt(searchParams.get('page') || '1', 10);
    const urlPageSize = parseInt(searchParams.get('pageSize') || '20', 10);
    const urlQuery = searchParams.get('query') || '';
    const rawSort = searchParams.get('sort');
    const urlSort: SortType = rawSort === 'created_at:asc' ? 'created_at:asc' : 'created_at:desc';
    const urlProjectId = searchParams.get('projectId') || '';

    setPage(Number.isFinite(urlPage) && urlPage > 0 ? urlPage : 1);
    setPageSize(Number.isFinite(urlPageSize) && urlPageSize > 0 ? urlPageSize : 20);
    setQuery(urlQuery);
    setSort(urlSort);
    setProjectId(urlProjectId);

    void loadLibrary(Number.isFinite(urlPage) && urlPage > 0 ? urlPage : 1, urlQuery, urlSort, urlPageSize, urlProjectId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const handle = setTimeout(() => {
      setPage(1);
      void loadLibrary(1);
    }, 300);
    return () => clearTimeout(handle);
  }, [query, loadLibrary]);

  useEffect(() => {
    const params = new URLSearchParams();
    params.set('page', String(page));
    params.set('pageSize', String(pageSize));
    if (query) params.set('query', query);
    params.set('sort', sort);
    if (projectId) params.set('projectId', projectId);
    setSearchParams(params, { replace: true });
  }, [page, pageSize, query, sort, projectId, setSearchParams]);

  useEffect(() => {
    (async () => {
      try {
        const ps = await listProjects();
        setProjects(ps.map((p) => ({ id: p.id, title: p.title })));
      } catch {
        setProjects([]);
      }
    })();
  }, []);

  const handleViewStatus = (entry: LibraryItem): void => {
    navigate(`/render/${entry.id}`, {
      state: {
        from: 'library',
      },
    });
    track('library_opened', { job_id: entry.id });
  };

  const handleShare = async (jobId: string) => {
    if (!SHARES_ENABLED) return;
    try {
      const res = await createShare(jobId);
      showToast('Share link ready', 'success');
      await navigator.clipboard.writeText(res.url);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create share';
      showToast(message, 'error');
    }
  };

  return (
    <div className="library-page">
      <div className="container">
        <header className="library-header">
          <h1>My Library</h1>
          <p className="subtitle">Browse and reuse your past video projects</p>
        </header>

        {error && <div className="alert alert-error">{error}</div>}

        <section className="library-filters">
          <div className="filter-group">
            <label htmlFor="query-filter">Search</label>
            <input
              id="query-filter"
              type="text"
              placeholder="Search by title..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
              aria-label="Search library"
            />
          </div>
          <div className="filter-group">
            <label htmlFor="sort-filter">Sort</label>
            <select
              id="sort-filter"
              value={sort}
              onChange={(e) => {
                const next = e.target.value as SortType;
                setSort(next);
                setPage(1);
                void loadLibrary(1, undefined, next);
              }}
              aria-label="Sort library"
            >
              <option value="created_at:desc">Newest first</option>
              <option value="created_at:asc">Oldest first</option>
            </select>
          </div>
          <div className="filter-group">
            <label htmlFor="project-filter">Project</label>
            <select
              id="project-filter"
              value={projectId}
              onChange={(e) => {
                const pid = e.target.value;
                setProjectId(pid);
                setPage(1);
                void loadLibrary(1, undefined, undefined, undefined, pid);
              }}
              aria-label="Filter by project"
            >
              <option value="">(All)</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
          </div>
        </section>

        {loading ? (
          <div className="library-loading">
            <div className="spinner"></div>
            <p>Loading library...</p>
          </div>
        ) : entries.length === 0 ? (
          <div className="library-empty">
            <div className="empty-icon">[library]</div>
            <h2>Export your first video</h2>
            <p>You'll see exported videos here once a render completes.</p>
            <div className="empty-actions">
              <button
                className="btn btn-secondary"
                onClick={() => navigate('/create')}
                aria-label="Create your first project"
              >
                Create your first project
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {entries.map((entry) => {
                const label = entry.title ?? `Job ${entry.id.slice(0, 8)}`;
                return (
                  <div key={entry.id} style={{ display: 'grid', gap: 8 }}>
                    <ArtifactCard
                      id={entry.id}
                      title={label}
                      thumbnailUrl={entry.thumbnail_url || `/artifacts/${entry.id}/thumb.png`}
                      videoUrl={entry.video_url || undefined}
                      createdAt={entry.created_at}
                      durationSec={entry.duration_sec || undefined}
                      voice={entry.voice as 'Swara' | 'Diya' | undefined}
                      template={entry.template}
                      onClick={() => handleViewStatus(entry)}
                    />
                    {SHARES_ENABLED && (
                      <button className="btn btn-secondary" onClick={() => void handleShare(entry.id)}>
                        Share
                      </button>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="library-pagination">
              <button
                className="btn btn-secondary"
                onClick={() => void loadLibrary(page - 1)}
                disabled={page === 1}
                aria-label="Previous page"
              >
                Previous
              </button>

              <span className="pagination-info">
                Page {page} of {Math.ceil(total / pageSize)} ({total} total)
              </span>

              <button
                className="btn btn-secondary"
                onClick={() => void loadLibrary(page + 1)}
                disabled={page >= Math.ceil(total / pageSize)}
                aria-label="Next page"
              >
                Next
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default LibraryPage;
