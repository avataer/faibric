"""
SOLUTION VALIDATOR
==================

Detects and BLOCKS instruction-based solutions.

An instruction-based solution is:
- Text that says "MUST", "SHOULD", "ALWAYS", "NEVER"
- But has NO corresponding enforcement code

This validator checks that every rule has enforcement.
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class InstructionViolation:
    """A detected instruction without enforcement."""
    file_path: str
    line_number: int
    instruction_text: str
    missing_enforcement: str


# Patterns that indicate instruction-based rules (bad)
INSTRUCTION_PATTERNS = [
    r'#.*\b(MUST|SHOULD|ALWAYS|NEVER)\b',
    r'\bIMPORTANT:',
    r'\bCRITICAL:',
    r'\bNOTE:.*\b(must|should|always|never)\b',
    r'\b(must|should|always|never)\b.*\b(use|include|have|be)\b',
]

# Known enforced rules - these have code backing them
ENFORCED_RULES = {
    "no_emojis": "user_rules.UserRulesRegistry.enforce_rules",
    "gateway_usage": "code_validator.CodeValidator._check_gateway_usage",
    "no_mock_data": "code_validator.CodeValidator._check_no_mock_data",
    "settings_view": "code_validator.CodeValidator._check_settings_view",
    "jsx_balance": "code_validator.CodeValidator._check_jsx_balance",
    "typescript_generics": "code_validator.CodeValidator._check_typescript_generics",
    "void_elements": "code_validator.CodeValidator._check_void_elements",
    "url_verification": "build_service.BuildService._wait_and_verify_deployment",
    "brace_balance": "code_validator.CodeValidator._check_brace_balance",
}


class SolutionValidator:
    """
    Validates that solutions use enforcement, not instructions.
    
    Checks:
    1. Prompt files for instruction-only rules
    2. Code changes for new rules without validators
    3. Problem fixes for missing systemic enforcement
    """
    
    def __init__(self):
        self.enforced_rules = ENFORCED_RULES
    
    def check_for_instruction_based_rules(self, code: str, file_path: str = "", auto_log: bool = True) -> List[InstructionViolation]:
        """
        Check if code contains instruction-based rules without enforcement.
        
        If auto_log=True, violations are automatically logged to the 
        InstructionSolutionLog so the owner can see them.
        
        Returns list of violations.
        """
        violations = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            for pattern in INSTRUCTION_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    # Found an instruction - check if it's enforced
                    instruction_text = line.strip()
                    
                    # Extract what the instruction is about
                    keywords = self._extract_keywords(instruction_text)
                    
                    # Check if any keyword maps to an enforced rule
                    is_enforced = any(
                        kw in rule_name 
                        for kw in keywords 
                        for rule_name in self.enforced_rules.keys()
                    )
                    
                    if not is_enforced:
                        missing = f"No enforcement found for: {', '.join(keywords)}"
                        
                        violations.append(InstructionViolation(
                            file_path=file_path,
                            line_number=i,
                            instruction_text=instruction_text[:100],
                            missing_enforcement=missing
                        ))
                        
                        # AUTO-LOG to the permanent instruction log
                        if auto_log:
                            try:
                                from .instruction_log import log_instruction_solution
                                log_instruction_solution(
                                    file_path=file_path,
                                    line_number=i,
                                    instruction_text=instruction_text,
                                    missing_enforcement=missing
                                )
                            except Exception as e:
                                logger.error(f"Failed to log instruction solution: {e}")
        
        return violations
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from instruction text."""
        # Remove common words
        stop_words = {'must', 'should', 'always', 'never', 'the', 'a', 'an', 'is', 'are', 'be', 'to', 'for', 'in', 'on', 'at', 'with', 'by', 'from', 'or', 'and', 'not', 'no', 'all', 'any'}
        
        # Extract words
        words = re.findall(r'\b[a-z]+\b', text.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        
        return keywords[:5]  # Return top 5 keywords
    
    def validate_new_rule(self, rule_description: str) -> Tuple[bool, str]:
        """
        Validate that a new rule has enforcement.
        
        Returns (is_valid, message).
        
        A rule is valid if it has a corresponding validator function.
        """
        keywords = self._extract_keywords(rule_description)
        
        # Check if any keyword maps to an existing enforcer
        for kw in keywords:
            for rule_name, validator in self.enforced_rules.items():
                if kw in rule_name:
                    return True, f"Rule enforced by: {validator}"
        
        return False, f"NO ENFORCEMENT FOUND. Must create validator for: {', '.join(keywords)}"
    
    def suggest_enforcement(self, instruction: str) -> str:
        """
        Suggest how to convert an instruction to enforcement.
        """
        keywords = self._extract_keywords(instruction)
        
        suggestion = f"""
INSTRUCTION-BASED SOLUTION DETECTED

You wrote: "{instruction[:80]}..."

This is NOT ALLOWED. Convert to enforcement:

1. Create a check function in code_validator.py:
   def _check_{keywords[0] if keywords else 'rule'}(self, code: str) -> List[ValidationError]:
       # Detect violations
       # Return warnings/errors

2. Add to problem_registry.py REQUIRED_FIXES:
   "{keywords[0] if keywords else 'new_rule'}": SystemicFix(
       id="fix-{keywords[0] if keywords else 'rule'}",
       problem_class="{keywords[0] if keywords else 'new_rule'}",
       validator_function="code_validator.CodeValidator._check_{keywords[0] if keywords else 'rule'}",
       ...
   )

3. Call the check in CodeValidator.validate()
"""
        return suggestion


# Global instance
_validator = None


def get_solution_validator() -> SolutionValidator:
    """Get the global solution validator."""
    global _validator
    if _validator is None:
        _validator = SolutionValidator()
    return _validator


def check_for_instructions(code: str, file_path: str = "") -> List[InstructionViolation]:
    """Check code for instruction-based rules."""
    return get_solution_validator().check_for_instruction_based_rules(code, file_path)


def validate_rule_has_enforcement(rule: str) -> Tuple[bool, str]:
    """Validate a rule has code enforcement."""
    return get_solution_validator().validate_new_rule(rule)


def block_instruction_based_solution(instruction: str) -> str:
    """Block an instruction-based solution and suggest enforcement."""
    return get_solution_validator().suggest_enforcement(instruction)

