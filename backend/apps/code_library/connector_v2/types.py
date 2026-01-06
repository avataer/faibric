"""
Faibric Connector V2 - Type System

Original design for component port typing.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple


class BaseType(Enum):
    """Primitive types."""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "Date"
    VOID = "void"
    ANY = "any"


class SemanticType(Enum):
    """
    Semantic types carry meaning beyond their structure.
    
    This is our key innovation: types that encode INTENT.
    VIEW_ID isn't just a string - it's a string that identifies a view.
    This allows smarter automatic wiring.
    """
    # Navigation
    VIEW_ID = "ViewId"           # String identifying current view
    NAV_ITEMS = "NavItem[]"      # Array of {id, label, icon?}
    ROUTE = "Route"              # URL path
    
    # Data Display
    TABLE_DATA = "TableRow[]"    # Array of row objects
    CHART_POINTS = "ChartPoint[]"  # Array of {x, y, label?}
    LIST_ITEMS = "ListItem[]"    # Array of {id, title, subtitle?}
    
    # Forms
    FORM_FIELDS = "FormField[]"  # Array of field definitions
    FORM_VALUES = "FormValues"   # Record of field values
    FORM_ERRORS = "FormErrors"   # Record of field errors
    
    # User
    USER = "User"                # {id, name, email, avatar?}
    AUTH_STATE = "AuthState"     # {isAuthenticated, user?, token?}
    
    # State
    LOADING = "Loading"          # boolean for loading state
    ERROR = "Error"              # Error | null
    
    # API
    API_RESPONSE = "ApiResponse" # {data, error, loading}
    CRYPTO_PRICES = "CryptoPrice[]"
    STOCK_DATA = "StockQuote[]"


@dataclass
class PortType:
    """
    Complete type specification for a port.
    
    Combines base type, semantic type, and constraints.
    """
    base: BaseType
    semantic: Optional[SemanticType] = None
    
    # For generics
    element_type: Optional['PortType'] = None  # For ARRAY<T>
    key_type: Optional['PortType'] = None      # For RECORD<K,V>
    value_type: Optional['PortType'] = None
    
    # Constraints
    is_optional: bool = False
    is_nullable: bool = False
    literal_value: Optional[Any] = None  # For literal types like "dashboard"
    
    # Validation
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None  # Regex for strings
    
    def __str__(self) -> str:
        if self.literal_value is not None:
            return f'"{self.literal_value}"'
        if self.semantic:
            return self.semantic.value
        if self.element_type:
            return f"{self.element_type}[]"
        return self.base.value
    
    @property
    def typescript(self) -> str:
        """Generate TypeScript type annotation."""
        if self.literal_value is not None:
            if isinstance(self.literal_value, str):
                return f'"{self.literal_value}"'
            return str(self.literal_value)
        
        if self.semantic:
            return self.semantic.value
        
        if self.element_type:
            inner = self.element_type.typescript
            return f"{inner}[]"
        
        if self.key_type and self.value_type:
            return f"Record<{self.key_type.typescript}, {self.value_type.typescript}>"
        
        base_map = {
            BaseType.STRING: "string",
            BaseType.NUMBER: "number", 
            BaseType.BOOLEAN: "boolean",
            BaseType.DATE: "Date",
            BaseType.VOID: "void",
            BaseType.ANY: "any",
        }
        
        result = base_map.get(self.base, "any")
        
        if self.is_nullable:
            result = f"{result} | null"
        if self.is_optional:
            result = f"{result} | undefined"
            
        return result


# Type constructors for convenience
def STRING() -> PortType:
    return PortType(base=BaseType.STRING)

def NUMBER() -> PortType:
    return PortType(base=BaseType.NUMBER)

def BOOLEAN() -> PortType:
    return PortType(base=BaseType.BOOLEAN)

def ARRAY(element: PortType) -> PortType:
    return PortType(base=BaseType.ANY, element_type=element)

def OPTIONAL(inner: PortType) -> PortType:
    return PortType(
        base=inner.base,
        semantic=inner.semantic,
        element_type=inner.element_type,
        is_optional=True
    )

def LITERAL(value: Any) -> PortType:
    if isinstance(value, str):
        base = BaseType.STRING
    elif isinstance(value, bool):
        base = BaseType.BOOLEAN
    elif isinstance(value, (int, float)):
        base = BaseType.NUMBER
    else:
        base = BaseType.ANY
    return PortType(base=base, literal_value=value)

def VIEW_ID() -> PortType:
    return PortType(base=BaseType.STRING, semantic=SemanticType.VIEW_ID)

def NAV_ITEMS() -> PortType:
    return PortType(base=BaseType.ANY, semantic=SemanticType.NAV_ITEMS)

def TABLE_DATA() -> PortType:
    return PortType(base=BaseType.ANY, semantic=SemanticType.TABLE_DATA)

def LOADING() -> PortType:
    return PortType(base=BaseType.BOOLEAN, semantic=SemanticType.LOADING)

def ERROR() -> PortType:
    return PortType(base=BaseType.ANY, semantic=SemanticType.ERROR, is_nullable=True)


class CompatibilityResult(Enum):
    """Result of type compatibility check."""
    EXACT = auto()      # Exact match
    SEMANTIC = auto()   # Semantic type match
    STRUCTURAL = auto() # Structural subtyping
    COERCION = auto()   # Requires coercion
    INCOMPATIBLE = auto()


def check_compatibility(source: PortType, target: PortType) -> Tuple[CompatibilityResult, float]:
    """
    Check if source type can connect to target type.
    
    Returns (result, score) where score is 0-1 confidence.
    Higher score = better match.
    """
    # Exact match
    if source == target:
        return (CompatibilityResult.EXACT, 1.0)
    
    # Literal to base type
    if source.literal_value is not None:
        if source.base == target.base:
            return (CompatibilityResult.EXACT, 0.95)
    
    # Semantic type match
    if source.semantic and target.semantic:
        if source.semantic == target.semantic:
            return (CompatibilityResult.SEMANTIC, 0.9)
    
    # Semantic to base (VIEW_ID → string)
    if source.semantic and not target.semantic:
        # Check if semantic's base matches target
        semantic_base = {
            SemanticType.VIEW_ID: BaseType.STRING,
            SemanticType.LOADING: BaseType.BOOLEAN,
            SemanticType.NAV_ITEMS: BaseType.ANY,
            SemanticType.TABLE_DATA: BaseType.ANY,
        }
        if semantic_base.get(source.semantic) == target.base:
            return (CompatibilityResult.STRUCTURAL, 0.7)
    
    # Base to semantic (string → VIEW_ID)
    if not source.semantic and target.semantic:
        semantic_base = {
            SemanticType.VIEW_ID: BaseType.STRING,
            SemanticType.LOADING: BaseType.BOOLEAN,
        }
        if source.base == semantic_base.get(target.semantic):
            return (CompatibilityResult.STRUCTURAL, 0.6)
    
    # Optional compatibility
    if target.is_optional and not source.is_optional:
        # Non-optional can satisfy optional
        inner_result, inner_score = check_compatibility(
            PortType(base=source.base, semantic=source.semantic),
            PortType(base=target.base, semantic=target.semantic)
        )
        if inner_result != CompatibilityResult.INCOMPATIBLE:
            return (inner_result, inner_score * 0.95)
    
    # Array compatibility
    if source.element_type and target.element_type:
        inner_result, inner_score = check_compatibility(
            source.element_type, target.element_type
        )
        if inner_result != CompatibilityResult.INCOMPATIBLE:
            return (inner_result, inner_score * 0.9)
    
    # Base type coercion
    coercion_rules = {
        (BaseType.NUMBER, BaseType.STRING): 0.5,  # toString
        (BaseType.BOOLEAN, BaseType.STRING): 0.4,
        (BaseType.ANY, BaseType.STRING): 0.3,
        (BaseType.ANY, BaseType.NUMBER): 0.3,
        (BaseType.ANY, BaseType.BOOLEAN): 0.3,
    }
    
    coercion_score = coercion_rules.get((source.base, target.base))
    if coercion_score:
        return (CompatibilityResult.COERCION, coercion_score)
    
    # ANY accepts anything
    if target.base == BaseType.ANY:
        return (CompatibilityResult.COERCION, 0.2)
    
    return (CompatibilityResult.INCOMPATIBLE, 0.0)

