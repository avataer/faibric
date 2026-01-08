"""
Modular App Composer
====================

Composes apps from library components WITHOUT AI for composition.

For browser-based deployment (CDN React, no build step):
- Components are embedded inline (can't use ES6 imports)
- But we DON'T modify the library component code
- We only generate the wiring/glue code

This means:
- Library components are used AS-IS (proven to work)
- Only the small App wrapper needs to be generated
- Much lower risk of broken code

Benefits:
- Components from library stay unchanged
- AI only generates ~30 lines of wiring code
- Much smaller context window needed
- No truncation risk
"""

import logging
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ComponentFile:
    """A component as a separate file."""
    filename: str      # e.g., "HeroSection.tsx"
    component_name: str  # e.g., "HeroSection"
    code: str          # The actual component code
    component_type: str  # e.g., "hero"


class ModularComposer:
    """
    Composes apps with components as separate files.
    
    AI task is ONLY to generate the small App.tsx that imports
    and wires the components together.
    """
    
    # Component type to display name mapping
    COMPONENT_NAMES = {
        'navigation': 'Navigation',
        'hero': 'HeroSection',
        'services': 'ServicesGrid',
        'about': 'AboutSection',
        'contact': 'ContactForm',
        'footer': 'Footer',
        'testimonials': 'Testimonials',
        'pricing': 'PricingTable',
        'gallery': 'Gallery',
        'team': 'TeamSection',
        'features': 'Features',
        'cta': 'CallToAction',
        'form': 'FormSection',
        'dashboard': 'Dashboard',
        'chart': 'ChartSection',
        'table': 'DataTable',
        'sidebar': 'Sidebar',
        'modal': 'Modal',
        'card': 'Card',
        'list': 'ListView',
        'settings': 'SettingsView',
    }
    
    def compose(
        self,
        components: Dict[str, str],
        prompt: str,
        needs_real_data: bool = False
    ) -> Tuple[Dict[str, str], str]:
        """
        Compose a modular app from components.
        
        For browser deployment, returns a COMBINED code file that:
        1. Includes all library components as inline definitions
        2. Has a small App() that wires them together
        
        The key principle: Library components are used AS-IS.
        Only the wiring code is generated (deterministically).
        
        Args:
            components: Dict mapping component key to code
                       e.g., {"hero_simple": "<code>", "navigation_header": "<code>"}
            prompt: Original user prompt
            needs_real_data: Whether app needs Gateway API
            
        Returns:
            Tuple of (files_dict, combined_code)
            - files_dict: Dict mapping filepath to code (for future build-based deploys)
            - combined_code: Single file with all components + App wiring
        """
        logger.info(f"[MODULAR] Composing {len(components)} library components")
        
        # Step 1: Parse each component
        component_files: List[ComponentFile] = []
        
        for key, code in components.items():
            comp_file = self._create_component_file(key, code)
            component_files.append(comp_file)
            logger.debug(f"[MODULAR] Component: {comp_file.component_name} ({comp_file.component_type})")
        
        # Step 2: Generate COMBINED code for browser deployment
        combined_code = self._generate_combined_code(component_files, prompt, needs_real_data)
        
        # Step 3: Also build files dict (for future build-based deploys)
        files = {}
        for comp_file in component_files:
            filepath = f"src/components/{comp_file.filename}"
            files[filepath] = comp_file.code
        
        # Small App.tsx for reference (not used in browser deploy)
        files["src/App.tsx"] = self._generate_app_tsx_imports_only(component_files)
        
        logger.info(f"[MODULAR] Combined code: {len(combined_code)} bytes, {len(component_files)} components")
        return files, combined_code
    
    def _generate_combined_code(
        self,
        component_files: List[ComponentFile],
        prompt: str,
        needs_real_data: bool
    ) -> str:
        """
        Generate a single combined code file for browser deployment.
        
        Structure:
        1. All library components (AS-IS, just cleaned)
        2. Small App() function that wires them
        3. export default App
        """
        sections = []
        
        # Section 1: Library components (cleaned, but not modified)
        sections.append("// ═══════════════════════════════════════════════════════")
        sections.append("// LIBRARY COMPONENTS (from Faibric Component Library)")
        sections.append("// ═══════════════════════════════════════════════════════")
        
        for comp_file in component_files:
            clean_code = self._clean_component_for_embedding(comp_file.code, comp_file.component_name)
            sections.append(f"\n// ── {comp_file.component_name} ──")
            sections.append(clean_code)
        
        # Section 2: App wiring
        sections.append("\n// ═══════════════════════════════════════════════════════")
        sections.append("// APP WIRING")
        sections.append("// ═══════════════════════════════════════════════════════")
        
        app_code = self._generate_app_wiring(component_files, prompt, needs_real_data)
        sections.append(app_code)
        
        # Section 3: Export
        sections.append("\nexport default App;")
        
        combined = "\n".join(sections)
        
        # Validate braces
        open_braces = combined.count('{')
        close_braces = combined.count('}')
        if open_braces != close_braces:
            logger.warning(f"[MODULAR] Brace imbalance: {open_braces} open, {close_braces} close")
            combined = self._fix_brace_balance(combined, open_braces, close_braces)
        
        return combined
    
    def _fix_brace_balance(self, code: str, open_count: int, close_count: int) -> str:
        """Fix brace imbalance by adding/removing braces."""
        if open_count > close_count:
            # Too many opening braces - add closing braces at the end
            missing = open_count - close_count
            code = code.rstrip() + ('\n}' * missing)
            logger.info(f"[MODULAR] Added {missing} closing braces")
        elif close_count > open_count:
            # Too many closing braces - remove excess from end
            excess = close_count - open_count
            # Remove trailing }
            for _ in range(excess):
                # Find last } that's not part of essential code
                match = re.search(r'\}[;\s]*$', code)
                if match:
                    code = code[:match.start()] + code[match.end():]
                else:
                    # Try another pattern
                    code = code.rstrip()
                    if code.endswith('}'):
                        code = code[:-1]
            logger.info(f"[MODULAR] Removed {excess} excess closing braces")
        
        return code
    
    def _clean_component_for_embedding(self, code: str, component_name: str) -> str:
        """
        Clean a library component for embedding.
        
        We DON'T modify the component logic - just:
        - Remove import statements (CDN provides React)
        - Remove export statements (we'll export App)
        - Ensure component name is consistent
        """
        if not code or not code.strip():
            # Empty component - generate a placeholder
            logger.warning(f"[MODULAR] Empty component code for {component_name}, using placeholder")
            return f'''const {component_name} = () => (
  <div className="p-8 text-center text-gray-500">
    {component_name} Component
  </div>
);'''
        
        # Remove import statements
        code = re.sub(r'^import\s+.*?[\'"][^"\']+[\'"];\s*\n?', '', code, flags=re.MULTILINE)
        code = re.sub(r'^import\s+.*?from\s+[\'"][^"\']+[\'"];\s*\n?', '', code, flags=re.MULTILINE)
        
        # Remove export default at end
        code = re.sub(r'\n?export\s+default\s+\w+;\s*$', '', code)
        
        # Remove export keyword from declarations (keep the rest)
        code = re.sub(r'^export\s+(?=const|function|class)', '', code, flags=re.MULTILINE)
        
        return code.strip()
    
    def _generate_app_tsx_imports_only(self, component_files: List[ComponentFile]) -> str:
        """Generate App.tsx with imports (for build-based deploys)."""
        imports = ["import React, { useState } from 'react';"]
        for comp in component_files:
            imports.append(f"import {comp.component_name} from './components/{comp.component_name}';")
        
        return "\n".join(imports) + "\n\n// App wiring would go here"
    
    def _create_component_file(self, key: str, code: str) -> ComponentFile:
        """Convert a component key+code to a file."""
        # Parse key: "hero_simple" -> type="hero", variant="simple"
        parts = key.split('_', 1)
        component_type = parts[0]
        
        # Get display name
        component_name = self.COMPONENT_NAMES.get(
            component_type, 
            ''.join(word.capitalize() for word in key.split('_'))
        )
        
        filename = f"{component_name}.tsx"
        
        # Ensure component has proper export
        code = self._ensure_export(code, component_name)
        
        return ComponentFile(
            filename=filename,
            component_name=component_name,
            code=code,
            component_type=component_type
        )
    
    def _ensure_export(self, code: str, component_name: str) -> str:
        """Ensure component has a default export."""
        # If already has export default, use as-is
        if 'export default' in code:
            return code
        
        # If code defines the component, add export at end
        if f'const {component_name}' in code or f'function {component_name}' in code:
            return f"{code}\n\nexport default {component_name};"
        
        # Otherwise, wrap the code as a component
        return f"""
import React from 'react';

const {component_name} = () => {{
  return (
    {code}
  );
}};

export default {component_name};
"""
    
    def _generate_app_wiring(
        self,
        component_files: List[ComponentFile],
        prompt: str,
        needs_real_data: bool
    ) -> str:
        """
        Generate the small App function that wires components together.
        
        This is ~30 lines of deterministic code - NO AI NEEDED.
        """
        # Separate by role
        nav_components = [c for c in component_files if c.component_type in ('navigation', 'navbar', 'header', 'sidebar', 'menu')]
        footer_components = [c for c in component_files if c.component_type == 'footer']
        view_components = [c for c in component_files if c.component_type not in ('navigation', 'navbar', 'header', 'sidebar', 'menu', 'footer', 'layout')]
        
        # Determine views
        views = []
        for comp in view_components:
            view_id = comp.component_type
            if view_id in ('hero', 'landing', 'home'):
                view_id = 'home'
            views.append((view_id, comp.component_name))
        
        # Always include settings
        has_settings = any(v[0] == 'settings' for v in views)
        
        # Default view
        default_view = views[0][0] if views else 'home'
        
        # Navigation JSX
        if nav_components:
            nav = nav_components[0]
            nav_jsx = f'<{nav.component_name} currentView={{currentView}} onNavigate={{setCurrentView}} />'
        else:
            # Generate simple inline nav
            view_ids = [v[0] for v in views]
            if not has_settings:
                view_ids.append('settings')
            nav_items = ", ".join([f'"{v}"' for v in view_ids])
            nav_jsx = f'''<nav className="bg-white shadow">
        <div className="container mx-auto px-4 py-4 flex gap-4">
          {{[{nav_items}].map(view => (
            <button
              key={{view}}
              onClick={{() => setCurrentView(view)}}
              className={{currentView === view 
                ? "text-blue-600 font-medium" 
                : "text-gray-600 hover:text-blue-600"
              }}
            >
              {{view.charAt(0).toUpperCase() + view.slice(1)}}
            </button>
          ))}}
        </div>
      </nav>'''
        
        # View switching JSX
        view_jsx_parts = []
        for view_id, comp_name in views:
            view_jsx_parts.append(f'{{currentView === "{view_id}" && <{comp_name} />}}')
        
        # Add settings if not present
        if not has_settings:
            view_jsx_parts.append('''{currentView === "settings" && (
          <div className="max-w-2xl mx-auto p-8">
            <h2 className="text-2xl font-bold mb-6">Settings</h2>
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-gray-600">Configure your application settings here.</p>
            </div>
          </div>
        )}''')
        
        view_jsx = "\n        ".join(view_jsx_parts)
        
        # Footer JSX
        footer_jsx = ""
        if footer_components:
            footer_jsx = f'<{footer_components[0].component_name} />'
        
        # Data fetching (if needed)
        state_declarations = f'const [currentView, setCurrentView] = React.useState("{default_view}");'
        data_effect = ""
        
        if needs_real_data:
            state_declarations += """
  const [data, setData] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);"""
            data_effect = """
  React.useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('https://api.faibric.com/api/gateway/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ service: 'coingecko', endpoint: '/simple/price?ids=bitcoin&vs_currencies=usd' })
        });
        const result = await response.json();
        setData(result.data || result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);"""
        
        # Assemble App function
        app_code = f'''
function App() {{
  {state_declarations}
{data_effect}
  return (
    <div className="min-h-screen bg-gray-50">
      {nav_jsx}

      <main className="container mx-auto px-4 py-8">
        {view_jsx}
      </main>

      {footer_jsx}
    </div>
  );
}}'''
        
        return app_code
    
    def _generate_app_tsx(
        self,
        component_files: List[ComponentFile],
        prompt: str,
        needs_real_data: bool
    ) -> str:
        """Generate the main App.tsx that wires components (legacy, for reference)."""
        
        # Separate by role
        nav_components = [c for c in component_files if c.component_type in ('navigation', 'navbar', 'header', 'sidebar')]
        footer_components = [c for c in component_files if c.component_type == 'footer']
        view_components = [c for c in component_files if c.component_type not in ('navigation', 'navbar', 'header', 'sidebar', 'footer')]
        
        # Generate imports
        imports = ["import React, { useState } from 'react';"]
        for comp in component_files:
            imports.append(f"import {comp.component_name} from './components/{comp.component_name}';")
        
        # Determine views for navigation
        views = []
        for comp in view_components:
            view_id = comp.component_type
            if view_id == 'hero':
                view_id = 'home'
            views.append((view_id, comp.component_name))
        
        # Always include settings
        if not any(v[0] == 'settings' for v in views):
            views.append(('settings', 'SettingsView'))
            # Add inline SettingsView since it's not from library
            imports.append("")
            imports.append("// Built-in Settings View")
            imports.append("const SettingsView = () => (")
            imports.append("  <div className=\"p-8 max-w-2xl mx-auto\">")
            imports.append("    <h2 className=\"text-2xl font-bold mb-6\">Settings</h2>")
            imports.append("    <div className=\"bg-white rounded-lg shadow p-6\">")
            imports.append("      <p className=\"text-gray-600\">Configure your application settings here.</p>")
            imports.append("    </div>")
            imports.append("  </div>")
            imports.append(");")
        
        # Navigation JSX
        nav_jsx = ""
        if nav_components:
            nav = nav_components[0]
            nav_jsx = f'<{nav.component_name} currentView={{currentView}} onNavigate={{setCurrentView}} />'
        else:
            # Simple inline nav
            nav_items = ", ".join([f'"{v[0]}"' for v in views])
            nav_jsx = f'''<nav className="bg-white shadow p-4">
        <div className="container mx-auto flex gap-4">
          {{[{nav_items}].map(view => (
            <button
              key={{view}}
              onClick={{() => setCurrentView(view)}}
              className={{currentView === view ? "text-blue-600 font-medium" : "text-gray-600"}}
            >
              {{view.charAt(0).toUpperCase() + view.slice(1)}}
            </button>
          ))}}
        </div>
      </nav>'''
        
        # View switching JSX
        view_jsx_lines = []
        for view_id, comp_name in views:
            view_jsx_lines.append(f'{{currentView === "{view_id}" && <{comp_name} />}}')
        view_jsx = "\n        ".join(view_jsx_lines)
        
        # Footer JSX
        footer_jsx = ""
        if footer_components:
            footer_jsx = f'<{footer_components[0].component_name} />'
        
        # Data fetching if needed
        data_state = ""
        data_effect = ""
        if needs_real_data:
            data_state = """
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);"""
            data_effect = """
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('https://api.faibric.com/api/gateway/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ service: 'coingecko', endpoint: '/simple/price?ids=bitcoin&vs_currencies=usd' })
        });
        const result = await response.json();
        setData(result.data || result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);"""
        
        # Default view
        default_view = views[0][0] if views else 'home'
        
        # Assemble App.tsx
        app_tsx = f"""{chr(10).join(imports)}

function App() {{
  const [currentView, setCurrentView] = useState('{default_view}');{data_state}
{data_effect}
  return (
    <div className="min-h-screen bg-gray-50">
      {nav_jsx}

      <main className="container mx-auto px-4 py-8">
        {view_jsx}
      </main>

      {footer_jsx}
    </div>
  );
}}

export default App;
"""
        
        return app_tsx


def compose_modular(
    components: Dict[str, str],
    prompt: str = "",
    needs_real_data: bool = False
) -> Tuple[Dict[str, str], str]:
    """
    Main entry point for modular composition.
    
    Returns (files_dict, app_tsx_code).
    """
    composer = ModularComposer()
    return composer.compose(components, prompt, needs_real_data)
