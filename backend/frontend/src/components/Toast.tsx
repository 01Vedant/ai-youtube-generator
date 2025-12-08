/**
 * Toast container component for rendering notifications.
 * Fully typed React component.
 */

import React, { useEffect, useState } from 'react';
import { toast, Toast } from '../lib/toast';
import './Toast.css';

export const ToastContainer: React.FC = () => {
  const [toasts, setToasts] = useState<Map<string, Toast>>(new Map());

  useEffect(() => {
    const unsubscribe = toast.subscribe((t: Toast) => {
      setToasts((prev) => new Map(prev).set(t.id, t));
    });

    const unsubscribeDismiss = toast.onDismiss((id: string) => {
      setToasts((prev) => {
        const next = new Map(prev);
        next.delete(id);
        return next;
      });
    });

    return () => {
      unsubscribe();
      unsubscribeDismiss();
    };
  }, []);

  return (
    <div className="toast-container">
      {Array.from(toasts.values()).map((t) => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          <div className="toast-content">
            <span className="toast-message">{t.message}</span>
            {t.link && (
              <a
                href={t.link.href}
                target="_blank"
                rel="noreferrer"
                className="toast-link"
              >
                {t.link.text}
              </a>
            )}
          </div>
          <button
            className="toast-dismiss"
            onClick={() => {
              toast.dismiss(t.id);
            }}
            aria-label="Dismiss notification"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
};
