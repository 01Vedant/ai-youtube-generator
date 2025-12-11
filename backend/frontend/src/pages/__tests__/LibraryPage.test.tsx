import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LibraryPage } from '@/pages/LibraryPage';

vi.mock('@/components/ArtifactCard', () => ({
  __esModule: true,
  default: ({ title, onClick }: { title: string; onClick: () => void }) => (
    <div data-testid="artifact-card" onClick={onClick}>
      {title}
    </div>
  ),
}));

const fetchLibrary = vi.fn();
const listProjects = vi.fn();
const createShare = vi.fn();
const getProject = vi.fn();

vi.mock('@/lib/api', () => ({
  fetchLibrary: (...args: unknown[]) => fetchLibrary(...args),
  listProjects: (...args: unknown[]) => listProjects(...args),
  createShare: (...args: unknown[]) => createShare(...args),
  getProject: (...args: unknown[]) => getProject(...args),
}));

vi.mock('@/lib/analytics', () => ({ track: vi.fn() }));
vi.mock('@/lib/toasts', () => ({ showToast: vi.fn(), withStickyToast: vi.fn() }));
vi.mock('@/lib/toast', () => ({ toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() } }));

describe('LibraryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it('renders library entries and shares a link', async () => {
    fetchLibrary.mockResolvedValue({
      entries: [
        {
          id: 'job-1',
          title: 'My Render',
          created_at: '2024-01-01T00:00:00Z',
          duration_sec: 30,
          voice: 'Swara',
          template: 'default',
          state: 'success',
          thumbnail_url: '/artifacts/job-1/thumb.png',
          video_url: '/artifacts/job-1/final.mp4',
        },
      ],
      total: 1,
      page: 1,
      pageSize: 20,
    });
    listProjects.mockResolvedValue([]);
    createShare.mockResolvedValue({ share_id: 'share-1', url: '/s/share-1' });

    render(
      <MemoryRouter>
        <LibraryPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('My Render')).toBeInTheDocument();
    const shareButton = await screen.findByRole('button', { name: /share/i });
    fireEvent.click(shareButton);

    await waitFor(() => expect(createShare).toHaveBeenCalledWith('job-1'));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('/s/share-1');
  });

  it('shows an empty state when there are no entries', async () => {
    fetchLibrary.mockResolvedValue({ entries: [], total: 0, page: 1, pageSize: 20 });
    listProjects.mockResolvedValue([]);

    render(
      <MemoryRouter>
        <LibraryPage />
      </MemoryRouter>
    );

    expect(await screen.findByText(/export your first video/i)).toBeInTheDocument();
  });
});
