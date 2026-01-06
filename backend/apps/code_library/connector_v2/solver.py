"""
Faibric Connector V2 - Connection Solver

The core innovation: automatic wiring through constraint satisfaction.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from enum import Enum

from .types import PortType, check_compatibility, CompatibilityResult
from .ports import Port, PortKind, PortDirection, ComponentSpec


@dataclass
class Connection:
    """A single connection between two ports."""
    source_component: str      # Component ID providing the value
    source_port: Port          # Output port
    target_component: str      # Component ID receiving the value
    target_port: Port          # Input port
    
    # Connection quality
    compatibility: CompatibilityResult = CompatibilityResult.EXACT
    score: float = 1.0
    
    # Generated code hint
    requires_coercion: bool = False
    coercion_code: str = ""
    
    def __str__(self):
        return f"{self.source_component}.{self.source_port.name} -> {self.target_component}.{self.target_port.name}"


@dataclass
class SharedState:
    """State that is shared between components."""
    name: str                  # State variable name
    state_type: PortType       # Type of the state
    default_value: str         # Default value (as code)
    
    # Which components read/write
    readers: List[str] = field(default_factory=list)
    writers: List[str] = field(default_factory=list)
    
    @property
    def setter_name(self) -> str:
        return f"set{self.name[0].upper()}{self.name[1:]}"


@dataclass 
class ConnectionGraph:
    """
    Complete wiring solution for a set of components.
    
    This is the output of the solver.
    """
    components: Dict[str, ComponentSpec]  # id -> spec
    connections: List[Connection]
    shared_states: List[SharedState]
    
    # Quality metrics
    total_score: float = 0.0
    unsatisfied_inputs: List[Tuple[str, Port]] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """A valid graph has no unsatisfied required inputs."""
        return len(self.unsatisfied_inputs) == 0
    
    def get_connections_to(self, component_id: str) -> List[Connection]:
        return [c for c in self.connections if c.target_component == component_id]
    
    def get_connections_from(self, component_id: str) -> List[Connection]:
        return [c for c in self.connections if c.source_component == component_id]


class Solver:
    """
    Solves the component wiring problem.
    
    Given a set of components, finds the optimal set of connections
    that satisfies all required inputs while minimizing shared state.
    """
    
    def __init__(self):
        self.debug = False
    
    def solve(self, components: Dict[str, ComponentSpec]) -> ConnectionGraph:
        """
        Find optimal wiring for a set of components.
        
        Args:
            components: Dict mapping component ID to its specification
            
        Returns:
            ConnectionGraph with all connections and shared state
        """
        # Phase 1: Collect all ports
        all_inputs: List[Tuple[str, Port]] = []
        all_outputs: List[Tuple[str, Port]] = []
        
        for comp_id, spec in components.items():
            for port in spec.inputs:
                all_inputs.append((comp_id, port))
            for port in spec.outputs:
                all_outputs.append((comp_id, port))
        
        if self.debug:
            print(f"[SOLVER] {len(all_inputs)} inputs, {len(all_outputs)} outputs")
        
        # Phase 2: Build compatibility matrix
        compat_matrix: Dict[Tuple[Tuple[str, Port], Tuple[str, Port]], float] = {}
        
        for out_comp, out_port in all_outputs:
            for in_comp, in_port in all_inputs:
                # Can't connect component to itself (usually)
                if out_comp == in_comp:
                    continue
                
                # Check type compatibility
                if out_port.kind == PortKind.EVENT and in_port.kind == PortKind.EVENT:
                    # Event ports: check parameter compatibility
                    if out_port.event_params == in_port.event_params:
                        score = 1.0
                    elif len(out_port.event_params) >= len(in_port.event_params):
                        score = 0.8  # Can use subset of params
                    else:
                        continue
                elif out_port.kind == PortKind.STATE and in_port.kind == PortKind.STATE:
                    # State ports: type must match
                    result, score = check_compatibility(out_port.port_type, in_port.port_type)
                    if result == CompatibilityResult.INCOMPATIBLE:
                        continue
                elif out_port.kind == PortKind.DATA and in_port.kind == PortKind.DATA:
                    # Data ports: check type compatibility
                    result, score = check_compatibility(out_port.port_type, in_port.port_type)
                    if result == CompatibilityResult.INCOMPATIBLE:
                        continue
                else:
                    # Different port kinds can't connect (usually)
                    continue
                
                # Bonus for name similarity
                if self._names_match(out_port.name, in_port.name):
                    score *= 1.2
                
                # Bonus for explicit compatibility hints
                if in_port.name in out_port.compatible_names:
                    score *= 1.3
                
                compat_matrix[((out_comp, out_port), (in_comp, in_port))] = min(score, 1.0)
        
        if self.debug:
            print(f"[SOLVER] {len(compat_matrix)} possible connections")
        
        # Phase 3: Solve assignment (greedy for now, could use ILP for optimal)
        connections: List[Connection] = []
        satisfied_inputs: Set[Tuple[str, Port]] = set()
        
        # Sort by score (highest first) and required-ness
        sorted_matches = sorted(
            compat_matrix.items(),
            key=lambda x: (
                x[0][1][1].required,  # Required inputs first
                x[1]                   # Then by score
            ),
            reverse=True
        )
        
        for ((out_comp, out_port), (in_comp, in_port)), score in sorted_matches:
            # Skip if input already satisfied
            if (in_comp, in_port) in satisfied_inputs:
                continue
            
            # Create connection
            result, _ = check_compatibility(out_port.port_type, in_port.port_type)
            conn = Connection(
                source_component=out_comp,
                source_port=out_port,
                target_component=in_comp,
                target_port=in_port,
                compatibility=result,
                score=score,
                requires_coercion=(result == CompatibilityResult.COERCION)
            )
            
            connections.append(conn)
            satisfied_inputs.add((in_comp, in_port))
            
            if self.debug:
                print(f"[SOLVER] Connected: {conn}")
        
        # Phase 4: Identify shared state needs
        shared_states = self._identify_shared_states(components, connections, all_inputs)
        
        # Phase 5: Find unsatisfied required inputs
        unsatisfied = []
        for comp_id, port in all_inputs:
            if port.required and (comp_id, port) not in satisfied_inputs:
                # Check if it's satisfied by shared state
                if not any(s.name == port.name for s in shared_states):
                    unsatisfied.append((comp_id, port))
        
        if self.debug and unsatisfied:
            print(f"[SOLVER] Unsatisfied: {unsatisfied}")
        
        # Build result
        total_score = sum(c.score for c in connections)
        
        return ConnectionGraph(
            components=components,
            connections=connections,
            shared_states=shared_states,
            total_score=total_score,
            unsatisfied_inputs=unsatisfied
        )
    
    def _names_match(self, name1: str, name2: str) -> bool:
        """Check if two port names are semantically similar."""
        # Exact match
        if name1 == name2:
            return True
        
        # Common patterns
        patterns = [
            ("onNavigate", "currentView"),
            ("onClick", "selected"),
            ("onChange", "value"),
            ("onSelect", "selected"),
            ("data", "items"),
            ("rows", "data"),
        ]
        
        for p1, p2 in patterns:
            if (p1 in name1 and p2 in name2) or (p2 in name1 and p1 in name2):
                return True
        
        return False
    
    def _identify_shared_states(
        self,
        components: Dict[str, ComponentSpec],
        connections: List[Connection],
        all_inputs: List[Tuple[str, Port]]
    ) -> List[SharedState]:
        """Identify state that needs to be lifted to parent."""
        states: Dict[str, SharedState] = {}  # Use dict to deduplicate by name
        
        # Find state ports that aren't connected
        for comp_id, port in all_inputs:
            if port.kind == PortKind.STATE:
                # Check if already connected
                connected = any(
                    c.target_component == comp_id and c.target_port == port
                    for c in connections
                )
                
                if not connected:
                    # Check if we already have this state
                    if port.name in states:
                        # Add this component as a reader
                        if comp_id not in states[port.name].readers:
                            states[port.name].readers.append(comp_id)
                    else:
                        # Create new shared state
                        state = SharedState(
                            name=port.name,
                            state_type=port.port_type,
                            default_value=self._get_default_value(port),
                            readers=[comp_id]
                        )
                        
                        # Find other components that also read this state
                        for other_id, other_port in all_inputs:
                            if other_id != comp_id and other_port.name == port.name:
                                if other_port.kind == PortKind.STATE:
                                    if other_id not in state.readers:
                                        state.readers.append(other_id)
                        
                        # Find components that write this state (from event outputs)
                        for other_id, spec in components.items():
                            for out_port in spec.outputs:
                                if out_port.kind == PortKind.EVENT:
                                    # Check if this event updates the state
                                    if self._event_updates_state(out_port, port):
                                        if other_id not in state.writers:
                                            state.writers.append(other_id)
                        
                        states[port.name] = state
        
        return list(states.values())
    
    def _event_updates_state(self, event_port: Port, state_port: Port) -> bool:
        """Check if an event port updates a state port."""
        # Common patterns
        if event_port.name == "onNavigate" and state_port.name == "currentView":
            return True
        if event_port.name == "onChange" and state_port.name == "value":
            return True
        if event_port.name == "onSelect" and state_port.name == "selected":
            return True
        return False
    
    def _get_default_value(self, port: Port) -> str:
        """Get default value as code string."""
        if port.default_value is not None:
            if isinstance(port.default_value, str):
                return f'"{port.default_value}"'
            return str(port.default_value)
        
        # Default based on type
        if port.port_type.semantic:
            from .types import SemanticType
            defaults = {
                SemanticType.VIEW_ID: '"dashboard"',
                SemanticType.LOADING: 'false',
                SemanticType.NAV_ITEMS: '[]',
                SemanticType.TABLE_DATA: '[]',
            }
            return defaults.get(port.port_type.semantic, 'null')
        
        from .types import BaseType
        base_defaults = {
            BaseType.STRING: '""',
            BaseType.NUMBER: '0',
            BaseType.BOOLEAN: 'false',
            BaseType.ANY: 'null',
        }
        return base_defaults.get(port.port_type.base, 'null')

