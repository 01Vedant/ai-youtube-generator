/**
 * Shared library types for frontend
 */

export type LibraryItem = {
  id: string;
  title: string;
  created_at: string;
  duration_sec: number;
  voice: "Swara" | "Diya";
  template: string;
  state?: string;
  thumbnail_url?: string;
  video_url?: string;
  error?: string;
};

export type FetchLibraryParams = {
  page?: number;
  pageSize?: number;
  query?: string;
  sort?: "created_at:desc" | "created_at:asc";
};

export type FetchLibraryResponse = {
  entries: LibraryItem[];
  total: number;
  page: number;
  pageSize: number;
};
