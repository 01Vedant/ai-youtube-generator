function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export type RetryOpts = {
  retries?: number; // default 3
  baseMs?: number; // default 400
  maxMs?: number; // default 3000
  jitter?: number; // default 0.2
  respectRetryAfter?: boolean; // default true
};

export async function retry<T>(fn: () => Promise<T>, opts: RetryOpts = {}): Promise<T> {
  const {
    retries = 3,
    baseMs = 400,
    maxMs = 3000,
    jitter = 0.2,
    respectRetryAfter = true,
  } = opts;

  let attempt = 0;
  while (true) {
    try {
      return await fn();
    } catch (err: unknown) {
      attempt += 1;
      const isTypeErr = err instanceof TypeError; // network failure in fetch
      const status = (err as any)?.status as number | undefined;
      const retryAfterSeconds = (err as any)?.retryAfterSeconds as number | undefined;

      const shouldRetry = isTypeErr || status === 429 || (typeof status === 'number' && status >= 500 && status < 600);
      if (!shouldRetry || attempt > retries) throw err;

      let delay = Math.min(maxMs, baseMs * Math.pow(2, attempt - 1));
      // Respect Retry-After header when applicable
      if (respectRetryAfter && status === 429 && typeof retryAfterSeconds === 'number') {
        delay = Math.min(maxMs, Math.max(0, Math.round(retryAfterSeconds * 1000)));
      } else {
        const j = 1 + (Math.random() * 2 - 1) * jitter; // 1 ± jitter
        delay = Math.round(delay * j);
      }
      await sleep(delay);
    }
  }
}
