"""
Connection Validator

Validates that components can properly connect to each other.

Used during:
1. Library healing cycles - ensure all components are compatible
2. Project composition - validate component mix before generation
3. Component upgrades - ensure new versions maintain compatibility
4. Build-time checks - catch issues before code generation

VALIDATION LEVELS:
- ERROR: Connection will fail, must be fixed
- WARNING: May have issues, should be reviewed
- INFO: Suggestion for improvement
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum

from .connectors import (
    ComponentInterface,
    Connector,
    ConnectorType,
    DataSchema,
)
from .standard_interfaces import get_interface, INTERFACE_REGISTRY


class ValidationLevel(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation issue."""
    level: ValidationLevel
    code: str
    message: str
    component: str = ""
    connector: str = ""
    suggestion: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'level': self.level.value,
            'code': self.code,
            'message': self.message,
            'component': self.component,
            'connector': self.connector,
            'suggestion': self.suggestion,
        }


@dataclass
class ValidationResult:
    """Result of validating a connection or composition."""
    valid: bool
    issues: List[ValidationIssue]
    
    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == ValidationLevel.ERROR]
    
    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == ValidationLevel.WARNING]
    
    def to_dict(self) -> Dict:
        return {
            'valid': self.valid,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'issues': [i.to_dict() for i in self.issues],
        }


class ConnectionValidator:
    """
    Validates connections between components.
    
    Think of it like type-checking for component wiring:
    - Does the output type match the input type?
    - Are all required inputs satisfied?
    - Is state properly provided before being read?
    - Are incompatible components being combined?
    """
    
    # Type compatibility mappings
    TYPE_COMPATIBILITY = {
        # Any array type can connect to generic array
        'T[]': ['any[]', 'object[]', 'unknown[]'],
        'any[]': ['T[]', 'object[]'],
        
        # Specific types that are compatible
        'Record<string, any>': ['object', '{}'],
        'T': ['any', 'unknown'],
        
        # Common conversions
        'number': ['string'],  # Numbers can be stringified
        'string': [],  # Strings are terminal (no auto-conversion to them)
        'boolean': [],
    }
    
    # Placeholder symbols for different data types
    PLACEHOLDER_SYMBOLS = {
        'currency': '$',
        'percentage': '%',
        'number': '#',
        'count': '#',
        'text': '',
        'date': '',
        'time': '',
        'temperature': '°',
    }
    
    def validate_connection(
        self,
        source: ComponentInterface,
        target: ComponentInterface,
        source_output: str,
        target_input: str
    ) -> ValidationResult:
        """
        Validate a specific connection between two components.
        
        Args:
            source: The component providing data/events
            target: The component receiving data/events
            source_output: Name of the output connector on source
            target_input: Name of the input connector on target
            
        Returns:
            ValidationResult with any issues found
        """
        issues = []
        
        # Find the connectors
        output = source.get_output(source_output)
        if not output:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="MISSING_OUTPUT",
                message=f"Component '{source.component_type}' has no output '{source_output}'",
                component=source.component_type,
                connector=source_output,
            ))
            return ValidationResult(valid=False, issues=issues)
        
        input_conn = target.get_input(target_input)
        if not input_conn:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="MISSING_INPUT",
                message=f"Component '{target.component_type}' has no input '{target_input}'",
                component=target.component_type,
                connector=target_input,
            ))
            return ValidationResult(valid=False, issues=issues)
        
        # Check type compatibility
        type_result = self._check_type_compatibility(output, input_conn)
        if type_result:
            issues.append(type_result)
        
        # Check connector type compatibility (data→data, event→event)
        conn_result = self._check_connector_type_compatibility(output, input_conn)
        if conn_result:
            issues.append(conn_result)
        
        valid = not any(i.level == ValidationLevel.ERROR for i in issues)
        return ValidationResult(valid=valid, issues=issues)
    
    def validate_composition(
        self,
        interfaces: List[ComponentInterface]
    ) -> ValidationResult:
        """
        Validate that a set of components can work together.
        
        Checks:
        1. All required inputs are satisfied
        2. State dependencies are met
        3. No incompatible components
        4. Slot requirements are fulfilled
        """
        issues = []
        
        # Collect all outputs, state providers, and component types
        all_outputs: Dict[str, Tuple[ComponentInterface, Connector]] = {}
        provided_state: Set[str] = set()
        component_types: Set[str] = set()
        
        for interface in interfaces:
            component_types.add(interface.component_type)
            provided_state.update(interface.provided_state)
            
            for output in interface.outputs:
                key = f"{interface.component_type}.{output.name}"
                all_outputs[key] = (interface, output)
        
        # 1. Check all required inputs are satisfied
        for interface in interfaces:
            for inp in interface.inputs:
                if not inp.required:
                    continue
                    
                # Check if there's a compatible output
                if inp.connector_type == ConnectorType.STATE_READ:
                    # State inputs are satisfied by state providers
                    if inp.name not in provided_state:
                        issues.append(ValidationIssue(
                            level=ValidationLevel.ERROR,
                            code="MISSING_STATE",
                            message=f"'{interface.component_type}' requires state '{inp.name}' but no component provides it",
                            component=interface.component_type,
                            connector=inp.name,
                            suggestion=f"Add a component that provides '{inp.name}' state",
                        ))
                elif inp.connector_type == ConnectorType.DATA_IN:
                    # Data inputs can have defaults
                    if inp.default_value is None:
                        # Check if any output can provide this
                        compatible_found = self._find_compatible_output(inp, all_outputs)
                        if not compatible_found:
                            issues.append(ValidationIssue(
                                level=ValidationLevel.WARNING,
                                code="UNPROVIDED_INPUT",
                                message=f"'{interface.component_type}' requires '{inp.name}' but no component provides it",
                                component=interface.component_type,
                                connector=inp.name,
                                suggestion=f"Wire a data source to '{inp.name}' or provide a default",
                            ))
        
        # 2. Check state dependencies
        required_state: Set[str] = set()
        for interface in interfaces:
            required_state.update(interface.required_state)
        
        missing_state = required_state - provided_state
        if missing_state:
            for state in missing_state:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="MISSING_STATE_PROVIDER",
                    message=f"State '{state}' is required but not provided by any component",
                    suggestion=f"Add Navigation or Layout component to provide '{state}'",
                ))
        
        # 3. Check incompatibilities
        for interface in interfaces:
            for incompatible in interface.incompatible_with:
                if incompatible in component_types:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        code="INCOMPATIBLE_COMPONENTS",
                        message=f"'{interface.component_type}' is incompatible with '{incompatible}'",
                        component=interface.component_type,
                        suggestion=f"Remove either '{interface.component_type}' or '{incompatible}'",
                    ))
        
        # 4. Check component requirements
        for interface in interfaces:
            for required in interface.requires_components:
                if required not in component_types:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.WARNING,
                        code="MISSING_DEPENDENCY",
                        message=f"'{interface.component_type}' works best with '{required}' component",
                        component=interface.component_type,
                        suggestion=f"Consider adding '{required}' component",
                    ))
        
        # 5. Check structural requirements
        has_layout = 'layout' in component_types
        has_navigation = 'navigation' in component_types
        
        if not has_layout and len(interfaces) > 2:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="MISSING_LAYOUT",
                message="No layout component - app may lack proper structure",
                suggestion="Add a Layout component for better organization",
            ))
        
        if not has_navigation and len(interfaces) > 3:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                code="MISSING_NAVIGATION",
                message="No navigation component - users may struggle to navigate",
                suggestion="Add a Navigation component for multi-view apps",
            ))
        
        valid = not any(i.level == ValidationLevel.ERROR for i in issues)
        return ValidationResult(valid=valid, issues=issues)
    
    def validate_component_interface(
        self,
        interface: ComponentInterface
    ) -> ValidationResult:
        """
        Validate that a component's interface is well-formed.
        
        Checks:
        - All connectors have proper types
        - Event signatures are valid
        - Style slots are properly defined
        """
        issues = []
        
        # Check inputs
        for inp in interface.inputs:
            if inp.connector_type == ConnectorType.DATA_IN:
                if not inp.data_schema:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.WARNING,
                        code="MISSING_SCHEMA",
                        message=f"Input '{inp.name}' has no data schema",
                        component=interface.component_type,
                        connector=inp.name,
                    ))
            elif inp.connector_type == ConnectorType.STATE_READ:
                if not inp.data_schema:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.WARNING,
                        code="MISSING_STATE_TYPE",
                        message=f"State input '{inp.name}' has no type definition",
                        component=interface.component_type,
                        connector=inp.name,
                    ))
        
        # Check outputs
        for out in interface.outputs:
            if out.connector_type == ConnectorType.EVENT_OUT:
                if not out.event_signature:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.WARNING,
                        code="MISSING_EVENT_SIGNATURE",
                        message=f"Event output '{out.name}' has no signature",
                        component=interface.component_type,
                        connector=out.name,
                    ))
        
        # Check state consistency
        for state in interface.required_state:
            has_reader = any(
                inp.name == state and inp.connector_type == ConnectorType.STATE_READ
                for inp in interface.inputs
            )
            if not has_reader:
                issues.append(ValidationIssue(
                    level=ValidationLevel.INFO,
                    code="STATE_NOT_EXPOSED",
                    message=f"Required state '{state}' is not exposed as an input",
                    component=interface.component_type,
                ))
        
        valid = not any(i.level == ValidationLevel.ERROR for i in issues)
        return ValidationResult(valid=valid, issues=issues)
    
    def _check_type_compatibility(
        self,
        output: Connector,
        input_conn: Connector
    ) -> Optional[ValidationIssue]:
        """Check if output type is compatible with input type."""
        
        if not output.data_schema or not input_conn.data_schema:
            return None  # Unknown types are assumed compatible
        
        out_type = output.data_schema.typescript_type
        in_type = input_conn.data_schema.typescript_type
        
        # Exact match
        if out_type == in_type:
            return None
        
        # Generic type matches anything
        if in_type == 'T' or out_type == 'T':
            return None
        
        # Generic array matches specific arrays
        if 'T[]' in in_type and '[]' in out_type:
            return None
        if '[]' in in_type and '[]' in out_type:
            return None
        
        # Check explicit compatibility mappings
        compatible_types = self.TYPE_COMPATIBILITY.get(in_type, [])
        if out_type in compatible_types:
            return None
        
        # Check if transformable
        if output.data_schema.can_transform_to:
            if in_type in output.data_schema.can_transform_to:
                return ValidationIssue(
                    level=ValidationLevel.INFO,
                    code="TYPE_TRANSFORMATION_NEEDED",
                    message=f"Type '{out_type}' can transform to '{in_type}' but requires conversion",
                    suggestion=self._suggest_transformer(out_type, in_type),
                )
        
        return ValidationIssue(
            level=ValidationLevel.ERROR,
            code="TYPE_MISMATCH",
            message=f"Type mismatch: output is '{out_type}' but input expects '{in_type}'",
            connector=f"{output.name} → {input_conn.name}",
            suggestion=self._suggest_transformer(out_type, in_type),
        )
    
    def _check_connector_type_compatibility(
        self,
        output: Connector,
        input_conn: Connector
    ) -> Optional[ValidationIssue]:
        """Check if connector types are compatible."""
        
        # Data outputs → Data inputs
        if output.connector_type == ConnectorType.DATA_OUT:
            if input_conn.connector_type != ConnectorType.DATA_IN:
                return ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="CONNECTOR_TYPE_MISMATCH",
                    message=f"Data output cannot connect to {input_conn.connector_type.value}",
                )
        
        # Event outputs → Event inputs (via handlers)
        if output.connector_type == ConnectorType.EVENT_OUT:
            if input_conn.connector_type != ConnectorType.EVENT_IN:
                return ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="CONNECTOR_TYPE_MISMATCH",
                    message=f"Event output cannot connect to {input_conn.connector_type.value}",
                )
        
        # State writers → State readers
        if output.connector_type == ConnectorType.STATE_WRITE:
            if input_conn.connector_type != ConnectorType.STATE_READ:
                return ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="CONNECTOR_TYPE_MISMATCH",
                    message=f"State output cannot connect to {input_conn.connector_type.value}",
                )
        
        return None
    
    def _find_compatible_output(
        self,
        input_conn: Connector,
        all_outputs: Dict[str, Tuple[ComponentInterface, Connector]]
    ) -> bool:
        """Check if any available output can satisfy this input."""
        
        for key, (interface, output) in all_outputs.items():
            # Check type compatibility
            if output.data_schema and input_conn.data_schema:
                out_type = output.data_schema.typescript_type
                in_type = input_conn.data_schema.typescript_type
                
                if out_type == in_type:
                    return True
                if 'T' in in_type or 'T' in out_type:
                    return True
                if '[]' in in_type and '[]' in out_type:
                    return True
        
        return False
    
    def _suggest_transformer(self, from_type: str, to_type: str) -> str:
        """Suggest a transformer function for type conversion."""
        
        suggestions = {
            ('object[]', 'ChartData[]'): 'data.map(item => ({ label: item.name, value: item.amount }))',
            ('number', 'string'): 'value.toString()',
            ('string', 'number'): 'parseInt(value, 10)',
            ('Date', 'string'): 'date.toISOString()',
            ('string', 'Date'): 'new Date(value)',
        }
        
        suggestion = suggestions.get((from_type, to_type))
        if suggestion:
            return f"Transform with: {suggestion}"
        
        return f"Manual conversion from {from_type} to {to_type} may be needed"


def validate_component_for_library(interface: ComponentInterface) -> ValidationResult:
    """
    Validate that a component is ready for the library.
    
    Additional checks for library-quality components:
    - Has proper documentation
    - All connectors have descriptions
    - Style slots are customizable
    """
    validator = ConnectionValidator()
    result = validator.validate_component_interface(interface)
    
    issues = list(result.issues)
    
    # Check documentation
    undocumented = [c for c in interface.inputs + interface.outputs if not c.description]
    if undocumented:
        issues.append(ValidationIssue(
            level=ValidationLevel.WARNING,
            code="UNDOCUMENTED_CONNECTORS",
            message=f"{len(undocumented)} connectors lack descriptions",
            component=interface.component_type,
            suggestion="Add descriptions to all connectors for better developer experience",
        ))
    
    # Check for sensible defaults
    required_without_defaults = [
        inp for inp in interface.inputs 
        if inp.required and inp.default_value is None
        and inp.connector_type == ConnectorType.DATA_IN
    ]
    if len(required_without_defaults) > 3:
        issues.append(ValidationIssue(
            level=ValidationLevel.INFO,
            code="MANY_REQUIRED_INPUTS",
            message=f"Component requires {len(required_without_defaults)} inputs with no defaults",
            component=interface.component_type,
            suggestion="Consider adding defaults to make the component easier to use",
        ))
    
    valid = not any(i.level == ValidationLevel.ERROR for i in issues)
    return ValidationResult(valid=valid, issues=issues)


# ═══════════════════════════════════════════════════════════════════════════════
# JSX BALANCE VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

import re

def validate_jsx_balance(code: str) -> ValidationResult:
    """
    Validate that JSX tags are properly balanced.
    
    Checks for:
    - Matching open/close tags for div, span, main, section, etc.
    - Self-closing tags are handled correctly
    - Returns specific line numbers where issues occur
    """
    issues = []
    
    # Tags to check (common JSX elements)
    tags_to_check = ['div', 'span', 'main', 'section', 'article', 'aside', 
                     'header', 'footer', 'nav', 'ul', 'ol', 'li', 'table', 
                     'thead', 'tbody', 'tr', 'td', 'th', 'form', 'button']
    
    for tag in tags_to_check:
        # Count opening tags (not self-closing)
        open_pattern = rf'<{tag}(?:\s[^>]*)?(?<!/)>'
        close_pattern = rf'</{tag}>'
        
        open_count = len(re.findall(open_pattern, code, re.IGNORECASE))
        close_count = len(re.findall(close_pattern, code, re.IGNORECASE))
        
        diff = open_count - close_count
        
        if diff != 0:
            level = ValidationLevel.ERROR if abs(diff) > 2 else ValidationLevel.WARNING
            issues.append(ValidationIssue(
                level=level,
                code="JSX_IMBALANCE",
                message=f"<{tag}> tag imbalance: {open_count} open, {close_count} close ({diff:+d})",
                suggestion=f"Add {abs(diff)} {'closing' if diff > 0 else 'opening'} <{'/' if diff > 0 else ''}{tag}> tag(s)",
            ))
    
    # Check for common truncation patterns
    truncation_patterns = [
        (r'<\w+\s+\w+=$', "Truncated attribute value"),
        (r'<\w+\s+\w+="[^"]*$', "Unclosed attribute string"),
        (r'<path\s+\w+$', "Truncated SVG path"),
        (r'className="[^"]*$', "Unclosed className"),
    ]
    
    lines = code.split('\n')
    for i, line in enumerate(lines[-10:], start=max(1, len(lines)-9)):  # Check last 10 lines
        for pattern, msg in truncation_patterns:
            if re.search(pattern, line.strip()):
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="TRUNCATED_JSX",
                    message=f"Line {i}: {msg}",
                    suggestion="Code appears truncated - regenerate or extend max_tokens",
                ))
    
    valid = not any(i.level == ValidationLevel.ERROR for i in issues)
    return ValidationResult(valid=valid, issues=issues)


def validate_code_quality(code: str) -> ValidationResult:
    """
    Comprehensive code quality validation.
    
    Checks:
    - JSX balance
    - Required patterns present (export default, useState, etc.)
    - No forbidden patterns (hardcoded data for API apps)
    """
    issues = []
    
    # 1. JSX Balance
    jsx_result = validate_jsx_balance(code)
    issues.extend(jsx_result.issues)
    
    # 2. Required patterns
    if 'export default' not in code:
        issues.append(ValidationIssue(
            level=ValidationLevel.ERROR,
            code="MISSING_EXPORT",
            message="Missing 'export default App' statement",
            suggestion="Add 'export default App;' at the end of the file",
        ))
    
    if 'useState' not in code and 'function App' in code:
        issues.append(ValidationIssue(
            level=ValidationLevel.WARNING,
            code="NO_STATE",
            message="No useState calls found - app may be static",
            suggestion="Add state management for interactivity",
        ))
    
    # 3. Check for Gateway API when data components are present
    has_data_components = any(kw in code.lower() for kw in ['chart', 'table', 'stats', 'price'])
    has_gateway = 'api.faibric.com' in code or 'fetchFromGateway' in code
    
    if has_data_components and not has_gateway:
        issues.append(ValidationIssue(
            level=ValidationLevel.WARNING,
            code="MISSING_GATEWAY",
            message="Data components present but no Gateway API integration",
            suggestion="Add fetch calls to https://api.faibric.com/api/gateway/",
        ))
    
    # 4. Check for hardcoded data (forbidden)
    hardcoded_patterns = [
        (r'const\s+\w+\s*=\s*\[\s*\{[^}]+\}', "Hardcoded array data"),
        (r'useState\(\[\s*\{[^}]+\}\s*,', "Hardcoded initial state array"),
    ]
    
    for pattern, msg in hardcoded_patterns:
        if re.search(pattern, code):
            issues.append(ValidationIssue(
                level=ValidationLevel.INFO,
                code="HARDCODED_DATA",
                message=f"Found pattern: {msg}",
                suggestion="Replace with API fetch or placeholder",
            ))
    
    valid = not any(i.level == ValidationLevel.ERROR for i in issues)
    return ValidationResult(valid=valid, issues=issues)

