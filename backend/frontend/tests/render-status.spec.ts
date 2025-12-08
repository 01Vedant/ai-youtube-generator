import { test, expect } from '@playwright/test';

test.describe('Render Status error callout', () => {
  test('shows structured error banner and stays interactive', async ({ page }) => {
    const jobId = 'job-error-1';

    // Intercept status API for this job
    await page.route(`**/api/render/${jobId}/status`, async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'failed',
          error: { code: 'TTS_FAILURE', phase: 'tts', message: 'Voice not available' },
        }),
      });
    });

    await page.goto(`/render/${jobId}`);

    // Assert inline error banner shows structured values
    const banner = page.locator('.alert', { hasText: 'TTS_FAILURE' });
    await expect(banner).toBeVisible();
    await expect(page.locator('.alert')).toContainText('tts');
    await expect(page.locator('.alert')).toContainText('Voice not available');

    // Page should remain interactive – e.g., buttons or links present
    const anyButton = page.locator('button');
    await expect(anyButton.first()).toBeVisible();
  });
});
