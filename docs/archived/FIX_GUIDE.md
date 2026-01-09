# 🔧 Faibric - Complete Fix Guide

**All critical issues have been fixed!** This guide will help you get everything running.

## ✅ What Was Fixed

### 1. **Backend Import Error** ✅
- **Issue**: Missing `serializers` import in `views.py`
- **Fix**: Added `serializers` to REST framework imports
- **Location**: `backend/apps/projects/views.py`

### 2. **Frontend NaN Bug** ✅
- **Issue**: Project ID was `NaN` causing `/api/projects/NaN/progress/` errors
- **Fix**: Added validation and error handling in CreateProduct navigation
- **Location**: `frontend/src/pages/CreateProduct.tsx`

### 3. **Missing Error States** ✅
- **Issue**: No user feedback when things went wrong
- **Fix**: Added error states and user-friendly error messages in LiveCreation
- **Location**: `frontend/src/pages/LiveCreation.tsx`

### 4. **Environment Configuration** ✅
- **Issue**: Missing .env file template
- **Fix**: Created `.env.example` with all required variables
- **Location**: Root directory

### 5. **Startup Checks** ✅
- **Issue**: No way to verify system requirements
- **Fix**: Created `check-system.sh` script
- **Location**: Root directory

---

## 🚀 Quick Start (3 Steps)

### Step 1: Start Docker
```bash
# Make sure Docker Desktop is running
# You should see the Docker icon in your menu bar
```

### Step 2: Run System Check
```bash
cd /Users/abram/Code/Faibric
./check-system.sh
```

### Step 3: Configure & Start
```bash
# Edit .env and add your OpenAI API key
nano .env
# Set: OPENAI_API_KEY=sk-your-actual-key-here

# Start everything
docker-compose down
docker-compose up -d --build

# Wait 30 seconds for services to initialize
sleep 30

# Create your first user
docker-compose exec backend python manage.py createsuperuser
```

### Step 4: Access the App
```bash
open http://localhost:5173
```

---

## 🔍 System Requirements

### Required Software
- ✅ **Docker Desktop** (must be running)
- ✅ **Docker Compose** (included with Docker Desktop)
- ✅ **OpenAI API Key** (get from https://platform.openai.com/api-keys)

### Ports Required
- `5173` - Frontend (React/Vite)
- `8000` - Backend (Django)
- `5432` - PostgreSQL
- `6379` - Redis
- `80` - Traefik (reverse proxy)
- `8080` - Traefik Dashboard

---

## 🐛 Troubleshooting

### Docker Not Running
**Error**: `Cannot connect to the Docker daemon`

**Solution**:
```bash
# 1. Open Docker Desktop application
# 2. Wait for it to fully start (green icon)
# 3. Verify it's running:
docker ps
```

### Frontend Won't Load
**Error**: Browser shows "Connection refused" at localhost:5173

**Solution**:
```bash
# Check if frontend is ready
docker-compose logs frontend | grep "ready in"

# If not ready, wait 30 more seconds and check again
# If still not ready after 2 minutes, rebuild:
docker-compose down
docker-compose build frontend
docker-compose up -d
```

### Backend API Errors
**Error**: API returns 500 errors

**Solution**:
```bash
# Check backend logs
docker-compose logs backend | tail -50

# Common issues:
# 1. OpenAI key not set → Edit .env
# 2. Database not ready → Wait 30 seconds
# 3. Migrations not run → Run:
docker-compose exec backend python manage.py migrate
```

### Can't Login / No User
**Error**: "Invalid credentials" or no user exists

**Solution**:
```bash
# Create a superuser
docker-compose exec backend python manage.py createsuperuser

# Follow prompts:
# - Username: admin
# - Email: admin@example.com
# - Password: (choose a secure password)
```

### NaN Project ID Error
**Error**: Console shows `/api/projects/NaN/progress/`

**Solution**: 
✅ **FIXED!** If you still see this:
1. Clear browser cache: `Cmd + Shift + R` (Mac) or `Ctrl + Shift + R` (Windows)
2. Rebuild frontend: `docker-compose build frontend && docker-compose up -d`

### Project Generation Fails
**Error**: Status stays "generating" forever or fails

**Solution**:
```bash
# 1. Check OpenAI API key is set correctly
grep OPENAI_API_KEY .env

# 2. Check Celery worker is running
docker-compose logs celery | tail -50

# 3. Restart celery if needed
docker-compose restart celery

# 4. Check for errors in celery logs
docker-compose logs celery -f
```

### Deployment Fails
**Error**: Project generated but deployment URL doesn't work

**Solution**:
```bash
# 1. Check deployed containers
docker ps | grep app-

# 2. Check deployment logs
docker-compose logs celery | grep -i deploy

# 3. Check Traefik
docker-compose logs traefik | tail -20

# 4. Verify Traefik is running
curl http://localhost:8080/dashboard/
```

---

## 📋 Health Check Commands

### Check All Services
```bash
docker-compose ps
```

Expected output - all services should show "Up":
```
faibric_backend     Up
faibric_celery      Up
faibric_frontend    Up
faibric_postgres    Up
faibric_redis       Up
faibric_traefik     Up
```

### Check Logs (Filtered)
```bash
./logs.sh
```

### Check Logs (Full)
```bash
./monitor.sh
```

### Check Database Connection
```bash
docker-compose exec backend python manage.py dbshell
# If you see postgres prompt, DB is working
# Type \q to exit
```

### Check API is Responding
```bash
curl http://localhost:8000/api/
```

### Check Frontend is Serving
```bash
curl http://localhost:5173
```

---

## 🔄 Common Operations

### Restart Everything
```bash
docker-compose down
docker-compose up -d
```

### Rebuild After Code Changes
```bash
docker-compose down
docker-compose up -d --build
```

### Reset Database (⚠️ Deletes all data)
```bash
docker-compose down -v
docker-compose up -d
sleep 30
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
```

### View Live Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f celery
```

### Clean Docker (⚠️ Nuclear option)
```bash
# Stop and remove everything
docker-compose down -v --remove-orphans

# Remove ALL Docker data (use with caution)
docker system prune -a --volumes
```

---

## 📝 Environment Variables

Required variables in `.env`:

```bash
# REQUIRED - Get from https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-key-here

# Database (defaults should work)
POSTGRES_DB=faibric_db
POSTGRES_USER=faibric_user
POSTGRES_PASSWORD=faibric_password

# Django
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=1

# Redis
REDIS_URL=redis://redis:6379/0

# Deployment
APP_SUBDOMAIN_BASE=localhost
```

---

## 🎯 Testing the Complete Flow

### End-to-End Test
```bash
# 1. Start services
docker-compose up -d

# 2. Wait for readiness
sleep 30

# 3. Create user (if not exists)
docker-compose exec backend python manage.py createsuperuser --noinput \
  --username=testuser --email=test@example.com || true

# 4. Open app
open http://localhost:5173

# 5. Login with your credentials

# 6. Go to /create and enter:
"A simple todo list app with add, delete, and mark complete"

# 7. Watch it build in real-time!
```

---

## 📚 Additional Documentation

- **Quick Start**: `QUICK_START.md`
- **Start Here**: `START_HERE.md`
- **Deployment**: `DEPLOYMENT_INSTRUCTIONS.md`
- **New Flow**: `NEW_FLOW_SUMMARY.md`
- **Main README**: `README.md`

---

## 🆘 Still Having Issues?

### 1. Run the System Check
```bash
./check-system.sh
```

### 2. Check All Services Are Running
```bash
docker-compose ps
```

### 3. Review Logs for Errors
```bash
docker-compose logs --tail=100
```

### 4. Verify Ports Aren't in Use
```bash
# Check if ports are available
lsof -i :5173  # Frontend
lsof -i :8000  # Backend
lsof -i :5432  # Postgres
lsof -i :6379  # Redis
```

### 5. Complete Reset
```bash
# Stop everything
docker-compose down -v

# Rebuild from scratch
docker-compose build --no-cache

# Start fresh
docker-compose up -d

# Wait and check
sleep 30
docker-compose ps
```

---

## ✨ What Should Work Now

✅ Docker startup and health checks
✅ Environment configuration
✅ Backend API with proper error handling
✅ Frontend navigation without NaN errors
✅ Error messages and user feedback
✅ Project creation flow
✅ Real-time progress updates
✅ Live deployment with iframe preview
✅ AI chat messages
✅ Quick updates to deployed apps

---

## 🎉 Success Checklist

- [ ] Docker Desktop is running
- [ ] `./check-system.sh` passes all checks
- [ ] OpenAI API key is configured in `.env`
- [ ] `docker-compose ps` shows 6 services "Up"
- [ ] http://localhost:5173 loads the frontend
- [ ] http://localhost:8000/api/ returns API response
- [ ] You can login with your user
- [ ] `/create` page shows single input field
- [ ] Creating a project navigates to `/create/{id}` (not `/create/NaN`)
- [ ] Progress updates appear in real-time
- [ ] Deployment URL shows in iframe when ready

If all above are checked ✅ - **You're ready to build!** 🚀

---

**Last Updated**: 2024-11-21
**Status**: All critical issues resolved ✅

