import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';
import RenderStatusPage from '@/pages/RenderStatusPage';

const getRender = vi.fn();

vi.mock('@/lib/api', () => ({
  getRender: (...args: unknown[]) => getRender(...args),
}));

describe('RenderStatusPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function renderWithRouter(): void {
    render(
      <MemoryRouter initialEntries={['/render/job-123']}>
        <Routes>
          <Route path="/render/:jobId" element={<RenderStatusPage />} />
        </Routes>
      </MemoryRouter>
    );
  }

  it('polls render status and shows artifacts when complete', async () => {
    getRender.mockResolvedValue({
      id: 'job-123',
      status: 'success',
      artifacts: [
        { type: 'video', url: '/videos/job-123.mp4' },
        { type: 'image', url: '/thumbs/job-123.png' },
      ],
      error: null,
    });

    renderWithRouter();

    await waitFor(() => expect(getRender).toHaveBeenCalledWith('job-123'));
    expect(await screen.findByText('success')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /thumbnail/i })).toBeInTheDocument();
  });

  it('shows an error message when fetch fails', async () => {
    getRender.mockRejectedValueOnce(new Error('boom'));

    renderWithRouter();

    expect(await screen.findByText(/failed to load render/i)).toBeInTheDocument();
  });
});
