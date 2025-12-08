import { toast } from './toast';

export type ToastOpts<T = unknown> = {
  pending?: string;
  success?: string | ((result: T) => string | void | null | undefined);
  error?: string | ((err: unknown) => string | void | null | undefined);
  stickyOnError?: boolean;
};

export function showToast(message: string, type: 'success' | 'warning' | 'error' | 'info' = 'info'): string {
  return toast.show(message, type);
}

export async function withToast<T>(op: () => Promise<T>, opts: ToastOpts<T> = {}): Promise<T> {
  const { pending, success, error, stickyOnError = true } = opts;
  const pendingId = pending ? toast.info(pending) : undefined;

  try {
    const res = await op();
    const msg = typeof success === 'function' ? success(res) : success;
    if (pendingId) toast.dismiss(pendingId);
    if (msg) toast.success(msg);
    return res;
  } catch (err) {
    const msg = typeof error === 'function'
      ? error(err)
      : error ?? (err instanceof Error ? err.message : 'Something went wrong');
    if (pendingId) toast.dismiss(pendingId);
    if (msg) {
      if (stickyOnError) {
        toast.error(msg, Infinity);
      } else {
        toast.error(msg);
      }
    }
    throw err;
  }
}

export function withStickyToast<T>(op: () => Promise<T>, opts: ToastOpts<T> = {}): Promise<T> {
  return withToast(op, { ...opts, stickyOnError: opts.stickyOnError ?? true });
}

export { toast };
