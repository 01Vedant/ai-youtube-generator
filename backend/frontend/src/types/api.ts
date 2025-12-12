/**
 * Precise type definitions for the video generation platform.
 * All types are strict; no implicit any allowed.
 */

import { z } from 'zod';

export type Voice = 'F' | 'M';
export type Language = 'en' | 'hi';
export type DurationSec = number; // 1..600

export type JobState = 'pending' | 'running' | 'success' | 'error' | 'cancelled';
export type PipelineStep =
  | 'images'
  | 'tts'
  | 'subtitles'
  | 'stitch'
  | 'upload'
  | 'youtube_publish'
  | 'completed'
  | 'error';

export interface SceneInput {
  image_prompt: string;
  narration: string;
  duration_sec: DurationSec;
}

export interface RenderPlan {
  topic: string;
  language: Language;
  voice: Voice;
  voice_id?: string;
  length: number;
  style: string;
  scenes: SceneInput[];
  images_per_scene?: number;
  burn_in_subtitles?: boolean;
  upload_to_cloud?: boolean;
  enable_youtube_upload?: boolean;
  watermark_path?: string;
  template_id?: string;
  // Hybrid pipeline flags
  enable_parallax?: boolean;
  enable_templates?: boolean;
  enable_audio_sync?: boolean;
  quality?: 'preview' | 'final';
}

export interface CreatorTemplate {
  id: string;
  title: string;
  description: string;
  topic: string;
  default_language: string;
  default_voice: string;
  default_style: string;
  default_length: number;
  tags: string[];
}

export interface LibraryEntry {
  job_id: string;
  created_at: string;
  final_video_url?: string | null;
  encoder?: string | null;
  fast_path?: boolean | null;
  resolution?: string | null;
  duration_sec?: number | null;
  thumbnail_url?: string | null;
  state: string;
  topic?: string | null;
  error?: string | null;
  language?: string | null;  // optional, default 'en'
  youtube_url?: string | null;  // optional
  status?: 'queued' | 'running' | 'completed' | 'error' | 'unknown';  // optional status field
}

export interface LibraryResponse {
  entries: LibraryEntry[];
  total: number;
  page: number;
  per_page: number;
  has_more: boolean;
}

export interface PublishSchedule {
  job_id: string;
  scheduled_at?: string;
  state: 'none' | 'scheduled' | 'published' | 'failed' | 'canceled';
  error?: string;
  created_at?: string;
}

export interface RenderResponse {
  job_id: string;
  status: string;
  estimated_wait_seconds: number;
}

export const AssetTypeSchema = z.enum(['image', 'audio', 'video', 'srt', 'other']);
export type AssetType = z.infer<typeof AssetTypeSchema>;

export const AssetRefSchema = z.object({
  type: AssetTypeSchema.or(z.string()),
  url: z.string().optional(),
  label: z.string().optional(),
  scene_index: z.number().optional(),
  path: z.string().optional(),
});
export type AssetRef = z.infer<typeof AssetRefSchema>;

export const LogEntrySchema = z.object({
  ts: z.string().optional(),
  level: z.enum(['info', 'warn', 'error']).optional(),
  message: z.string().optional(),
  msg: z.string().optional(),
});
export type LogEntry = z.infer<typeof LogEntrySchema>;

const AudioSceneSchema = z.object({
  scene_index: z.number(),
  path: z.string(),
  duration_sec: z.number(),
  paced: z.boolean(),
});

export const AudioMetaSchema = z.object({
  lang: z.enum(['hi', 'en']),
  voice_id: z.string().optional(),
  provider: z.string().optional(),
  paced: z.boolean().optional(),
  total_duration_sec: z.number().optional(),
  scenes: z.array(AudioSceneSchema).optional(),
});
export type AudioMeta = z.infer<typeof AudioMetaSchema>;

const DualSubtitlesSchema = z.object({
  hi_url: z.string().optional(),
  en_url: z.string().optional(),
});

export const OrchestratorErrorSchema = z.object({
  code: z.string(),
  phase: z.string(),
  message: z.string(),
  meta: z.record(z.unknown()).optional(),
});
export type OrchestratorError = z.infer<typeof OrchestratorErrorSchema>;

const SharedStatusFields = z.object({
  job_id: z.string().optional(),
  step: z.string().optional(),
  progress_pct: z.number().optional(),
  progress: z.number().optional(),
  assets: z.array(AssetRefSchema).optional(),
  logs: z.array(LogEntrySchema).optional(),
  final_video_url: z.string().nullable().optional(),
  thumbnail_url: z.string().nullable().optional(),
  youtube_url: z.string().nullable().optional(),
  dual_subtitles: DualSubtitlesSchema.optional(),
  audio: AudioMetaSchema.optional(),
  encoder: z.string().nullable().optional(),
  resolution: z.string().nullable().optional(),
  fast_path: z.boolean().optional(),
  audio_error: z.string().nullable().optional(),
  templates: z.record(z.unknown()).optional(),
  parallax: z.record(z.unknown()).optional(),
  audio_director: z.record(z.unknown()).optional(),
  profile: z.record(z.unknown()).optional(),
  qa: z.record(z.unknown()).optional(),
});

const NonFailedStatusExtras = SharedStatusFields.extend({
  error: z.string().nullable().optional(),
});

const QueuedStatusSchema = z
  .object({
    status: z.literal('queued'),
    progress: z.number().min(0).max(100).optional(),
  })
  .merge(NonFailedStatusExtras);

const RunningStatusSchema = z
  .object({
    status: z.literal('running'),
    progress: z.number().min(0).max(100).optional(),
  })
  .merge(NonFailedStatusExtras);

const CompletedStatusSchema = z
  .object({
    status: z.literal('completed'),
    artifacts: z.record(z.string()),
    audioMeta: AudioMetaSchema.optional(),
  })
  .merge(NonFailedStatusExtras);

const CancelledStatusSchema = z
  .object({
    status: z.literal('cancelled'),
    error: OrchestratorErrorSchema.optional(),
  })
  .merge(SharedStatusFields.partial());

const FailedStatusSchema = z
  .object({
    status: z.literal('failed'),
    error: OrchestratorErrorSchema,
  })
  .merge(
    SharedStatusFields.extend({
      legacy_error: z.string().optional(),
      artifacts: z.record(z.string()).optional(),
      audioMeta: AudioMetaSchema.optional(),
    })
  );

export const JobStatusSchema = z.union([
  QueuedStatusSchema,
  RunningStatusSchema,
  FailedStatusSchema,
  CompletedStatusSchema,
  CancelledStatusSchema,
]);
export type JobStatus = z.infer<typeof JobStatusSchema>;

export interface Metrics {
  jobs_started: number;
  jobs_completed: number;
  jobs_failed: number;
  total_duration_seconds: number;
  image_errors: number;
  tts_errors: number;
  upload_errors: number;
  youtube_uploads: number;
  success_rate: number;
}

export interface ApiError {
  status: number;
  body?: Record<string, unknown>;
  message: string;
}
