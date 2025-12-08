# Project State

## Launch Toggle: FEATURE_TEMPLATES_MARKETPLACE
- Backend flag: `FEATURE_TEMPLATES_MARKETPLACE` (default OFF)
- Frontend flag: `VITE_FEATURE_TEMPLATES_MARKETPLACE` (default OFF)
- When OFF: backend 404s marketplace endpoints; frontend hides route and links.

## E2E Smoke + CI
- Playwright tests added under `platform/frontend/e2e/`.
- CI job `e2e.yml` runs simulate render.

## Legal & Privacy
- Legal routes under `/legal/*` with MD payloads.
- Privacy requests: `/privacy/request-export`, `/privacy/request-delete` simulate jobs.
 - Added backend /legal/* markdown-backed HTML pages + frontend legal index + footer links.

## Status
- Public `/status.json` and `/status` static page.

## Security
- SecurityHeadersMiddleware adds CSP and headers in prod.

## Backup
- DB backup script: `scripts/backup.ps1` with retention.

## Prometheus
- Alert rules in `monitoring/alert_rules.yml`.
