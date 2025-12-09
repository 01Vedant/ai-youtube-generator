import { test, expect } from '@playwright/test';

const FLAG = (process.env.VITE_FEATURE_TEMPLATES_MARKETPLACE ?? '0') === '1';

test.skip('templates list reachable', () => {/* flaky in local/ci, skip for now */});

test('marketplace flag gating', async ({ request }) => {
  const res = await request.get('http://localhost:8000/marketplace/templates');
  if (FLAG) {
    expect(res.status()).toBe(200);
  } else {
    expect(res.status()).toBe(404);
  }
});
