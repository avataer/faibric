# Faibric Platform Architecture

## Overview

Faibric is an AI-powered website builder that generates, deploys, and manages React websites from natural language prompts. The platform uses Claude AI for code generation and Render.com for deployment.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FAIBRIC PLATFORM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │   Frontend   │────▶│   Backend    │────▶│   AI Engine  │                │
│  │  React/Vite  │     │   Django     │     │   Anthropic  │                │
│  │  Port: 5173  │     │  Port: 8000  │     │   Claude AI  │                │
│  └──────────────┘     └──────────────┘     └──────────────┘                │
│         │                    │                    │                         │
│         │                    ▼                    │                         │
│         │             ┌──────────────┐            │                         │
│         │             │   Database   │            │                         │
│         │             │   SQLite/    │            │                         │
│         │             │  PostgreSQL  │            │                         │
│         │             └──────────────┘            │                         │
│         │                    │                    │                         │
│         │                    ▼                    │                         │
│         │             ┌──────────────┐     ┌──────────────┐                │
│         │             │    Redis     │     │   GitHub     │                │
│         │             │   (Cache)    │     │   API        │                │
│         │             └──────────────┘     └──────────────┘                │
│         │                                        │                         │
│         │                                        ▼                         │
│         │                                 ┌──────────────┐                 │
│         └────────────────────────────────▶│  Render.com  │                 │
│                (Live preview)             │  Deployment  │                 │
│                                           └──────────────┘                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
/Users/abram/Code/Faibric/
├── backend/                    # Django Backend
│   ├── apps/
│   │   ├── ai_engine/         # AI code generation
│   │   │   └── v2/
│   │   │       ├── generator.py    # Main AI generator
│   │   │       └── prompts.py      # AI prompt templates
│   │   ├── analytics/         # Admin dashboard & analytics
│   │   │   ├── admin_dashboard.py  # Dashboard HTML generation
│   │   │   ├── services.py         # Analytics services
│   │   │   ├── models.py           # Core analytics models
│   │   │   ├── models_dashboard.py # Extended dashboard models
│   │   │   └── cost_tracker.py     # Cost tracking
│   │   ├── code_library/      # Reusable component library
│   │   │   ├── models.py           # Library models
│   │   │   └── search.py           # Semantic search
│   │   ├── deployment/        # Render deployment
│   │   │   └── render_deployer.py  # Render API integration
│   │   ├── onboarding/        # User onboarding flow
│   │   │   ├── models.py           # Session, events, inputs
│   │   │   ├── services.py         # Onboarding logic
│   │   │   ├── views.py            # API views
│   │   │   └── build_service.py    # Build orchestration
│   │   ├── projects/          # Project management
│   │   ├── tenants/           # Multi-tenancy
│   │   ├── users/             # User management
│   │   └── templates/         # Project templates
│   ├── faibric_backend/
│   │   ├── settings.py        # Django settings
│   │   └── urls.py            # URL routing
│   └── manage.py
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── BuildingStudio.tsx   # Split-screen builder
│   │   │   └── ProgressivePreview.tsx # Animated preview
│   │   ├── pages/
│   │   │   └── LandingFlow.tsx      # Main landing page
│   │   └── lib/
│   │       └── api.ts               # API client
│   └── package.json
├── constraints/               # AI generation constraints
│   ├── apis.md
│   ├── database.md
│   ├── react.md
│   ├── security.md
│   └── styling.md
├── .env                       # Production environment
├── .env.local                 # Local development
├── docker-compose.yml         # Docker configuration
├── start-dev.sh              # Local development script
└── monitor_services.py       # Health monitoring
```

---

## Core Components

### 1. Frontend (React/Vite)

**Location:** `/frontend/`

**Key Components:**
- `BuildingStudio.tsx` - Split-screen builder with chat on left, preview on right
- `ProgressivePreview.tsx` - Animated build progress visualization
- `LandingFlow.tsx` - Main user journey from prompt to deployment

**Features:**
- Real-time progress updates via polling
- Live code preview with Sandpack
- Session persistence in localStorage
- Contextual placeholder content during build

### 2. Backend (Django REST Framework)

**Location:** `/backend/`

**Apps:**
| App | Purpose |
|-----|---------|
| `ai_engine` | Claude AI integration, code generation |
| `analytics` | Admin dashboard, cost tracking, health scores |
| `code_library` | Reusable component storage, semantic search |
| `deployment` | Render.com deployment automation |
| `onboarding` | User journey, session management |
| `projects` | Project data, generated code storage |
| `tenants` | Multi-tenant architecture |
| `users` | User authentication |
| `templates` | Project templates |

### 3. AI Engine

**Location:** `/backend/apps/ai_engine/v2/`

**Features:**
- Smart model selection (Opus for new code, Haiku for reuse)
- Streaming response for real-time updates
- Code library integration
- JSON response parsing with fallbacks
- JSX validation and fixing

**Models Used:**
- `claude-sonnet-4-20250514` (Opus 4.5) - New code generation
- `claude-3-5-haiku-20241022` (Haiku 3.5) - Classification, summaries, reuse

### 4. Deployment (Render)

**Location:** `/backend/apps/deployment/`

**Flow:**
1. Create GitHub branch with generated code
2. Create Render static site service
3. Configure build commands
4. Return deployment URL

**Requirements:**
- `GITHUB_TOKEN` - GitHub API access
- `GITHUB_APPS_REPO` - Repository for deployed apps
- `RENDER_API_KEY` - Render API access
- `RENDER_OWNER_ID` - Render account owner

### 5. Analytics Dashboard

**Location:** `/backend/apps/analytics/`

**Features:**
- Real-time activity feed
- Customer health scores
- Conversion funnel visualization
- Cohort retention analysis
- Cost tracking and forecasting
- Alert system with email notifications
- AI-generated daily reports

---

## Data Flow

### User Build Flow

```
1. User submits prompt
   └── Frontend: LandingFlow.tsx
       └── POST /api/onboarding/initial-request/
           └── Creates LandingSession

2. User provides email
   └── POST /api/onboarding/provide-email/
       └── Sends magic link email

3. User verifies email
   └── GET /api/onboarding/verify/{token}/
       └── Marks session verified

4. Build triggered
   └── POST /api/onboarding/trigger-build/
       └── Background thread: BuildService.build_from_session()
           ├── Create Project
           ├── AIGeneratorV2.generate_app()
           │   ├── Check code library for reuse
           │   ├── Select model (Opus/Haiku)
           │   └── Stream generated code
           └── RenderDeployer.deploy_react_app()
               ├── Create GitHub branch
               └── Create Render service

5. User sees live site
   └── Frontend polls /api/onboarding/session-status/
       └── Returns deployment_url when ready
```

### Modification Flow

```
1. User sends chat message
   └── POST /api/onboarding/modify/
       ├── Detect: New project or modification?
       ├── If modification:
       │   └── AIGeneratorV2.modify_app()
       │       └── Apply targeted change
       └── If new project:
           └── Full rebuild
```

---

## Database Schema

### Key Models

**LandingSession** (onboarding)
- Tracks user from landing to deployment
- Status: request_submitted → email_provided → verified → building → deployed

**SessionEvent** (onboarding)
- Every event in a user's journey
- Types: request_submitted, build_started, deployed, error, etc.

**Project** (projects)
- Generated code storage
- Deployment URL
- User/tenant association

**LibraryItem** (code_library)
- Reusable code components
- Semantic embeddings for search
- Usage count, quality score

**APIUsageLog** (analytics)
- Every AI API call
- Model, tokens, cost
- Per-session tracking

**CustomerHealthScore** (analytics)
- Health 0-100
- Churn prediction
- Component scores

---

## Environment Variables

### Required

```bash
# AI
ANTHROPIC_API_KEY=sk-ant-...

# GitHub (for deployment)
GITHUB_TOKEN=ghp_...
GITHUB_APPS_REPO=username/apps-repo

# Render (for deployment)
RENDER_API_KEY=rnd_...
RENDER_OWNER_ID=usr-...

# Django
SECRET_KEY=your-secret-key
DEBUG=0

# Email
SENDGRID_API_KEY=SG....
DEFAULT_FROM_EMAIL=noreply@faibric.com
```

### Local Development

```bash
# In .env.local
USE_SQLITE=1
DEBUG=1
```

---

## API Endpoints

### Onboarding

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/onboarding/initial-request/` | Submit initial prompt |
| POST | `/api/onboarding/provide-email/` | Provide email |
| GET | `/api/onboarding/verify/{token}/` | Verify email |
| POST | `/api/onboarding/trigger-build/` | Start build |
| GET | `/api/onboarding/session-status/` | Poll for status |
| POST | `/api/onboarding/modify/` | Modify existing site |
| POST | `/api/onboarding/stop/` | Stop build |

### Analytics Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/dashboard/` | Main dashboard |
| GET | `/api/analytics/dashboard/users/` | All users |
| GET | `/api/analytics/dashboard/user/{token}` | User detail |
| GET | `/api/analytics/dashboard/health/` | Health scores |
| GET | `/api/analytics/dashboard/funnel/` | Funnel viz |
| GET | `/api/analytics/dashboard/cohorts/` | Cohort analysis |
| GET | `/api/analytics/dashboard/costs/` | Cost analysis |
| POST | `/api/analytics/dashboard/run-daily/` | Run daily tasks |

---

## Deployment

### Local Development

```bash
# Start backend
cd backend
python manage.py runserver 0.0.0.0:8000

# Start frontend
cd frontend
npm run dev

# Or use the script
./start-dev.sh
```

### Production (Render)

1. Backend deploys as web service
2. Uses PostgreSQL database
3. Redis for caching
4. Environment variables set in Render dashboard

---

## Security Considerations

1. **No admin authentication** - Dashboard is currently public
2. **API keys in environment** - Never commit to git
3. **CORS configured** - Allows frontend origin
4. **CSRF disabled for API** - Uses token auth instead
5. **Rate limiting** - Not yet implemented

---

## Performance Optimizations

1. **Smart model selection** - Uses cheap model when possible
2. **Code library reuse** - Avoids regenerating similar code
3. **Background threading** - Builds don't block requests
4. **Redis caching** - Session state cached
5. **Lazy loading** - Dashboard pages load on demand

---

## Monitoring

### Health Check
```bash
curl http://localhost:8000/api/health/
```

### Monitor Script
```bash
python monitor_services.py
```
- Checks backend and frontend health
- Sends email alerts on failure
- Auto-restart capability

---

## Future Improvements

1. Add authentication to admin dashboard
2. Implement rate limiting
3. Add A/B testing for AI prompts
4. Webhook integrations (Slack, etc.)
5. User feedback collection
6. More granular permissions
