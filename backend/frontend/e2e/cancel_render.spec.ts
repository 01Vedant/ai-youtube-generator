import { test, expect, request as playwrightRequest } from '@playwright/test';

test('user can cancel a render job', async () => {
  const apiBase = process.env.PW_API_URL || 'http://127.0.0.1:8000';
  const api = await playwrightRequest.newContext({ baseURL: apiBase });

  const payload = {
    topic: 'e2e cancel',
    language: 'en',
    voice: 'F',
    fast_path: true,
    proxy: false,
    scenes: [
      { image_prompt: 'A serene temple at sunrise', narration: 'Hello world', duration_sec: 1.0 },
    ],
  };

  const createResp = await api.post('/render', { data: payload });
  if (!createResp.ok()) {
    const bodyText = await createResp.text();
    console.error('Create render failed:', bodyText);
  }
  expect(createResp.ok()).toBeTruthy();
  const createBody = await createResp.json();
  const jobId: string = createBody.job_id;
  expect(jobId).toBeTruthy();

  const cancelResp1 = await api.post(`/render/${jobId}/cancel`);
  expect(cancelResp1.status()).toBe(200);

  const cancelResp2 = await api.post(`/render/${jobId}/cancel`);
  expect(cancelResp2.status()).toBe(200);

  let seenCanceled = false;
  for (let i = 0; i < 10; i++) {
    const statusResp = await api.get(`/render/${jobId}/status`);
    if (statusResp.ok()) {
      const statusBody = await statusResp.json();
      const s = String(statusBody.status || '').toLowerCase();
      if (s.includes('cancel')) {
        seenCanceled = true;
        break;
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  expect(seenCanceled).toBeTruthy();
});
