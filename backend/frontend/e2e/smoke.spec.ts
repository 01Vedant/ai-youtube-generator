import { test, expect } from '@playwright/test';

test('Create Story -> thumbnails appear', async ({ page }) => {
  const base = (process.env.PW_BASE_URL || 'http://localhost:5173').trim().replace(/\/+$/, '');
  await page.goto(`${base}/?e2e=1`, { waitUntil: 'domcontentloaded' });

  const createBtn = page.getByTestId('create-story')
    .or(page.getByRole('button', { name: /create (story|video)/i }).first());
  await expect(createBtn).toBeVisible({ timeout: 15_000 });
  await createBtn.click();

  const modal = page.getByTestId('create-story-modal');
  const modalVisible = modal.waitFor({ state: 'visible', timeout: 15_000 }).catch(() => null);
  const routeChanged = page.waitForURL('**/create*', { timeout: 15_000 }).catch(() => null);
  await Promise.race([modalVisible, routeChanged]);

  const title = page.getByTestId('title-input').or(page.getByLabel(/title/i)).first();
  const desc  = page.getByTestId('description-input').or(page.getByLabel(/description/i)).first();
  const full  = page.getByTestId('fulltext-input').or(page.getByLabel(/(full\\s*text|body|content)/i)).first();

  await title.fill('E2E Smoke Title');
  await desc.fill('Short description');
  await full.fill('Body text for E2E');

  const submit = page.getByTestId('submit-create')
    .or(page.getByRole('button', { name: /(create|render|start)/i })).first();
  await submit.click();

  await expect(page.getByTestId('thumbnail')).toBeVisible({ timeout: 30_000 });
});
