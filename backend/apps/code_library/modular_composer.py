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

from .typescript_stripper import strip_typescript_annotations

logger = logging.getLogger(__name__)


@dataclass
class ComponentFile:
    """A component as a separate file."""
    filename: str      # e.g., "HeroSection.jsx"
    component_name: str  # e.g., "HeroSection"
    code: str          # The actual component code
    component_type: str  # e.g., "hero"


class ModularComposer:
    """
    Composes apps with components as separate files.

    AI task is ONLY to generate the small App.jsx that imports
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

        # Store prompt for use in _get_default_props_for_component()
        self._current_prompt = prompt

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
        
        # Small App.jsx for reference (not used in browser deploy)
        files["src/App.jsx"] = self._generate_app_jsx_imports_only(component_files)
        
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

        # NOTE: No import statement needed - React is provided globally by CDN
        # All hooks must use React.useState, React.useEffect, etc.
        sections.append("// React is provided globally by CDN - no import needed")
        sections.append("")

        # SVG Icon components (needed because lucide-react isn't available in browser)
        sections.append("// ═══════════════════════════════════════════════════════")
        sections.append("// ICON COMPONENTS (SVG replacements for lucide-react)")
        sections.append("// ═══════════════════════════════════════════════════════")
        sections.append(self._get_icon_definitions())
        sections.append("")

        # Section 1: Library components (cleaned, but not modified)
        sections.append("// ═══════════════════════════════════════════════════════")
        sections.append("// LIBRARY COMPONENTS (from Faibric Component Library)")
        sections.append("// ═══════════════════════════════════════════════════════")
        
        for comp_file in component_files:
            clean_code = self._clean_component_for_embedding(comp_file.code, comp_file.component_name)
            
            # CRITICAL: Validate each component is complete (ends with }; or })
            clean_code = self._ensure_component_complete(clean_code, comp_file.component_name)
            
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
    
    def _ensure_component_complete(self, code: str, component_name: str) -> str:
        """
        CRITICAL: Ensure a component is complete with proper closing.
        
        Arrow function components must end with };
        Regular function components must end with }
        
        This catches truncation/corruption issues.
        """
        if not code or not code.strip():
            return code
        
        code = code.rstrip()
        
        # Check brace balance for this specific component
        open_braces = code.count('{')
        close_braces = code.count('}')
        
        if open_braces != close_braces:
            missing = open_braces - close_braces
            if missing > 0:
                # Add missing closing braces
                logger.warning(f"[MODULAR] Component {component_name} missing {missing} closing braces, adding them")
                code += '\n' + ('}' * missing)
            elif missing < 0:
                # Too many closing braces - this is a problem but don't remove
                logger.warning(f"[MODULAR] Component {component_name} has {abs(missing)} extra closing braces")
        
        # Ensure arrow function components end with };
        # Pattern: const Name = () => { ... }; 
        if f'const {component_name}' in code or 'const ' in code.split('\n')[0]:
            # This is an arrow function - should end with };
            if code.endswith('}') and not code.endswith('};'):
                code += ';'
                logger.info(f"[MODULAR] Added trailing ; to component {component_name}")
        
        return code

    def _get_icon_definitions(self) -> str:
        """
        Return SVG icon component definitions.

        These replace lucide-react icons which aren't available in browser runtime.
        Library components use these icons, so we must define them.
        """
        return '''
const Home = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
    <polyline points="9 22 9 12 15 12 15 22"></polyline>
  </svg>
);

const Check = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"></polyline>
  </svg>
);

const ArrowRight = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="5" y1="12" x2="19" y2="12"></line>
    <polyline points="12 5 19 12 12 19"></polyline>
  </svg>
);

const Clock = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"></circle>
    <polyline points="12 6 12 12 16 14"></polyline>
  </svg>
);

const Settings = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"></circle>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
  </svg>
);

const X = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
  </svg>
);

const Plus = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19"></line>
    <line x1="5" y1="12" x2="19" y2="12"></line>
  </svg>
);

const ChevronLeft = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="15 18 9 12 15 6"></polyline>
  </svg>
);

const ChevronRight = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="9 18 15 12 9 6"></polyline>
  </svg>
);

const ChevronUp = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="18 15 12 9 6 15"></polyline>
  </svg>
);

const ChevronDown = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="6 9 12 15 18 9"></polyline>
  </svg>
);

const ArrowLeft = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="19" y1="12" x2="5" y2="12"></line>
    <polyline points="12 19 5 12 12 5"></polyline>
  </svg>
);

const Menu = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="3" y1="12" x2="21" y2="12"></line>
    <line x1="3" y1="6" x2="21" y2="6"></line>
    <line x1="3" y1="18" x2="21" y2="18"></line>
  </svg>
);

const User = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
    <circle cx="12" cy="7" r="4"></circle>
  </svg>
);

const Mail = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
    <polyline points="22,6 12,13 2,6"></polyline>
  </svg>
);

const Phone = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
  </svg>
);

const Calendar = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
    <line x1="16" y1="2" x2="16" y2="6"></line>
    <line x1="8" y1="2" x2="8" y2="6"></line>
    <line x1="3" y1="10" x2="21" y2="10"></line>
  </svg>
);

const Facebook = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"></path>
  </svg>
);

const Twitter = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M23 3a10.9 10.9 0 0 1-3.14 1.53 4.48 4.48 0 0 0-7.86 3v1A10.66 10.66 0 0 1 3 4s-4 9 5 13a11.64 11.64 0 0 1-7 2c9 5 20 0 20-11.5a4.5 4.5 0 0 0-.08-.83A7.72 7.72 0 0 0 23 3z"></path>
  </svg>
);

const Linkedin = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"></path>
    <rect x="2" y="9" width="4" height="12"></rect>
    <circle cx="4" cy="4" r="2"></circle>
  </svg>
);

const Instagram = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
    <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
    <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
  </svg>
);

const MapPin = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
    <circle cx="12" cy="10" r="3"></circle>
  </svg>
);

const Star = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
  </svg>
);

const Briefcase = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
    <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
  </svg>
);

const Users = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
    <circle cx="9" cy="7" r="4"></circle>
    <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
  </svg>
);

const Scale = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 16l3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1z"></path>
    <path d="M2 16l3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1z"></path>
    <path d="M7 21h10"></path>
    <path d="M12 3v18"></path>
    <path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"></path>
  </svg>
);

const Scales = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 16l3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1z"></path>
    <path d="M2 16l3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1z"></path>
    <path d="M7 21h10"></path>
    <path d="M12 3v18"></path>
    <path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"></path>
  </svg>
);

const Heart = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
  </svg>
);

const Scissors = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="6" cy="6" r="3"></circle>
    <circle cx="6" cy="18" r="3"></circle>
    <line x1="20" y1="4" x2="8.12" y2="15.88"></line>
    <line x1="14.47" y1="14.48" x2="20" y2="20"></line>
    <line x1="8.12" y1="8.12" x2="12" y2="12"></line>
  </svg>
);

const Award = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="8" r="7"></circle>
    <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline>
  </svg>
);

const Shield = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
  </svg>
);

const Gavel = ({ className, size = 24 }) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14.5 2.5l5 5-1.5 1.5-5-5 1.5-1.5z"></path>
    <path d="M8.5 8.5l5 5-1.5 1.5-5-5 1.5-1.5z"></path>
    <path d="M3 21l4-4"></path>
    <path d="M21 11l-8 8-4-4 8-8 4 4z"></path>
  </svg>
);

// Default social icons object (AI sometimes references this)
const defaultSocialIcons = {
  facebook: Facebook,
  twitter: Twitter,
  instagram: Instagram,
  linkedin: Linkedin
};
'''

    def _clean_component_for_embedding(self, code: str, component_name: str) -> str:
        """
        Clean a library component for embedding.

        We DON'T modify the component logic - just:
        - Remove import statements (CDN provides React)
        - Remove export statements (we'll export App)
        - Ensure component name is consistent
        - RENAME the component to the expected name
        """
        if not code or not code.strip():
            # Empty component - generate a placeholder
            logger.warning(f"[MODULAR] Empty component code for {component_name}, using placeholder")
            return f'''const {component_name} = () => (
  <div className="p-8 text-center text-gray-500">
    {component_name} Component
  </div>
);'''

        # Remove import statements LINE BY LINE (not DOTALL - that causes corruption!)
        # Pattern 1: import { x, y } from 'module'; (standard ES6 import)
        # Pattern 2: import x from 'module'; (default import)
        # Pattern 3: import 'module'; (side-effect import)
        # CRITICAL: Use MULTILINE, not DOTALL - DOTALL causes catastrophic regex matching
        code = re.sub(r'^import\s+.*?from\s+[\'"][^"\']+[\'"];?\s*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'^import\s+[\'"][^"\']+[\'"];?\s*$', '', code, flags=re.MULTILINE)

        # CRITICAL FIX: Detect and rename component to expected name
        # This fixes "Footer is not defined" errors when library component is named differently
        actual_name = self._extract_component_name(code)
        if actual_name and actual_name != component_name:
            logger.info(f"[MODULAR] Renaming component: {actual_name} -> {component_name}")
            # Replace const/function declaration
            # Handle TypeScript type annotations: const X: Type = ... OR const X = ...
            code = re.sub(rf'\bconst\s+{re.escape(actual_name)}\s*(?::[^=]+)?\s*=', f'const {component_name} =', code)
            code = re.sub(rf'\bfunction\s+{re.escape(actual_name)}\s*\(', f'function {component_name}(', code)
            # Also update export default if present (before removing it)
            code = re.sub(rf'export\s+default\s+{re.escape(actual_name)}', f'export default {component_name}', code)

        # Remove export default at end
        code = re.sub(r'\n?export\s+default\s+\w+;\s*$', '', code)

        # Remove export keyword from declarations (keep the rest)
        code = re.sub(r'^export\s+(?=const|function|class)', '', code, flags=re.MULTILINE)

        # CRITICAL: Strip TypeScript-specific syntax that Babel can't handle
        # Remove 'as TypeName' casts (e.g., {} as FormValues -> {})
        code = re.sub(r'\s+as\s+[A-Z][a-zA-Z0-9<>\[\],\s]*(?=[)\],;\n])', '', code)
        # Remove type parameters from function calls (e.g., useState<Type>() -> useState())
        code = re.sub(r'<[A-Z][a-zA-Z0-9<>\[\],\s|]*>(?=\()', '', code)
        # Remove standalone type declarations (type X = ...)
        code = re.sub(r'^type\s+\w+\s*=\s*[^;]+;\s*$', '', code, flags=re.MULTILINE)
        # Remove interface declarations
        code = re.sub(r'^interface\s+\w+\s*\{[^}]*\}\s*$', '', code, flags=re.MULTILINE)

        # CRITICAL: Convert destructured React hooks to React.X prefix
        # Browser CDN deployment provides React as a global, not a module
        # So useState(...) must become React.useState(...)
        # Only convert standalone hook calls, not React.useState (already prefixed)
        code = re.sub(r'(?<![.\w])useState\(', 'React.useState(', code)
        code = re.sub(r'(?<![.\w])useEffect\(', 'React.useEffect(', code)
        code = re.sub(r'(?<![.\w])useRef\(', 'React.useRef(', code)
        code = re.sub(r'(?<![.\w])useMemo\(', 'React.useMemo(', code)
        code = re.sub(r'(?<![.\w])useCallback\(', 'React.useCallback(', code)
        code = re.sub(r'(?<![.\w])useContext\(', 'React.useContext(', code)
        code = re.sub(r'(?<![.\w])useReducer\(', 'React.useReducer(', code)

        # CRITICAL: Prefix local data variables with component name to avoid collisions
        # When multiple components define "const defaultSections = [...]", they clash
        # when combined into a single file. Prefix them to make unique.
        collision_prone_vars = ['defaultSections', 'defaultItems', 'sampleData', 'sampleColumns',
                                'mockData', 'defaultLinks', 'defaultNavItems', 'defaultFooterLinks',
                                'defaultSocialIcons', 'socialIcons', 'defaultServices', 'defaultTestimonials']
        for var_name in collision_prone_vars:
            # Check if this variable is defined in this component
            pattern = rf'\bconst\s+{var_name}\s*='
            if re.search(pattern, code):
                # Rename variable and all its usages
                new_name = f'{component_name}_{var_name}'
                # Rename definition
                code = re.sub(pattern, f'const {new_name} =', code)
                # Rename usages (not in strings or comments)
                # Use word boundary to avoid partial matches
                code = re.sub(rf'\b{var_name}\b', new_name, code)
                logger.debug(f"[MODULAR] Renamed {var_name} -> {new_name} in {component_name}")

        return code.strip()

    def _extract_component_name(self, code: str) -> Optional[str]:
        """
        Extract the actual component name from code.

        IMPORTANT: Prioritize the EXPORTED component name, not internal helpers.
        A library component may have multiple internal components (e.g., ReusableForm)
        but we only care about the one that's exported.

        Looks for patterns like:
        - export default ComponentName
        - const ComponentName = () =>
        - const ComponentName: React.FC = () =>
        - function ComponentName()
        """
        # Pattern 1: export default ComponentName (HIGHEST PRIORITY)
        # This is the component that will be used, so it's what we need to rename
        match = re.search(r'export\s+default\s+([A-Z][a-zA-Z0-9]*)\s*;?\s*$', code, re.MULTILINE)
        if match:
            return match.group(1)

        # Pattern 2: const ComponentName: Type = ( (TypeScript with type annotation)
        # This catches: const ReusableForm: React.FC<Props> = ({...}) => {
        match = re.search(r'const\s+([A-Z][a-zA-Z0-9]*)\s*:\s*(?:React\.)?FC[^=]*=', code)
        if match:
            return match.group(1)

        # Pattern 3: const ComponentName = ( (plain arrow function)
        match = re.search(r'const\s+([A-Z][a-zA-Z0-9]*)\s*=\s*\([^)]*\)\s*=>', code)
        if match:
            return match.group(1)

        # Pattern 4: function ComponentName(
        match = re.search(r'function\s+([A-Z][a-zA-Z0-9]*)\s*\(', code)
        if match:
            return match.group(1)

        return None
    
    def _generate_app_jsx_imports_only(self, component_files: List[ComponentFile]) -> str:
        """Generate App.jsx with imports (for build-based deploys)."""
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

        filename = f"{component_name}.jsx"

        # Strip TypeScript annotations (library was built with TS, now use plain JS)
        code = strip_typescript_annotations(code)

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

        If LayoutApp component is available from library, use it.
        Otherwise, generate inline layout.
        """
        # Separate by role
        layout_components = [c for c in component_files if c.component_type == 'layout']
        nav_components = [c for c in component_files if c.component_type in ('navigation', 'navbar', 'header', 'sidebar', 'menu')]
        footer_components = [c for c in component_files if c.component_type == 'footer']
        view_components = [c for c in component_files if c.component_type not in ('navigation', 'navbar', 'header', 'sidebar', 'menu', 'footer', 'layout')]

        # NEVER use library LayoutApp - it has internal state that ignores onNavigate props
        # Always use inline layout with proper navigation
        has_layout_app = False
        
        # Determine views
        views = []
        for comp in view_components:
            view_id = comp.component_type
            if view_id in ('hero', 'landing', 'home'):
                view_id = 'home'
            views.append((view_id, comp.component_name))
        
        # Always include settings
        has_settings = any(v[0] == 'settings' for v in views)

        # Default view - prefer 'home' or 'hero' if available
        view_ids_set = {v[0] for v in views}
        if 'home' in view_ids_set:
            default_view = 'home'
        elif 'hero' in view_ids_set:
            default_view = 'home'  # hero maps to 'home' in the nav
        elif views:
            default_view = views[0][0]
        else:
            default_view = 'home'

        # Navigation JSX
        # CRITICAL: Always use inline navigation that supports view switching
        # Library Navigation components use static href links, not onNavigate callbacks
        # So we generate functional inline nav for SPA-style view switching

        # Build view names for navigation
        view_ids = [v[0] for v in views]
        if not has_settings:
            view_ids.append('settings')

        # Pretty names for navigation
        view_labels = {
            'home': 'Home',
            'hero': 'Home',
            'services': 'Services',
            'about': 'About',
            'contact': 'Contact',
            'testimonials': 'Testimonials',
            'pricing': 'Pricing',
            'gallery': 'Gallery',
            'form': 'Contact',
            'card': 'Services',
            'list': 'Listings',
            'settings': 'Settings',
        }

        # Generate nav items with beautiful styling
        nav_buttons = []
        for view_id in view_ids:
            label = view_labels.get(view_id, view_id.capitalize())
            nav_buttons.append(
                f'''<button
              key="{view_id}"
              onClick={{() => setCurrentView("{view_id}")}}
              className={{currentView === "{view_id}"
                ? "text-white font-semibold px-4 py-2 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 shadow-lg shadow-blue-500/30 transition-all duration-300"
                : "text-gray-300 hover:text-white px-4 py-2 rounded-full hover:bg-white/10 transition-all duration-300"
              }}
            >
              {label}
            </button>'''
            )

        # Join nav buttons outside f-string (Python 3.11 doesn't allow backslash in f-strings)
        nav_buttons_joined = "\n              ".join(nav_buttons)

        # Extract business name from prompt
        business_name = self._extract_business_name(prompt)

        nav_jsx = f'''<header className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 shadow-2xl sticky top-0 z-50">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            <div className="flex-shrink-0">
              <span className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400">{business_name}</span>
            </div>
            <div className="hidden md:flex items-center space-x-8">
              {nav_buttons_joined}
            </div>
            <div className="md:hidden">
              <button
                onClick={{() => setCurrentView("home")}}
                className="text-gray-300 hover:text-white p-2 transition-colors duration-200"
              >
                <Menu size={{24}} />
              </button>
            </div>
          </div>
        </nav>
      </header>'''
        
        # View switching JSX - pass default props based on component type
        view_jsx_parts = []
        for view_id, comp_name in views:
            # Some components need default props to render properly
            default_props = self._get_default_props_for_component(view_id)
            view_jsx_parts.append(f'{{currentView === "{view_id}" && <{comp_name} {default_props}/>}}')
        
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
        # Use LayoutApp component if available, otherwise inline layout
        if has_layout_app:
            # Use library LayoutApp component
            app_code = f'''
function App() {{
  {state_declarations}
{data_effect}
  return (
    <LayoutApp
      currentView={{currentView}}
      onNavigate={{setCurrentView}}
      brandName="{business_name}"
    >
      {view_jsx}
      {footer_jsx}
    </LayoutApp>
  );
}}'''
        else:
            # Use inline layout (fallback) with beautiful styling
            app_code = f'''
function App() {{
  {state_declarations}
{data_effect}
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100">
      {nav_jsx}

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="space-y-16">
          {view_jsx}
        </div>
      </main>

      {footer_jsx}
    </div>
  );
}}'''

        return app_code

    def _get_default_props_for_component(self, component_type: str) -> str:
        """
        Return default props for components based on the BUSINESS TYPE.

        CRITICAL: These props must match the user's business, not hardcoded dog walking.
        The business context is stored in self._current_prompt.
        """
        # Use stored prompt to determine business type
        prompt = getattr(self, '_current_prompt', '').lower()

        # Detect business type from prompt
        if 'restaurant' in prompt or 'cafe' in prompt or 'bakery' in prompt or 'food' in prompt:
            biz_type = 'food'
        elif 'law' in prompt or 'attorney' in prompt or 'legal' in prompt:
            biz_type = 'legal'
        elif 'real estate' in prompt or 'property' in prompt or 'realtor' in prompt:
            biz_type = 'realestate'
        elif 'fitness' in prompt or 'gym' in prompt or 'yoga' in prompt:
            biz_type = 'fitness'
        elif 'photography' in prompt or 'photo' in prompt or 'camera' in prompt:
            biz_type = 'photo'
        elif 'dog' in prompt or 'pet' in prompt or 'walk' in prompt:
            biz_type = 'pet'
        else:
            biz_type = 'generic'

        # Business-specific content
        content = {
            'food': {
                'card': 'title="Our Menu" subtitle="Freshly Made Daily" description="Discover our delicious offerings crafted with the finest ingredients."',
                'list': '''items={[
                    { id: 1, title: "Appetizers", description: "Start your meal right", price: "From $8" },
                    { id: 2, title: "Main Courses", description: "Signature dishes", price: "From $18" },
                    { id: 3, title: "Desserts", description: "Sweet finishes", price: "From $6" }
                ]}''',
                'form': 'title="Make a Reservation" subtitle="Book your table today"',
            },
            'legal': {
                'card': 'title="Practice Areas" subtitle="Expert Legal Services" description="Dedicated representation for your legal needs."',
                'list': '''items={[
                    { id: 1, title: "Personal Injury", description: "Fighting for your rights", price: "Free Consultation" },
                    { id: 2, title: "Family Law", description: "Protecting your family", price: "Free Consultation" },
                    { id: 3, title: "Business Law", description: "Corporate expertise", price: "Free Consultation" }
                ]}''',
                'form': 'title="Free Case Evaluation" subtitle="Get expert legal advice"',
            },
            'realestate': {
                'card': 'title="Featured Properties" subtitle="Find Your Dream Home" description="Discover exceptional properties in prime locations."',
                'list': '''items={[
                    { id: 1, title: "Luxury Homes", description: "Premium properties", price: "From $500K" },
                    { id: 2, title: "Family Homes", description: "Perfect for families", price: "From $300K" },
                    { id: 3, title: "Condos", description: "Modern living", price: "From $200K" }
                ]}''',
                'form': 'title="Schedule a Viewing" subtitle="See your future home today"',
            },
            'fitness': {
                'card': 'title="Our Classes" subtitle="Transform Your Body" description="Expert-led fitness programs for all levels."',
                'list': '''items={[
                    { id: 1, title: "HIIT Training", description: "High intensity workouts", price: "$25/class" },
                    { id: 2, title: "Yoga", description: "Mind and body wellness", price: "$20/class" },
                    { id: 3, title: "Strength Training", description: "Build muscle", price: "$30/class" }
                ]}''',
                'form': 'title="Start Your Journey" subtitle="Sign up for a free trial"',
            },
            'photo': {
                'card': 'title="Portfolio" subtitle="Capturing Moments" description="Professional photography for life\'s special occasions."',
                'list': '''items={[
                    { id: 1, title: "Weddings", description: "Your special day", price: "From $2000" },
                    { id: 2, title: "Portraits", description: "Professional headshots", price: "From $200" },
                    { id: 3, title: "Events", description: "Corporate and private", price: "From $500" }
                ]}''',
                'form': 'title="Book a Session" subtitle="Let\'s create something beautiful"',
            },
            'pet': {
                'card': 'title="Our Services" subtitle="Quality Care for Your Pets" description="Professional pet care services tailored to your needs."',
                'list': '''items={[
                    { id: 1, title: "30 Minute Walk", description: "Quick exercise", price: "$20" },
                    { id: 2, title: "1 Hour Walk", description: "Extended adventure", price: "$35" },
                    { id: 3, title: "Pet Sitting", description: "Overnight care", price: "$50" }
                ]}''',
                'form': 'title="Book a Walk" subtitle="Schedule your pet\'s next adventure"',
            },
            'generic': {
                'card': 'title="Our Services" subtitle="Excellence in Everything We Do" description="Professional services tailored to your needs."',
                'list': '''items={[
                    { id: 1, title: "Service 1", description: "Quality service", price: "Contact us" },
                    { id: 2, title: "Service 2", description: "Expert solutions", price: "Contact us" },
                    { id: 3, title: "Service 3", description: "Personalized attention", price: "Contact us" }
                ]}''',
                'form': 'title="Contact Us" subtitle="Get in touch today"',
            },
        }

        biz_content = content.get(biz_type, content['generic'])
        return biz_content.get(component_type, '')

    def _extract_business_name(self, prompt: str) -> str:
        """
        Extract business name from the prompt.

        Looks for patterns like:
        - "called 'Business Name'"
        - "named 'Business Name'"
        - "for Business Name"
        - Or generates a name from the business type
        """
        import re

        # Try to find explicit name in quotes
        match = re.search(r"(?:called|named)\s+['\"]([^'\"]+)['\"]", prompt, re.IGNORECASE)
        if match:
            return match.group(1)

        # Try "for X business/company/studio/gallery"
        match = re.search(r"for\s+(?:a\s+)?([A-Z][a-zA-Z\s]+?)(?:\s+business|\s+company|\s+studio|\s+gallery|\s+broker|\s+artist|\.|,)", prompt)
        if match:
            name = match.group(1).strip()
            if len(name) > 3 and len(name) < 50:
                return name

        # Extract business type and create a name
        if 'real estate' in prompt.lower():
            return 'Premier Properties'
        if 'nft' in prompt.lower() or 'digital art' in prompt.lower():
            return 'Digital Canvas'
        if 'dog walk' in prompt.lower():
            return 'Happy Paws'
        if 'restaurant' in prompt.lower():
            return 'Fine Dining'
        if 'fitness' in prompt.lower() or 'gym' in prompt.lower():
            return 'Peak Fitness'
        if 'law' in prompt.lower() or 'attorney' in prompt.lower():
            return 'Legal Partners'

        # Default
        return 'My Business'

    def _generate_app_jsx(
        self,
        component_files: List[ComponentFile],
        prompt: str,
        needs_real_data: bool
    ) -> str:
        """Generate the main App.jsx that wires components (legacy, for reference)."""
        
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

        # Assemble App.jsx
        app_jsx = f"""{chr(10).join(imports)}

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

        return app_jsx


def compose_modular(
    components: Dict[str, str],
    prompt: str = "",
    needs_real_data: bool = False
) -> Tuple[Dict[str, str], str]:
    """
    Main entry point for modular composition.

    Returns (files_dict, app_jsx_code).
    """
    composer = ModularComposer()
    return composer.compose(components, prompt, needs_real_data)
