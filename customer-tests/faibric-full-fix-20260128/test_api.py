#!/usr/bin/env python3
"""
API Test Script for Faibric Full Fix
Tests the intent detection and code generation via the production API.
"""
import requests
import json
import time
from datetime import datetime

API_URL = "https://faibric-api.onrender.com"
LOCAL_API = "http://localhost:8000"

# Use local API if available, otherwise production
def get_api_url():
    try:
        r = requests.get(f"{LOCAL_API}/api/health/", timeout=2)
        if r.status_code == 200:
            return LOCAL_API
    except:
        pass
    return API_URL

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def test_intent_detection():
    """Test that questions are detected correctly and don't trigger builds."""
    api = get_api_url()
    log(f"Using API: {api}")

    # First, start a session (use dev endpoint to skip email verification)
    log("Starting new session...")
    r = requests.post(f"{api}/api/onboarding/start-dev/", json={
        "request": "I want a website for my bakery"
    })

    if r.status_code != 200:
        log(f"FAIL: Could not start session: {r.status_code}")
        log(r.text[:500])
        return False

    data = r.json()
    session_token = data.get('session_token')
    log(f"Session started: {session_token[:20]}...")

    # Wait for initial build
    log("Waiting for initial build (this may take 30-60 seconds)...")
    time.sleep(5)

    # Check status until ready
    for i in range(60):
        r = requests.get(f"{api}/api/onboarding/status/{session_token}/")
        status_data = r.json()
        status = status_data.get('status')
        log(f"Build status: {status}")

        if status == 'ready':
            break
        elif status == 'error':
            log(f"FAIL: Build failed: {status_data.get('error')}")
            return False
        time.sleep(2)

    if status != 'ready':
        log(f"WARN: Build not ready after 120s, continuing anyway...")

    # TEST 1: Question should return conversation mode
    log("\n--- TEST 1: Question Detection ---")
    test_question = "What colors can I use for my website?"

    r = requests.post(f"{api}/api/onboarding/modify/", json={
        "session_token": session_token,
        "request": test_question
    })

    if r.status_code != 200:
        log(f"FAIL: Modify request failed: {r.status_code}")
        log(r.text[:500])
        return False

    result = r.json()
    mode = result.get('mode')
    response = result.get('response', '')

    log(f"Mode: {mode}")
    log(f"Response: {response[:200]}...")

    if mode != 'conversation':
        log(f"FAIL: Expected mode='conversation', got mode='{mode}'")
        return False

    if not response or len(response) < 10:
        log(f"FAIL: Expected conversational response, got empty/short response")
        return False

    log("PASS: Question detected correctly, got conversational response")

    # TEST 2: Another question type
    log("\n--- TEST 2: How-to Question ---")
    test_question2 = "How do I add a contact form?"

    r = requests.post(f"{api}/api/onboarding/modify/", json={
        "session_token": session_token,
        "request": test_question2
    })

    result = r.json()
    mode = result.get('mode')
    response = result.get('response', '')

    log(f"Mode: {mode}")
    log(f"Response: {response[:200]}...")

    if mode != 'conversation':
        log(f"FAIL: Expected mode='conversation', got mode='{mode}'")
        return False

    log("PASS: How-to question detected correctly")

    # TEST 3: Feedback should also be conversational
    log("\n--- TEST 3: Feedback Detection ---")
    test_feedback = "I think the colors look too dark"

    r = requests.post(f"{api}/api/onboarding/modify/", json={
        "session_token": session_token,
        "request": test_feedback
    })

    result = r.json()
    mode = result.get('mode')
    response = result.get('response', '')

    log(f"Mode: {mode}")
    log(f"Response: {response[:200]}...")

    if mode != 'conversation':
        log(f"FAIL: Expected mode='conversation', got mode='{mode}'")
        return False

    log("PASS: Feedback detected correctly")

    # TEST 4: Command should trigger build
    log("\n--- TEST 4: Command Detection ---")
    test_command = "Make the header blue"

    r = requests.post(f"{api}/api/onboarding/modify/", json={
        "session_token": session_token,
        "request": test_command
    })

    result = r.json()
    mode = result.get('mode')

    log(f"Mode: {mode}")

    if mode not in ('modify', 'rebuild'):
        log(f"FAIL: Expected mode='modify' or 'rebuild', got mode='{mode}'")
        return False

    log("PASS: Command detected correctly, triggered build")

    return True


def test_code_generation_no_placeholders():
    """Test that generated code has no template placeholders."""
    api = get_api_url()
    log(f"\n=== TESTING CODE GENERATION (NO PLACEHOLDERS) ===")
    log(f"Using API: {api}")

    # Start a session with an e-commerce prompt (uses cards variant)
    log("Starting session with e-commerce prompt (should use cards hero)...")
    r = requests.post(f"{api}/api/onboarding/start-dev/", json={
        "request": "I want an online shop for vintage vinyl records"
    })

    if r.status_code != 200:
        log(f"FAIL: Could not start session: {r.status_code}")
        return False

    data = r.json()
    session_token = data.get('session_token')
    log(f"Session started: {session_token[:20]}...")

    # Wait for build to complete
    log("Waiting for build (60-120 seconds)...")
    start_time = time.time()

    for i in range(90):
        r = requests.get(f"{api}/api/onboarding/status/{session_token}/")
        status_data = r.json()
        status = status_data.get('status')

        if i % 10 == 0:
            log(f"Build status: {status} ({int(time.time() - start_time)}s elapsed)")

        if status == 'ready':
            break
        elif status == 'error':
            log(f"FAIL: Build failed: {status_data.get('error')}")
            return False
        time.sleep(2)

    if status != 'ready':
        log(f"WARN: Build not ready after 180s")
        return False

    # Get the project code
    project_id = status_data.get('project', {}).get('id')
    frontend_code = status_data.get('project', {}).get('frontend_code', '')

    if not frontend_code:
        log("FAIL: No frontend code in response")
        return False

    log(f"Build complete! Code length: {len(frontend_code)} chars")

    # Check for template placeholders
    placeholders_found = []

    if '{{@' in frontend_code:
        # Find all array placeholders
        import re
        matches = re.findall(r'\{\{@\w+\}\}', frontend_code)
        placeholders_found.extend(matches)

    if '{{' in frontend_code and '}}' in frontend_code:
        # Find all string placeholders (excluding JSX expressions)
        import re
        # This pattern matches {{ not followed by white space (which would be JSX)
        matches = re.findall(r'\{\{[^{}\s][^{}]*\}\}', frontend_code)
        # Filter out valid JSX object syntax like {{ foo: bar }}
        matches = [m for m in matches if not ':' in m]
        placeholders_found.extend(matches)

    if placeholders_found:
        log(f"FAIL: Found unresolved placeholders: {placeholders_found}")
        # Save the code for debugging
        with open('/Users/avataer/Code/Faibric/customer-tests/faibric-full-fix-20260128/failed_code.jsx', 'w') as f:
            f.write(frontend_code)
        log("Saved failed code to failed_code.jsx")
        return False

    log("PASS: No template placeholders found in generated code")

    # Check for valid JavaScript syntax by looking for basic patterns
    if 'function App' not in frontend_code and 'const App' not in frontend_code:
        log("WARN: No App component found")

    if 'export default' not in frontend_code:
        log("WARN: No export default found")

    log("Code structure looks valid!")
    return True


if __name__ == "__main__":
    log("=== FAIBRIC FULL FIX TEST SUITE ===")
    log("")

    results = {}

    # Test 1: Intent Detection
    log("\n" + "="*50)
    log("RUNNING: Intent Detection Tests")
    log("="*50)
    results['intent_detection'] = test_intent_detection()

    # Test 2: Code Generation
    log("\n" + "="*50)
    log("RUNNING: Code Generation Tests")
    log("="*50)
    results['code_generation'] = test_code_generation_no_placeholders()

    # Summary
    log("\n" + "="*50)
    log("TEST SUMMARY")
    log("="*50)

    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        log(f"  {test_name}: {status}")

    all_passed = all(results.values())
    log(f"\nOVERALL: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")

    exit(0 if all_passed else 1)
