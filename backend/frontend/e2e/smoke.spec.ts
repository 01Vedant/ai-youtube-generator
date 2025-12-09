import { test, expect } from "@playwright/test";

test("Create Story -> thumbnails appear", async ({ page }) => {
  // Go to root and wait until network is idle to avoid early clicks
  await page.goto("/", { waitUntil: "networkidle" });

  // Click CTA using data-testid (stable selector)
  await page.getByTestId("create-story-cta").click();

  // Fill form using accessible labels
  await page.getByLabel(/title/i).fill("Smoke");
  await page.getByLabel(/description/i).fill("Smoke");
  await page.getByLabel(/duration/i).fill("30");

  // Submit (keep existing role-based query or give submit a data-testid="create-story-submit")
  await page.getByRole("button", { name: /create/i }).click();

  // Assert progress card becomes visible
  await expect(page.getByTestId("job-progress-card")).toBeVisible();

  // Wait for at least one scene thumbnail
  await page.waitForSelector('[data-testid^="scene-thumb-"]', { timeout: 60_000 });
});
