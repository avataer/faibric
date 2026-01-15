#!/usr/bin/env python3
"""Stop/session completion validator. Fail-closed design.

This hook runs before a session completes to ensure all requirements are met:
- If implementation files were modified, test evidence is required
- If URLs were presented, verification evidence is required
- If bugs were fixed, root cause documentation is required
"""

import json
import os
import re
import sys

# Patterns for implementation files (not tests, configs, docs)
IMPLEMENTATION_PATTERNS = [
    r'\.py$',
    r'\.js$',
    r'\.jsx$',
    r'\.ts$',
    r'\.tsx$',
    r'\.go$',
    r'\.rs$',
    r'\.java$',
    r'\.c$',
    r'\.cpp$',
    r'\.h$',
]

# Patterns to exclude from implementation files
EXCLUDE_PATTERNS = [
    r'test[_/]',
    r'_test\.py$',
    r'\.test\.',
    r'spec\.',
    r'_spec\.',
    r'__tests__',
    r'conftest\.py$',
    r'setup\.py$',
    r'config\.',
    r'\.config\.',
    r'\.md$',
    r'\.txt$',
    r'\.json$',
    r'\.yaml$',
    r'\.yml$',
]

# Patterns that indicate test execution
TEST_EVIDENCE_PATTERNS = [
    r'pytest',
    r'npm\s+test',
    r'npm\s+run\s+test',
    r'go\s+test',
    r'cargo\s+test',
    r'jest',
    r'mocha',
    r'passed',
    r'PASSED',
    r'OK\s+\(\d+\s+tests?\)',
]

# Patterns that indicate URL verification
URL_PATTERN = re.compile(r'https?://[^\s<>\"\'\)\]]+')

VERIFICATION_PATTERNS = [
    r'curl\s+-I',
    r'curl.*HEAD',
    r'verified',
    r'confirmed',
    r'accessible',
    r'200\s+OK',
    r'status.*200',
]

# Patterns that indicate bug fix context
BUG_FIX_PATTERNS = [
    r'fix(ed|es|ing)?',
    r'bug',
    r'issue',
    r'error',
    r'broken',
    r'crash',
    r'fail(ed|ing|ure)?',
]

# Patterns that indicate root cause documentation
ROOT_CAUSE_PATTERNS = [
    r'root\s*cause',
    r'caused\s+by',
    r'because',
    r'the\s+problem\s+was',
    r'the\s+issue\s+was',
    r'reason:',
    r'due\s+to',
]


def is_implementation_file(file_path):
    """Check if a file is an implementation file (not test/config/docs)."""
    if not file_path:
        return False

    # Check if it matches implementation patterns
    is_impl = any(re.search(p, file_path, re.IGNORECASE) for p in IMPLEMENTATION_PATTERNS)
    if not is_impl:
        return False

    # Check if it should be excluded
    is_excluded = any(re.search(p, file_path, re.IGNORECASE) for p in EXCLUDE_PATTERNS)
    return not is_excluded


def extract_modified_files(session_context):
    """Extract list of modified files from session context."""
    files = []

    # Look for file paths in various forms
    file_path_pattern = re.compile(r'(?:file[_\s]?path|modified|edited|created|wrote)[:\s]+([/\w\.\-]+\.\w+)', re.IGNORECASE)

    if isinstance(session_context, dict):
        # Check tool_input for file_path
        tool_input = session_context.get('tool_input', {})
        if isinstance(tool_input, dict):
            fp = tool_input.get('file_path')
            if fp:
                files.append(fp)

        # Check files_modified if present
        files_modified = session_context.get('files_modified', [])
        if isinstance(files_modified, list):
            files.extend(files_modified)

        # Check content for file references
        content = session_context.get('content', '')
        if isinstance(content, str):
            matches = file_path_pattern.findall(content)
            files.extend(matches)

    return list(set(files))


def check_test_evidence(session_context):
    """Check if test execution evidence exists in session context."""
    content = ""

    if isinstance(session_context, dict):
        content = str(session_context.get('content', ''))
        content += str(session_context.get('output', ''))
        content += str(session_context.get('summary', ''))
    elif isinstance(session_context, str):
        content = session_context

    for pattern in TEST_EVIDENCE_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return True, f"Found test evidence: {pattern}"

    return False, "No test execution evidence found"


def check_url_verification(session_context, urls):
    """Check if URL verification evidence exists."""
    content = ""

    if isinstance(session_context, dict):
        content = str(session_context.get('content', ''))
        content += str(session_context.get('output', ''))
        content += str(session_context.get('summary', ''))
    elif isinstance(session_context, str):
        content = session_context

    for pattern in VERIFICATION_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return True, f"Found verification evidence: {pattern}"

    return False, f"URLs presented but no verification evidence found. URLs: {urls[:3]}"


def check_root_cause_documentation(session_context):
    """Check if root cause documentation exists for bug fixes."""
    content = ""

    if isinstance(session_context, dict):
        content = str(session_context.get('content', ''))
        content += str(session_context.get('output', ''))
        content += str(session_context.get('summary', ''))
    elif isinstance(session_context, str):
        content = session_context

    for pattern in ROOT_CAUSE_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return True, f"Found root cause documentation: {pattern}"

    return False, "Bug fix detected but no root cause documentation found"


def extract_urls(session_context):
    """Extract URLs from session context."""
    content = ""

    if isinstance(session_context, dict):
        content = str(session_context.get('content', ''))
        content += str(session_context.get('output', ''))
    elif isinstance(session_context, str):
        content = session_context

    return URL_PATTERN.findall(content)


def is_bug_fix_context(session_context):
    """Check if the session context indicates a bug fix."""
    content = ""

    if isinstance(session_context, dict):
        content = str(session_context.get('content', ''))
        content += str(session_context.get('description', ''))
        content += str(session_context.get('task', ''))
    elif isinstance(session_context, str):
        content = session_context

    for pattern in BUG_FIX_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return True

    return False


def main():
    """Main validator entry point."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        # Fail-closed: deny on parse error
        result = {
            "continueExecution": False,
            "message": f"Failed to parse input JSON: {e}"
        }
        print(json.dumps(result))
        return

    # Get session context from input
    session_context = input_data.get('session_context', input_data)

    errors = []

    # Check 1: If implementation files were modified, require test evidence
    modified_files = extract_modified_files(session_context)
    impl_files = [f for f in modified_files if is_implementation_file(f)]

    if impl_files:
        has_tests, test_reason = check_test_evidence(session_context)
        if not has_tests:
            errors.append(f"Implementation files modified ({impl_files[:3]}...) but {test_reason}")

    # Check 2: If URLs were presented, require verification evidence
    urls = extract_urls(session_context)
    if urls:
        has_verification, verify_reason = check_url_verification(session_context, urls)
        if not has_verification:
            errors.append(verify_reason)

    # Check 3: If bug was fixed, require root cause documentation
    if is_bug_fix_context(session_context):
        has_root_cause, root_cause_reason = check_root_cause_documentation(session_context)
        if not has_root_cause:
            errors.append(root_cause_reason)

    if errors:
        result = {
            "continueExecution": False,
            "message": "Session completion blocked: " + "; ".join(errors)
        }
    else:
        result = {"continueExecution": True}

    print(json.dumps(result))


if __name__ == "__main__":
    main()
