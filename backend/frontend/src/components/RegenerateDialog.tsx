import React, { useEffect, useMemo, useState } from 'react';
import { regenerateJob, type RegenerateOverrides } from '@/lib/api';
import { toast } from '@/lib/toast';
import { withStickyToast } from '@/lib/toasts';
import { useAuth } from '@/state/auth';

export interface RegenerateDialogProps {
  open: boolean;
  onClose: () => void;
  jobId: string;
  initial: { title?: string; voice?: 'Swara' | 'Diya'; template?: string; duration_sec?: number };
  onQueued?: (newJobId: string) => void;
}

const fieldLabel: Record<keyof NonNullable<RegenerateDialogProps['initial']>, string> = {
  title: 'Title',
  voice: 'Voice',
  template: 'Template',
  duration_sec: 'Duration (sec)'
};

export const RegenerateDialog: React.FC<RegenerateDialogProps> = ({ open, onClose, jobId, initial, onQueued }) => {
  const { user } = useAuth();
  const [title, setTitle] = useState<string>('');
  const [voice, setVoice] = useState<'Swara' | 'Diya' | ''>('');
  const [template, setTemplate] = useState<string>('');
  const [durationSec, setDurationSec] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);
  const isFree = (user?.plan_id ?? 'free') === 'free';

  useEffect(() => {
    if (!open) return;
    setTitle(initial.title ?? '');
    setVoice(initial.voice ?? '');
    setTemplate(initial.template ?? '');
    setDurationSec(
      typeof initial.duration_sec === 'number' && isFinite(initial.duration_sec)
        ? String(initial.duration_sec)
        : ''
    );
  }, [open, initial]);

  const overrides: RegenerateOverrides = useMemo(() => {
    const o: RegenerateOverrides = {};
    if (title.trim()) o.title = title.trim();
    if (voice === 'Swara' || voice === 'Diya') o.voice = voice;
    if (template.trim()) o.template = template.trim();
    if (durationSec.trim()) {
      const n = Number(durationSec);
      if (!Number.isNaN(n) && n > 0) o.duration_sec = n;
    }
    return o;
  }, [title, voice, template, durationSec]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!open || submitting) return;
    setSubmitting(true);
    try {
      const res = await withStickyToast(() => regenerateJob(jobId, overrides), {
        pending: 'Queuing new render…',
        success: () => 'Queued new render',
        error: (e) => e instanceof Error ? e.message : 'Failed to enqueue',
      });
      if (onQueued) onQueued(res.job_id);
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to enqueue';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={onClose} role="presentation">
      <div
        className="w-full max-w-md rounded-lg border bg-white p-4 shadow-md"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="regen-dialog-title"
      >
        <header className="flex items-center justify-between mb-3">
          <h2 id="regen-dialog-title" className="text-lg font-semibold">Regenerate</h2>
          <button className="text-gray-500 hover:text-gray-700" aria-label="Close" onClick={onClose}>✕</button>
        </header>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1" htmlFor="regen-title">{fieldLabel.title}</label>
            <input
              id="regen-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded border px-2 py-1 text-sm"
              placeholder="e.g., Morning Bhakti Short"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1" htmlFor="regen-voice">{fieldLabel.voice}</label>
            <select
              id="regen-voice"
              value={voice}
              onChange={(e) => setVoice((e.target.value as 'Swara' | 'Diya' | ''))}
              className="w-full rounded border px-2 py-1 text-sm"
            >
              <option value="">—</option>
              <option value="Swara">Swara</option>
              <option value="Diya">Diya</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1" htmlFor="regen-template">{fieldLabel.template}</label>
            <input
              id="regen-template"
              type="text"
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              className="w-full rounded border px-2 py-1 text-sm"
              placeholder="e.g., classic-title"
            />
            {isFree && template && template.toLowerCase().includes('pro') && (
              <div className="mt-1 text-xs text-orange-700 bg-orange-50 border border-orange-200 rounded px-2 py-1">
                Template might be Pro-only. <button className="underline" onClick={() => toast.info('Upgrade to Pro to use premium templates')}>Go Pro</button>
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-1" htmlFor="regen-duration">{fieldLabel.duration_sec}</label>
            <input
              id="regen-duration"
              type="number"
              min={1}
              value={durationSec}
              onChange={(e) => setDurationSec(e.target.value)}
              className="w-full rounded border px-2 py-1 text-sm"
              placeholder="e.g., 30"
            />
          </div>

          <footer className="mt-4 flex items-center justify-end gap-2">
            <button type="button" className="text-sm px-3 py-1 border rounded" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="text-sm px-3 py-1 border rounded bg-black text-white" disabled={submitting}>
              {submitting ? '⏳ Queuing...' : '⚡ Regenerate'}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
};
