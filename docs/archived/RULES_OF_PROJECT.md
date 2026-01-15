# Rules of Project

This document contains mandatory rules for all development work on Faibric. Claude must read this file at the beginning of every session.

---

## Rule 1: No Regex for JSX/JavaScript Errors

**NEVER use regex to "fix" JavaScript or JSX syntax errors.**

When AI-generated code has syntax errors like:
- `defaultSocialIcons is not defined`
- `handleSubscribe is not defined`
- Undefined variables or functions

**WRONG approach (regex band-aid):**
```python
code = re.sub(r'defaultSocialIcons\.\w+', 'null', code)
code = re.sub(r'onClick=\{handle\w+\}', 'onClick={() => {}}', code)
```

**CORRECT approaches:**
1. **Pre-seeded scope**: Tell the AI exactly what variables/functions are available
2. **Component interface contracts**: Enforce props in prompts
3. **AST-based validation**: Use esbuild or similar tools
4. **Fix the prompt**: Improve AI instructions to prevent errors

---

## Rule 2: Customer Test Protocol

Every significant code change must include a **Customer Test** that verifies the system works end-to-end.

### CRITICAL: What Counts as Evidence

**ONLY these count as valid evidence:**
- **Chat logs**: The ACTUAL conversation text from Faibric's chat interface. NOT API calls, NOT curl commands, NOT JSON responses. Real human-readable chat messages.
- **Screenshot**: An ACTUAL screenshot image file (.png/.jpg) of the deployed website opened in a browser. NOT WebFetch analysis, NOT curl output, NOT HTML inspection. A real visual screenshot.

**These are NOT valid evidence:**
- curl commands or API responses
- WebFetch tool analysis
- grep/inspection of HTML/JS code
- HTTP status checks
- Any programmatic analysis
- Test scripts that call ComponentGenerationPipeline directly
- Screenshots of localhost test servers (localhost:8766, etc.)
- Any URL that is NOT a deployed Render/Vercel URL

**Success is judged ONLY by:** Looking at the screenshot and confirming the features requested in the chat logs are visibly present.

### How to Take Screenshots (Headless Playwright)

**NEVER use macOS screencapture** - it captures your entire screen including private information.

**ALWAYS use Playwright** (already installed via pip) for headless screenshots:

```python
python3 -c "
from playwright.sync_api import sync_playwright

url = 'https://your-deployed-url.faibric.com'
output = '/tmp/screenshot.png'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.goto(url, wait_until='networkidle')
    page.screenshot(path=output, full_page=True)
    browser.close()
    print(f'Screenshot saved to {output}')
"
```

Then use the Read tool to visually analyze the screenshot:
```
Read tool: /tmp/screenshot.png
```

**Claude can see images** - the Read tool displays images visually. Claude must look at the screenshot and confirm each requested feature is visible.

### Complete Customer Test Workflow

```python
# customer_test.py
from playwright.sync_api import sync_playwright
import requests
import time

# Step 1: Record the chat prompt
PROMPT = "Create a dog walking website with navigation, services section with prices, and contact form"

# Step 2: Submit to Faibric
response = requests.post('http://localhost:8000/api/onboarding/start-dev/',
    json={'request': PROMPT})
session_token = response.json()['session_token']

# Step 3: Poll for deployment URL
while True:
    status = requests.get(f'http://localhost:8000/api/onboarding/status/{session_token}/').json()
    if status.get('deployment_url'):
        url = status['deployment_url']
        break
    time.sleep(5)

# Step 4: Take headless screenshot
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.goto(url, wait_until='networkidle')
    page.screenshot(path='/tmp/test_screenshot.png', full_page=True)
    browser.close()

# Step 5: Claude reads /tmp/test_screenshot.png and confirms features
```

**Test PASSES only if:** Claude can see in the screenshot that all requested features from the prompt are visibly present.

### Customer Test Report (MANDATORY)

At the end of every Customer Test, Claude MUST present a formal report in this exact format:

```
═══════════════════════════════════════════════════════════════
                    CUSTOMER TEST REPORT
═══════════════════════════════════════════════════════════════

RESULT: [PASSED / FAILED]

CHAT LOG:
---------
[Copy-paste the FULL conversation with Faibric's chat interface]

USER: [what the customer typed]
FAIBRIC: [Faibric's response]
USER: [any follow-up]
FAIBRIC: [response]
... (complete conversation until deployment)

DEPLOYMENT:
-----------
URL: [deployed URL]
Build Time: [time in seconds]
Screenshot: [path to screenshot file]

FEATURE VERIFICATION:
---------------------
[ ] Feature 1: [description] - [VISIBLE / NOT VISIBLE]
[ ] Feature 2: [description] - [VISIBLE / NOT VISIBLE]
[ ] Feature 3: [description] - [VISIBLE / NOT VISIBLE]
... (all features from prompt)

JAVASCRIPT ERRORS:
------------------
[list any console errors, or "None"]

SCREENSHOT ANALYSIS:
--------------------
[Description of what is visible in the screenshot, confirming each feature]

═══════════════════════════════════════════════════════════════
```

This report is MANDATORY. Without it, the Customer Test is not complete.

### Customer Test Requirements:

1. **Interface constraint**: You can ONLY interact through Faibric's builder chat interface (prompts to the AI builder)
   - You must act as a human customer using natural language ONLY
   - You may NEVER modify, patch, or touch the generated code
   - You may NEVER use sed, edit, or any code manipulation on Faibric's output
   - If the output is broken, the test is FAILED - do not fix the output

2. **Feature requirement**: Must test at least **3 core technical features** explicitly:
   - Examples of valid features: navigation, forms, data fetching, state management, API integration, authentication, real-time updates, charts/visualizations
   - NOT valid: text changes, color changes, simple static content

3. **Time limit**: From start to successful deployment must take **no longer than 7 minutes**
   - If exceeded: ABORT the test and investigate why it took too long
   - Document the issue and propose fixes

4. **Required deliverables**:
   - **Chat logs**: Copy-paste of the actual chat conversation with Faibric
   - **Screenshot file**: An actual screenshot image of the deployed website in a browser
   - **Screenshot analysis**: Claude must visually analyze the screenshot and confirm each requested feature is visible

5. **Success criteria**:
   - Website deploys without errors
   - All 3+ requested features are visible and functional in the screenshot
   - No console errors in the browser
   - Claude has analyzed the screenshot and confirmed all features are present

6. **When test FAILS**:
   - Immediately declare "CUSTOMER TEST FAILED"
   - Do NOT patch or modify the generated output
   - Investigate the root cause in Faibric's codebase (component_pipeline.py, modular_composer.py, etc.)
   - Create a SYSTEMIC fix that prevents this class of error
   - Run a completely NEW Customer Test from scratch
   - Repeat until success

7. **MANDATORY: Test After Every Fix**:
   - After applying ANY systemic fix, you MUST immediately run a Customer Test
   - Do NOT declare the fix complete until the Customer Test PASSES
   - If the test fails, apply another fix and test again
   - Keep iterating fix -> test -> fix -> test until ALL tests pass
   - This is NOT optional - fixes without verification are worthless

8. **MANDATORY: Always Present Full Reports**:
   - You CANNOT say "test passed" without presenting the FULL Customer Test Report
   - Every report MUST include:
     - Screenshot file path (e.g., /tmp/test_screenshot.png) that you READ with the Read tool
     - Chat log showing USER prompt and FAIBRIC response
     - Feature verification based on VISUAL inspection of screenshot
   - Saying "PASSED" without a report is a VIOLATION of rules
   - If you run 3 tests, you MUST present 3 complete reports
   - NO EXCEPTIONS - a test without a report is not a valid test

### Example Customer Test Prompts (GOOD):
- "Create a dashboard with real-time stock data using the Gateway API, a navigation sidebar, and a dark theme with charts"
- "Build a task manager with drag-and-drop, form validation, and local storage persistence"
- "Create an e-commerce product page with image gallery, add-to-cart functionality, and responsive layout"

### Example Customer Test Prompts (BAD - not enough features):
- "Create a click counter" (only 1 feature)
- "Make a personal website" (no specific technical features)
- "Build a calculator" (single feature)

---

## Rule 3: No TypeScript Anywhere

**NEVER use TypeScript in any part of the Faibric project.**

All code must be plain JavaScript (.js or .jsx files). This applies to:
- Generated frontend code
- Library components
- AI prompts and generated output
- New code written by developers

**Why:**
1. LLMs produce more reliable JavaScript than TypeScript
2. TypeScript annotations create parsing/build errors when mixed with JSX
3. Simpler code = fewer bugs

**Enforcement:**
- Library components MUST be stored as plain JavaScript
- The `strip_typescript_annotations()` function from `apps/code_library/typescript_stripper.py` is used as a safety net to clean any TypeScript that slips through
- Build validation should fail if TypeScript syntax is detected

**What to check for:**
- Type annotations: `const x: string`, `function(a: number)`
- Generic types: `Array<T>`, `Record<K,V>`
- Interface/type definitions: `interface X {}`, `type Y = ...`
- Type imports: `import type { X }`

---

## Rule 4: Fix Cause, Not Symptom

When fixing a problem:
1. Fix the IMMEDIATE symptom to unblock the user
2. IMMEDIATELY AFTER, create a SYSTEMIC fix that prevents this CLASS of problems forever
3. A systemic fix means: validation, tests, guards, or architectural changes
4. NEVER consider the task complete until the systemic fix is in place

---

## Rule 5: Base44 Lessons (AI Code Generation)

From Base44 founder Maor Shlomo:

1. **Use plain JavaScript over TypeScript** - LLMs produce more reliable JS
2. **Pre-seed the scope** - Tell AI exactly what variables/functions are available
3. **Component interface contracts** - Define inputs/outputs clearly
4. **No regex fixes** - Fix the generation, not the output
5. **Simple is better** - Avoid complex abstractions in generated code

---

## Rule 6: URL Verification Before Showing to User

NEVER show a URL to the user unless ALL of these are verified:
1. HTTP 200 status on main page
2. JavaScript bundle loads (not 404)
3. JavaScript bundle size > 10KB (real app, not error page)
4. No build errors detected in the JS content
5. Pre-deployment code validation passed

---

## Rule 7: No Emojis

NEVER use emojis anywhere in:
- Generated code
- UI text
- Log messages
- Responses to the user
- Database content
- API responses

Use text labels like [OK], [ERROR], [WARN] instead.

---

## Adding New Rules

When a new systemic issue is discovered and fixed, add a rule here documenting:
1. What the problem was
2. What NOT to do
3. What TO do instead
