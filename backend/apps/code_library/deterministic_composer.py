"""
Deterministic App Composer
==========================

Composes App.tsx WITHOUT a big AI call.

Strategy:
1. Take already-generated component code
2. Embed components directly into App.tsx
3. Use templates for the App shell
4. Generate wiring deterministically

Benefits:
- Zero truncation risk (no big AI output)
- Instant (<10ms vs 5-15s for AI)
- 100% consistent output
- Easy to debug

This replaces the AI composition step that was causing JSX breakage.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ComponentInfo:
    """Extracted info about a component."""
    key: str  # e.g., "hero_simple"
    name: str  # e.g., "HeroSection"
    code: str  # The actual component code
    component_type: str  # e.g., "hero"
    variant: str  # e.g., "simple"
    is_navigation: bool = False
    is_footer: bool = False
    is_layout: bool = False
    view_id: Optional[str] = None  # e.g., "home" for routing


class DeterministicComposer:
    """
    Composes App.tsx from component code using templates.
    
    NO AI CALLS - purely mechanical string operations.
    """
    
    # Component types that are navigation
    NAV_TYPES = {'navigation', 'navbar', 'header', 'sidebar', 'menu'}
    
    # Component types that are footers
    FOOTER_TYPES = {'footer'}
    
    # Component types that are layouts (wrap content)
    LAYOUT_TYPES = {'layout', 'wrapper', 'container'}
    
    # Component types that are views (switchable content)
    VIEW_TYPES = {
        'hero': 'home',
        'landing': 'home', 
        'home': 'home',
        'dashboard': 'dashboard',
        'analytics': 'analytics',
        'form': 'contact',
        'contact': 'contact',
        'about': 'about',
        'settings': 'settings',
        'profile': 'profile',
        'list': 'list',
        'table': 'data',
        'chart': 'charts',
        'gallery': 'gallery',
        'portfolio': 'portfolio',
        'blog': 'blog',
        'pricing': 'pricing',
        'features': 'features',
        'testimonials': 'testimonials',
        'team': 'team',
        'services': 'services',
        'products': 'products',
        'shop': 'shop',
        'cart': 'cart',
        'checkout': 'checkout',
    }
    
    def compose(
        self,
        components: Dict[str, str],
        prompt: str = "",
        needs_real_data: bool = False
    ) -> str:
        """
        Compose a complete App.tsx from component code.
        
        Args:
            components: Dict mapping component key to code
                       e.g., {"hero_simple": "<code>", "navigation_header": "<code>"}
            prompt: Original user prompt (for context)
            needs_real_data: Whether to include Gateway API fetching
            
        Returns:
            Complete App.tsx code
        """
        logger.info(f"[COMPOSER] Composing {len(components)} components deterministically")
        
        # Step 1: Extract info from each component
        component_infos = []
        for key, code in components.items():
            info = self._extract_component_info(key, code)
            component_infos.append(info)
            logger.debug(f"[COMPOSER] {key} -> {info.name} (nav={info.is_navigation}, footer={info.is_footer}, view={info.view_id})")
        
        # Step 2: Separate components by type
        nav_components = [c for c in component_infos if c.is_navigation]
        footer_components = [c for c in component_infos if c.is_footer]
        layout_components = [c for c in component_infos if c.is_layout]
        view_components = [c for c in component_infos if c.view_id and not c.is_navigation and not c.is_footer]
        
        # Step 3: Build the App.tsx
        sections = []
        
        # 3a. Imports
        sections.append(self._generate_imports(needs_real_data))
        
        # 3b. Embedded component code
        for info in component_infos:
            clean_code = self._clean_component_code(info.code)
            sections.append(f"// ========== {info.key.upper()} ==========\n{clean_code}")
        
        # 3c. App component
        app_code = self._generate_app_component(
            nav_components=nav_components,
            footer_components=footer_components,
            view_components=view_components,
            needs_real_data=needs_real_data
        )
        sections.append(app_code)
        
        # 3d. Export
        sections.append("export default App;")
        
        result = "\n\n".join(sections)
        
        # Validate braces are balanced
        open_braces = result.count('{')
        close_braces = result.count('}')
        if open_braces != close_braces:
            logger.warning(f"[COMPOSER] Brace imbalance: {open_braces} open, {close_braces} close")
            result = self._fix_brace_balance(result)
        
        logger.info(f"[COMPOSER] Generated {len(result)} bytes, {len(result.split(chr(10)))} lines")
        return result
    
    def _extract_component_info(self, key: str, code: str) -> ComponentInfo:
        """Extract information about a component from its code."""
        # Parse key: "hero_simple" -> type="hero", variant="simple"
        parts = key.split('_', 1)
        component_type = parts[0]
        variant = parts[1] if len(parts) > 1 else "default"
        
        # Extract component name from code
        name = self._extract_component_name(code)
        if not name:
            # Generate name from key
            name = ''.join(word.capitalize() for word in key.split('_'))
        
        # Determine component role
        is_navigation = component_type in self.NAV_TYPES
        is_footer = component_type in self.FOOTER_TYPES
        is_layout = component_type in self.LAYOUT_TYPES
        view_id = self.VIEW_TYPES.get(component_type)
        
        return ComponentInfo(
            key=key,
            name=name,
            code=code,
            component_type=component_type,
            variant=variant,
            is_navigation=is_navigation,
            is_footer=is_footer,
            is_layout=is_layout,
            view_id=view_id
        )
    
    def _extract_component_name(self, code: str) -> Optional[str]:
        """Extract the component name from code."""
        # Pattern 1: const ComponentName = 
        match = re.search(r'const\s+([A-Z][a-zA-Z0-9]*)\s*=', code)
        if match:
            return match.group(1)
        
        # Pattern 2: function ComponentName(
        match = re.search(r'function\s+([A-Z][a-zA-Z0-9]*)\s*\(', code)
        if match:
            return match.group(1)
        
        # Pattern 3: export default ComponentName
        match = re.search(r'export\s+default\s+([A-Z][a-zA-Z0-9]*)', code)
        if match:
            return match.group(1)
        
        return None
    
    def _clean_component_code(self, code: str) -> str:
        """Clean component code for embedding."""
        if not code:
            return ""
        
        # Remove import statements
        code = re.sub(r'^import\s+[^;]+;\s*\n?', '', code, flags=re.MULTILINE)
        
        # Remove export default at end
        code = re.sub(r'\n?export\s+default\s+\w+;\s*$', '', code)
        
        # Remove standalone 'export' keyword but keep the rest
        code = re.sub(r'^export\s+(?=const|function|class)', '', code, flags=re.MULTILINE)
        
        return code.strip()
    
    def _generate_imports(self, needs_real_data: bool) -> str:
        """Generate import statements."""
        imports = ["import React, { useState, useEffect } from 'react';"]
        return "\n".join(imports)
    
    def _generate_app_component(
        self,
        nav_components: List[ComponentInfo],
        footer_components: List[ComponentInfo],
        view_components: List[ComponentInfo],
        needs_real_data: bool
    ) -> str:
        """Generate the main App component."""
        
        # Determine default view
        default_view = "home"
        if view_components:
            default_view = view_components[0].view_id or "home"
        
        # Build state declarations
        state_lines = [
            f'const [currentView, setCurrentView] = useState("{default_view}");',
        ]
        
        if needs_real_data:
            state_lines.extend([
                'const [loading, setLoading] = useState(true);',
                'const [data, setData] = useState(null);',
                'const [error, setError] = useState(null);',
            ])
        
        # Build navigation handler
        handler_lines = [
            'const handleNavigate = (viewId) => {',
            '  setCurrentView(viewId);',
            '};',
        ]
        
        # Build data fetching effect if needed
        effect_lines = []
        if needs_real_data:
            effect_lines = [
                '',
                'useEffect(() => {',
                '  const fetchData = async () => {',
                '    try {',
                '      setLoading(true);',
                '      const response = await fetch("https://api.faibric.com/api/gateway/", {',
                '        method: "POST",',
                '        headers: { "Content-Type": "application/json" },',
                '        body: JSON.stringify({ service: "coingecko", endpoint: "/simple/price?ids=bitcoin&vs_currencies=usd" })',
                '      });',
                '      const result = await response.json();',
                '      setData(result.data || result);',
                '    } catch (err) {',
                '      setError(err.message);',
                '    } finally {',
                '      setLoading(false);',
                '    }',
                '  };',
                '  fetchData();',
                '}, []);',
            ]
        
        # Build navigation JSX
        nav_jsx = ""
        if nav_components:
            nav = nav_components[0]
            nav_jsx = f'<{nav.name} currentView={{currentView}} onNavigate={{handleNavigate}} />'
        else:
            # Generate simple navigation
            nav_items = [vc.view_id for vc in view_components if vc.view_id]
            if nav_items:
                nav_jsx = self._generate_simple_nav(nav_items)
        
        # Build view switching JSX
        view_jsx_lines = []
        for vc in view_components:
            view_jsx_lines.append(
                f'{{currentView === "{vc.view_id}" && <{vc.name} />}}'
            )
        
        # Always include settings view
        if not any(vc.view_id == "settings" for vc in view_components):
            view_jsx_lines.append('{currentView === "settings" && <SettingsView />}')
        
        view_jsx = "\n          ".join(view_jsx_lines)
        
        # Build footer JSX
        footer_jsx = ""
        if footer_components:
            footer = footer_components[0]
            footer_jsx = f'<{footer.name} />'
        
        # Assemble App component
        app_code = f'''
// ========== SIMPLE SETTINGS VIEW ==========
const SettingsView = () => (
  <div className="p-8 max-w-2xl mx-auto">
    <h2 className="text-2xl font-bold mb-6">Settings</h2>
    <div className="bg-white rounded-lg shadow p-6">
      <p className="text-gray-600">Configure your application settings here.</p>
    </div>
  </div>
);

// ========== MAIN APP ==========
function App() {{
  {chr(10).join("  " + line for line in state_lines)}

  {chr(10).join("  " + line for line in handler_lines)}
  {"".join(effect_lines)}

  return (
    <div className="min-h-screen bg-gray-50">
      {{/* Navigation */}}
      {nav_jsx}

      {{/* Main Content */}}
      <main className="container mx-auto px-4 py-8">
        {view_jsx if view_jsx else '{/* Add your content here */}'}
      </main>

      {{/* Footer */}}
      {footer_jsx}
    </div>
  );
}}'''
        
        return app_code
    
    def _generate_simple_nav(self, view_ids: List[str]) -> str:
        """Generate a simple navigation component inline."""
        nav_items = ", ".join([f'{{ id: "{vid}", label: "{vid.title()}" }}' for vid in view_ids])
        
        return f'''<nav className="bg-white shadow">
        <div className="container mx-auto px-4">
          <div className="flex space-x-4 py-4">
            {{[{nav_items}].map(item => (
              <button
                key={{item.id}}
                onClick={{() => handleNavigate(item.id)}}
                className={{currentView === item.id 
                  ? "px-4 py-2 bg-blue-600 text-white rounded" 
                  : "px-4 py-2 text-gray-600 hover:text-blue-600"
                }}
              >
                {{item.label}}
              </button>
            ))}}
          </div>
        </div>
      </nav>'''
    
    def _fix_brace_balance(self, code: str) -> str:
        """Fix brace imbalance."""
        open_braces = code.count('{')
        close_braces = code.count('}')
        
        if open_braces > close_braces:
            # Add missing closing braces
            code += '\n' + ('}' * (open_braces - close_braces))
        elif close_braces > open_braces:
            # Remove excess closing braces from end
            excess = close_braces - open_braces
            for _ in range(excess):
                last_close = code.rfind('}')
                if last_close != -1:
                    code = code[:last_close] + code[last_close+1:]
        
        return code


# Convenience function
def compose_deterministic(
    components: Dict[str, str],
    prompt: str = "",
    needs_real_data: bool = False
) -> str:
    """
    Compose App.tsx deterministically without AI.
    
    This is the main entry point for deterministic composition.
    """
    composer = DeterministicComposer()
    return composer.compose(components, prompt, needs_real_data)
