# Faibric Connector System v2 - Original Design

## Goal
Create the world's best UI component connector system, proven with measurements.

## Core Innovation: Constraint-Based Automatic Wiring

Instead of:
- Manual prop passing
- AI-generated wiring (error-prone)
- Template-based composition (inflexible)

We use: **Constraint Satisfaction** to automatically discover valid connections.

## Key Insight

A component connection is a **constraint satisfaction problem**:
- Component A outputs `currentView: string`
- Component B requires input `activeTab: string`  
- These are **compatible** if types match and semantics align

The system finds ALL valid wirings automatically, then selects the optimal one.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONNECTOR SYSTEM V2                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. PORT DEFINITIONS (per component)                            │
│     ┌──────────────┐                                           │
│     │ Component    │                                           │
│     │ ┌──────────┐ │                                           │
│     │ │ IN ports │◄──── typed inputs with constraints          │
│     │ └──────────┘ │                                           │
│     │ ┌──────────┐ │                                           │
│     │ │OUT ports │────► typed outputs with guarantees          │
│     │ └──────────┘ │                                           │
│     └──────────────┘                                           │
│                                                                 │
│  2. CONNECTION SOLVER                                           │
│     - Takes: Set of components with ports                       │
│     - Finds: All valid connection graphs                        │
│     - Returns: Optimal wiring (minimal state, maximal reuse)    │
│                                                                 │
│  3. CODE GENERATOR                                              │
│     - Takes: Connection graph                                   │
│     - Produces: Exact React code (no AI)                        │
│     - Guarantees: Type-safe, minimal, correct                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Port Type System

### Basic Types
```
STRING, NUMBER, BOOLEAN, DATE
ARRAY<T>, RECORD<K,V>, OPTIONAL<T>
```

### Semantic Types (our innovation)
```
VIEW_ID      - string that identifies a view/page
NAV_ITEMS    - array of navigation items
TABLE_DATA   - array of row objects
CHART_POINTS - array of {x, y} points
FORM_FIELDS  - array of field definitions
USER         - user object with id, name, email
LOADING      - boolean indicating loading state
ERROR        - Error | null
```

### Type Compatibility Rules
```
1. Exact match: STRING → STRING ✓
2. Subtype: "dashboard" → VIEW_ID ✓ (literal to semantic)
3. Structural: {id, name} → USER ✓ (if fields present)
4. Coercion: NUMBER → STRING ✓ (with toString)
5. Optional: T → OPTIONAL<T> ✓ (always)
```

## Connection Semantics

### Directional Connections
```
OUTPUT → INPUT (data flow)
EVENT → HANDLER (control flow)
STATE.READ ← STATE.WRITE (shared state)
SLOT.CHILD → SLOT.PARENT (composition)
```

### Connection Constraints
```
- REQUIRED inputs MUST be satisfied
- OPTIONAL inputs MAY be satisfied
- Outputs MAY connect to multiple inputs
- Inputs accept at most one connection (unless MERGE)
```

## Solver Algorithm

```python
def solve(components: List[Component]) -> ConnectionGraph:
    # 1. Extract all ports
    outputs = flatten([c.outputs for c in components])
    inputs = flatten([c.inputs for c in components])
    
    # 2. Build compatibility matrix
    compat = {}
    for out in outputs:
        for inp in inputs:
            if is_compatible(out.type, inp.type):
                compat[(out, inp)] = compatibility_score(out, inp)
    
    # 3. Find optimal assignment (constraint satisfaction)
    # - All REQUIRED inputs must be satisfied
    # - Minimize total state declarations
    # - Maximize semantic matches over type coercions
    
    return solve_csp(compat, constraints)
```

## Code Generation

The generator produces EXACT code, not suggestions:

```python
def generate(graph: ConnectionGraph) -> str:
    code = []
    
    # 1. Imports (deterministic)
    code.append(generate_imports(graph))
    
    # 2. State declarations (from shared state analysis)
    for state in graph.shared_states:
        code.append(f"const [{state.name}, set{state.name.title()}] = useState({state.default});")
    
    # 3. Handlers (from event connections)
    for event in graph.events:
        code.append(generate_handler(event))
    
    # 4. Component instances (from connection graph)
    code.append("return (")
    code.append(generate_jsx(graph.root))
    code.append(");")
    
    return "\n".join(code)
```

## Measurement Plan

### KPIs to Track

| KPI | Definition | Target |
|-----|------------|--------|
| **Wiring Success Rate** | % of compositions with zero connection errors | 100% |
| **Type Safety** | % of connections with compile-time type checking | 100% |
| **Code Correctness** | % of generated apps that render without errors | 100% |
| **Optimality** | State count vs theoretical minimum | 1.0x |
| **Speed** | Time to generate wiring | <100ms |

### Comparison Baselines

1. **AI-Generated (current)**: Claude generates wiring
2. **Manual Template**: Hardcoded composition templates
3. **Connector V1**: Current connector system (not used)
4. **Connector V2**: This new system

### Test Suite

1. **Unit Tests**: Each port type, each compatibility rule
2. **Integration Tests**: Full app compositions
3. **Stress Tests**: 50+ components, complex graphs
4. **Regression Tests**: Known failure cases from production

## Success Criteria

To claim "best in the world":

1. **100% wiring success rate** (vs ~60% for AI-generated)
2. **100% type safety** (vs 0% for AI-generated)
3. **100% code correctness** (vs ~70% for AI-generated)
4. **<100ms generation** (vs ~5s for AI-generated)
5. **Published benchmarks** with reproducible results

