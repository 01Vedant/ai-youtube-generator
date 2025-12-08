# DevotionalAI Platform - Complete Documentation

> World-class, cloud-accessible platform for creating devotional videos at scale. Convert any Sanatan Dharma story into stunning 4K videos with AI-generated images, natural TTS audio, and cinematic subtitles.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Folder Structure](#folder-structure)
5. [API Reference](#api-reference)
6. [Dashboard Usage Guide](#dashboard-usage-guide)
7. [Deployment (Local & Cloud)](#deployment)
8. [Adding Stories & Templates](#adding-stories--templates)
9. [Troubleshooting](#troubleshooting)

---

## Overview

**DevotionalAI Platform** is a production-ready SaaS for creating high-quality devotional videos. It bridges the gap between creators (who may be non-technical) and advanced video production workflows.

### Key Features

✅ **Beautiful Web Dashboard** - No installation required; accessible from any device
✅ **Multi-User Support** - Each user has isolated projects and storage
✅ **Async Job Queueing** - Multiple videos render simultaneously without blocking
✅ **Cloud Storage Integration** - S3 or local filesystem support
✅ **4K Video Output** - Cinematic 3840x2160 resolution at 24 fps
✅ **AI Image Generation** - DALL-E 3, Stable Diffusion XL, Runway, or Luma integration
✅ **Natural TTS** - ElevenLabs or local pyttsx3 audio synthesis
✅ **Synchronized Subtitles** - Auto-generated SRT files with intelligent wrapping
✅ **Progress Tracking** - Real-time job status updates
✅ **One-Click Downloads** - Final video + all assets as ZIP

### Use Cases

- 📖 Devotional storytellers creating YouTube channels
- 🕉️ Religious educators producing educational content
- 🎓 Students learning about Sanatan Dharma
- 📹 Content creators needing bulk video generation
- 🎬 Production houses needing automated workflows

---

## Quick Start

### For End Users (Dashboard)

1. **Sign Up / Login**
   - Navigate to `https://devotionalai.example.com`
   - Create account or log in with email

2. **Create First Project**
   - Click "New Project" button
   - Choose a template (Prahlad, Krishna, Hanuman, etc.) or start blank
   - Give project a name

3. **Edit Story (Optional)**
   - Edit scene titles, voiceovers, image descriptions
   - Add custom intro/outro

4. **Generate Assets**
   - Click "Generate TTS" → Choose voice (Aria, Sagara, Daya)
   - Click "Generate Images" → Choose engine (DALL-E, SDXL, local)
   - Monitor progress in job queue

5. **Preview Assets**
   - Listen to audio clips
   - View scene images
   - Preview subtitles

6. **Render Final Video**
   - Click "Render Video"
   - Choose resolution (720p, 1080p, 4K) and quality
   - Wait for rendering to complete
   - Download MP4

---

## Architecture

### Tech Stack

**Backend:**
- **FastAPI** - Async Python web framework
- **SQLAlchemy** - ORM for database
- **Celery + Redis** - Async job queue
- **MoviePy** - Video composition
- **ElevenLabs/pyttsx3** - TTS
- **DALL-E 3/SDXL/Runway/Luma** - Image generation

**Frontend:**
- **React 18** - UI framework
- **Tailwind CSS** - Styling
- **Vite** - Build tool
- **Axios** - HTTP client

**Deployment:**
- **Docker** - Containerization
- **AWS S3** / **Google Drive** - Cloud storage
- **AWS EC2/Lambda** - GPU compute
- **PostgreSQL** - Production database
- **Redis** - Job queue backend

### Data Flow

```
┌─────────────────┐
│   Web Dashboard │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────────┐
│  FastAPI Backend    │
│  (routes, auth)     │
└────────┬────────────┘
         │
         ├──► Celery Job Queue (Redis)
         │    ├─ TTS Worker
         │    ├─ Image Worker
         │    ├─ Subtitle Worker
         │    └─ Video Worker
         │
         └──► Database (PostgreSQL)
         │    ├─ Users
         │    ├─ Projects
         │    └─ Jobs
         │
         └──► Cloud Storage (S3)
              ├─ users/{user_id}/projects/{project_id}/
              │  ├─ audio/
              │  ├─ images/
              │  ├─ subtitles/
              │  ├─ prompts/
              │  └─ videos/
```

---

## Folder Structure

```
platform/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app (all endpoints)
│   │   ├── models.py               # SQLAlchemy models
│   │   ├── auth.py                 # JWT authentication
│   │   ├── config.py               # Settings & environment
│   │   ├── storage.py              # S3 & local storage abstraction
│   │   └── celery_config.py        # Celery setup & task creation
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── tts_worker.py           # Generate audio (ElevenLabs/pyttsx3)
│   │   ├── image_worker.py         # Generate images (DALL-E/SDXL)
│   │   ├── subtitle_worker.py      # Generate SRT files
│   │   ├── video_worker.py         # Stitch video clips
│   │   └── utils.py                # Shared utilities
│   ├── requirements.txt            # Python dependencies
│   ├── Dockerfile                  # Backend container
│   └── .env.example                # Environment template
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx       # Main hub
│   │   │   ├── ProjectEditor.jsx   # Edit project settings
│   │   │   ├── VideoStudio.jsx     # Asset generation & rendering
│   │   │   ├── Templates.jsx       # Browse templates
│   │   │   ├── Settings.jsx        # User settings
│   │   │   ├── Login.jsx
│   │   │   └── Register.jsx
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   ├── ProjectCard.jsx
│   │   │   ├── NewProjectModal.jsx
│   │   │   ├── JobProgressCard.jsx
│   │   │   ├── SceneEditor.jsx
│   │   │   └── AssetPreview.jsx
│   │   ├── context/
│   │   │   └── AuthContext.jsx     # Auth state management
│   │   ├── services/
│   │   │   ├── api.js              # API client
│   │   │   └── websocket.js        # WebSocket for live updates
│   │   ├── styles/
│   │   │   ├── App.css
│   │   │   ├── Dashboard.css
│   │   │   ├── ProjectEditor.css
│   │   │   └── VideoStudio.css
│   │   └── App.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
│
├── templates/
│   ├── prahlad.json               # Prahlad Bhakt story (8 scenes)
│   ├── krishna.json               # Krishna Leela story
│   ├── hanuman.json               # Hanuman devotion
│   ├── rama.json                  # Ramayana
│   ├── durga.json                 # Durga Puja story
│   └── template_schema.json       # JSON schema for new templates
│
├── cloud-config/
│   ├── docker-compose.yml         # Local development setup
│   ├── docker-compose.prod.yml    # Production setup
│   ├── Dockerfile.backend
│   ├── Dockerfile.worker
│   ├── Dockerfile.frontend
│   ├── nginx.conf                 # Reverse proxy config
│   ├── .env.local
│   ├── .env.prod                  # Production environment
│   ├── aws-deployment.yml         # AWS CloudFormation template
│   └── kubernetes/
│       ├── deployment.yml
│       ├── service.yml
│       └── configmap.yml
│
├── docs/
│   ├── README.md                  # This file
│   ├── API_REFERENCE.md           # Detailed API docs
│   ├── DEPLOYMENT_GUIDE.md        # Cloud deployment steps
│   ├── ADDING_TEMPLATES.md        # How to create story templates
│   ├── ARCHITECTURE.md            # System design details
│   └── TROUBLESHOOTING.md
│
└── .github/
    ├── workflows/
    │   ├── ci.yml                 # GitHub Actions CI/CD
    │   └── deploy.yml             # Auto-deployment
    └── copilot-instructions.md    # For AI assistants
```

---

## API Reference

### Authentication

**POST /api/v1/auth/register**
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "name": "User Name"
}
```

**POST /api/v1/auth/login**
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**GET /api/v1/auth/me** (requires Bearer token)
Returns current user details

### Projects

**POST /api/v1/projects/create**
```json
{
  "name": "My Prahlad Video",
  "description": "Devotional video about Prahlad Bhakt",
  "template": "prahlad"  // optional
}
```

**GET /api/v1/projects** (paginated)
**GET /api/v1/projects/{project_id}**
**PUT /api/v1/projects/{project_id}**
**DELETE /api/v1/projects/{project_id}**

### Asset Generation

**POST /api/v1/projects/{project_id}/generate/tts**
```json
{
  "voice": "aria"  // aria, sagara, daya
}
```

**POST /api/v1/projects/{project_id}/generate/images**
```json
{
  "engine": "openai",  // openai, sdxl, runway, luma
  "quality": "preview"  // preview or final (4k)
}
```

**POST /api/v1/projects/{project_id}/generate/subtitles**
```json
{
  "language": "hindi"
}
```

### Video Rendering

**POST /api/v1/projects/{project_id}/render/stitch**
```json
{
  "resolution": "4k",  // 720p, 1080p, 4k
  "fps": 24
}
```

### Job Tracking

**GET /api/v1/jobs/{job_id}**
Returns job status with progress (0-100)

**GET /api/v1/projects/{project_id}/jobs**
Lists all jobs for a project

### Downloads

**GET /api/v1/projects/{project_id}/download/video**
Download final MP4 video

**GET /api/v1/projects/{project_id}/download/assets**
Download all assets as ZIP

**GET /api/v1/projects/{project_id}/preview/image/{scene_number}**
Preview scene image

---

## Dashboard Usage Guide

### 1. Create Project

1. Click "New Project" on Dashboard
2. Choose template or "Blank Project"
3. Enter project name and description
4. Click "Create"

**You're now in the Project Editor**

### 2. Edit Story (Optional)

In Project Editor:
- **Edit Scene Titles** - Click on scene title to edit
- **Edit Voiceover** - Update narration text (supports Hindi/English/Sanskrit)
- **Edit Image Prompt** - Modify AI image generation prompt
- **Add/Remove Scenes** - Use "+" and "×" buttons
- **Reorder Scenes** - Drag to reorder
- **Save Changes** - Auto-saves; watch for checkmark

### 3. Generate TTS Audio

1. Click "Generate Audio" button
2. Select voice (Aria, Sagara, Daya)
3. Choose engine:
   - **ElevenLabs** (recommended) - professional, natural
   - **pyttsx3** (free) - local, lower quality
4. Monitor progress (check "Jobs" panel)
5. Once complete, click "Preview" to listen

### 4. Generate Images

1. Click "Generate Images" button
2. Choose engine:
   - **DALL-E 3** - cinematic, detailed
   - **SDXL** - versatile, indie-friendly
   - **Local** - placeholder for testing
3. Choose quality:
   - **Preview** (720p) - fast, for testing
   - **Final** (4K) - slow, for production
4. Monitor progress (typically 1-2 min per image with DALL-E)
5. Once complete, click "Preview Images" to view

### 5. Generate Subtitles

1. Click "Generate Subtitles" button
2. Select language (Hindi, English, Sanskrit)
3. Watch progress
4. Subtitles auto-sync to audio

### 6. Render Final Video

1. Click "Render Video" button
2. Choose settings:
   - **Resolution**: 720p (fast), 1080p (medium), 4K (slow but stunning)
   - **FPS**: 24 (film) or 30 (smooth)
3. Confirm rendering
4. Grab coffee ☕ - video rendering takes time (15 min for 1080p, 60+ min for 4K)
5. Once complete:
   - Click "Download Video" to get MP4
   - Click "Download Assets" to get all project files

---

## Deployment

### Local Development

**Prerequisites:**
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- Redis
- PostgreSQL (or SQLite)

**Steps:**

```bash
# 1. Clone repo
git clone https://github.com/yourusername/devotionalai-platform.git
cd devotionalai-platform

# 2. Setup environment
cp .env.local.example .env
# Edit .env with your API keys (OpenAI, ElevenLabs, etc.)

# 3. Build and run with Docker Compose
docker-compose -f cloud-config/docker-compose.yml up -d

# 4. Initialize database
docker-compose exec backend python -m app.models

# 5. Access dashboard
# Frontend: http://localhost:3000
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Cloud Deployment (AWS)

**Option A: AWS EC2 + RDS + S3**

```bash
# 1. Create EC2 instance (t3.xlarge, Ubuntu 22.04)
# 2. Install Docker, Docker Compose
# 3. Clone repo and setup

# 4. Configure environment
export DATABASE_URL="postgresql://user:pass@rds-endpoint:5432/devotionalai"
export AWS_S3_BUCKET="devotionalai-videos"
export USE_S3=True

# 5. Deploy with docker-compose.prod.yml
docker-compose -f cloud-config/docker-compose.prod.yml up -d

# 6. Setup Nginx reverse proxy
sudo cp cloud-config/nginx.conf /etc/nginx/sites-available/devotionalai
sudo ln -s /etc/nginx/sites-available/devotionalai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# 7. SSL certificate (Let's Encrypt)
sudo certbot certonly --nginx -d devotionalai.example.com
```

**Option B: AWS ECS + Fargate**

Use the `aws-deployment.yml` CloudFormation template to spin up:
- Application Load Balancer
- ECS Fargate tasks (backend, workers, frontend)
- RDS PostgreSQL
- ElastiCache Redis
- S3 bucket for videos

```bash
aws cloudformation create-stack \
  --stack-name devotionalai \
  --template-body file://cloud-config/aws-deployment.yml \
  --parameters ParameterKey=Environment,ParameterValue=prod
```

**Option C: Kubernetes (GKE, EKS)**

```bash
kubectl apply -f cloud-config/kubernetes/

# Scale workers for high throughput
kubectl scale deployment video-worker --replicas=5
```

---

## Adding Stories & Templates

### Create a New Story Template

1. **JSON Template Format:**

```json
{
  "name": "Your Story Name",
  "description": "Brief description",
  "category": "devotional",
  "duration_minutes": 12,
  "scenes": [
    {
      "scene_number": 1,
      "scene_title": "Scene Title",
      "image_prompt": "Detailed AI image generation prompt...",
      "voiceover": "Hindi narration text...",
      "notes": "Duration: 10-12s. Camera: slow zoom. Tone: reverent."
    },
    ...
  ]
}
```

2. **Save in `/templates/your_story.json`**

3. **Add thumbnail (optional):**
   - Create 400x300 JPG at `/templates/thumbnails/your_story.jpg`

4. **Submit to platform:**
   - Templates auto-load from folder
   - No deployment needed; picked up immediately

### Example: Krishna Story

See `templates/krishna.json` for a fully-formatted 8-scene example.

---

## Troubleshooting

### Video Rendering is Slow

**Solution:**
- 4K rendering at 24fps is inherently slow (~1.5 sec/frame)
- Use 1080p for faster preview (~15 min)
- Use 4K for final output when you have time
- Consider GPU rendering (requires setup on cloud instance)

### Image Generation Failing

**Common Issues:**
1. **No DALL-E API key** → Uses placeholder images. Add `OPENAI_API_KEY` to continue.
2. **Rate limited** → Wait 1 hour before retrying
3. **Inappropriate content flagged** → Rephrase image prompt

### Audio/Subtitle Out of Sync

**Solution:**
1. Regenerate subtitles (sometimes helps)
2. Check audio duration vs. subtitle timing
3. Manually edit SRT files if needed

### Jobs Stuck in "Queued"

**Solution:**
1. Check Redis is running: `redis-cli ping`
2. Check Celery workers: `celery -A app inspect active`
3. Restart workers: `docker-compose restart worker`
4. Check logs: `docker-compose logs worker`

### Storage Full

**Solution:**
- Videos ~200-500 MB each (4K)
- Delete old projects: Settings → Delete Project
- Upgrade storage plan or enable S3 auto-cleanup

---

## Support & Contributing

- **Issues & Bugs:** GitHub Issues
- **Feature Requests:** GitHub Discussions
- **Email:** support@devotionalai.example.com
- **Community:** Discord server

---

## License & Attribution

DevotionalAI Platform is built with love for the devotional community.

- Powered by MoviePy, ElevenLabs, DALL-E, and open-source tools
- Inspired by the rich legacy of Sanatan Dharma storytelling

---

**Happy creating! 🙏**
