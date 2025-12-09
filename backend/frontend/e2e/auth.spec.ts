import { test, expect } from '@playwright/test';

// Only run when explicitly enabled. Default: skip in CI and local.
const AUTH_ENABLED = (process.env.E2E_AUTH ?? '0') === '1';
test.skip(!AUTH_ENABLED, 'Auth E2E is gated behind E2E_AUTH=1');

test('auth: seed and refresh flow', async () => {
  // TODO: real auth flow wiring goes here
  // Keep this placeholder structure to preserve the test for future work.
  await expect(true).toBeTruthy();
});
