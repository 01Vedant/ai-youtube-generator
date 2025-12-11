import { test, expect } from '@playwright/test';

test('app loads and shows something', async ({ page }) => {
  const base = process.env.PW_BASE_URL || 'http://127.0.0.1:5173';
  await page.goto(base + '/');

  // Basic sanity check: page renders
  await expect(page.locator('body')).toBeVisible();
});
