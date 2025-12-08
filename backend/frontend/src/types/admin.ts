export type AdminUserEntry = {
  id: string;
  email: string;
  role?: string;
  plan_id?: string | null;
  created_at: string;
  last_login_at?: string | null;
};

export type AdminUsersRes = { entries: AdminUserEntry[]; total: number; page: number; pageSize: number };

export type AdminJobEntry = {
  id: string;
  user_id: string;
  title?: string | null;
  status: string;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms?: number | null;
  error_code?: string | null;
  project_id?: string | null;
};

export type AdminJobsRes = { entries: AdminJobEntry[]; total: number; page: number; pageSize: number };

export type AdminUsageEntry = { user_id: string; day: string; renders: number; tts_sec: number };
export type AdminUsageRes = { entries: AdminUsageEntry[]; total: number; page: number; pageSize: number };
