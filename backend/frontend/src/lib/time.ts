export function formatRelative(ts: string): string {
  const ms = Date.parse(ts);
  if (!Number.isFinite(ms)) return '';
  const diff = Date.now() - ms;
  const sec = Math.max(0, Math.floor(diff / 1000));
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hrs = Math.floor(min / 60);
  return `${hrs}h ago`;
}

export function formatClock(ts: string): string {
  const ms = Date.parse(ts);
  if (!Number.isFinite(ms)) return '';
  const d = new Date(ms);
  return d.toLocaleTimeString();
}