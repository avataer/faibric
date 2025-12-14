# Faibric Known Issues & Pending Items

## Analysis Date: Based on full conversation history

---

## 🔴 Critical Issues

### 1. Admin Dashboard Has No Authentication
**Status:** Not implemented  
**Risk:** High - Anyone can access `/api/analytics/dashboard/`  
**Impact:** All user data, costs, and admin controls are publicly accessible  
**Fix needed:** Add login requirement or API key authentication

### 2. Email Sending May Fail Silently
**Status:** Partially working  
**Issue:** SendGrid/email configuration may not be properly configured  
**Impact:** Magic link emails may not be delivered  
**Workaround:** The "[DEV] Skip to Building" button bypasses email verification  

### 3. Render Deployment Requires External Account Setup
**Status:** Requires manual setup  
**Requirements:**
- `RENDER_API_KEY` must be set
- `RENDER_OWNER_ID` must be set
- `GITHUB_TOKEN` must be set
- `GITHUB_APPS_REPO` repository must exist and be writable  
**Impact:** Without these, deployments fail silently

---

## 🟡 Medium Issues

### 4. AI-Generated Images May Not Match Prompts
**Status:** Improved but not perfect  
**Issue:** Using Picsum.photos with keyword seeds, but images are random  
**Previous issue:** Unsplash source URLs return 503 errors  
**Current workaround:** Using `https://picsum.photos/seed/KEYWORD/800/600`  
**Impact:** Images may not exactly match what user requested (e.g., "Asian woman with two dogs")

### 5. Generated Code May Be Truncated
**Status:** Mitigated  
**Issue:** AI sometimes generates incomplete JSX  
**Mitigations applied:**
- Increased `max_tokens` to 16000
- Added `_validate_code` function to fix common issues
- Added JSX tag completion logic  
**Impact:** Occasional build failures due to syntax errors

### 6. Chat Modification Context Sometimes Lost
**Status:** Improved but not fully tested  
**Issue:** When user asks for modifications, AI sometimes forgets original context  
**Fix applied:** Now passing full context (original request + all follow-ups)  
**Impact:** Modifications may not preserve original intent

### 7. Iframe Preview Flickering
**Status:** Mostly fixed  
**Issue:** Deployed app iframe flickers during polling  
**Fix applied:** Stable `key` attribute, conditional polling  
**Impact:** Minor visual annoyance if it still occurs

### 8. Session Lost on Page Refresh
**Status:** Fixed with localStorage  
**Issue:** Refreshing page would lose build progress  
**Fix applied:** Session persistence in localStorage  
**Remaining:** Session might not restore perfectly in all cases

---

## 🟢 Minor Issues / Nice-to-Haves

### 9. No Rate Limiting
**Status:** Not implemented  
**Risk:** Could be abused with many API calls  
**Impact:** Potential cost overruns

### 10. Daily Tasks Not Auto-Scheduled
**Status:** Manual only  
**Issue:** Daily report generation requires manual trigger  
**Current:** Must call `POST /api/analytics/dashboard/run-daily/`  
**Needed:** Cron job or Celery Beat for automatic scheduling

### 11. Code Library Not Pre-Populated
**Status:** Empty by default  
**Issue:** No component reuse until projects are built  
**Impact:** First builds always use expensive model  
**Workaround:** Build several projects to populate library

### 12. Cohort/Funnel Data Empty Initially
**Status:** Expected behavior  
**Issue:** Dashboard shows empty until data is generated  
**Fix:** Run daily tasks after getting some user sessions

### 13. Health Scores Not Auto-Calculated
**Status:** Manual trigger required  
**Issue:** Must click "Recalculate All" button  
**Needed:** Add to daily tasks or calculate on session update

---

## ⚠️ Environment-Specific Issues

### 14. Local Development Database
**Status:** Working  
**Issue:** Uses SQLite locally, PostgreSQL on Render  
**Impact:** Some features may behave differently

### 15. Redis Connection on Render
**Status:** May require configuration  
**Issue:** SSL certificate validation, IP allowlisting  
**Fix applied:** Using `?ssl_cert_reqs=none` parameter

### 16. Django StatReloader Loses Environment
**Status:** Fixed  
**Issue:** Django's auto-reload was losing environment variables  
**Fix applied:** Explicit `os.environ` setting in settings.py

---

## 📋 Features Mentioned But Not Yet Implemented

### From User Requests:
1. **Slack notifications** - Only email alerts implemented
2. **Custom report builder** - Only daily summary available
3. **A/B testing for prompts** - Not implemented
4. **ML-based churn prediction** - Only simple score-based prediction
5. **User feedback collection** - Not implemented
6. **Webhook integrations** - Not implemented
7. **API for external BI tools** - Not implemented

### Infrastructure:
1. **Celery Beat scheduler** - For automated daily tasks
2. **Rate limiting middleware** - For API protection
3. **Authentication on admin dashboard** - For security
4. **Multi-region deployment** - Only single region

---

## ✅ Recently Fixed Issues

1. ✅ GITHUB_TOKEN not configured - Environment variable loading fixed
2. ✅ Invalid Render URLs with periods - Slug sanitization added
3. ✅ Escaped newlines in generated code - JSON serialization fixed
4. ✅ AI using placeholder content - Strict prompts added
5. ✅ Split-screen not showing final site - UI logic fixed
6. ✅ Server crashes losing session - Monitor script added
7. ✅ AI forgetting modification context - Full context now passed
8. ✅ Expensive model always used - Smart model selection added
9. ✅ No cost tracking - APIUsageLog model added
10. ✅ No admin visibility - Full dashboard built

---

## Recommended Priority Fixes

### High Priority:
1. Add authentication to admin dashboard
2. Implement scheduled daily task runner
3. Add rate limiting

### Medium Priority:
4. Pre-populate code library with common components
5. Improve image matching in AI prompts
6. Add Slack webhook notifications

### Low Priority:
7. Custom report builder
8. User feedback surveys
9. A/B testing framework
