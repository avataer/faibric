# Faibric Changes - January 8, 2026 (iPhone Session)

## Branch: `claude/code-review-pBBJT`

---

## Changes Completed

### 1. Security Fixes

| Fix | File | Description |
|-----|------|-------------|
| Hardcoded BUILDER_SECRET | `backend/faibric_backend/settings.py` | Now reads from environment variable |
| CORS unrestricted | `backend/faibric_backend/settings.py` | `CORS_ALLOW_ALL_ORIGINS = DEBUG` (restricted in production) |
| SECRET_KEY validation | `backend/faibric_backend/settings.py` | Raises error if insecure in production |
| Wildcard ALLOWED_HOSTS | `backend/faibric_backend/settings.py` | Removed `*` from production hosts |
| Rate limiting | `backend/apps/users/views.py` | 5/minute registration, 3/hour password change |
| Audit middleware | `backend/faibric_backend/middleware.py` | Fixed logging to use proper logger |

### 2. Code Quality Fixes

| Fix | File | Description |
|-----|------|-------------|
| V2/V3 naming confusion | Multiple files | Cleaned up inconsistent naming |
| Deprecated `onKeyPress` | `frontend/src/components/chat/ChatInput.tsx` | Changed to `onKeyDown` |
| useCallback stale closure | `frontend/src/pages/BuilderPage.tsx` | Fixed dependency array |
| Print statements | `backend/apps/ai_engine/` | Replaced with proper logging |
| Type annotations | `backend/apps/ai_engine/v2/generator.py` | Fixed return type hints |

### 3. Infrastructure Fix (CRITICAL)

**File:** `render.yaml`

**Problem:** All services were using `plan: starter` which has:
- Limited RAM (~512MB)
- Workers suspended after inactivity
- Cold starts of 30-60 seconds
- Insufficient for AI workloads

**Fix Applied:**
```yaml
# All services now use plan: standard
- faibric-api: standard (2GB RAM, always-on)
- faibric-worker: standard (2GB RAM, always-on)
- faibric-redis: standard (256MB, persistent)
- faibric-db: standard (1GB, daily backups)
```

Added infrastructure policy header warning against downgrades.

### 4. Documentation Updates

**File:** `TEST_LOGS.md`

Added:
- URL branding policy (all URLs must be `*.faibric.com`)
- Real production test session logs
- Root cause analysis for generation timeouts
- Infrastructure Policy section
- Complete test results summary

---

## What Couldn't Be Completed

### 1. Full E2E App Deployment

**Status:** Blocked

**What was done:**
- Connected to production API at `faibric-api.onrender.com`
- Verified health check (all tokens configured: Vercel, Render, GitHub, AI)
- Registered test user #156 (testuser1767904138)
- Created project #147 "Bitcoin Price Tracker"
- Triggered V2 regeneration
- Celery worker became active (status changed to "generating")

**What's blocking:**
- The current production infrastructure is still running on starter plans
- The `render.yaml` changes have been pushed but need to be deployed through Render dashboard
- AI generation (Claude Opus 4.5 with 16K tokens) requires more than 512MB RAM
- Worker was stuck in "generating" status for 5+ minutes with no code produced

**To complete this:**
1. Deploy the updated `render.yaml` through Render dashboard
2. OR manually upgrade each service to Standard plan in Render UI
3. Re-trigger generation after infrastructure is upgraded

### 2. Verifying Deployed App URL

**Status:** Blocked (depends on #1)

Expected URL format: `https://app{random}.faibric.com`

---

## Test Data Created

| Item | Value |
|------|-------|
| Test User ID | 156 |
| Test Username | testuser1767904138 |
| Test Email | test-1767904138@test.faibric.com |
| Test Password | TestPass123! |
| Project ID | 147 |
| Project Name | Bitcoin Price Tracker |
| Project Status | generating (stuck) |

---

## Commits Made

```
eb6c501 Upgrade all Render services to standard plans - NEVER use starter
6b980fe Update TEST_LOGS.md with real production test results
```

All changes pushed to `origin/claude/code-review-pBBJT`

---

## Next Steps (Desktop)

1. **Deploy infrastructure upgrade:**
   - Go to Render dashboard
   - Update each service to Standard plan
   - OR use "Blueprints" to sync from `render.yaml`

2. **Re-test after infrastructure upgrade:**
   ```bash
   # Login
   curl -X POST https://faibric-api.onrender.com/api/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"username":"testuser1767904138","password":"TestPass123!"}'

   # Re-trigger project 147
   curl -X POST https://faibric-api.onrender.com/api/projects/147/regenerate/ \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json"

   # Poll for completion
   curl https://faibric-api.onrender.com/api/projects/147/ \
     -H "Authorization: Bearer <token>"
   ```

3. **Verify deployed app URL** uses `*.faibric.com` subdomain

4. **Update TEST_LOGS.md** with successful deployment results

---

## Files Modified

- `render.yaml` - Infrastructure plans upgraded to standard
- `TEST_LOGS.md` - Real test results and infrastructure policy
- `backend/faibric_backend/settings.py` - Security fixes
- `backend/faibric_backend/middleware.py` - Logging fix
- `backend/apps/users/views.py` - Rate limiting
- `backend/apps/ai_engine/v2/generator.py` - Type annotations
- `backend/apps/ai_engine/v2/tasks.py` - Print → logging
- `frontend/src/components/chat/ChatInput.tsx` - onKeyPress fix
- `frontend/src/pages/BuilderPage.tsx` - useCallback fix
