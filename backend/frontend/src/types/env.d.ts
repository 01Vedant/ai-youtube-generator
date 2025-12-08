/**
 * Vite environment variable type definitions.
 * Ensures import.meta.env is properly typed.
 */

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_ENV?: 'development' | 'production' | 'test';
  readonly VITE_SENTRY_DSN?: string;
  readonly MODE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
