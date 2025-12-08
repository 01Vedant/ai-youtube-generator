# DevotionalAI Platform - Quick Reference Guide

## 🚀 Quick Start (< 5 minutes)

### For Users (Dashboard)
```
1. Go to http://localhost:3000
2. Sign up with email
3. Click "New Project" → Select "Prahlad" template
4. Click "Generate Audio" → Select "Aria" voice
5. Click "Render Video" → Select "1080p"
6. Download video in 20 minutes
```

### For Developers (Local Setup)
```bash
# 1. Clone
git clone <repo-url>
cd devotionalai-platform

# 2. Config
cp cloud-config/.env.example .env
# Edit .env: add API keys if you want AI features

# 3. Run
docker-compose -f cloud-config/docker-compose.yml up -d

# 4. Access
# http://localhost:3000  (frontend)
# http://localhost:8000  (API docs)
# http://localhost:5432  (database)
```

---

## 📁 File Organization Cheat Sheet

### What File Does What?

| File/Folder | Purpose | Edit When... |
|---|---|---|
| `/platform/frontend/` | React dashboard UI | Adding features, fixing UI bugs |
| `/platform/backend/app/main.py` | FastAPI routes | Adding new endpoints |
| `/platform/backend/workers/` | Async tasks (TTS, image, video) | Tweaking generation quality |
| `/platform/templates/` | Story templates (JSON) | Adding new devotional stories |
| `/platform/docs/` | Documentation | Keeping docs up-to-date |
| `/platform/cloud-config/` | Deployment configs | Deploying to cloud |

### Core Files by Role

**Frontend Developer:**
- `/platform/frontend/src/pages/*.jsx`
- `/platform/frontend/src/components/*.jsx`
- `/platform/frontend/src/styles/*.css`

**Backend Developer:**
- `/platform/backend/app/main.py`
- `/platform/backend/app/models.py`
- `/platform/backend/workers/*.py`

**DevOps/Deployment:**
- `/platform/cloud-config/docker-compose.yml`
- `/platform/cloud-config/Dockerfile*`
- `/platform/cloud-config/kubernetes/`

**Content Creator:**
- `/platform/templates/*.json`
- Create new story templates here

---

## 🔌 API Endpoints at a Glance

### User Authentication
```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
GET    /api/v1/auth/me
```

### Project Management
```
POST   /api/v1/projects/create
GET    /api/v1/projects
GET    /api/v1/projects/{id}
PUT    /api/v1/projects/{id}
DELETE /api/v1/projects/{id}
```

### Asset Generation (Async)
```
POST   /api/v1/projects/{id}/generate/tts
POST   /api/v1/projects/{id}/generate/images
POST   /api/v1/projects/{id}/generate/subtitles
POST   /api/v1/projects/{id}/render/stitch
```

### Job Tracking
```
GET    /api/v1/jobs/{job_id}
GET    /api/v1/projects/{id}/jobs
```

### Downloads
```
GET    /api/v1/projects/{id}/download/video
GET    /api/v1/projects/{id}/download/assets
GET    /api/v1/projects/{id}/preview/image/{scene}
GET    /api/v1/projects/{id}/preview/audio/{scene}
```

### Templates
```
GET    /api/v1/templates
GET    /api/v1/templates/{template_id}
```

---

## 🎯 Common Tasks

### Add a New Story Template

1. Create `/platform/templates/my_story.json`
2. Copy format from `prahlad.json`
3. Fill in 6-8 scenes with prompts and voiceovers
4. Test in dashboard: "New Project" → Select template
5. Done! No code changes needed.

### Deploy to AWS

1. Create EC2 + RDS + S3 instances
2. SSH into EC2
3. Clone repo
4. Edit `.env` with AWS credentials
5. Run: `docker-compose -f cloud-config/docker-compose.yml up -d`
6. Setup Nginx + SSL
7. Access via domain name

### Scale Video Workers (Faster Rendering)

```bash
# Option 1: Docker Compose
docker-compose -f cloud-config/docker-compose.yml up -d --scale worker_video=3

# Option 2: Kubernetes
kubectl scale deployment video-worker --replicas=5

# Option 3: AWS ECS
# Update desired task count in console
```

### Add New API Endpoint

1. Edit `/platform/backend/app/main.py`
2. Add route with `@app.post()` or `@app.get()`
3. Import required models/functions
4. Restart backend: `docker-compose restart backend`
5. Test in Postman or http://localhost:8000/docs

### Add New UI Page

1. Create `/platform/frontend/src/pages/MyPage.jsx`
2. Add route in `App.jsx`: `<Route path="/mypage" element={<MyPage />} />`
3. Add menu link in `Sidebar.jsx`
4. Reload browser (dev mode auto-updates)

---

## 🐛 Troubleshooting Quick Fixes

### Problem: Video rendering stuck
```bash
# Check worker logs
docker-compose logs worker_video

# Restart workers
docker-compose restart worker_video

# Check disk space
df -h
```

### Problem: API returning 500 error
```bash
# Check backend logs
docker-compose logs backend

# Check database connection
docker-compose exec backend python -c "from app.models import User; print('OK')"

# Restart backend
docker-compose restart backend
```

### Problem: Images not generating
```bash
# Check if OPENAI_API_KEY is set
cat .env | grep OPENAI_API_KEY

# Check image worker logs
docker-compose logs worker_images

# Try with "local" engine (free placeholder)
```

### Problem: Out of disk space
```bash
# Delete old videos
rm -rf storage/*/projects/*/videos/*

# Or delete entire old project
docker-compose exec postgres psql -U devuser -d devotionalai -c "DELETE FROM projects WHERE created_at < NOW() - INTERVAL '30 days';"
```

---

## 📊 Architecture Overview (One Diagram)

```
[User Browser] 
    ↓ HTTPS
[Nginx Proxy]
    ↓ (splits traffic)
    ├→ [React Frontend :3000]
    ├→ [FastAPI Backend :8000]
    │   ├→ [PostgreSQL] (projects, users)
    │   ├→ [Redis Queue] (jobs)
    │   └→ [S3 Storage] (videos, images)
    │
    └→ [Celery Workers] (async tasks)
        ├→ TTS Worker (audio)
        ├→ Image Worker (images)
        ├→ Subtitle Worker (SRT)
        └→ Video Worker (stitching)
```

---

## 🎓 Learning Resources

### Understand the System
1. **Start here**: `/platform/docs/README.md`
2. **Architecture deep-dive**: `/platform/docs/SYSTEM_SUMMARY.md`
3. **API details**: `/platform/docs/API_REFERENCE.md`

### Deployment
1. **Local setup**: `/platform/docs/DEPLOYMENT_GUIDE.md` (Option A)
2. **Cloud setup**: `/platform/docs/DEPLOYMENT_GUIDE.md` (Option B/C)

### Customization
1. **Add templates**: `/platform/docs/ADDING_TEMPLATES.md`
2. **Frontend mods**: React docs + `/platform/frontend/` examples
3. **Backend mods**: FastAPI docs + `/platform/backend/app/` examples

---

## 📋 Checklist: New Feature

- [ ] Understand the feature (write spec)
- [ ] Identify affected components (frontend/backend/workers)
- [ ] Update database schema if needed (`models.py`)
- [ ] Add API endpoint (`main.py`)
- [ ] Update frontend UI (`pages/` or `components/`)
- [ ] Add worker task if async (`workers/`)
- [ ] Test locally (docker-compose)
- [ ] Write documentation
- [ ] Submit PR with tests

---

## 🔐 Security Checklist

- [ ] `.env` files NOT in git (use `.env.example`)
- [ ] API keys rotated monthly
- [ ] Database backups enabled
- [ ] HTTPS/SSL enforced in production
- [ ] CORS configured correctly
- [ ] Input validation on all endpoints
- [ ] Rate limiting on auth endpoints
- [ ] SQL injection protection (SQLAlchemy ORM used)

---

## 📈 Monitoring & Health

### Key Metrics to Watch

```bash
# API responsiveness
curl -w "\n%{http_code}\n" http://localhost:8000/health

# Database connection
docker-compose exec postgres pg_isready

# Redis queue depth
docker-compose exec redis redis-cli LLEN celery

# Disk usage
df -h /storage/

# Worker status
docker-compose exec backend celery inspect active
```

### Setup Monitoring (Optional)

```bash
# Enable Prometheus metrics
# See: /platform/cloud-config/monitoring/prometheus.yml

# View Grafana dashboard
# http://localhost:3001 (when using monitoring stack)
```

---

## 🚢 Deployment Checklist

### Before Going Live

- [ ] Env vars configured (API keys, database URL, S3 bucket)
- [ ] Database migrations run
- [ ] SSL certificate installed
- [ ] Backups configured
- [ ] Monitoring/alerting enabled
- [ ] Load testing done (target: 100 concurrent users)
- [ ] Security audit passed
- [ ] Documentation reviewed
- [ ] Team trained on ops

### Day 1 Launch

- [ ] Monitor API latency & error rates
- [ ] Check job queue depth
- [ ] Verify video quality
- [ ] User feedback collection
- [ ] Performance optimization

---

## 💰 Cost Optimization Tips

1. **Use Reserved Instances** (40% savings)
2. **Enable S3 Lifecycle** (auto-delete old videos)
3. **Compression** (reduce bitrate 20% - imperceptible quality loss)
4. **Spot Instances** for workers (70% cheaper, non-critical)
5. **Cache** frequently accessed data
6. **CDN** for video distribution (CloudFront)

---

## 🎯 What's Next?

### For Individual Use
1. Deploy locally
2. Create your first video
3. Share & get feedback
4. Iterate on templates

### For Business
1. Deploy on AWS
2. Invite users (teams/family)
3. Monetize (subscription/per-video)
4. Scale workers for speed

### For Developers
1. Contribute to GitHub
2. Add new features
3. Create marketplace templates
4. Build integrations

---

## 📞 Support Matrix

| Issue Type | Resource | Link |
|---|---|---|
| How do I use the dashboard? | FAQ | `/platform/docs/README.md` |
| How do I deploy? | Guide | `/platform/docs/DEPLOYMENT_GUIDE.md` |
| API not working? | Docs | `http://localhost:8000/docs` |
| Video rendering slow? | Troubleshoot | `/platform/docs/TROUBLESHOOTING.md` |
| Want to add a story? | Template Guide | `/platform/docs/ADDING_TEMPLATES.md` |
| Code bug/feature request? | GitHub | Issues |

---

## 🎬 Pro Tips

1. **Preview Before Stitching**: Use "Generate Images" with "local" engine first to test story flow
2. **Start with 1080p**: Faster testing, upgrade to 4K for final
3. **Use ElevenLabs**: Better audio quality than pyttsx3
4. **Scale Workers**: For multiple videos, increase worker count
5. **Template Reuse**: Create once, use for unlimited projects
6. **Batch Jobs**: Generate audio/images for multiple projects overnight

---

## Version Info

| Component | Version | Updated |
|---|---|---|
| Platform | 1.0.0 | Dec 2024 |
| FastAPI | 0.104.1 | Dec 2024 |
| React | 18.2 | Dec 2024 |
| MoviePy | 2.0.3 | Dec 2024 |
| Docker | 24.0+ | Dec 2024 |

---

**Questions?** Check `/platform/docs/` or raise an issue on GitHub! 🙏

**Want to contribute?** Fork the repo and submit a PR!

**Ready to launch your channel?** You have everything you need! 🚀
