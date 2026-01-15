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
