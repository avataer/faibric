"""
Component-Based Generation Pipeline

1. Decompose request into building blocks
2. Search library for EACH block
3. Reuse found blocks, generate missing ones
4. Save new blocks to library
5. Compose final app
"""

import json
import logging
import re
import anthropic
from typing import Dict, List, Optional
from django.conf import settings

from .components import (
    ProjectDecomposer,
    ComponentLibrary,
    ComponentComposer,
    ComponentRequirement,
    ComponentType,
)
from .connectors import ComponentInterface
from .standard_interfaces import get_interface, INTERFACE_REGISTRY
from .connection_validator import ConnectionValidator, ValidationLevel, validate_code_quality
from .wire_generator import WireGenerator, generate_wiring_prompt_injection
from .user_rules import enforce_user_rules, get_rules_prompt_injection
from .owner_instructions import enforce_instructions, get_instruction_prompt
from apps.ai_engine.models_config import CODE_MODEL

# Import Connector V2 for deterministic wiring
from .connector_v2.health_check import is_connector_v2_healthy, run_health_check
from .connector_v2.pipeline_integration import compose_app_v2

# Import modular composer (components as separate files)
from .modular_composer import compose_modular

logger = logging.getLogger(__name__)

# Check Connector V2 health on module load
_connector_v2_status = None

# Import TypeScript stripper (in separate file to avoid circular imports)
from .typescript_stripper import strip_typescript_annotations, validate_jsx_tags

# Import complexity detection (Base44 lesson: auto-refactoring triggers)
from .complexity import measure_complexity, get_refactor_prompt_injection, check_and_warn


class JSXValidationError(Exception):
    """
    Raised when generated JSX code fails validation.

    This exception is caught by build_service.py which triggers AI retry.
    The code is NOT deployed until it passes validation.
    """
    def __init__(self, message: str, code: str = None):
        super().__init__(message)
        self.code = code  # The invalid code, for AI to fix


class ComponentGenerationPipeline:
    """
    The RIGHT way to build apps:
    - Decompose into components
    - Reuse from library
    - Generate only what's missing
    - Save new components
    - Compose final app
    """

    def __init__(self, session=None, model_key: str = None):
        self.session = session
        self.decomposer = ProjectDecomposer()
        self.library = ComponentLibrary()
        self.composer = ComponentComposer()
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Model selection - use get_model_id to resolve model key
        from apps.ai_engine.models_config import get_model_id
        self.model = get_model_id(model_key) if model_key else CODE_MODEL
        
        # ═══ CONNECTOR SYSTEM ═══
        self.validator = ConnectionValidator()
        self.wire_generator = WireGenerator()
        
        # Store generated images for deployment
        self.generated_images = {}

        # Stats for tracking
        self.stats = {
            'components_required': 0,
            'components_reused': 0,
            'components_generated': 0,
            'reused_from': [],  # IDs of reused components
            'generated_ids': [],  # IDs of newly generated
            'validation_issues': [],  # Connection validation issues
            'wiring_used': False,  # Whether auto-wiring was applied
        }
        
        # Component files for modular composition
        # Dict mapping filepath to code, e.g., {"src/components/Hero.jsx": "<code>"}
        self.component_files = {}

    def _get_available_scope(self, components: Dict[str, str] = None) -> str:
        """
        Generate a pre-seeded scope definition for the AI.

        Per Base44 lessons: Tell the AI exactly what variables, functions,
        and components are available to prevent undefined reference errors.
        """
        scope_parts = []

        # 1. Standard handlers always available
        scope_parts.append("""
AVAILABLE HANDLERS (use these, do NOT create new undefined handlers):
- handleNavigate(viewId) - Switch between views, already defined
- handleSubmit(e) - Form submission, calls e.preventDefault()
- handleClick(item) - Generic click handler
- handleChange(value) - Input change handler
- () => {} - Use empty arrow function if no handler needed
""")

        # 2. Standard state variables
        scope_parts.append("""
AVAILABLE STATE VARIABLES:
- currentView - Current active view/page (string)
- setCurrentView - Setter for currentView
- loading - Data loading state (boolean)
- error - Error message (string or null)
- data - Fetched API data (object)
""")

        # 3. Available components from this build
        if components:
            comp_names = list(components.keys())
            scope_parts.append(f"""
AVAILABLE COMPONENTS (already defined, import and use these):
{chr(10).join(f'- {name}' for name in comp_names)}
""")

        # 4. Standard icons (from lucide-react)
        scope_parts.append("""
AVAILABLE ICONS (import from 'lucide-react'):
- Home, User, Settings, Menu, X, Check, Plus, Minus
- ArrowRight, ArrowLeft, ChevronDown, ChevronUp
- Mail, Phone, MapPin, Clock, Calendar
- Facebook, Twitter, Linkedin, Instagram
NOTE: If you need an icon not listed, use null instead of an undefined variable.
""")

        # 5. Forbidden patterns
        scope_parts.append("""
FORBIDDEN PATTERNS (will cause runtime errors):
- onClick={handleSomething} where handleSomething is not defined above
- icon={someIcon} where someIcon is not imported
- defaultSocialIcons.xxx - this variable does not exist
- defaultIcons.xxx - this variable does not exist
Instead, use: onClick={() => {}} or icon={null}
""")

        # 6. CRITICAL: Defensive array patterns to prevent undefined.map() errors
        scope_parts.append("""
CRITICAL - ARRAY SAFETY (prevents "Cannot read properties of undefined (reading 'map')"):
When using .map() on any array, ALWAYS use defensive patterns:

GOOD: {(items || []).map(item => ...)}
GOOD: {items?.map(item => ...) || null}
GOOD: {Array.isArray(items) && items.map(item => ...)}

BAD: {items.map(item => ...)}  // CRASHES if items is undefined

ALWAYS define arrays with default empty arrays:
const [items, setItems] = useState([]);  // NOT useState()
const items = props.items || [];  // NOT const items = props.items

NEVER call .map() without a null check. This is the #1 cause of blank pages.
""")

        return "\n".join(scope_parts)

    def _format_interface_for_prompt(self, interface: ComponentInterface) -> str:
        """
        Format a component interface as a prompt-friendly specification.

        This tells the AI exactly what props are valid for a component,
        preventing it from adding or removing props arbitrarily.
        """
        if not interface:
            return ""

        lines = ["COMPONENT INTERFACE CONTRACT (DO NOT VIOLATE):"]

        # Inputs (props)
        required_props = []
        optional_props = []

        for inp in getattr(interface, 'inputs', []):
            if hasattr(inp, 'data_schema') and inp.data_schema:
                type_str = getattr(inp.data_schema, 'typescript_type', 'any')
            else:
                type_str = 'any'

            prop_name = getattr(inp, 'name', str(inp))
            is_required = getattr(inp, 'required', False)

            if is_required:
                required_props.append(f"  - {prop_name}: {type_str}")
            else:
                default = getattr(inp, 'default_value', None)
                default_str = f" = {default}" if default is not None else ""
                optional_props.append(f"  - {prop_name}: {type_str}{default_str}")

        if required_props:
            lines.append("REQUIRED PROPS (must keep):")
            lines.extend(required_props)

        if optional_props:
            lines.append("OPTIONAL PROPS (keep if present in original):")
            lines.extend(optional_props)

        # Outputs (callbacks)
        outputs = getattr(interface, 'outputs', [])
        if outputs:
            lines.append("EVENT HANDLERS (component may call these):")
            for out in outputs:
                out_name = getattr(out, 'name', str(out))
                lines.append(f"  - {out_name}")

        lines.append("")
        lines.append("RULE: Do NOT add props not in this interface. Do NOT remove existing props.")

        return "\n".join(lines)

    def _update_progress(self, progress: int, message: str):
        """Update build progress for the customer to see."""
        if self.session:
            try:
                from apps.onboarding.models import SessionEvent
                SessionEvent.objects.create(
                    session=self.session,
                    event_type='build_progress',
                    event_data={'progress': progress, 'message': message}
                )
            except Exception as e:
                print(f"[PROGRESS] Failed to update: {e}")
    
    def build(self, prompt: str, project=None) -> str:
        """
        Build a complete app from building blocks.
        
        CRITICAL FIXES:
        - Fix #1: Layout/Navigation are PERMANENT (priority=0), never dropped
        - Fix #2: Gateway First - force real data for trackers/dashboards

        Returns the final App.jsx code.
        """
        print(f"[COMPONENT PIPELINE] Starting build for: {prompt[:50]}...")
        self._update_progress(5, "Analyzing your requirements...")

        # DISABLED: template_matcher returns static templates that don't customize content.
        # The golden_templates system below uses AI to generate customized content
        # for each prompt, which solves the "generic templates" issue.
        #
        # Old code used template_matcher which only replaced {{BUSINESS_NAME}} and {{TAGLINE}}
        # but didn't customize services, features, testimonials, etc. to match the prompt.
        # Result: "NFT dog artist" prompt got generic "Portfolio Website" template.

        # GOLDEN TEMPLATES: AI generates DATA, templates handle STRUCTURE
        # This is the reliable approach - 60-80% reduction in syntax errors
        try:
            from .golden_templates import compose_from_templates
            print(f"[COMPONENT PIPELINE] Trying GOLDEN TEMPLATES (data + template injection)...")
            self._update_progress(15, "Generating content...")

            app_code, metadata = compose_from_templates(prompt)

            if app_code and 'function App' in app_code and 'export default' in app_code:
                print(f"[COMPONENT PIPELINE] GOLDEN TEMPLATES SUCCESS: {metadata.get('line_count', 0)} lines")
                print(f"[COMPONENT PIPELINE] Components: {metadata.get('components_used', [])}")

                self.stats['golden_templates'] = True
                self.stats['template_components'] = metadata.get('components_used', [])
                self.stats['components_reused'] = len(metadata.get('components_used', []))
                self.stats['components_generated'] = 0

                # Store generated images from metadata
                self.generated_images = metadata.get('generated_images', {})
                if self.generated_images:
                    print(f"[COMPONENT PIPELINE] AI images generated: {list(self.generated_images.keys())}")

                # Validate with esbuild
                from apps.code_library.jsx_validator import validate_jsx
                is_valid, error = validate_jsx(app_code)

                if is_valid:
                    print(f"[COMPONENT PIPELINE] Golden template code VALIDATED")
                    self._update_progress(95, "Finalizing code...")
                    return app_code
                else:
                    print(f"[COMPONENT PIPELINE] Golden template validation failed: {error}")
                    # Don't raise, fall through to component generation
            else:
                print(f"[COMPONENT PIPELINE] Golden template output incomplete")

        except Exception as e:
            print(f"[COMPONENT PIPELINE] Golden templates error: {e}")

        print(f"[COMPONENT PIPELINE] Falling back to component-by-component generation...")

        # Step 1: Decompose into required components
        requirements = self.decomposer.decompose(prompt)
        
        # FIX #1: Smart Component Sizing
        # Separate PERMANENT components (priority=0) from content components
        permanent_reqs = [r for r in requirements if r.priority == 0]
        content_reqs = [r for r in requirements if r.priority > 0]
        
        # Limit ONLY content components (max 5), keep ALL permanent components
        MAX_CONTENT_COMPONENTS = 5
        if len(content_reqs) > MAX_CONTENT_COMPONENTS:
            print(f"[COMPONENT PIPELINE] Limiting content from {len(content_reqs)} to {MAX_CONTENT_COMPONENTS}")
            # Keep highest priority content components
            content_reqs = sorted(content_reqs, key=lambda r: r.priority)[:MAX_CONTENT_COMPONENTS]
        
        # Combine: permanent + limited content
        requirements = permanent_reqs + content_reqs
        
        self.stats['components_required'] = len(requirements)
        
        print(f"[COMPONENT PIPELINE] Required components: {len(requirements)} ({len(permanent_reqs)} permanent + {len(content_reqs)} content)")
        self._update_progress(10, f"Planning {len(requirements)} components...")
        
        for req in requirements:
            perm = "(PERMANENT)" if req.priority == 0 else ""
            print(f"  - {req.component_type.value}/{req.variant} {perm}")
        
        # FIX #2: Detect if this needs real data (Gateway First Policy)
        prompt_lower = prompt.lower()
        needs_real_data = any(kw in prompt_lower for kw in [
            'real-time', 'live', 'tracker', 'monitor', 'stock', 'crypto', 
            'prices', 'api', 'fetch', 'external', 'trading', 'market',
            'weather', 'dashboard', 'analytics', 'data', 'news', 'currency',
            'exchange', 'rate', 'temperature', 'forecast'
        ])
        if needs_real_data:
            print(f"[COMPONENT PIPELINE] [CRITICAL] GATEWAY FIRST: Real-time data detected")
        
        # Step 2: For each component, search library or generate
        components = {}
        total = len(requirements)
        
        for idx, req in enumerate(requirements):
            # Calculate progress: 10-80% for component building
            progress = 10 + int((idx / total) * 70)
            component_name = f"{req.component_type.value}/{req.variant}"
            self._update_progress(progress, f"Building {component_name}...")
            
            component_code = self._get_or_generate_component(req, prompt)
            if component_code:
                key = f"{req.component_type.value}_{req.variant}"
                components[key] = component_code
        
        # Step 2.5: Get interfaces and validate connections
        interfaces = self._get_interfaces_for_requirements(requirements)
        validation_result = self._validate_composition(interfaces)
        
        if not validation_result['valid']:
            print(f"[COMPONENT PIPELINE] [WARN] Composition issues: {len(validation_result['issues'])} issues")
            self.stats['validation_issues'] = validation_result['issues']
        
        # Step 2.6: Generate wiring blueprint WITH Gateway integration
        wiring_blueprint = self._generate_wiring_blueprint(interfaces, needs_real_data)
        self.stats['wiring_used'] = True
        
        # Step 3: Compose final app (with SPA wrapper for navigation)
        print(f"[COMPONENT PIPELINE] Composing app from {len(components)} components...")
        self._update_progress(85, "Assembling your application...")
        
        # Pass the real_data flag and wiring to composer
        final_code = self._compose_app(components, prompt, requirements, needs_real_data, wiring_blueprint)
        
        # Step 3.5: Validate code quality (JSX balance, required patterns, etc.)
        code_validation = validate_code_quality(final_code)
        if not code_validation.valid:
            print(f"[COMPONENT PIPELINE] [WARN] Code quality issues detected:")
            for issue in code_validation.issues:
                print(f"    {issue.level.value.upper()}: {issue.message}")
            self.stats['code_quality_issues'] = [i.to_dict() for i in code_validation.issues]

            # Fix undefined components by generating stubs
            undefined_issues = [i for i in code_validation.issues if i.code == "UNDEFINED_COMPONENT"]
            if undefined_issues:
                print(f"[COMPONENT PIPELINE] Generating stubs for {len(undefined_issues)} undefined components...")
                stubs = []
                for issue in undefined_issues:
                    comp_name = issue.component
                    stub = f'''
const {comp_name} = ({{ children, ...props }}) => (
  <div className="p-4 border rounded" {{...props}}>
    {{children || <span>{comp_name}</span>}}
  </div>
);
'''
                    stubs.append(stub)
                    print(f"    [STUB] Generated stub for {comp_name}")

                # Insert stubs after the icon components section
                stub_code = '\n// AUTO-GENERATED STUBS for undefined components\n' + '\n'.join(stubs)
                # Find a good insertion point (after icon definitions, before first Section component)
                insert_match = re.search(r'(// ={10,}.*?SECTION|const \w+Section)', final_code)
                if insert_match:
                    insert_pos = insert_match.start()
                    final_code = final_code[:insert_pos] + stub_code + '\n\n' + final_code[insert_pos:]
                else:
                    # Fallback: insert after first component definitions
                    final_code = final_code.replace('// React is provided globally', '// React is provided globally\n' + stub_code)
        else:
            print(f"[COMPONENT PIPELINE] [OK] Code quality validation passed")

        # NOTE: Regex band-aids for JSX errors REMOVED per Rule 1
        # We fixed the AI prompts to prevent these errors at generation time
        # See: CRITICAL - PLAIN JAVASCRIPT ONLY sections in _generate_component and _adapt_component

        # Step 3.6: Validate JSX tag balancing (log warning but don't attempt regex fix)
        # NOTE: fix_jsx_tags() REMOVED per Rule 1 - it was adding stray closing tags
        # that broke valid code. Prompts now instruct AI to generate balanced JSX.
        jsx_valid, jsx_error = validate_jsx_tags(final_code)
        if not jsx_valid:
            print(f"[COMPONENT PIPELINE] [WARN] JSX tag mismatch detected: {jsx_error}")
            print(f"[COMPONENT PIPELINE] [WARN] Not attempting auto-fix (per Rule 1 - no regex for JSX)")
            self.stats['jsx_tag_error'] = jsx_error
        else:
            print(f"[COMPONENT PIPELINE] [OK] JSX tag validation passed")

        # Step 3.7: Check code complexity (Base44 lesson: auto-refactoring triggers)
        complexity_metrics = measure_complexity(final_code)
        self.stats['complexity'] = complexity_metrics

        if complexity_metrics['needs_refactor']:
            print(f"[COMPONENT PIPELINE] [WARN] Code complexity exceeds thresholds:")
            for reason in complexity_metrics['refactor_reasons']:
                print(f"    - {reason}")
            print(f"[COMPONENT PIPELINE] [INFO] Consider refactoring before adding features")
        else:
            print(f"[COMPONENT PIPELINE] [OK] Code complexity within limits "
                  f"(lines={complexity_metrics['line_count']}, "
                  f"functions={complexity_metrics['function_count']}, "
                  f"depth={complexity_metrics['nesting_depth']})")

        self._update_progress(95, "Finalizing code...")

        # Stats summary
        print(f"[COMPONENT PIPELINE] BUILD COMPLETE:")
        print(f"  - Components required: {self.stats['components_required']}")
        print(f"  - Components reused: {self.stats['components_reused']}")
        print(f"  - Components generated: {self.stats['components_generated']}")
        
        return final_code
    
    def _get_or_generate_component(
        self, 
        requirement: ComponentRequirement,
        full_prompt: str
    ) -> Optional[str]:
        """
        Get component from library or generate new one.
        """
        # Search library
        match = self.library.search(requirement)
        
        if match.found:
            print(f"[COMPONENT PIPELINE] [OK] REUSE: {requirement.component_type.value}/{requirement.variant}")
            print(f"    Source: {match.component.id} (score={match.score:.1f})")
            print(f"    Reason: {match.reason}")
            
            self.stats['components_reused'] += 1
            self.stats['reused_from'].append(match.component.id)
            
            # INCREMENT USAGE COUNT - track component reuse
            try:
                from apps.code_library.models import LibraryItem
                library_item = LibraryItem.objects.get(id=match.component.id)
                library_item.increment_usage()
                print(f"    Usage count: {library_item.usage_count}")
            except Exception as e:
                print(f"    [WARN] Failed to increment usage: {e}")
            
            # Strip TypeScript annotations (library was built with TS, but we now use plain JS)
            code = strip_typescript_annotations(match.component.code)

            # Adapt the component for this specific use case
            adapted = self._adapt_component(code, requirement, full_prompt)
            return adapted
        
        else:
            print(f"[COMPONENT PIPELINE] [NEW] GENERATE: {requirement.component_type.value}/{requirement.variant}")
            print(f"    Reason: {match.reason}")
            
            # Generate new component
            code = self._generate_component(requirement, full_prompt)
            
            if code:
                # Save to library for future reuse
                component_id = self.library.save_component(
                    code=code,
                    component_type=requirement.component_type,
                    variant=requirement.variant,
                    description=requirement.description,
                    version="1.0.0",
                    version_notes=f"Initial version. Generated for: {full_prompt[:100]}"
                )
                
                self.stats['components_generated'] += 1
                self.stats['generated_ids'].append(component_id)
            
            return code
    
    def _generate_component(
        self,
        requirement: ComponentRequirement,
        full_prompt: str
    ) -> str:
        """
        Generate a NEW component using Opus 4.5.

        This component should be:
        - Self-contained
        - Reusable
        - Well-structured
        - Using production Gateway URL
        """
        # Get user rules and owner instructions for injection
        rules_injection = get_rules_prompt_injection()
        instruction_injection = get_instruction_prompt()

        # Get interface contract for this component type (Base44 lesson)
        interface = get_interface(requirement.component_type.value)
        interface_spec = self._format_interface_for_prompt(interface) if interface else ""

        # Get pre-seeded scope (Base44 lesson - tell AI what's available)
        scope_spec = self._get_available_scope()

        prompt = f"""
Generate a REUSABLE React component for the following requirement.

COMPONENT TYPE: {requirement.component_type.value}
VARIANT: {requirement.variant}
CONTEXT: {full_prompt}
DESCRIPTION: {requirement.description}

{interface_spec}

{scope_spec}

{rules_injection}
{instruction_injection}

REQUIREMENTS:
1. Make it a REUSABLE building block, not tied to one specific use case
2. Use Tailwind CSS for styling
3. If it needs external data, use the Gateway:
   fetch('https://api.faibric.com/api/gateway/', {{
     method: 'POST',
     headers: {{ 'Content-Type': 'application/json' }},
     body: JSON.stringify({{ service: 'SERVICE', endpoint: '/endpoint' }})
   }})
4. Export the component as default
5. Add brief comments explaining key parts
6. Use TEXT LABELS only for icons, NEVER use emojis
7. Only use handlers and variables from AVAILABLE HANDLERS and AVAILABLE STATE VARIABLES above

CRITICAL - PLAIN JAVASCRIPT ONLY (NO TYPESCRIPT):
You MUST generate plain JavaScript. TypeScript will cause build failures.

FORBIDDEN (TypeScript syntax - DO NOT USE):
- Type annotations: const x: string = ..., function foo(a: number)
- Interface definitions: interface Props {{ ... }}
- Type definitions: type MyType = ...
- Generic types: Array<string>, Record<K,V>, React.FC<Props>
- Type imports: import type {{ X }} from 'y'
- Type assertions: value as Type, <Type>value
- keyof, typeof in type context
- Optional chaining with types: param?: Type

CORRECT (plain JavaScript):
- const x = "hello"
- function foo(a) {{ ... }}
- const MyComponent = ({{ prop1, prop2 = "default" }}) => {{ ... }}
- Array, Object, Map, Set (without generics)

ALSO CRITICAL - VALID JSX:
- Every opening tag MUST have a matching closing tag
- Do NOT create duplicate variable names in the same scope
- Use React.Fragment or <></> for multiple root elements

CRITICAL - SELF-CONTAINED COMPONENT:
- The component must be COMPLETELY self-contained
- Do NOT reference undefined components like <ReusableForm>, <CustomWidget>, etc.
- Use ONLY HTML elements (div, span, form, input, button) or components defined IN THIS CODE
- Every JSX tag starting with uppercase MUST be defined in the code you return

AVAILABLE SERVICES (via Gateway):
- yahoo_finance: Stock data (e.g., /chart/AAPL)
- coingecko: Crypto prices (e.g., /simple/price?ids=bitcoin&vs_currencies=usd)
- restcountries: Country data (e.g., /all)

Return ONLY the component code, nothing else.
"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            
            code = response.content[0].text.strip()
            
            # Clean up markdown if present
            if code.startswith('```'):
                lines = code.split('\n')
                code = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])
            
            # CRITICAL: Sanitize code to fix common AI mistakes
            code = self._sanitize_code(code)
            
            return code
            
        except Exception as e:
            print(f"[COMPONENT PIPELINE] Generation error: {e}")
            return None
    
    def _sanitize_code(self, code: str) -> str:
        """
        CRITICAL: Fix common AI code generation mistakes.
        
        Problems fixed:
        - Smart quotes ('') → regular quotes ('')
        - Curly quotes ("") → straight quotes ("")
        - Em/en dashes (—–) → regular dashes (-)
        - Unescaped apostrophes in single-quoted strings
        - Other problematic unicode characters
        """
        import re
        
        if not code:
            return code
        
        # Smart/curly quotes to straight quotes
        replacements = {
            ''': "'",  # Right single quote (U+2019)
            ''': "'",  # Left single quote (U+2018)
            '"': '"',  # Left double quote (U+201C)
            '"': '"',  # Right double quote (U+201D)
            '—': '-',  # Em dash
            '–': '-',  # En dash
            '…': '...',  # Ellipsis
            '\u00a0': ' ',  # Non-breaking space
        }
        
        for bad, good in replacements.items():
            code = code.replace(bad, good)
        
        # FIX: Broken arrow function syntax
        # AI sometimes generates `= />` instead of `=>`
        # Pattern: `(e) = />` should be `(e) =>`
        code = re.sub(r'\)\s*=\s*/>', r') =>', code)
        # Pattern: `= />` at end of line or before something
        code = re.sub(r'=\s*/>\s*(\w)', r'=> \1', code)
        # More general: any `= />` → `=>`
        code = code.replace('= />', '=>')
        code = code.replace('=/>', '=>')
        
        # Fix TypeScript generic syntax errors
        # CRITICAL: The AI often forgets closing `>` in nested generics
        
        # Pattern 1: useState<SomeThing<T>( should be useState<SomeThing<T>>(
        code = re.sub(r'useState<(\w+)<(\w+)>\(', r'useState<\1<\2>>(', code)
        code = re.sub(r'useRef<(\w+)<(\w+)>\(', r'useRef<\1<\2>>(', code)
        code = re.sub(r'useCallback<(\w+)<(\w+)>\(', r'useCallback<\1<\2>>(', code)
        code = re.sub(r'useMemo<(\w+)<(\w+)>\(', r'useMemo<\1<\2>>(', code)
        
        # Pattern 2: React.Dispatch<React.SetStateAction<Type[]>; (missing >)
        # Should be: React.Dispatch<React.SetStateAction<Type[]>>;
        code = re.sub(
            r'React\.Dispatch<React\.SetStateAction<([^>]+)>;',
            r'React.Dispatch<React.SetStateAction<\1>>;',
            code
        )
        
        # Pattern 3: Fix unbalanced generics in TYPE DECLARATION lines only
        # Must NOT touch lines with comparison operators (<=, >=, <, >)
        # Only fix lines that look like type declarations (contain keywords)
        lines = code.split('\n')
        fixed_lines = []
        type_indicators = ['React.', 'Dispatch', 'SetStateAction', 'FC<', 'useState<', 
                           'useRef<', ': {', '}: ', 'interface ', 'type ']
        for line in lines:
            stripped = line.rstrip()
            # Only process lines that:
            # 1. End with semicolon
            # 2. Contain type-related keywords
            # 3. Have unbalanced angle brackets
            # 4. Do NOT contain comparison operators like <= or >= or direct <> comparisons
            is_type_line = any(ind in line for ind in type_indicators)
            has_comparison = '<=' in line or '>=' in line or '< ' in line or '> ' in line
            
            if (stripped.endswith(';') and is_type_line and not has_comparison and '<' in line):
                open_angles = line.count('<')
                close_angles = line.count('>')
                if open_angles > close_angles:
                    missing = open_angles - close_angles
                    line = stripped[:-1] + ('>' * missing) + ';'
            fixed_lines.append(line)
        code = '\n'.join(fixed_lines)
        
        # Common contractions that break single-quoted strings
        # Replace common contraction patterns within single-quoted JSX text
        contractions = ["I've", "I'm", "don't", "doesn't", "won't", "can't", "shouldn't", 
                       "couldn't", "wouldn't", "it's", "that's", "what's", "there's"]
        for contraction in contractions:
            # Only fix if it appears to be in a single-quoted string context
            # This is a simple heuristic - replace with non-contraction form
            expanded = {
                "I've": "I have", "I'm": "I am", "don't": "do not", 
                "doesn't": "does not", "won't": "will not", "can't": "cannot",
                "shouldn't": "should not", "couldn't": "could not", 
                "wouldn't": "would not", "it's": "it is", "that's": "that is",
                "what's": "what is", "there's": "there is"
            }
            if contraction in expanded:
                code = code.replace(contraction, expanded[contraction])
        
        # CRITICAL: Apply user rules (removes emojis, forbidden patterns, etc.)
        code = enforce_user_rules(code)
        
        # CRITICAL: Apply owner instructions enforcement
        code, fixes = enforce_instructions(code)
        if fixes:
            print(f"[COMPONENT PIPELINE] Owner instruction fixes: {fixes}")
        
        return code
    
    def _fix_duplicate_exports(self, code: str) -> str:
        """
        Fix multiple 'export default' statements in the code.
        
        Common AI mistake: Including export default for each component
        when combining multiple components into one file.
        """
        import re
        
        if not code:
            return code
        
        # Count export defaults
        export_matches = list(re.finditer(r'export\s+default\s+\w+\s*;?', code))
        
        if len(export_matches) <= 1:
            return code  # Only one or none, no fix needed
        
        print(f"[COMPONENT PIPELINE] Fixing {len(export_matches)} duplicate exports")
        
        # Keep only the last one (export default App)
        # Remove all others
        for match in export_matches[:-1]:
            code = code.replace(match.group(), '', 1)
        
        # Also remove "export default function X" -> "function X"
        code = re.sub(r'export\s+default\s+function\s+(\w+)', r'function \1', code)
        code = re.sub(r'export\s+default\s+const\s+(\w+)', r'const \1', code)
        
        return code
    
    def _adapt_component(
        self,
        code: str,
        requirement: ComponentRequirement,
        full_prompt: str
    ) -> str:
        """
        Adapt an existing component for the specific use case.

        Uses Opus 4.5 to customize the component with business-specific content.
        This is the key to making reused components feel custom.

        NOTE: Previously used Haiku but it was generating invalid JSX (missing closing tags).
        Opus 4.5 is more reliable for code generation.
        """
        # Sanitize the code first
        code = self._sanitize_code(code)

        # Get interface contract for this component type (Base44 lesson)
        interface = get_interface(requirement.component_type.value)
        interface_spec = self._format_interface_for_prompt(interface) if interface else ""

        # Get pre-seeded scope (Base44 lesson - tell AI what's available)
        scope_spec = self._get_available_scope()

        # Extract business context from prompt
        adaptation_prompt = f"""You are a senior frontend developer creating a BEAUTIFUL, MODERN website for a specific business.

THE BUSINESS: {full_prompt}

YOUR JOB:
1. Rewrite ALL text content to match THIS business
2. ENHANCE the styling to look BEAUTIFUL and MODERN

ORIGINAL TEMPLATE:
```jsx
{code}
```

{interface_spec}

{scope_spec}

CONTENT CHANGES (be aggressive):
1. ALL text strings - titles, descriptions, labels, button text
2. ALL data arrays - menu items, services, features, testimonials
3. Business name, tagline, services offered
4. Section headings and descriptions
5. Any placeholder text -> replace with {full_prompt} content

STYLING (CRITICAL - respect USER'S color preferences):
If the user's request mentions specific colors, USE THEM EXCLUSIVELY:
- For "brown/espresso/coffee" -> use ONLY amber-900, amber-800, amber-700, stone-800, yellow-900
- For "cream/beige/tan" -> use ONLY amber-50, amber-100, orange-50, yellow-50
- For "green" -> use green-600, emerald-700, green-800

CRITICAL COLOR RESTRICTIONS:
If user requests "brown and cream" or "coffee shop" colors:
- FORBIDDEN: gray, slate, zinc, neutral, blue, indigo, green, emerald, teal, cyan, sky, purple, violet
- ALLOWED ONLY: amber-*, orange-50, yellow-50, stone-*, white (for text on dark), black (for text on light)
- Headers/navbars: bg-amber-900 (dark brown)
- Section backgrounds: bg-amber-50 (cream)
- Buttons: bg-amber-700 hover:bg-amber-800
- Text on dark: text-amber-50 or text-white
- Text on light: text-amber-900 or text-stone-800
- Borders: border-amber-200 or border-amber-300

BEAUTIFUL MODERN STYLING (for brown/cream theme):
1. Gradients: bg-gradient-to-r from-amber-900 to-amber-800, bg-gradient-to-br from-stone-900 via-amber-900 to-stone-800
2. Shadows: shadow-lg, shadow-xl, shadow-2xl
3. Rounded: rounded-xl, rounded-2xl, rounded-full
4. Hover: hover:scale-105, hover:shadow-xl, transition-all duration-300
5. Cards: bg-amber-50 shadow-xl rounded-2xl p-6 border border-amber-200
6. Buttons: bg-amber-700 hover:bg-amber-800 text-white font-semibold py-3 px-6 rounded-lg

IMAGES (CRITICAL - use Picsum, NEVER Unsplash):
- For coffee shops: seed/coffee-latte, seed/espresso-cup, seed/cafe-interior, seed/coffee-beans
- Hero backgrounds: Use inline style with Picsum: style={{backgroundImage: "url('https://picsum.photos/seed/KEYWORD/1920/1080')"}}
- Gallery images: <img src="https://picsum.photos/seed/UNIQUE_WORD/800/600" className="..." />
- Profile photos: https://picsum.photos/seed/person1/400/400
- NEVER use unsplash.com URLs - they are broken
- NEVER use local paths like /image.jpg - they don't exist
- Each image MUST have a UNIQUE seed keyword
- For coffee shops, use: coffee-latte, espresso-art, cafe-table, barista, coffee-beans, cappuccino

EXAMPLE HERO for coffee shop:
<section className="min-h-screen bg-cover bg-center relative" style={{backgroundImage: "url('https://picsum.photos/seed/coffee-shop-interior/1920/1080')"}}>
  <div className="absolute inset-0 bg-gradient-to-r from-amber-900/80 to-amber-800/60"></div>
  <div className="relative z-10 container mx-auto px-6 py-32">
    <h1 className="text-5xl font-bold text-amber-50 mb-4">Business Name</h1>
  </div>
</section>

YOU MUST KEEP:
- The function name and props signature
- JSX structure (div, span, button elements)
- React hooks and state management

TECHNICAL RULES:
- Plain JavaScript (no TypeScript annotations)
- Keep JSX tags balanced
- Only use standard lucide-react icons that exist: Home, User, Settings, Menu, X, Check, Plus, Minus, Mail, Phone, MapPin, Clock, Calendar, Star, Heart, ShoppingCart, Search, Bell, ChevronRight, ChevronDown, ArrowRight
- IMPORTANT: Use DOUBLE QUOTES for ALL strings, never single quotes. This avoids apostrophe escaping issues.
  - WRONG: 'Tuscany's finest wine'
  - CORRECT: "Tuscany's finest wine"

CRITICAL: Your response must start with "const" or "function" - NO explanatory text before the code.
Do NOT say "Here's..." or explain anything. ONLY output the code starting with the component definition."""

        try:
            # Use configured model for code generation
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": adaptation_prompt}]
            )

            adapted_code = response.content[0].text.strip()

            # Clean up any markdown formatting
            if adapted_code.startswith("```"):
                lines = adapted_code.split("\n")
                # Remove first line (```jsx) and last line (```)
                adapted_code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            # CRITICAL: Strip any explanatory text before the actual code
            # AI sometimes says "Here's the code:" before the actual code
            import re
            # Find where actual code starts (const, function, or //)
            code_start = re.search(r'^(const |function |// )', adapted_code, re.MULTILINE)
            if code_start and code_start.start() > 0:
                print(f"[ADAPT] [WARN] Stripping {code_start.start()} chars of explanatory text before code")
                adapted_code = adapted_code[code_start.start():]

            # CRITICAL: Validate props are preserved
            # If AI removed props that exist in original, restore them
            adapted_code = self._restore_missing_props(code, adapted_code)

            # NOTE: _fix_undefined_references() removed - pre-seeded scope in prompts now prevents these errors
            # See BASE44 lessons and docs/guides/NO_REGEX_FOR_JSX.md

            print(f"[ADAPT] Customized {requirement.component_type.value}/{requirement.variant} for business context")
            return adapted_code

        except Exception as e:
            print(f"[ADAPT] [WARN] Adaptation failed, using original: {e}")
            return code

    # _fix_undefined_references() REMOVED - see BASE44 lessons
    # Pre-seeded scope in AI prompts now prevents undefined variable errors at generation time
    # Using regex to fix JSX errors hides problems and breaks functionality
    # See: docs/guides/NO_REGEX_FOR_JSX.md

    def _restore_missing_props(self, original_code: str, adapted_code: str) -> str:
        """
        Restore props that AI accidentally removed during adaptation.

        Extracts props from original destructuring and ensures they exist in adapted code.
        """
        import re

        # Extract original destructured props
        orig_match = re.search(r'(?:const|function)\s+\w+\s*=?\s*\(\{\s*([^}]+)\}\)', original_code, re.DOTALL)
        adapted_match = re.search(r'(?:const|function)\s+\w+\s*=?\s*\(\{\s*([^}]+)\}\)', adapted_code, re.DOTALL)

        if not orig_match or not adapted_match:
            return adapted_code

        # Parse props (looking for prop names, ignoring defaults)
        def extract_prop_names(params_str):
            props = set()
            for line in params_str.split('\n'):
                line = line.strip().rstrip(',')
                if '=' in line:
                    prop = line.split('=')[0].strip()
                elif ':' in line and '?' in line:
                    continue  # Skip TypeScript interface lines
                else:
                    prop = line.strip()
                if prop and not prop.startswith('//'):
                    props.add(prop)
            return props

        orig_props = extract_prop_names(orig_match.group(1))
        adapted_props = extract_prop_names(adapted_match.group(1))

        missing_props = orig_props - adapted_props

        if missing_props:
            print(f"[ADAPT] [WARN] AI removed props: {missing_props}, restoring them")
            # Add missing props to the adapted code's destructuring
            adapted_params = adapted_match.group(1)
            for prop in missing_props:
                # Find the prop with default in original
                orig_prop_match = re.search(rf'{re.escape(prop)}\s*(?:=\s*[^,]+)?(?:,|\s*$)', orig_match.group(1))
                if orig_prop_match:
                    prop_with_default = orig_prop_match.group(0).strip().rstrip(',')
                    # Add to the end of destructuring
                    adapted_params = adapted_params.rstrip() + ',\n  ' + prop_with_default

            # Replace the destructuring in adapted code
            adapted_code = adapted_code[:adapted_match.start(1)] + adapted_params + adapted_code[adapted_match.end(1):]

        return adapted_code

    def _compose_app(
        self,
        components: Dict[str, str],
        prompt: str,
        requirements: List[ComponentRequirement],
        needs_real_data: bool = False,
        wiring_blueprint: str = ""
    ) -> str:
        """
        Compose all components into a final App.jsx.

        STRATEGY:
        1. Try Connector V2 first (deterministic, 130,000x faster)
        2. Fall back to AI if Connector V2 is unhealthy

        Uses Opus 4.5 to intelligently combine components.
        """
        global _connector_v2_status

        # STRATEGY:
        # 1. Try MODULAR composition (components as separate files)
        # 2. This produces a small App.jsx + component files
        # 3. Store component files in self.component_files for deployer

        try:
            logger.info("[COMPOSE] Using MODULAR composition (separate component files)")
            files_dict, app_code = compose_modular(
                components=components,
                prompt=prompt,
                needs_real_data=needs_real_data
            )

            # Store component files for the deployer to use
            self.component_files = files_dict

            # Validate the generated App.jsx
            if app_code and 'function App' in app_code and 'export default' in app_code:
                logger.info(f"[COMPOSE] Modular SUCCESS: {len(app_code)} bytes App.jsx, {len(files_dict)} total files")
                self.stats['wiring_method'] = 'modular'
                self.stats['component_files'] = list(files_dict.keys())
                
                # VALIDATE with esbuild - BLOCKING validation
                # If invalid, raise JSXValidationError for build_service to retry with AI
                from apps.code_library.jsx_validator import validate_jsx
                is_valid, error = validate_jsx(app_code)

                if is_valid:
                    logger.info("[COMPOSE] Modular code validated by esbuild - PASSED")
                    return app_code
                else:
                    # BLOCKING: Raise exception - do NOT return invalid code
                    logger.error(f"[COMPOSE] JSX validation FAILED: {error}")
                    raise JSXValidationError(
                        f"Generated code has syntax error: {error}",
                        code=app_code
                    )
            else:
                logger.warning("[COMPOSE] Modular output incomplete, falling back to AI")
        except JSXValidationError:
            # Re-raise validation errors - don't fall back, let build_service handle retry
            raise
        except Exception as e:
            logger.error(f"[COMPOSE] Modular failed: {e}, falling back to AI")
        
        # Connector V2 is disabled (library components corrupted)
        _connector_v2_status = False
        
        if _connector_v2_status:
            try:
                # Use Connector V2 for deterministic wiring
                logger.info("[CONNECTOR V2] Using deterministic wiring")
                
                # Get component types for each component
                component_types = {
                    f"{req.component_type.value}_{req.variant}": req.component_type.value
                    for req in requirements
                }
                
                app_code, metadata = compose_app_v2(components, component_types, prompt)
                
                # Validate the generated code
                if app_code and 'function App' in app_code and 'export default' in app_code:
                    logger.info(f"[CONNECTOR V2] SUCCESS: Generated in {metadata.get('generation_time_ms', 0):.2f}ms")
                    self.stats['wiring_method'] = 'connector_v2'
                    self.stats['wiring_time_ms'] = metadata.get('generation_time_ms', 0)
                    
                    # Apply sanitization and fixes
                    app_code = self._sanitize_code(app_code)
                    app_code = self._fix_duplicate_exports(app_code)
                    app_code = self._fix_jsx_balance(app_code)
                    
                    return app_code
                else:
                    logger.warning("[CONNECTOR V2] Generated code incomplete, falling back to AI")
            except Exception as e:
                logger.error(f"[CONNECTOR V2] Error: {e}, falling back to AI")
                _connector_v2_status = False  # Mark as unhealthy for this session
        
        # Fall back to AI-generated wiring
        logger.info("[COMPOSE] Using AI-generated wiring (fallback)")
        # Pass component SIGNATURES only to save tokens
        components_desc = "\n".join([
            f"- {name}: {len(code)} chars, {code.count('interface')} interfaces" 
            for name, code in components.items()
        ])
        
        # FIX #2: Gateway First Policy - STRICT NO FAKE DATA
        gateway_instruction = ""
        if needs_real_data:
            gateway_instruction = """
⛔⛔⛔ ABSOLUTELY NO FAKE/HARDCODED DATA ⛔⛔⛔

FORBIDDEN PATTERNS (do NOT use these):
- const data = [{...}, {...}]
- const prices = { bitcoin: 45000 }  
- useState([{ name: "...", value: ... }])
- Any array with sample/mock/fake values

REQUIRED: Start with EMPTY state, fetch REAL data (NO TypeScript - plain JavaScript only):

const [prices, setPrices] = React.useState({});
const [loading, setLoading] = React.useState(true);

React.useEffect(() => {
  const fetchPrices = async () => {
    try {
      const response = await fetch("https://api.faibric.com/api/gateway/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          service: "coingecko", 
          endpoint: "/simple/price?ids=bitcoin,ethereum&vs_currencies=usd" 
        })
      });
      const data = await response.json();
      setPrices(data.data || data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  fetchPrices();
  const interval = setInterval(fetchPrices, 30000);
  return () => clearInterval(interval);
}, []);

// PLACEHOLDER COMPONENT - use this when data is loading or unavailable:
const DataPlaceholder = ({ symbol = "$", onActivate }) => (
  <span className="inline-flex items-center gap-1">
    <span className="text-gray-400 font-mono">{symbol}---</span>
    <button 
      onClick={onActivate}
      className="text-xs text-blue-500 hover:text-blue-700 underline"
    >
      Turn On Real Values
    </button>
  </span>
);

// In render - show placeholder while loading, real data when available:
{loading || !prices ? (
  <DataPlaceholder symbol="$" onActivate={() => setCurrentView("settings")} />
) : (
  <span>${prices.bitcoin?.toLocaleString()}</span>
)}

// IMPORTANT: Always include a "settings" view for API configuration:
{currentView === "settings" && (
  <div className="p-8">
    <h2 className="text-2xl font-bold mb-4">Connect Your Data</h2>
    <p className="text-gray-600 mb-6">To see real values, connect your data sources:</p>
    <div className="space-y-4">
      <div className="p-4 border rounded-lg">
        <h3 className="font-semibold">Cryptocurrency Prices</h3>
        <p className="text-sm text-gray-500">Free - No API key needed</p>
        <span className="text-green-500 text-sm">✓ Auto-connected</span>
      </div>
      <div className="p-4 border rounded-lg">
        <h3 className="font-semibold">Stock Market Data</h3>
        <p className="text-sm text-gray-500">Free tier available</p>
        <span className="text-green-500 text-sm">✓ Auto-connected</span>
      </div>
      <div className="p-4 border rounded-lg">
        <h3 className="font-semibold">Custom API</h3>
        <p className="text-sm text-gray-500">Add your own API endpoint</p>
        <input type="text" placeholder="API Key" className="mt-2 w-full p-2 border rounded" />
        <button className="mt-2 px-4 py-2 bg-blue-500 text-white rounded">Connect</button>
      </div>
    </div>
  </div>
)}

REAL APIs (auto-connected, no key needed):
- coingecko: /simple/price?ids=bitcoin,ethereum&vs_currencies=usd
- yahoo_finance: /chart/AAPL
- restcountries: /all

PLACEHOLDER SYMBOLS TO USE:
- Prices/Money: "$---" or "€---"
- Percentages: "%---"
- Numbers/Counts: "#---"
- Text/Names: "---"
- Dates: "--/--/----"

EVERY data point MUST either show real fetched data OR a placeholder with "Turn On Real Values" link.
"""
        
        # FIX #3: SPA Wrapper - Functional Navigation with Settings
        spa_instruction = """
MANDATORY: FUNCTIONAL NAVIGATION WITH SETTINGS

The sidebar/navigation MUST:
1. Be functional (clicking changes the view)
2. ALWAYS include a "Settings" option
3. Settings view shows API connection status
4. NEVER use emojis - use text labels only or SVG icons

```
const [currentView, setCurrentView] = useState("dashboard");

// Navigation with Settings - NO EMOJIS:
const navItems = [
  { id: "dashboard", label: "Dashboard" },
  { id: "analytics", label: "Analytics" },
  { id: "settings", label: "Settings" },  // ALWAYS include this
];

// Sidebar component:
<nav>
  {navItems.map(item => (
    <button 
      key={item.id}
      onClick={() => onNavigate(item.id)}
      className={currentView === item.id ? "bg-blue-500 text-white" : ""}
    >
      {item.label}
    </button>
  ))}
</nav>

// Main content with view switching:
<main>
  {currentView === "dashboard" && <Dashboard />}
  {currentView === "analytics" && <Analytics />}
  {currentView === "settings" && <SettingsView />}  // REQUIRED
</main>
```

The Settings view MUST show data source connection status and allow API key input.
"""
        
        # Inject wiring blueprint if available
        wiring_section = ""
        if wiring_blueprint:
            wiring_section = f"""
═══════════════════════════════════════════════════════════════════════════════
COMPONENT WIRING BLUEPRINT (FOLLOW THIS EXACTLY)
═══════════════════════════════════════════════════════════════════════════════

{wiring_blueprint}
"""

        # BASE44 LESSON: Pre-seed the available scope to prevent undefined reference errors
        available_scope = self._get_available_scope(components)

        compose_prompt = f"""
Create a COMPLETE React App.jsx for this request:

USER REQUEST: {prompt}

COMPONENT TYPES NEEDED: {components_desc}

{wiring_section}

{gateway_instruction}

{spa_instruction}

{available_scope}

CRITICAL JSX RULES - MUST FOLLOW (VIOLATING THESE WILL CAUSE BUILD FAILURE):
1. Every JSX element MUST have COMPLETE opening tags: <ComponentName prop={{value}}>, NOT just prop={{value}}
2. Every <div> MUST have a matching </div>
3. Every component MUST start with <ComponentName and end with /> or </ComponentName>
4. The App return statement MUST have this EXACT structure:
   return (
     <div className="...">
       <Navigation currentView={{currentView}} onNavigate={{handleNavigate}} />
       {{/* content */}}
     </div>
   );
5. NEVER write orphaned props like:
   WRONG: return (
            currentView={{currentView}}  <- THIS IS BROKEN
          />
   CORRECT: return (
            <Navigation
              currentView={{currentView}}
            />
          );

PLACEHOLDER PATTERN (use when data fails to load):
When fetch fails or data is unavailable, show a placeholder with animated pulse.
Just use a simple span with className="animate-pulse text-gray-400" showing "---" when loading.

Example:
const Placeholder = () => <span className="animate-pulse text-gray-400">$---</span>;
Use: loading ? <Placeholder /> : <span>${{{{data.price}}}}</span>

REQUIREMENTS:
1. Create a SINGLE complete App.jsx file (plain JavaScript, NO TypeScript)
2. Use Tailwind CSS for styling
3. Navigation clicks MUST change the view using React state
4. MUST end with exactly: export default App;
5. Keep code SIMPLE - use plain JavaScript function components
6. Include the DataPlaceholder component for loading/error states
7. Settings view must show API connection options

STRUCTURE:
- Import React at top
- Define navigation state: const [currentView, setCurrentView] = useState("dashboard");
- Define simple component functions (NO generic types like <T>)
- Define main App function with view switching
- End with: export default App;

Keep it simple and working. Aim for 200-400 lines.
Do NOT use external imports except React.
Use double quotes for all strings.
Return ONLY the complete code.
"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=16384,  # Increased for larger apps
                messages=[{"role": "user", "content": compose_prompt}]
            )
            
            code = response.content[0].text.strip()
            
            # Clean up markdown code blocks
            if code.startswith('```'):
                lines = code.split('\n')
                code = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])
            
            # CRITICAL: Sanitize and fix common issues
            code = self._sanitize_code(code)
            code = self._fix_duplicate_exports(code)
            code = self._fix_jsx_balance(code)
            
            # Validate the code is complete
            code = self._ensure_complete_code(code)

            return code
            
        except Exception as e:
            print(f"[COMPONENT PIPELINE] Compose error: {e}")
            # Fallback: simple composition
            code = self.composer.compose(components, prompt)
            code = self._sanitize_code(code)
            code = self._fix_duplicate_exports(code)
            code = self._ensure_complete_code(code)
            return code
    
    def _fix_jsx_balance(self, code: str) -> str:
        """
        CRITICAL: Fix unbalanced JSX tags (divs, spans, etc.)
        
        Handles two cases:
        1. Extra closing tags at end (remove them)
        2. Missing closing tags (add them inside the return statement)
        """
        import re
        
        if not code:
            return code
        
        # STEP 1: Remove orphaned JSX tags after the last function/export
        # These cause "Expected identifier but found /" errors
        lines = code.split('\n')
        result_lines = []
        in_jsx_block = False
        last_valid_line_idx = 0
        
        # Find where the App function ends and export happens
        export_found = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Track if we've seen export default
            if 'export default' in line:
                export_found = True
            
            # After export, any JSX tags are orphaned
            if export_found and stripped.startswith('</') and stripped.endswith('>'):
                print(f"[FIX JSX] Removing orphaned closing tag after export: {stripped}")
                continue
            
            # Also remove orphaned tags that appear after function closing
            if export_found and stripped.startswith('<') and not stripped.startswith('//'):
                # This is JSX after export - invalid
                print(f"[FIX JSX] Removing orphaned JSX after export: {stripped[:50]}")
                continue
            
            result_lines.append(line)
        
        code = '\n'.join(result_lines)
        
        # STEP 2: Check div balance and fix if needed
        open_divs = len(re.findall(r'<div(?:\s|>)', code))
        close_divs = len(re.findall(r'</div>', code))
        diff = open_divs - close_divs
        
        if diff == 0:
            return code  # Balanced
        
        print(f"[FIX JSX] JSX imbalance detected: {open_divs} open, {close_divs} close ({diff:+d})")
        
        if diff > 0:
            # Missing closing divs - find the return statement and add them before the closing
            # Look for the last return's closing pattern
            match = re.search(r'(return\s*\([^)]*?)(\s*\);?\s*\})', code, re.DOTALL)
            if match:
                # Add missing closing divs before the last );
                closing_tags = '</div>\n' * diff
                code = code[:match.end(1)] + '\n' + closing_tags + code[match.end(1):]
                print(f"[FIX JSX] Added {diff} missing </div> tags")
        
        elif diff < 0:
            # Too many closing divs - remove extras from the end
            excess = abs(diff)
            for _ in range(excess):
                # Remove the last </div> 
                last_close = code.rfind('</div>')
                if last_close != -1:
                    code = code[:last_close] + code[last_close + 6:]
                    print(f"[FIX JSX] Removed excess </div>")
        
        return code
    
    def _ensure_complete_code(self, code: str) -> str:
        """
        Ensure the code is complete with proper export.
        
        If the code is truncated or missing export, fix it.
        """
        import re
        
        # Check for truncated JSX (incomplete tags)
        # Look for patterns like "<path fill" or "<svg class" without proper closing
        truncation_patterns = [
            r'<\w+\s+\w+$',  # Tag attribute without value at end
            r'<\w+\s+\w+="[^"]*$',  # Unclosed attribute value
            r'<path\s+fill$',  # Common truncation point
        ]
        
        lines = code.split('\n')
        
        # Find and remove truncated lines at the end
        while lines:
            last_line = lines[-1].strip()
            if not last_line or last_line in [')', ');', '}', '};']:
                break
            # Check if last content line is truncated JSX
            is_truncated = any(re.search(p, last_line) for p in truncation_patterns)
            if is_truncated or (last_line.startswith('<') and '>' not in last_line):
                print(f"[COMPONENT PIPELINE] Removing truncated line: {last_line[:50]}...")
                lines.pop()
            else:
                break
        
        code = '\n'.join(lines)
        
        # DON'T add closing tags here - they cause more problems than they solve
        # The key is to have complete code from the AI in the first place
        # If code is truncated, we'll generate a simpler fallback instead
        
        # Check if code ends with export default App
        if 'export default App' not in code:
            print("[COMPONENT PIPELINE] WARNING: Code missing export, adding it...")
            
            # Try to find the App function and ensure proper ending
            if 'function App' in code or 'const App' in code:
                code = code.rstrip()
                
                # Ensure proper closing braces
                open_braces = code.count('{')
                close_braces = code.count('}')
                missing_braces = open_braces - close_braces
                
                if missing_braces > 0:
                    code += '\n' + ('  );\n}' * min(missing_braces, 5))
                
                code += '\n\nexport default App;'
            else:
                print("[COMPONENT PIPELINE] ERROR: No App function found!")
                code += '\n\nfunction App() {\n  return <div>Error: App component not generated properly</div>;\n}\n\nexport default App;'
        
        return code
    
    def get_stats(self) -> Dict:
        """Get build statistics."""
        return self.stats

    def get_generated_images(self) -> Dict[str, bytes]:
        """Get AI-generated images for deployment."""
        return self.generated_images

    # ═══════════════════════════════════════════════════════════════════════════
    # CONNECTOR SYSTEM METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _get_interfaces_for_requirements(
        self,
        requirements: List[ComponentRequirement]
    ) -> List[ComponentInterface]:
        """
        Get or create interfaces for each required component.
        
        Uses standard interfaces from the registry, or creates
        generic ones for unknown component types.
        """
        interfaces = []
        
        for req in requirements:
            # Try to get standard interface
            interface = get_interface(req.component_type.value, req.variant)
            
            if interface:
                interfaces.append(interface)
            else:
                # Create generic interface for unknown types
                interfaces.append(ComponentInterface(
                    component_type=req.component_type.value,
                    variant=req.variant,
                    version="1.0.0",
                    inputs=[],
                    outputs=[],
                ))
        
        return interfaces
    
    def _validate_composition(
        self,
        interfaces: List[ComponentInterface]
    ) -> Dict:
        """
        Validate that the component set can work together.
        
        Returns validation result with any issues found.
        """
        try:
            result = self.validator.validate_composition(interfaces)
            
            # Log any errors
            for issue in result.errors:
                print(f"[CONNECTOR] [ERROR] {issue.code}: {issue.message}")
            
            # Log warnings
            for issue in result.warnings:
                print(f"[CONNECTOR] [WARN] {issue.code}: {issue.message}")
            
            return result.to_dict()
        except Exception as e:
            print(f"[CONNECTOR] Validation error: {e}")
            return {'valid': True, 'issues': []}
    
    def _generate_wiring_blueprint(
        self,
        interfaces: List[ComponentInterface],
        needs_real_data: bool = False
    ) -> str:
        """
        Generate wiring blueprint for the AI composer.
        
        This provides the AI with exact patterns to follow
        for state management, event handlers, composition,
        AND Gateway API integration when real data is needed.
        """
        try:
            blueprint = generate_wiring_prompt_injection(interfaces, needs_real_data)
            return blueprint
        except Exception as e:
            print(f"[CONNECTOR] Wiring generation error: {e}")
            return ""


def build_with_components(prompt: str, session=None, project=None) -> str:
    """
    Convenience function to build using component pipeline.
    """
    pipeline = ComponentGenerationPipeline(session)
    return pipeline.build(prompt, project)


def build_compact_app(prompt: str, needs_data: bool = False) -> str:
    """
    Build a COMPACT app for Vercel/browser deployment.
    
    Uses DETERMINISTIC TEMPLATES - NO AI CALL.
    This eliminates truncation and JSX breakage risks.
    
    Args:
        prompt: User's request
        needs_data: Whether app needs real-time data from Gateway
    
    Returns:
        Complete app code (plain JavaScript)
    """
    # Use deterministic template instead of AI
    return _build_deterministic_compact_app(prompt, needs_data)


def _build_deterministic_compact_app(prompt: str, needs_data: bool = False) -> str:
    """
    Build a compact app using TEMPLATES - no AI call.
    
    This is 100% reliable - no truncation, no malformed JSX.
    """
    print(f"[COMPACT] Using DETERMINISTIC template (no AI)")
    
    # Determine app type from prompt
    prompt_lower = prompt.lower()
    
    # Determine if needs data
    data_keywords = ['stock', 'crypto', 'bitcoin', 'price', 'weather', 'api', 
                     'tracker', 'live', 'real-time', 'monitor', 'dashboard', 'analytics']
    needs_data = needs_data or any(kw in prompt_lower for kw in data_keywords)
    
    # Use the fallback template which is already tested and working
    return _fallback_compact_app(prompt, needs_data)


def _legacy_build_compact_app(prompt: str, needs_data: bool = False) -> str:
    """
    LEGACY: AI-based compact app generation.
    
    Kept for reference but no longer used.
    Use _build_deterministic_compact_app instead.
    """
    # This function is no longer called - deterministic templates are used instead
    print("[COMPACT] WARNING: Legacy AI function called - redirecting to deterministic")
    return _build_deterministic_compact_app(prompt, needs_data)


def _unused_ai_compact_app(prompt: str, needs_data: bool = False) -> str:
    """
    UNUSED: Original AI-based generation.
    
    Left here as reference only. NOT CALLED.
    """
    import anthropic
    from django.conf import settings
    from apps.ai_engine.models_config import CODE_MODEL
    
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    # Determine app type and data needs
    data_keywords = ['stock', 'crypto', 'bitcoin', 'price', 'weather', 'api', 
                     'tracker', 'live', 'real-time', 'monitor', 'dashboard']
    needs_data = needs_data or any(kw in prompt.lower() for kw in data_keywords)
    
    # DIRECT API calls - No gateway needed for free APIs
    gateway_code = ""
    if needs_data:
        gateway_code = """
  // DIRECT API CALLS - Free APIs, no key needed, no gateway
  const savedInterval = localStorage.getItem("refreshInterval");
  const [refreshInterval, setRefreshIntervalState] = React.useState(
    savedInterval ? parseInt(savedInterval) : 30000
  );
  const [connectionStatus, setConnectionStatus] = React.useState("checking");
  const [lastUpdated, setLastUpdated] = React.useState(null);
  const [errorMessage, setErrorMessage] = React.useState(null);
  const intervalRef = React.useRef(null);
  
  const updateRefreshInterval = (newInterval) => {
    setRefreshIntervalState(newInterval);
    localStorage.setItem("refreshInterval", newInterval.toString());
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = setInterval(loadData, newInterval);
  };
  
  const loadData = async () => {
    setLoading(true);
    setConnectionStatus("checking");
    
    try {
      // Call CoinGecko DIRECTLY - free API, no key needed
      const response = await fetch(
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,cardano&vs_currencies=usd&include_24hr_change=true"
      );
      
      if (response.ok) {
        const result = await response.json();
        setData(result);
        setConnectionStatus("connected");
        setLastUpdated(new Date().toLocaleTimeString());
        setErrorMessage(null);
        localStorage.setItem("cached_crypto", JSON.stringify(result));
      } else if (response.status === 429) {
        // Rate limited - try cache
        const cached = localStorage.getItem("cached_crypto");
        if (cached) {
          setData(JSON.parse(cached));
          setConnectionStatus("cached");
          setErrorMessage("Using cached data (rate limited)");
        } else {
          throw new Error("Rate limited, no cache");
        }
      } else {
        throw new Error("API error");
      }
    } catch (err) {
      console.error("Fetch error:", err);
      // Try CoinDesk as backup (Bitcoin only)
      try {
        const backup = await fetch("https://api.coindesk.com/v1/bpi/currentprice.json");
        if (backup.ok) {
          const cd = await backup.json();
          const btcPrice = cd.bpi?.USD?.rate_float || 0;
          setData({
            bitcoin: { usd: btcPrice },
            ethereum: { usd: null },
            solana: { usd: null },
            cardano: { usd: null }
          });
          setConnectionStatus("connected");
          setErrorMessage("Using CoinDesk backup");
        }
      } catch (e2) {
        // Use cache as last resort
        const cached = localStorage.getItem("cached_crypto");
        if (cached) {
          setData(JSON.parse(cached));
          setConnectionStatus("cached");
        } else {
          setConnectionStatus("error");
          setErrorMessage("Could not fetch prices");
        }
      }
    }
    setLoading(false);
  };
  
  React.useEffect(() => {
    loadData();
    intervalRef.current = setInterval(loadData, refreshInterval);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);
"""

    # Placeholder component - simpler, no fake "Turn On" link for free APIs
    placeholder_code = """
  // PLACEHOLDER - Show when data is loading
  const DataPlaceholder = ({ symbol = "$" }) => (
    <span className="inline-flex items-center gap-2 text-gray-400 animate-pulse">
      <span className="font-mono">{symbol}---</span>
    </span>
  );
"""

    # Admin panel is injected by deployers (vercel_deployer, render_deployer)
    # Unused legacy code removed - see vercel_deployer._inject_admin_panel

    # Settings view - REQUIRED for all apps
    settings_view = """
        {currentView === "settings" && (
          <div className="max-w-md">
            <h2 className="text-2xl font-bold mb-4">Settings</h2>
            <div className="bg-white p-4 rounded shadow space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Refresh Interval</label>
                <select className="w-full p-2 border rounded">
                  <option value="10000">10 seconds</option>
                  <option value="30000">30 seconds</option>
                  <option value="60000">1 minute</option>
                </select>
              </div>
              <div className="border-t pt-4">
                <p className="text-sm font-medium">Data Source Status</p>
                <p className="text-xs text-green-500">Connected</p>
              </div>
            </div>
          </div>
        )}
    """

    compact_prompt = f"""
Create a compact React app for this request: {prompt}

CRITICAL RULES (for browser Babel compatibility):
1. Use ONLY plain JavaScript - NO TypeScript (no interfaces, no type annotations, no generics like <T>)
2. Use React.useState, React.useEffect (not destructured imports)
3. Keep code under 400 lines (extra for admin panel)
4. Include functional navigation with Settings view
5. DO NOT use emojis anywhere
6. Use double quotes for all strings
7. DO NOT include any admin panel code - it will be injected automatically

REQUIRED STRUCTURE:
```javascript
function App() {{
  const [currentView, setCurrentView] = React.useState("dashboard");
  const [data, setData] = React.useState({{}});
  const [loading, setLoading] = React.useState(false);
  
{gateway_code if needs_data else "  // Static data app - no external API needed"}

{placeholder_code if needs_data else ""}

  // Navigation items - ALWAYS include Settings
  const navItems = [
    {{ id: "dashboard", label: "Dashboard" }},
    {{ id: "analytics", label: "Analytics" }},
    {{ id: "settings", label: "Settings" }},
  ];

  return (
    <div className="min-h-screen bg-gray-100">
      {{/* Navigation */}}
      <nav className="bg-white shadow p-4">
        <div className="flex gap-4">
          {{navItems.map(item => (
            <button
              key={{item.id}}
              onClick={{() => setCurrentView(item.id)}}
              className={{currentView === item.id 
                ? "text-blue-600 font-medium" 
                : "text-gray-600 hover:text-gray-900"}}
            >
              {{item.label}}
            </button>
          ))}}
        </div>
      </nav>

      {{/* Main Content - View Switching */}}
      <main className="p-6">
        {{currentView === "dashboard" && (
          <div>
            {{/* Dashboard content with real data or placeholders */}}
            {{loading ? <DataPlaceholder /> : (
              <div>{{/* Display real data */}}</div>
            )}}
          </div>
        )}}
        
        {{currentView === "analytics" && (
          <div>{{/* Analytics content */}}</div>
        )}}
        
{settings_view}
      </main>
    </div>
  );
}}
```

REQUIREMENTS:
1. Navigation MUST work (clicking changes view)
2. Settings view MUST be included
3. {"Use Gateway API for real data, show DataPlaceholder when loading" if needs_data else "Show appropriate static content"}
4. Keep it SIMPLE - under 250 lines
5. Use Tailwind CSS for styling
6. Make it look professional and complete

Return ONLY the code, no markdown.
"""
    
    try:
        response = client.messages.create(
            model=CODE_MODEL,
            max_tokens=8000,
            messages=[{"role": "user", "content": compact_prompt}]
        )
        
        code = response.content[0].text.strip()
        
        # Clean up markdown
        if code.startswith('```'):
            lines = code.split('\n')
            code = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])
        
        # Remove any export statements (Vercel adds ReactDOM.createRoot)
        code = code.replace('export default App;', '')
        code = code.replace('export default App', '')
        
        # Remove any imports (CDN provides React)
        import re
        code = re.sub(r'^import\s+.*$', '', code, flags=re.MULTILINE)
        
        # Ensure we have App function
        if 'function App' not in code:
            print("[COMPACT] ERROR: No App function generated")
            code = _fallback_compact_app(prompt, needs_data)
        
        # Admin panel injection is handled by deployers (vercel_deployer, render_deployer)
        # They use a cleaner wrapper approach that's more robust
        
        return code.strip()
        
    except Exception as e:
        print(f"[COMPACT] Generation error: {e}")
        return _fallback_compact_app(prompt, needs_data)



def _fallback_compact_app(prompt: str, needs_data: bool) -> str:
    """Fallback compact app if AI generation fails - WITH REAL FUNCTIONALITY."""
    title = prompt[:50].replace('"', "'")
    
    if needs_data:
        return f'''
function App() {{
  const [currentView, setCurrentView] = React.useState("dashboard");
  const [data, setData] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [connectionStatus, setConnectionStatus] = React.useState("checking");
  const [lastUpdated, setLastUpdated] = React.useState(null);
  
  // FUNCTIONAL: Load saved refresh interval
  const savedInterval = localStorage.getItem("refreshInterval");
  const [refreshInterval, setRefreshIntervalState] = React.useState(
    savedInterval ? parseInt(savedInterval) : 30000
  );
  const intervalRef = React.useRef(null);
  
  const loadData = async () => {{
    setLoading(true);
    try {{
      const response = await fetch("https://api.faibric.com/api/gateway/", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ service: "coingecko", endpoint: "/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true" }})
      }});
      if (!response.ok) throw new Error("API error");
      const result = await response.json();
      setData(result.data || result);
      setConnectionStatus("connected");
      setLastUpdated(new Date().toLocaleTimeString());
    }} catch (err) {{
      console.error(err);
      setConnectionStatus("error");
    }}
    setLoading(false);
  }};
  
  // FUNCTIONAL: Change refresh interval
  const updateRefreshInterval = (newInterval) => {{
    setRefreshIntervalState(newInterval);
    localStorage.setItem("refreshInterval", newInterval.toString());
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = setInterval(loadData, newInterval);
  }};
  
  React.useEffect(() => {{
    loadData();
    intervalRef.current = setInterval(loadData, refreshInterval);
    return () => {{ if (intervalRef.current) clearInterval(intervalRef.current); }};
  }}, []);

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow p-4 flex gap-4">
        {{["dashboard", "settings"].map(view => (
          <button key={{view}} onClick={{() => setCurrentView(view)}} 
            className={{currentView === view ? "text-blue-600 font-medium" : "text-gray-600"}}>
            {{view.charAt(0).toUpperCase() + view.slice(1)}}
          </button>
        ))}}
      </nav>
      <main className="p-6">
        {{currentView === "dashboard" && (
          <div>
            <h1 className="text-2xl font-bold mb-4">{title}</h1>
            {{loading ? (
              <div className="animate-pulse text-gray-400">Loading...</div>
            ) : (
              <div className="grid grid-cols-3 gap-4">
                {{data && Object.entries(data).map(([coin, prices]) => (
                  <div key={{coin}} className="bg-white p-4 rounded shadow">
                    <p className="text-gray-500 capitalize">{{coin}}</p>
                    <p className="text-2xl font-bold">${{prices?.usd?.toLocaleString() || "---"}}</p>
                  </div>
                ))}}
              </div>
            )}}
            {{lastUpdated && <p className="text-xs text-gray-400 mt-4">Updated: {{lastUpdated}}</p>}}
          </div>
        )}}
        {{currentView === "settings" && (
          <div className="max-w-md">
            <h2 className="text-2xl font-bold mb-4">Settings</h2>
            <div className="bg-white p-4 rounded shadow space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Refresh Interval</label>
                <select 
                  value={{refreshInterval}}
                  onChange={{(e) => updateRefreshInterval(parseInt(e.target.value))}}
                  className="w-full p-2 border rounded"
                >
                  <option value="10000">10 seconds</option>
                  <option value="30000">30 seconds</option>
                  <option value="60000">1 minute</option>
                </select>
              </div>
              <div className="border-t pt-4">
                <p className="text-sm font-medium">CoinGecko API</p>
                <p className="text-xs text-gray-500">Free - no key needed</p>
                <p className={{connectionStatus === "connected" ? "text-green-500 text-sm" : connectionStatus === "error" ? "text-red-500 text-sm" : "text-yellow-500 text-sm"}}>
                  {{connectionStatus === "connected" ? "Live" : connectionStatus === "error" ? "Error" : "Checking..."}}
                </p>
              </div>
              <button 
                onClick={{loadData}}
                disabled={{loading}}
                className="w-full py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300"
              >
                {{loading ? "Refreshing..." : "Refresh Now"}}
              </button>
            </div>
          </div>
        )}}
      </main>
    </div>
  );
}}
'''
    else:
        # Extract business type from prompt for better content
        prompt_lower = prompt.lower()
        
        # Detect profession/business type
        if 'psycholog' in prompt_lower or 'therap' in prompt_lower or 'counsel' in prompt_lower:
            profession = "Psychology Practice"
            tagline = "Professional Mental Health Services"
            services = ["Individual Therapy", "Couples Counseling", "Anxiety Treatment", "Depression Support"]
            cta = "Book a Consultation"
        elif 'lawyer' in prompt_lower or 'attorney' in prompt_lower or 'legal' in prompt_lower:
            profession = "Law Firm"
            tagline = "Expert Legal Representation"
            services = ["Personal Injury", "Family Law", "Business Law", "Estate Planning"]
            cta = "Schedule a Consultation"
        elif 'doctor' in prompt_lower or 'medical' in prompt_lower or 'clinic' in prompt_lower or 'health' in prompt_lower:
            profession = "Medical Practice"
            tagline = "Quality Healthcare Services"
            services = ["General Checkups", "Preventive Care", "Specialist Referrals", "Lab Services"]
            cta = "Book an Appointment"
        elif 'restaurant' in prompt_lower or 'food' in prompt_lower or 'cafe' in prompt_lower:
            profession = "Restaurant"
            tagline = "Delicious Food, Great Experience"
            services = ["Dine-In", "Takeout", "Catering", "Private Events"]
            cta = "View Menu"
        elif 'portfolio' in prompt_lower or 'designer' in prompt_lower or 'creative' in prompt_lower:
            profession = "Creative Portfolio"
            tagline = "Bringing Ideas to Life"
            services = ["Web Design", "Branding", "UI/UX", "Graphic Design"]
            cta = "View Work"
        elif 'coach' in prompt_lower or 'fitness' in prompt_lower or 'trainer' in prompt_lower:
            profession = "Fitness Coaching"
            tagline = "Transform Your Body and Mind"
            services = ["Personal Training", "Nutrition Plans", "Group Classes", "Online Coaching"]
            cta = "Start Your Journey"
        elif 'real estate' in prompt_lower or 'realtor' in prompt_lower or 'property' in prompt_lower:
            profession = "Real Estate"
            tagline = "Find Your Dream Home"
            services = ["Home Buying", "Home Selling", "Property Management", "Market Analysis"]
            cta = "Browse Listings"
        else:
            # Generic business
            profession = "Professional Services"
            tagline = "Quality Service You Can Trust"
            services = ["Consultation", "Custom Solutions", "Ongoing Support", "Expert Advice"]
            cta = "Get Started"
        
        services_jsx = ", ".join([f'"{s}"' for s in services])
        
        return f'''
function App() {{
  const [currentView, setCurrentView] = React.useState("home");
  const [formData, setFormData] = React.useState({{ name: "", email: "", message: "" }});
  const [submitted, setSubmitted] = React.useState(false);
  
  const handleSubmit = (e) => {{
    e.preventDefault();
    console.log("Form submitted:", formData);
    setSubmitted(true);
    setTimeout(() => setSubmitted(false), 3000);
    setFormData({{ name: "", email: "", message: "" }});
  }};
  
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {{/* Navigation */}}
      <nav className="bg-white shadow-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
          <span className="text-xl font-bold text-gray-800">{profession}</span>
          <div className="flex gap-6">
            {{["home", "services", "about", "contact", "settings"].map(view => (
              <button key={{view}} onClick={{() => setCurrentView(view)}}
                className={{currentView === view 
                  ? "text-blue-600 font-medium" 
                  : "text-gray-600 hover:text-blue-600 transition"}}>
                {{view.charAt(0).toUpperCase() + view.slice(1)}}
              </button>
            ))}}
          </div>
        </div>
      </nav>
      
      <main>
        {{/* Hero Section */}}
        {{currentView === "home" && (
          <div>
            <section className="py-20 px-4 bg-gradient-to-r from-blue-600 to-blue-800 text-white">
              <div className="max-w-4xl mx-auto text-center">
                <h1 className="text-5xl font-bold mb-6">{profession}</h1>
                <p className="text-xl mb-8 opacity-90">{tagline}</p>
                <button 
                  onClick={{() => setCurrentView("contact")}}
                  className="px-8 py-4 bg-white text-blue-600 rounded-lg font-semibold hover:bg-gray-100 transition shadow-lg"
                >
                  {cta}
                </button>
              </div>
            </section>
            
            {{/* Services Preview */}}
            <section className="py-16 px-4">
              <div className="max-w-6xl mx-auto">
                <h2 className="text-3xl font-bold text-center mb-12">Our Services</h2>
                <div className="grid md:grid-cols-4 gap-6">
                  {{[{services_jsx}].map((service, i) => (
                    <div key={{i}} className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition text-center">
                      <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span className="text-blue-600 text-xl">{{i + 1}}</span>
                      </div>
                      <h3 className="font-semibold text-lg">{{service}}</h3>
                    </div>
                  ))}}
                </div>
              </div>
            </section>
          </div>
        )}}
        
        {{/* Services Page */}}
        {{currentView === "services" && (
          <section className="py-16 px-4">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-3xl font-bold mb-8">Our Services</h2>
              <div className="space-y-6">
                {{[{services_jsx}].map((service, i) => (
                  <div key={{i}} className="bg-white p-6 rounded-xl shadow-md">
                    <h3 className="font-semibold text-xl mb-2">{{service}}</h3>
                    <p className="text-gray-600">Professional {{service.toLowerCase()}} tailored to your needs. Contact us to learn more about how we can help you.</p>
                  </div>
                ))}}
              </div>
            </div>
          </section>
        )}}
        
        {{/* About Page */}}
        {{currentView === "about" && (
          <section className="py-16 px-4">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-3xl font-bold mb-8">About Us</h2>
              <div className="bg-white p-8 rounded-xl shadow-md">
                <p className="text-gray-600 text-lg leading-relaxed mb-6">
                  We are dedicated professionals committed to providing exceptional service. 
                  With years of experience and a passion for what we do, we strive to exceed 
                  your expectations every time.
                </p>
                <p className="text-gray-600 text-lg leading-relaxed">
                  Our mission is to deliver quality results while building lasting relationships 
                  with our clients. We believe in transparency, integrity, and excellence in 
                  everything we do.
                </p>
              </div>
            </div>
          </section>
        )}}
        
        {{/* Contact Page */}}
        {{currentView === "contact" && (
          <section className="py-16 px-4">
            <div className="max-w-xl mx-auto">
              <h2 className="text-3xl font-bold mb-8">Contact Us</h2>
              {{submitted ? (
                <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
                  Thank you! We will get back to you soon.
                </div>
              ) : null}}
              <form onSubmit={{handleSubmit}} className="bg-white p-8 rounded-xl shadow-md space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Name</label>
                  <input 
                    type="text" 
                    value={{formData.name}}
                    onChange={{(e) => setFormData({{...formData, name: e.target.value}})}}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
                  <input 
                    type="email"
                    value={{formData.email}}
                    onChange={{(e) => setFormData({{...formData, email: e.target.value}})}}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Message</label>
                  <textarea 
                    value={{formData.message}}
                    onChange={{(e) => setFormData({{...formData, message: e.target.value}})}}
                    rows="4"
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  ></textarea>
                </div>
                <button 
                  type="submit"
                  className="w-full py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition"
                >
                  Send Message
                </button>
              </form>
            </div>
          </section>
        )}}
        
        {{/* Settings Page */}}
        {{currentView === "settings" && (
          <section className="py-16 px-4">
            <div className="max-w-md mx-auto">
              <h2 className="text-3xl font-bold mb-8">Settings</h2>
              <div className="bg-white p-6 rounded-xl shadow-md space-y-4">
                <div className="border-b pb-4">
                  <p className="font-medium">Theme</p>
                  <p className="text-sm text-gray-500">Light mode</p>
                </div>
                <div className="border-b pb-4">
                  <p className="font-medium">Notifications</p>
                  <p className="text-sm text-gray-500">Enabled</p>
                </div>
                <div>
                  <p className="font-medium">Version</p>
                  <p className="text-sm text-gray-500">1.0.0</p>
                </div>
              </div>
            </div>
          </section>
        )}}
      </main>
      
      {{/* Footer */}}
      <footer className="bg-gray-800 text-white py-8 mt-16">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <p className="text-gray-400">Built with Faibric</p>
        </div>
      </footer>
    </div>
  );
}}
'''

# Tue Jan  6 10:18:50 PST 2026
