export type ActivityEvent = {
  ts: string;
  type: string;
  payload?: Record<string, unknown>;
};

export function titleFor(type: string): string {
  const map: Record<string, string> = {
    job_created: 'Job created',
    tts_started: 'TTS started',
    tts_completed: 'TTS completed',
    render_started: 'Render started',
    render_completed: 'Render completed',
    job_completed: 'Job completed',
    job_failed: 'Job failed',
    artifact_uploaded: 'Artifact uploaded',
  };
  return map[type] ?? type.replace(/_/g, ' ');
}

export function detailsFor(type: string, payload?: Record<string, unknown>): string {
  if (!payload) return '';
  try {
    if (type === 'tts_completed') {
      const dur = payload['duration_sec'];
      if (typeof dur === 'number') return `Duration: ${Math.round(dur)}s`;
    }
    if (type === 'render_completed') {
      const tmpl = payload['template'];
      const dur = payload['duration_sec'];
      if (typeof tmpl === 'string') return `Template: ${tmpl}`;
      if (typeof dur === 'number') return `Duration: ${Math.round(dur)}s`;
    }
    if (type === 'artifact_uploaded') {
      const key = payload['key'];
      const size = payload['size_bytes'];
      const sizeStr = typeof size === 'number' ? `${size} bytes` : '';
      return `${typeof key === 'string' ? key : 'artifact'}${sizeStr ? ` — ${sizeStr}` : ''}`;
    }
    return '';
  } catch {
    return '';
  }
}