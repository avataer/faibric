"""
PROBLEM REGISTRY
================

A system that FORCES systemic fixes by:
1. Logging every problem encountered
2. Requiring a systemic fix for each problem class
3. Detecting recurring problems (proof that systemic fix is missing/inadequate)
4. Blocking deployment if a known problem class has no systemic fix

This is NOT instructions. This is CODE that BLOCKS bad behavior.
"""

import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Problem:
    """A problem that was encountered."""
    id: str
    problem_class: str  # e.g., "typescript_generic_syntax", "jsx_balance", "emoji_in_code"
    description: str
    first_seen: datetime
    occurrences: int = 1
    last_seen: datetime = None
    systemic_fix_id: Optional[str] = None  # ID of the fix that should prevent this
    
    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = self.first_seen


@dataclass
class SystemicFix:
    """A systemic fix that prevents a class of problems."""
    id: str
    problem_class: str
    description: str
    validator_function: str  # Name of the function that implements this fix
    created_at: datetime
    is_active: bool = True


# ══════════════════════════════════════════════════════════════════════════════
# KNOWN PROBLEM CLASSES AND THEIR REQUIRED FIXES
# ══════════════════════════════════════════════════════════════════════════════

REQUIRED_FIXES: Dict[str, SystemicFix] = {
    "typescript_generic_syntax": SystemicFix(
        id="fix-ts-generics",
        problem_class="typescript_generic_syntax",
        description="TypeScript generic syntax errors like useState<Type>( instead of useState<Type>>(",
        validator_function="code_validator.CodeValidator._check_typescript_generics",
        created_at=datetime(2024, 12, 29),
        is_active=True
    ),
    "jsx_balance": SystemicFix(
        id="fix-jsx-balance",
        problem_class="jsx_balance",
        description="Unbalanced JSX tags (more opening than closing)",
        validator_function="code_validator.CodeValidator._check_jsx_balance",
        created_at=datetime(2024, 12, 29),
        is_active=True
    ),
    "void_element_not_self_closing": SystemicFix(
        id="fix-void-elements",
        problem_class="void_element_not_self_closing",
        description="Void elements like <input> not self-closing in JSX",
        validator_function="code_validator.CodeValidator._check_void_elements",
        created_at=datetime(2024, 12, 29),
        is_active=True
    ),
    "emoji_in_code": SystemicFix(
        id="fix-emoji",
        problem_class="emoji_in_code",
        description="Emojis appearing in generated code or output",
        validator_function="user_rules.UserRulesRegistry.enforce_rules",
        created_at=datetime(2024, 12, 29),
        is_active=True
    ),
    "url_shown_before_verified": SystemicFix(
        id="fix-url-verification",
        problem_class="url_shown_before_verified",
        description="URLs shown to user before deployment is verified working",
        validator_function="build_service.BuildService._wait_and_verify_deployment",
        created_at=datetime(2024, 12, 29),
        is_active=True
    ),
    "gateway_not_used": SystemicFix(
        id="fix-gateway-usage",
        problem_class="gateway_not_used",
        description="App needs data but doesn't use Gateway API",
        validator_function="code_validator.CodeValidator._check_gateway_usage",
        created_at=datetime(2024, 12, 29),
        is_active=True
    ),
    "mock_data_detected": SystemicFix(
        id="fix-mock-data",
        problem_class="mock_data_detected",
        description="Hardcoded mock/fake data instead of using Gateway API",
        validator_function="code_validator.CodeValidator._check_no_mock_data",
        created_at=datetime(2024, 12, 29),
        is_active=True
    ),
    "missing_settings_view": SystemicFix(
        id="fix-settings-view",
        problem_class="missing_settings_view",
        description="App uses data but has no Settings view for API configuration",
        validator_function="code_validator.CodeValidator._check_settings_view",
        created_at=datetime(2024, 12, 29),
        is_active=True
    ),
    "instruction_based_solution": SystemicFix(
        id="fix-instruction-solution",
        problem_class="instruction_based_solution",
        description="Solution uses instructions (MUST/SHOULD/ALWAYS/NEVER) instead of code enforcement",
        validator_function="solution_validator.SolutionValidator.check_for_instruction_based_rules",
        created_at=datetime(2024, 12, 30),
        is_active=True
    ),
}


class ProblemRegistry:
    """
    Tracks problems and ensures systemic fixes exist.
    
    BLOCKING BEHAVIOR:
    - If a problem occurs and no systemic fix exists, log ERROR and require fix
    - If a problem recurs (fix exists but didn't work), log ERROR and require fix improvement
    """
    
    def __init__(self):
        self.problems: Dict[str, Problem] = {}
        self.required_fixes = REQUIRED_FIXES
        self._load_from_db()
    
    def _load_from_db(self):
        """Load problem history from database."""
        try:
            from .models import ProblemRecord
            for record in ProblemRecord.objects.all():
                self.problems[record.problem_id] = Problem(
                    id=record.problem_id,
                    problem_class=record.problem_class,
                    description=record.description,
                    first_seen=record.first_seen,
                    occurrences=record.occurrences,
                    last_seen=record.last_seen,
                    systemic_fix_id=record.systemic_fix_id
                )
        except Exception:
            pass  # Model might not exist yet
    
    def _save_to_db(self, problem: Problem):
        """Save problem to database."""
        try:
            from .models import ProblemRecord
            ProblemRecord.objects.update_or_create(
                problem_id=problem.id,
                defaults={
                    'problem_class': problem.problem_class,
                    'description': problem.description,
                    'first_seen': problem.first_seen,
                    'occurrences': problem.occurrences,
                    'last_seen': problem.last_seen,
                    'systemic_fix_id': problem.systemic_fix_id
                }
            )
        except Exception:
            pass  # Model might not exist yet
    
    def classify_problem(self, error_message: str, code: str = "") -> str:
        """
        Classify an error into a problem class.
        Returns the problem_class string.
        """
        error_lower = error_message.lower()
        code_sample = code[:1000].lower() if code else ""
        
        # TypeScript generic issues
        if any(x in error_lower for x in ['generic', 'type', 'usestate<', 'expected ">"']):
            return "typescript_generic_syntax"
        
        # JSX balance issues
        if any(x in error_lower for x in ['jsx', 'unclosed', 'unexpected', '</div>']):
            return "jsx_balance"
        
        # Void element issues
        if any(x in error_lower for x in ['void element', 'self-closing', '<input', '<img']):
            return "void_element_not_self_closing"
        
        # Emoji issues
        emoji_pattern = re.compile(r'[\U0001F600-\U0001F9FF]')
        if emoji_pattern.search(error_message) or emoji_pattern.search(code_sample):
            return "emoji_in_code"
        
        # URL verification issues
        if any(x in error_lower for x in ['404', 'not found', 'failed to load', 'blank page']):
            return "url_shown_before_verified"
        
        # Unknown - this needs a new systemic fix!
        return f"unknown_{hashlib.md5(error_message[:100].encode()).hexdigest()[:8]}"
    
    def report_problem(self, error_message: str, code: str = "") -> Tuple[str, bool, str]:
        """
        Report a problem that occurred.
        
        Returns: (problem_class, has_systemic_fix, action_required)
        
        action_required will be:
        - "" if fix exists and is active
        - "CREATE_FIX: ..." if no fix exists
        - "IMPROVE_FIX: ..." if fix exists but problem recurred
        """
        problem_class = self.classify_problem(error_message, code)
        now = datetime.now()
        
        # Check if we've seen this class before
        problem_id = f"prob_{problem_class}"
        
        if problem_id in self.problems:
            # RECURRING PROBLEM - fix didn't work!
            problem = self.problems[problem_id]
            problem.occurrences += 1
            problem.last_seen = now
            self._save_to_db(problem)
            
            if problem_class in self.required_fixes:
                fix = self.required_fixes[problem_class]
                logger.error(
                    f"[PROBLEM REGISTRY] RECURRING PROBLEM: {problem_class} "
                    f"(occurred {problem.occurrences} times). "
                    f"Systemic fix '{fix.id}' exists but is INADEQUATE."
                )
                return problem_class, True, f"IMPROVE_FIX: {fix.validator_function} is not catching all cases"
            else:
                logger.error(
                    f"[PROBLEM REGISTRY] RECURRING PROBLEM: {problem_class} "
                    f"(occurred {problem.occurrences} times). "
                    f"NO SYSTEMIC FIX EXISTS - MUST CREATE ONE."
                )
                return problem_class, False, f"CREATE_FIX: Need validator for {problem_class}"
        else:
            # NEW PROBLEM
            problem = Problem(
                id=problem_id,
                problem_class=problem_class,
                description=error_message[:500],
                first_seen=now
            )
            self.problems[problem_id] = problem
            self._save_to_db(problem)
            
            if problem_class in self.required_fixes:
                fix = self.required_fixes[problem_class]
                problem.systemic_fix_id = fix.id
                logger.info(f"[PROBLEM REGISTRY] Problem {problem_class} has fix: {fix.id}")
                return problem_class, True, ""
            else:
                logger.error(
                    f"[PROBLEM REGISTRY] NEW PROBLEM CLASS: {problem_class}. "
                    f"MUST CREATE SYSTEMIC FIX before continuing."
                )
                return problem_class, False, f"CREATE_FIX: Need validator for {problem_class}"
    
    def check_fix_exists(self, problem_class: str) -> Tuple[bool, Optional[SystemicFix]]:
        """Check if a systemic fix exists for a problem class."""
        if problem_class in self.required_fixes:
            return True, self.required_fixes[problem_class]
        return False, None
    
    def verify_fix_works(self, problem_class: str, test_input: str) -> bool:
        """
        Verify that a systemic fix actually catches the problem.
        
        This runs the validator function on test input that SHOULD trigger it.
        """
        if problem_class not in self.required_fixes:
            return False
        
        fix = self.required_fixes[problem_class]
        
        # Import and run the validator
        try:
            if "code_validator" in fix.validator_function:
                from .code_validator import validate_and_fix
                is_valid, fixed_code, messages = validate_and_fix(test_input)
                # If it found and fixed something, the fix works
                return any(problem_class.replace("_", " ") in m.lower() for m in messages)
            
            if "user_rules" in fix.validator_function:
                from .user_rules import enforce_user_rules
                result = enforce_user_rules(test_input)
                return result != test_input  # Changed means it caught something
            
        except Exception as e:
            logger.error(f"[PROBLEM REGISTRY] Fix verification failed: {e}")
            return False
        
        return False
    
    def get_unresolved_problems(self) -> List[Problem]:
        """Get problems that don't have systemic fixes."""
        return [p for p in self.problems.values() 
                if p.problem_class not in self.required_fixes]
    
    def get_recurring_problems(self, threshold: int = 2) -> List[Problem]:
        """Get problems that have occurred multiple times despite having fixes."""
        return [p for p in self.problems.values() 
                if p.occurrences >= threshold and p.problem_class in self.required_fixes]


# Global instance
_registry = None


def get_registry() -> ProblemRegistry:
    """Get the global problem registry."""
    global _registry
    if _registry is None:
        _registry = ProblemRegistry()
    return _registry


def report_problem(error_message: str, code: str = "") -> Tuple[str, bool, str]:
    """Report a problem and get required action."""
    return get_registry().report_problem(error_message, code)


def must_have_systemic_fix(problem_class: str) -> bool:
    """
    BLOCKING CHECK: Returns True only if a systemic fix exists.
    Use this to BLOCK operations that don't have proper fixes.
    """
    exists, _ = get_registry().check_fix_exists(problem_class)
    return exists


def get_missing_fixes() -> List[str]:
    """Get list of problem classes that need systemic fixes."""
    registry = get_registry()
    return [p.problem_class for p in registry.get_unresolved_problems()]

