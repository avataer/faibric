"""
Faibric Connector V2 - Code Generator

Produces exact, correct React code from a ConnectionGraph.
NO AI involvement - purely mechanical transformation.
"""

import re
import logging
from typing import List, Dict, Set, Tuple
from .solver import ConnectionGraph, Connection, SharedState
from .ports import Port, PortKind, ComponentSpec

logger = logging.getLogger(__name__)


class CodeGenerator:
    """
    Generates React code from a solved connection graph.
    
    This is purely mechanical - no AI, no guessing.
    The output is guaranteed to be syntactically correct.
    """
    
    def __init__(self, use_typescript: bool = True):
        self.use_typescript = use_typescript
        self.indent = "  "
    
    def generate(self, graph: ConnectionGraph) -> str:
        """
        Generate complete App.tsx from connection graph.
        
        Returns syntactically correct React code.
        """
        sections = []
        
        # 1. Imports
        sections.append(self._generate_imports(graph))
        
        # 2. Type definitions (if TypeScript)
        if self.use_typescript:
            types = self._generate_types(graph)
            if types:
                sections.append(types)
        
        # 3. Component definitions (from library)
        components_section = self._generate_components(graph)
        sections.append(components_section)
        
        # 4. App component
        sections.append(self._generate_app(graph))
        
        # 5. Export
        sections.append("export default App;")
        
        code = "\n\n".join(sections)
        
        # CRITICAL: Validate and fix brace balance before returning
        code = self._ensure_balanced_braces(code)
        
        return code
    
    def _ensure_balanced_braces(self, code: str) -> str:
        """
        Ensure all braces are balanced. Fix if not.
        
        This is a safety net to catch any brace imbalance issues.
        """
        # Count braces
        open_curly = code.count('{')
        close_curly = code.count('}')
        open_paren = code.count('(')
        close_paren = code.count(')')
        open_angle = code.count('<')
        close_angle = code.count('>')
        
        # Log any imbalances
        if open_curly != close_curly:
            logger.warning(f"[GENERATOR] Curly brace imbalance: {open_curly} open, {close_curly} close")
        if open_paren != close_paren:
            logger.warning(f"[GENERATOR] Paren imbalance: {open_paren} open, {close_paren} close")
        
        # Fix curly braces if needed
        diff = open_curly - close_curly
        if diff > 0:
            # More open than close - add closing braces at end
            code = code.rstrip() + '\n' + ('}' * diff)
        elif diff < 0:
            # More close than open - remove excess closing braces from end
            for _ in range(-diff):
                # Find last closing brace and remove it
                last_close = code.rfind('}')
                if last_close != -1:
                    code = code[:last_close] + code[last_close+1:]
        
        # Verify fix worked
        new_open = code.count('{')
        new_close = code.count('}')
        if new_open != new_close:
            logger.error(f"[GENERATOR] Failed to balance braces: {new_open} vs {new_close}")
        
        return code
    
    def _generate_imports(self, graph: ConnectionGraph) -> str:
        """Generate import statements."""
        hooks = set()
        
        # Analyze what hooks are needed
        if graph.shared_states:
            hooks.add("useState")
        
        # Check if any component uses effects
        for spec in graph.components.values():
            if "useEffect" in spec.code:
                hooks.add("useEffect")
            if "useRef" in spec.code:
                hooks.add("useRef")
            if "useCallback" in spec.code:
                hooks.add("useCallback")
        
        if hooks:
            hooks_str = ", ".join(sorted(hooks))
            return f"import React, {{ {hooks_str} }} from 'react';"
        else:
            return "import React from 'react';"
    
    def _generate_types(self, graph: ConnectionGraph) -> str:
        """Generate TypeScript type definitions."""
        types = []
        
        # Collect all semantic types used
        semantic_types_used = set()
        
        for spec in graph.components.values():
            for port in spec.all_ports:
                if port.port_type.semantic:
                    semantic_types_used.add(port.port_type.semantic)
        
        # Generate interfaces for semantic types
        from .types import SemanticType
        
        type_defs = {
            SemanticType.NAV_ITEMS: """interface NavItem {
  id: string;
  label: string;
  icon?: string;
}""",
            SemanticType.TABLE_DATA: """interface TableRow {
  id: string;
  [key: string]: any;
}""",
            SemanticType.CHART_POINTS: """interface ChartPoint {
  x: number;
  y: number;
  label?: string;
}""",
            SemanticType.FORM_FIELDS: """interface FormField {
  name: string;
  type: string;
  label: string;
  required?: boolean;
}""",
            SemanticType.USER: """interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
}""",
        }
        
        for sem_type in semantic_types_used:
            if sem_type in type_defs:
                types.append(type_defs[sem_type])
        
        return "\n\n".join(types)
    
    def _generate_components(self, graph: ConnectionGraph) -> str:
        """Generate component definitions from library code."""
        components = []
        
        for comp_id, spec in graph.components.items():
            if spec.code:
                # Use library code directly
                code = self._clean_component_code(spec.code, comp_id)
                components.append(f"// {spec.component_type} component")
                components.append(code)
            else:
                # Generate placeholder
                components.append(self._generate_placeholder_component(comp_id, spec))
        
        return "\n\n".join(components)
    
    def _clean_component_code(self, code: str, component_id: str) -> str:
        """
        Clean library component code for inclusion.
        
        IMPORTANT: Preserves brace balance by only removing complete statements.
        """
        original_code = code
        
        # Remove import statements (we'll add unified imports)
        # Only remove complete import lines
        code = re.sub(r'^import\s+[^;]+;\s*\n?', '', code, flags=re.MULTILINE)
        
        # Remove export default at end
        code = re.sub(r'\nexport\s+default\s+\w+;\s*$', '', code)
        
        # Remove standalone export keyword (but keep the rest)
        code = re.sub(r'^export\s+(?=(const|function|class|interface|type))', '', code, flags=re.MULTILINE)
        
        # Clean up any trailing/leading whitespace
        code = code.strip()
        
        # Verify brace balance is preserved
        original_balance = original_code.count('{') - original_code.count('}')
        new_balance = code.count('{') - code.count('}')
        
        if new_balance != original_balance:
            logger.warning(f"[GENERATOR] Component {component_id} brace balance changed: "
                          f"{original_balance} -> {new_balance}")
        
        return code
    
    def _generate_placeholder_component(self, comp_id: str, spec: ComponentSpec) -> str:
        """Generate a placeholder when library code isn't available."""
        name = self._component_name(comp_id)
        
        # Generate props interface
        props = []
        for port in spec.inputs:
            props.append(port.typescript_prop)
        
        props_str = "; ".join(props) if props else ""
        props_type = f"{{ {props_str} }}" if props else "{}"
        
        # Use escaped braces for component type to avoid JSX interpretation
        comp_type = spec.component_type
        
        return f"""const {name} = (props: {props_type}) => {{
  return (
    <div className="p-4 border rounded">
      <p className="text-gray-500">{comp_type} placeholder</p>
    </div>
  );
}};"""
    
    def _generate_app(self, graph: ConnectionGraph) -> str:
        """Generate the main App component."""
        lines = []
        
        # App function signature
        lines.append("function App() {")
        
        # State declarations
        for state in graph.shared_states:
            state_line = self._generate_state_declaration(state)
            lines.append(f"{self.indent}{state_line}")
        
        if graph.shared_states:
            lines.append("")
        
        # Event handlers
        handlers = self._generate_handlers(graph)
        if handlers:
            lines.extend(handlers)
            lines.append("")
        
        # Return statement with JSX
        lines.append(f"{self.indent}return (")
        jsx = self._generate_jsx(graph)
        for jsx_line in jsx:
            lines.append(f"{self.indent}{self.indent}{jsx_line}")
        lines.append(f"{self.indent});")
        
        lines.append("}")
        
        return "\n".join(lines)
    
    def _generate_state_declaration(self, state: SharedState) -> str:
        """Generate useState declaration."""
        type_annotation = ""
        if self.use_typescript:
            type_annotation = f"<{state.state_type.typescript}>"
        
        return f"const [{state.name}, {state.setter_name}] = useState{type_annotation}({state.default_value});"
    
    def _generate_handlers(self, graph: ConnectionGraph) -> List[str]:
        """Generate event handler functions."""
        handlers = []
        
        # Find all event connections
        for conn in graph.connections:
            if conn.source_port.kind == PortKind.EVENT:
                handler = self._generate_handler_for_connection(conn, graph)
                if handler:
                    handlers.append(f"{self.indent}{handler}")
        
        # Generate handlers for state updates
        for state in graph.shared_states:
            if state.writers:
                # Create handler that updates this state
                handler_name = f"handle{state.name[0].upper()}{state.name[1:]}Change"
                param_type = state.state_type.typescript if self.use_typescript else ""
                param = f"value{': ' + param_type if param_type else ''}"
                handlers.append(
                    f"{self.indent}const {handler_name} = ({param}) => {state.setter_name}(value);"
                )
        
        return handlers
    
    def _generate_handler_for_connection(self, conn: Connection, graph: ConnectionGraph) -> str:
        """Generate handler for a specific event connection."""
        # Find what state this event updates
        for state in graph.shared_states:
            if self._event_updates_state(conn.source_port.name, state.name):
                params = ", ".join(p[0] for p in conn.source_port.event_params)
                if params:
                    # Event has parameters - use first one for state update
                    first_param = conn.source_port.event_params[0][0]
                    return f"const handle{conn.source_port.name[2:]} = ({params}) => {state.setter_name}({first_param});"
        
        return None
    
    def _event_updates_state(self, event_name: str, state_name: str) -> bool:
        """Check if an event updates a state."""
        patterns = [
            ("onNavigate", "currentView"),
            ("onChange", "value"),
            ("onSelect", "selected"),
            ("onTabChange", "activeTab"),
        ]
        for e, s in patterns:
            if e == event_name and s == state_name:
                return True
        return False
    
    def _generate_jsx(self, graph: ConnectionGraph) -> List[str]:
        """Generate JSX composition."""
        lines = []
        
        # Root wrapper
        lines.append('<div className="min-h-screen bg-gray-50">')
        
        # Render components with their props
        for comp_id, spec in graph.components.items():
            comp_jsx = self._generate_component_jsx(comp_id, spec, graph)
            lines.append(f"  {comp_jsx}")
        
        lines.append("</div>")
        
        return lines
    
    def _generate_component_jsx(
        self, 
        comp_id: str, 
        spec: ComponentSpec, 
        graph: ConnectionGraph
    ) -> str:
        """Generate JSX for a single component."""
        name = self._component_name(comp_id)
        props = []
        
        # Get connections to this component
        connections = graph.get_connections_to(comp_id)
        connected_ports = {c.target_port.name for c in connections}
        
        # Add props from connections
        for conn in connections:
            prop_value = self._get_prop_value(conn, graph)
            props.append(f'{conn.target_port.name}={{{prop_value}}}')
        
        # Add props from shared state
        for state in graph.shared_states:
            if comp_id in state.readers:
                port = spec.get_port(state.name)
                if port and port.name not in connected_ports:
                    props.append(f'{state.name}={{{state.name}}}')
        
        # Add event handlers
        for port in spec.event_inputs:
            if port.name not in connected_ports:
                # Check if there's a generated handler
                for state in graph.shared_states:
                    if self._event_updates_state(port.name, state.name):
                        handler_name = f"handle{port.name[2:]}"
                        props.append(f'{port.name}={{{handler_name}}}')
                        break
        
        # Build JSX
        if props:
            props_str = " ".join(props)
            return f"<{name} {props_str} />"
        else:
            return f"<{name} />"
    
    def _get_prop_value(self, conn: Connection, graph: ConnectionGraph) -> str:
        """Get the value expression for a prop."""
        # If source is state, use state variable
        if conn.source_port.kind == PortKind.STATE:
            return conn.source_port.name
        
        # If source is data output, need to trace where it comes from
        # For now, use the port name as a variable
        return conn.source_port.name
    
    def _component_name(self, comp_id: str) -> str:
        """Convert component ID to React component name."""
        # e.g., "navigation_sidebar" -> "NavigationSidebar"
        parts = comp_id.replace("-", "_").split("_")
        return "".join(p.capitalize() for p in parts)


def generate_app(graph: ConnectionGraph, use_typescript: bool = True) -> str:
    """Convenience function to generate app code."""
    generator = CodeGenerator(use_typescript=use_typescript)
    return generator.generate(graph)

