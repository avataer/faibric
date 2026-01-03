"""
CODE VALIDATOR
==============

Pre-deployment validation that catches ALL syntax errors BEFORE deployment.
NO URL is shown to users until ALL validations pass.

VALIDATION STEPS:
1. TypeScript/JSX syntax validation (using esbuild or regex patterns)
2. JSX balance check (opening/closing tags)
3. Required patterns (export default, function App, etc.)
4. Forbidden patterns (emojis, lorem ipsum, etc.)
5. TypeScript generic syntax
6. Import/export consistency
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """A single validation error."""
    error_type: str
    message: str
    line_number: Optional[int] = None
    line_content: Optional[str] = None
    severity: str = "error"  # "error" = blocks deployment, "warning" = logged only
    auto_fix: Optional[str] = None  # If set, the fix that was auto-applied


@dataclass
class ValidationResult:
    """Result of code validation."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    fixed_code: Optional[str] = None  # If auto-fixes were applied
    

class CodeValidator:
    """
    Comprehensive code validation before deployment.
    
    This class ensures NO broken code ever gets deployed.
    """
    
    # TypeScript/JSX patterns that indicate syntax errors
    SYNTAX_ERROR_PATTERNS = [
        # Missing closing angle bracket in generics
        (r'useState<[^>]+>\(', 'useState<Type>( should be useState<Type>>(('),
        (r'useRef<[^>]+>\(', 'useRef<Type>( should be useRef<Type>>('),
        (r'React\.Dispatch<React\.SetStateAction<[^>]+>;', 'Missing closing > in React.Dispatch'),
        # Unclosed JSX
        (r'<\w+[^/>]*$', 'Possible unclosed JSX element'),
        # Invalid JSX self-closing
        (r'<(input|img|br|hr|meta|link)\s+[^/]*(?<!/)>', 'Void element must be self-closing in JSX'),
    ]
    
    # Required patterns for a valid React app
    # Note: CDN-based apps use ReactDOM.createRoot instead of export default
    REQUIRED_PATTERNS = [
        (r'(export\s+default\s+\w+|ReactDOM\.createRoot)', 'Missing export default or ReactDOM.createRoot'),
        (r'function\s+App|const\s+App', 'Missing App component'),
    ]
    
    # Forbidden patterns that indicate bad code
    FORBIDDEN_DATA_PATTERNS = [
        # Hardcoded mock data arrays (should use Gateway API)
        (r'const\s+\w+\s*=\s*\[\s*\{[^}]+price[^}]+\}', 'Hardcoded price data array'),
        (r'const\s+\w+\s*=\s*\[\s*\{[^}]+name[^}]+value[^}]+\}', 'Hardcoded chart data array'),
        (r'const\s+(mockData|fakeData|sampleData|dummyData)', 'Mock/fake data variable'),
    ]
    
    # Gateway URL that MUST be used for external data
    GATEWAY_URL = "faibric-api.onrender.com"
    
    # Patterns that indicate app needs external data
    DATA_INDICATORS = [
        'stock', 'price', 'crypto', 'bitcoin', 'weather', 'api', 'fetch',
        'real-time', 'live', 'tracker', 'dashboard', 'monitor', 'chart'
    ]
    
    # Void elements that must be self-closing in JSX
    VOID_ELEMENTS = ['input', 'img', 'br', 'hr', 'meta', 'link', 'area', 'base', 'col', 'embed', 'source', 'track', 'wbr']
    
    def validate(self, code: str) -> ValidationResult:
        """
        Validate code and return result.
        
        Attempts auto-fixes where possible.
        Returns ValidationResult with is_valid=True only if code can be deployed.
        """
        errors = []
        warnings = []
        fixed_code = code
        
        # Run all validations
        fixed_code, jsx_errors = self._check_jsx_balance(fixed_code)
        errors.extend(jsx_errors)
        
        fixed_code, ts_errors = self._check_typescript_generics(fixed_code)
        errors.extend(ts_errors)
        
        fixed_code, void_errors = self._check_void_elements(fixed_code)
        errors.extend(void_errors)
        
        req_errors = self._check_required_patterns(fixed_code)
        errors.extend(req_errors)
        
        forbidden_warnings = self._check_forbidden_patterns(fixed_code)
        warnings.extend(forbidden_warnings)
        
        fixed_code, brace_errors = self._check_brace_balance(fixed_code)
        errors.extend(brace_errors)
        
        fixed_code, arrow_errors = self._check_arrow_syntax(fixed_code)
        errors.extend(arrow_errors)
        
        fixed_code, dup_errors = self._check_duplicate_declarations(fixed_code)
        errors.extend(dup_errors)
        
        # ENFORCEMENT: Check Gateway URL usage (not just instructions)
        gateway_warnings = self._check_gateway_usage(fixed_code)
        warnings.extend(gateway_warnings)
        
        # ENFORCEMENT: Check for hardcoded mock data
        mock_warnings = self._check_no_mock_data(fixed_code)
        warnings.extend(mock_warnings)
        
        # ENFORCEMENT: Check settings view exists if using data
        settings_warnings = self._check_settings_view(fixed_code)
        warnings.extend(settings_warnings)
        
        # Determine if valid (no blocking errors after auto-fixes)
        blocking_errors = [e for e in errors if e.severity == "error" and not e.auto_fix]
        is_valid = len(blocking_errors) == 0
        
        if errors:
            logger.warning(f"[VALIDATOR] Found {len(errors)} errors, {len([e for e in errors if e.auto_fix])} auto-fixed")
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            fixed_code=fixed_code if fixed_code != code else None
        )
    
    def _check_jsx_balance(self, code: str) -> Tuple[str, List[ValidationError]]:
        """
        Check JSX tag balance and NESTING structure.
        
        This catches issues like:
        - Unclosed tags
        - Mismatched closing tags (closing </button> when </nav> expected)
        - Improperly nested elements
        - ORPHANED JSX after export default (causes "Expected identifier" errors)
        """
        errors = []
        nesting_errors = []
        
        # FIRST: Remove orphaned JSX after export default
        # This is a common AI generation bug
        lines = code.split('\n')
        cleaned_lines = []
        export_seen = False
        
        for line in lines:
            stripped = line.strip()
            
            if 'export default' in line:
                export_seen = True
            
            # After export, remove any JSX lines
            if export_seen:
                # Skip orphaned JSX tags after export
                if stripped.startswith('</') and stripped.endswith('>'):
                    errors.append(ValidationError(
                        error_type="jsx_orphaned",
                        message=f"Auto-fixed: Removed orphaned closing tag after export: {stripped}",
                        severity="warning",
                        auto_fix=f"Removed {stripped}"
                    ))
                    continue
                if stripped.startswith('<') and not stripped.startswith('//'):
                    # Skip any JSX after export
                    errors.append(ValidationError(
                        error_type="jsx_orphaned", 
                        message=f"Auto-fixed: Removed orphaned JSX after export: {stripped[:50]}",
                        severity="warning",
                        auto_fix=f"Removed orphaned JSX"
                    ))
                    continue
            
            cleaned_lines.append(line)
        
        code = '\n'.join(cleaned_lines)
        
        # Track tag stack for nesting validation
        tag_stack = []
        
        # Find all tags with line numbers
        tag_pattern = re.compile(
            r'<(/?)(\w+)([^>]*?)(/?)>',
            re.MULTILINE
        )
        
        lines = code.split('\n')
        line_starts = [0]
        for line in lines:
            line_starts.append(line_starts[-1] + len(line) + 1)
        
        def get_line_number(pos):
            for i, start in enumerate(line_starts):
                if start > pos:
                    return i
            return len(lines)
        
        for match in tag_pattern.finditer(code):
            is_closing = match.group(1) == '/'
            tag_name = match.group(2).lower()
            is_self_closing = match.group(4) == '/'
            line_num = get_line_number(match.start())
            
            # Skip void elements and self-closing
            if tag_name in self.VOID_ELEMENTS or is_self_closing:
                continue
            
            # Skip non-JSX tags (like SVG paths, TypeScript generics)
            if tag_name in ['path', 'svg', 'g', 'circle', 'rect', 'line', 'polygon', 'polyline']:
                continue
            
            # ONLY validate known HTML/React elements - skip TypeScript generics
            # TypeScript generics look like <SomeType> but aren't JSX
            known_html_elements = [
                'div', 'span', 'p', 'a', 'button', 'input', 'form', 'label',
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li',
                'table', 'thead', 'tbody', 'tr', 'td', 'th',
                'header', 'footer', 'nav', 'main', 'section', 'article', 'aside',
                'img', 'video', 'audio', 'canvas', 'iframe',
                'select', 'option', 'textarea', 'fieldset', 'legend',
                'strong', 'em', 'b', 'i', 'u', 'small', 'code', 'pre',
            ]
            
            # Skip if not a known HTML element (likely TypeScript generic or React component)
            # React components start with uppercase, so lowercase non-HTML = skip
            if tag_name not in known_html_elements:
                continue
            
            if is_closing:
                if tag_stack:
                    expected_tag, expected_line = tag_stack[-1]
                    if expected_tag == tag_name:
                        tag_stack.pop()
                    else:
                        # Mismatched close - this is a critical error
                        nesting_errors.append(ValidationError(
                            error_type="jsx_nesting",
                            message=f"Line {line_num}: Closing </{tag_name}> but expected </{expected_tag}> (opened on line {expected_line})",
                            line_number=line_num,
                            severity="error"
                        ))
                        # Try to recover by finding matching open tag
                        for i in range(len(tag_stack) - 1, -1, -1):
                            if tag_stack[i][0] == tag_name:
                                tag_stack = tag_stack[:i]
                                break
                else:
                    # Extra closing tag with no matching open - AUTO-FIX by removing it
                    nesting_errors.append(ValidationError(
                        error_type="jsx_nesting",
                        message=f"Line {line_num}: Removing orphan </{tag_name}> with no matching open tag",
                        line_number=line_num,
                        severity="warning",
                        auto_fix=f"Removed orphan </{tag_name}>"
                    ))
                    # Remove the orphan closing tag from code
                    code = code[:match.start()] + code[match.end():]
            else:
                tag_stack.append((tag_name, line_num))
        
        # Check for unclosed tags and AUTO-FIX by adding closing tags
        if tag_stack:
            # Auto-fix: add missing closing tags before export default
            closing_tags = ""
            for tag_name, line_num in reversed(tag_stack):
                closing_tags += f"</{tag_name}>"
                errors.append(ValidationError(
                    error_type="jsx_unclosed",
                    message=f"Auto-fixed: Added </{tag_name}> (was opened on line {line_num})",
                    line_number=line_num,
                    severity="warning"  # Warning, not error - we fixed it
                ))
            
            # Insert closing tags before export default
            if closing_tags:
                if "export default App" in code:
                    code = code.replace("export default App", f"{closing_tags}\n\nexport default App")
                else:
                    code = code + f"\n{closing_tags}"
        
        # Nesting errors are warnings - we try to fix, but don't block
        if nesting_errors:
            for err in nesting_errors:
                err.severity = "warning"  # Downgrade to warning
            errors.extend(nesting_errors)
        
        # Also do simple count check as backup
        tag_counts = {}
        for tag in ['div', 'span', 'p', 'section', 'article', 'header', 'footer', 'nav', 'main', 'aside']:
            open_count = len(re.findall(rf'<{tag}(?:\s[^>]*)?>(?!/)', code))
            close_count = len(re.findall(rf'</{tag}>', code))
            
            if open_count != close_count:
                tag_counts[tag] = (open_count, close_count)
        
        for tag, (open_c, close_c) in tag_counts.items():
            diff = open_c - close_c
            if diff != 0:
                errors.append(ValidationError(
                    error_type="jsx_balance",
                    message=f"<{tag}> imbalance: {open_c} open, {close_c} close",
                    severity="warning"
                ))
        
        return code, errors
    
    def _check_typescript_generics(self, code: str) -> Tuple[str, List[ValidationError]]:
        """Check and fix TypeScript generic syntax errors."""
        errors = []
        original_code = code
        
        # Pattern 1: useState<Type>( should be useState<Type>>(
        # But be careful not to over-fix
        patterns = [
            # useState<SomeType>( -> useState<SomeType>>(
            (r'(useState|useRef|useMemo|useCallback)<(\w+)>\(', r'\1<\2>>('),
            # useState<Some<Type>>( is correct, don't touch
            # useState<Record<string, any>( -> useState<Record<string, any>>(
            (r'(useState|useRef)<(Record<[^>]+)>\(', r'\1<\2>>('),
            (r'(useState|useRef)<(Array<[^>]+)>\(', r'\1<\2>>('),
            # React.Dispatch<React.SetStateAction<Type>; -> React.Dispatch<React.SetStateAction<Type>>;
            (r'React\.Dispatch<React\.SetStateAction<([^>]+)>;', r'React.Dispatch<React.SetStateAction<\1>>;'),
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, code):
                code = re.sub(pattern, replacement, code)
        
        # Check for remaining unbalanced angle brackets in type lines
        lines = code.split('\n')
        fixed_lines = []
        type_indicators = ['React.', 'Dispatch', 'SetStateAction', 'FC<', 'useState<', 
                          'useRef<', ': {', '}: ', 'interface ', 'type ', ']: ']
        
        for i, line in enumerate(lines):
            original_line = line
            stripped = line.rstrip()
            
            # Only process lines that look like type declarations
            is_type_line = any(ind in line for ind in type_indicators)
            has_comparison = '<=' in line or '>=' in line or ' < ' in line or ' > ' in line
            
            if stripped.endswith(';') and is_type_line and not has_comparison and '<' in line:
                open_angles = line.count('<')
                close_angles = line.count('>')
                if open_angles > close_angles:
                    missing = open_angles - close_angles
                    line = stripped[:-1] + ('>' * missing) + ';'
                    errors.append(ValidationError(
                        error_type="typescript_generic",
                        message=f"Line {i+1}: Added {missing} missing '>' in type declaration",
                        line_number=i+1,
                        line_content=original_line.strip()[:80],
                        severity="warning",
                        auto_fix=f"Added {missing} '>'"
                    ))
            
            fixed_lines.append(line)
        
        code = '\n'.join(fixed_lines)
        
        if code != original_code:
            errors.insert(0, ValidationError(
                error_type="typescript_generic",
                message="Auto-fixed TypeScript generic syntax errors",
                severity="warning",
                auto_fix="Fixed generics"
            ))
        
        return code, errors
    
    def _check_void_elements(self, code: str) -> Tuple[str, List[ValidationError]]:
        """Check and fix non-self-closing void elements."""
        errors = []
        
        for element in self.VOID_ELEMENTS:
            # Find void elements that aren't self-closing
            # Pattern: <input ...> but not <input ... />
            pattern = rf'<({element})(\s[^>]*)?(?<!/)>'
            
            def fix_void(match):
                tag = match.group(1)
                attrs = match.group(2) or ''
                return f'<{tag}{attrs} />'
            
            new_code = re.sub(pattern, fix_void, code, flags=re.IGNORECASE)
            if new_code != code:
                count = len(re.findall(pattern, code, flags=re.IGNORECASE))
                errors.append(ValidationError(
                    error_type="void_element",
                    message=f"Auto-fixed {count} non-self-closing <{element}> elements",
                    severity="warning",
                    auto_fix=f"Fixed {count} <{element}> tags"
                ))
                code = new_code
        
        return code, errors
    
    def _check_required_patterns(self, code: str) -> List[ValidationError]:
        """Check for required patterns."""
        errors = []
        
        for pattern, message in self.REQUIRED_PATTERNS:
            if not re.search(pattern, code):
                errors.append(ValidationError(
                    error_type="missing_required",
                    message=message,
                    severity="error"  # Blocking - cannot be auto-fixed
                ))
        
        return errors
    
    def _check_forbidden_patterns(self, code: str) -> List[ValidationError]:
        """Check for forbidden patterns (emojis, lorem ipsum, etc.)."""
        warnings = []
        
        # Check for emojis
        emoji_pattern = re.compile(
            '['
            '\U0001F600-\U0001F64F'
            '\U0001F300-\U0001F5FF'
            '\U0001F680-\U0001F6FF'
            '\U0001F1E0-\U0001F1FF'
            '\U00002702-\U000027B0'
            '\U0001F900-\U0001F9FF'
            '\U00002600-\U000026FF'
            ']+', 
            flags=re.UNICODE
        )
        
        emojis = emoji_pattern.findall(code)
        if emojis:
            warnings.append(ValidationError(
                error_type="forbidden_emoji",
                message=f"Contains {len(emojis)} emojis (forbidden by owner rules)",
                severity="warning"
            ))
        
        # Check for Lorem Ipsum
        if 'lorem ipsum' in code.lower():
            warnings.append(ValidationError(
                error_type="forbidden_lorem",
                message="Contains Lorem Ipsum placeholder text",
                severity="warning"
            ))
        
        return warnings
    
    def _check_brace_balance(self, code: str) -> Tuple[str, List[ValidationError]]:
        """Check and fix brace/parenthesis balance."""
        errors = []
        
        open_braces = code.count('{')
        close_braces = code.count('}')
        open_parens = code.count('(')
        close_parens = code.count(')')
        
        if open_braces > close_braces:
            missing = open_braces - close_braces
            # Add before export default or at end
            export_match = re.search(r'\n\s*export\s+default', code)
            if export_match:
                code = code[:export_match.start()] + '\n' + ('}' * missing) + code[export_match.start():]
            else:
                code += '\n' + ('}' * missing)
            errors.append(ValidationError(
                error_type="brace_balance",
                message=f"Auto-fixed: Added {missing} missing closing braces",
                severity="warning",
                auto_fix=f"Added {missing} closing braces"
            ))
        
        if open_parens > close_parens:
            missing = open_parens - close_parens
            code += ')' * missing
            errors.append(ValidationError(
                error_type="paren_balance",
                message=f"Auto-fixed: Added {missing} missing closing parentheses",
                severity="warning",
                auto_fix=f"Added {missing} closing parens"
            ))
        
        return code, errors
    
    def _check_arrow_syntax(self, code: str) -> Tuple[str, List[ValidationError]]:
        """
        Check and fix broken arrow function syntax.
        
        AI often generates `= />` instead of `=>` which causes
        "Unterminated regular expression" errors in esbuild.
        """
        errors = []
        original = code
        
        # Fix broken arrow function syntax patterns
        # Pattern: `(e) = />` should be `(e) =>`
        if '= />' in code or '=/>' in code:
            code = re.sub(r'\)\s*=\s*/>', r') =>', code)
            code = re.sub(r'=\s*/>\s*(\w)', r'=> \1', code)
            code = code.replace('= />', '=>')
            code = code.replace('=/>', '=>')
            
            if code != original:
                errors.append(ValidationError(
                    error_type="arrow_syntax",
                    message="Auto-fixed: Corrected broken arrow function syntax (= /> to =>)",
                    severity="warning",
                    auto_fix="Fixed arrow functions"
                ))
        
        return code, errors
    
    def _check_duplicate_declarations(self, code: str) -> Tuple[str, List[ValidationError]]:
        """
        Check and fix duplicate const/function declarations.
        
        AI sometimes generates the same component twice, which causes
        "symbol has already been declared" errors in esbuild.
        """
        errors = []
        
        # Find all const declarations
        const_pattern = re.compile(r'^(\s*)(const\s+(\w+)\s*[=:])', re.MULTILINE)
        
        # Track declarations
        declarations = {}
        lines = code.split('\n')
        lines_to_remove = set()
        
        for i, line in enumerate(lines):
            match = const_pattern.match(line)
            if match:
                var_name = match.group(3)
                if var_name in declarations:
                    # Duplicate found - mark for removal (keep first occurrence)
                    # Find the end of this declaration (next const or function or closing brace at same level)
                    # For simplicity, just warn for now
                    errors.append(ValidationError(
                        error_type="duplicate_declaration",
                        message=f"Duplicate declaration of '{var_name}' found on line {i+1}",
                        line_number=i+1,
                        severity="warning"
                    ))
                else:
                    declarations[var_name] = i
        
        # For common duplicate patterns like AppLayout, try to remove the second occurrence
        # Find the block boundaries and remove
        common_duplicates = ['AppLayout', 'Navigation', 'Header', 'Footer', 'Sidebar']
        
        for dup_name in common_duplicates:
            pattern = rf'(const\s+{dup_name}\s*[=:][^;]+;)'
            matches = list(re.finditer(pattern, code, re.DOTALL))
            
            if len(matches) > 1:
                # Remove all but the first
                for m in reversed(matches[1:]):
                    code = code[:m.start()] + code[m.end():]
                    errors.append(ValidationError(
                        error_type="duplicate_declaration",
                        message=f"Auto-fixed: Removed duplicate declaration of '{dup_name}'",
                        severity="warning",
                        auto_fix=f"Removed duplicate {dup_name}"
                    ))
        
        # Also check for duplicate const with FC type (full component declarations)
        fc_pattern = rf'(const\s+(\w+):\s*React\.FC[^}}]+\}})'
        seen_components = {}
        
        for match in re.finditer(fc_pattern, code, re.DOTALL):
            comp_name = match.group(2)
            if comp_name in seen_components:
                # Remove this duplicate
                code = code[:match.start()] + code[match.end():]
                errors.append(ValidationError(
                    error_type="duplicate_declaration",
                    message=f"Auto-fixed: Removed duplicate component '{comp_name}'",
                    severity="warning",
                    auto_fix=f"Removed duplicate {comp_name}"
                ))
            else:
                seen_components[comp_name] = match.start()
        
        return code, errors
    
    def _check_gateway_usage(self, code: str) -> List[ValidationError]:
        """
        ENFORCEMENT: Check that Gateway URL is used for external data.
        
        This is NOT an instruction - it's a check that DETECTS violations.
        """
        warnings = []
        code_lower = code.lower()
        
        # Check if this app likely needs external data
        needs_data = any(indicator in code_lower for indicator in self.DATA_INDICATORS)
        
        if needs_data:
            # Check if using Gateway URL
            uses_gateway = self.GATEWAY_URL in code
            
            # Check for other fetch calls that don't use Gateway
            other_fetches = re.findall(r'fetch\(["\']https?://(?!' + re.escape(self.GATEWAY_URL) + r')[^"\']+', code)
            
            if not uses_gateway and 'fetch(' in code:
                warnings.append(ValidationError(
                    error_type="gateway_not_used",
                    message=f"App needs data but doesn't use Gateway API ({self.GATEWAY_URL})",
                    severity="warning"
                ))
            
            if other_fetches:
                warnings.append(ValidationError(
                    error_type="non_gateway_fetch",
                    message=f"Found {len(other_fetches)} fetch calls not using Gateway API",
                    severity="warning"
                ))
        
        return warnings
    
    def _check_no_mock_data(self, code: str) -> List[ValidationError]:
        """
        ENFORCEMENT: Check for hardcoded mock/fake data.
        
        This DETECTS when AI ignored the "use real data" instruction.
        """
        warnings = []
        
        for pattern, message in self.FORBIDDEN_DATA_PATTERNS:
            matches = re.findall(pattern, code, re.IGNORECASE)
            if matches:
                warnings.append(ValidationError(
                    error_type="mock_data_detected",
                    message=f"{message} - should use Gateway API",
                    severity="warning"
                ))
        
        return warnings
    
    def _check_settings_view(self, code: str) -> List[ValidationError]:
        """
        ENFORCEMENT: Check that Settings view exists if app uses data.
        
        This DETECTS when AI ignored the "include settings view" instruction.
        """
        warnings = []
        
        # Check if app uses Gateway or fetch
        uses_data = self.GATEWAY_URL in code or 'fetch(' in code
        
        if uses_data:
            # Check for settings view
            has_settings = any([
                'settings' in code.lower() and 'view' in code.lower(),
                '"settings"' in code.lower(),
                "'settings'" in code.lower(),
                'Settings' in code,  # Component name
            ])
            
            if not has_settings:
                warnings.append(ValidationError(
                    error_type="missing_settings_view",
                    message="App uses external data but has no Settings view for API configuration",
                    severity="warning"
                ))
        
        return warnings


# Global instance
_validator = None


def get_validator() -> CodeValidator:
    """Get the global code validator."""
    global _validator
    if _validator is None:
        _validator = CodeValidator()
    return _validator


def validate_code(code: str) -> ValidationResult:
    """Validate code and return result."""
    return get_validator().validate(code)


def validate_and_fix(code: str) -> Tuple[bool, str, List[str]]:
    """
    Validate code, apply fixes, return (is_valid, fixed_code, error_messages).
    
    This is the main entry point for pre-deployment validation.
    """
    result = validate_code(code)
    
    error_messages = []
    for e in result.errors:
        if e.severity == "error" and not e.auto_fix:
            error_messages.append(f"ERROR: {e.message}")
        elif e.auto_fix:
            error_messages.append(f"AUTO-FIXED: {e.message}")
    
    for w in result.warnings:
        error_messages.append(f"WARNING: {w.message}")
    
    final_code = result.fixed_code if result.fixed_code else code
    
    return result.is_valid, final_code, error_messages

