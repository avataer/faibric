#!/usr/bin/env python3
"""
Customer Test: Intent Detection Fix
Date: 2026-01-28
Fix: Chat now distinguishes questions/feedback from commands

Test Scenario: User creates a website and asks questions about it
"""
import requests
import json
import time
from datetime import datetime

API_BASE = "https://faibric-api.onrender.com"
RESULTS = []

def log(msg, status="INFO"):
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{timestamp}] [{status}] {msg}")
    RESULTS.append({"time": timestamp, "status": status, "message": msg})

def test_step(name, condition, details=""):
    if condition:
        log(f"✓ {name}: PASS {details}", "PASS")
        return True
    else:
        log(f"✗ {name}: FAIL {details}", "FAIL")
        return False

print("=" * 60)
print("CUSTOMER TEST: Intent Detection Fix")
print("=" * 60)

# Step 1: Create session
log("Creating new session...")
resp = requests.post(f"{API_BASE}/api/onboarding/start/", 
    json={"request": "I need a coffee shop website with menu and online ordering"},
    headers={"Content-Type": "application/json"})

session_data = resp.json()
session_token = session_data.get("session_token")
test_step("Session created", session_token is not None, f"token={session_token[:20]}...")

# Step 2: Test question (should NOT trigger rebuild)
log("Testing: User asks a QUESTION...")
resp = requests.post(f"{API_BASE}/api/onboarding/modify/",
    json={"session_token": session_token, "request": "What colors would work best for a coffee shop?"},
    headers={"Content-Type": "application/json"})
q1 = resp.json()
test_step("Question detected", q1.get("intent") == "question", f"intent={q1.get('intent')}")
test_step("Conversation mode", q1.get("mode") == "conversation", f"mode={q1.get('mode')}")
test_step("Got helpful response", len(q1.get("response", "")) > 20, f"response_len={len(q1.get('response', ''))}")

# Step 3: Test another question with ?
log("Testing: User asks another QUESTION (with ?)...")
resp = requests.post(f"{API_BASE}/api/onboarding/modify/",
    json={"session_token": session_token, "request": "Can you suggest some fonts?"},
    headers={"Content-Type": "application/json"})
q2 = resp.json()
test_step("Question with ? detected", q2.get("intent") == "question", f"intent={q2.get('intent')}")
test_step("Conversation mode for ?", q2.get("mode") == "conversation", f"mode={q2.get('mode')}")

# Step 4: Test feedback (should NOT trigger rebuild)
log("Testing: User gives FEEDBACK...")
resp = requests.post(f"{API_BASE}/api/onboarding/modify/",
    json={"session_token": session_token, "request": "I think warm brown tones would be nice"},
    headers={"Content-Type": "application/json"})
f1 = resp.json()
test_step("Feedback detected", f1.get("intent") == "feedback", f"intent={f1.get('intent')}")
test_step("Conversation mode for feedback", f1.get("mode") == "conversation", f"mode={f1.get('mode')}")

# Step 5: Test command (SHOULD trigger rebuild)
log("Testing: User gives COMMAND...")
resp = requests.post(f"{API_BASE}/api/onboarding/modify/",
    json={"session_token": session_token, "request": "Make the header dark brown and add a coffee cup logo"},
    headers={"Content-Type": "application/json"})
c1 = resp.json()
test_step("Command triggers rebuild", c1.get("mode") == "rebuild", f"mode={c1.get('mode')}")

# Step 6: Test edge case - "I don't like" feedback
log("Testing: User says 'I don't like' (FEEDBACK)...")
resp = requests.post(f"{API_BASE}/api/onboarding/modify/",
    json={"session_token": session_token, "request": "I don't like the current layout"},
    headers={"Content-Type": "application/json"})
f2 = resp.json()
test_step("'I don't like' is feedback", f2.get("intent") == "feedback", f"intent={f2.get('intent')}")

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
passes = sum(1 for r in RESULTS if r["status"] == "PASS")
fails = sum(1 for r in RESULTS if r["status"] == "FAIL")
print(f"PASSED: {passes}")
print(f"FAILED: {fails}")
print(f"RESULT: {'✓ ALL TESTS PASSED' if fails == 0 else '✗ SOME TESTS FAILED'}")
print("=" * 60)

# Exit with appropriate code
exit(0 if fails == 0 else 1)
