# Docker Deployment Guide - Business Analyzer

Complete guide for containerizing and deploying the Business Analyzer application using Docker.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Docker Deployment](#local-docker-deployment)
3. [Docker Compose Deployment](#docker-compose-deployment)
4. [Push to GitHub](#push-to-github)
5. [Cloud Deployment Options](#cloud-deployment-options)
6. [Production Considerations](#production-considerations)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Install Docker

**Windows:**
1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
2. Run installer
3. Restart computer
4. Verify: `docker --version`

**macOS:**
```bash
# Using Homebrew
brew install --cask docker

# Or download from docker.com
# Verify
docker --version
```

**Linux (Ubuntu/Debian):**
```bash
# Update package index
sudo apt-get update

# Install Docker
sudo apt-get install docker.io docker-compose

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (optional, to run without sudo)
sudo usermod -aG docker $USER

# Verify
docker --version
```

---

## Local Docker Deployment

### Step 1: Build Docker Image

Navigate to your project directory and build the image:

```bash
cd /path/to/BusinessAnalyzer

# Build the image
docker build -t business-analyzer:latest .
```

**Build with custom tag:**
```bash
docker build -t business-analyzer:v1.0 .
```

**Build output should show:**
```
[+] Building 45.2s (12/12) FINISHED
 => [internal] load build definition from Dockerfile
 => => transferring dockerfile: 789B
 => [internal] load .dockerignore
 => ...
 => exporting to image
 => => naming to docker.io/library/business-analyzer:latest
```

### Step 2: Run Docker Container

**Basic run:**
```bash
docker run -p 8501:8501 business-analyzer:latest
```

**Run with volume for database persistence:**
```bash
docker run -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  business-analyzer:latest
```

**Run with environment variables:**
```bash
docker run -p 8501:8501 \
  -e JWT_SECRET_KEY="your-secure-secret-key" \
  -v $(pwd)/data:/app/data \
  business-analyzer:latest
```

**Run in detached mode (background):**
```bash
docker run -d \
  --name business-analyzer-app \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  business-analyzer:latest
```

### Step 3: Access Application

Open your browser and navigate to:
```
http://localhost:8501
```

### Step 4: Manage Container

**View running containers:**
```bash
docker ps
```

**View all containers (including stopped):**
```bash
docker ps -a
```

**Stop container:**
```bash
docker stop business-analyzer-app
```

**Start stopped container:**
```bash
docker start business-analyzer-app
```

**View logs:**
```bash
docker logs business-analyzer-app

# Follow logs in real-time
docker logs -f business-analyzer-app
```

**Remove container:**
```bash
docker rm business-analyzer-app

# Force remove running container
docker rm -f business-analyzer-app
```

**Remove image:**
```bash
docker rmi business-analyzer:latest
```

---

## Docker Compose Deployment

Docker Compose simplifies multi-container applications and configuration management.

### Step 1: Create Environment File

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and set your values:
```bash
nano .env
# or
code .env
```

**Important:** Change the JWT_SECRET_KEY to a secure random string!

### Step 2: Start with Docker Compose

**Build and start:**
```bash
docker-compose up --build
```

**Start in detached mode:**
```bash
docker-compose up -d
```

**View logs:**
```bash
docker-compose logs -f
```

### Step 3: Manage with Docker Compose

**Stop services:**
```bash
docker-compose down
```

**Stop and remove volumes:**
```bash
docker-compose down -v
```

**Restart services:**
```bash
docker-compose restart
```

**View status:**
```bash
docker-compose ps
```

**Execute commands in container:**
```bash
docker-compose exec business-analyzer bash
```

---

## Push to GitHub

### Step 1: Initialize Git Repository

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Add Docker deployment configuration"
```

### Step 2: Create GitHub Repository

1. Go to [GitHub](https://github.com)
2. Click "New Repository"
3. Name it: `business-analyzer`
4. Don't initialize with README (you already have one)
5. Click "Create Repository"

### Step 3: Push to GitHub

```bash
# Add remote
git remote add origin https://github.com/YOUR_USERNAME/business-analyzer.git

# Set main branch
git branch -M main

# Push
git push -u origin main
```

**For subsequent pushes:**
```bash
git add .
git commit -m "Your commit message"
git push
```

---

## Cloud Deployment Options

### Option 1: Railway (Recommended - Easy & Free Tier)

**Steps:**

1. **Sign Up**
   - Go to [Railway.app](https://railway.app)
   - Sign up with GitHub

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `business-analyzer` repository

3. **Configure**
   - Railway auto-detects Dockerfile
   - Add environment variables:
     - `JWT_SECRET_KEY`: Your secure key
   - Click "Deploy"

4. **Access Your App**
   - Railway provides a URL like: `https://business-analyzer-production.up.railway.app`
   - Click "Generate Domain" if not automatic

**Railway Configuration File (optional):**

Create `railway.json`:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Pros:**
- Free tier available
- Automatic HTTPS
- Easy GitHub integration
- Automatic deployments on push

**Cons:**
- Free tier has usage limits
- Databases not persistent on free tier (use volumes)

---

### Option 2: Render

**Steps:**

1. **Sign Up**
   - Go to [Render.com](https://render.com)
   - Sign up with GitHub

2. **Create Web Service**
   - Click "New +"
   - Select "Web Service"
   - Connect your GitHub repository

3. **Configure**
   - Name: `business-analyzer`
   - Environment: `Docker`
   - Region: Choose closest to you
   - Branch: `main`
   - Docker Command: (leave default, uses Dockerfile CMD)

4. **Environment Variables**
   - Add `JWT_SECRET_KEY`
   - Add any other variables from `.env.example`

5. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)

6. **Access**
   - URL: `https://business-analyzer.onrender.com`

**Render Configuration File (optional):**

Create `render.yaml`:
```yaml
services:
  - type: web
    name: business-analyzer
    env: docker
    plan: free
    dockerfilePath: ./Dockerfile
    envVars:
      - key: JWT_SECRET_KEY
        generateValue: true
      - key: STREAMLIT_SERVER_PORT
        value: 8501
    healthCheckPath: /_stcore/health
```

**Pros:**
- Free tier available
- Automatic HTTPS
- Good documentation
- Persistent storage options

**Cons:**
- Free tier spins down after inactivity
- Cold start delay (30-60 seconds)

---

### Option 3: Hugging Face Spaces (Best for ML Apps)

**Steps:**

1. **Create Account**
   - Go to [Hugging Face](https://huggingface.co)
   - Sign up

2. **Create Space**
   - Click "New Space"
   - Name: `business-analyzer`
   - SDK: Select "Docker"
   - Visibility: Public or Private

3. **Upload Files**
   - Upload all project files
   - Ensure Dockerfile is in root

4. **Configure**
   - Hugging Face automatically builds from Dockerfile
   - Add secrets in Settings → Repository secrets

5. **Access**
   - URL: `https://huggingface.co/spaces/YOUR_USERNAME/business-analyzer`

**Hugging Face Dockerfile (modify if needed):**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

ENV STREAMLIT_SERVER_PORT=7860
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=7860", "--server.address=0.0.0.0"]
```

**Note:** Hugging Face uses port 7860 by default.

**Pros:**
- Great for ML/AI applications
- Free hosting
- Good community
- Persistent storage

**Cons:**
- Slower than other options
- Limited to ML/data science apps

---

### Option 4: AWS (Production-Grade)

**Using AWS Elastic Container Service (ECS):**

1. **Install AWS CLI**
```bash
pip install awscli
aws configure
```

2. **Create ECR Repository**
```bash
aws ecr create-repository --repository-name business-analyzer
```

3. **Build and Push Image**
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag image
docker tag business-analyzer:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/business-analyzer:latest

# Push
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/business-analyzer:latest
```

4. **Create ECS Task Definition**
5. **Create ECS Service**
6. **Configure Load Balancer**

**Pros:**
- Production-grade
- Highly scalable
- Full control
- Many AWS integrations

**Cons:**
- More complex setup
- Costs money (no free tier for ECS)
- Requires AWS knowledge

---

### Option 5: DigitalOcean App Platform

**Steps:**

1. **Create Account** at [DigitalOcean](https://www.digitalocean.com)
2. **Create App** → Deploy from GitHub
3. **Select Repository**
4. **Configure**:
   - Detected as Docker
   - Set environment variables
   - Choose plan (starts at $5/month)
5. **Deploy**

**Pros:**
- Simple interface
- Good documentation
- Predictable pricing
- Managed databases available

**Cons:**
- No free tier
- Minimum $5/month

---

## Production Considerations

### 1. Database Persistence

**Problem:** Docker containers are ephemeral. Data is lost when container is removed.

**Solution:** Use volumes

```bash
# Create named volume
docker volume create business-analyzer-data

# Run with volume
docker run -p 8501:8501 \
  -v business-analyzer-data:/app/data \
  business-analyzer:latest
```

**For production:** Consider using external database (PostgreSQL, MySQL)

### 2. Security

**Change JWT Secret:**
```bash
# Generate secure random key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Set as environment variable
export JWT_SECRET_KEY="your-generated-key"
```

**Use HTTPS:**
- Railway, Render, Hugging Face provide automatic HTTPS
- For custom deployment, use Nginx with Let's Encrypt

**Environment Variables:**
- Never commit `.env` file to Git
- Use platform-specific secrets management
- Rotate secrets regularly

### 3. Monitoring & Logging

**View logs:**
```bash
docker logs -f business-analyzer-app
```

**Health checks:**
```bash
curl http://localhost:8501/_stcore/health
```

**Resource monitoring:**
```bash
docker stats business-analyzer-app
```

### 4. Backup Strategy

**Backup databases:**
```bash
# Create backup directory
mkdir -p backups

# Copy database from container
docker cp business-analyzer-app:/app/USER.db ./backups/USER_$(date +%Y%m%d).db
docker cp business-analyzer-app:/app/BUSINESS.db ./backups/BUSINESS_$(date +%Y%m%d).db
```

**Automated backup script:**
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
docker cp business-analyzer-app:/app/USER.db ./backups/USER_$DATE.db
docker cp business-analyzer-app:/app/BUSINESS.db ./backups/BUSINESS_$DATE.db
echo "Backup completed: $DATE"
```

### 5. Scaling

**Horizontal scaling:**
- Use load balancer (Nginx, HAProxy)
- Multiple container instances
- Shared database on network storage

**Vertical scaling:**
- Increase container resources
```bash
docker run --cpus="2" --memory="2g" -p 8501:8501 business-analyzer:latest
```

---

## Troubleshooting

### Issue: Container exits immediately

**Check logs:**
```bash
docker logs business-analyzer-app
```

**Common causes:**
- Missing dependencies in requirements.txt
- Syntax errors in Python code
- Port already in use

### Issue: Can't access app at localhost:8501

**Solutions:**
1. Check if container is running: `docker ps`
2. Check port mapping: `docker port business-analyzer-app`
3. Try: `http://127.0.0.1:8501`
4. Check firewall settings

### Issue: Database not persisting

**Solution:** Use volumes
```bash
docker run -v $(pwd)/data:/app/data -p 8501:8501 business-analyzer:latest
```

### Issue: Build fails with "no space left on device"

**Solution:** Clean up Docker
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove everything unused
docker system prune -a
```

### Issue: Slow build times

**Solutions:**
1. Use `.dockerignore` to exclude unnecessary files
2. Order Dockerfile commands efficiently (requirements.txt before code)
3. Use Docker build cache
4. Use smaller base image (python:3.10-slim instead of python:3.10)

### Issue: Prophet installation fails in Docker

**Solution:** Add build dependencies to Dockerfile
```dockerfile
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*
```

Or remove Prophet from requirements.txt (app will use linear regression fallback)

---

## Quick Reference Commands

```bash
# Build
docker build -t business-analyzer:latest .

# Run
docker run -d --name business-analyzer-app -p 8501:8501 -v $(pwd)/data:/app/data business-analyzer:latest

# Stop
docker stop business-analyzer-app

# Start
docker start business-analyzer-app

# Logs
docker logs -f business-analyzer-app

# Remove
docker rm -f business-analyzer-app

# Docker Compose
docker-compose up -d
docker-compose down
docker-compose logs -f

# Clean up
docker system prune -a
```

---

## Next Steps

1. Test locally with Docker
2. Push to GitHub
3. Choose cloud platform
4. Deploy
5. Configure custom domain (optional)
6. Set up monitoring
7. Configure backups

---

**Deployment Status:** Ready for Production  
**Last Updated:** 2024  
**Maintained By:** Development Team
