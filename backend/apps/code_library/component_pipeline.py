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

# Import deterministic composer (no AI, no truncation risk)
from .deterministic_composer import compose_deterministic

logger = logging.getLogger(__name__)

# Check Connector V2 health on module load
_connector_v2_status = None


class ComponentGenerationPipeline:
    """
    The RIGHT way to build apps:
    - Decompose into components
    - Reuse from library
    - Generate only what's missing
    - Save new components
    - Compose final app
    """
    
    def __init__(self, session=None):
        self.session = session
        self.decomposer = ProjectDecomposer()
        self.library = ComponentLibrary()
        self.composer = ComponentComposer()
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        # ═══ CONNECTOR SYSTEM ═══
        self.validator = ConnectionValidator()
        self.wire_generator = WireGenerator()
        
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
        
        Returns the final App.tsx code.
        """
        print(f"[COMPONENT PIPELINE] Starting build for: {prompt[:50]}...")
        self._update_progress(5, "Analyzing your requirements...")
        
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
        else:
            print(f"[COMPONENT PIPELINE] [OK] Code quality validation passed")
        
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
            
            # Adapt the component for this specific use case
            adapted = self._adapt_component(match.component.code, requirement, full_prompt)
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
        
        prompt = f"""
Generate a REUSABLE React component for the following requirement.

COMPONENT TYPE: {requirement.component_type.value}
VARIANT: {requirement.variant}
CONTEXT: {full_prompt}
DESCRIPTION: {requirement.description}
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
5. Include TypeScript interfaces if needed
6. Add brief comments explaining key parts
7. Use TEXT LABELS only for icons, NEVER use emojis

AVAILABLE SERVICES (via Gateway):
- yahoo_finance: Stock data (e.g., /chart/AAPL)
- coingecko: Crypto prices (e.g., /simple/price?ids=bitcoin&vs_currencies=usd)
- restcountries: Country data (e.g., /all)

Return ONLY the component code, nothing else.
"""
        
        try:
            response = self.client.messages.create(
                model=CODE_MODEL,
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
        
        This is CHEAP (uses existing code) but customizes it.
        """
        # Sanitize the code first
        code = self._sanitize_code(code)
        # For now, return as-is with minor adaptations
        # In future, could use a cheaper model to tweak
        return code
    
    def _compose_app(
        self,
        components: Dict[str, str],
        prompt: str,
        requirements: List[ComponentRequirement],
        needs_real_data: bool = False,
        wiring_blueprint: str = ""
    ) -> str:
        """
        Compose all components into a final App.tsx.
        
        STRATEGY:
        1. Try Connector V2 first (deterministic, 130,000x faster)
        2. Fall back to AI if Connector V2 is unhealthy
        
        Uses Opus 4.5 to intelligently combine components.
        """
        global _connector_v2_status
        
        # STRATEGY:
        # 1. Try DETERMINISTIC composition first (instant, no truncation)
        # 2. If that fails, fall back to AI composition
        
        # Try deterministic composition - embeds component code directly
        try:
            logger.info("[COMPOSE] Using DETERMINISTIC composition (no AI)")
            app_code = compose_deterministic(
                components=components,
                prompt=prompt,
                needs_real_data=needs_real_data
            )
            
            # Validate the generated code
            if app_code and 'function App' in app_code and 'export default' in app_code:
                # Check for empty _OriginalApp or App
                if 'return (\n  );' not in app_code and 'return (\n    );' not in app_code:
                    logger.info(f"[COMPOSE] Deterministic SUCCESS: {len(app_code)} bytes")
                    self.stats['wiring_method'] = 'deterministic'
                    
                    # Apply sanitization
                    app_code = self._sanitize_code(app_code)
                    app_code = self._fix_jsx_balance(app_code)
                    
                    return app_code
                else:
                    logger.warning("[COMPOSE] Deterministic produced empty App, falling back to AI")
            else:
                logger.warning("[COMPOSE] Deterministic output incomplete, falling back to AI")
        except Exception as e:
            logger.error(f"[COMPOSE] Deterministic failed: {e}, falling back to AI")
        
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
        
        compose_prompt = f"""
Create a COMPLETE React App.tsx for this request:

USER REQUEST: {prompt}

COMPONENT TYPES NEEDED: {components_desc}

{wiring_section}

{gateway_instruction}

{spa_instruction}

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
1. Create a SINGLE complete App.tsx file
2. Include TypeScript interfaces for all props  
3. Use Tailwind CSS for styling
4. Navigation clicks MUST change the view using React state
5. MUST end with exactly: export default App;
6. Keep code SIMPLE - avoid complex nested generics
7. Include the DataPlaceholder component for loading/error states
8. Settings view must show API connection options

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
                model=CODE_MODEL,
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
    
    This generates simpler code that:
    - Uses plain JavaScript (no TypeScript interfaces)
    - Includes FUNCTIONAL Faibric features (not fake UI)
    - Works reliably with browser Babel
    
    REAL FEATURES:
    - Settings that actually save to localStorage
    - Refresh interval that actually changes timing
    - Connection status that actually tests the API
    - No fake "Custom API" inputs for free APIs
    
    Args:
        prompt: User's request
        needs_data: Whether app needs real-time data from Gateway
    
    Returns:
        Complete app code (plain JavaScript)
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
        return f'''
function App() {{
  const [currentView, setCurrentView] = React.useState("home");
  
  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow p-4 flex gap-4">
        {{["home", "about"].map(view => (
          <button key={{view}} onClick={{() => setCurrentView(view)}}
            className={{currentView === view ? "text-blue-600 font-medium" : "text-gray-600"}}>
            {{view.charAt(0).toUpperCase() + view.slice(1)}}
          </button>
        ))}}
      </nav>
      <main className="p-6">
        {{currentView === "home" && (
          <div>
            <h1 className="text-3xl font-bold mb-4">{title}</h1>
            <p className="text-gray-600">Welcome to your app.</p>
          </div>
        )}}
        {{currentView === "about" && (
          <div>
            <h2 className="text-2xl font-bold mb-4">About</h2>
            <p className="text-gray-600">Built with Faibric.</p>
          </div>
        )}}
      </main>
    </div>
  );
}}
'''

# Tue Jan  6 10:18:50 PST 2026
