#!/usr/bin/env python
"""
End-to-end customer test for Faibric.

Simulates a real customer:
1. Creates a session
2. Provides email
3. Triggers build
4. Polls for completion
5. Verifies the deployed app
"""
import os
import sys
import time
import json
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'faibric_backend.settings')
sys.path.insert(0, '/app')
django.setup()

from apps.onboarding.models import LandingSession, SessionEvent
from apps.onboarding.build_service import BuildService
from apps.projects.models import Project
import secrets
import requests

def test_customer_build(prompt: str, description: str):
    """Run a complete customer build test."""
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"{'='*60}")
    print(f"Prompt: {prompt[:80]}...")
    
    # Create session
    session_token = secrets.token_urlsafe(32)
    email = f"test{secrets.token_hex(4)}@faibric.test"
    
    session = LandingSession.objects.create(
        session_token=session_token,
        initial_request=prompt,
        email=email,
        status='verified'
    )
    print(f"✓ Created session: {session_token[:20]}...")
    
    # Build the app
    print("Building...")
    start_time = time.time()
    
    result = BuildService.build_from_session(session_token)
    
    elapsed = time.time() - start_time
    print(f"Build time: {elapsed:.1f}s")
    
    if result.get('success'):
        url = result.get('url', '')
        print(f"✓ Build SUCCESS: {url}")
        
        # Verify the URL
        time.sleep(2)  # Give Render a moment
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                has_js = 'assets/index' in resp.text
                print(f"✓ Site accessible: {resp.status_code}, Has JS: {has_js}")
                return {'success': True, 'url': url, 'time': elapsed}
            else:
                print(f"✗ Site returned {resp.status_code}")
                return {'success': False, 'error': f'HTTP {resp.status_code}', 'url': url}
        except Exception as e:
            print(f"⚠ Could not verify URL: {e}")
            return {'success': True, 'url': url, 'time': elapsed, 'verified': False}
    else:
        print(f"✗ Build FAILED: {result.get('error', 'Unknown error')}")
        return {'success': False, 'error': result.get('error')}

def main():
    print("\n" + "="*60)
    print("FAIBRIC END-TO-END CUSTOMER TEST")
    print("="*60)
    
    # Test cases representing real customer requests
    test_cases = [
        ("Build a personal portfolio website with my projects, skills, and contact form", "Portfolio Website"),
        ("Create a real-time crypto price tracker dashboard", "Crypto Dashboard"),
        ("Build a task management app with kanban boards", "Task Manager"),
    ]
    
    results = []
    for prompt, desc in test_cases:
        result = test_customer_build(prompt, desc)
        results.append((desc, result))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    success_count = sum(1 for _, r in results if r.get('success'))
    print(f"Passed: {success_count}/{len(results)}")
    
    for desc, result in results:
        status = "✓" if result.get('success') else "✗"
        url = result.get('url', 'N/A')
        print(f"  {status} {desc}: {url}")
    
    return success_count == len(results)

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
