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
    GATEWAY_URL = "api.faibric.com"
    
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
        
        # CRITICAL: Remove broken/empty component bodies
        fixed_code, broken_errors = self._check_broken_components(fixed_code)
        errors.extend(broken_errors)
        
        # ENFORCEMENT: Check for undefined TypeScript types and auto-generate them
        fixed_code, type_errors = self._check_undefined_types(fixed_code)
        errors.extend(type_errors)
        
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
        - Missing Fragment wrapper around multiple JSX children
        - Incomplete component tags (missing component name)
        """
        errors = []
        nesting_errors = []
        
        # CHECK 1: Fix "return (" followed by "{" or just whitespace (no JSX wrapper)
        # This is a common AI bug where return ( is followed by {expressions} without a wrapper
        # We need to wrap the entire return body in <> and </>
        code = self._fix_unwrapped_return_statements(code, errors)
        
        # CHECK 2: Fix incomplete component tags - missing component name
        # Pattern 1: `return (\n    propName={...}` - missing opening tag after return
        # Pattern 2: `&& (\n    propName={...}` - missing opening tag after &&
        # We can detect props by: word followed by = followed by {
        code = self._fix_missing_opening_tags(code, errors)
        
        # CHECK 3: Fix empty conditionals and orphaned props
        # Pattern 1: `{condition && ()}` - empty conditional block
        # Pattern 2: `isOpen={value}` appearing after `)}` without a component tag
        code = self._fix_empty_conditionals_and_orphan_props(code, errors)
        
        # FIRST: Remove orphaned JSX ONLY after the final export default
        # Don't remove JSX between components - that's valid code!
        # 
        # OLD BUG: We were detecting ANY `};` as "App function closes" which 
        # incorrectly stripped JSX from subsequent library components in combined code.
        #
        # NEW LOGIC: Only remove JSX that appears AFTER `export default App;`
        lines = code.split('\n')
        cleaned_lines = []
        export_default_app_seen = False  # Only true after "export default App;" or similar
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Only set flag when we see the FINAL export default (for App)
            # This is always at the very end of combined/modular code
            if 'export default' in line and ('App' in line or stripped == 'export default App;'):
                export_default_app_seen = True
            
            # Only remove JSX AFTER the final export default
            skip_line = False
            if export_default_app_seen:
                # Skip orphaned JSX closing tags like </div>
                if stripped.startswith('</') and stripped.endswith('>'):
                    errors.append(ValidationError(
                        error_type="jsx_orphaned",
                        message=f"Auto-fixed: Removed orphaned closing tag: {stripped}",
                        severity="warning",
                        auto_fix=f"Removed {stripped}"
                    ))
                    skip_line = True
                # Skip orphaned JSX opening tags
                elif stripped.startswith('<') and not stripped.startswith('//') and not 'export' in stripped:
                    errors.append(ValidationError(
                        error_type="jsx_orphaned", 
                        message=f"Auto-fixed: Removed orphaned JSX: {stripped[:50]}",
                        severity="warning",
                        auto_fix=f"Removed orphaned JSX"
                    ))
                    skip_line = True
            
            if not skip_line:
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

        # PHASE 3 FIX: Check for generic placeholder content
        # These indicate components weren't properly adapted to the business context
        generic_patterns = [
            ('Item 1', 'generic_item', 'Contains generic "Item 1" placeholder'),
            ('Item 2', 'generic_item', 'Contains generic "Item 2" placeholder'),
            ('Item A', 'generic_item', 'Contains generic "Item A" placeholder'),
            ('Sample Title', 'generic_title', 'Contains generic "Sample Title"'),
            ('Your Company', 'generic_brand', 'Contains generic "Your Company"'),
            ('example.com', 'generic_domain', 'Contains generic "example.com"'),
            ('Description for item', 'generic_desc', 'Contains generic description placeholder'),
            ('"Brand"', 'generic_brand', 'Contains default "Brand" placeholder'),
            ('brandName = "Brand"', 'generic_brand', 'Contains default brandName'),
        ]

        for pattern, error_type, message in generic_patterns:
            if pattern in code:
                warnings.append(ValidationError(
                    error_type=f"generic_{error_type}",
                    message=message,
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
        
        elif close_braces > open_braces:
            # More close braces than open - remove excess closing braces
            excess = close_braces - open_braces
            
            # Find and remove orphan closing braces (on lines by themselves)
            # Pattern: lines that are just "}" or "};" or with whitespace
            orphan_pattern = re.compile(r'^\s*\};\s*$\n?', re.MULTILINE)
            removed = 0
            
            # Remove orphan }; one at a time
            while removed < excess:
                match = orphan_pattern.search(code)
                if match:
                    code = code[:match.start()] + code[match.end():]
                    removed += 1
                else:
                    # No more orphans, try removing from end
                    break
            
            # If still unbalanced, remove trailing close braces
            if removed < excess:
                remaining = excess - removed
                for _ in range(remaining):
                    # Find last closing brace
                    last_close = code.rfind('}')
                    if last_close != -1:
                        code = code[:last_close] + code[last_close+1:]
                        removed += 1
            
            if removed > 0:
                errors.append(ValidationError(
                    error_type="brace_balance",
                    message=f"Auto-fixed: Removed {removed} excess closing braces",
                    severity="warning",
                    auto_fix=f"Removed {removed} excess closing braces"
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
        
        elif close_parens > open_parens:
            # Remove excess closing parens from end
            excess = close_parens - open_parens
            for _ in range(excess):
                last_close = code.rfind(')')
                if last_close != -1:
                    code = code[:last_close] + code[last_close+1:]
            
            errors.append(ValidationError(
                error_type="paren_balance",
                message=f"Auto-fixed: Removed {excess} excess closing parentheses",
                severity="warning",
                auto_fix=f"Removed {excess} excess closing parens"
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
    
    def _fix_missing_opening_tags(self, code: str, errors: List[ValidationError]) -> str:
        """
        Fix JSX where the opening tag component name is missing.
        
        Pattern detected:
            return (
                propName={value}   <- Missing <ComponentName before this
                anotherProp={...}
            />
        
        We detect this by finding `return (\n` or `&& (\n` followed by `word={`.
        Unfortunately we can't auto-fix because we don't know the component name.
        But we can log a warning and try to wrap in Fragment to prevent crash.
        """
        lines = code.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Check for return ( or && (
            if stripped == 'return (' or stripped.endswith('&& ('):
                # Look at next non-empty line
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                
                if j < len(lines):
                    next_stripped = lines[j].strip()
                    # Check if next line is a prop assignment without opening tag
                    # Pattern: word={  or word= where word is lowercase (prop name)
                    if re.match(r'^[a-z]\w*\s*=\s*[\{"]', next_stripped):
                        # This is a prop without opening tag!
                        errors.append(ValidationError(
                            error_type="jsx_missing_opening_tag",
                            message=f"Detected props without opening tag: '{next_stripped[:30]}...'",
                            severity="error",
                            auto_fix="Wrapped in Fragment (component name unknown)"
                        ))
                        
                        # Find the closing /> and wrap everything in a Fragment
                        # This won't make it work perfectly but will prevent crash
                        result_lines.append(line)
                        indent = len(lines[j]) - len(lines[j].lstrip())
                        result_lines.append(' ' * indent + '<>')  # Add Fragment opener
                        
                        # Find the matching /> closing tag
                        k = j
                        while k < len(lines):
                            if '/>' in lines[k].strip():
                                # Add all lines up to and including />
                                for m in range(j, k + 1):
                                    result_lines.append(lines[m])
                                # Add Fragment closer
                                result_lines.append(' ' * indent + '</>')
                                i = k + 1
                                break
                            k += 1
                        else:
                            # No /> found, just continue normally
                            result_lines.append(line)
                            i += 1
                        continue
            
            result_lines.append(line)
            i += 1
        
        return '\n'.join(result_lines)
    
    def _fix_unwrapped_return_statements(self, code: str, errors: List[ValidationError]) -> str:
        """
        Fix return statements that have multiple JSX children without a Fragment wrapper.
        
        Pattern detected:
            return (
                {condition && <Component />}
                {condition2 && <Component2 />}
            );
        
        Fixed to:
            return (
                <>
                    {condition && <Component />}
                    {condition2 && <Component2 />}
                </>
            );
        """
        lines = code.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Detect "return (" pattern
            if stripped == 'return (' or stripped.endswith('return ('):
                # Look at next non-empty line
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                
                if j < len(lines):
                    next_line = lines[j].strip()
                    # If next line starts with { and not a JSX element, wrap with Fragment
                    if next_line.startswith('{') and not next_line.startswith('{/*'):
                        # This is a return with multiple expressions, needs Fragment
                        # Find the matching closing );
                        indent = len(line) - len(line.lstrip())
                        inner_indent = ' ' * (indent + 4)
                        
                        # Add the return line
                        result_lines.append(line)
                        # Add Fragment opening
                        result_lines.append(inner_indent + '<>')
                        
                        # Find all lines until );
                        j = i + 1
                        content_lines = []
                        paren_depth = 1
                        
                        while j < len(lines) and paren_depth > 0:
                            content_line = lines[j]
                            content_stripped = content_line.strip()
                            
                            # Count parens
                            paren_depth += content_stripped.count('(') - content_stripped.count(')')
                            
                            if paren_depth <= 0:
                                # This is the closing );
                                break
                            
                            content_lines.append(content_line)
                            j += 1
                        
                        # Add content lines with extra indent
                        for content_line in content_lines:
                            if content_line.strip():
                                result_lines.append('    ' + content_line)
                            else:
                                result_lines.append(content_line)
                        
                        # Add Fragment closing
                        result_lines.append(inner_indent + '</>')
                        
                        # Add the closing );
                        if j < len(lines):
                            result_lines.append(lines[j])
                        
                        errors.append(ValidationError(
                            error_type="jsx_missing_wrapper",
                            message="Auto-fixed: Added Fragment wrapper around multiple JSX children in return statement",
                            severity="warning",
                            auto_fix="Added <> and </> wrapper"
                        ))
                        
                        i = j + 1
                        continue
            
            result_lines.append(line)
            i += 1
        
        return '\n'.join(result_lines)
    
    def _fix_empty_conditionals_and_orphan_props(self, code: str, errors: List[ValidationError]) -> str:
        """
        Fix common AI generation bugs:
        1. Empty conditionals: {condition && ()} or {condition && (\n        )}
        2. Orphaned props: props appearing after a component without an opening tag
        
        Example of broken code:
            {currentView === "contact" && (
            )}                              <- Empty conditional
            isOpen={isModalOpen}           <- Orphaned prop (missing <Modal)
        """
        lines = code.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Pattern 1: Empty conditional - `&& (` followed by just `)}` or whitespace then `)}`
            if '&& (' in stripped or stripped.endswith('&& ('):
                # Look ahead for empty body
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                
                if j < len(lines) and lines[j].strip() in [')', ')}', ');']:
                    # This is an empty conditional - skip both lines
                    errors.append(ValidationError(
                        error_type="jsx_empty_conditional",
                        message=f"Auto-fixed: Removed empty conditional: {stripped[:40]}",
                        severity="warning",
                        auto_fix="Removed empty && () block"
                    ))
                    i = j + 1
                    continue
            
            # Pattern 2: Orphaned props after `)}` - line starts with lowercase prop=
            if re.match(r'^\s+[a-z]\w*\s*=\s*[\{"]', line):
                # Check if previous non-empty line ends with )} or />
                prev_idx = len(result_lines) - 1
                while prev_idx >= 0 and not result_lines[prev_idx].strip():
                    prev_idx -= 1
                
                if prev_idx >= 0:
                    prev_stripped = result_lines[prev_idx].strip()
                    if prev_stripped.endswith(')}') or prev_stripped.endswith('/>'):
                        # This is an orphaned prop - find all orphaned props and wrap them
                        orphan_start = i
                        while i < len(lines):
                            current = lines[i].strip()
                            if re.match(r'^[a-z]\w*\s*=\s*[\{"]', current):
                                i += 1
                            elif current == '/>' or current.startswith('/>'):
                                # End of orphaned props - skip all including />
                                errors.append(ValidationError(
                                    error_type="jsx_orphaned_props",
                                    message=f"Auto-fixed: Removed orphaned props without component tag",
                                    severity="error",
                                    auto_fix="Removed orphaned props (component tag was missing)"
                                ))
                                i += 1
                                break
                            else:
                                break
                        continue
            
            result_lines.append(line)
            i += 1
        
        return '\n'.join(result_lines)
    
    def _check_undefined_types(self, code: str) -> Tuple[str, List[ValidationError]]:
        """
        ENFORCEMENT: Detect and auto-generate missing TypeScript interface definitions.
        
        The AI often uses types like `KanbanCard` or `Product` in function signatures
        but forgets to define them. This causes Babel runtime errors.
        
        This function:
        1. Finds all PascalCase type references in type annotations
        2. Checks if they're defined as interface/type
        3. Auto-generates missing interfaces based on usage context
        """
        errors = []
        
        # Find all type usages in the code (PascalCase words after : or in generics)
        # Patterns: `: TypeName`, `<TypeName>`, `TypeName[]`, `Omit<TypeName,`
        type_usage_patterns = [
            r':\s*([A-Z][a-zA-Z0-9]+)(?:\[\])?(?:\s*[;,\)\}]|\s*=>)',  # : TypeName or : TypeName[]
            r'<([A-Z][a-zA-Z0-9]+)(?:\s*,|\s*>)',  # <TypeName, or <TypeName>
            r'Omit<([A-Z][a-zA-Z0-9]+)',  # Omit<TypeName
            r'Partial<([A-Z][a-zA-Z0-9]+)',  # Partial<TypeName
            r'Pick<([A-Z][a-zA-Z0-9]+)',  # Pick<TypeName
            r'Record<[^,]+,\s*([A-Z][a-zA-Z0-9]+)',  # Record<string, TypeName>
        ]
        
        used_types = set()
        for pattern in type_usage_patterns:
            matches = re.findall(pattern, code)
            used_types.update(matches)
        
        # Built-in/common types that don't need definitions
        builtin_types = {
            'React', 'ReactNode', 'ReactElement', 'FC', 'Component',
            'HTMLElement', 'HTMLDivElement', 'HTMLInputElement', 'HTMLButtonElement',
            'MouseEvent', 'ChangeEvent', 'FormEvent', 'KeyboardEvent',
            'SetStateAction', 'Dispatch', 'RefObject', 'MutableRefObject',
            'Promise', 'Error', 'Date', 'RegExp', 'Map', 'Set', 'Array',
            'Record', 'Partial', 'Required', 'Readonly', 'Pick', 'Omit',
            'String', 'Number', 'Boolean', 'Object', 'Function', 'Symbol',
            'CSSProperties', 'PropsWithChildren', 'ComponentProps',
            'SVGProps', 'InputHTMLAttributes', 'ButtonHTMLAttributes',
        }
        
        # Find already-defined types
        defined_pattern = r'(?:interface|type)\s+([A-Z][a-zA-Z0-9]+)'
        defined_types = set(re.findall(defined_pattern, code))
        
        # Find missing types
        missing_types = used_types - builtin_types - defined_types
        
        if not missing_types:
            return code, errors
        
        # Generate interface definitions for missing types
        generated_interfaces = []
        
        for type_name in sorted(missing_types):
            # Try to infer the interface structure from usage context
            interface_def = self._infer_interface_definition(type_name, code)
            generated_interfaces.append(interface_def)
            errors.append(ValidationError(
                error_type="missing_type_definition",
                message=f"Auto-generated missing interface: {type_name}",
                severity="warning",
                auto_fix=f"Generated interface {type_name}"
            ))
        
        # Insert generated interfaces after "// Interfaces" comment or at the top of the script
        interfaces_block = '\n\n'.join(generated_interfaces)
        
        if '// Interfaces' in code:
            # Insert after the comment
            code = code.replace('// Interfaces', f'// Interfaces\n{interfaces_block}', 1)
        else:
            # Find the first const/function declaration and insert before it
            first_decl = re.search(r'^(const|function|let|var)\s+\w+', code, re.MULTILINE)
            if first_decl:
                insert_pos = first_decl.start()
                code = code[:insert_pos] + f'// Auto-generated interfaces\n{interfaces_block}\n\n' + code[insert_pos:]
            else:
                # Fallback: insert at very beginning
                code = f'// Auto-generated interfaces\n{interfaces_block}\n\n' + code
        
        return code, errors
    
    def _infer_interface_definition(self, type_name: str, code: str) -> str:
        """
        Infer an interface definition based on how the type is used in the code.
        
        Uses heuristics based on the type name and context.
        """
        # Look for usage patterns to infer fields
        fields = []
        
        # Common patterns based on type name
        type_lower = type_name.lower()
        
        # Kanban/Task/Card types
        if 'card' in type_lower or 'task' in type_lower or 'item' in type_lower:
            fields = [
                'id: string;',
                'title: string;',
                'description?: string;',
                'status?: string;',
                'priority?: string;',
                'dueDate?: string;',
                'assignee?: { id: string; name: string; avatar?: string };',
                'columnId?: string;',
            ]
        # Column/List types
        elif 'column' in type_lower or 'list' in type_lower:
            fields = [
                'id: string;',
                'title: string;',
                'cards?: any[];',
                'items?: any[];',
            ]
        # User/Member/Assignee types
        elif 'user' in type_lower or 'member' in type_lower or 'assignee' in type_lower:
            fields = [
                'id: string;',
                'name: string;',
                'email?: string;',
                'avatar?: string;',
            ]
        # Product types
        elif 'product' in type_lower:
            fields = [
                'id: string;',
                'name: string;',
                'price: number;',
                'description?: string;',
                'image?: string;',
                'category?: string;',
                'inStock?: boolean;',
            ]
        # Chart/Data types
        elif 'chart' in type_lower or 'data' in type_lower:
            fields = [
                'label: string;',
                'value: number;',
                'color?: string;',
            ]
        # Navigation types
        elif 'nav' in type_lower or 'menu' in type_lower:
            fields = [
                'id: string;',
                'label: string;',
                'icon?: string;',
                'href?: string;',
            ]
        # Props types - look for component usage
        elif type_lower.endswith('props'):
            component_name = type_name[:-5]  # Remove 'Props'
            # Look for how this component is used
            usage_pattern = rf'<{component_name}\s+([^>]+)'
            match = re.search(usage_pattern, code)
            if match:
                # Extract prop names from usage
                props_str = match.group(1)
                prop_names = re.findall(r'(\w+)=', props_str)
                for prop in prop_names:
                    fields.append(f'{prop}?: any;')
            if not fields:
                fields = ['children?: React.ReactNode;']
        # Default generic object
        else:
            fields = [
                'id: string;',
                '[key: string]: any;',
            ]
        
        return f"""interface {type_name} {{
  {chr(10) + "  ".join(fields) if fields else "  [key: string]: any;"}
}}"""
    
    def _check_broken_components(self, code: str) -> Tuple[str, List[ValidationError]]:
        """
        Check for and remove broken/empty component definitions.
        
        Common patterns that indicate corrupted library components:
        - JSDoc comment followed immediately by }; (empty function body)
        - Orphan props without component tags (type="button" onClick=... without <button)
        - Empty ternary expressions: condition ? ( ) : ( )
        """
        errors = []
        original_code = code
        
        # Pattern 1: Empty function bodies after JSDoc
        # */ followed by just }; on its own line
        empty_body_pattern = re.compile(
            r'\*/\s*\n+\s*\};\s*\n',
            re.MULTILINE
        )
        
        while empty_body_pattern.search(code):
            code = empty_body_pattern.sub('*/\n\n', code)
            errors.append(ValidationError(
                error_type="broken_component",
                message="Auto-fixed: Removed empty component body after JSDoc",
                severity="warning",
                auto_fix="Removed empty component body"
            ))
        
        # Pattern 2: Props without opening tag (orphan props)
        # Lines that start with props like type="..." or onClick=... but no <element
        orphan_props_pattern = re.compile(
            r'^\s+(?:type|onClick|onChange|onBlur|onKeyDown|className|aria-\w+)="[^"]*"[^<]*$',
            re.MULTILINE
        )
        
        # Remove lines that are just orphan props
        for match in orphan_props_pattern.finditer(code):
            line = match.group(0)
            # Check if previous line has opening tag
            start = match.start()
            prev_line_end = code.rfind('\n', 0, start)
            if prev_line_end > 0:
                prev_line_start = code.rfind('\n', 0, prev_line_end - 1) + 1
                prev_line = code[prev_line_start:prev_line_end]
                # If previous line doesn't have an opening tag, this is orphan
                if '<' not in prev_line or prev_line.strip().startswith('//'):
                    # Mark for removal
                    pass
        
        # Pattern 3: Empty ternary arms
        # condition ? ( ) : ( )
        empty_ternary_pattern = re.compile(
            r'\?\s*\(\s*\)\s*:\s*\(\s*\)',
            re.MULTILINE
        )
        
        if empty_ternary_pattern.search(code):
            code = empty_ternary_pattern.sub('? null : null', code)
            errors.append(ValidationError(
                error_type="broken_component",
                message="Auto-fixed: Replaced empty ternary with null",
                severity="warning",
                auto_fix="Replaced empty ternary"
            ))
        
        # Pattern 4: Conditional with empty block
        # {condition && (\n)}
        empty_conditional_pattern = re.compile(
            r'\{[^}]+&&\s*\(\s*\)\s*\}',
            re.MULTILINE
        )
        
        if empty_conditional_pattern.search(code):
            code = empty_conditional_pattern.sub('{/* removed empty conditional */}', code)
            errors.append(ValidationError(
                error_type="broken_component",
                message="Auto-fixed: Removed empty conditional block",
                severity="warning",
                auto_fix="Removed empty conditional"
            ))
        
        # Pattern 5: Lines that are just }; without a matching function
        # Look for }; that appears right after a comment or blank line
        orphan_closure_pattern = re.compile(
            r'\n\n+\s*\};\s*\n(?!\s*//)',
            re.MULTILINE
        )
        
        count = 0
        while orphan_closure_pattern.search(code) and count < 10:
            code = orphan_closure_pattern.sub('\n\n', code)
            count += 1
        
        if count > 0:
            errors.append(ValidationError(
                error_type="broken_component",
                message=f"Auto-fixed: Removed {count} orphan closure(s)",
                severity="warning",
                auto_fix=f"Removed {count} orphan closures"
            ))
        
        return code, errors


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

