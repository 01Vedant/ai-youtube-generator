import { test, expect } from '@playwright/test';

test.describe('simple mode render', () => {
  test('one-click simple render flow', async ({ page, context }) => {
    const base = process.env.PW_BASE_URL || 'http://127.0.0.1:5173';
    const jobId = 'simple-e2e-job';

    await context.addInitScript(() => {
      localStorage.setItem('auth_tokens', JSON.stringify({ access_token: 'test', refresh_token: 'test' }));
    });

    await context.route('**/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 'test-user', email: 'test@example.com', plan_id: 'free', roles: [] }),
      });
    });

    await context.route('**/render/simple', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ job_id: jobId }),
      });
    });

    await context.route(`**/render/${jobId}/status`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ job_id: jobId, status: 'queued' }),
      });
    });

    await page.goto(`${base}/create`);

    await page.fill('#simple-topic', 'Playwright Simple Mode');
    await page.selectOption('#simple-voice', 'F');
    await page.getByTestId('simple-generate-render').click();

    await expect(page).toHaveURL(/\/renders\//);
    await expect(page.getByTestId('cancel-render')).toBeVisible();
  });
});
