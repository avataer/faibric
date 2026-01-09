# Faibric V5: Complete Architecture Redesign

## The Core Problem

The current AI doesn't understand when to:
- **Generate content inline** (static product lists, descriptions, etc.)
- **Use database** (user-generated content like posts, comments)
- **Use gateway** (real-time external data like stock prices)

It keeps making wrong decisions, leading to broken apps.

## The Solution: Smarter Code Generation Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           V5 GENERATION PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   USER PROMPT ──────────────────────────────────────────────────────────>   │
│         │                                                                    │
│         ▼                                                                    │
│   ┌─────────────┐                                                           │
│   │  STEP 1:    │  What kind of content does this app need?                 │
│   │  CLASSIFY   │  - Static content? → Generate inline                      │
│   │             │  - User data? → Use database API                          │
│   │             │  - Real-time? → Use gateway API                           │
│   └─────────────┘                                                           │
│         │                                                                    │
│         ▼                                                                    │
│   ┌─────────────┐                                                           │
│   │  STEP 2:    │  Generate complete, working React code                    │
│   │  GENERATE   │  - Include ALL imports                                    │
│   │             │  - Include ALL content (no placeholders!)                 │
│   │             │  - Beautiful inline styles                                │
│   └─────────────┘                                                           │
│         │                                                                    │
│         ▼                                                                    │
│   ┌─────────────┐                                                           │
│   │  STEP 3:    │  Validate before deploying                                │
│   │  VALIDATE   │  - Check syntax errors                                    │
│   │             │  - Check imports exist                                    │
│   │             │  - Check export default exists                            │
│   └─────────────┘                                                           │
│         │                                                                    │
│         ▼ (if errors)                                                       │
│   ┌─────────────┐                                                           │
│   │  STEP 4:    │  Fix any errors before deployment                         │
│   │  AUTO-FIX   │  - Re-run AI with error context                          │
│   │             │  - Max 3 attempts                                         │
│   └─────────────┘                                                           │
│         │                                                                    │
│         ▼                                                                    │
│   ┌─────────────┐                                                           │
│   │  STEP 5:    │  Build and deploy                                         │
│   │  DEPLOY     │                                                           │
│   └─────────────┘                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Insight: Content Classification

| Content Type | Example | How to Handle |
|--------------|---------|---------------|
| **Static Info** | Product lists, company info, recipes | Generate as hardcoded data in the code |
| **User Content** | Posts, comments, todos, forms | Use Database API |
| **Real-time Data** | Stock prices, weather, crypto | Use Gateway API |

### Example: Fender Telecaster Pickups

**WRONG (what AI did):**
```javascript
// Tries to load from empty database
const pickups = await fetch('/api/v1/db/127/pickups/');
// Result: empty array, broken UI
```

**CORRECT (what AI should do):**
```javascript
// Hardcode the actual data
const pickups = [
  { name: 'Original Vintage', description: 'Classic 50s tone...' },
  { name: 'Noiseless', description: 'Hum-canceling design...' },
  { name: 'Custom Shop 51', description: 'Hand-wound...' },
];
```

## Implementation Plan

### 1. Better Prompts

The prompt must explicitly tell the AI:

```
CONTENT RULES:

1. STATIC CONTENT (product lists, info pages, recipes, descriptions):
   - Generate ALL content as hardcoded JavaScript arrays/objects
   - DO NOT use database or API for static information
   - Include real, accurate descriptions - NO placeholders
   
2. USER-GENERATED CONTENT (posts, comments, todos, form submissions):
   - Use the Faibric Database API
   - Users will add/edit/delete this data
   
3. REAL-TIME DATA (stocks, weather, crypto, live feeds):
   - Use the Faibric Gateway API
   - Data changes frequently, must be fetched
```

### 2. Code Validation

Before deploying, check:
- Has `import React`
- Has `export default`
- No undefined variables
- JSX is valid

### 3. Auto-Retry on Errors

If validation fails:
1. Send error back to AI
2. Ask AI to fix it
3. Retry up to 3 times

### 4. Better Error UI

If app fails to deploy:
- Show user what went wrong
- Offer to regenerate

---

## Files to Change

1. `backend/apps/ai_engine/v3/prompts.py` - Add content classification rules
2. `backend/apps/ai_engine/v3/generator.py` - Add validation step
3. `backend/apps/ai_engine/v3/tasks.py` - Add retry logic
4. `frontend/src/pages/LiveCreation.tsx` - Fix chat message persistence

---

## Immediate Fix: Chat Messages Disappearing

The frontend keeps replacing messages instead of merging them. Need to fix the state management.

## Immediate Fix: Content Generation

Update prompts to explicitly forbid using database for static content.



