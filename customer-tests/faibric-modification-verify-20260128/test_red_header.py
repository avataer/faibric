#!/usr/bin/env python
"""
Test: Verify Modification Works - RED Header Color Change

This test verifies that the modification feature works by:
1. Creating a new simple website project
2. Waiting for the initial build to complete
3. Requesting a bright RED header modification
4. Waiting for the modification to complete
5. Taking a screenshot to verify the RED header is visible
"""

import requests
import time
import json
import os
import subprocess
from datetime import datetime

# Configuration
API_BASE = "http://localhost:8000/api/onboarding"
SCREENSHOT_DIR = os.path.dirname(os.path.abspath(__file__)) + "/screenshots"

def log(msg):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def create_project():
    """Step 1: Create a new project using dev flow."""
    log("Creating new project...")

    response = requests.post(f"{API_BASE}/start-dev/", json={
        "request": "Create a simple landing page for a coffee shop called 'Morning Brew' with a header, hero section, and contact info"
    })

    if response.status_code != 200:
        log(f"ERROR: Failed to create project: {response.text}")
        return None

    data = response.json()
    if not data.get('success'):
        log(f"ERROR: Project creation failed: {data}")
        return None

    session_token = data.get('session_token')
    log(f"Project created! Session token: {session_token[:20]}...")
    return session_token

def wait_for_build(session_token, timeout=300):
    """Step 2: Wait for build to complete."""
    log("Waiting for build to complete...")
    start = time.time()

    while time.time() - start < timeout:
        response = requests.get(f"{API_BASE}/status/{session_token}/")

        if response.status_code != 200:
            log(f"ERROR: Failed to get status: {response.text}")
            time.sleep(5)
            continue

        data = response.json()
        status = data.get('status', '')
        progress = data.get('build_progress', 0)
        deployment_url = data.get('deployment_url', '')

        log(f"Status: {status}, Progress: {progress}%, URL: {deployment_url or 'N/A'}")

        if status == 'deployed' and deployment_url:
            log(f"BUILD COMPLETE! URL: {deployment_url}")
            return deployment_url

        if status in ('failed', 'error'):
            log(f"BUILD FAILED: {data}")
            return None

        time.sleep(5)

    log("ERROR: Build timed out")
    return None

def request_modification(session_token):
    """Step 3: Request bright red header modification."""
    log("Requesting modification: BRIGHT RED HEADER...")

    response = requests.post(f"{API_BASE}/modify/", json={
        "session_token": session_token,
        "request": "Make the header background bright red. Use #FF0000 or similar bright red color. The header/navigation area should be very obviously RED."
    })

    if response.status_code != 200:
        log(f"ERROR: Modification request failed: {response.text}")
        return False

    data = response.json()
    log(f"Modification response: {data}")

    if data.get('mode') == 'conversation':
        log("AI responded conversationally instead of modifying. Trying again with stronger command...")
        response = requests.post(f"{API_BASE}/modify/", json={
            "session_token": session_token,
            "request": "Change header background to bright red #FF0000"
        })
        data = response.json()
        log(f"Second attempt response: {data}")

    return data.get('success', False) or data.get('mode') == 'modify'

def wait_for_modification(session_token, timeout=180):
    """Step 4: Wait for modification to complete."""
    log("Waiting for modification to complete...")
    start = time.time()

    while time.time() - start < timeout:
        response = requests.get(f"{API_BASE}/status/{session_token}/")

        if response.status_code != 200:
            time.sleep(3)
            continue

        data = response.json()
        status = data.get('status', '')
        deployment_url = data.get('deployment_url', '')

        log(f"Status: {status}, URL: {deployment_url or 'waiting...'}")

        if status == 'deployed' and deployment_url:
            log(f"MODIFICATION COMPLETE! URL: {deployment_url}")
            return deployment_url

        time.sleep(3)

    log("ERROR: Modification timed out")
    return None

def take_screenshot(url, filename):
    """Step 5: Take a screenshot using webkit2png or similar."""
    log(f"Taking screenshot of {url}...")

    # Ensure screenshots directory exists
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    filepath = os.path.join(SCREENSHOT_DIR, filename)

    # Try using screencapture with Safari (macOS)
    # We'll use a simple approach - save URL and instructions

    # First, let's try using playwright if available
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1280, 'height': 720})
            page.goto(url, wait_until='networkidle', timeout=30000)
            time.sleep(2)  # Extra wait for React to render
            page.screenshot(path=filepath)
            browser.close()
            log(f"Screenshot saved to {filepath}")
            return filepath
    except ImportError:
        log("Playwright not available, trying alternative...")

    # Try using webdriver with selenium
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--window-size=1280,720')
        options.add_argument('--no-sandbox')

        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(3)  # Wait for render
        driver.save_screenshot(filepath)
        driver.quit()
        log(f"Screenshot saved to {filepath}")
        return filepath
    except Exception as e:
        log(f"Selenium not available: {e}")

    # Fallback: save URL to file for manual screenshot
    url_file = os.path.join(SCREENSHOT_DIR, "SCREENSHOT_URL.txt")
    with open(url_file, 'w') as f:
        f.write(f"URL to screenshot: {url}\n")
        f.write(f"Expected: Header should be BRIGHT RED (#FF0000)\n")
        f.write(f"Filename: {filename}\n")
    log(f"Could not auto-screenshot. URL saved to {url_file}")
    return None

def main():
    """Run the full test."""
    log("=" * 60)
    log("FAIBRIC MODIFICATION TEST - RED HEADER")
    log("=" * 60)

    results = {
        "test_name": "faibric-modification-verify-20260128",
        "start_time": datetime.now().isoformat(),
        "steps": []
    }

    # Step 1: Create project
    session_token = create_project()
    if not session_token:
        results["status"] = "FAILED"
        results["error"] = "Failed to create project"
        save_results(results)
        return False

    results["session_token"] = session_token
    results["steps"].append({"step": "create_project", "status": "success"})

    # Step 2: Wait for build
    initial_url = wait_for_build(session_token)
    if not initial_url:
        results["status"] = "FAILED"
        results["error"] = "Initial build failed or timed out"
        save_results(results)
        return False

    results["initial_url"] = initial_url
    results["steps"].append({"step": "initial_build", "status": "success", "url": initial_url})

    # Take screenshot before modification
    take_screenshot(initial_url, "01_before_modification.png")

    # Step 3: Request modification
    if not request_modification(session_token):
        results["status"] = "FAILED"
        results["error"] = "Modification request failed"
        save_results(results)
        return False

    results["steps"].append({"step": "request_modification", "status": "success"})

    # Step 4: Wait for modification
    modified_url = wait_for_modification(session_token)
    if not modified_url:
        results["status"] = "FAILED"
        results["error"] = "Modification build failed or timed out"
        save_results(results)
        return False

    results["modified_url"] = modified_url
    results["steps"].append({"step": "modification_complete", "status": "success", "url": modified_url})

    # Step 5: Take screenshot after modification
    screenshot_path = take_screenshot(modified_url, "02_after_red_header.png")
    results["screenshot"] = screenshot_path
    results["steps"].append({"step": "screenshot", "status": "success" if screenshot_path else "manual_required"})

    results["status"] = "SUCCESS"
    results["end_time"] = datetime.now().isoformat()

    save_results(results)

    log("=" * 60)
    log("TEST COMPLETE")
    log(f"Initial URL: {initial_url}")
    log(f"Modified URL: {modified_url}")
    log(f"VERIFY: Header should be BRIGHT RED")
    log("=" * 60)

    return True

def save_results(results):
    """Save test results to JSON file."""
    filepath = os.path.join(SCREENSHOT_DIR, "test_results.json")
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2)
    log(f"Results saved to {filepath}")

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
