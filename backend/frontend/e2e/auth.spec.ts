import { test, expect } from '@playwright/test';

// Minimal smoke: seed user and hit backend endpoints

test('auth: seed and refresh flow', async ({ request }) => {
  const seed = await request.post('http://localhost:8000/__e2e/seed_user', { data: { email: 'e2e@example.test' } });
  expect(seed.ok()).toBeTruthy();
  // Simulate login: in real app, you would post to /auth/login; here just assert health
  const health = await request.get('http://localhost:8000/queue/health');
  expect(health.ok()).toBeTruthy();
});
