import { test, expect } from '@playwright/test';

test('Create Story -> thumbnails appear', async ({ page }) => {
  await page.goto('/');

  const createBtn = page.getByTestId('create-story')
    .or(page.getByRole('button', { name: /create (story|video)/i }).first());
  await expect(createBtn).toBeVisible();
  await createBtn.click();

  const title = page.getByTestId('title-input').or(page.getByLabel(/title/i).first());
  const desc  = page.getByTestId('description-input').or(page.getByLabel(/description/i).first());
  const dur   = page.getByTestId('duration-input').or(page.getByLabel(/duration/i).first());

  await title.fill('Smoke');
  await desc.fill('Smoke');
  await dur.fill('30');

  const submit = page.getByTestId('submit-create')
    .or(page.getByRole('button', { name: /create|render|start/i }).first());
  await submit.click();

  await page.waitForLoadState('networkidle');
  const thumb = page.locator('img, [data-testid="thumbnail"]').first();
  await expect(thumb).toBeVisible({ timeout: 15000 });
});
