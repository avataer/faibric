# Customer Test Log: Yellow Dog Walker
**Date:** 2026-01-26
**Tester:** Automated (Playwright via Cloud Atlas Manager)
**Product:** Faibric

---

## TEST SUMMARY: INCOMPLETE / ISSUES FOUND

### What Was Requested
```
I am a dog walker who ONLY walks yellow dogs. I love the color green and I drive a Porsche. Build me a website that reflects my unique business and personality\!
```

### What Was Delivered
- Website deployed to: https://appacl92n6szz-7iulgwolg-antons-projects-f1d70cf2.vercel.app
- Yellow dogs requirement: ✓ MET ("dedicated exclusively to yellow and golden-coated dogs")
- Green color requirement: ✗ NOT MET (no green in the design)
- Porsche reference: ✗ NOT MET (not mentioned)

### Critical Issues
1. NO CHAT ITERATION - Test only submitted initial request, never used chat to refine
2. MISSING REQUIREMENTS - Green color and Porsche not incorporated
3. FILE ORGANIZATION WRONG - Files saved to CloudAtlas instead of Faibric
4. EARLY SCREENSHOTS SHOW FAILURE - "Failed to submit request" error was shown but not explained

---

## TIMELINE

| Time (Local) | Event |
|--------------|-------|
| ~17:05 | First test attempt - FAILED (frontend pointing to production API) |
| ~17:09 | Fixed .env.local to point to localhost:8000 |
| ~17:09 | Restarted frontend server |
| ~17:12:55 | Successful submission via Playwright |
| ~17:12:59 | Backend received POST /api/onboarding/start-dev/ - 200 OK |
| ~17:13:00-17:13:57 | Status polling (58 requests) |
| ~17:14:28 | Session marked as deployed |
| ~17:18 | Screenshot of deployed site captured |

---

## DATABASE RECORDS

### Landing Session
```
ID: 28098374c9744ed89b3864c1ec3c6350
Session Token: Bao4LcZe2uO3GXZf14acrTuPHT7hIh5PcOsgBylzFMQ
Status: deployed
Email: dev@faibric.local
User Agent: HeadlessChrome/143.0.7499.4
Created: 2026-01-27 01:12:59.758435 (UTC)
Updated: 2026-01-27 01:14:28.481300 (UTC)
Project ID: 2
Mode: building
```

### Project
```
ID: 2
Name: I am a dog walker who ONLY walks yellow _c95c81e6
Status: deployed
Deployment URL: https://appacl92n6szz-7iulgwolg-antons-projects-f1d70cf2.vercel.app
Created: 2026-01-27 01:12:59.775779 (UTC)
```

---

## BACKEND LOGS (Full)

```
[ENV] Optional not set: VERCEL_TEAM_ID - Vercel team ID (auto-detected if not set)
[ENV] Optional not set: VERCEL_TEAM_ID - Vercel team ID (auto-detected if not set)
Watching for file changes with StatReloader
[27/Jan/2026 01:09:49] "POST /api/onboarding/start-dev/ HTTP/1.1" 200 138
[JSX_VALIDATOR] esbuild binary not found
127.0.0.1 - - [27/Jan/2026 01:09:53] "GET / HTTP/1.1" 200 -
[LOCAL PREVIEW] Verification FAILED: JavaScript errors detected: Failed to execute appendChild on Node: Unexpected token export
127.0.0.1 - - [27/Jan/2026 01:10:09] "GET / HTTP/1.1" 200 -
[27/Jan/2026 01:12:59] "OPTIONS /api/onboarding/start-dev/ HTTP/1.1" 200 0
[27/Jan/2026 01:12:59] "POST /api/onboarding/start-dev/ HTTP/1.1" 200 138
[27/Jan/2026 01:12:59-01:13:57] GET /api/onboarding/status/Bao4LcZe2uO3GXZf14acrTuPHT7hIh5PcOsgBylzFMQ/ - 58 requests, all 200 OK
[27/Jan/2026 01:13:29] "POST /api/onboarding/activity/ HTTP/1.1" 200 15
[LOCAL PREVIEW] Verification FAILED: JavaScript errors detected: Failed to execute appendChild on Node: Unexpected token export
127.0.0.1 - - [27/Jan/2026 01:14:04] "GET / HTTP/1.1" 200 -
```

### Known Errors in Logs
1. `[JSX_VALIDATOR] esbuild binary not found` - Build tool missing
2. `[LOCAL PREVIEW] Verification FAILED: JavaScript errors detected` - ESM module issue

---

## FRONTEND LOGS

```
> faibric-frontend@0.0.1 dev
> vite

VITE v5.4.21  ready in 145 ms

➜  Local:   http://localhost:5173/
➜  Network: http://192.168.12.167:5173/
➜  Network: http://100.75.63.51:5173/
[baseline-browser-mapping] The data in this module is over two months old.
```

---

## SCREENSHOTS CAPTURED

| # | File | Size | What It Shows |
|---|------|------|---------------|
| 1 | 01_faibric_homepage_20260126_171255.png | 41KB | Faibric landing page |
| 2 | 02_request_typed_20260126_171255.png | 48KB | Customer request in textarea |
| 3 | 03_building_started_20260126_171255.png | 71KB | "Building... 16.6%" |
| 4 | 04_building_progress_1_20260126_171255.png | 77KB | Early build progress |
| 5 | 04_building_progress_2_20260126_171255.png | 442KB | Preview appearing |
| 6 | 04_building_progress_3_20260126_171255.png | 442KB | Website visible |
| 7 | 04_building_progress_4_20260126_171255.png | 442KB | Website visible |
| 8 | 04_building_progress_5_20260126_171255.png | 442KB | Website visible |
| 9 | 05_build_complete_20260126_171255.png | 442KB | Build at 76% verifying |
| 10 | 06_DEPLOYED_WEBSITE_FINAL.png | 3.2MB | Full page deployed site |
| 11 | 07_DEPLOYED_WEBSITE_VIEWPORT.png | 3.0MB | Viewport of deployed site |

---

## WHAT WAS NOT CAPTURED

1. **Chat interactions** - No screenshots of iterative chat refinement
2. **Requirement fulfillment** - No iteration to add green color
3. **Error recovery** - No documentation of how "Failed to submit" was resolved
4. **Full build completion** - Screenshots stopped at 76%, no 100% complete

---

## CONFIGURATION CHANGES MADE DURING TEST

### Frontend .env.local
Before:
```
VITE_API_URL=https://faibric-api.onrender.com
```

After:
```
VITE_API_URL=http://localhost:8000
```

### Database Migration Fix
File: `/Users/avataer/Code/Faibric/backend/apps/code_library/migrations/0007_fix_missing_columns.py`
- Modified to skip PostgreSQL-specific SQL on SQLite

---

## TEST VERDICT

**FAIL** - This was not a proper Customer Test because:
1. No iterative chat interaction captured
2. Requirements not fully met (missing green color, Porsche)
3. Misleading screenshots (showed failure, then success without explanation)
4. Files saved to wrong project directory

A proper Customer Test should demonstrate a non-technical user iterating with Faibric chat to refine their website until all requirements are met.
