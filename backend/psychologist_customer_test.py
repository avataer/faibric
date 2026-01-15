#!/usr/bin/env python
"""
Customer Test: Psychologist Website

Tests Faibric with a specific customer prompt for a psychologist website.
"""
import os
import sys
import time
import json
import django
import secrets
import subprocess
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'faibric_backend.settings')
sys.path.insert(0, '/app')
django.setup()

from apps.onboarding.models import LandingSession, SessionEvent
from apps.onboarding.build_service import BuildService
import requests

# The exact customer prompt
CUSTOMER_PROMPT = """I am a psychologist. A need a website to find new clients. Create a compelling, very beautiful website, and make them want to buy my services. I should get information about new clients to my email from the website which is amptiness@icloud.com I charge 99$/hour, I only help asian women with two dogs, i never take clients with less then two dogs or with more than two dogs, this is bad karma. Please use no placeholders, only final version of the working website, i relly need new clients i need money asap. Website must have an AI generated image where there is a yellow UFO parked near a green Bentley."""

# Feature checklist
FEATURE_CHECKLIST = [
    ("Email: amptiness@icloud.com in contact form", "amptiness@icloud.com"),
    ("Price: $99/hour displayed", "99"),
    ("Niche: Asian women with exactly two dogs messaging", "two dogs"),
    ("Beautiful/compelling design", None),  # Manual check
]

def run_test():
    """Run the customer test."""
    report = {
        "test_name": "Psychologist Website Customer Test",
        "timestamp": datetime.now().isoformat(),
        "prompt": CUSTOMER_PROMPT,
        "status": "running",
        "phases": [],
        "deployed_url": None,
        "errors": [],
        "feature_checks": [],
    }

    print("\n" + "="*70)
    print("CUSTOMER TEST: Psychologist Website")
    print("="*70)
    print(f"Timestamp: {report['timestamp']}")
    print(f"\nPrompt:\n{CUSTOMER_PROMPT[:200]}...")

    # Phase 1: Create session
    print("\n--- PHASE 1: Creating session ---")
    session_token = secrets.token_urlsafe(32)
    email = "test-psychologist@faibric.test"

    try:
        session = LandingSession.objects.create(
            session_token=session_token,
            initial_request=CUSTOMER_PROMPT,
            email=email,
            status='verified'
        )
        print(f"Session created: {session_token[:20]}...")
        report["phases"].append({"name": "session_creation", "status": "success", "session_token": session_token[:20]})
    except Exception as e:
        print(f"FAILED to create session: {e}")
        report["phases"].append({"name": "session_creation", "status": "failed", "error": str(e)})
        report["status"] = "failed"
        return report

    # Phase 2: Build the website
    print("\n--- PHASE 2: Building website ---")
    start_time = time.time()

    try:
        result = BuildService.build_from_session(session_token)
        elapsed = time.time() - start_time
        print(f"Build time: {elapsed:.1f}s")

        if result.get('success'):
            url = result.get('url', '')
            print(f"Build SUCCESS: {url}")
            report["deployed_url"] = url
            report["phases"].append({
                "name": "build",
                "status": "success",
                "url": url,
                "build_time": elapsed
            })
        else:
            error = result.get('error', 'Unknown error')
            print(f"Build FAILED: {error}")
            report["phases"].append({"name": "build", "status": "failed", "error": error})
            report["errors"].append(f"Build failed: {error}")
            report["status"] = "failed"
            return report

    except Exception as e:
        print(f"Build exception: {e}")
        report["phases"].append({"name": "build", "status": "failed", "error": str(e)})
        report["errors"].append(f"Build exception: {str(e)}")
        report["status"] = "failed"
        return report

    # Phase 3: Verify deployment
    print("\n--- PHASE 3: Verifying deployment ---")
    time.sleep(5)  # Give Render time to deploy

    deployed_url = report["deployed_url"]
    if not deployed_url or "localhost" in deployed_url:
        print("ERROR: Not a deployed URL (localhost detected)")
        report["errors"].append("URL is localhost, not deployed")
        report["status"] = "failed"
        return report

    try:
        resp = requests.get(deployed_url, timeout=30)
        html_content = resp.text

        if resp.status_code == 200:
            print(f"Site accessible: HTTP {resp.status_code}")
            report["phases"].append({
                "name": "verification",
                "status": "success",
                "http_status": resp.status_code
            })

            # Phase 4: Feature checks
            print("\n--- PHASE 4: Feature checks ---")
            for feature_name, search_term in FEATURE_CHECKLIST:
                if search_term:
                    found = search_term.lower() in html_content.lower()
                    status = "PASS" if found else "FAIL"
                    print(f"  {status}: {feature_name}")
                    report["feature_checks"].append({
                        "feature": feature_name,
                        "status": "pass" if found else "fail",
                        "search_term": search_term
                    })
                else:
                    print(f"  MANUAL: {feature_name}")
                    report["feature_checks"].append({
                        "feature": feature_name,
                        "status": "manual_check_required"
                    })
        else:
            print(f"Site returned HTTP {resp.status_code}")
            report["phases"].append({
                "name": "verification",
                "status": "failed",
                "http_status": resp.status_code
            })
            report["errors"].append(f"Site returned HTTP {resp.status_code}")

    except Exception as e:
        print(f"Verification failed: {e}")
        report["phases"].append({"name": "verification", "status": "failed", "error": str(e)})
        report["errors"].append(f"Verification failed: {str(e)}")

    # Final status
    failed_phases = [p for p in report["phases"] if p.get("status") == "failed"]
    if failed_phases:
        report["status"] = "failed"
    else:
        report["status"] = "completed"

    print("\n" + "="*70)
    print(f"TEST STATUS: {report['status'].upper()}")
    print(f"DEPLOYED URL: {report['deployed_url']}")
    print("="*70)

    return report


if __name__ == '__main__':
    report = run_test()

    # Save report
    report_path = '/app/docs/PSYCHOLOGIST_TEST_REPORT.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to: {report_path}")

    sys.exit(0 if report["status"] == "completed" else 1)
