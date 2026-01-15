# Rule Enforcement System Plan

**Date:** January 2026
**Problem:** Project rules in CLAUDE.md and docs/RULES_OF_PROJECT.md are consistently ignored despite strong wording (MUST, NEVER, CRITICAL, MANDATORY)
**Goal:** Make rule violations impossible or impossible to ignore

---

## The Core Problem

### What We Tried (Doesn't Work)

40+ rules with strong wording:
- "MUST", "NEVER", "CRITICAL", "MANDATORY", "ALWAYS"
- Bold text, caps, repeated statements
- Explicit consequences described

### Why It Doesn't Work

1. **Text rules are suggestions.** Claude reads them but prioritizes the system prompt's task completion patterns over project-specific rules.

2. **System prompt wins.** The built-in Claude Code instructions emphasize efficiency and task completion. When these conflict with project rules, efficiency wins.

3. **No enforcement mechanism.** Rules say "you MUST" but nothing prevents violation. The TodoWrite tool works because it has:
   - A tool (concrete action)
   - System reminders (repeated pressure)
   - Integration into task completion flow

4. **One-time reading.** Rules are read once at session start, then fade as focus shifts to completing tasks.

---

## The Solution: Three-Layer Enforcement

### Layer 1: Hooks (Makes Violation Impossible)

**What:** Shell scripts that run before/after tool calls. Can BLOCK actions.

**Why:** If the action is blocked, it cannot happen. No willpower or memory required.

**Example:** A pre-edit hook that scans for regex JSX patterns will reject the edit entirely. Claude cannot proceed until the approach changes.

### Layer 2: Required Tools (Makes Completion Impossible Without)

**What:** Custom tools that MUST be called before work is considered complete.

**Why:** Like a gate that won't open. Can't mark task done without passing through.

**Example:** CustomerTest tool must be called and return `passed: true` before any pipeline change is complete. The tool handles the entire flow automatically.

### Layer 3: System Reminders (Constant Pressure)

**What:** Messages injected into the conversation repeatedly until action is taken.

**Why:** Same mechanism that makes TodoWrite work. Repeated pressure creates behavior.

**Example:** "CUSTOMER TEST REQUIRED: You modified pipeline code but have not run CustomerTest tool. You cannot complete this task without a passing Customer Test."

---

## Implementation Plan

### Phase 1: Blocking Hooks (Highest Impact)

These hooks make violations literally impossible.

#### Hook 1.1: No Regex for JSX

**File:** `.claude/hooks/check_no_regex_jsx.py`

**Triggers:** Before any Edit tool call

**What it does:** Scans the new content for patterns like:
- `re.sub(...)` containing JSX terms (onClick, className, handle*)
- `.replace(...)` modifying JSX structure

**Why this rule exists:** Regex "fixes" for JSX errors hide bugs instead of fixing them. Results in dead buttons, missing icons, broken functionality. The correct fix is always to improve the AI prompt or validation.

**Enforcement:** BLOCK. Edit is rejected. Claude must try a different approach.

#### Hook 1.2: No Emojis

**File:** `.claude/hooks/check_no_emojis.py`

**Triggers:** Before Edit or Write tool calls

**What it does:** Scans content for emoji unicode ranges.

**Why this rule exists:** Emojis cause encoding issues, look unprofessional in generated business apps, and indicate lazy AI output.

**Enforcement:** BLOCK. Edit/Write is rejected.

#### Hook 1.3: No TypeScript Syntax

**File:** `.claude/hooks/check_no_typescript.py`

**Triggers:** Before Edit or Write to .js/.jsx files

**What it does:** Scans for TypeScript patterns:
- Type annotations (`: string`, `: number`)
- Generics (`<T>`)
- Interface/type declarations

**Why this rule exists:** LLMs produce more reliable JavaScript than TypeScript. TypeScript annotations cause parsing errors when mixed with browser-based JSX transpilation.

**Enforcement:** BLOCK. Must use plain JavaScript.

#### Hook 1.4: Gateway API Only

**File:** `.claude/hooks/check_gateway_usage.py`

**Triggers:** Before Edit to files containing fetch() calls

**What it does:** Detects direct external API calls not going through `api.faibric.com/api/gateway/`

**Why this rule exists:** Browsers block CORS. Direct API calls fail silently. All external data must go through Faibric's gateway proxy.

**Enforcement:** BLOCK. Must use Gateway API.

---

### Phase 2: Required Tools (Gate Completion)

These tools must be called for work to be considered complete.

#### Tool 2.1: CustomerTest

**File:** `.claude/tools/customer_test.py`

**Purpose:** Runs complete customer flow and returns structured result.

**Why a tool:**
- Automates the entire protocol (no steps to forget)
- Returns structured data (passed/failed, URL, screenshot)
- Blocks completion until called
- Removes "I'll do it manually" shortcuts

**Parameters:**
```json
{
  "prompt": "Test prompt with 3+ features",
  "expected_features": ["feature1", "feature2", "feature3"]
}
```

**Returns:**
```json
{
  "passed": true,
  "deployed_url": "https://...",
  "screenshot_path": "/tmp/...",
  "report": "Full formatted report text"
}
```

**Implementation:**
1. POST to /api/onboarding/start-dev/ with prompt
2. Poll /api/onboarding/status/ until deployed
3. Take Playwright screenshot
4. Analyze screenshot for expected features
5. Return structured result

**When required:** After any edit to:
- `apps/code_library/*.py`
- `apps/ai_engine/**/*.py`
- `apps/deployment/*.py`

#### Tool 2.2: VerifyURL

**File:** `.claude/tools/verify_url.py`

**Purpose:** Verifies a URL works before showing to user.

**Why a tool:**
- Consolidates all verification checks
- Must be called explicitly
- Returns clear pass/fail

**Checks performed:**
1. HTTP 200 status
2. JavaScript bundle loads (not 404)
3. Bundle size > 10KB
4. No build errors in JS content
5. Takes screenshot for visual verification

**When required:** Before presenting any deployed URL to user.

#### Tool 2.3: SystemicFix

**File:** `.claude/tools/systemic_fix.py`

**Purpose:** Documents the systemic fix after any bug fix.

**Why a tool:**
- Forces explicit documentation
- Can't skip "I'll do it later"
- Creates audit trail

**Parameters:**
```json
{
  "symptom_fixed": "What immediate fix was applied",
  "root_cause": "Why this class of bug happens",
  "systemic_fix": "What prevents recurrence",
  "files_modified": ["list of files"]
}
```

**When required:** After fixing any bug before marking complete.

#### Tool 2.4: AcknowledgeRules

**File:** `.claude/tools/acknowledge_rules.py`

**Purpose:** Reads and acknowledges project rules at session start.

**Why a tool:**
- All other tools BLOCKED until called
- Creates explicit checkpoint
- Can't skip or forget

**Behavior:**
1. Reads CLAUDE.md and docs/RULES_OF_PROJECT.md
2. Extracts key rules
3. Returns summary
4. Sets session state flag that unlocks other tools

**When required:** Start of every session, before any other tool.

---

### Phase 3: System Reminders (Pressure)

These create TodoWrite-style repeated pressure.

#### Reminder 3.1: Customer Test Required

**Trigger:** Pipeline files modified AND CustomerTest tool not called

**Frequency:** Every 5 tool calls

**Message:**
```
CUSTOMER TEST REQUIRED: You modified pipeline code but have not run
CustomerTest tool. You cannot complete this task without a passing
Customer Test. Call the CustomerTest tool now.
```

#### Reminder 3.2: URL Verification Required

**Trigger:** Deployment URL in context AND VerifyURL not called

**Frequency:** Every 3 tool calls

**Message:**
```
URL VERIFICATION REQUIRED: A deployment URL exists but VerifyURL
tool has not been called. You CANNOT show this URL to the user
until verified. Call VerifyURL now.
```

#### Reminder 3.3: Systemic Fix Required

**Trigger:** Bug fix context detected AND SystemicFix not called

**Frequency:** Every 5 tool calls

**Message:**
```
SYSTEMIC FIX REQUIRED: You fixed a symptom but have not called
SystemicFix tool. You cannot complete this task until you document
what systemic fix prevents this CLASS of problems from recurring.
```

#### Reminder 3.4: Rules Not Acknowledged

**Trigger:** Session start AND AcknowledgeRules not called

**Frequency:** Every tool call (blocking)

**Message:**
```
SESSION START: You MUST call AcknowledgeRules tool before any
other action. All other tools are blocked until you do this.
```

---

## File Structure

```
.claude/
├── settings.json              # Main configuration
├── hooks/
│   ├── pre_tool.py           # Master router for all pre-tool hooks
│   ├── check_no_regex_jsx.py
│   ├── check_no_emojis.py
│   ├── check_no_typescript.py
│   ├── check_gateway_usage.py
│   └── post_pipeline_edit.sh
├── tools/
│   ├── customer_test.py
│   ├── verify_url.py
│   ├── systemic_fix.py
│   └── acknowledge_rules.py
└── state/
    └── .session_state        # Tracks what's been done this session
```

---

## Configuration (settings.json)

```json
{
  "hooks": {
    "pre-edit": [".claude/hooks/pre_tool.py edit"],
    "pre-write": [".claude/hooks/pre_tool.py write"],
    "post-edit": [".claude/hooks/post_pipeline_edit.sh"]
  },
  "tools": {
    "CustomerTest": ".claude/tools/customer_test.py",
    "VerifyURL": ".claude/tools/verify_url.py",
    "SystemicFix": ".claude/tools/systemic_fix.py",
    "AcknowledgeRules": ".claude/tools/acknowledge_rules.py"
  },
  "reminders": {
    "customer_test": {
      "trigger": "pipeline_modified && !customer_test_passed",
      "frequency": 5,
      "message": "CUSTOMER TEST REQUIRED..."
    },
    "url_verification": {
      "trigger": "url_in_context && !url_verified",
      "frequency": 3,
      "message": "URL VERIFICATION REQUIRED..."
    },
    "systemic_fix": {
      "trigger": "bug_fix_detected && !systemic_fix_called",
      "frequency": 5,
      "message": "SYSTEMIC FIX REQUIRED..."
    },
    "rules_first": {
      "trigger": "session_start && !rules_acknowledged",
      "frequency": 1,
      "message": "SESSION START: You MUST call AcknowledgeRules..."
    }
  }
}
```

---

## Enforcement Summary

| Rule | Layer 1 (Hook) | Layer 2 (Tool) | Layer 3 (Reminder) |
|------|----------------|----------------|-------------------|
| Customer Test Protocol | Post-edit trigger | CustomerTest (required) | Yes |
| No Regex for JSX | BLOCKS edit | - | - |
| URL Verification | Post-deploy trigger | VerifyURL (required) | Yes |
| Read Rules First | Blocks all tools | AcknowledgeRules (required) | Yes |
| No Emojis | BLOCKS edit/write | - | - |
| Gateway API Only | BLOCKS edit | - | - |
| Systemic Fix | Post-edit trigger | SystemicFix (required) | Yes |
| No TypeScript | BLOCKS edit/write | - | - |

---

## Why This Will Work

1. **Same mechanisms as TodoWrite.** TodoWrite is followed because it has tools + reminders. This system uses identical patterns.

2. **Impossible > Difficult > Suggested.** Hooks make violations impossible. Tools make completion impossible without compliance. Reminders create pressure. Text rules only suggest.

3. **No memory required.** The system enforces rules automatically. Claude doesn't need to remember—the system blocks non-compliant actions.

4. **Explicit checkpoints.** Tools create concrete moments where compliance is verified. No ambiguity about whether a rule was followed.

5. **Repeated pressure.** System reminders don't give up. They keep appearing until action is taken, just like TodoWrite reminders.

---

## Implementation Priority

1. **Phase 1 (Hooks)** - Implement blocking hooks first. Immediate prevention of worst violations.

2. **Phase 2 (Tools)** - Build CustomerTest tool. This is the most violated rule with highest impact.

3. **Phase 3 (Reminders)** - Add system reminders. Creates TodoWrite-like pressure.

4. **Phase 4 (Integration)** - Wire everything into settings.json and test.

---

## Success Criteria

- Claude cannot complete pipeline changes without passing CustomerTest
- Claude cannot show URLs without VerifyURL passing
- Claude cannot use regex to fix JSX (blocked)
- Claude cannot write TypeScript to JS files (blocked)
- Claude cannot skip reading rules at session start (blocked)
- Every bug fix includes documented systemic fix
