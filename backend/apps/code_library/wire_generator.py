"""
Wire Generator

Generates the React code that connects components together.

This is the "magic" that makes components work together automatically.
Given a set of ComponentInterfaces, it generates:
- Shared state declarations
- Event handler wiring
- Prop passing
- Component composition

WIRING PATTERNS:
1. State Wiring - shared state between components
2. Event Wiring - callbacks that trigger actions
3. Data Wiring - props that flow between components
4. Style Wiring - theme and style propagation
"""

import json
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass

from .connectors import (
    ComponentInterface,
    Connector,
    ConnectorType,
    DataSchema,
)
from .connection_validator import ConnectionValidator


@dataclass
class WiringContext:
    """Context for wire generation."""
    has_data_fetching: bool = False
    has_navigation: bool = False
    has_modals: bool = False
    needs_settings_view: bool = False
    needs_real_data: bool = False  # Gateway API required
    theme_tokens: Set[str] = None
    data_services: List[str] = None  # e.g., ['coingecko', 'yahoo_finance']
    
    def __post_init__(self):
        if self.theme_tokens is None:
            self.theme_tokens = set()
        if self.data_services is None:
            self.data_services = []


class WireGenerator:
    """
    Automatically generates React wiring code.
    
    This connects components by:
    1. Analyzing their interfaces
    2. Finding compatible connections
    3. Generating the glue code
    
    The generated code handles:
    - State management (useState)
    - Effect side effects (useEffect)
    - Event propagation
    - Prop drilling
    """
    
    def __init__(self):
        self.validator = ConnectionValidator()
    
    def generate_wiring(
        self,
        interfaces: List[ComponentInterface],
        app_context: str = ""
    ) -> Dict[str, str]:
        """
        Generate complete wiring code for a set of components.
        
        Returns a dictionary with:
        - imports: Import statements
        - types: TypeScript type definitions
        - state: State declarations
        - effects: useEffect hooks
        - handlers: Event handlers
        - composition: JSX composition code
        - full: Complete wiring code block
        """
        context = self._analyze_context(interfaces)
        
        # Generate each section
        imports = self._generate_imports(interfaces, context)
        types = self._generate_types(interfaces)
        state = self._generate_state(interfaces, context)
        effects = self._generate_effects(interfaces, context)
        handlers = self._generate_handlers(interfaces)
        composition = self._generate_composition(interfaces, context)
        
        # Combine into full wiring block
        full = f"""
// ═══════════════════════════════════════════════════════════════════════════
// GENERATED WIRING - DO NOT EDIT MANUALLY
// ═══════════════════════════════════════════════════════════════════════════

{imports}

{types}

// ═══ STATE ═══
{state}

// ═══ EFFECTS ═══
{effects}

// ═══ HANDLERS ═══
{handlers}

// ═══ COMPOSITION ═══
{composition}
"""
        
        return {
            'imports': imports,
            'types': types,
            'state': state,
            'effects': effects,
            'handlers': handlers,
            'composition': composition,
            'full': full,
        }
    
    def _analyze_context(self, interfaces: List[ComponentInterface]) -> WiringContext:
        """Analyze the component set to determine wiring needs."""
        context = WiringContext()
        
        for interface in interfaces:
            # Check for data fetching components
            if interface.component_type == 'data_fetcher':
                context.has_data_fetching = True
                context.needs_settings_view = True
                context.needs_real_data = True
            
            # Check for navigation
            if interface.component_type == 'navigation':
                context.has_navigation = True
            
            # Check for modals
            if interface.component_type == 'modal':
                context.has_modals = True
            
            # Check for components that typically need real data
            if interface.component_type in ('chart', 'table', 'stats'):
                context.needs_real_data = True
                context.needs_settings_view = True
            
            # Collect theme tokens
            context.theme_tokens.update(interface.theme_tokens)
            
            # Check for data inputs that might need API
            for inp in interface.inputs:
                if inp.data_schema and inp.data_schema.placeholder_symbol:
                    context.needs_settings_view = True
                    context.needs_real_data = True
        
        # Set default data services based on component types
        if context.needs_real_data and not context.data_services:
            context.data_services = ['coingecko']  # Default to crypto as it's free
        
        return context
    
    def _generate_imports(
        self,
        interfaces: List[ComponentInterface],
        context: WiringContext
    ) -> str:
        """Generate React import statements."""
        hooks = {'useState'}
        
        # Add hooks based on component needs
        for interface in interfaces:
            for out in interface.outputs:
                if out.connector_type == ConnectorType.STATE_WRITE:
                    hooks.add('useCallback')
            
            if interface.component_type == 'data_fetcher':
                hooks.add('useEffect')
                hooks.add('useCallback')
        
        if context.has_data_fetching:
            hooks.add('useEffect')
        
        hooks_str = ', '.join(sorted(hooks))
        return f"import React, {{ {hooks_str} }} from 'react';"
    
    def _generate_types(self, interfaces: List[ComponentInterface]) -> str:
        """Generate TypeScript type definitions."""
        types = []
        seen_types = set()
        
        # Standard types
        standard_types = """
// Navigation
interface NavItem {
  id: string;
  label: string;
  icon?: string;
}

// Data Display
interface ChartData {
  label: string;
  value: number;
  color?: string;
}

interface StatItem {
  label: string;
  value: number | string;
  change?: number;
  format?: 'currency' | 'number' | 'percentage';
}

// Forms
interface FormField {
  name: string;
  label: string;
  type: 'text' | 'email' | 'password' | 'number' | 'select' | 'textarea';
  required?: boolean;
  options?: { value: string; label: string }[];
}

// API
interface FetchState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}
"""
        types.append(standard_types)
        
        # Custom types from interfaces
        for interface in interfaces:
            for inp in interface.inputs + interface.outputs:
                if inp.data_schema:
                    ts_type = inp.data_schema.typescript_type
                    
                    # Extract custom type names (not primitives)
                    if ts_type not in seen_types and not self._is_primitive(ts_type):
                        if ts_type.endswith('[]'):
                            base_type = ts_type[:-2]
                            if base_type not in seen_types and not self._is_primitive(base_type):
                                # Generate interface for the array item type
                                types.append(f"// Interface for {base_type} - customize as needed")
                                seen_types.add(base_type)
                        seen_types.add(ts_type)
        
        return '\n'.join(types)
    
    def _generate_state(
        self,
        interfaces: List[ComponentInterface],
        context: WiringContext
    ) -> str:
        """Generate state declarations."""
        states = []
        seen_state = set()
        
        # Always include navigation state
        if context.has_navigation:
            states.append('const [currentView, setCurrentView] = useState<string>("dashboard");')
            seen_state.add('currentView')
        
        # Modal states
        if context.has_modals:
            states.append('const [isModalOpen, setIsModalOpen] = useState<boolean>(false);')
            seen_state.add('isModalOpen')
        
        # Data fetching states
        if context.has_data_fetching:
            states.append('const [loading, setLoading] = useState<boolean>(true);')
            states.append('const [error, setError] = useState<Error | null>(null);')
            seen_state.add('loading')
            seen_state.add('error')
        
        # Collect state from all interfaces
        for interface in interfaces:
            for state_name in interface.provided_state:
                if state_name not in seen_state:
                    state_type = self._infer_state_type(interface, state_name)
                    default_value = self._get_state_default(state_type)
                    states.append(f'const [{state_name}, set{state_name.title()}] = useState<{state_type}>({default_value});')
                    seen_state.add(state_name)
            
            for state_name in interface.required_state:
                if state_name not in seen_state:
                    state_type = self._infer_state_type(interface, state_name)
                    default_value = self._get_state_default(state_type)
                    states.append(f'const [{state_name}, set{state_name.title()}] = useState<{state_type}>({default_value});')
                    seen_state.add(state_name)
        
        return '\n'.join(states)
    
    def _generate_effects(
        self,
        interfaces: List[ComponentInterface],
        context: WiringContext
    ) -> str:
        """Generate useEffect hooks including Gateway API integration."""
        effects = []
        
        # GATEWAY API INTEGRATION - Always generate when real data is needed
        if context.needs_real_data or context.has_data_fetching:
            effects.append("""
// ═══════════════════════════════════════════════════════════════════════════
// GATEWAY API INTEGRATION - MANDATORY FOR REAL DATA
// ═══════════════════════════════════════════════════════════════════════════

// Data state
const [apiData, setApiData] = useState<Record<string, any>>({});
const [loading, setLoading] = useState<boolean>(true);
const [error, setError] = useState<Error | null>(null);

// Gateway fetch function - reuse for all API calls
const fetchFromGateway = async (service: string, endpoint: string) => {
  const response = await fetch("https://faibric-api.onrender.com/api/gateway/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ service, endpoint })
  });
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  const result = await response.json();
  return result.data || result;
};

// Initial data fetch
useEffect(() => {
  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch from available services
      const [cryptoData] = await Promise.all([
        fetchFromGateway("coingecko", "/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd,eur")
          .catch(() => null),
      ]);
      
      setApiData({
        crypto: cryptoData,
        lastUpdated: new Date().toISOString(),
      });
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to fetch data"));
    } finally {
      setLoading(false);
    }
  };
  
  loadData();
  const interval = setInterval(loadData, 30000); // Refresh every 30s
  return () => clearInterval(interval);
}, []);

// Placeholder component for loading/missing data
const DataPlaceholder = ({ symbol = "$", onActivate }: { symbol?: string; onActivate?: () => void }) => (
  <span className="inline-flex items-center gap-2 text-gray-400">
    <span className="font-mono bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded animate-pulse">
      {symbol}---
    </span>
    {onActivate && (
      <button 
        onClick={onActivate}
        className="text-xs text-blue-500 hover:text-blue-700 underline"
      >
        Turn On Real Values
      </button>
    )}
  </span>
);

// Helper to safely get data with placeholder fallback
const getData = (path: string, symbol = "$") => {
  if (loading) return <DataPlaceholder symbol={symbol} />;
  if (error) return <DataPlaceholder symbol={symbol} onActivate={() => setCurrentView("settings")} />;
  
  const keys = path.split(".");
  let value: any = apiData;
  for (const key of keys) {
    value = value?.[key];
  }
  
  if (value === undefined || value === null) {
    return <DataPlaceholder symbol={symbol} onActivate={() => setCurrentView("settings")} />;
  }
  
  // Format based on symbol
  if (symbol === "$") return `$${Number(value).toLocaleString()}`;
  if (symbol === "%") return `${Number(value).toFixed(2)}%`;
  return String(value);
};
""")
        
        return '\n'.join(effects)
    
    def _generate_handlers(self, interfaces: List[ComponentInterface]) -> str:
        """Generate event handlers."""
        handlers = []
        seen_handlers = set()
        
        for interface in interfaces:
            comp_name = interface.component_type.title().replace('_', '')
            
            for output in interface.outputs:
                if output.connector_type == ConnectorType.EVENT_OUT:
                    handler_name = f"handle{comp_name}{output.name.replace('on', '').title()}"
                    
                    if handler_name in seen_handlers:
                        continue
                    seen_handlers.add(handler_name)
                    
                    # Get event signature
                    if output.event_signature:
                        params_str = ', '.join(
                            f"{name}: {typ}" 
                            for name, typ in output.event_signature.params
                        )
                        args_str = ', '.join(name for name, _ in output.event_signature.params)
                    else:
                        params_str = ""
                        args_str = ""
                    
                    # Generate handler based on type
                    if 'Navigate' in handler_name or 'navigate' in output.name.lower():
                        handlers.append(f"""
const {handler_name} = ({params_str}) => {{
  setCurrentView(viewId);
}};
""")
                    elif 'Click' in handler_name:
                        handlers.append(f"""
const {handler_name} = ({params_str}) => {{
  console.log("{interface.component_type} clicked", {args_str});
  // Add your click handler logic here
}};
""")
                    elif 'Submit' in handler_name:
                        handlers.append(f"""
const {handler_name} = ({params_str}) => {{
  console.log("Form submitted", {args_str});
  // Add your form submission logic here
}};
""")
                    elif 'Close' in handler_name or 'close' in output.name.lower():
                        handlers.append(f"""
const {handler_name} = () => {{
  setIsModalOpen(false);
}};
""")
                    else:
                        handlers.append(f"""
const {handler_name} = ({params_str}) => {{
  // Handle {output.name} from {interface.component_type}
  console.log("{output.name}", {args_str});
}};
""")
        
        return '\n'.join(handlers)
    
    def _generate_composition(
        self,
        interfaces: List[ComponentInterface],
        context: WiringContext
    ) -> str:
        """Generate JSX composition code."""
        
        # Sort components by role
        layout = next((i for i in interfaces if i.component_type == 'layout'), None)
        nav = next((i for i in interfaces if i.component_type == 'navigation'), None)
        footer = next((i for i in interfaces if i.component_type == 'footer'), None)
        
        content_components = [
            i for i in interfaces 
            if i.component_type not in ('layout', 'navigation', 'footer')
        ]
        
        lines = ['return (']
        
        # With layout wrapper
        if layout:
            lines.append('  <div className="min-h-screen flex">')
            
            # Sidebar navigation
            if nav:
                nav_props = self._generate_props(nav)
                lines.append(f'    <aside className="w-64 bg-gray-900 text-white">')
                lines.append(f'      <Navigation {nav_props} />')
                lines.append(f'    </aside>')
            
            # Main content area
            lines.append('    <main className="flex-1 bg-gray-50 dark:bg-gray-900">')
            
            # View switching for navigation
            if context.has_navigation:
                lines.append('      {/* View switching based on currentView */}')
                for comp in content_components:
                    comp_name = comp.component_type.title().replace('_', '')
                    view_id = comp.component_type.lower()
                    comp_props = self._generate_props(comp)
                    lines.append(f'      {{currentView === "{view_id}" && <{comp_name} {comp_props} />}}')
                
                # Settings view
                if context.needs_settings_view:
                    lines.append('      {currentView === "settings" && <SettingsView />}')
            else:
                # No navigation - render all content components
                for comp in content_components:
                    comp_name = comp.component_type.title().replace('_', '')
                    comp_props = self._generate_props(comp)
                    lines.append(f'      <{comp_name} {comp_props} />')
            
            lines.append('    </main>')
            lines.append('  </div>')
        else:
            # No layout - simple div wrapper
            lines.append('  <div className="min-h-screen bg-gray-50 dark:bg-gray-900">')
            
            if nav:
                nav_props = self._generate_props(nav)
                lines.append(f'    <Navigation {nav_props} />')
            
            for comp in content_components:
                comp_name = comp.component_type.title().replace('_', '')
                comp_props = self._generate_props(comp)
                lines.append(f'    <{comp_name} {comp_props} />')
            
            if footer:
                footer_props = self._generate_props(footer)
                lines.append(f'    <Footer {footer_props} />')
            
            lines.append('  </div>')
        
        lines.append(');')
        
        return '\n'.join(lines)
    
    def _generate_props(self, interface: ComponentInterface) -> str:
        """Generate props string for a component."""
        props = []
        
        for inp in interface.inputs:
            if inp.connector_type == ConnectorType.STATE_READ:
                # Pass state directly
                props.append(f'{inp.name}={{{inp.name}}}')
            
            elif inp.connector_type == ConnectorType.DATA_IN:
                # Only include if no default or required
                if inp.required and inp.default_value is None:
                    props.append(f'{inp.name}={{/* TODO: provide {inp.name} */}}')
        
        for output in interface.outputs:
            if output.connector_type == ConnectorType.EVENT_OUT:
                comp_name = interface.component_type.title().replace('_', '')
                event_name = output.name.replace('on', '').title()
                handler_name = f"handle{comp_name}{event_name}"
                props.append(f'{output.name}={{{handler_name}}}')
        
        return ' '.join(props)
    
    def _is_primitive(self, ts_type: str) -> bool:
        """Check if a TypeScript type is primitive."""
        primitives = {
            'string', 'number', 'boolean', 'null', 'undefined', 
            'any', 'unknown', 'never', 'void', 'T',
            'Record<string, any>', 'Record<string, T>',
        }
        return ts_type in primitives or ts_type.startswith("'")
    
    def _infer_state_type(self, interface: ComponentInterface, state_name: str) -> str:
        """Infer the TypeScript type for a state variable."""
        
        # Check outputs that provide this state
        for output in interface.outputs:
            if output.name == state_name and output.data_schema:
                return output.data_schema.typescript_type
        
        # Check inputs that read this state
        for inp in interface.inputs:
            if inp.name == state_name and inp.data_schema:
                return inp.data_schema.typescript_type
        
        # Common defaults
        defaults = {
            'currentView': 'string',
            'isOpen': 'boolean',
            'loading': 'boolean',
            'error': 'Error | null',
            'data': 'any',
        }
        
        return defaults.get(state_name, 'any')
    
    def _get_state_default(self, ts_type: str) -> str:
        """Get default value for a TypeScript type."""
        
        defaults = {
            'string': '"dashboard"',
            'boolean': 'false',
            'number': '0',
            'Error | null': 'null',
            'null': 'null',
        }
        
        if ts_type in defaults:
            return defaults[ts_type]
        
        if ts_type.endswith('[]'):
            return '[]'
        
        if ts_type.startswith('Record<'):
            return '{}'
        
        return 'null'


def generate_component_wiring(interfaces: List[ComponentInterface]) -> str:
    """
    Convenience function to generate wiring code.
    
    Returns the full wiring code block ready to inject into App.tsx.
    """
    generator = WireGenerator()
    result = generator.generate_wiring(interfaces)
    return result['full']


def generate_wiring_prompt_injection(
    interfaces: List[ComponentInterface],
    needs_real_data: bool = False
) -> str:
    """
    Generate a prompt injection for the AI composer.
    
    This gives the AI the wiring "blueprint" to follow,
    INCLUDING Gateway API integration when real data is needed.
    """
    generator = WireGenerator()
    result = generator.generate_wiring(interfaces)
    
    gateway_section = ""
    if needs_real_data:
        gateway_section = """

═══════════════════════════════════════════════════════════════════════════════
GATEWAY API INTEGRATION (MANDATORY - NO FAKE DATA)
═══════════════════════════════════════════════════════════════════════════════

⛔ FORBIDDEN - Never use these patterns:
   - const data = [{...}, {...}]           // Hardcoded arrays
   - const prices = { bitcoin: 45000 }     // Fake values
   - useState([{ name: "...", value: 100 }]) // Mock data in state

[OK] REQUIRED - Always use this pattern:

const [apiData, setApiData] = useState<Record<string, any>>({});
const [loading, setLoading] = useState(true);
const [error, setError] = useState<Error | null>(null);

const fetchFromGateway = async (service: string, endpoint: string) => {
  const response = await fetch("https://faibric-api.onrender.com/api/gateway/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ service, endpoint })
  });
  const result = await response.json();
  return result.data || result;
};

useEffect(() => {
  const loadData = async () => {
    try {
      setLoading(true);
      const data = await fetchFromGateway("coingecko", "/simple/price?ids=bitcoin,ethereum&vs_currencies=usd");
      setApiData({ crypto: data });
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Fetch failed"));
    } finally {
      setLoading(false);
    }
  };
  loadData();
  const interval = setInterval(loadData, 30000);
  return () => clearInterval(interval);
}, []);

// Show placeholder while loading
{loading ? <span className="text-gray-400">$---</span> : <span>${apiData.crypto?.bitcoin?.usd}</span>}

Available Gateway Services:
- coingecko: /simple/price?ids=bitcoin,ethereum&vs_currencies=usd
- yahoo_finance: /chart/AAPL
- restcountries: /all

"""
    
    return f"""
═══════════════════════════════════════════════════════════════════════════════
COMPONENT WIRING BLUEPRINT (FOLLOW EXACTLY)
═══════════════════════════════════════════════════════════════════════════════
{gateway_section}
STATE DECLARATIONS:
{result['state']}

EFFECTS (INCLUDE THESE):
{result['effects']}

EVENT HANDLERS:
{result['handlers']}

COMPOSITION PATTERN:
{result['composition']}

═══════════════════════════════════════════════════════════════════════════════
CRITICAL: 
1. Include ALL state declarations above
2. Include the useEffect for data fetching
3. Include ALL event handlers
4. Follow the composition pattern for layout
═══════════════════════════════════════════════════════════════════════════════
"""

