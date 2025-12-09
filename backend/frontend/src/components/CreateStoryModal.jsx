import React, { useState } from 'react';
import { createProjectFromTitle } from '../services/api';

export default function CreateStoryModal({ open = true, onClose = () => {}, onSubmitted = () => {} }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [fullText, setFullText] = useState('');
  const [duration, setDuration] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const payload = { title, description, full_text: fullText };
      if (duration) payload.duration = Number(duration);
      const res = await createProjectFromTitle(payload);
      onSubmitted(res);
    } catch (err) {
      console.error(err);
      setError('Could not start job. Check connection.');
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-black opacity-60" onClick={onClose} />

      <div className="relative w-full max-w-2xl mx-4 bg-gradient-to-br from-white/5 to-white/2 border border-white/10 rounded-lg p-6 shadow-lg">
        <div className="flex items-start justify-between">
          <h2 className="text-xl font-semibold">Create Story</h2>
          <button aria-label="Close" onClick={onClose} className="text-white/70 hover:text-white">x</button>
        </div>

        <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="block text-sm font-medium" htmlFor="create-story-title">Title</label>
            <input
              id="create-story-title"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., The Devotion of Prahlad"
              aria-label="Title"
              className="mt-1 w-full rounded p-2 bg-black/50 border border-white/10"
            />
            <p className="text-xs text-white/60 mt-1">Short title used to generate scenes and filenames.</p>
          </div>

          <div>
            <label className="block text-sm font-medium" htmlFor="create-story-description">Short Description (optional)</label>
            <input
              id="create-story-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="One-line summary"
              aria-label="Description"
              className="mt-1 w-full rounded p-2 bg-black/50 border border-white/10"
            />
          </div>

          <div>
            <label className="block text-sm font-medium" htmlFor="create-story-duration">Duration (seconds)</label>
            <input
              id="create-story-duration"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              placeholder="30"
              inputMode="numeric"
              aria-label="Duration"
              className="mt-1 w-full rounded p-2 bg-black/50 border border-white/10"
            />
          </div>

          <div>
            <label className="block text-sm font-medium" htmlFor="create-story-full-text">Full Story Text (optional)</label>
            <textarea
              id="create-story-full-text"
              value={fullText}
              onChange={(e) => setFullText(e.target.value)}
              rows={5}
              placeholder="Paste full story or leave blank to use the title"
              className="mt-1 w-full rounded p-2 bg-black/50 border border-white/10"
            />
            <p className="text-xs text-white/60 mt-1">If left blank, the system will expand the title into scenes automatically.</p>
          </div>

          {error && <div className="text-sm text-rose-300">{error}</div>}

          <div className="flex items-center gap-3">
            <button
              type="submit"
              data-testid="create-story-submit"
              disabled={loading}
              className="px-4 py-2 bg-amber-500 text-black rounded font-medium"
            >
              {loading ? 'Creating...' : 'Create Story'}
            </button>
            <button type="button" onClick={onClose} className="px-3 py-2 bg-white/5 rounded">Cancel</button>
            <span className="ml-auto text-xs text-white/60">Tip: Stories in Hindi often produce better voiceovers.</span>
          </div>
        </form>
      </div>
    </div>
  );
}
