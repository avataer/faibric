"""
Faibric Component Connector System (State-of-the-Art)

This module defines how building blocks connect to each other.
Think of it like USB ports - each component has input/output ports
with defined types that must match for connection.

CONNECTOR TYPES:
- DATA_IN/OUT: Props and data flow
- EVENT_IN/OUT: Callbacks and handlers  
- STATE_READ/WRITE: Shared state access
- SLOT: Composition (children/render props)
- STYLE: Style customization points

Each connector has:
- name: The prop/event name
- schema: TypeScript type + JSON schema for validation
- required: Whether it must be provided
- default: Default value if not provided
- compatible_with: List of compatible connectors for auto-wiring
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple
import json
import re


class ConnectorType(Enum):
    """Types of connections between components."""
    
    # Data Flow
    DATA_IN = "data_in"       # Component receives data as props
    DATA_OUT = "data_out"     # Component provides data (via context/callback)
    
    # Events
    EVENT_IN = "event_in"     # Component receives event handler props
    EVENT_OUT = "event_out"   # Component emits events (calls callbacks)
    
    # State
    STATE_READ = "state_read"   # Component reads from shared state
    STATE_WRITE = "state_write" # Component writes to shared state
    
    # Composition
    SLOT_PARENT = "slot_parent"   # Component has slots for children
    SLOT_CHILD = "slot_child"     # Component fills a slot
    
    # Styling
    STYLE_IN = "style_in"     # Component accepts style customization
    STYLE_OUT = "style_out"   # Component exposes style tokens


class DataType(Enum):
    """Standard data types for connectors."""
    
    # Primitives
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "Date"
    
    # Collections
    ARRAY = "T[]"
    RECORD = "Record<string, T>"
    
    # UI Data
    NAV_ITEMS = "NavItem[]"
    TABLE_DATA = "TableRow[]"
    CHART_DATA = "ChartPoint[]"
    FORM_FIELDS = "FormField[]"
    
    # Domain Data
    CRYPTO_PRICES = "CryptoPrice[]"
    STOCK_DATA = "StockQuote[]"
    USER = "User"
    
    # State
    LOADING = "boolean"
    ERROR = "Error | null"
    VIEW_ID = "string"


@dataclass
class DataSchema:
    """
    Schema for data flowing through a connector.
    
    Includes both TypeScript type (for code gen) and JSON Schema (for validation).
    """
    
    name: str
    typescript_type: str  # e.g., "CryptoPrice[]", "User", "string"
    
    # JSON Schema for runtime validation
    json_schema: Dict = field(default_factory=dict)
    
    # Example value (for docs and testing)
    example: Any = None
    
    # Transformation compatibility
    can_transform_from: List[str] = field(default_factory=list)
    can_transform_to: List[str] = field(default_factory=list)
    
    # Placeholder for missing data
    placeholder: str = "---"
    placeholder_symbol: str = ""  # e.g., "$" for prices
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DataSchema':
        return cls(**data)


@dataclass
class EventSignature:
    """
    Signature for event handlers.
    
    Defines what arguments the callback receives.
    """
    
    name: str  # e.g., "onSelect", "onSubmit"
    params: List[Tuple[str, str]]  # [(param_name, type), ...]
    return_type: str = "void"
    
    @property
    def typescript(self) -> str:
        """Generate TypeScript signature."""
        params_str = ", ".join(f"{name}: {typ}" for name, typ in self.params)
        return f"({params_str}) => {self.return_type}"
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'params': self.params,
            'return_type': self.return_type,
            'typescript': self.typescript
        }


@dataclass  
class StyleSlot:
    """
    A customizable style point in a component.
    
    Components expose style slots that can be customized
    without modifying the component code.
    """
    
    name: str  # e.g., "container", "header", "item"
    description: str
    default_classes: str  # Default Tailwind classes
    
    # What can be customized
    customizable: List[str] = field(default_factory=lambda: [
        "colors", "spacing", "typography", "borders", "shadows"
    ])
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Connector:
    """
    A single input/output point on a component.
    
    This is the core building block of the connector system.
    Think of it as a typed "port" that components use to communicate.
    """
    
    name: str  # Prop/state name: "data", "onSelect", "currentView"
    connector_type: ConnectorType
    
    # Type information
    data_schema: Optional[DataSchema] = None
    event_signature: Optional[EventSignature] = None
    style_slot: Optional[StyleSlot] = None
    
    # Requirements
    required: bool = True
    default_value: Any = None
    
    # Documentation
    description: str = ""
    
    # Auto-wiring compatibility
    compatible_with: List[str] = field(default_factory=list)
    
    # Priority for auto-wiring (higher = preferred)
    priority: int = 0
    
    def to_dict(self) -> Dict:
        result = {
            'name': self.name,
            'connector_type': self.connector_type.value,
            'required': self.required,
            'description': self.description,
            'priority': self.priority,
            'compatible_with': self.compatible_with,
        }
        
        if self.data_schema:
            result['data_schema'] = self.data_schema.to_dict()
        if self.event_signature:
            result['event_signature'] = self.event_signature.to_dict()
        if self.style_slot:
            result['style_slot'] = self.style_slot.to_dict()
        if self.default_value is not None:
            result['default_value'] = self.default_value
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Connector':
        data = data.copy()
        data['connector_type'] = ConnectorType(data['connector_type'])
        
        if 'data_schema' in data and data['data_schema']:
            data['data_schema'] = DataSchema.from_dict(data['data_schema'])
        if 'event_signature' in data and data['event_signature']:
            sig_data = data['event_signature']
            data['event_signature'] = EventSignature(
                name=sig_data['name'],
                params=sig_data['params'],
                return_type=sig_data.get('return_type', 'void')
            )
        if 'style_slot' in data and data['style_slot']:
            data['style_slot'] = StyleSlot(**data['style_slot'])
            
        return cls(**data)


@dataclass
class ComponentInterface:
    """
    Complete interface definition for a component.
    
    This is the "contract" that a component must fulfill.
    It defines all inputs, outputs, slots, and styling hooks.
    """
    
    # Identity
    component_type: str          # e.g., "navigation", "table", "chart"
    variant: str                 # e.g., "sidebar", "data", "line"
    version: str = "1.0.0"
    
    # Connectors
    inputs: List[Connector] = field(default_factory=list)
    outputs: List[Connector] = field(default_factory=list)
    
    # Composition slots
    slots: List[str] = field(default_factory=list)
    
    # State requirements
    required_state: List[str] = field(default_factory=list)
    provided_state: List[str] = field(default_factory=list)
    
    # Dependencies
    requires_components: List[str] = field(default_factory=list)
    incompatible_with: List[str] = field(default_factory=list)
    
    # Style slots
    style_slots: List[StyleSlot] = field(default_factory=list)
    
    # Theme tokens this component uses
    theme_tokens: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'component_type': self.component_type,
            'variant': self.variant,
            'version': self.version,
            'inputs': [c.to_dict() for c in self.inputs],
            'outputs': [c.to_dict() for c in self.outputs],
            'slots': self.slots,
            'required_state': self.required_state,
            'provided_state': self.provided_state,
            'requires_components': self.requires_components,
            'incompatible_with': self.incompatible_with,
            'style_slots': [s.to_dict() for s in self.style_slots],
            'theme_tokens': self.theme_tokens,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ComponentInterface':
        data = data.copy()
        data['inputs'] = [Connector.from_dict(c) for c in data.get('inputs', [])]
        data['outputs'] = [Connector.from_dict(c) for c in data.get('outputs', [])]
        data['style_slots'] = [StyleSlot(**s) for s in data.get('style_slots', [])]
        return cls(**data)
    
    def get_input(self, name: str) -> Optional[Connector]:
        """Get an input connector by name."""
        for inp in self.inputs:
            if inp.name == name:
                return inp
        return None
    
    def get_output(self, name: str) -> Optional[Connector]:
        """Get an output connector by name."""
        for out in self.outputs:
            if out.name == name:
                return out
        return None
    
    def get_required_inputs(self) -> List[Connector]:
        """Get all required inputs."""
        return [inp for inp in self.inputs if inp.required]
    
    def get_data_inputs(self) -> List[Connector]:
        """Get all data input connectors."""
        return [inp for inp in self.inputs 
                if inp.connector_type == ConnectorType.DATA_IN]
    
    def get_event_outputs(self) -> List[Connector]:
        """Get all event output connectors."""
        return [out for out in self.outputs 
                if out.connector_type == ConnectorType.EVENT_OUT]


# =============================================================================
# CONNECTOR FACTORIES
# =============================================================================

def data_input(
    name: str,
    typescript_type: str,
    required: bool = True,
    description: str = "",
    default: Any = None,
    placeholder_symbol: str = "",
    example: Any = None
) -> Connector:
    """Factory for creating data input connectors."""
    return Connector(
        name=name,
        connector_type=ConnectorType.DATA_IN,
        data_schema=DataSchema(
            name=name,
            typescript_type=typescript_type,
            placeholder_symbol=placeholder_symbol,
            example=example
        ),
        required=required,
        default_value=default,
        description=description
    )


def data_output(
    name: str,
    typescript_type: str,
    description: str = ""
) -> Connector:
    """Factory for creating data output connectors."""
    return Connector(
        name=name,
        connector_type=ConnectorType.DATA_OUT,
        data_schema=DataSchema(name=name, typescript_type=typescript_type),
        required=False,
        description=description
    )


def event_output(
    name: str,
    params: List[Tuple[str, str]] = None,
    description: str = ""
) -> Connector:
    """Factory for creating event output connectors."""
    return Connector(
        name=name,
        connector_type=ConnectorType.EVENT_OUT,
        event_signature=EventSignature(
            name=name,
            params=params or []
        ),
        required=False,
        description=description
    )


def state_reader(
    name: str,
    typescript_type: str,
    description: str = ""
) -> Connector:
    """Factory for creating state read connectors."""
    return Connector(
        name=name,
        connector_type=ConnectorType.STATE_READ,
        data_schema=DataSchema(name=name, typescript_type=typescript_type),
        required=True,
        description=description
    )


def state_writer(
    name: str,
    typescript_type: str,
    description: str = ""
) -> Connector:
    """Factory for creating state write connectors."""
    return Connector(
        name=name,
        connector_type=ConnectorType.STATE_WRITE,
        data_schema=DataSchema(name=name, typescript_type=typescript_type),
        required=False,
        description=description
    )


def style_slot_connector(
    name: str,
    default_classes: str,
    description: str = ""
) -> Connector:
    """Factory for creating style slot connectors."""
    return Connector(
        name=f"styles.{name}",
        connector_type=ConnectorType.STYLE_IN,
        style_slot=StyleSlot(
            name=name,
            description=description,
            default_classes=default_classes
        ),
        required=False,
        description=description
    )



