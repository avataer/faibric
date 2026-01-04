"""
USER RULES SYSTEM
=================

This module provides a PERSISTENT, NEVER-FORGOTTEN system for storing
and enforcing user rules across all code generation.

RULES ARE STORED IN:
1. AdminDesignRules database model (for design/style rules)
2. This file's HARDCODED_RULES (for absolute rules from the owner)
3. Environment variables (for deployment-specific rules)

ALL CODE GENERATION MUST CHECK THESE RULES.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Rule:
    """A single rule that MUST be enforced."""
    id: str
    name: str
    description: str
    rule_type: str  # 'forbidden', 'required', 'style', 'content'
    pattern: Optional[str] = None  # Regex pattern to detect violations
    replacement: Optional[str] = None  # What to replace violations with
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "owner"  # 'owner', 'admin', 'user'
    priority: int = 100  # Higher = more important


# ══════════════════════════════════════════════════════════════════════════════
# HARDCODED OWNER RULES - THESE ARE NEVER FORGOTTEN
# ══════════════════════════════════════════════════════════════════════════════

OWNER_RULES: List[Rule] = [
    Rule(
        id="no-emojis",
        name="No Emojis",
        description="NEVER use emojis anywhere in generated code, UI, or output. Use text labels or SVG icons instead.",
        rule_type="forbidden",
        pattern=r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0001F900-\U0001F9FF\U00002600-\U000026FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002300-\U000023FF\U0000FE00-\U0000FE0F]',
        replacement='',
        source="owner",
        priority=1000  # Highest priority
    ),
]


class UserRulesRegistry:
    """
    Central registry for all user rules.
    
    This class ensures rules are:
    1. ALWAYS loaded (from hardcoded + database + env)
    2. ALWAYS enforced (via enforce_rules method)
    3. NEVER forgotten (hardcoded rules persist across restarts)
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._rules: Dict[str, Rule] = {}
        self._load_all_rules()
        self._initialized = True
    
    def _load_all_rules(self):
        """Load all rules from all sources."""
        # 1. Load HARDCODED owner rules (NEVER forgotten)
        for rule in OWNER_RULES:
            self._rules[rule.id] = rule
            logger.info(f"[RULES] Loaded owner rule: {rule.id}")
        
        # 2. Load from database
        self._load_database_rules()
        
        # 3. Load from environment
        self._load_env_rules()
    
    def _load_database_rules(self):
        """Load rules from AdminDesignRules model."""
        try:
            from .models import AdminDesignRules, Constraint
            
            # Load from AdminDesignRules
            active_rules = AdminDesignRules.objects.filter(is_active=True).first()
            if active_rules:
                # Parse forbidden_patterns
                if active_rules.forbidden_patterns:
                    for line in active_rules.forbidden_patterns.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('-'):
                            rule_id = f"db-{hash(line) % 10000}"
                            self._rules[rule_id] = Rule(
                                id=rule_id,
                                name=f"Forbidden: {line[:30]}",
                                description=line,
                                rule_type="forbidden",
                                source="admin"
                            )
            
            # Load from Constraint model
            try:
                for constraint in Constraint.objects.filter(is_active=True):
                    self._rules[f"constraint-{constraint.id}"] = Rule(
                        id=f"constraint-{constraint.id}",
                        name=constraint.name,
                        description=constraint.rule_text,
                        rule_type=constraint.constraint_type,
                        source="admin",
                        priority=constraint.priority
                    )
            except Exception:
                pass  # Constraint table might not exist yet
                
        except Exception as e:
            logger.warning(f"[RULES] Could not load database rules: {e}")
    
    def _load_env_rules(self):
        """Load rules from environment variables."""
        import os
        
        # Check for FAIBRIC_RULES_* environment variables
        for key, value in os.environ.items():
            if key.startswith('FAIBRIC_RULE_'):
                rule_id = key.replace('FAIBRIC_RULE_', '').lower()
                self._rules[f"env-{rule_id}"] = Rule(
                    id=f"env-{rule_id}",
                    name=rule_id.replace('_', ' ').title(),
                    description=value,
                    rule_type="forbidden" if "NO_" in key else "required",
                    source="env"
                )
    
    def get_all_rules(self) -> List[Rule]:
        """Get all rules, sorted by priority."""
        return sorted(self._rules.values(), key=lambda r: -r.priority)
    
    def get_rules_by_type(self, rule_type: str) -> List[Rule]:
        """Get rules of a specific type."""
        return [r for r in self.get_all_rules() if r.rule_type == rule_type]
    
    def get_forbidden_patterns(self) -> List[str]:
        """Get list of forbidden patterns for prompt injection."""
        patterns = []
        for rule in self.get_rules_by_type("forbidden"):
            patterns.append(f"- {rule.description}")
        return patterns
    
    def enforce_rules(self, content: str) -> str:
        """
        Apply all rules to content, fixing violations.
        
        Args:
            content: The generated code/text to check
            
        Returns:
            The content with violations fixed
        """
        fixed_content = content
        violations = []
        
        for rule in self.get_all_rules():
            if rule.pattern:
                try:
                    pattern = re.compile(rule.pattern, re.UNICODE)
                    matches = pattern.findall(fixed_content)
                    if matches:
                        violations.append({
                            'rule': rule.id,
                            'matches': len(matches),
                            'examples': matches[:3]
                        })
                        # Apply replacement if defined
                        if rule.replacement is not None:
                            fixed_content = pattern.sub(rule.replacement, fixed_content)
                            logger.info(f"[RULES] Fixed {len(matches)} violations of {rule.id}")
                except re.error as e:
                    logger.warning(f"[RULES] Invalid pattern in rule {rule.id}: {e}")
        
        if violations:
            logger.warning(f"[RULES] Found violations: {violations}")
        
        return fixed_content
    
    def get_prompt_injection(self) -> str:
        """
        Get text to inject into AI prompts to enforce rules.
        
        This should be added to EVERY code generation prompt.
        """
        forbidden = self.get_forbidden_patterns()
        if not forbidden:
            return ""
        
        return f"""
ABSOLUTE RULES (NEVER VIOLATE):
{chr(10).join(forbidden)}
"""
    
    def add_rule(self, rule: Rule):
        """Add a new rule to the registry."""
        self._rules[rule.id] = rule
        logger.info(f"[RULES] Added rule: {rule.id}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule (cannot remove owner rules)."""
        if rule_id in self._rules:
            rule = self._rules[rule_id]
            if rule.source == "owner":
                logger.error(f"[RULES] Cannot remove owner rule: {rule_id}")
                return False
            del self._rules[rule_id]
            logger.info(f"[RULES] Removed rule: {rule_id}")
            return True
        return False
    
    def display_rules(self) -> str:
        """Get a human-readable display of all rules."""
        lines = ["=" * 60]
        lines.append("USER RULES REGISTRY")
        lines.append("=" * 60)
        lines.append("")
        
        for rule in self.get_all_rules():
            lines.append(f"[{rule.source.upper()}] {rule.name} (priority: {rule.priority})")
            lines.append(f"  Type: {rule.rule_type}")
            lines.append(f"  {rule.description}")
            lines.append("")
        
        lines.append("=" * 60)
        return "\n".join(lines)


# Global instance
_rules_registry = None


def get_rules_registry() -> UserRulesRegistry:
    """Get the global rules registry."""
    global _rules_registry
    if _rules_registry is None:
        _rules_registry = UserRulesRegistry()
    return _rules_registry


def enforce_user_rules(content: str) -> str:
    """Apply all user rules to content."""
    return get_rules_registry().enforce_rules(content)


def get_rules_prompt_injection() -> str:
    """Get text to inject into AI prompts."""
    return get_rules_registry().get_prompt_injection()


def display_all_rules() -> str:
    """Display all active rules."""
    return get_rules_registry().display_rules()



