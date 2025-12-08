# PRODUCTION DEPLOYMENT GUIDE - SaaS Edition

Complete guide for deploying DevotionalAI Platform with multi-tenant auth, billing, metering, and reliability hardening.

---

## 1. ARCHITECTURE OVERVIEW

### Multi-Tenant SaaS Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ LoginPage → Magic Link → JWT (httpOnly cookie) → AppPages │   │
│  │ UsageBanner on Create/Status/Library                      │   │
│  │ BillingPage (Stripe) | AccountPage (GDPR/API keys)       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
         ┌────────────────────────────────────────┐
         │   API Gateway / Load Balancer          │
         │   (TenancyMiddleware attached)        │
         └────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       Backend (FastAPI)                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ routes/auth.py         → Magic links + JWT              │    │
│  │ middleware_tenancy.py  → Resolve tenant_id, scope paths │    │
│  │ metering.py + quotas   → Track usage, enforce limits    │    │
│  │ routes/billing.py      → Stripe integration + guards    │    │
│  │ routes/account.py      → GDPR export, delete, backups   │    │
│  │ routes/render.py       → (existing) with quota checks   │    │
│  │ routes/templates.py    → (existing) public access       │    │
│  │ Orchestrator           → Step timeouts, idempotent retry│    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────┬──────────────┬──────────────┐
        ↓             ↓              ↓              ↓
      Auth      Tenancy         Storage         Database
     (Redis)    (Middleware)   (S3/Local)      (PostgreSQL)
                              │ tenants/
                              │ └── {tenant_id}/
                              │     ├── jobs/
                              │     ├── videos/
                              │     └── backups/
```

---

## 2. AUTH & PASSWORDLESS FLOW

### Prerequisites
```bash
pip install python-jose[cryptography] email-validator redis stripe
```

### Setup

1. **Environment Variables** (.env)
```
JWT_SECRET=use-cryptographically-secure-random-string
JWT_EXPIRE_HOURS=24
MAGIC_LINK_TTL_MINUTES=15
MAGIC_LINK_FROM=noreply@devotionalai.example.com
REDIS_URL=redis://redis:6379/0
SECURE_COOKIES=true  # HTTPS only in prod
```

2. **Email Service** (SendGrid / AWS SES)
- Configure in routes/auth.py `request_magic_link()` endpoint
- Current: logs magic link to console (dev mode)
- Production: integrate SendGrid or AWS SES to send actual emails

### User Flow
```
1. User enters email → POST /api/auth/magic-link/request
2. Backend generates one-time token (15 min TTL), stores in Redis
3. Email sent with magic link: https://app.example.com/login?token={token}
4. User clicks link → frontend calls POST /api/auth/magic-link/verify
5. Backend returns JWT + refresh_token (httpOnly cookie)
6. Frontend stores JWT in localStorage, uses for all API calls
7. On 401, exchange refresh_token for new JWT via POST /api/auth/refresh
```

### Adding to main.py
```python
from routes.auth import router as auth_router
from app.middleware_tenancy import TenancyMiddleware

app.add_middleware(TenancyMiddleware)
app.include_router(auth_router)
```

---

## 3. TENANCY & STORAGE ISOLATION

### How It Works

**TenancyMiddleware** (middleware_tenancy.py):
- Extracts JWT from Authorization header or refresh_token cookie
- Resolves `tenant_id` and `user_id` from JWT claims
- Attaches to `request.state` for downstream use
- Guards authenticated routes by checking for valid JWT

**Storage Path Scoping**:
```
S3 (or local):
  tenants/
  ├── tenant_a1b2c3/
  │   ├── jobs/
  │   ├── videos/
  │   ├── images/
  │   └── backups/
  ├── tenant_x9y8z7/
  │   └── (same structure)
```

**In storage.py**, update methods to accept `tenant_id`:
```python
def get_project_path(self, tenant_id: str, project_id: str) -> str:
    return f"tenants/{tenant_id}/projects/{project_id}"
```

### Audit Logging

All routes should include tenant_id in audit logs:
```python
from app.audit import log_event

# In any route
tenant_id = request.state.tenant_id
user_id = request.state.user_id
log_event("render_started", user_id=user_id, tenant_id=tenant_id, job_id=job_id)
```

---

## 4. USAGE METERING & QUOTAS

### How It Works

**metering.py**:
- `UsageCounter(tenant_id)`: increment usage in Redis + append to monthly JSONL log
- `QuotaManager(tenant_id, plan)`: check/enforce limits based on plan tier

**Step 1: Track Usage in Orchestrator**

In `orchestrator.py` or `routes/render.py`, after each step:
```python
from app.metering import UsageCounter

counter = UsageCounter(tenant_id)
counter.increment("images_count", 3)       # 3 images generated
counter.increment("tts_seconds", 45.5)    # 45.5 seconds of audio
counter.increment("render_minutes", 12)   # 12 minutes of video render
```

**Step 2: Enforce Quota Before High-Cost Operations**

```python
from app.metering import QuotaManager

quota_mgr = QuotaManager(tenant_id, plan="pro")
quota_mgr.enforce_quota("images_count", 5)  # Raises 402 if exceeded
quota_mgr.enforce_quota("render_minutes", 15)
```

**Usage Log Format** (`platform/usage/usage-202501.jsonl`):
```json
{"timestamp":"2025-01-15T14:30:00","tenant_id":"tenant_a1b2c3","metric":"images_count","amount":3}
{"timestamp":"2025-01-15T14:31:00","tenant_id":"tenant_a1b2c3","metric":"tts_seconds","amount":45.5}
```

### Quota Tiers

| Plan      | Images/mo | TTS Seconds/mo | Render Min/mo | Storage |
|-----------|-----------|----------------|---------------|---------|
| Free      | 500       | 60,000 (1000m) | 500           | 100 GB  |
| Pro (5x)  | 2,500     | 300,000        | 2,500         | 500 GB  |
| Enterprise| ∞         | ∞              | ∞             | ∞       |

---

## 5. BILLING & STRIPE INTEGRATION

### Prerequisites
```bash
pip install stripe
```

### Setup

1. **Stripe Account**
- Create products: "Pro" and "Enterprise" plans
- Note Price IDs: `price_1234567890` etc.

2. **Environment Variables**
```
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PRO=price_1234567890
STRIPE_PRICE_ENTERPRISE=price_0987654321
```

3. **Webhook Endpoint**
- Configure in Stripe Dashboard: Events → `customer.subscription.*`
- Point to: `https://api.example.com/api/billing/webhook`

### Features

**Routes**:
- `POST /api/billing/checkout` → Create Stripe session, return checkout_url
- `GET /api/billing/subscription` → Get current plan + status
- `POST /api/billing/webhook` → Handle Stripe events (creation, cancellation)

**Premium Features Guard** (in routes/render.py):
```python
from routes.billing import require_paid_subscription

@app.post("/api/v1/projects/{project_id}/render/stitch")
async def stitch_video(
    project_id: str,
    resolution: str = "4k",  # 4K is premium
    current_user: dict = Depends(require_paid_subscription),
):
    # User must have active Pro+ subscription
    if resolution == "4k":
        quota_mgr = QuotaManager(current_user["tenant_id"], plan="pro")
        quota_mgr.enforce_quota("render_minutes", 15)
```

---

## 6. DATA PROTECTION & ACCOUNT MANAGEMENT

### GDPR Compliance

**routes/account.py** provides:

1. **Export My Data** → ZIP of all tenant assets
   ```bash
   POST /api/account/export
   → /api/account/download-export/{filename}  (24h expiry)
   ```

2. **Delete Account** → Async purge of all data
   ```bash
   POST /api/account/delete?confirm=true
   → Queued background job, all data deleted within 24h
   ```

3. **Rotate API Key** → Invalidate old, generate new
   ```bash
   POST /api/account/rotate-api-key
   → Returns new key (shown once)
   ```

### Backups

**Nightly backup job** (implement in Celery):
```python
@celery_app.task(name="backup_tenant_data")
def backup_tenant_data(tenant_id: str):
    """Nightly: copy job_summary.json + plans to backups/{date}/"""
    backup_date = datetime.utcnow().strftime("%Y%m%d")
    backup_path = f"backups/{backup_date}/{tenant_id}/"
    
    # Copy job summaries from tenants/{tenant_id}/jobs/ → backup_path
    # Compress if > 100MB
```

---

## 7. RELIABILITY & SCALE

### Orchestrator Improvements

**Step Timeouts**:
```python
# In orchestrator.py
import asyncio

async def execute_step(step_type: str, *args, **kwargs):
    try:
        result = await asyncio.wait_for(
            _do_step(step_type, *args, **kwargs),
            timeout=300  # 5 min per step
        )
    except asyncio.TimeoutError:
        logger.error(f"Step {step_type} timed out")
        # Retry with backoff (exponential: 2s, 4s, 8s, then fail)
```

**Idempotent Retries**:
```python
# Use idempotency key to prevent duplicate work
idempotency_key = f"{job_id}:{step_type}:{attempt}"
cached_result = redis_client.get(f"step:{idempotency_key}")
if cached_result:
    return json.loads(cached_result)

# Do work...
result = ...

# Cache result
redis_client.setex(f"step:{idempotency_key}", 86400, json.dumps(result))
return result
```

### Metrics & Autoscaling

**Prometheus Metrics** (in app/metrics.py):
```python
queue_depth = Gauge("render_queue_depth", "Jobs waiting in queue")
worker_busy = Gauge("worker_busy_count", "Workers currently busy")
step_duration = Histogram("step_duration_seconds", "Time per step")
```

**Worker Autoscale Hints**:
- If `queue_depth > 50`: scale up workers
- If `worker_busy < 0.3`: scale down
- Kubernetes HPA can read from Prometheus

### Chaos Testing

See `tests/chaos/test_failures.py`:
- Image gen timeouts → 408, friendly message
- TTS API down → fallback to pyttsx3
- FFmpeg stuck → 60s timeout, retry with backoff
- Disk full → 507 Insufficient Storage

### Load Testing

```bash
pip install locust

locust -f platform/load/locustfile.py \
  --host=http://localhost:8000 \
  -u 100 \
  -r 20 \
  --run-time 10m
```

---

## 8. DEPLOYMENT CHECKLIST

### Pre-Production

- [ ] Database: PostgreSQL with SSL, backups every 6 hours
- [ ] Cache: Redis Cluster for HA
- [ ] Storage: S3 with versioning + lifecycle policies
- [ ] Auth: JWT_SECRET is cryptographically random (32+ bytes)
- [ ] Billing: Stripe live keys, webhook verified
- [ ] Email: SendGrid/SES configured, test email works
- [ ] Monitoring: Sentry, Prometheus, ELK stack running
- [ ] Certificates: TLS 1.3+, HSTS enabled
- [ ] CORS: Only allow frontend origin
- [ ] Rate Limiting: 60 req/min per IP, 10 req/sec per user
- [ ] Audit Logging: All user actions logged with tenant_id
- [ ] Backups: Nightly automated, tested recovery

### Kubernetes Deployment

```yaml
# deployment.yaml excerpt
env:
  - name: JWT_SECRET
    valueFrom:
      secretKeyRef:
        name: auth-secrets
        key: jwt-secret
  - name: STRIPE_API_KEY
    valueFrom:
      secretKeyRef:
        name: stripe-secrets
        key: api-key
  - name: REDIS_URL
    value: "redis://redis-cluster.default.svc.cluster.local:6379"

livenessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /readyz
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5

resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "2000m"
    memory: "2Gi"
```

### Docker Setup

```dockerfile
# Dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg
RUN pip install --no-cache -r requirements.txt

COPY app /app/app
COPY routes /app/routes
COPY platform /app/platform

ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose (Dev)

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:pass@db:5432/devai
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: postgres
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

---

## 9. MONITORING & ALERTING

### Key Metrics to Track

```
- API latency (p50, p99)
- Queue depth (target < 20 jobs)
- Image gen success rate (target > 98%)
- TTS success rate (target > 98%)
- Render success rate (target > 95%)
- Storage usage by tenant
- Revenue by plan (MRR)
- Churn rate
```

### Alert Rules (Prometheus)

```yaml
groups:
  - name: sla
    rules:
      - alert: RenderQueueBacklog
        expr: render_queue_depth > 100
        for: 5m
        annotations:
          summary: "Render queue backlog: {{ $value }} jobs"

      - alert: ImageGenFailureRate
        expr: rate(image_gen_failures[5m]) > 0.02
        for: 10m
        annotations:
          summary: "Image gen failure rate > 2%"
```

---

## 10. COST ESTIMATION (AWS)

**Monthly for 1,000 paying users (Pro tier)**:

| Component          | Cost    | Notes                 |
|--------------------|---------|------------------------|
| RDS (PostgreSQL)   | $500    | Multi-AZ, 100GB       |
| ElastiCache        | $200    | Redis Cluster         |
| S3 Storage         | $1,000  | ~500GB user projects  |
| S3 Transfer        | $1,500  | Outbound data         |
| EC2 (API servers)  | $3,000  | 3x t3.2xlarge + LB    |
| EC2 (Workers)      | $2,000  | 10x t3.large          |
| SendGrid           | $150    | Email @ $0.15/mo      |
| Sentry             | $500    | Error tracking        |
| Stripe             | $2,900  | 2.9% + $0.30/txn      |
| **Total**          | **$11,750** | **~$12/user/month** |

---

## 11. SECURITY BEST PRACTICES

1. **API Keys**: Rotate monthly, store in AWS Secrets Manager
2. **Database**: Use RDS IAM auth, encrypt at rest
3. **Backups**: Test recovery quarterly, store off-region
4. **Secrets**: Never commit to git, use .env + CI/CD secrets
5. **CORS**: Whitelist only frontend domain
6. **Rate Limits**: 60 req/min global, 10 req/sec per user
7. **Audit Logs**: All mutations logged to Sentry + local JSON
8. **HTTPS**: Enforce TLS 1.3+, HSTS 1 year
9. **GDPR**: Data minimization, deletion, exports
10. **DDoS**: Use Cloudflare or AWS Shield

---

## 12. RUNBOOKS

### Emergency Procedures

**Database Down**
- Failover to read replica (RDS: 1-3 min)
- Notify users: "Experiencing database maintenance"
- Disable image generation (cache tier)
- Keep API gateway responding 503

**Redis Down**
- Ephemeral: can restart safely (session loss acceptable)
- Graceful degradation: fallback to in-memory session store
- Alert: manual intervention needed if > 10 min

**Mass Quota Overage**
- Investigate: audit logs for bot/abuse
- Soft reset: extend quotas 10% if legitimate spike
- Hard reset: disable high-cost features (4K, YouTube publish)

**Billing Webhook Failures**
- Retry queue via Celery: exponential backoff 5 times
- Manual reconciliation: query Stripe API weekly
- Alert: Sentry webhook_failed alert

