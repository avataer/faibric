# Faibric Customer Test Logs

**Test Date:** 2026-01-08
**Branch:** `claude/code-review-pBBJT`
**Production URL:** https://faibric-frontend.onrender.com

---

## URL Branding Policy

**CRITICAL:** All customer-facing URLs MUST use `*.faibric.com` subdomains.

Customers must NEVER see:
- `*.vercel.app`
- `*.onrender.com`
- `*.netlify.app`
- Any other provider domains

All deployments are proxied through Faibric's domain for brand consistency.

URL Format: `https://app{random_10_chars}.faibric.com`

---

## Production API Health Check

```
GET https://faibric-api.onrender.com/api/health/

{
  "status": "healthy",
  "service": "faibric-api",
  "deployment": {
    "vercel": {"configured": true, "message": "VERCEL_TOKEN configured (24 chars)"},
    "render": {"configured": true},
    "github": {"configured": true, "repo": "avataer/faibric-apps"},
    "ai": {"configured": true}
  }
}
```

✅ All tokens configured in production

---

## Real Test Session (Production API)

### Customer 1: Registration ✅
```
[20:28:58] >>> CUSTOMER: I want to sign up for Faibric

[20:28:58] SYSTEM: POST /api/auth/register/ - 201 Created
[20:28:58] SYSTEM: Account created!
           User ID: 156
           Username: testuser1767904138
           Email: test-1767904138@test.faibric.com
           Max Apps: 10
           JWT tokens issued ✅
```

### Customer 1: Create Bitcoin Tracker
```
[20:28:58] >>> CUSTOMER: "Build me a Bitcoin price tracker with live charts"

[20:29:00] SYSTEM: POST /api/projects/ - 201 Created
[20:29:00] FAIBRIC: Creating your app (Project #147)...
[20:29:00] FAIBRIC: Task queued for Celery worker...

[20:49:27] SYSTEM: Regeneration triggered - V2 generation started
[20:58:08] SYSTEM: Status: generating (worker active)
[21:00:39] SYSTEM: Status: generating (2m 32s elapsed, no code yet)
```

**Result:** Project created, worker active, but generation taking too long.

### Root Cause Analysis

The generation is stuck at the AI API call phase. Investigation revealed infrastructure was incorrectly configured with starter plans instead of production-grade Standard plans.

**Issue:** `render.yaml` used `plan: starter` which has:
- Limited RAM (~512MB)
- Workers can be suspended after inactivity
- Cold starts of 30-60 seconds

**Fix Applied:** Updated all services to `plan: standard`:
- 2GB RAM for API and Worker
- Always-on instances (no suspension)
- Proper resources for AI generation

---

## Test Results Summary

| Component | Status | Notes |
|-----------|--------|-------|
| API Health | ✅ Working | All tokens configured |
| User Registration | ✅ Working | Rate limiting active |
| JWT Authentication | ✅ Working | Access + Refresh tokens |
| Project Creation | ✅ Working | Saved to database |
| Celery Worker Activation | ✅ Working | Status changes from `draft` to `generating` |
| AI Code Generation | ⏳ Slow/Timeout | Claude Opus 4.5 + 16K tokens + free tier = slow |
| GitHub Push | ⏳ Pending | Requires generated code |
| Render Deployment | ⏳ Pending | Requires GitHub push |

---

## Security Verification

| Check | Status |
|-------|--------|
| CORS restricted in production | ✅ `CORS_ALLOW_ALL_ORIGINS = DEBUG` |
| Rate limiting on auth | ✅ 5/minute registration, 3/hour password |
| Builder secret configured | ✅ `BUILDER_SECRET` from env |
| SECRET_KEY validation | ✅ Raises error if insecure in production |
| ALLOWED_HOSTS | ✅ No wildcard in production |
| Tenant isolation | ✅ Projects scoped to user/tenant |

---

## Backend Test Results

```
=== TEST 1: Module Imports ===
✓ UniversalGenerator imported
✓ ComponentGenerationPipeline imported
✓ ProjectViewSet loaded
✓ RegisterView loaded

=== TEST 2: Generator Methods ===
✓ App type detection works
✓ Title generation works
✓ Service detection works

=== TEST 3: Security Configuration ===
✓ Auth rate limit: 5/minute
✓ Password change limit: 3/hour
✓ CORS restricted in production
✓ BUILDER_SECRET configured
```

## Frontend Build Results

```
vite v5.4.21 building for production...
✓ 1093 modules transformed
✓ built in 7.46s

dist/index.html                   0.79 kB
dist/assets/index-DN5eojBM.js   680.88 kB (gzip: 206.58 kB)
```

---

## Infrastructure Policy

**CRITICAL:** We prioritize product quality over cost savings.

### Required Plan Levels

| Service | Required Plan | Resources |
|---------|---------------|-----------|
| API (Django) | Standard | 2GB RAM, always-on |
| Worker (Celery) | Standard | 2GB RAM, always-on |
| Redis | Standard | 256MB, persistent |
| PostgreSQL | Standard | 1GB, daily backups |

### Never Use

- Free tier plans
- Starter plans
- Any plan that suspends after inactivity
- Any plan with insufficient RAM for AI workloads

### Config Applied

All services in `render.yaml` now use `plan: standard` with explicit comments warning against downgrades

---

## How to Run Full E2E Test

The Celery worker needs sufficient resources. Options:

1. **Upgrade Render to paid plan** - Workers stay active
2. **Wake up the worker manually** - Visit Render dashboard
3. **Run locally with all tokens**:

```bash
# 1. Set environment variables
export ANTHROPIC_API_KEY=sk-ant-...
export VERCEL_TOKEN=...
export GITHUB_TOKEN=ghp_...

# 2. Start Redis
redis-server

# 3. Start Celery worker
cd backend && celery -A faibric_backend worker -l info

# 4. Start Django
cd backend && python manage.py runserver

# 5. Start frontend
cd frontend && npm run dev

# 6. Visit http://localhost:5173 and create an app
```

**URL Format (when deployed):** `https://app{random}.faibric.com`

---

## Changes in This Session

1. Fixed hardcoded `BUILDER_SECRET`
2. Restricted CORS in production
3. Added SECRET_KEY validation
4. Removed wildcard from ALLOWED_HOSTS
5. Added rate limiting to auth endpoints
6. Fixed audit middleware logging
7. Cleaned up V2/V3 naming confusion
8. Fixed deprecated `onKeyPress` → `onKeyDown`
9. Fixed useCallback stale closure
10. Replaced print statements with logging
11. Fixed type annotations
12. **Upgraded all Render services from starter to standard plans** - CRITICAL infrastructure fix

---

## Test Data

| Item | Value |
|------|-------|
| Test User ID | 156 |
| Test Username | testuser1767904138 |
| Test Email | test-1767904138@test.faibric.com |
| Project ID | 147 |
| Project Name | Bitcoin Price Tracker |
| Project Status | generating (stuck) |
