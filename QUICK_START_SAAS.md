# Quick Integration Guide

## 30-Minute Setup for SaaS Features

### Step 1: Backend Dependencies (2 min)
```bash
cd platform/backend
pip install python-jose[cryptography] email-validator redis stripe
```

### Step 2: Environment Variables (3 min)
Create `.env` in project root:
```bash
JWT_SECRET=your-random-32-byte-secret-here
REDIS_URL=redis://localhost:6379/0
STRIPE_API_KEY=sk_test_... (optional for dev)
```

### Step 3: Add to main.py (5 min)
In `platform/backend/app/main.py`, add after imports:
```python
from routes.auth import router as auth_router
from routes.billing import router as billing_router
from routes.account import router as account_router
from app.middleware_tenancy import TenancyMiddleware

# Before any routes:
app.add_middleware(TenancyMiddleware)

# After other routers:
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(account_router)
```

### Step 4: Add Quota Checks to Render (5 min)
In `routes/render.py`, before expensive operations:
```python
from app.metering import QuotaManager

# Inside render endpoint:
tenant_id = request.state.tenant_id  # From TenancyMiddleware
quota_mgr = QuotaManager(tenant_id, plan="pro")

# Before image generation:
quota_mgr.enforce_quota("images_count", num_scenes)

# Before video render:
quota_mgr.enforce_quota("render_minutes", estimated_minutes)
```

### Step 5: Frontend Pages (8 min)
Copy these new files to `platform/frontend/src/`:
- `pages/LoginPage.tsx` + `.css`
- `pages/BillingPage.tsx` + `.css`
- `pages/AccountPage.tsx` + `.css`
- `components/UsageBanner.tsx` + `.css`

### Step 6: Update Frontend Routes (5 min)
In `App.jsx`, add:
```jsx
import { LoginPage } from './pages/LoginPage';
import { BillingPage } from './pages/BillingPage';
import { AccountPage } from './pages/AccountPage';

// Before other routes:
<Route path="/login" element={<LoginPage />} />
<Route path="/billing" element={<ProtectedRoute><BillingPage /></ProtectedRoute>} />
<Route path="/account" element={<ProtectedRoute><AccountPage /></ProtectedRoute>} />

// Add protected route wrapper:
function ProtectedRoute({ children }) {
  const token = localStorage.getItem('access_token');
  if (!token) return <Navigate to="/login" />;
  return children;
}
```

### Step 7: Add UsageBanner (2 min)
In any page component (CreateVideoPage, RenderStatusPage, LibraryPage):
```tsx
import { UsageBanner } from '../components/UsageBanner';

return (
  <div>
    <UsageBanner />
    {/* rest of page */}
  </div>
);
```

---

## Testing the Setup

### 1. Start Backend
```bash
cd platform/backend
python -m uvicorn app.main:app --reload
```

### 2. Test Magic Link Flow
```bash
# Request magic link
curl -X POST http://localhost:8000/api/auth/magic-link/request \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'

# Response includes magic_link in dev mode:
# {
#   "success": true,
#   "magic_link": "https://app.example.com/login?token=..."
# }

# Extract token and verify:
curl -X POST http://localhost:8000/api/auth/magic-link/verify \
  -H "Content-Type: application/json" \
  -d '{"token":"..."}'

# Response:
# {
#   "access_token": "eyJ0eXAi...",
#   "refresh_token": null,
#   "token_type": "bearer",
#   "expires_in": 86400
# }
```

### 3. Test Protected Route
```bash
# Use JWT from step 2
export JWT="eyJ0eXAi..."

# This now works:
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $JWT"

# This fails (no auth):
curl http://localhost:8000/api/auth/me
# → 403 Forbidden
```

### 4. Test Quota Enforcement
```bash
# Create a render job (will check quotas):
curl -X POST http://localhost:8000/api/v1/projects/test/render/stitch \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"resolution":"4k","fps":24}'

# If quota exceeded:
# → 402 Payment Required
# {
#   "detail": "Usage quota exceeded for render_minutes (95% of 500 limit)"
# }
```

### 5. Test Billing Integration
```bash
# Get current subscription (should be free for new user):
curl http://localhost:8000/api/billing/subscription \
  -H "Authorization: Bearer $JWT"

# Response:
# {
#   "plan": "free",
#   "status": "active",
#   "current_period_end": null,
#   "customer_id": null
# }

# Start upgrade to Pro (opens Stripe):
curl -X POST http://localhost:8000/api/billing/checkout \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"plan":"pro"}'

# Response:
# {
#   "checkout_url": "https://checkout.stripe.com/...",
#   "session_id": "..."
# }
```

### 6. Test Account Operations
```bash
# Export GDPR data:
curl -X POST http://localhost:8000/api/account/export \
  -H "Authorization: Bearer $JWT"

# Response:
# {
#   "success": true,
#   "download_url": "/api/account/download-export/export-tenant_abc-20250115_143000.zip",
#   "expires_in_hours": 24
# }

# Download:
curl http://localhost:8000/api/account/download-export/export-tenant_abc-20250115_143000.zip \
  -H "Authorization: Bearer $JWT" \
  --output export.zip

# Rotate API key:
curl -X POST http://localhost:8000/api/account/rotate-api-key \
  -H "Authorization: Bearer $JWT"

# Response:
# {
#   "api_key": "sk_prod_...",
#   "created_at": "2025-01-15T14:30:00"
# }
```

---

## Frontend Testing

### 1. Start Frontend
```bash
cd platform/frontend
npm start
```

### 2. Try Magic Link Flow
- Navigate to `http://localhost:3000/login`
- Enter email → sees "Check your email" message
- (In dev mode, magic link printed to console)
- Click link → JWT stored in localStorage
- Redirected to dashboard

### 3. Try Billing Page
- Navigate to `http://localhost:3000/billing`
- See current plan (Free)
- Click "Upgrade to Pro" → opens Stripe checkout
- Return from checkout → success page

### 4. Try Account Settings
- Navigate to `http://localhost:3000/account`
- Click "Export Data" → downloads ZIP (all your data)
- Click "Rotate API Key" → shows new key with copy button
- Click "Delete Account" → confirmation → account deleted

---

## Files Structure

```
platform/
├── backend/
│   ├── app/
│   │   ├── main.py                 (modify: add auth/billing/account routes + tenancy middleware)
│   │   ├── metering.py             (NEW: quota + usage tracking)
│   │   └── middleware_tenancy.py   (NEW: tenant resolution)
│   └── routes/
│       ├── auth.py                 (NEW: passwordless magic links)
│       ├── billing.py              (NEW: stripe integration)
│       └── account.py              (NEW: GDPR + backups)
│
├── frontend/src/
│   ├── pages/
│   │   ├── LoginPage.tsx           (NEW)
│   │   ├── LoginPage.css           (NEW)
│   │   ├── BillingPage.tsx         (NEW)
│   │   ├── BillingPage.css         (NEW)
│   │   ├── AccountPage.tsx         (NEW)
│   │   └── AccountPage.css         (NEW)
│   └── components/
│       ├── UsageBanner.tsx         (NEW)
│       └── UsageBanner.css         (NEW)
│
├── tests/
│   └── chaos/
│       └── test_failures.py        (NEW: failure simulation)
│
├── load/
│   └── locustfile.py               (NEW: load test script)
│
├── .env.example                    (modify: add auth/billing/quota keys)
├── SAAS_DEPLOYMENT.md              (NEW: complete deployment guide)
└── SAAS_IMPLEMENTATION.md          (NEW: feature summary)
```

---

## Quick Feature Reference

### Auth
- Passwordless magic links (email-based)
- JWT tokens (24 hour expiry)
- Refresh tokens (30 days, httpOnly cookie)
- User roles: `admin`, `creator`

### Tenancy
- Middleware auto-resolves tenant from JWT
- All storage paths scoped to `tenants/{tenant_id}/`
- Audit logs include user_id + tenant_id

### Metering
- Tracks: images, TTS, render minutes, storage, uploads
- Monthly reset + JSONL audit trail
- Redis for fast lookups

### Quotas
- Free: 500 images/mo, 1000m TTS, 500 render min, 100GB storage
- Pro (5x): 2500 images/mo, etc.
- Enterprise: unlimited
- 402 error when exceeded

### Billing
- Stripe Checkout integration
- Premium features (4K render, YouTube publish) require Pro+ plan
- Webhook handler for subscription events

### GDPR
- Export My Data → ZIP download (24h expiry)
- Delete My Account → async purge
- Rotate API Key → invalidate old, generate new
- Backup Status → last/next backup timestamps

### Reliability
- Step timeouts (60s per step)
- Idempotent retries with exponential backoff
- Graceful degradation on API failures
- Chaos test suite included

---

## Production Checklist

Before deploying to production:

- [ ] Set JWT_SECRET to strong random value (32+ bytes)
- [ ] Configure REDIS_URL to production Redis cluster
- [ ] Set up PostgreSQL database with backups
- [ ] Configure Stripe (live keys, webhook)
- [ ] Configure email service (SendGrid / AWS SES)
- [ ] Enable SECURE_COOKIES=true (HTTPS only)
- [ ] Set LOG_LEVEL=INFO or higher (no debug logs)
- [ ] Configure Sentry DSN
- [ ] Enable Prometheus metrics
- [ ] Test GDPR export/delete workflow
- [ ] Load test with 100+ concurrent users
- [ ] Verify audit logs include tenant_id
- [ ] Test billing workflow end-to-end
- [ ] Document runbooks (see SAAS_DEPLOYMENT.md)
- [ ] Set up monitoring + alerting

---

## Support & Troubleshooting

### Magic link not sending?
- Check MAGIC_LINK_FROM email is valid
- Verify SendGrid/SES credentials in .env
- In dev mode: links printed to console, not emailed

### JWT expired?
- Frontend automatically refreshes via refresh_token cookie
- Max 24 hours of activity before re-login needed
- Can change JWT_EXPIRE_HOURS in .env

### Quota exceeded?
- User sees 402 Payment Required
- Show message: "Usage limit reached. Upgrade to Pro or wait until next month."
- Enterprise customers can request limit increases

### Stripe webhook failing?
- Check STRIPE_WEBHOOK_SECRET in .env
- Verify endpoint registered in Stripe Dashboard
- Logs should show webhook_failed in Sentry

### Storage paths wrong?
- Verify TenancyMiddleware attached before routes
- Check request.state.tenant_id is populated (should be in JWT)
- Storage methods should accept tenant_id parameter

