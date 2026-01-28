"""
Local Preview Module

Runs generated code locally and verifies it works BEFORE deployment.

Flow:
1. Write code to temp directory with HTML template
2. Start local HTTP server
3. Use Playwright to screenshot and check for JS errors
4. Return success/failure with details
5. Clean up

This catches runtime errors that esbuild syntax checking misses.
"""

import os
import tempfile
import subprocess
import time
import logging
import shutil
from typing import Tuple, List, Optional
from dataclasses import dataclass
import threading
import http.server
import socketserver

logger = logging.getLogger(__name__)

# Port range for local preview servers
PREVIEW_PORT_START = 8765
PREVIEW_PORT_END = 8799


@dataclass
class PreviewResult:
    """Result of local preview verification."""
    success: bool
    screenshot_path: Optional[str] = None
    js_errors: List[str] = None
    console_logs: List[str] = None
    page_title: Optional[str] = None
    page_content: Optional[str] = None  # First 500 chars of body text
    error: Optional[str] = None

    def __post_init__(self):
        if self.js_errors is None:
            self.js_errors = []
        if self.console_logs is None:
            self.console_logs = []


class LocalPreviewServer:
    """
    Simple HTTP server for local preview.

    Uses Python's built-in http.server to serve static files.
    Runs in a background thread so it doesn't block.
    """

    def __init__(self, directory: str, port: int = None):
        self.directory = directory
        self.port = port or self._find_available_port()
        self.server = None
        self.thread = None

    def _find_available_port(self) -> int:
        """Find an available port in the preview range."""
        import socket
        for port in range(PREVIEW_PORT_START, PREVIEW_PORT_END):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                continue
        raise RuntimeError("No available ports for preview server")

    def start(self) -> str:
        """Start the server and return the URL."""
        os.chdir(self.directory)

        handler = http.server.SimpleHTTPRequestHandler
        self.server = socketserver.TCPServer(("", self.port), handler)

        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

        url = f"http://localhost:{self.port}"
        logger.info(f"[LOCAL PREVIEW] Server started at {url}")
        return url

    def stop(self):
        """Stop the server."""
        if self.server:
            self.server.shutdown()
            logger.info("[LOCAL PREVIEW] Server stopped")


def create_preview_html(app_code: str, project_name: str = "Preview") -> str:
    """
    Create the HTML file for local preview.

    Uses the same CDN-based React setup as Vercel deployment.
    """
    # CRITICAL: Strip ES module syntax that doesn't work in browser Babel
    # Babel in-browser can't handle 'export default' - it's not a bundler
    import re
    app_code = re.sub(r'^\s*export\s+default\s+\w+\s*;?\s*$', '', app_code, flags=re.MULTILINE)
    app_code = re.sub(r'^\s*import\s+React.*$', '', app_code, flags=re.MULTILINE)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{project_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js" crossorigin></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js" crossorigin></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script>
        // Mock Faibric globals for preview
        window.FAIBRIC_PROJECT_ID = "preview";
        window.FAIBRIC_APP_ID = 999;
    </script>
    <style>
        body {{ margin: 0; font-family: system-ui, -apple-system, sans-serif; }}
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="text/babel" data-presets="react,typescript">
{app_code}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(React.createElement(App));
    </script>
</body>
</html>'''


def run_playwright_check(url: str, screenshot_path: str, timeout: int = 30) -> PreviewResult:
    """
    Use Playwright to load the page, take screenshot, and check for errors.

    This is the core verification step.
    """
    try:
        # Try to import playwright
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("[LOCAL PREVIEW] Playwright not installed, skipping browser check")
        return PreviewResult(
            success=True,  # Pass through if playwright not available
            error="Playwright not installed - skipping browser verification"
        )

    js_errors = []
    console_logs = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1280, 'height': 900})

            # Collect console messages
            def handle_console(msg):
                if msg.type == 'error':
                    js_errors.append(msg.text)
                else:
                    console_logs.append(f"[{msg.type}] {msg.text}")

            page.on('console', handle_console)

            # Collect page errors (uncaught exceptions)
            def handle_pageerror(error):
                js_errors.append(str(error))

            page.on('pageerror', handle_pageerror)

            # Navigate to the page
            try:
                page.goto(url, wait_until='networkidle', timeout=timeout * 1000)
            except Exception as nav_error:
                browser.close()
                return PreviewResult(
                    success=False,
                    js_errors=js_errors,
                    error=f"Navigation failed: {nav_error}"
                )

            # Wait a bit for any animations/renders
            page.wait_for_timeout(2000)

            # Take screenshot
            page.screenshot(path=screenshot_path, full_page=True)

            # Get page info
            title = page.title()
            body_text = page.evaluate('() => document.body.innerText')

            browser.close()

            # Check for blank page
            is_blank = len(body_text.strip()) < 50

            if js_errors:
                return PreviewResult(
                    success=False,
                    screenshot_path=screenshot_path,
                    js_errors=js_errors,
                    console_logs=console_logs,
                    page_title=title,
                    page_content=body_text[:500] if body_text else None,
                    error=f"JavaScript errors detected: {js_errors[0][:100]}"
                )

            if is_blank:
                return PreviewResult(
                    success=False,
                    screenshot_path=screenshot_path,
                    js_errors=js_errors,
                    console_logs=console_logs,
                    page_title=title,
                    page_content=body_text[:500] if body_text else None,
                    error="Page appears blank (less than 50 characters of content)"
                )

            return PreviewResult(
                success=True,
                screenshot_path=screenshot_path,
                js_errors=[],
                console_logs=console_logs,
                page_title=title,
                page_content=body_text[:500] if body_text else None
            )

    except Exception as e:
        logger.error(f"[LOCAL PREVIEW] Playwright error: {e}")
        return PreviewResult(
            success=False,
            js_errors=js_errors,
            error=f"Playwright error: {e}"
        )


def verify_code_locally(
    app_code: str,
    project_name: str = "Preview",
    timeout: int = 30
) -> PreviewResult:
    """
    Main entry point: Verify generated code works locally before deployment.

    Args:
        app_code: The generated React/JSX code
        project_name: Name for the preview (used in title)
        timeout: Max seconds to wait for page load

    Returns:
        PreviewResult with success status, screenshot, and any errors
    """
    logger.info("[LOCAL PREVIEW] Starting local verification...")

    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="faibric_preview_")
    screenshot_path = os.path.join(temp_dir, "preview.png")

    server = None
    original_cwd = os.getcwd()

    try:
        # Write HTML file
        html_content = create_preview_html(app_code, project_name)
        html_path = os.path.join(temp_dir, "index.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"[LOCAL PREVIEW] Created preview files in {temp_dir}")

        # Start server
        server = LocalPreviewServer(temp_dir)
        url = server.start()

        # Give server a moment to start
        time.sleep(0.5)

        # Run Playwright check
        result = run_playwright_check(url, screenshot_path, timeout)

        # Copy screenshot to a persistent location if successful
        if result.screenshot_path and os.path.exists(result.screenshot_path):
            persistent_path = f"/tmp/faibric_preview_{int(time.time())}.png"
            shutil.copy(result.screenshot_path, persistent_path)
            result.screenshot_path = persistent_path

        return result

    except Exception as e:
        logger.error(f"[LOCAL PREVIEW] Error: {e}")
        return PreviewResult(
            success=False,
            error=f"Preview failed: {e}"
        )

    finally:
        # Restore original working directory
        os.chdir(original_cwd)

        # Stop server
        if server:
            server.stop()

        # Clean up temp directory (but keep screenshot)
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def preview_and_fix(
    app_code: str,
    project_name: str = "Preview",
    max_retries: int = 3
) -> Tuple[bool, str, PreviewResult]:
    """
    Verify code locally and attempt AI fixes if errors found.

    Args:
        app_code: The generated code
        project_name: Name for preview
        max_retries: Max AI fix attempts

    Returns:
        Tuple of (success, final_code, preview_result)
    """
    current_code = app_code

    for attempt in range(max_retries):
        logger.info(f"[LOCAL PREVIEW] Verification attempt {attempt + 1}/{max_retries}")

        result = verify_code_locally(current_code, project_name)

        if result.success:
            logger.info("[LOCAL PREVIEW] Verification PASSED")
            return True, current_code, result

        logger.warning(f"[LOCAL PREVIEW] Verification FAILED: {result.error}")

        if attempt < max_retries - 1:
            # Try AI fix
            try:
                from .code_fixer import fix_code_with_ai

                error_msg = result.error
                if result.js_errors:
                    error_msg = f"{error_msg}\nJS Errors: {'; '.join(result.js_errors[:3])}"

                success, fixed_code = fix_code_with_ai(current_code, error_msg, attempt + 1)

                if success and fixed_code and fixed_code != current_code:
                    current_code = fixed_code
                    logger.info(f"[LOCAL PREVIEW] AI fix applied, retrying...")
                else:
                    logger.warning("[LOCAL PREVIEW] AI couldn't fix the code")

            except Exception as e:
                logger.error(f"[LOCAL PREVIEW] AI fix error: {e}")

    # All retries exhausted
    logger.error(f"[LOCAL PREVIEW] Verification failed after {max_retries} attempts")
    return False, current_code, result


# Quick test function
if __name__ == "__main__":
    test_code = '''
const App = () => {
    return (
        <div className="min-h-screen bg-gray-100 p-8">
            <h1 className="text-3xl font-bold text-center">Hello World</h1>
            <p className="text-center mt-4">This is a test preview.</p>
        </div>
    );
};

export default App;
'''

    result = verify_code_locally(test_code, "Test Preview")
    print(f"Success: {result.success}")
    print(f"Screenshot: {result.screenshot_path}")
    print(f"Errors: {result.js_errors}")
    print(f"Content: {result.page_content}")
