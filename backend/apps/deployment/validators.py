"""
Code validation before deployment

Includes:
- Static validation (syntax checks)
- Local build validation (runs actual vite build)
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


class CodeValidationError(Exception):
    """Raised when code validation fails"""
    pass


class BuildValidationError(Exception):
    """Raised when local build fails"""
    pass


# Cache for node_modules to speed up repeated builds
_NODE_MODULES_CACHE = None


def get_or_create_node_modules_cache():
    """
    Get or create a cached node_modules directory.
    This speeds up local builds from ~30s to ~5s.
    """
    global _NODE_MODULES_CACHE

    cache_dir = Path(tempfile.gettempdir()) / "faibric_build_cache"
    node_modules = cache_dir / "node_modules"

    if node_modules.exists() and _NODE_MODULES_CACHE == str(node_modules):
        return cache_dir

    # Create cache if it doesn't exist
    if not cache_dir.exists():
        cache_dir.mkdir(parents=True)

        # Write package.json - Plain JavaScript (no TypeScript per Base44 lessons)
        package_json = {
            "name": "faibric-build-cache",
            "private": True,
            "version": "1.0.0",
            "type": "module",
            "scripts": {
                "build": "vite build"
            },
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "react-router-dom": "^6.20.0",
                "recharts": "^2.10.0",
                "lucide-react": "^0.294.0",
                "clsx": "^2.0.0",
                "date-fns": "^2.30.0",
                "@supabase/supabase-js": "^2.39.0"
            },
            "devDependencies": {
                "@vitejs/plugin-react": "^4.2.0",
                "vite": "^5.0.0",
                "tailwindcss": "^3.3.0",
                "postcss": "^8.4.0",
                "autoprefixer": "^10.4.0"
            }
        }

        with open(cache_dir / "package.json", "w") as f:
            json.dump(package_json, f, indent=2)

        # Install dependencies
        print("[BUILD] Installing dependencies for build cache...")
        result = subprocess.run(
            ["npm", "install", "--legacy-peer-deps"],
            cwd=cache_dir,
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode != 0:
            shutil.rmtree(cache_dir, ignore_errors=True)
            raise BuildValidationError(f"Failed to install dependencies: {result.stderr}")

        print("[BUILD] Build cache ready")

    _NODE_MODULES_CACHE = str(node_modules)
    return cache_dir


def validate_build_locally(code_dict: dict, project_name: str = "test-app") -> dict:
    """
    Run an actual vite build locally to validate the code compiles.

    This catches errors that static analysis misses:
    - Import errors
    - JSX syntax errors
    - Missing dependencies

    Returns: {"success": True} or {"success": False, "error": "...", "details": "..."}

    Typical time: ~5s with cached node_modules, ~30s first run
    """
    build_dir = None
    try:
        # Get cached node_modules
        cache_dir = get_or_create_node_modules_cache()

        # Create temp build directory
        build_dir = Path(tempfile.mkdtemp(prefix="faibric_build_"))

        # Copy cached node_modules (symlink for speed)
        cached_modules = cache_dir / "node_modules"
        if cached_modules.exists():
            os.symlink(cached_modules, build_dir / "node_modules")

        # Write package.json
        package_json = {
            "name": project_name.lower().replace(" ", "-"),
            "private": True,
            "version": "1.0.0",
            "type": "module",
            "scripts": {"build": "vite build"},
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "react-router-dom": "^6.20.0",
                "recharts": "^2.10.0",
                "lucide-react": "^0.294.0",
                "clsx": "^2.0.0",
                "date-fns": "^2.30.0",
                "@supabase/supabase-js": "^2.39.0"
            },
            "devDependencies": {
                "@vitejs/plugin-react": "^4.2.0",
                "vite": "^5.0.0",
                "tailwindcss": "^3.3.0",
                "postcss": "^8.4.0",
                "autoprefixer": "^10.4.0"
            }
        }
        with open(build_dir / "package.json", "w") as f:
            json.dump(package_json, f, indent=2)

        # Write vite.config.js (plain JavaScript)
        vite_config = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
"""
        with open(build_dir / "vite.config.js", "w") as f:
            f.write(vite_config)

        # Write tailwind.config.js
        tailwind_config = """/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
"""
        with open(build_dir / "tailwind.config.js", "w") as f:
            f.write(tailwind_config)

        # Write postcss.config.js
        postcss_config = """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
"""
        with open(build_dir / "postcss.config.js", "w") as f:
            f.write(postcss_config)

        # Write index.html
        index_html = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Build Test</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""
        with open(build_dir / "index.html", "w") as f:
            f.write(index_html)

        # Create src directory
        src_dir = build_dir / "src"
        src_dir.mkdir()

        # Write main.jsx (plain JavaScript)
        main_jsx = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""
        with open(src_dir / "main.jsx", "w") as f:
            f.write(main_jsx)

        # Write index.css
        index_css = """@tailwind base;
@tailwind components;
@tailwind utilities;
"""
        with open(src_dir / "index.css", "w") as f:
            f.write(index_css)

        # Write App.jsx (accept either App.jsx or App.tsx from code_dict)
        app_code = code_dict.get('App.jsx') or code_dict.get('App.tsx', '')
        if not app_code:
            return {"success": False, "error": "Missing App.jsx", "details": ""}
        with open(src_dir / "App.jsx", "w") as f:
            f.write(app_code)

        # Write components with .jsx extension
        components = code_dict.get('components', {})
        if components:
            comp_dir = src_dir / "components"
            comp_dir.mkdir()
            for comp_name, comp_code in components.items():
                # Strip any existing extension and use .jsx
                clean_name = comp_name.replace('.tsx', '').replace('.jsx', '').replace('.js', '')
                filename = f"{clean_name}.jsx"
                with open(comp_dir / filename, "w") as f:
                    f.write(comp_code)

        # Run vite build
        print(f"[BUILD] Running local build validation...")
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=build_dir,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            # Extract the actual error from vite output
            error_output = result.stderr + result.stdout

            # Parse common error patterns
            error_msg = "Build failed"
            if "SyntaxError" in error_output:
                error_msg = "Syntax error in code"
            elif "Cannot find module" in error_output:
                import re
                module_error = re.search(r"Cannot find module '([^']+)'", error_output)
                if module_error:
                    error_msg = f"Missing import: {module_error.group(1)}"
            elif "is not defined" in error_output:
                import re
                undef_error = re.search(r"'(\w+)' is not defined", error_output)
                if undef_error:
                    error_msg = f"Undefined: {undef_error.group(1)}"

            return {
                "success": False,
                "error": error_msg,
                "details": error_output[-2000:]  # Last 2000 chars of output
            }

        print("[BUILD] Local build passed")
        return {"success": True}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Build timed out (60s)", "details": ""}
    except Exception as e:
        return {"success": False, "error": str(e), "details": ""}
    finally:
        # Cleanup
        if build_dir and build_dir.exists():
            # Remove symlink first to avoid deleting cached node_modules
            node_modules_link = build_dir / "node_modules"
            if node_modules_link.is_symlink():
                node_modules_link.unlink()
            shutil.rmtree(build_dir, ignore_errors=True)


def validate_frontend_code(project):
    """
    Validate frontend code before deployment.

    Raises CodeValidationError if validation fails.
    Returns the parsed code dict if validation passes.
    """
    if not project.frontend_code:
        raise CodeValidationError("No frontend code found")

    # Parse the code
    try:
        if isinstance(project.frontend_code, str):
            try:
                code_dict = json.loads(project.frontend_code)
            except json.JSONDecodeError:
                import ast
                code_dict = ast.literal_eval(project.frontend_code)
        else:
            code_dict = project.frontend_code
    except Exception as e:
        raise CodeValidationError(f"Failed to parse frontend code: {str(e)}")

    # Check required keys
    if not isinstance(code_dict, dict):
        raise CodeValidationError("Frontend code must be a dictionary")

    # Accept either App.jsx or App.tsx (prefer .jsx)
    app_code = code_dict.get('App.jsx') or code_dict.get('App.tsx', '')
    if not app_code:
        raise CodeValidationError("Missing App.jsx in frontend code")

    # Validate App code
    validate_react_code(app_code, 'App.jsx')

    # Validate components
    components = code_dict.get('components', {})
    for comp_name, comp_code in components.items():
        validate_react_code(comp_code, comp_name)

    return code_dict


def validate_react_code(code: str, filename: str):
    """
    Basic validation of React/JSX code.

    Checks for common issues that would prevent compilation.
    """
    if not code or not code.strip():
        raise CodeValidationError(f"{filename}: Empty code")

    # Check for unclosed JSX tags (basic check)
    # Count opening and closing braces/brackets
    open_braces = code.count('{')
    close_braces = code.count('}')
    if abs(open_braces - close_braces) > 2:
        raise CodeValidationError(
            f"{filename}: Mismatched braces ({{ {open_braces}, }} {close_braces})"
        )

    open_parens = code.count('(')
    close_parens = code.count(')')
    if abs(open_parens - close_parens) > 2:
        raise CodeValidationError(
            f"{filename}: Mismatched parentheses (( {open_parens}, ) {close_parens})"
        )

    # Check for common syntax errors
    if '<<<' in code or '>>>' in code:
        raise CodeValidationError(
            f"{filename}: Contains merge conflict markers"
        )

    # Check for export (must have at least one export)
    if 'export' not in code:
        raise CodeValidationError(
            f"{filename}: Missing export statement"
        )

    # Check for basic React structure (function component or class)
    has_function = bool(re.search(r'(function\s+\w+|const\s+\w+\s*=)', code))
    has_class = bool(re.search(r'class\s+\w+', code))
    if not has_function and not has_class:
        raise CodeValidationError(
            f"{filename}: No function or class component found"
        )

    # Check for return statement with JSX
    if 'return' not in code:
        raise CodeValidationError(
            f"{filename}: Missing return statement"
        )

    return True
