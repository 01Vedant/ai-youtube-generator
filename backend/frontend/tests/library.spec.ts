import { test, expect } from '@playwright/test';

// Mocked library entries generator
function makeEntries(count: number, offset = 0) {
  return Array.from({ length: count }).map((_, i) => {
    const id = `job-${offset + i + 1}`;
    return {
      id,
      title: `Video ${offset + i + 1}`,
      created_at: new Date(Date.now() - (offset + i) * 10_000).toISOString(),
      thumbnail_url: `/artifacts/${id}/thumb.png`,
      video_url: `/artifacts/${id}/final.mp4`,
      duration_sec: 61 + i,
      voice: 'Swara',
      template: 'Default',
      state: 'completed',
    };
  });
}

test.describe('Library browse/search/sort', () => {
  test.beforeEach(async ({ page }) => {
    // Intercept fetchLibrary API calls – adjust path as needed
    await page.route('**/api/library**', async (route) => {
      const url = new URL(route.request().url());
      const pageParam = Number(url.searchParams.get('page') || '1');
      const sort = url.searchParams.get('sort') || 'created_at:desc';
      const query = url.searchParams.get('query') || '';

      let entries = makeEntries(8, (pageParam - 1) * 8);

      if (query) {
        entries = entries.filter(e => (e.title ?? '').toLowerCase().includes(query.toLowerCase()));
      }

      if (sort === 'created_at:asc') {
        entries = entries.slice().reverse();
      }

      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({ entries, total: 24 }),
      });
    });
  });

  test('grid renders, search updates URL/cards, sort and pagination work', async ({ page }) => {
    await page.goto('/');

    // Navigate to Library (assumes link exists; fallback directly)
    const libraryLink = page.locator('a[href="/library"]');
    if (await libraryLink.count()) {
      await libraryLink.first().click();
    } else {
      await page.goto('/library');
    }

    // Grid/cards render
    const cards = page.locator('.artifact-card');
    await expect(cards.first()).toBeVisible();

    // Enter search query
    const searchInput = page.getByLabel('Search library').or(page.locator('#query-filter'));
    await searchInput.fill('video 1');
    // Debounce wait
    await page.waitForTimeout(400);
    await expect(page).toHaveURL(/\?[^#]*query=video%201/);

    // Change sort
    const sortSelect = page.getByLabel('Sort library').or(page.locator('#sort-filter'));
    await sortSelect.selectOption('created_at:asc');
    await expect(page).toHaveURL(/\?[^#]*sort=created_at:asc/);

    // Paginate to page 2
    const nextBtn = page.getByRole('button', { name: /Next/ });
    await nextBtn.click();
    await expect(page).toHaveURL(/\?[^#]*page=2/);

    // Cards update
    await expect(cards.nth(0)).toBeVisible();
  });
});
