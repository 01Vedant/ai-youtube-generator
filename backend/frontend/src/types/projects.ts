export type Project = { id: string; title: string; description?: string; cover_thumb?: string; created_at: string; video_count?: number };
export type ProjectCreate = { title: string; description?: string };
export type ProjectUpdate = { title?: string; description?: string; cover_thumb?: string };
