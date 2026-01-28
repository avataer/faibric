# Faibric Feature Priorities Based on Competitor Analysis

**Generated:** 2026-01-27
**Based on:** COMPETITORS.md analysis

---

## Executive Summary

After analyzing 5 major competitors (Manus, Lovable, v0, Base44, Bolt), the key insight is:
**Reliability beats features.** Competitors that work consistently beat those with more features.

---

## PRIORITY 1: Core Reliability (Must Fix First)

### 1.1 Chat Amendment Race Condition ✅ FIXED
- **Status:** Fix deployed to production
- **Impact:** Users couldn't see their changes after chat amendments
- **Fix:** Clear deployment_url before starting modification thread

### 1.2 Build Success Rate
- **Current:** Unknown (need to measure)
- **Target:** >95% successful builds
- **Competitors:** Bolt has only 31% success rate for complex apps - opportunity to differentiate

### 1.3 Deployment Speed
- **Current:** ~90-180 seconds
- **Target:** <60 seconds
- **Competitors:** v0 and Lovable deploy in seconds

---

## PRIORITY 2: Critical Missing Features (Competitor Table Stakes)

Based on feature matrix gaps, these are table stakes that competitors have:

### 2.1 Visual Editor / Click-to-Edit ⚠️ INFRASTRUCTURE BUILT, NEEDS INTEGRATION
- **Lovable:** Visual Edits - click-to-modify UI elements (40% faster iteration)
- **Base44:** Visual editor for fonts, styles
- **v0:** Preview during development
- **Faibric:** Infrastructure exists but not integrated into main flow
  - `VisualEditor.tsx` - iframe-based click detection
  - `PropertyPanel.tsx` - property editing (text, button, image, style)
  - `VisualEditView` backend endpoint ready
  - `design_editor.py` CSS variable editing service
- **Integration Needed:**
  1. Replace PreviewPanel iframe with VisualEditor component
  2. Inject visual editing script into deployed apps
  3. Wire onEditApplied callback to /api/onboarding/modify/
- **Estimated Effort:** Medium - no new development, just integration work

### 2.2 Version Control / Rollback ✅ ALREADY IMPLEMENTED
- **Base44:** Version control with rollback
- **GitHub:** Bidirectional sync (Lovable)
- **Faibric:** ✅ FULLY IMPLEMENTED (discovered during Phase 5 investigation)
  - `ProjectVersion` model stores snapshots
  - `VersionService` handles create/diff/rollback
  - Auto-versioning on generate and modify
  - `VersionsPanel.tsx` UI in project dashboard (Tab 2)
  - API endpoints: `/api/projects/{id}/versions/`, `/api/projects/{id}/rollback/`
- **Status:** Production-ready, users can access via project detail page

### 2.3 Discussion/Planning Mode
- **Lovable:** Discussion Mode for brainstorming
- **Base44:** Discussion mode before coding
- **Faibric:** Partially implemented (PlanningFlowView exists)
- **Implementation:** Complete the planning flow, make it discoverable

---

## PRIORITY 3: Differentiation Features (What Makes Faibric Unique)

### 3.1 All-in-One Stack (Base44's Winning Formula)
Base44 was acquired by Wix because of their all-in-one approach:
- Database built-in
- Auth built-in
- Payments built-in
- No external services needed

**Faibric Status:**
- Vercel for deployment ✅
- No built-in database (need external)
- No built-in auth
- No built-in payments

**Recommendation:** Consider adding Supabase integration or built-in database

### 3.2 Agent Mode
- **Lovable:** Autonomous development, debugging, web search
- **v0:** Web search, file reading, error review, self-correction
- **Faibric:** Basic agent mode exists (AgentModeService)
- **Enhancement:** Add web search, better error recovery, iteration loop

### 3.3 Real Image Generation
- **Base44:** Image generation integration
- **Faibric:** Uses Unsplash (placeholder images)
- **Enhancement:** Add DALL-E/Flux integration for real generated images

---

## PRIORITY 4: Nice-to-Have Features

### 4.1 Model Selection (Base44 Feature)
- Let users choose: Claude Opus/Sonnet, GPT-4, Gemini
- Auto model selection option
- Credit-based pricing per model

### 4.2 Templates Library
- Pre-built templates for common apps
- E-commerce, Portfolio, Blog, Landing Page
- Faibric already has some via component library

### 4.3 GitHub Integration
- Import from GitHub
- Push changes to GitHub
- Bidirectional sync

### 4.4 Custom Domains
- Faibric.com subdomains currently
- Allow custom domain mapping

---

## Recommended Implementation Order (UPDATED 2026-01-27)

1. **Fix Reliability Issues** ✅ DONE
   - ✅ Chat amendment race condition - FIXED and deployed
   - Improve build success rate - ongoing
   - Better error handling and recovery - ongoing

2. **Integrate Visual Editor** (NEXT PRIORITY)
   - ⚠️ Infrastructure already built (VisualEditor.tsx, PropertyPanel.tsx)
   - Needs: Wire into BuildingStudio/PreviewPanel
   - Needs: Inject visual editing script into deployed apps
   - Lower effort than originally estimated

3. **Version Control** ✅ ALREADY DONE
   - ✅ Code snapshots stored (ProjectVersion model)
   - ✅ Rollback UI in dashboard (VersionsPanel.tsx)
   - ✅ Auto-versioning on generate/modify
   - ✅ API endpoints complete

4. **Enhance Agent Mode**
   - Self-correcting builds
   - Error detection and fix loop
   - Web search for solutions

5. **Database Integration**
   - Supabase integration
   - CRUD generation
   - Auth scaffolding

---

## Success Metrics

| Metric | Current | Target | Industry Best |
|--------|---------|--------|---------------|
| Build Success Rate | ? | 95% | Lovable (high) |
| Deploy Time | ~120s | <60s | v0 (~10s) |
| Chat Amendment Success | Fixed | 100% | - |
| Customer Satisfaction | ? | >4.5/5 | Base44 (4.7) |

---

## Key Takeaways from Competitor Analysis

1. **v0 gap:** No backend - Faibric already does full-stack
2. **Bolt gap:** Struggles with complexity - Faibric can be more reliable
3. **Base44:** All-in-one is compelling - consider similar approach
4. **Lovable:** Enterprise focus - opportunity in SMB/individual market

**Faibric's Potential Positioning:**
"The reliable, affordable, full-stack builder that just works"
