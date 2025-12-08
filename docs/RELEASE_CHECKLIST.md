## Feedback Feature Checklist

- `/feedback` POST/GET functional with auth + admin guard
- Floating Feedback button appears when logged in
- Admin page lists recent feedback
- `VITE_FEEDBACK_ENABLED` flag respected to toggle UI

## Public + Waitlist Checklist

- Public landing enabled when `VITE_PUBLIC_ENABLED=true`
- SEO tags present for landing and templates pages
- `/public/robots.txt` and `/public/sitemap.xml` return expected content
- Waitlist POST inserts; admin CSV available at `/admin/waitlist.csv`
- Public templates gallery reachable at `/templates/public`
 - Rate-limit triggers at >10/day/IP and >1/15s; 429 returns `{ code:"QUOTA_EXCEEDED", detail:{ metric, limit, reset_at } }`
 - CSV has `Content-Disposition: attachment; filename=waitlist.csv`

## Public Preview Checklist

- Public pages load (`/`, `/templates/public`) with header/footer
- Waitlist submit works (success + duplicate UX)
- `robots.txt` and `sitemap.xml` OK
- SEO tags present on `/` and `/templates/public`
- Legal footer visible
- 404 page renders in public mode
- Rate-limit returns 429 JSON with code/detail
- Admin CSV downloads via `/admin/waitlist.csv`
# Release Checklist

- [ ] Pull `main`; run `./scripts/verify_release.ps1`
- [ ] Backend: start `uvicorn` locally; check `GET http://127.0.0.1:8000/health/ready` returns 200
- [ ] Frontend: `cd platform/frontend && npm run typecheck` succeeds
- [ ] Plans & quotas: call `/usage/today` as Pro & Free; verify limits/deltas
- [ ] Stripe (mock): `pytest platform/backend/tests/test_billing.py -q` passes
- [ ] S3/MinIO: `docker compose -f docker-compose.dev.yml up -d`; check `/version` and `/metrics`
- [ ] Render: submit demo plan; worker processes; artifacts manifest returns URLs
- [ ] Share: create share link (`/s/:id`), open; revoke; confirm 404
- [ ] Export: mock export returns URL; UI opens link
- [ ] Queue Admin: page loads; “Check live” works; stale badge visible when applicable
- [ ] Maintenance Mode: enable/disable; verify 503 envelope + Retry-After
- [ ] Maintenance bypass: health/version/webhook; allowlist IP; admin user
- [ ] Operations: Run purge dry-run; verify summary logs; run actual purge on staging
 - [ ] Admin: Admin role can access dashboard; filters/sort working; CSV exports match JSON counts; non-admin blocked (403)
 - [ ] Security: Refresh rotates jti (old invalid); Logout revokes refresh; CSRF required on refresh/logout; prod cookie Secure + SameSite=Lax
- [ ] Tag release: `git tag vX.Y.Z && git push origin vX.Y.Z`

## Troubleshooting

- Node/npm missing: install Node 20 (https://nodejs.org/) and rerun frontend steps.
- Playwright install issues: run `npx playwright install --with-deps` in `platform/frontend`.
- Windows PowerShell execution policy: `Set-ExecutionPolicy -Scope Process Bypass -Force` to allow running `verify_release.ps1`.
