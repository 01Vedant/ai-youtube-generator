/**
 * Toast notification system with pub-sub pattern.
 * Fully typed; no implicit any.
 */

export type ToastType = 'success' | 'warning' | 'error' | 'info';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
  link?: { text: string; href: string };
}

type ToastListener = (toast: Toast) => void;
type DismissListener = (id: string) => void;

class ToastManager {
  private listeners: ToastListener[] = [];
  private dismissListeners: DismissListener[] = [];
  private toastId = 0;

  subscribe(listener: ToastListener): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  onDismiss(listener: DismissListener): () => void {
    this.dismissListeners.push(listener);
    return () => {
      this.dismissListeners = this.dismissListeners.filter((l) => l !== listener);
    };
  }

  show(
    message: string,
    type: ToastType = 'info',
    duration = 4000,
    link?: { text: string; href: string }
  ): string {
    const id = `toast-${++this.toastId}`;
    const toast: Toast = { id, message, type, duration, link };
    this.listeners.forEach((listener) => {
      listener(toast);
    });
    if (duration > 0) {
      setTimeout(() => {
        this.dismiss(id);
      }, duration);
    }
    return id;
  }

  dismiss(id: string): void {
    this.dismissListeners.forEach((listener) => {
      listener(id);
    });
  }

  success(message: string, duration?: number): string {
    return this.show(message, 'success', duration);
  }

  warning(message: string, duration?: number): string {
    return this.show(message, 'warning', duration ?? 5000);
  }

  error(message: string, duration?: number): string {
    return this.show(message, 'error', duration ?? 6000);
  }

  info(message: string, duration?: number): string {
    return this.show(message, 'info', duration);
  }
}

export const toast = new ToastManager();
