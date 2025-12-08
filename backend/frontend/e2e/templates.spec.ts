import { test, expect } from '@playwright/test';

const FLAG = (process.env.VITE_FEATURE_TEMPLATES_MARKETPLACE ?? '0') === '1';

test('templates list reachable', async ({ request }) => {
  const res = await request.get('http://localhost:8000/templates/templates');
  expect(res.ok()).toBeTruthy();
});

test('marketplace flag gating', async ({ request }) => {
  const res = await request.get('http://localhost:8000/marketplace/templates');
  if (FLAG) {
    expect(res.status()).toBe(200);
  } else {
    expect(res.status()).toBe(404);
  }
});
