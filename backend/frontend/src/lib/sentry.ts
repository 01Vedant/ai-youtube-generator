/**
 * Sentry Error Tracking - Stub implementation (Sentry removed for React 19 compatibility)
 * No-op fallback - all functions are stubs
 */

/**
 * Initialize Sentry (stub - does nothing)
 */
export async function initSentry(): Promise<void> {
  console.debug('[sentry] Stub mode - error tracking disabled for React 19 compatibility');
}

/**
 * Capture an exception (stub - logs to console in dev)
 */
export function captureException(
  err: unknown,
  context?: Record<string, unknown>
): void {
  const isDev = import.meta.env.MODE === 'development';
  if (isDev) {
    console.error('[error]', err, context);
  }
}

