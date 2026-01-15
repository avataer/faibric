"""
TypeScript Annotation Stripper

Removes TypeScript type annotations from JavaScript code.
Needed because the component library was built with TypeScript,
but we now generate plain JavaScript (.jsx files).
"""

import re


def strip_typescript_annotations(code: str) -> str:
    """
    Remove TypeScript type annotations from JavaScript code.

    Handles:
    - Type annotations: const x: string = ...
    - Generic types: Array<T>, Record<K,V>, etc.
    - Interface definitions
    - Type imports
    - Function parameter types
    - Return type annotations
    """
    if not code:
        return code

    # Remove interface/type definitions entirely (including multi-line interfaces)
    # First handle single-line interfaces
    code = re.sub(r'^\s*(?:export\s+)?interface\s+\w+\s*\{[^}]*\}\s*;?\s*$', '', code, flags=re.MULTILINE)
    # Then handle multi-line interfaces with generic type parameters like Column<T>
    code = re.sub(r'^\s*(?:export\s+)?interface\s+\w+(?:<[^>]+>)?\s*\{[\s\S]*?\n\}\s*;?\s*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^\s*(?:export\s+)?type\s+\w+\s*=\s*[^;]+;\s*$', '', code, flags=re.MULTILINE)

    # Remove keyof keyword (TypeScript-specific)
    code = re.sub(r'\bkeyof\s+\w+', 'string', code)

    # Remove type imports: import type { X } from 'y' or import { type X } from 'y'
    code = re.sub(r'import\s+type\s+\{[^}]*\}\s*from\s*[\'"][^\'"]*[\'"];?\s*\n?', '', code)
    code = re.sub(r',\s*type\s+\w+', '', code)  # Remove ", type X" from imports

    # Remove type annotations from variable declarations
    # const x: Type = ... -> const x = ...
    code = re.sub(r'(const|let|var)\s+(\w+)\s*:\s*[^=]+\s*=', r'\1 \2 =', code)

    # Remove type annotations from function parameters
    # (param: Type) -> (param)
    # (param: Type = default) -> (param = default)
    # IMPORTANT: Only strip actual TYPE annotations, NOT values
    #
    # TypeScript TYPE-ONLY keywords (never valid as JS values):
    # - string, number, boolean, void, never, any, unknown, symbol, bigint
    #
    # TypeScript types that ARE also valid JavaScript values:
    # - null, undefined, object - DO NOT STRIP these
    #
    # JavaScript values look like:
    # - Simple identifiers: Home, Icon, Modal (React components)
    # - null, undefined, object
    #
    # We ONLY strip if it looks like a TYPE (type-only keywords, generics, arrays, unions)
    type_only_keywords = r'string|number|boolean|void|never|any|unknown|symbol|bigint'
    # Complex types: contain <, |, &, or [] - these are definitely types
    complex_type_pattern = rf'(?:{type_only_keywords}|[\w.]+<[^>]+>|[\w.]+\[\]|[\w.]+\s*\|\s*[\w.]+|[\w.]+\s*&\s*[\w.]+)'
    code = re.sub(rf'(\w+)\s*:\s*(?:{complex_type_pattern})(\s*=)', r'\1\2', code)  # with default
    code = re.sub(rf'(\w+)\s*:\s*(?:{complex_type_pattern})(?=[,\)])', r'\1', code)  # without default

    # AGGRESSIVE: Strip PascalCase type annotations in function parameters
    # Pattern: (param: PascalCaseType) or (param: PascalCaseType,
    # These are almost always TypeScript types like FormValues, EventHandler, Props, etc.
    # NOT React components (which would be default values, not type annotations)
    code = re.sub(r'(\w+)\s*:\s*([A-Z][a-zA-Z0-9]*)\s*(?=[,\)])', r'\1', code)

    # Strip inline object type annotations in arrow function parameters
    # Pattern: ({ prop }: { prop: type }) -> ({ prop })
    # Pattern: ({ prop }: { prop }) -> ({ prop })
    # This catches: const Fn = ({ x }: { x: string }) => ...
    code = re.sub(r'(\{[^}]+\})\s*:\s*\{[^}]+\}', r'\1', code)

    # Remove return type annotations
    # ): ReturnType => -> ) =>
    # ): ReturnType { -> ) {
    code = re.sub(r'\)\s*:\s*[\w<>\[\],\s|&]+\s*(=>|\{)', r') \1', code)

    # Remove generic type parameters from function calls and declarations
    # Array<string> -> Array
    # Record<string, number> -> object (simplified)
    code = re.sub(r'Record<[^>]+>', 'object', code)
    code = re.sub(r'Array<[^>]+>', 'Array', code)
    code = re.sub(r'Map<[^>]+>', 'Map', code)
    code = re.sub(r'Set<[^>]+>', 'Set', code)
    code = re.sub(r'Promise<[^>]+>', 'Promise', code)

    # Remove React-specific generics
    code = re.sub(r'React\.FC<[^>]*>', 'React.FC', code)
    code = re.sub(r'React\.ComponentType<[^>]*>', 'React.ComponentType', code)
    code = re.sub(r'React\.ReactNode', 'any', code)
    code = re.sub(r'React\.ReactElement', 'any', code)

    # Remove as Type assertions
    code = re.sub(r'\s+as\s+[\w<>\[\],\s|&]+(?=[;\),\]\}])', '', code)

    # Remove angle bracket type assertions: <Type>value
    # IMPORTANT: Do NOT match JSX tags like <span>, <div>, <button>
    # JSX tags are lowercase, TypeScript type assertions start with uppercase
    # Pattern: <Type> where Type starts with uppercase letter
    code = re.sub(r'<[A-Z][\w<>\[\],\s|&]*>(?=\w)', '', code)

    # Remove remaining standalone type annotations that might have been missed
    # IMPORTANT: Only strip actual TYPE annotations, NOT object property values
    #
    # We ONLY strip if it looks like a TYPE:
    # - Type-only keywords: string, number, boolean, void, never, any, unknown, symbol, bigint
    # - Generics: Array<T>, Record<K,V>
    # - Complex: Type | null, Type[]
    #
    # We do NOT strip:
    # - null, undefined, object - these are also valid JavaScript VALUES
    # - Simple CamelCase identifiers like Home, Icon, Modal (React components)
    type_only_keywords = r'string|number|boolean|void|never|any|unknown|symbol|bigint'
    # Only strip types that have clear type markers: type-only primitives, generics, arrays, unions
    code = re.sub(
        rf':\s*(?:{type_only_keywords}|[\w.]+<[^>]+>|[\w.]+\[\]|[\w.]+\s*\|\s*[\w.]+)(?=\s*[,\)\]\}}])',
        '',
        code
    )

    # Clean up any double spaces created
    code = re.sub(r'  +', ' ', code)

    # Clean up double commas created when removing type-only parameters
    # e.g., "isLoading = false,," -> "isLoading = false,"
    code = re.sub(r',\s*,', ',', code)

    # Clean up lines that are now just commas or empty after removing type-only params
    # e.g., lines that were just "success: boolean," are now just ","
    code = re.sub(r'^\s*,\s*$', '', code, flags=re.MULTILINE)

    # Clean up trailing commas before closing parens/braces (syntax error in some cases)
    # e.g., "value,)" -> "value)"
    code = re.sub(r',(\s*[)\]}])', r'\1', code)

    # Clean up empty lines created by removing interfaces/types
    code = re.sub(r'\n\s*\n\s*\n', '\n\n', code)

    return code


def validate_jsx_tags(code: str) -> tuple[bool, str]:
    """
    Validate that JSX tags are properly balanced.

    Returns (is_valid, error_message)

    This catches the common "Expected corresponding JSX closing tag" error
    before deployment.
    """
    if not code:
        return True, ""

    # Find all JSX tags (opening and closing)
    # Opening: <tagName or <TagName
    # Self-closing: <tagName /> or <TagName />
    # Closing: </tagName> or </TagName>

    tag_pattern = re.compile(r'<(/?)([a-zA-Z][a-zA-Z0-9]*)\s*[^>]*?(/?)>')

    stack = []

    for match in tag_pattern.finditer(code):
        is_closing = match.group(1) == '/'
        tag_name = match.group(2)
        is_self_closing = match.group(3) == '/'

        # Skip self-closing tags
        if is_self_closing:
            continue

        # Skip void elements that don't need closing tags
        void_elements = {'br', 'hr', 'img', 'input', 'meta', 'link', 'area', 'base', 'col', 'embed', 'source', 'track', 'wbr'}
        if tag_name.lower() in void_elements:
            continue

        if is_closing:
            if not stack:
                return False, f"Unexpected closing tag </{tag_name}> with no matching opening tag"
            expected = stack.pop()
            if expected != tag_name:
                return False, f"Expected closing tag </{expected}> but found </{tag_name}>"
        else:
            stack.append(tag_name)

    if stack:
        return False, f"Unclosed tags: {', '.join(f'<{tag}>' for tag in stack)}"

    return True, ""


def fix_jsx_tags(code: str) -> str:
    """
    Attempt to fix common JSX tag issues.

    This is a last-resort fix for mismatched tags.
    """
    if not code:
        return code

    # Fix common pattern: extra closing tags at end
    # e.g., </div></div> when there should only be one
    is_valid, error = validate_jsx_tags(code)

    if is_valid:
        return code

    # If there are unclosed tags, try to close them
    if "Unclosed tags:" in error:
        # Extract the unclosed tag names
        unclosed = re.findall(r'<(\w+)>', error)
        for tag in reversed(unclosed):
            # Add closing tag at the end before the last export/return
            if 'export default' in code:
                code = code.replace('export default', f'</{tag}>\n\nexport default')
            else:
                code += f'\n</{tag}>'

    return code
