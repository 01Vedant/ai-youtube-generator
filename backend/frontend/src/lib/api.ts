import type { InputsSchema } from '@/types/plan';
import type { Project, ProjectCreate, ProjectUpdate } from '@/types/projects';
import { FetchLibraryResponseSchema, type FetchLibraryResponse } from '../schemas/library';
import type { AdminJobsRes, AdminUsageRes, AdminUsersRes } from '../types/admin';
import type { AppUser } from '../types/app';
import type { AuthTokens, Me } from '../types/auth';
import type { FetchLibraryParams } from '../types/library';
import {
  JobStatusSchema,
  type JobStatus,
  type PublishSchedule,
} from '../types/api';

/**
 * API client with unified fetch wrapper
 * Handles CORS credentials based on environment configuration
 */

const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

// Credentials control: only include credentials if explicitly enabled
const AUTH_MODE: string = import.meta.env.VITE_AUTH_MODE ?? 'none';
const USE_CREDENTIALS: boolean = AUTH_MODE !== 'none';
let INMEM_ACCESS: string | null = null;
let CSRF_TOKEN: string | null = null;

/**
 * Unified fetch wrapper with consistent error handling and credentials control
 */
type FetchJsonOptions = RequestInit & { retry?: boolean; idempotent?: boolean };

async function fetchJson<T>(
  url: string,
  options: FetchJsonOptions = {},
  retryOn401: boolean = true
): Promise<T> {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`;
  const tokensRaw = localStorage.getItem('auth_tokens');
  const tokens = tokensRaw ? JSON.parse(tokensRaw) as { access_token?: string } : null;
  const doFetch = async (): Promise<Response> => {
    return fetch(fullUrl, {
      ...options,
      credentials: USE_CREDENTIALS ? 'include' : 'omit',
      headers: {
        'Content-Type': 'application/json',
        ...(INMEM_ACCESS ? { Authorization: `Bearer ${INMEM_ACCESS}` } : (tokens?.access_token ? { Authorization: `Bearer ${tokens.access_token}` } : {})),
        ...((options.method && options.method !== 'GET' && CSRF_TOKEN) ? { 'X-CSRF-Token': CSRF_TOKEN } : {}),
        ...options.headers,
      },
    });
  };

  // Retry logic defaults
  const method = (options.method || 'GET').toUpperCase();
  const shouldRetry = options.retry ?? (method === 'GET' ? true : options.idempotent === true);
  const run = shouldRetry
    ? await (await import('./retry')).retry<Response>(async () => {
        const resp = await doFetch();
        if (!resp.ok) {
          const err: any = new Error(`HTTP ${resp.status}`);
          err.status = resp.status;
          const ra = resp.headers.get('Retry-After');
          if (ra) {
            const s = Number(ra);
            if (!Number.isNaN(s)) err.retryAfterSeconds = s;
          }
          // Only trigger retry for 5xx and 429; for others, throw through
          if (resp.status >= 500 || resp.status === 429) throw err;
        }
        return resp;
      })
    : await doFetch();
  const response = run;

  if (!response.ok) {
    if (response.status === 429) {
      let payload: any = undefined;
      try { payload = await response.json(); } catch { /* ignore */ }
      const err: any = new Error('QUOTA_EXCEEDED');
      err.code = 'QUOTA_EXCEEDED';
      err.payload = payload;
      const ra = response.headers.get('Retry-After');
      if (ra) {
        const s = Number(ra);
        if (!Number.isNaN(s)) err.retryAfterSeconds = s;
      }
      throw err;
    }
    if (response.status === 401 && retryOn401) {
      try {
        if (!CSRF_TOKEN) {
          try { const c = await fetchJson<{ csrf_token: string }>(`/auth/csrf`, { method: 'GET' }, false); CSRF_TOKEN = c.csrf_token; } catch {}
        }
        const r = await fetch(`${API_BASE}/auth/refresh`, { method: 'POST', headers: { 'X-CSRF-Token': CSRF_TOKEN || '' }, credentials: USE_CREDENTIALS ? 'include' : 'omit' });
        if (r.ok) {
          const refreshed = await r.json();
          INMEM_ACCESS = refreshed.access_token;
          return await fetchJson<T>(url, options, false);
        }
      } catch {
        // fall through to error
      }
    }
    const text = await response.text();
    let errorDetail = text;
    try {
      const json = JSON.parse(text);
      errorDetail = json.detail || json.error || text;
    } catch {
      // Keep text as-is
    }
    throw new Error(`HTTP ${response.status}: ${errorDetail}`);
  }

  return response.json();
}

/**
 * Calls the backend /debug/echo endpoint
 */
export async function debugEcho(): Promise<{ ok: boolean; env: string }> {
  return fetchJson<{ ok: boolean; env: string }>('/debug/echo');
}

/**
 * Get render job status
 */
export async function getStatus(jobId: string): Promise<JobStatus> {
  const raw = await fetchJson<unknown>(`/render/${jobId}/status`);
  const parsed = JobStatusSchema.safeParse(raw);

  if (!parsed.success) {
    throw new Error(`Invalid job status payload: ${parsed.error.message}`);
  }

  return parsed.data;
}

/**
 * Submit new render job
 */
export async function submitRender(payload: unknown): Promise<{ job_id: string }> {
  return fetchJson<{ job_id: string }>('/render', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
// Admin API

export async function getAdminUsers(params: { page?: number; pageSize?: number; q?: string; sort?: string } = {}): Promise<AdminUsersRes> {
  const usp = new URLSearchParams();
  if (params.page) usp.set('page', String(params.page));
  if (params.pageSize) usp.set('pageSize', String(params.pageSize));
  if (params.q) usp.set('q', params.q);
  if (params.sort) usp.set('sort', params.sort);
  return fetchJson(`/admin/users?${usp.toString()}`);
}

export async function getAdminJobs(params: { page?: number; pageSize?: number; status?: string; userId?: string; projectId?: string; q?: string; from?: string; to?: string; sort?: string } = {}): Promise<AdminJobsRes> {
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v != null) usp.set(k === 'from' ? 'from_' : k, String(v)); });
  return fetchJson(`/admin/jobs?${usp.toString()}`);
}

export async function getAdminUsage(params: { page?: number; pageSize?: number; userId?: string; day?: string; sort?: string } = {}): Promise<AdminUsageRes> {
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v != null) usp.set(k, String(v)); });
  return fetchJson(`/admin/usage?${usp.toString()}`);
}

export async function exportAdminUsersCsv(params: { q?: string; sort?: string } = {}): Promise<string> {
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v != null) usp.set(k, String(v)); });
  const res = await fetch(`${API_BASE}/admin/export/users.csv?${usp.toString()}`, { headers: { 'Accept': 'text/csv' } });
  return res.text();
}

export async function exportAdminJobsCsv(params: { status?: string; userId?: string; projectId?: string; q?: string; from?: string; to?: string; sort?: string } = {}): Promise<string> {
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v != null) usp.set(k === 'from' ? 'from_' : k, String(v)); });
  const res = await fetch(`${API_BASE}/admin/export/jobs.csv?${usp.toString()}`, { headers: { 'Accept': 'text/csv' } });
  return res.text();
}

export async function exportAdminUsageCsv(params: { userId?: string; day?: string; sort?: string } = {}): Promise<string> {
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v != null) usp.set(k, String(v)); });
  const res = await fetch(`${API_BASE}/admin/export/usage.csv?${usp.toString()}`, { headers: { 'Accept': 'text/csv' } });
  return res.text();
}

// Templates API
export type TemplateItem = {
  id: string;
  title: string;
  description?: string;
  category?: string;
  thumb?: string;
  plan_json: unknown;
  visibility: string;
  user_id: string;
  inputs_schema?: InputsSchema;
};

export async function getBuiltinTemplates(): Promise<{ templates: TemplateItem[] }> {
  return fetchJson(`/templates/builtin`);
}

// Template Editor APIs
export type Scene = { script?: string; image_prompt?: string; duration_sec?: number };
export type Plan = { title?: string; voice_id?: string; template?: string; duration_sec?: number; scenes: Scene[]; [k: string]: any };

export async function getTemplatePlan(id: string): Promise<Plan> {
  return fetchJson(`/templates/${id}/plan`);
}

export async function putTemplatePlan(id: string, plan: Plan): Promise<{ plan: Plan; warnings?: string[] }> {
  return fetchJson(`/templates/${id}/plan`, { method: 'PUT', body: JSON.stringify(plan) });
}

// Template variables APIs

export async function getTemplateVars(id: string): Promise<{ vars: string[]; inputs_schema?: InputsSchema }>{
  return fetchJson(`/templates/${id}/vars`);
}

export async function patchTemplateInputsSchema(id: string, schema: InputsSchema): Promise<{ ok: true }>{
  return fetchJson(`/templates/${id}/inputs-schema`, { method: 'PATCH', body: JSON.stringify(schema) });
}

export async function previewTemplatePlan(
  id: string,
  inputs: Record<string, unknown>
): Promise<{ plan: Plan; warnings?: string[] }>{
  return fetchJson(`/templates/${id}/preview-plan`, { method: 'POST', body: JSON.stringify({ inputs }) });
}

export async function renderFromTemplate(
  id: string,
  payload?: { inputs?: Record<string, unknown>; overrides?: any; project_id?: string }
): Promise<{ job_id: string; status: 'queued' }>{
  return fetchJson(`/templates/${id}/render`, { method: 'POST', body: JSON.stringify(payload || {}) });
}

// Onboarding (no-op safe)
export type OnboardingSteps = { created_project?: boolean; rendered_video?: boolean; exported_video?: boolean };
export type OnboardingState = {
  seen_welcome?: boolean;
  steps?: OnboardingSteps;
  recommended_template_id?: string | number | null;
  has_render?: boolean;
  seed_job_id?: string | null;
};

export async function getOnboardingState(): Promise<OnboardingState> {
  try {
    return await fetchJson<OnboardingState>('/onboarding/state');
  } catch {
    return { seen_welcome: false, steps: {} };
  }
}

export async function sendOnboardingEvent(event: string): Promise<void> {
  try {
    await fetchJson('/onboarding/event', {
      method: 'POST',
      body: JSON.stringify({ event }),
    });
  } catch {}
}

// Marketplace APIs
export async function getMarketplaceTemplates(params: { q?: string; category?: string; sort?: 'new' | 'popular'; page?: number; page_size?: number } = {}): Promise<{ items: TemplateItem[]; total: number; page: number; page_size: number }>{
  const usp = new URLSearchParams();
  if (params.q) usp.set('q', params.q);
  if (params.category) usp.set('category', params.category);
  if (params.sort) usp.set('sort', params.sort);
  if (params.page) usp.set('page', String(params.page));
  if (params.page_size) usp.set('page_size', String(params.page_size));
  return fetchJson(`/marketplace/templates?${usp.toString()}`);
}

export async function getMarketplaceTemplate(id: string): Promise<TemplateItem>{
  return fetchJson(`/marketplace/templates/${id}`);
}

export async function duplicateTemplate(id: string): Promise<TemplateItem>{
  return fetchJson(`/marketplace/templates/${id}/duplicate`, { method: 'POST' });
}

/**
 * Submit new render job (alias for backward compatibility)
 */
export async function postRender(payload: unknown): Promise<{ job_id: string }> {
  return submitRender(payload);
}

/**
 * Cancel a render job
 */
export async function cancelRender(jobId: string): Promise<void> {
  await fetchJson<void>(`/render/${jobId}/cancel`, {
    method: 'DELETE',
  });
}

/**
 * Get activity log events for a render job
 */
export async function getJobActivity(
  jobId: string,
  limit = 100
): Promise<{
  events: Array<{
    ts_iso: string;
    job_id: string;
    event_type: string;
    message: string;
    meta?: Record<string, unknown>;
  }>;
}> {
  return fetchJson(`/api/render/${jobId}/activity?limit=${limit}`);
}

/**
 * Duplicate a project/job
 */
export async function duplicateProject(jobId: string): Promise<{ job_id: string; new_job_id?: string }> {
  const result = await fetchJson<{ job_id: string }>(`/render/${jobId}/duplicate`, {
    method: 'POST',
  });
  // Add new_job_id for backward compatibility
  return { ...result, new_job_id: result.job_id };
}

// Regenerate API
export type RegenerateOverrides = Partial<{
  title: string;
  voice: 'Swara' | 'Diya';
  template: string;
  duration_sec: number;
}>;

export async function regenerateJob(
  jobId: string,
  overrides: RegenerateOverrides
): Promise<{ job_id: string; status: 'queued'; parent_job_id: string }> {
  // Map UI-friendly overrides to backend expected keys
  const body: Record<string, unknown> = {};
  if (overrides.title) body.topic = overrides.title;
  if (overrides.voice) {
    // Map to specific voice_id commonly used in this project
    body.voice_id = overrides.voice === 'Swara' ? 'hi-IN-SwaraNeural' : 'hi-IN-DiyaNeural';
  }
  if (typeof overrides.template === 'string') body.template = overrides.template;
  if (typeof overrides.duration_sec === 'number') body.duration_sec = overrides.duration_sec;

  return fetchJson<{ job_id: string; status: 'queued'; parent_job_id: string }>(
    `/render/${jobId}/regenerate`,
    {
      method: 'POST',
      body: JSON.stringify(body),
    }
  );
}

/**
 * Fetch publish schedule for a job
 */
export async function fetchSchedule(jobId: string): Promise<PublishSchedule | null> {
  try {
    return await fetchJson<PublishSchedule>(`/api/publish/${jobId}/schedule`);
  } catch (err) {
    // Schedule may not exist yet
    if (err instanceof Error && err.message.includes('404')) {
      return null;
    }
    throw err;
  }
}

// (duplicate removed) Onboarding API is defined above with typed `OnboardingState`.

/**
 * Schedule a job for publishing
 */
export async function schedulePublish(
  jobId: string,
  datetimeOrPayload: string | { platform: string; scheduled_at: string; title?: string; description?: string }
): Promise<void> {
  const payload = typeof datetimeOrPayload === 'string'
    ? { platform: 'youtube', scheduled_at: datetimeOrPayload }
    : datetimeOrPayload;
  
  await fetchJson<void>(`/api/publish/${jobId}/schedule`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Cancel a scheduled publish
 */
export async function cancelScheduledPublish(jobId: string): Promise<void> {
  await fetchJson<void>(`/api/publish/${jobId}/cancel`, {
    method: 'DELETE',
  });
}

/**
 * Delete a project/job
 */
export async function deleteProject(jobId: string): Promise<void> {
  await fetchJson<void>(`/render/${jobId}`, {
    method: 'DELETE',
  });
}

/**
 * Check backend connectivity (for connectivity pill)
 */
export async function checkBackendHealth(): Promise<{
  ok: boolean;
  cors_ok: boolean;
  error?: string;
}> {
  try {
    const health = await fetchJson<{ ok: boolean; status: string }>('/healthz');
    
    // Check CORS config
    try {
      const corsDebug = await fetchJson<{ origins: string[]; allow_credentials: boolean }>(
        '/debug/cors'
      );
      return {
        ok: health.ok,
        cors_ok: corsDebug.origins.length > 0 && corsDebug.allow_credentials,
      };
    } catch {
      return { ok: health.ok, cors_ok: false };
    }
  } catch (err) {
    return {
      ok: false,
      cors_ok: false,
      error: err instanceof Error ? err.message : 'Unknown error',
    };
  }
}

/**
 * Get list of available templates
 */
export async function getTemplates(): Promise<unknown[]> {
  return fetchJson<unknown[]>('/api/templates');
}

/**
 * Generate plan from template
 */
export async function generatePlanFromTemplate(
  templateId: string,
  payload: Record<string, unknown>
): Promise<unknown> {
  return fetchJson<unknown>('/api/templates/plan', {
    method: 'POST',
    body: JSON.stringify({ template_id: templateId, ...payload }),
  });
}

/**
 * Get user's library with runtime validation
 */
export async function getLibrary(params?: FetchLibraryParams): Promise<FetchLibraryResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set('page', params.page.toString());
  if (params?.pageSize) searchParams.set('pageSize', params.pageSize.toString());
  if (params?.query) searchParams.set('query', params.query);
  if (params?.sort) searchParams.set('sort', params.sort);
  
  const queryString = searchParams.toString();
  const url = queryString ? `/api/library?${queryString}` : '/api/library';
  const response = await fetchJson<unknown>(url);
  
  // Runtime validation with Zod
  const parseResult = FetchLibraryResponseSchema.safeParse(response);
  if (!parseResult.success) {
    throw new Error(`Invalid library response: ${parseResult.error.message}`);
  }
  
  return parseResult.data;
}

/**
 * Get user's library (alias for backward compatibility)
 */
export async function fetchLibrary(params?: FetchLibraryParams): Promise<FetchLibraryResponse> {
  return getLibrary(params);
}

/**
 * Get user's scheduled posts
 */
export async function getScheduledPosts(): Promise<unknown[]> {
  return fetchJson<unknown[]>('/api/schedule');
}

// Usage history
export type UsagePoint = { day: string; renders: number; tts_sec: number };
export type UsageHistory = { days: number; series: UsagePoint[] };
export async function getUsageHistory(days: number = 14): Promise<UsageHistory> {
  const allowed = [14, 30, 90];
  const clamped = allowed.includes(days) ? days : 14;
  const url = `/usage/history?days=${clamped}`;
  return fetchJson<UsageHistory>(url);
}

/**
 * Request magic link for authentication
 */
export async function requestMagicLink(email: string): Promise<void> {
  await fetchJson<void>('/api/auth/magic-link/request', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

/**
 * Verify magic link token
 */
export async function verifyMagicLink(token: string): Promise<{ access_token: string }> {
  return fetchJson<{ access_token: string }>('/api/auth/magic-link/verify', {
    method: 'POST',
    body: JSON.stringify({ token }),
  });
}

/**
 * Get current user info
 */
export async function getCurrentUser(): Promise<AppUser> {
  return fetchJson<AppUser>('/api/auth/me');
}

/**
 * Get current user info (alias for backward compatibility)
 */
export async function getMe(): Promise<AppUser> {
  return getCurrentUser();
}

/**
 * Preview TTS voice before rendering
 */
export async function ttsPreview(body: {
  text: string;
  lang: 'hi' | 'en';
  voice_id?: string;
  pace?: number;
}): Promise<{ url: string; duration_sec: number; cached: boolean }> {
  return fetchJson<{ url: string; duration_sec: number; cached: boolean }>('/tts/preview', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Get billing subscription info
 */
export async function getBillingSubscription(): Promise<unknown> {
  return fetchJson<unknown>('/api/billing/subscription');
}

// New Billing APIs
export async function createCheckoutSession(planId: 'pro' | string): Promise<{ url: string }> {
  const res = await fetchJson<{ url: string }>('/billing/checkout', {
    method: 'POST',
    body: JSON.stringify({ plan_id: planId }),
  });
  return res;
}

export async function createPortalSession(): Promise<{ url: string }> {
  return fetchJson<{ url: string }>('/billing/portal', { method: 'POST' });
}

/**
 * Get usage stats
 */
export async function getUsageStats(): Promise<unknown> {
  return fetchJson<unknown>('/api/usage');
}

// Analytics
export type AnalyticsSummary = { users_total:number; paying_users:number; projects_total:number; renders_today:number; renders_7d:number; tts_sec_today:number; exports_total:number; shares_total:number; mrr:number };
export type AnalyticsDaily = { days:string[]; renders:number[]; tts_sec:number[]; new_users:number[]; exports:number[] };
export async function getAnalyticsSummary(): Promise<AnalyticsSummary> {
  return fetchJson('/analytics/summary');
}
export async function getAnalyticsDaily(days = 14): Promise<AnalyticsDaily> {
  return fetchJson(`/analytics/timeseries/daily?days=${days}`);
}

// Feedback APIs
export type FeedbackRow = { id:string; user_id?:string; message:string; created_at:string; meta_json?:string };

export async function submitFeedback(message: string, meta?: any): Promise<{ ok: true }> {
  return fetchJson('/feedback', { method: 'POST', body: JSON.stringify({ message, meta }) });
}

export async function getFeedback(): Promise<FeedbackRow[]> {
  return fetchJson('/feedback');
}

// Growth API (no UI yet)
export type ShareProgress = { unique_visitors: number; goal: number; unlocked: boolean };

export async function getShareProgress(shareId: string): Promise<ShareProgress> {
  return fetchJson(`/growth/share-progress/${shareId}`);
}

export async function shareUnlock(shareId: string): Promise<{ granted: boolean; bonus?: string; amount?: number }> {
  return fetchJson(`/growth/share-unlock/${shareId}`, { method: 'POST' });
}

// Public APIs
export async function joinWaitlist(email: string, source?: string, meta?: any): Promise<{ ok: true; duplicate?: boolean }>{
  return fetchJson('/public/waitlist', { method: 'POST', body: JSON.stringify({ email, source, meta }) });
}

export async function fetchOgForTemplate(id: string): Promise<{ title: string; description: string; image: string }>{
  return fetchJson(`/public/og/template/${id}`);
}

export async function createReferralCode(): Promise<{ code: string; url: string }> {
  return fetchJson(`/growth/referral/create`, { method: 'POST' });
}

export async function claimReferral(code: string): Promise<{ ok: true }> {
  return fetchJson(`/growth/referral/claim`, { method: 'POST', body: JSON.stringify({ code }) });
}

// Admin Logs bundle download
export type LogInclude = "structured" | "activity";

function authHeaders(): Record<string, string> {
  const tokensRaw = localStorage.getItem('auth_tokens');
  const tokens = tokensRaw ? JSON.parse(tokensRaw) as { access_token?: string } : null;
  return tokens?.access_token ? { Authorization: `Bearer ${tokens.access_token}` } : {};
}

export async function downloadLogsBundle(params: { from?: string; to?: string; include?: LogInclude[] }): Promise<Blob> {
  const qs = new URLSearchParams();
  if (params.from) qs.set('from', params.from);
  if (params.to) qs.set('to', params.to);
  if (params.include?.length) qs.set('include', params.include.join(','));
  const res = await fetch(`${API_BASE}/logs/bundle?${qs.toString()}`, { headers: authHeaders() });
  if (res.status === 204) throw new Error('No logs for selected range');
  if (!res.ok) throw new Error(`Failed to download logs (${res.status})`);
  return await res.blob();
}

export async function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; document.body.appendChild(a); a.click();
  a.remove(); URL.revokeObjectURL(url);
}

export async function downloadAuditCsv(params: { from?: string; to?: string }): Promise<Blob> {
  const qs = new URLSearchParams();
  if (params.from) qs.set('from_day', params.from);
  if (params.to) qs.set('to_day', params.to);
  const res = await fetch(`${API_BASE}/analytics/audit.csv?${qs.toString()}`, { headers: authHeaders() });
  if (res.status === 204) throw new Error('No audit events for selected range');
  if (!res.ok) throw new Error(`Failed to download audit CSV (${res.status})`);
  return await res.blob();
}

export async function downloadAdminWaitlistCsv(): Promise<Blob> {
  const res = await fetch(`${API_BASE}/admin/waitlist.csv`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to download waitlist CSV (${res.status})`);
  return await res.blob();
}

// Feature flags
export type FeatureFlags = Record<string, boolean>;
export async function getFeatureFlags(): Promise<FeatureFlags> {
  return fetchJson('/admin/flags');
}
export async function setFeatureFlag(key: string, value: boolean): Promise<FeatureFlags> {
  return fetchJson('/admin/flags', { method: 'PUT', body: JSON.stringify({ key, value }) });
}

// Lightweight per-user usage (today)
export type UsageToday = {
  day: string;
  renders: number;
  tts_sec: number;
  limit_renders: number;
  limit_tts_sec: number;
  reset_at: string;
};

export async function getUsageToday(): Promise<UsageToday> {
  return fetchJson<UsageToday>('/usage/today');
}

/**
 * Task 3: Get TTS debug info (provider status)
 */
export async function getTtsDebug(): Promise<{
  ok: boolean;
  provider: 'edge' | 'mock' | 'unknown';
  voices: string[];
  default_voice?: string;
}> {
  try {
    return await fetchJson<{
      ok: boolean;
      provider: 'edge' | 'mock' | 'unknown';
      voices: string[];
      default_voice?: string;
    }>('/debug/tts');
  } catch {
    return {
      ok: false,
      provider: 'unknown',
      voices: [],
    };
  }
}

/**
 * Get auth headers for API requests.
 * In dev mode (VITE_AUTH_MODE=none), auth headers are empty.
 */
export function getAuthHeaders(): Record<string, string> {
  if (AUTH_MODE === 'none') {
    return {};
  }
  
  const token = localStorage.getItem('auth_token');
  if (!token) return {};
  
  return {
    'Authorization': `Bearer ${token}`,
  };
}

/**
 * Export from fetchJson for testing
 */
export { fetchJson };

// Auth APIs

export async function register(email: string, password: string): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    return await fetchJson<{ ok: true }>(`/auth/register`, {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : 'Register failed' };
  }
}

export async function login(email: string, password: string): Promise<AuthTokens> {
  const tokens = await fetchJson<AuthTokens>(`/auth/login`, {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  localStorage.setItem('auth_tokens', JSON.stringify(tokens));
  return tokens;
}

export async function refresh(refresh_token: string): Promise<{ access_token: string }> {
  return fetchJson<{ access_token: string }>(`/auth/refresh`, {
    method: 'POST',
    body: JSON.stringify({ refresh_token }),
  }, false);
}

export async function me(): Promise<Me> {
  return fetchJson<Me>(`/auth/me`);
}

/**
 * Get artifact manifest for a job
 */
export async function getArtifactManifest(jobId: string): Promise<{ thumbnail: string; video: string; audio: string } | null> {
  try {
    return await fetchJson<{ thumbnail: string; video: string; audio: string }>(`/artifacts/${jobId}/manifest`);
  } catch (err) {
    // Graceful fallback if endpoint unavailable
    return null;
  }
}

export type ExportYouTubeReq = { job_id: string; title: string; description?: string; tags?: string[]; visibility?: 'public' | 'unlisted' | 'private' };
export type ExportYouTubeRes = { export_id: string; status: 'completed' | 'failed' | 'queued'; youtube_url?: string };
export async function exportToYouTube(req: ExportYouTubeReq): Promise<ExportYouTubeRes> {
  return fetchJson<ExportYouTubeRes>('/exports/youtube', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

// Backward compatibility layer for legacy callers
export async function startRender(input: unknown): Promise<{ job_id: string }> {
  return submitRender(input);
}

export type RenderArtifactType = 'video' | 'audio' | 'image' | 'json';

export interface RenderArtifact {
  type: RenderArtifactType;
  url: string;
  meta?: unknown;
}

export interface RenderJob {
  id: string;
  status: 'queued' | 'running' | 'success' | 'error';
  artifacts?: RenderArtifact[];
  error?: string;
}

export async function getRender(jobId: string): Promise<RenderJob> {
  const raw = await fetchJson<unknown>(`/render/${jobId}/status`);
  const parsed = JobStatusSchema.safeParse(raw);
  if (!parsed.success) {
    throw new Error(`Invalid job status payload: ${parsed.error.message}`);
  }
  const status = parsed.data;

  const mapStatus: Record<JobStatus['status'], RenderJob['status']> = {
    queued: 'queued',
    running: 'running',
    completed: 'success',
    failed: 'error',
  };

  const toArtifact = (type: string, url: string, meta?: unknown): RenderArtifact => {
    const allowed: RenderArtifactType[] = ['video', 'audio', 'image', 'json'];
    const normalized = allowed.includes(type as RenderArtifactType) ? (type as RenderArtifactType) : 'json';
    return { type: normalized, url, meta };
  };

  let artifacts: RenderArtifact[] | undefined;

  if (status.status === 'completed' && status.artifacts) {
    const entries = Object.entries(status.artifacts).filter(([, url]) => typeof url === 'string' && url.length > 0);
    artifacts = entries.map(([type, url]) => toArtifact(type, url));
  } else if (status.assets?.length) {
    const mapped = status.assets
      .filter((asset) => typeof asset?.url === 'string' && !!asset.url)
      .map((asset) => toArtifact(String(asset.type ?? 'json'), String(asset.url), asset));
    artifacts = mapped.length ? mapped : undefined;
  }

  const error =
    status.status === 'failed'
      ? status.error?.message || status.legacy_error || status.error?.code || 'Render failed'
      : undefined;

  return {
    id: status.job_id ?? jobId,
    status: mapStatus[status.status],
    artifacts,
    error,
  };
}

// Projects API
export async function listProjects(): Promise<Project[]> {
  return fetchJson<Project[]>('/projects');
}

export async function createProject(input: ProjectCreate): Promise<Project> {
  return fetchJson<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function updateProject(id: string, input: ProjectUpdate): Promise<Project> {
  return fetchJson<Project>(`/projects/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export async function deleteProjectApi(id: string): Promise<{ ok: true }> {
  return fetchJson<{ ok: true }>(`/projects/${id}`, { method: 'DELETE' });
}

export async function assignToProject(projectId: string, jobId: string): Promise<{ ok: true }> {
  return fetchJson<{ ok: true }>(`/projects/${projectId}/assign`, {
    method: 'POST',
    body: JSON.stringify({ job_id: jobId }),
  });
}

export async function unassignFromProject(projectId: string, jobId: string): Promise<{ ok: true }> {
  return fetchJson<{ ok: true }>(`/projects/${projectId}/unassign`, {
    method: 'POST',
    body: JSON.stringify({ job_id: jobId }),
  });
}

export async function getProject(id: string): Promise<{ project: Project; entries: Array<{ id: string; title: string; created_at: string }>; total: number }> {
  return fetchJson<{ project: Project; entries: Array<{ id: string; title: string; created_at: string }>; total: number }>(`/projects/${id}`);
}

// Shares API
export async function createShare(jobId: string): Promise<{ share_id: string; url: string }> {
  return fetchJson<{ share_id: string; url: string }>(`/shares`, {
    method: 'POST',
    body: JSON.stringify({ job_id: jobId }),
  });
}

export async function revokeShare(shareId: string): Promise<{ ok: true }> {
  return fetchJson<{ ok: true }>(`/shares/${shareId}/revoke`, { method: 'POST' });
}

export async function getSharedView(shareId: string): Promise<{
  job_id: string;
  title: string;
  created_at: string;
  artifacts: { video?: string; thumbnail?: string; audio?: string };
}> {
  return fetchJson(`/s/${shareId}`);
}
