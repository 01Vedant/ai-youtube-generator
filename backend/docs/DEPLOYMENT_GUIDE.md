# DevotionalAI Platform - Quick Start & Deployment Guide

## Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose
- Git
- 20GB free disk space (for videos and models)
- API keys (optional): OpenAI, ElevenLabs

### Step 1: Clone & Setup

```bash
git clone https://github.com/yourusername/devotionalai-platform.git
cd devotionalai-platform
cp cloud-config/.env.example .env
```

### Step 2: Configure .env

Edit `.env` with your API keys:

```bash
nano .env
# Required for image generation:
# OPENAI_API_KEY=sk-...
# ELEVENLABS_API_KEY=sk-...
```

### Step 3: Start Local Stack

```bash
# Start all services (backend, frontend, database, cache)
docker-compose -f cloud-config/docker-compose.yml up -d

# OR with workers
docker-compose -f cloud-config/docker-compose.yml --profile workers up -d

# Watch logs
docker-compose -f cloud-config/docker-compose.yml logs -f backend
```

### Step 4: Access Dashboard

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Adminer (DB)**: http://localhost:8080 (optional)

### Step 5: Create First Account

1. Go to http://localhost:3000
2. Click "Sign Up"
3. Enter email and password
4. Create account

### Step 6: Create First Project

1. Click "New Project"
2. Select "Prahlad" template
3. Name: "My First Devotional Video"
4. Click "Create"

### Step 7: Generate Assets (Quick Test)

1. **Generate TTS**:
   - Click "Generate Audio"
   - Select voice "Aria"
   - Wait for completion (~30s per scene)

2. **Generate Images** (with placeholder):
   - Click "Generate Images"
   - Select "local" engine (free, instant)
   - Wait for completion (~1s per scene)

3. **Render Video**:
   - Click "Render Video"
   - Select "1080p" resolution (faster for testing)
   - Wait for rendering (~10-15 minutes)

4. **Download**:
   - Once complete, click "Download Video"
   - Save to your device

---

## Production Deployment (AWS)

### Option A: EC2 + RDS + S3 (Recommended for Startups)

#### Prerequisites
- AWS account with EC2, RDS, S3 access
- Elastic IP for server
- Domain name (optional but recommended)

#### Step 1: Create AWS Resources

```bash
# 1. Create EC2 Instance
# Type: t3.xlarge (4 vCPU, 16GB RAM)
# OS: Ubuntu 22.04 LTS
# Storage: 100GB gp3
# Security Group: Open ports 22, 80, 443

# 2. Create RDS PostgreSQL
# Engine: PostgreSQL 15.3
# Instance: db.t3.large (2 vCPU, 8GB RAM)
# Storage: 50GB gp3
# Backup: 30 days

# 3. Create S3 Bucket
# Name: devotionalai-videos
# Region: us-east-1
# Block all public access

# 4. Create Redis (ElastiCache)
# Engine: Redis 7.0
# Node type: cache.t3.medium
# Number of replicas: 1
```

#### Step 2: SSH into EC2 & Install Dependencies

```bash
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Nginx
sudo apt install nginx -y
```

#### Step 3: Deploy Application

```bash
# Clone repository
git clone https://github.com/yourusername/devotionalai-platform.git
cd devotionalai-platform

# Copy production environment
cp cloud-config/.env.example .env

# Edit with production values
sudo nano .env
# Set:
# DEBUG=False
# DATABASE_URL=postgresql://user:password@rds-endpoint:5432/devotionalai
# AWS_S3_BUCKET=devotionalai-videos
# USE_S3=True
# OPENAI_API_KEY=sk-...
# ELEVENLABS_API_KEY=sk-...
```

#### Step 4: Start Services

```bash
# Build and start
docker-compose -f cloud-config/docker-compose.yml --profile workers up -d

# Verify
docker-compose ps
docker-compose logs backend
```

#### Step 5: Setup Nginx Reverse Proxy

```bash
sudo tee /etc/nginx/sites-available/devotionalai > /dev/null <<EOF
server {
    listen 80;
    server_name devotionalai.example.com;

    # Redirect HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name devotionalai.example.com;

    ssl_certificate /etc/letsencrypt/live/devotionalai.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/devotionalai.example.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }

    # API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/devotionalai /etc/nginx/sites-enabled/

# Test config
sudo nginx -t

# Start nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

#### Step 6: Setup SSL Certificate (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot certonly --standalone -d devotionalai.example.com -d www.devotionalai.example.com

# Auto-renewal (cron)
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

#### Step 7: Monitor & Maintain

```bash
# View logs
docker-compose logs -f

# Scale workers (for faster video rendering)
docker-compose -f cloud-config/docker-compose.yml up -d --scale worker_video=3

# Database backups
# RDS automatic backups are enabled (30 days retention)

# Monitor disk space
df -h

# Check API health
curl https://devotionalai.example.com/health
```

---

### Option B: Kubernetes (GKE/EKS) for Scale

Use `cloud-config/kubernetes/` manifests:

```bash
# Create namespace
kubectl create namespace devotionalai

# Deploy PostgreSQL
kubectl apply -f cloud-config/kubernetes/postgres.yml

# Deploy Redis
kubectl apply -f cloud-config/kubernetes/redis.yml

# Deploy backend
kubectl apply -f cloud-config/kubernetes/backend.yml

# Deploy workers (scale as needed)
kubectl apply -f cloud-config/kubernetes/workers.yml
kubectl scale deployment video-worker --replicas=5 -n devotionalai

# Deploy frontend
kubectl apply -f cloud-config/kubernetes/frontend.yml

# Expose via LoadBalancer or Ingress
kubectl apply -f cloud-config/kubernetes/ingress.yml
```

---

## Monitoring & Performance

### Track Video Rendering

```bash
# Check running jobs
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/projects/{project_id}/jobs

# View job status
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/jobs/{job_id}
```

### Performance Tuning

1. **Increase Worker Concurrency**:
   - Modify `docker-compose.yml` worker concurrency
   - Or scale horizontally: `docker-compose up -d --scale worker_video=5`

2. **Enable GPU Acceleration** (A100/V100):
   - Update `Dockerfile` to use NVIDIA CUDA base image
   - Configure MoviePy for GPU rendering
   - Estimated 3-5x speedup

3. **Cache Video Segments**:
   - Implement Redis caching for scene clips
   - Reduce re-rendering on project updates

---

## Troubleshooting

### Videos Failing to Render

```bash
# Check worker logs
docker-compose logs worker_video

# Check disk space
df -h

# Restart workers
docker-compose restart worker_video
```

### API Errors

```bash
# Check backend logs
docker-compose logs backend

# Verify database connection
docker-compose exec backend python -c "from app.models import User; print('DB OK')"
```

### Out of Memory (OOM)

```bash
# Increase container memory in docker-compose.yml
services:
  backend:
    mem_limit: 4g
    memswap_limit: 4g
```

---

## Cost Estimation (AWS)

**Monthly costs for small-to-medium deployment:**

| Component | Instance Type | Monthly Cost |
|-----------|---------------|-------------|
| EC2 (main) | t3.xlarge | $150 |
| RDS PostgreSQL | db.t3.large | $180 |
| ElastiCache Redis | cache.t3.medium | $50 |
| S3 Storage (10TB) | - | $230 |
| Data Transfer (5TB out) | - | $500 |
| **TOTAL** | | **~$1,110/month** |

**Cost optimization:**
- Use reserved instances (40% savings)
- Compress videos (reduce S3 cost)
- Auto-scale workers based on demand
- Use spot instances for workers (70% savings)

---

## Support

- **Docs**: https://github.com/yourusername/devotionalai-platform/wiki
- **Issues**: https://github.com/yourusername/devotionalai-platform/issues
- **Email**: support@devotionalai.example.com
- **Discord**: [Community server link]

Happy deploying! 🚀
