# 🚀 Faibric - AI-Powered No-Code App Builder

# 🚀 Faibric - AI-Powered No-Code App Builder

**Status: ✅ All Critical Issues Fixed** - [See Fix Guide](./FIX_GUIDE.md)

## Quick Start

### 1. Start Docker Desktop
Make sure Docker Desktop is running before proceeding.

### 2. Quick Start Script
```bash
cd /Users/abram/Code/Faibric
./start-faibric.sh
```

This will:
- ✅ Check Docker is running
- ✅ Verify environment configuration
- ✅ Build and start all services
- ✅ Wait for services to be ready
- ✅ Show service status

### 3. Create User & Access
```bash
# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Open the app
open http://localhost:5173
```

## What It Does

Faibric generates **fully working web applications** from text descriptions:

1. **Describe your app** - "Website for guitar pickups with specs"
2. **AI generates** - Database models, API endpoints, frontend
3. **Deploy** - Live app at `username-project.localhost`

## Features

- ✅ AI-powered app generation (OpenAI GPT-4)
- ✅ Real-time progress tracking
- ✅ Live deployment with Docker + Traefik
- ✅ Sample data generation
- ✅ Beautiful, responsive UI
- ✅ RESTful APIs
- ✅ User authentication & management

## Architecture

```
Frontend (React/TypeScript) → Backend (Django/DRF) → Celery (AI Tasks)
                                    ↓
                              PostgreSQL (Data)
                                    ↓
                           Docker (Deployments) → Traefik (Routing)
```

## Development

### View Logs
```bash
./logs.sh          # Filtered logs
./monitor.sh       # Full dashboard
docker-compose logs -f
```

### Reset Database
```bash
docker-compose down -v
docker-compose up -d
./setup-db.sh
```

### Rebuild
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

## Documentation

- **Project Storage**: `PROJECT-STORAGE-EXPLAINED.md`
- **Full Working Apps**: `FULLY-WORKING-APPS.md`
- **Deployment Setup**: `REAL-DEPLOYMENT-SETUP.md`
- **Logs Guide**: `LOGS-GUIDE.md`

## Troubleshooting

**Having issues?** See the comprehensive [Fix Guide](./FIX_GUIDE.md)

Common fixes:
- **Docker not running**: Start Docker Desktop
- **NaN errors**: Fixed in latest version, clear browser cache
- **API errors**: Check `.env` has valid `OPENAI_API_KEY`
- **Won't start**: Run `./check-system.sh` for diagnostics

### Quick Health Check
```bash
./check-system.sh
```

## License

MIT
