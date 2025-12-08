export function showToast(msg: string) {
  alert(msg);
}
import { toast } from '@/lib/toast';

type ToastOpts<T> = {
  pending?: string;
  success?: string | ((res: T) => string);
  error?: string | ((err: unknown) => string);
  stickyOnError?: boolean; // default true
};

export function withToast<T>(p: Promise<T>, pending?: string, success?: string, fail?: string) {
  // if you have a toast lib that supports loading(), keep it, else fallback:
  if (pending) console.log(pending);
  return p.then((res) => {
    if (success) console.log(success);
    return res;
  }).catch((err) => {
    if (fail) console.error(fail);
    throw err;
  });
}
import { toast } from '@/lib/toast';

type ToastOpts<T> = {
  pending?: string;
  success?: string | ((res: T) => string);
  error?: string | ((err: unknown) => string);
  stickyOnError?: boolean; // default true
};

export async function withStickyToast<T>(op: () => Promise<T>, opts: ToastOpts<T> = {}): Promise<T> {
  const { pending, success, error, stickyOnError = true } = opts;
  const id = pending ? toast.loading(pending) : undefined;
  try {
    const res = await op();
    const msg = typeof success === 'function' ? success(res) : success;
    if (id) toast.dismiss(id);
    if (msg) toast.success(msg);
    return res;
  } catch (err) {
    const msg = typeof error === 'function' ? error(err) : (error ?? (err instanceof Error ? err.message : 'Something went wrong'));
    if (id) toast.dismiss(id);
    if (stickyOnError) {
      toast.error(msg, { duration: Infinity });
    } else {
      toast.error(msg);
    }
    throw err;
  }
}
