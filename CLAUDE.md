# CLAUDE.md - Faibric AI Instructions

This file provides context for AI assistants (Claude Code) working on the Faibric codebase.

## Project Overview

**Faibric** is an AI-powered No-Code App Builder that generates fully functional web applications from natural language descriptions.

### Tech Stack
- **Frontend:** React 18 + TypeScript + Vite + Material-UI + Redux/Zustand
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

### 5. Understand Underlying vs Immediate
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
