"""
Faibric Connector V2 - Port System

Ports are the connection points on components.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable

from .types import PortType, BaseType, SemanticType, STRING, BOOLEAN, VIEW_ID


class PortDirection(Enum):
    """Direction of data/control flow through port."""
    IN = "in"       # Component receives through this port
    OUT = "out"     # Component sends through this port
    INOUT = "inout" # Bidirectional (rare)


class PortKind(Enum):
    """What kind of connection this port represents."""
    DATA = "data"       # Props, data flow
    EVENT = "event"     # Callbacks, event handlers
    STATE = "state"     # Shared state access
    SLOT = "slot"       # Child composition
    STYLE = "style"     # Style customization


@dataclass
class Port:
    """
    A single connection point on a component.
    
    This is the fundamental unit of the connector system.
    """
    name: str                          # Prop/callback name
    port_type: PortType                # Type of data
    direction: PortDirection           # In or out
    kind: PortKind                     # Data, event, state, slot
    
    # Requirements
    required: bool = True              # Must be connected
    default_value: Optional[Any] = None
    
    # Documentation
    description: str = ""
    
    # Event-specific
    event_params: List[tuple] = field(default_factory=list)  # [(name, type), ...]
    
    # Connection hints
    compatible_names: List[str] = field(default_factory=list)  # Names that often connect
    priority: int = 0                  # Higher = preferred for auto-wiring
    
    def __hash__(self):
        return hash((self.name, self.direction.value, self.kind.value))
    
    def __eq__(self, other):
        if not isinstance(other, Port):
            return False
        return (self.name == other.name and 
                self.direction == other.direction and
                self.kind == other.kind)
    
    @property
    def is_input(self) -> bool:
        return self.direction in (PortDirection.IN, PortDirection.INOUT)
    
    @property
    def is_output(self) -> bool:
        return self.direction in (PortDirection.OUT, PortDirection.INOUT)
    
    @property
    def typescript_prop(self) -> str:
        """Generate TypeScript prop definition."""
        opt = "?" if not self.required else ""
        
        if self.kind == PortKind.EVENT:
            params = ", ".join(f"{n}: {t}" for n, t in self.event_params)
            return f"{self.name}{opt}: ({params}) => void"
        
        return f"{self.name}{opt}: {self.port_type.typescript}"


# Port factory functions

def data_in(
    name: str,
    port_type: PortType,
    required: bool = True,
    default: Any = None,
    description: str = ""
) -> Port:
    """Create a data input port (component receives this prop)."""
    return Port(
        name=name,
        port_type=port_type,
        direction=PortDirection.IN,
        kind=PortKind.DATA,
        required=required,
        default_value=default,
        description=description
    )


def data_out(
    name: str,
    port_type: PortType,
    description: str = ""
) -> Port:
    """Create a data output port (component provides this value)."""
    return Port(
        name=name,
        port_type=port_type,
        direction=PortDirection.OUT,
        kind=PortKind.DATA,
        required=False,
        description=description
    )


def event_in(
    name: str,
    params: List[tuple] = None,
    required: bool = True,
    description: str = ""
) -> Port:
    """Create an event input port (component receives this callback)."""
    return Port(
        name=name,
        port_type=PortType(base=BaseType.VOID),
        direction=PortDirection.IN,
        kind=PortKind.EVENT,
        required=required,
        description=description,
        event_params=params or []
    )


def event_out(
    name: str,
    params: List[tuple] = None,
    description: str = ""
) -> Port:
    """Create an event output port (component calls this callback)."""
    return Port(
        name=name,
        port_type=PortType(base=BaseType.VOID),
        direction=PortDirection.OUT,
        kind=PortKind.EVENT,
        required=False,
        description=description,
        event_params=params or []
    )


def state_read(
    name: str,
    port_type: PortType,
    description: str = ""
) -> Port:
    """Create a state read port (component reads shared state)."""
    return Port(
        name=name,
        port_type=port_type,
        direction=PortDirection.IN,
        kind=PortKind.STATE,
        required=True,
        description=description
    )


def state_write(
    name: str,
    port_type: PortType,
    description: str = ""
) -> Port:
    """Create a state write port (component writes shared state)."""
    return Port(
        name=name,
        port_type=port_type,
        direction=PortDirection.OUT,
        kind=PortKind.STATE,
        required=False,
        description=description
    )


def slot(
    name: str = "children",
    required: bool = False,
    description: str = ""
) -> Port:
    """Create a slot port for component composition."""
    return Port(
        name=name,
        port_type=PortType(base=BaseType.ANY),
        direction=PortDirection.IN,
        kind=PortKind.SLOT,
        required=required,
        description=description
    )


@dataclass
class ComponentSpec:
    """
    Complete specification for a component's interface.
    
    This defines all connection points for a component type.
    """
    component_type: str              # e.g., "navigation", "table"
    variant: str = "default"         # e.g., "sidebar", "header"
    
    # Ports
    inputs: List[Port] = field(default_factory=list)
    outputs: List[Port] = field(default_factory=list)
    
    # The actual component code (from library)
    code: str = ""
    
    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    @property
    def all_ports(self) -> List[Port]:
        return self.inputs + self.outputs
    
    @property
    def required_inputs(self) -> List[Port]:
        return [p for p in self.inputs if p.required]
    
    @property
    def data_inputs(self) -> List[Port]:
        return [p for p in self.inputs if p.kind == PortKind.DATA]
    
    @property
    def event_inputs(self) -> List[Port]:
        return [p for p in self.inputs if p.kind == PortKind.EVENT]
    
    @property
    def state_inputs(self) -> List[Port]:
        return [p for p in self.inputs if p.kind == PortKind.STATE]
    
    @property
    def data_outputs(self) -> List[Port]:
        return [p for p in self.outputs if p.kind == PortKind.DATA]
    
    @property
    def event_outputs(self) -> List[Port]:
        return [p for p in self.outputs if p.kind == PortKind.EVENT]
    
    @property
    def state_outputs(self) -> List[Port]:
        return [p for p in self.outputs if p.kind == PortKind.STATE]
    
    def get_port(self, name: str) -> Optional[Port]:
        for port in self.all_ports:
            if port.name == name:
                return port
        return None


# Standard component specs

NAVIGATION_SPEC = ComponentSpec(
    component_type="navigation",
    variant="sidebar",
    inputs=[
        state_read("currentView", VIEW_ID(), "Currently active view"),
        data_in("items", PortType(base=BaseType.ANY, semantic=SemanticType.NAV_ITEMS), 
                required=False, description="Navigation items"),
    ],
    outputs=[
        event_out("onNavigate", [("viewId", "string")], "User clicks nav item"),
    ],
    description="Navigation sidebar with view switching"
)

TABLE_SPEC = ComponentSpec(
    component_type="table",
    variant="data",
    inputs=[
        data_in("data", PortType(base=BaseType.ANY, semantic=SemanticType.TABLE_DATA),
                description="Table rows"),
        data_in("columns", PortType(base=BaseType.ANY), required=False,
                description="Column definitions"),
        data_in("loading", PortType(base=BaseType.BOOLEAN, semantic=SemanticType.LOADING),
                required=False, default=False),
    ],
    outputs=[
        event_out("onRowClick", [("row", "any"), ("index", "number")]),
        event_out("onSort", [("column", "string"), ("direction", "string")]),
    ],
    description="Data table with sorting and row selection"
)

CHART_SPEC = ComponentSpec(
    component_type="chart",
    variant="line",
    inputs=[
        data_in("data", PortType(base=BaseType.ANY, semantic=SemanticType.CHART_POINTS),
                description="Chart data points"),
        data_in("title", STRING(), required=False),
        data_in("loading", PortType(base=BaseType.BOOLEAN, semantic=SemanticType.LOADING),
                required=False, default=False),
    ],
    outputs=[
        event_out("onPointClick", [("point", "ChartPoint"), ("index", "number")]),
    ],
    description="Line chart visualization"
)

STATS_SPEC = ComponentSpec(
    component_type="stats",
    variant="cards",
    inputs=[
        data_in("stats", PortType(base=BaseType.ANY), description="Stats data"),
        data_in("loading", PortType(base=BaseType.BOOLEAN, semantic=SemanticType.LOADING),
                required=False, default=False),
    ],
    outputs=[
        event_out("onStatClick", [("stat", "any")]),
    ],
    description="Statistics cards display"
)

FORM_SPEC = ComponentSpec(
    component_type="form",
    variant="contact",
    inputs=[
        data_in("fields", PortType(base=BaseType.ANY, semantic=SemanticType.FORM_FIELDS),
                required=False),
        data_in("initialValues", PortType(base=BaseType.ANY), required=False),
        data_in("loading", PortType(base=BaseType.BOOLEAN, semantic=SemanticType.LOADING),
                required=False, default=False),
    ],
    outputs=[
        event_out("onSubmit", [("values", "FormValues")]),
        event_out("onChange", [("field", "string"), ("value", "any")]),
    ],
    description="Form with validation"
)

# Registry of standard specs
COMPONENT_SPECS: Dict[str, ComponentSpec] = {
    "navigation_sidebar": NAVIGATION_SPEC,
    "table_data": TABLE_SPEC,
    "chart_line": CHART_SPEC,
    "stats_cards": STATS_SPEC,
    "form_contact": FORM_SPEC,
}


def get_spec(component_type: str, variant: str = "default") -> Optional[ComponentSpec]:
    """Get spec for a component type/variant."""
    key = f"{component_type}_{variant}"
    return COMPONENT_SPECS.get(key)

