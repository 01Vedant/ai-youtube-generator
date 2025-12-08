## P5: Feedback v1


## P6: Public + Waitlist v1

- Public landing enabled under `VITE_PUBLIC_ENABLED`.
- SEO tags via `src/seo.tsx` for landing and templates.
- `/public/robots.txt` and `/public/sitemap.xml` available.
- `/public/waitlist` accepts email; admin CSV at `/admin/waitlist.csv`.
- Public templates gallery at `/templates/public`.
 - Polish: public header/footer on public routes, rate-limit on waitlist (1/15s, 10/day/IP), sitemap `lastmod` with host, admin CSV download headers.

### Public Preview Ready

- Typecheck/build pending local Node install; commands:
	- `cd platform/frontend && npm run typecheck && npm run build`
- Backend tests green (`pytest` suite).
- Smoke scripts:
	- PowerShell: `scripts/public_smoke.ps1 -ApiBase http://127.0.0.1:8000`
- Deploy configs:
	- Frontend: `platform/frontend/vercel.json` rewrite `/api/*` → `${VITE_API_BASE_URL}`
	- Backend: `platform/backend/render.yaml` uvicorn run; set envs: `APP_ENV=prod`, `CORS_ALLOWED_ORIGINS=<frontend-url>`, `CSRF_SECURE_COOKIES=true`.

- Structured logging helper writes JSONL to `data/logs/app-YYYY-MM-DD.jsonl`.
## P3-5A: Growth loop wired (backend) + FE API stubs

- Backend growth router wired under `/growth` with endpoints:
	- `GET /growth/share-progress/{share_id}`: returns `{ unique_visitors, goal, unlocked }`
	- `POST /growth/share-unlock/{share_id}`: grants daily bonus when unlocked
	- `POST /growth/referral/create` and `POST /growth/referral/claim`
- Shares router exposes public `POST /s/{share_id}/hit` for recording visits.
- Frontend `src/lib/api.ts` exports growth API stubs without UI:
	- `getShareProgress`, `shareUnlock`, `createReferralCode`, `claimReferral`
-
Status: Backend wired; FE API stubs available. UI pending.
### Change Log

- Added sticky toast helper; API auto-retry (GET by default, opt-in for idempotent POST); read-only Queue Admin page using Library + on-demand Status with stale detection.
- Template presets + smarter defaults (local prefs) on Create, and one-click Retry on failed jobs.
- Release prep: verify script, CI pipeline, and RELEASE_CHECKLIST.md.
 - Public Demo Pack: DEMO_RUNBOOK, demo_plan.json, one-click demo_submit.ps1 + demo_share.ps1, and polished LAUNCH_COPY.
# Project State

## Key Modules
- **backend/app/logs/activity.py**: JSONL activity logger
- **backend/routes/jobs.py**: `GET /jobs/{job_id}/activity`
- **backend/app/errors.py**: Orchestrator typed errors
- **frontend/src/schemas/library.ts**: Zod schemas
- **frontend/src/components/ActivityLogPanel.tsx**: Job timeline
- **frontend/pages/RenderStatusPage.tsx**: Metadata badges + error callout

## Current Status – Working
- **Library API**: Standardized and validated with Zod (frontend)
- **Activity logs**: End-to-end (events + UI panel, polling)
- **Error envelope**: Structured orchestrator failures (`status: "failed"` with `{code, phase, message}`)
- **UI Metadata**: Badges for voice, duration (mm:ss), template

## Decision Log (2025-12-05)
- **Zod validation**: Adopted runtime validation at API boundaries
- **Typed errors**: Introduced structured orchestrator errors and stable failure payload
- **Activity logs**: Implemented file-based JSONL logs + `/jobs/{id}/activity`

## Change Log (2025-12-05)
- Playwright E2E smoke tests added for Library and Render Status (frontend-only)

- **Library UX**: Search + sort controls persisted in URL (query params)
- **Artifacts UI**: Thumbnail & artifact cards (preview image + "open artifact" button)
- **Frontend tests**: Smoke test for `/library` and `/render/:id` (Playwright)
- **Zod shim**: Replace temp Zod shim once packages are installed

## Change Log (2025-12-06)
- Added Regenerate flow (UI dialog + API), optional lineage badge.

- Docker Compose: api + worker + MinIO; one-command dev up.

- Added onboarding modal (one-time), demo video action, and empty states for Dashboard/Library.

- Added robust render-status polling (exponential backoff, stale detection, improved banners).

 - P2-Step1: Rate Limiting middleware (per IP/User) with unified 429 envelopes
 - P2-Step2: Maintenance Mode (backend middleware + frontend /maintenance redirect, countdown)
	- P2-Step3: Structured JSON logging, request_id, Sentry hook, 500 error envelope
	- P2-Step4: Artifact retention (FS/S3 list+delete), purge service + admin endpoints, tests
	- P2-Step5: Admin APIs (users/jobs/usage) + read-only Admin UI with CSV export
	- P2-Step6b: Refresh rotation via HttpOnly cookie; CSRF enforced; prod CORS configured

## How to Run (Docker Dev)
- ./dev-up.ps1 → bring stack up
- ./dev-logs.ps1 → follow logs
- ./dev-down.ps1 → stop & clean

Open http://localhost:9001 to create bucket `bhaktigen` if not auto-created.

Stripe CLI (optional): `stripe listen --forward-to localhost:8000/billing/webhook` to forward webhooks during local dev.

## Decision Log (2025-12-06)
- Store `input_json` & `parent_job_id` for lineage in `jobs_index`; implement regenerate by cloning stored plan with overrides.

## P4-Step2: Template Gallery + Built-In Presets (2025-12-07)

- Backend: `templates` table added; `init_db()` seeds built-ins from `app/templates/builtin/*.json` (idempotent). New `GET /templates/builtin` returns only built-in templates.
- Built-ins: 6 presets seeded (Hindu Quotes, Shiva Stories, Bhagavad Gita Explainer, Motivational Shorts, Devotional Slokas, AI Narrated Mythology) with simple 2-scene `plan_json`.
- Frontend: Added `TemplatesPage` with a Featured section (built-ins) and an All Templates grid; built-ins show an “Official” badge and hide edit/delete actions.
- Backward compatible with existing `/api/v1/templates` filesystem-based listing.
