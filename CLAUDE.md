# CLAUDE.md

Enforcement is code-based. Text rules don't work.

## Enforcement Layers

### Layer 1: Hooks (PreToolUse)
Blocks violations at edit time:
- No emojis
- No TypeScript in JS files
- No regex JSX fixes
- No direct API calls (use Gateway)

See: `.claude/hooks/`

### Layer 2: Manager/Worker (Orchestrator)
Rejects non-compliant work:
- Customer test required for code changes
- URL verification required before showing
- Systemic fix required after bug fixes

See: `.claude/orchestrator/`

## Configuration

- `.claude/settings.json` - Hook configuration
- `.claude/hooks/` - Blocking validators
- `.claude/orchestrator/` - Manager/Worker system

## Historical Context

Archived instruction files: `docs/archived/`

These text-based rules were consistently ignored. Now replaced with code enforcement.

---

## Customer Test Requirements (MANDATORY)

### What a Customer Test MUST Include

1. **AI THINKING LOGS** - Every prompt sent to Claude/OpenAI and every response received. Modify backend to log these BEFORE running any test.

2. **CHAT ITERATION** - Customer tests are NOT one-shot submissions. The test MUST show:
   - Initial build request
   - At least ONE amendment request through the builder chat
   - AI responding and rebuilding

3. **REQUIREMENT VERIFICATION** - If customer says "I love green color", the final website MUST have green. If not, iterate until it does.

4. **SCREENSHOTS REQUIRED**:
   - Chat amendment interaction (customer requesting change + AI response)
   - Final deployed website in Chrome (proving it is online)
   - NO other screenshots needed

5. **FILE LOCATIONS** - All test outputs go to:
   `/Users/avataer/Code/Faibric/customer-tests/{test-name}/`
   
   NOT CloudAtlas, NOT random folders.

6. **FULL_TEST_LOG.md** must contain:
   - All AI prompts (full text)
   - All AI responses (full text)
   - Timestamps for each interaction
   - Token usage
   - Any errors and how they were fixed

### Test Success Criteria

A Customer Test is ONLY successful when:
- [ ] AI thinking logs are complete
- [ ] Amendment was requested AND fulfilled
- [ ] All customer requirements are visible in final site
- [ ] Website is deployed and accessible online
- [ ] Screenshots prove the above
- [ ] All files in correct Faibric location

### Infinite Retry Policy

Workers MUST keep working until SUCCESS. Do not stop on failure. Fix issues, retry, iterate. Only stop when ALL success criteria are met.

---

## Customer Test Verification Protocol (MANDATORY)

### Before Claiming Success

1. **Run color verification:**
   ```bash
   curl -s $DEPLOYED_URL | grep -oE "bg-[a-z]+-[0-9]+" | sort | uniq -c
   ```

2. **Verify REQUIRED colors exist:**
   - If customer said "brown" → must see bg-amber-*, bg-stone-*, bg-yellow-900
   - If customer said "cream" → must see bg-amber-50, bg-orange-50, bg-yellow-50
   - If customer said "green" → must see bg-green-*, bg-emerald-*

3. **Verify UNWANTED colors are ZERO:**
   ```bash
   # This must return 0 or empty
   curl -s $DEPLOYED_URL | grep -c "bg-gray\|bg-blue" 
   ```
   - If customer asked for brown/cream, there should be NO gray, blue, etc.

4. **Verify imagery matches theme:**
   - Coffee shop → coffee cups, beans, cafe photos
   - Dog walker → dogs, parks, outdoor photos
   - NOT random stock photos (winter forests, generic landscapes)

### Color Enforcement in AI Prompts

When customer specifies colors, the AI prompt MUST include:
- "Use ONLY [color1] and [color2] colors"
- "DO NOT use gray, blue, or any other colors"
- "Replace all bg-gray-* with bg-[requested]-*"
- "Replace all bg-white with bg-[light-requested]-*"

### Test is NOT Successful Until:
- [ ] Required colors: grep shows them
- [ ] Unwanted colors: grep shows ZERO
- [ ] Theme imagery: matches customer request
- [ ] Manager verification: passes all checks
