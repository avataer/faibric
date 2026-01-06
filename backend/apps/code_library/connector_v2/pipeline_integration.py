"""
Faibric Connector V2 - Pipeline Integration

Replaces AI-generated wiring with deterministic Connector V2.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple

from .types import PortType, BaseType, SemanticType, VIEW_ID, STRING, LOADING
from .ports import (
    ComponentSpec, Port, PortKind, PortDirection,
    data_in, data_out, event_in, event_out, state_read, state_write
)
from .solver import Solver, ConnectionGraph
from .generator import CodeGenerator

logger = logging.getLogger(__name__)


class ComponentSpecExtractor:
    """
    Extracts ComponentSpec from library component code.
    
    Analyzes component source code to determine its ports.
    """
    
    @staticmethod
    def extract_from_code(component_type: str, code: str) -> ComponentSpec:
        """
        Extract ComponentSpec from component source code.
        
        Parses the code to find:
        - Props (input ports)
        - Callbacks (event ports)
        - State dependencies (state ports)
        """
        import re
        
        spec = ComponentSpec(
            component_type=component_type,
            code=code
        )
        
        # Find props interface/type
        # Pattern: interface ComponentProps { ... } or type ComponentProps = { ... }
        props_match = re.search(
            r'(?:interface|type)\s+\w*Props\w*\s*(?:=\s*)?\{([^}]+)\}',
            code,
            re.MULTILINE | re.DOTALL
        )
        
        if props_match:
            props_body = props_match.group(1)
            
            # Extract each prop
            prop_pattern = re.compile(r'(\w+)(\?)?:\s*([^;,\n]+)')
            for match in prop_pattern.finditer(props_body):
                prop_name = match.group(1)
                is_optional = match.group(2) == '?'
                type_str = match.group(3).strip()
                
                # Determine port kind and type
                if 'on' in prop_name.lower() and '(' in type_str:
                    # This is a callback/event
                    params = ComponentSpecExtractor._parse_callback_params(type_str)
                    spec.inputs.append(event_in(prop_name, params, required=not is_optional))
                else:
                    # This is a data prop
                    port_type = ComponentSpecExtractor._parse_type(type_str)
                    spec.inputs.append(data_in(prop_name, port_type, required=not is_optional))
        
        # Check for state reads (useState or context)
        if 'currentView' in code or 'setCurrentView' in code:
            spec.inputs.append(state_read('currentView', VIEW_ID()))
        
        # Check for event emissions
        if 'onNavigate' in code:
            spec.outputs.append(event_out('onNavigate', [('viewId', 'string')]))
        
        return spec
    
    @staticmethod
    def _parse_callback_params(type_str: str) -> List[Tuple[str, str]]:
        """Parse callback parameters from type string."""
        import re
        
        # Pattern: (param: Type, ...) => void
        match = re.search(r'\(([^)]*)\)', type_str)
        if not match:
            return []
        
        params_str = match.group(1)
        if not params_str.strip():
            return []
        
        params = []
        for part in params_str.split(','):
            part = part.strip()
            if ':' in part:
                name, typ = part.split(':', 1)
                params.append((name.strip(), typ.strip()))
        
        return params
    
    @staticmethod
    def _parse_type(type_str: str) -> PortType:
        """Parse TypeScript type string to PortType."""
        type_str = type_str.strip()
        
        # Check for common types
        type_map = {
            'string': PortType(base=BaseType.STRING),
            'number': PortType(base=BaseType.NUMBER),
            'boolean': PortType(base=BaseType.BOOLEAN),
            'Date': PortType(base=BaseType.DATE),
            'any': PortType(base=BaseType.ANY),
        }
        
        if type_str in type_map:
            return type_map[type_str]
        
        # Check for arrays
        if type_str.endswith('[]'):
            inner_type = type_str[:-2]
            return PortType(
                base=BaseType.ANY,
                element_type=ComponentSpecExtractor._parse_type(inner_type)
            )
        
        # Check for semantic types by name
        semantic_keywords = {
            'NavItem': SemanticType.NAV_ITEMS,
            'TableRow': SemanticType.TABLE_DATA,
            'ChartPoint': SemanticType.CHART_POINTS,
            'FormField': SemanticType.FORM_FIELDS,
            'User': SemanticType.USER,
        }
        
        for keyword, semantic in semantic_keywords.items():
            if keyword in type_str:
                return PortType(base=BaseType.ANY, semantic=semantic)
        
        # Default to ANY
        return PortType(base=BaseType.ANY)


class ConnectorPipeline:
    """
    Main integration point for Connector V2.
    
    Replaces the AI-based composition with deterministic wiring.
    """
    
    def __init__(self):
        self.solver = Solver()
        self.generator = CodeGenerator(use_typescript=True)
        self.extractor = ComponentSpecExtractor()
    
    def compose_app(
        self,
        components: Dict[str, str],  # component_id -> source code
        component_types: Dict[str, str] = None,  # component_id -> type name
        prompt: str = ""
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Compose a complete App.tsx from component source code.
        
        Args:
            components: Dict mapping component ID to its source code
            component_types: Optional dict mapping component ID to type name
            prompt: Original user prompt (for metadata)
            
        Returns:
            (app_code, metadata)
        """
        start_time = time.time()
        
        # Step 1: Extract ComponentSpecs from source code
        specs: Dict[str, ComponentSpec] = {}
        
        for comp_id, code in components.items():
            comp_type = (component_types or {}).get(comp_id, comp_id)
            spec = self.extractor.extract_from_code(comp_type, code)
            spec.code = code  # Store original code
            specs[comp_id] = spec
            
            logger.debug(f"[CONNECTOR] Extracted spec for {comp_id}: "
                        f"{len(spec.inputs)} inputs, {len(spec.outputs)} outputs")
        
        # Step 2: Solve the wiring problem
        graph = self.solver.solve(specs)
        
        if not graph.is_valid:
            logger.warning(f"[CONNECTOR] Unsatisfied inputs: {graph.unsatisfied_inputs}")
        
        logger.info(f"[CONNECTOR] Solved: {len(graph.connections)} connections, "
                   f"{len(graph.shared_states)} shared states")
        
        # Step 3: Generate the App.tsx
        app_code = self.generator.generate(graph)
        
        generation_time = (time.time() - start_time) * 1000
        
        # Build metadata
        metadata = {
            "pipeline": "connector_v2",
            "generation_time_ms": round(generation_time, 2),
            "components": len(components),
            "connections": len(graph.connections),
            "shared_states": len(graph.shared_states),
            "unsatisfied_inputs": len(graph.unsatisfied_inputs),
            "valid": graph.is_valid,
            "deterministic": True,
            "type_safe": True
        }
        
        logger.info(f"[CONNECTOR] Generated App.tsx in {generation_time:.2f}ms")
        
        return app_code, metadata
    
    def compose_from_specs(
        self,
        specs: Dict[str, ComponentSpec]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Compose App.tsx from pre-defined ComponentSpecs.
        
        Useful when specs are defined manually or cached.
        """
        start_time = time.time()
        
        graph = self.solver.solve(specs)
        app_code = self.generator.generate(graph)
        
        generation_time = (time.time() - start_time) * 1000
        
        metadata = {
            "pipeline": "connector_v2",
            "generation_time_ms": round(generation_time, 2),
            "components": len(specs),
            "connections": len(graph.connections),
            "shared_states": len(graph.shared_states),
            "valid": graph.is_valid
        }
        
        return app_code, metadata


# Global instance
connector_pipeline = ConnectorPipeline()


def compose_app_v2(
    components: Dict[str, str],
    component_types: Dict[str, str] = None,
    prompt: str = ""
) -> Tuple[str, Dict[str, Any]]:
    """
    Convenience function for composing apps with Connector V2.
    
    This is the main entry point for the component pipeline.
    """
    return connector_pipeline.compose_app(components, component_types, prompt)

