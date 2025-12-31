"""
OWNER INSTRUCTIONS
==================

PERMANENT instructions from the owner that must ALWAYS be followed.
These are HARDCODED and cannot be forgotten or ignored.

This file is checked at the start of every major operation.
"""

from dataclasses import dataclass
from typing import List
from datetime import datetime


@dataclass
class Instruction:
    """A permanent instruction from the owner."""
    id: str
    category: str
    instruction: str
    examples: List[str]
    created_at: str


# ══════════════════════════════════════════════════════════════════════════════
# OWNER INSTRUCTIONS - THESE MUST ALWAYS BE FOLLOWED
# ══════════════════════════════════════════════════════════════════════════════

OWNER_INSTRUCTIONS: List[Instruction] = [
    
    Instruction(
        id="fix-cause-not-symptom",
        category="problem_solving",
        instruction="""
When asked to fix a problem:
1. Fix the IMMEDIATE symptom to unblock the user
2. IMMEDIATELY AFTER, create a SYSTEMIC fix that prevents this CLASS of problems forever
3. A systemic fix means: validation, tests, guards, or architectural changes
4. NEVER consider the task complete until the systemic fix is in place
5. NEVER wait for the user to remind you - do it proactively
""",
        examples=[
            "User: 'URL doesn't work' -> Fix the broken URL, THEN create pre-deployment validation",
            "User: 'Emoji appeared' -> Remove the emoji, THEN create emoji detection/removal system",
            "User: 'Data is fake' -> Fix the data, THEN enforce Gateway API usage in code generation",
        ],
        created_at="2024-12-29"
    ),
    
    Instruction(
        id="no-url-without-verification",
        category="deployment",
        instruction="""
NEVER show a URL to the user unless ALL of these are verified:
1. HTTP 200 status on main page
2. JavaScript bundle loads (not 404)
3. JavaScript bundle size > 10KB (real app, not error page)
4. No build errors detected in the JS content
5. Pre-deployment code validation passed

If ANY check fails, do NOT show the URL. Instead show the error.
""",
        examples=[
            "Bad: 'Here is your URL: ...' when JS returns 404",
            "Good: 'Build failed: TypeScript syntax error on line X' with no URL",
        ],
        created_at="2024-12-29"
    ),
    
    Instruction(
        id="no-emojis-anywhere",
        category="output",
        instruction="""
NEVER use emojis anywhere:
- Not in generated code
- Not in UI text
- Not in log messages
- Not in responses to the user
- Not in database content
- Not in API responses

Use text labels like [OK], [ERROR], [WARN] instead.
""",
        examples=[
            "Bad: '✅ Build complete'",
            "Good: '[OK] Build complete'",
        ],
        created_at="2024-12-29"
    ),
    
    Instruction(
        id="always-report-what-failed",
        category="reporting",
        instruction="""
At the end of EVERY task, ALWAYS include:
1. What worked
2. What failed (if anything)
3. What was the root cause of failures
4. What systemic fix was applied to prevent recurrence
""",
        examples=[
            "Bad: 'Done!'",
            "Good: 'Completed. 3/3 projects deployed. No failures. Added validation system to prevent syntax errors.'",
        ],
        created_at="2024-12-29"
    ),
    
    Instruction(
        id="understand-underlying-vs-immediate",
        category="problem_solving",
        instruction="""
When the user says any of these, they mean CREATE A SYSTEMIC FIX:
- "fix the underlying cause"
- "fix the root cause"
- "I don't want to see this again"
- "fix this forever"
- "prevent this from happening"
- "why did this happen"

These are NOT requests to patch one instance. They are requests to:
1. Identify the class of problem
2. Create validation/tests/guards to catch ALL instances of this class
3. Integrate it into the build/deploy pipeline
4. Make it permanent (cannot be forgotten)
""",
        examples=[
            "User: 'Fix the underlying cause' -> Create a validator, not just fix one error",
            "User: 'I don't want to see this again' -> Add a permanent rule/check",
        ],
        created_at="2024-12-29"
    ),

]


def get_all_instructions() -> List[Instruction]:
    """Get all owner instructions."""
    return OWNER_INSTRUCTIONS


def get_instructions_by_category(category: str) -> List[Instruction]:
    """Get instructions for a specific category."""
    return [i for i in OWNER_INSTRUCTIONS if i.category == category]


def display_instructions() -> str:
    """Display all instructions in human-readable format."""
    lines = ["=" * 70]
    lines.append("OWNER INSTRUCTIONS (PERMANENT)")
    lines.append("=" * 70)
    lines.append("")
    
    for inst in OWNER_INSTRUCTIONS:
        lines.append(f"[{inst.category.upper()}] {inst.id}")
        lines.append("-" * 50)
        lines.append(inst.instruction.strip())
        lines.append("")
        lines.append("Examples:")
        for ex in inst.examples:
            lines.append(f"  - {ex}")
        lines.append("")
        lines.append("=" * 70)
        lines.append("")
    
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# RUNTIME ENFORCEMENT
# ══════════════════════════════════════════════════════════════════════════════

import logging
import re
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class InstructionEnforcer:
    """
    Actively enforces owner instructions at runtime.
    
    Integrated into:
    - Build pipeline (before deployment)
    - Code generation (before saving)
    - API responses (before returning to user)
    """
    
    def __init__(self):
        self.instructions = {i.id: i for i in OWNER_INSTRUCTIONS}
        self.violation_count = 0
        self.fixes_applied = []
    
    def enforce_no_emojis(self, content: str) -> Tuple[str, bool]:
        """
        Enforce: no-emojis-anywhere
        Returns (fixed_content, had_violation)
        """
        emoji_pattern = re.compile(
            '['
            '\U0001F600-\U0001F64F'  # emoticons
            '\U0001F300-\U0001F5FF'  # symbols & pictographs
            '\U0001F680-\U0001F6FF'  # transport & map
            '\U0001F1E0-\U0001F1FF'  # flags
            '\U00002702-\U000027B0'  # dingbats
            '\U0001F900-\U0001F9FF'  # supplemental symbols
            '\U00002600-\U000026FF'  # misc symbols
            '\U00002300-\U000023FF'  # misc technical
            ']+',
            flags=re.UNICODE
        )
        
        if emoji_pattern.search(content):
            self.violation_count += 1
            fixed = emoji_pattern.sub('', content)
            self.fixes_applied.append("Removed emojis (no-emojis-anywhere)")
            logger.warning("[ENFORCER] Removed emojis from content")
            return fixed, True
        
        return content, False
    
    def enforce_no_unverified_url(self, url: str, verification_result: Dict[str, Any]) -> Tuple[Optional[str], str]:
        """
        Enforce: no-url-without-verification
        Returns (url_or_none, message)
        
        verification_result should contain:
        - html_status: int
        - js_status: int
        - js_size: int
        - validation_passed: bool
        """
        checks = [
            ("HTML 200", verification_result.get('html_status') == 200),
            ("JS loads", verification_result.get('js_status') == 200),
            ("JS > 10KB", verification_result.get('js_size', 0) > 10240),
            ("Validation passed", verification_result.get('validation_passed', False)),
        ]
        
        failed = [name for name, passed in checks if not passed]
        
        if failed:
            self.violation_count += 1
            logger.warning(f"[ENFORCER] URL blocked - failed checks: {failed}")
            return None, f"Build failed: {', '.join(failed)}"
        
        return url, "Verified"
    
    def get_prompt_injection(self) -> str:
        """
        Get text to inject into AI prompts to enforce instructions.
        """
        lines = [
            "OWNER INSTRUCTIONS (MUST FOLLOW):",
            ""
        ]
        
        for inst in OWNER_INSTRUCTIONS:
            if inst.category in ['output', 'deployment']:
                lines.append(f"- {inst.id}: {inst.instruction.strip()[:200]}")
        
        return "\n".join(lines)
    
    def enforce_all(self, content: str) -> Tuple[str, List[str]]:
        """
        Apply all content-based enforcements.
        Returns (fixed_content, list_of_fixes_applied)
        """
        self.fixes_applied = []
        
        # Enforce no emojis
        content, _ = self.enforce_no_emojis(content)
        
        return content, self.fixes_applied
    
    def get_stats(self) -> Dict[str, Any]:
        """Get enforcement statistics."""
        return {
            "violations_caught": self.violation_count,
            "fixes_applied": self.fixes_applied,
            "instructions_count": len(self.instructions)
        }


# Global enforcer instance
_enforcer = None


def get_enforcer() -> InstructionEnforcer:
    """Get the global instruction enforcer."""
    global _enforcer
    if _enforcer is None:
        _enforcer = InstructionEnforcer()
    return _enforcer


def enforce_instructions(content: str) -> Tuple[str, List[str]]:
    """Apply all owner instruction enforcements to content."""
    return get_enforcer().enforce_all(content)


def check_url_allowed(url: str, verification: Dict[str, Any]) -> Tuple[Optional[str], str]:
    """Check if a URL can be shown to the user."""
    return get_enforcer().enforce_no_unverified_url(url, verification)


def get_instruction_prompt() -> str:
    """Get owner instructions for AI prompt injection."""
    return get_enforcer().get_prompt_injection()


logger.info(f"[INSTRUCTIONS] Loaded {len(OWNER_INSTRUCTIONS)} owner instructions with runtime enforcement")

