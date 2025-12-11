# Faibric Current Architecture (V5)

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    FAIBRIC PLATFORM                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│   ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐       │
│   │   FRONTEND      │         │    BACKEND      │         │    CELERY       │       │
│   │   (React/Vite)  │◄───────►│   (Django)      │◄───────►│   (Workers)     │       │
│   │   Port: 5173    │   API   │   Port: 8000    │  Tasks  │                 │       │
│   └─────────────────┘         └─────────────────┘         └─────────────────┘       │
│           │                           │                           │                 │
│           │                           │                           │                 │
│           ▼                           ▼                           ▼                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐       │
│   │                              TRAEFIK                                     │       │
│   │                         (Reverse Proxy)                                  │       │
│   │   Routes: *.localhost → Docker containers                                │       │
│   └─────────────────────────────────────────────────────────────────────────┘       │
│                                       │                                             │
│                                       ▼                                             │
│   ┌─────────────────────────────────────────────────────────────────────────┐       │
│   │                         DEPLOYED APPS                                    │       │
│   │   batman1-livestocks-133.localhost                                       │       │
│   │   batman1-cafemenu-130.localhost                                         │       │
│   │   batman1-telecasterpickups-128.localhost                                │       │
│   │   ... (Docker containers)                                                │       │
│   └─────────────────────────────────────────────────────────────────────────┘       │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## AI Generation Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              AI GENERATION FLOW                                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│   USER PROMPT                                                                        │
│   "Create a stocks dashboard for AAPL, GOOGL..."                                    │
│        │                                                                             │
│        ▼                                                                             │
│   ┌─────────────┐    OpenAI API    ┌─────────────┐                                  │
│   │  STEP 1:    │ ───────────────► │   GPT-4o    │                                  │
│   │  ANALYZE    │ ◄─────────────── │   (345 tok) │                                  │
│   └─────────────┘                  └─────────────┘                                  │
│        │                                                                             │
│        │  Determines: app_type=dashboard, services=[yahoo_finance]                  │
│        ▼                                                                             │
│   ┌─────────────┐    OpenAI API    ┌─────────────┐                                  │
│   │  STEP 2:    │ ───────────────► │   GPT-4o    │                                  │
│   │  GENERATE   │ ◄─────────────── │  (3125 tok) │                                  │
│   └─────────────┘                  └─────────────┘                                  │
│        │                                                                             │
│        │  Generates: Complete React component with styles                           │
│        ▼                                                                             │
│   ┌─────────────┐                                                                   │
│   │  STEP 3:    │  - Ensure imports present                                         │
│   │  VALIDATE   │  - Ensure export default present                                  │
│   └─────────────┘                                                                   │
│        │                                                                             │
│        ▼                                                                             │
│   ┌─────────────┐                                                                   │
│   │  STEP 4:    │  - Build Docker image with React app                              │
│   │  DEPLOY     │  - Start container with Traefik labels                            │
│   └─────────────┘  - App available at subdomain.localhost                           │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Content Classification Rules

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           CONTENT TYPE ROUTING                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│   ┌─────────────────────┐                                                           │
│   │  STATIC CONTENT     │  Products, menus, recipes, info pages                     │
│   │                     │  ────────────────────────────────────►  HARDCODE IN JS    │
│   │  Examples:          │                                                           │
│   │  - Coffee menu      │  const drinks = [                                         │
│   │  - Product catalog  │    { name: 'Latte', price: 4.50 },                        │
│   │  - Company info     │    { name: 'Mocha', price: 5.00 }                         │
│   └─────────────────────┘  ];                                                       │
│                                                                                      │
│   ┌─────────────────────┐                                                           │
│   │  USER CONTENT       │  Posts, todos, comments, form data                        │
│   │                     │  ────────────────────────────────────►  DATABASE API      │
│   │  Examples:          │                                                           │
│   │  - Todo list        │  fetch('http://localhost:8000/api/v1/db/APP_ID/todos/')   │
│   │  - Blog posts       │                                                           │
│   │  - User comments    │                                                           │
│   └─────────────────────┘                                                           │
│                                                                                      │
│   ┌─────────────────────┐                                                           │
│   │  REAL-TIME DATA     │  Stocks, crypto, weather, live feeds                      │
│   │                     │  ────────────────────────────────────►  GATEWAY API       │
│   │  Examples:          │                                                           │
│   │  - Stock prices     │  fetch('http://localhost:8000/api/gateway/', {            │
│   │  - Crypto rates     │    method: 'POST',                                        │
│   │  - Weather data     │    body: JSON.stringify({ service: 'yahoo_finance' })     │
│   └─────────────────────┘  })                                                       │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Backend Services

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND SERVICES                                        │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│   /api/gateway/                    Universal API Proxy                              │
│   ├── yahoo_finance               └── Proxies external APIs                         │
│   ├── coingecko                   └── Handles CORS                                  │
│   ├── openweather                 └── Caches responses                              │
│   └── investment                  └── Manages API keys                              │
│                                                                                      │
│   /api/v1/db/{app_id}/            Platform Database                                 │
│   ├── GET    /{collection}/       └── List documents                                │
│   ├── POST   /{collection}/       └── Create document                               │
│   ├── PUT    /{collection}/{id}/  └── Update document                               │
│   └── DELETE /{collection}/{id}/  └── Delete document                               │
│                                                                                      │
│   /api/projects/                   Project Management                                │
│   ├── POST   /                    └── Create project (triggers AI generation)       │
│   ├── GET    /{id}/               └── Get project details                           │
│   ├── POST   /{id}/quick_update/  └── Modify with AI                                │
│   └── GET    /{id}/progress/      └── Get build progress                            │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Docker Containers

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              DOCKER COMPOSE SERVICES                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│   faibric_frontend     │  React dev server (Vite)           │  Port 5173           │
│   faibric_backend      │  Django REST API                   │  Port 8000           │
│   faibric_celery       │  Async task workers                │  Internal            │
│   faibric_postgres     │  PostgreSQL database               │  Port 5432           │
│   faibric_redis        │  Cache + Celery broker             │  Port 6379           │
│   faibric_traefik      │  Reverse proxy                     │  Port 80             │
│                                                                                      │
│   + Dynamic containers per deployed app:                                            │
│   app-batman1-livestocks-133                                                        │
│   app-batman1-cafemenu-130                                                          │
│   ...                                                                               │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 18 + TypeScript + Vite + MUI |
| Backend | Django 4.2 + Django REST Framework |
| AI | OpenAI GPT-4o |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Task Queue | Celery |
| Proxy | Traefik 2.10 |
| Containers | Docker + Docker Compose |

## Token Usage (Per App)

| Step | Tokens |
|------|--------|
| Analysis | ~300-500 |
| Generation | ~2,000-4,000 |
| Modification | ~3,000-5,000 |
| **Total per app** | **~3,000-5,000** |

## URLs

- **Dashboard**: http://localhost:5173
- **API**: http://localhost:8000/api/
- **Deployed Apps**: http://{username}-{appname}-{id}.localhost

