export type UserPrefs = {
  voice_id?: string;
  template?: string;
  duration_default?: number;
};

const KEY = 'bhaktigen.prefs';

export function getPrefs(): UserPrefs {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return {};
    const obj = JSON.parse(raw);
    return typeof obj === 'object' && obj ? obj as UserPrefs : {};
  } catch {
    return {};
  }
}

export function savePrefs(p: UserPrefs): void {
  try {
    const current = getPrefs();
    const merged: UserPrefs = { ...current, ...p };
    localStorage.setItem(KEY, JSON.stringify(merged));
  } catch {
    // ignore
  }
}
