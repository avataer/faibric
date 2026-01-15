# CLAUDE.md - Faibric AI Instructions

This file provides context for AI assistants (Claude Code) working on the Faibric codebase.

---

## MANDATORY: READ RULES FIRST

**BEFORE doing ANY work, you MUST read:**
```
docs/RULES_OF_PROJECT.md
```

This file contains mandatory rules that override any other instructions. Read it at the start of EVERY session. If you haven't read it recently, read it now.

**Failure to follow these rules (especially Customer Test Protocol) has caused repeated failures.**

---

## CRITICAL: Customer Test Reports

**You CANNOT claim a test passed without presenting the FULL report.**

### What is NOT a Customer Test:
- Running test scripts that call the pipeline directly
- Screenshots of localhost test servers
- API responses or curl commands
- Any test that doesn't go through Faibric's chat interface
- Any test without a DEPLOYED URL (must be Render/Vercel, not localhost)

### What IS a Customer Test:
1. **Chat Log**: The actual conversation with Faibric's chat interface (USER types prompt, FAIBRIC responds)
2. **Deployed URL**: A real URL like `https://xxx.onrender.com` or `https://xxx.vercel.app` (NOT localhost)
3. **Screenshot**: Playwright screenshot of the DEPLOYED website
4. **Feature Verification**: Visual confirmation that requested features are visible

### WRONG:
```
Running test script...
Tests passed: 3/3
[Screenshots of localhost:8766]
"All tests passed!"
```

### RIGHT:
```
═══════════════════════════════════════════════════════════════
                    CUSTOMER TEST REPORT
═══════════════════════════════════════════════════════════════

RESULT: PASSED

CHAT LOG:
---------
USER: Create a real estate website with property listings, navigation, and contact form
FAIBRIC: Building your website... [progress updates] ... Deployed!

DEPLOYMENT:
-----------
URL: https://faibric-app-abc123.onrender.com
Screenshot: /tmp/realestate.png

FEATURE VERIFICATION:
---------------------
[x] Property listings - VISIBLE (3 property cards shown)
[x] Navigation - VISIBLE (Home, Properties, Contact links)
[x] Contact form - VISIBLE (name, email, message fields)

SCREENSHOT ANALYSIS:
--------------------
[Claude reads /tmp/realestate.png and describes what is visible]

═══════════════════════════════════════════════════════════════
```

**If you don't present the full report with a DEPLOYED URL, the test is INVALID.**

---

## Project Overview

**Faibric** is an AI-powered No-Code App Builder that generates fully functional web applications from natural language descriptions.

### Tech Stack
- **Frontend (Faibric UI):** React 18 + TypeScript + Vite + Material-UI + Redux/Zustand
- **Generated Apps:** React 18 + Plain JavaScript + Vite + Tailwind CSS (NO TypeScript - per Base44 lessons)
- **Backend:** Django 5.0 + Django REST Framework + Celery
- **Database:** PostgreSQL + Redis
- **Deployment:** Render.com + GitHub + Docker

### Key Directories
```
backend/
  apps/
    ai_engine/       # AI code generation (v2, v3, v6 pipelines)
    code_library/    # Code validation, rules, instructions
    deployment/      # Render/GitHub deployment
    chat/            # Chat widget for generated apps
    project_services/# OAuth, database, auth for generated apps
frontend/
  src/
    components/      # React components
    pages/           # Page components
    store/           # Redux/Zustand state
```

---

## SESSION CONTINUITY (READ FIRST)

**At the START of every session, ALWAYS do these steps:**

### Step 1: Read Session History
```
.claude-sessions/
```
1. List files in `.claude-sessions/` directory
2. Read the most recent session file (sorted by date)
3. Understand what was done previously before proceeding

### Step 2: Read Project Rules (MANDATORY)
**ALWAYS read this file first - it contains mandatory rules:**
```
docs/RULES_OF_PROJECT.md               # MANDATORY - Project rules and constraints
```

### Step 3: Read Project Documentation
Read these MD files to understand the project:
```
README.md                              # Project overview
docs/guides/START_HERE.md              # Where to begin
docs/guides/QUICK_START.md             # Quick setup guide
docs/guides/SETUP.md                   # Full setup instructions
docs/guides/DEPLOYMENT_INSTRUCTIONS.md # How to deploy
docs/research/COMPETITORS.md           # Competitive landscape
docs/research/MARKETING_STRATEGY.md    # Go-to-market strategy
docs/research/RISK_ANALYSIS.md         # Business risks
docs/research/MARKET_RESEARCH.md       # Market analysis
docs/research/FAIBRIC_STRATEGY.md      # Core strategy decisions
docs/research/BASE44_LESSONS.md        # Base44 founder architecture lessons ($0 to $80M)
docs/research/SCRT_RESEARCH_FINDINGS.md # FOUNDER INTERVIEW + Philosophy (Section 16)
docs/research/SCRT_ANTON_MODEL.md      # Anton's SCRT framework
```

**At the END of every session, ALWAYS create/update a session file:**
- File: `.claude-sessions/YYYY-MM-DD_session.txt`
- Include: what was done, pending tasks, files modified, context for next session
- This prevents amnesia across sessions

---

## FOUNDER PHILOSOPHY (READ EVERY SESSION)

**Full interview:** `docs/research/SCRT_RESEARCH_FINDINGS.md` Section 16

### The Founder's Operating System

Abram operates differently from typical founders:

| Normal Founders | Abram |
|-----------------|-------|
| Market analysis | Flow guidance |
| User research | Direct perception |
| Competitor study | "They're like me at 15 - everything they think is wrong" |
| KPIs and metrics | "Hot" or "not hot" feeling |
| Strategy | Transmission |

**Core principle:** "I am the business. All I do is flow."

### Faibric's Purpose

**One word:** BE.

Faibric is an extension of the founder's flow state, which is an extension of the ubiquitous light in the universe. When people touch Faibric, they get transformed - they don't know what transformed them.

### The Formula for "Hot"

From 38 startups and hundreds of apps:

1. **Design beautifully**
2. **Basic things just work**
3. That's it.

### The Only Judge

> "For Faibric, I am the only human who matters. The only judge."

No market validation. No user testing. No metrics. The test: Does the founder feel the "click"? Is it "hot"?

### Elegance

Armani: "Elegance is not about being noticed, it's about being remembered."

Every detail matters. Every absence of a detail matters. We design memories.

### What This Means for AI Assistants

1. **Don't suggest market research** - The founder's perception IS the market research
2. **Don't suggest competitor analysis** - They're cargo cult; irrelevant
3. **Don't suggest user testing** - The founder is the only judge
4. **Focus on:** Clean up the mess. Design beautifully. Basic things work.
5. **Success metric:** Does the founder feel it's "hot"?

---

## OWNER INSTRUCTIONS (MUST ALWAYS FOLLOW)

These are permanent rules that must never be ignored.

### 1. Fix Cause, Not Symptom
When asked to fix a problem:
1. Fix the IMMEDIATE symptom to unblock the user
2. IMMEDIATELY AFTER, create a SYSTEMIC fix that prevents this CLASS of problems forever
3. A systemic fix means: validation, tests, guards, or architectural changes
4. NEVER consider the task complete until the systemic fix is in place
5. NEVER wait for the user to remind you - do it proactively

**Examples:**
- User: "URL doesn't work" -> Fix the broken URL, THEN create pre-deployment validation
- User: "Data is fake" -> Fix the data, THEN enforce Gateway API usage in code generation

### 2. No URL Without Verification
NEVER show a URL to the user unless ALL of these are verified:
1. HTTP 200 status on main page
2. JavaScript bundle loads (not 404)
3. JavaScript bundle size > 10KB (real app, not error page)
4. No build errors detected in the JS content
5. Pre-deployment code validation passed

If ANY check fails, do NOT show the URL. Instead show the error.

### 3. No Emojis Anywhere
NEVER use emojis anywhere:
- Not in generated code
- Not in UI text
- Not in log messages
- Not in responses to the user
- Not in database content
- Not in API responses

Use text labels like [OK], [ERROR], [WARN] instead.

### 4. Always Report What Failed
At the end of EVERY task, ALWAYS include:
1. What worked
2. What failed (if anything)
3. What was the root cause of failures
4. What systemic fix was applied to prevent recurrence

**Bad:** "Done!"
**Good:** "Completed. 3/3 projects deployed. No failures. Added validation system to prevent syntax errors."

### 5. Never Delete MD Files
NEVER delete any .md files unless explicitly told "delete this file".
- If asked to "clean up" or "remove" documentation, move to `docs/archived/` instead
- MD files contain valuable business context, research, and decisions
- When in doubt, archive - never delete

### 6. Understand Underlying vs Immediate
When the user says any of these, they mean CREATE A SYSTEMIC FIX:
- "fix the underlying cause"
- "fix the root cause"
- "I don't want to see this again"
- "fix this forever"
- "prevent this from happening"

These are NOT requests to patch one instance. They require:
1. Identify the class of problem
2. Create validation/tests/guards to catch ALL instances
3. Integrate it into the build/deploy pipeline
4. Make it permanent (cannot be forgotten)

### 8. Never Use Regex to Fix JSX Errors
NEVER use regex to "fix" JavaScript/JSX errors in generated code.

**Bad approach (DO NOT DO):**
```python
code = re.sub(r'defaultSocialIcons\.\w+', 'null', code)
code = re.sub(r'onClick=\{handle\w+\}', 'onClick={() => {}}', code)
```

This hides errors instead of fixing them. The result is broken functionality (dead buttons, missing icons).

**Correct approaches:**
1. Fix the AI prompt so it generates valid code
2. Use AST-based validation to detect undefined references
3. Return errors to AI for correction, don't silently patch

**Full documentation:** `docs/guides/NO_REGEX_FOR_JSX.md`

### 9. Never Ask Permission for Web Fetches
When running Customer Tests or verifying deployed URLs:
- ALWAYS fetch URLs automatically without asking permission
- NEVER interrupt the testing process for confirmations
- If a task requires fetching content, just do it
- Complete all tests fully before reporting results to the user

This rule exists because interrupting tests breaks flow and wastes time.

### 10. Always Test as Customer (End-to-End Verification)
After ANY code changes that affect app generation or deployment, ALWAYS:

1. **Run a full customer flow test:**
   ```bash
   # Create session, provide email, trigger build, poll status
   curl -X POST http://localhost:8000/api/onboarding/start/ -d '{"request": "..."}'
   curl -X POST http://localhost:8000/api/onboarding/email/ -d '{"session_token": "...", "email": "..."}'
   curl -X POST http://localhost:8000/api/onboarding/build/ -d '{"session_token": "..."}'
   # Poll /api/onboarding/status/{token}/ until deployed
   ```

2. **Take screenshots of the deployed website:**
   ```javascript
   // Use puppeteer to screenshot the deployed URL
   await page.goto(deployedUrl, { waitUntil: 'networkidle2' });
   await page.screenshot({ path: '/tmp/verify.png' });
   ```

3. **Verify content, not just HTTP 200:**
   - Check page has actual content (not blank)
   - Verify no JavaScript errors in console
   - Test navigation clicks work
   - Confirm business-specific content appears

4. **Provide verification report:**
   - Screenshots of key pages (Home, Services, Contact, etc.)
   - Any JavaScript errors found
   - What content was verified
   - Final deployed URL

**Never consider a fix complete until screenshots show the website working correctly.**

### 11. Run Customer Tests After Implementation Changes (FULL PROTOCOL)

After implementing ANY changes to the code generation pipeline, AI prompts, or component system, you MUST run a **REAL Customer Test** following the FULL protocol from `docs/RULES_OF_PROJECT.md`.

**WRONG (what you must NOT do):**
- Running test scripts that call the pipeline directly
- Using localhost test servers
- Skipping the Faibric chat interface
- Presenting results without the formal report format

**RIGHT (what you MUST do):**

1. **Use Faibric's chat interface** - Act as a real customer
2. **Get a DEPLOYED URL** - Not localhost, real Render/Vercel deployment
3. **Take screenshot of DEPLOYED site** - Using Playwright headless
4. **Present the FULL formal report** - See format below

**MANDATORY REPORT FORMAT:**
```
═══════════════════════════════════════════════════════════════
                    CUSTOMER TEST REPORT
═══════════════════════════════════════════════════════════════

RESULT: [PASSED / FAILED]

CHAT LOG:
---------
USER: [exact prompt typed into Faibric]
FAIBRIC: [Faibric's response]

DEPLOYMENT:
-----------
URL: [deployed URL - must be real, not localhost]
Screenshot: [path to screenshot file]

FEATURE VERIFICATION:
---------------------
[ ] Feature 1 - [VISIBLE / NOT VISIBLE in screenshot]
[ ] Feature 2 - [VISIBLE / NOT VISIBLE in screenshot]
[ ] Feature 3 - [VISIBLE / NOT VISIBLE in screenshot]

SCREENSHOT ANALYSIS:
--------------------
[Description of what Claude sees in the screenshot]

═══════════════════════════════════════════════════════════════
```

**Read the full protocol:** `docs/RULES_OF_PROJECT.md` Rule 2

**If deployment is blocked by rate limits:**
- Vercel has 100 deployments/day limit on free tier
- If blocked, document the issue and note "Customer Test blocked by deployment rate limits"
- The test is NOT passed until a deployed URL is verified
- Do not use localhost as a substitute for a deployed URL

---

## CODE GENERATION RULES

### Absolute Rules (Never Break)
1. Output ONLY valid JSON when generating apps - no markdown, no backticks
2. Components must be complete, working, self-contained functions
3. For "live" data: use useEffect + setInterval to randomly update values

### Understanding User Requests (Critical)
- Read EVERY word of the user's request - they tell you EXACTLY what they want
- If they mention specific names, terms, stocks, concepts - USE THOSE EXACTLY
- If they ask for N items - generate EXACTLY N items
- DO NOT substitute generic content for specific requirements
- The user's request is your specification - follow it precisely

### Real Data vs Fake Data (Extremely Important)
- If user asks for "real data", "factual data", "historical data" - you MUST use the Gateway API
- NEVER make up stock prices, dates, or financial data - it's WRONG and DANGEROUS
- For stocks: fetch from yahoo_finance via Gateway
- If data cannot be fetched, show: "Connect to fetch real-time data"
- DO NOT HALLUCINATE - if you don't have real data, say so

### Available Libraries
```javascript
// Core
import React, { useState, useEffect } from 'react';

// Routing (for multi-page apps)
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';

// Charts
import { LineChart, Line, BarChart, Bar, PieChart, XAxis, YAxis, ResponsiveContainer } from 'recharts';

// Icons
import { Home, User, Settings, TrendingUp, Check, X, Plus } from 'lucide-react';

// Utilities
import clsx from 'clsx';
import { format } from 'date-fns';
```

### Styling (Tailwind CSS Preferred)
```jsx
// Good - Tailwind
<div className="bg-gray-900 text-white p-6 rounded-xl shadow-lg hover:bg-gray-800 transition">

// Also acceptable - inline styles
<div style={{ backgroundColor: '#1a1a2e', padding: '20px' }}>
```

### Content Rules
- NEVER use placeholder text: No "Lorem ipsum", "placeholder", "[Your text]"
- NEVER use placeholder images: No "placeholder.jpg", empty src
- Generate REAL, realistic content that matches the business/site type
- Write compelling, professional copy as if for a real business

### Image Rules
- Use Picsum: `https://picsum.photos/seed/KEYWORD/800/600`
- Replace KEYWORD with relevant word (dog1, portrait2, art3)
- Each image needs UNIQUE seed for different images
- NEVER use source.unsplash.com - it is broken

---

## FAIBRIC APIs

### Gateway API (External Data)
NEVER use fetch() to call external APIs directly - browsers block CORS.
ALWAYS use the Faibric Gateway:

```javascript
const response = await fetch('https://api.faibric.com/api/gateway/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    service: 'SERVICE_NAME',
    endpoint: '/endpoint',
    params: { key: 'value' }
  })
});
const result = await response.json();
const actualData = result.data;
```

**Available Services (FREE):**
| Service | ID | Example |
|---------|-----|---------|
| Stocks | yahoo_finance | /chart/AAPL |
| Crypto | coingecko | /simple/price?ids=bitcoin&vs_currencies=usd |
| Countries | restcountries | /all |

### Database API (User-Generated Content)
```javascript
const APP_ID = window.FAIBRIC_APP_ID || 999;
const API_BASE = `http://localhost:8000/api/v1/db/${APP_ID}`;

// CREATE
await fetch(`${API_BASE}/items/`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ data: { title: 'New Item' } })
});

// READ
const res = await fetch(`${API_BASE}/items/`);
const { documents } = await res.json();

// UPDATE
await fetch(`${API_BASE}/items/${id}/`, {
  method: 'PUT',
  body: JSON.stringify({ data: { title: 'Updated' } })
});

// DELETE
await fetch(`${API_BASE}/items/${id}/`, { method: 'DELETE' });
```

### Authentication API
```javascript
// Check if logged in
const isLoggedIn = window.FaibricAuth?.isLoggedIn();

// Get current user
const user = window.FaibricAuth?.getUser(); // { id, email, name } or null

// Sign up
const user = await window.FaibricAuth?.signUp('email@example.com', 'password');

// Login
const user = await window.FaibricAuth?.login('email@example.com', 'password');

// Logout
await window.FaibricAuth?.logout();
```

---

## DEPLOYMENT

### GitHub Integration
- Apps are pushed to GitHub branches: `app{random_id}`
- Repository: Configured via `GITHUB_APPS_REPO` env var
- Uses GitHub API for commits and branch management

### Render Deployment
- Production deploys to Render.com
- Config: `/render.yaml`
- API: Uses `RENDER_API_KEY` and `RENDER_OWNER_ID`

### Environment Variables
```bash
# AI
ANTHROPIC_API_KEY=sk-ant-api03-xxx
OPENAI_API_KEY=sk-xxxx

# Deployment
RENDER_API_KEY=rnd_xxxx
GITHUB_TOKEN=ghp_xxxx
GITHUB_APPS_REPO=username/faibric-apps

# Database
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
```

---

## CURRENT SESSION STATE

Use this section to track work in progress across sessions:

### Active Work
<!-- Update this when switching devices -->
- [ ] Current task: (describe what you're working on)
- [ ] Branch: (current git branch)
- [ ] Files modified: (list key files)

### Recent Decisions
<!-- Log important decisions here -->
- (date): Decision about X - chose Y because Z

### Known Issues
<!-- Track bugs or problems -->
- (none currently)

---

## KEY FILES REFERENCE

| Purpose | File |
|---------|------|
| Owner Instructions | `backend/apps/code_library/owner_instructions.py` |
| User Rules | `backend/apps/code_library/user_rules.py` |
| V2 Prompts | `backend/apps/ai_engine/v2/prompts.py` |
| V3 Prompts | `backend/apps/ai_engine/v3/prompts.py` |
| V6 Pipeline | `backend/apps/ai_engine/v6/pipeline.py` |
| Render Deployer | `backend/apps/deployment/render_deployer.py` |
| Django Settings | `backend/faibric_backend/settings.py` |
| Frontend Entry | `frontend/src/main.tsx` |
