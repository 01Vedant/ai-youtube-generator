import { test, expect } from '@playwright/test';

test('Create Story -> thumbnails appear', async ({ page }) => {
  const base = (process.env.PW_BASE_URL || 'http://localhost:5173').trim().replace(/\/+$/, '');
  await page.goto(`${base}/?e2e=1`, { waitUntil: 'domcontentloaded' });

  const createBtn = page.getByTestId('create-story').first();
  await expect(createBtn).toBeVisible({ timeout: 15_000 });
  await createBtn.click();

  const modal = page.getByTestId('create-story-modal');
  await expect(modal).toBeVisible({ timeout: 15_000 });

  await page.getByTestId('title-input').fill('E2E Smoke Title');
  await page.getByTestId('description-input').fill('Short description');
  await page.getByTestId('fulltext-input').fill('Body text for E2E');

  await page.getByTestId('submit-create').click();

  await page.waitForLoadState('networkidle');
  const thumb = page.getByTestId('thumbnail').first();
  await thumb.waitFor({ state: 'visible', timeout: 25_000 });
});
