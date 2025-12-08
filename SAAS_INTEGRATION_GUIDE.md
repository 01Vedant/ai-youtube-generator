# SaaS Integration - Exact Setup & Testing Guide

This document provides exact curl commands and configuration for integrating SaaS features with minimal diffs.

## Backend Integration Changes

### 1. main.py - 3 sections added

**Section A: Import SaaS modules (optional)**
```python
# After existing imports, before CORS middleware:
try:
    from app.middleware_tenancy import TenancyMiddleware
    from routes.auth import router as auth_router
    from routes.billing import router as billing_router
    from routes.account import router as account_router
    SAAS_ENABLED = True
except ImportError as e:
    logger.warning("SaaS modules not available (optional): %s", e)
    SAAS_ENABLED = False
```

**Section B: Add middleware (after existing middlewares)**
```python
# Add tenancy middleware early (after API key, before routes)
if SAAS_ENABLED:
    app.add_middleware(TenancyMiddleware)
```

**Section C: Include routers (after Creator routers)**
```python
# Include SaaS routers (auth, billing, account)
if SAAS_ENABLED:
    app.include_router(auth_router)
    app.include_router(billing_router)
    app.include_router(account_router)
```

**Section D: Add /me endpoint (in AUTH ENDPOINTS)**
```python
# Expose /me endpoint - updated version:
@app.get("/api/auth/me")
async def get_current_user(credentials: HTTPAuthCredentials = Depends(security)):
    """Get current authenticated user"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Return tenant info if SaaS enabled
    tenant_id = getattr(user, 'tenant_id', user_id)
    roles = getattr(user, 'roles', ['creator'])
    
    return {
        "user_id": user.id,
        "tenant_id": tenant_id,
        "email": user.email,
        "name": user.name,
        "roles": roles,
        "created_at": user.created_at
    }

# Add /me endpoint alias for SaaS compatibility
if SAAS_ENABLED:
    @app.get("/api/auth/me")
    async def get_current_user_saas(request: Request):
        """Get current user - SaaS compatible endpoint"""
        # Tenant info attached by TenancyMiddleware
        if not hasattr(request.state, 'user_id'):
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        return {
            "user_id": request.state.user_id,
            "tenant_id": request.state.tenant_id,
            "roles": getattr(request.state, 'roles', ['creator']),
        }
```

### 2. render.py - 4 changes

**Change 1: Add metering import (at top)**
```python
# Import SaaS modules (optional)
try:
    from app.metering import QuotaManager, UsageCounter
    METERING_ENABLED = True
except ImportError:
    METERING_ENABLED = False
```

**Change 2: Update _run_job_background signature**
```python
def _run_job_background(
    job_id: str, 
    plan_dict: dict, 
    request_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    # ... rest of function with usage metering added
```

**Change 3: Add quota check in POST /render**
```python
# Check quota if metering enabled
if METERING_ENABLED and tenant_id:
    try:
        quota_mgr = QuotaManager(tenant_id, plan_type="pro")
        quota_mgr.enforce_quota("render_minutes", 30)
    except HTTPException as e:
        if e.status_code == 402:
            raise HTTPException(status_code=402, detail={
                "error": "Quota exceeded",
                "message": "You've reached your monthly render quota. Upgrade to continue."
            })
        raise
```

**Change 4: Pass tenant info to background task**
```python
background_tasks.add_task(
    _run_job_background, 
    job_id, 
    plan_dict, 
    request_id,
    tenant_id,  # NEW
    user_id     # NEW
)
```

### 3. New Files (Already Delivered in Phase 2)

- `routes/auth.py` - Passwordless auth
- `routes/billing.py` - Stripe integration  
- `routes/account.py` - GDPR compliance
- `app/metering.py` - Usage tracking
- `app/middleware_tenancy.py` - Tenant isolation

## Frontend Integration Changes

### 1. App.jsx - Complete auth routing

See changes above - adds login page, protected routes, auth state, logout.

### 2. api.ts - Add SaaS methods

New functions added:
- `getMe()` - Get current user
- `requestMagicLink(email)` - Request login link
- `completeLogin(token)` - Verify magic link
- `logout()` - Sign out
- `getUsage()` - Get usage metrics
- `getPlan()` - Get subscription
- `getCheckoutUrl(plan)` - Get Stripe link
- `exportData()` - GDPR export
- `deleteTenant()` - Delete account
- `rotateApiKey()` - Rotate API key
- `getBackupStatus()` - Backup info

All methods include credentials: 'include' and auth headers.

### 3. New Frontend Files (Already Delivered in Phase 2)

- `pages/LoginPage.tsx` + CSS
- `pages/BillingPage.tsx` + CSS
- `pages/AccountPage.tsx` + CSS
- `components/UsageBanner.tsx` + CSS

## Environment Variables

Add to `.env`:

```bash
# Auth & Tenancy
JWT_SECRET=your-32-byte-random-string
JWT_EXPIRE_HOURS=24
MAGIC_LINK_TTL_MINUTES=15
MAGIC_LINK_FROM=noreply@bhakti.ai
SECURE_COOKIES=true
REDIS_URL=redis://localhost:6379/0

# Stripe Billing (optional)
STRIPE_API_KEY=sk_test_... or sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_ENTERPRISE=price_...

# Usage Quotas
QUOTA_IMAGES_COUNT=500
QUOTA_TTS_SECONDS=60000
QUOTA_RENDER_MINUTES=500
QUOTA_STORAGE_MB=100000
USAGE_LOG_DIR=./platform/usage

# Backups
BACKUP_DIR=/backups
BACKUPS_CRON="0 2 * * *"
BACKUPS_RETENTION_DAYS=30
TENANT_DEFAULT_PLAN=free
```

## Testing with Curl

### 1. Auth Flow

```bash
# Request magic link
curl -X POST http://localhost:8000/api/auth/magic-link/request \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com"}'

# Response: {"success": true, "message": "Check your email"}

# Verify magic link (token from email/Redis in test)
curl -X POST http://localhost:8000/api/auth/magic-link/verify \
  -H "Content-Type: application/json" \
  -d '{"token":"eyJ..."}' \
  -c cookies.txt

# Extract JWT from response
# {"access_token": "eyJ...", "user": {...}}
export JWT="eyJ..."

# Get current user
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $JWT"

# Response: {"user_id": "uuid", "tenant_id": "uuid", "roles": ["creator"]}
```

### 2. Quota Enforcement

```bash
# POST /render with low quota tenant
curl -X POST http://localhost:8000/render \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Test Video",
    "scenes": [{"description": "Scene", "duration_sec": 30, ...}]
  }'

# On quota exceeded:
# HTTP 402 Payment Required
# {"error": "Quota exceeded", "message": "...upgrade to continue"}

# On rate limited:
# HTTP 429 Too Many Requests
# {"error": "Rate limited", "message": "...too high"}
```

### 3. Billing

```bash
# Get subscription status
curl -X GET http://localhost:8000/api/billing/subscription \
  -H "Authorization: Bearer $JWT"

# Response: {"plan": "free", "status": "active"}

# Create checkout session
curl -X POST http://localhost:8000/api/billing/checkout \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"plan":"pro"}'

# Response: {"checkout_url": "https://checkout.stripe.com/..."}
```

### 4. Usage Tracking

```bash
# Get current usage
curl -X GET http://localhost:8000/api/usage \
  -H "Authorization: Bearer $JWT"

# Response:
# {
#   "images_count": 15,
#   "tts_seconds": 450,
#   "render_minutes": 25,
#   "storage_mb": 2500,
#   "quota_images_count": 500,
#   "quota_render_minutes": 500,
#   "period_start": "2025-01-01",
#   "period_end": "2025-01-31",
#   "plan": "pro"
# }
```

### 5. Account Management

```bash
# Export data (GDPR)
curl -X POST http://localhost:8000/api/account/export \
  -H "Authorization: Bearer $JWT"

# Response: 
# {"success": true, "download_url": "https://.../export-uuid.zip", "message": "..."}

# Delete account (async, 24h confirmation window)
curl -X POST http://localhost:8000/api/account/delete \
  -H "Authorization: Bearer $JWT"

# Response: {"success": true, "message": "Account deletion queued"}

# Rotate API key
curl -X POST http://localhost:8000/api/account/rotate-api-key \
  -H "Authorization: Bearer $JWT"

# Response: {"api_key": "new_sk_...", "message": "Key rotated"}

# Backup status
curl -X GET http://localhost:8000/api/account/backup-status \
  -H "Authorization: Bearer $JWT"

# Response: 
# {
#   "last_backup": "2025-01-05T02:00:00Z",
#   "next_backup": "2025-01-06T02:00:00Z",
#   "size_mb": 1250
# }
```

## Running E2E Smoke Tests

```bash
# Install dependencies
pip install pytest pytest-asyncio httpx

# Run tests (skips Stripe tests if no STRIPE_API_KEY)
pytest platform/tests/e2e/smoke_saas.py -v

# Run only non-Stripe tests
pytest platform/tests/e2e/smoke_saas.py -v -m "not requires_stripe"
```

## Minimal Diffs Summary

**Backend**: 
- main.py: 4 sections (~30 lines total diff)
- render.py: 4 changes (~40 lines total diff)
- Plus 5 new files (auth.py, billing.py, account.py, metering.py, middleware_tenancy.py)

**Frontend**:
- App.jsx: ~60 lines diff
- api.ts: ~250 lines of new SaaS methods added
- Plus 4 new files (LoginPage, BillingPage, AccountPage, UsageBanner)

**Tests**:
- 1 new e2e smoke test file

**Total new/changed**: ~360 lines of diffs + 12 new files

## Verification Checklist

- [ ] JWT_SECRET set to 32+ random bytes
- [ ] REDIS_URL points to running Redis
- [ ] STRIPE_API_KEY configured (or tests skip billing)
- [ ] All 5 SaaS modules copy/install successfully
- [ ] main.py imports SaaS modules without error
- [ ] render.py POST /render enforces quotas
- [ ] App.jsx handles auth state on boot
- [ ] Magic link auth flow works end-to-end
- [ ] Quota violation returns 402 Payment Required
- [ ] Usage tracking increments on each render step
- [ ] E2E smoke tests pass (or skip gracefully)

## Production Readiness

See SAAS_DEPLOYMENT.md for:
- Kubernetes deployment
- Monitoring & alerting
- Emergency runbooks
- Cost estimation
- Security best practices

