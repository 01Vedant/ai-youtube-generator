# Release Checklist

- Security headers enabled (prod): CSP set or default.
- Marketplace flag OFF by default in prod.
- E2E tests green (simulate render).
- Legal pages accessible under `/legal/terms` and `/legal/privacy`.
 
## Compliance / Legal
- [ ] Verify `/legal/*` endpoints render HTML (terms, privacy, cookies, imprint)
- [ ] Footer links visible on all pages: Privacy · Terms · Cookies · Imprint
- Privacy request endpoints responding.
- Status endpoints: `/status.json` and `/status`.
- Prometheus alert rules mounted and reloaded.
- Backup script tested; retention respected.
- Canary gating verified via `FEATURE_CANARY`.
