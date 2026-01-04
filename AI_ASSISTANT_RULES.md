# AI Assistant Rules for Faibric

**THIS FILE MUST BE READ BEFORE STARTING ANY WORK ON FAIBRIC**

These are permanent rules that the AI assistant MUST follow when working on Faibric.

---

## RULE 1: Act as a Human Customer When Testing

When testing Faibric's features:
- **DO**: Chat with Faibric using normal human language only
- **DO**: Use the Faibric API endpoints as a real customer would
- **DO NOT**: Write code to do things Faibric should do automatically
- **DO NOT**: Manually issue SSL certificates - Faibric must do this
- **DO NOT**: Manually configure DNS - Faibric must do this
- **DO NOT**: Bypass any Faibric functionality

### Example of CORRECT testing:
```
Customer: "Build me a portfolio website with dark theme"
Faibric: [Generates code, deploys, issues SSL, returns URL]
Customer: [Checks the URL works]
```

### Example of WRONG testing:
```
[AI manually issues SSL certificate via Vercel API]
[AI manually adds DNS records]
[AI manually deploys to Vercel]
```

If Faibric fails to do something (like issue SSL), the AI must FIX FAIBRIC'S CODE, not do the task manually.

---

## RULE 2: Fix Causes, Not Symptoms

When a problem is found:
1. Fix the immediate issue
2. **IMMEDIATELY create CODE that prevents this CLASS of problems**
3. Task is NOT complete until enforcement code exists

**BAD** (symptom fix):
- Manually issuing SSL certificates when Faibric doesn't

**GOOD** (cause fix):
- Adding SSL certificate issuance to Faibric's deployment pipeline

---

## RULE 3: No Instruction-Based Solutions

NEVER create fixes that rely on documentation or instructions.

**BAD**:
- Adding "IMPORTANT: always do X" to a prompt
- Writing a comment "# MUST do Y"
- Documenting rules that aren't enforced by code

**GOOD**:
- Validator function that DETECTS violations
- Code that BLOCKS deployment if rule is broken
- Test that FAILS if rule is violated

---

## RULE 4: URLs Must Use faibric.com

All deployed apps must have URLs ending in `faibric.com`, not `vercel.app` or `onrender.com`.

Faibric automatically handles:
- Generating short slugs (e.g., `app7x3km9p2wq`)
- Adding custom domain to Vercel (e.g., `app7x3km9p2wq.faibric.com`)
- Issuing SSL certificates via Let's Encrypt (in `_add_custom_domain()`)
- Returning the faibric.com URL to the customer

**SSL Certificate Propagation**: SSL certificates are issued automatically by Faibric's `vercel_deployer.py` in the `_issue_ssl_certificate()` method. If SSL isn't working for a new subdomain, it may take 30-60 seconds to propagate. The AI should NOT manually issue certificates - this is handled by Faibric's code.

---

## RULE 5: Verify URLs Before Presenting

Before showing ANY URL to users:
- Verify HTTP status is 200
- Verify JavaScript loads correctly
- Verify React app renders
- Verify admin panel is accessible at `/faibric`

All verification must be done BY FAIBRIC'S CODE, not manually by the AI.

---

## RULE 6: Component Library Usage

All generated apps should use Faibric's component library building blocks:
- Navigation components
- Hero sections
- Cards (product, profile, stats)
- Tables (data, sortable)
- Charts (line, bar, pie)
- Forms (contact, login, signup)
- Modals (confirm, info, form)
- etc.

The AI generates code that uses existing library components when available.

---

## RULE 7: Gateway API for External Data

Apps that need external data must use the Faibric Gateway:

```javascript
fetch('https://faibric-api.onrender.com/api/gateway/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ 
    service: 'coingecko', 
    endpoint: '/simple/price?ids=bitcoin&vs_currencies=usd' 
  })
})
```

Available services: `coingecko`, `yahoo_finance`, `restcountries`, etc.

---

## RULE 8: No Mock Data

Generated apps must NOT contain hardcoded fake/mock data arrays. They should either:
- Use the Gateway API for real data
- Use local state that the user can modify
- Show placeholder UI that indicates data source is needed

---

## RULE 9: Settings View Required

All apps that use data must have a Settings view where users can:
- Configure API connections
- View current data sources
- Toggle features on/off

---

## RULE 10: No Emojis in Code

All generated code must use text labels for icons, NEVER emojis.

Enforced by: `user_rules.UserRulesRegistry.enforce_rules()`

---

## Testing Workflow

When testing Faibric as a customer:

1. **Start session**: POST to `/api/onboarding/start/` with request
2. **Provide email**: POST to `/api/onboarding/email/`
3. **Trigger build**: POST to `/api/onboarding/build/`
4. **Poll status**: GET `/api/onboarding/status/{token}/`
5. **Verify URL**: Only check HTTP status, Faibric handles the rest

DO NOT manually:
- Generate code
- Push to GitHub
- Create Render/Vercel services
- Issue SSL certificates
- Configure DNS
- Add domain aliases

If any of these fail, FIX FAIBRIC'S CODE.

---

## Code Enforcement Locations

| Rule | Enforced By |
|------|-------------|
| No emojis | `user_rules.py` |
| No mock data | `code_validator.py` |
| Gateway usage | `code_validator.py` |
| Settings view | `code_validator.py` |
| JSX balance | `code_validator.py` |
| TypeScript interfaces | `code_validator.py` |
| SSL certificates | `vercel_deployer.py` |
| Custom domains | `vercel_deployer.py` |
| URL generation | `url_generator.py` |

---

## Relevant Files

| File | Purpose |
|------|---------|
| `backend/apps/deployment/vercel_deployer.py` | Vercel deployments + SSL + domains |
| `backend/apps/deployment/render_deployer.py` | Render deployments |
| `backend/apps/deployment/url_generator.py` | Short URL slug generation |
| `backend/apps/code_library/code_validator.py` | Pre-deployment validation |
| `backend/apps/onboarding/build_service.py` | Build orchestration |
| `backend/apps/code_library/pipeline.py` | Code generation pipeline |

---

## Remember

**The goal is for Faibric to work completely automatically.** 

The AI assistant should only:
1. Act as a human customer to test features
2. Fix Faibric's code when it doesn't work
3. Never do Faibric's job manually

**If you find yourself writing curl commands to Vercel/Render APIs during testing, STOP. Fix Faibric instead.**

