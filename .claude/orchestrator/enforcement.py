"""
Enforcement verification module for Manager/Worker system.

All methods fail-closed: return passed=False on any error.
"""

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def verify_files_exist(file_paths: List[str]) -> Dict:
    """
    Check each claimed file exists on disk.

    Args:
        file_paths: List of file paths to check

    Returns:
        {"passed": bool, "missing": list}
    """
    try:
        if not file_paths:
            return {"passed": False, "missing": [], "error": "No files provided"}

        missing = []
        for path in file_paths:
            if not os.path.isfile(path):
                missing.append(path)

        return {
            "passed": len(missing) == 0,
            "missing": missing
        }
    except Exception as e:
        return {"passed": False, "missing": file_paths, "error": str(e)}


def verify_files_match_git(file_paths: List[str]) -> Dict:
    """
    Cross-reference claimed files with git status.

    Args:
        file_paths: List of file paths to verify against git

    Returns:
        {"passed": bool, "untracked": list, "not_modified": list}
    """
    try:
        if not file_paths:
            return {"passed": False, "untracked": [], "not_modified": [], "error": "No files provided"}

        # Get git status for porcelain output
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return {
                "passed": False,
                "untracked": [],
                "not_modified": file_paths,
                "error": f"git status failed: {result.stderr}"
            }

        # Parse git status output
        # Format: XY filename (where X=staging, Y=working tree)
        git_files = {}
        for line in result.stdout.split('\n'):
            if not line or len(line) < 4:
                continue
            status = line[:2]
            filepath = line[3:].strip()
            # Handle renamed files (format: "R  old -> new")
            if ' -> ' in filepath:
                filepath = filepath.split(' -> ')[1]
            git_files[filepath] = status

        untracked = []
        not_modified = []

        for path in file_paths:
            # Normalize path for comparison
            normalized = os.path.relpath(path) if os.path.isabs(path) else path

            if normalized in git_files:
                status = git_files[normalized]
                if status == '??':
                    untracked.append(path)
            else:
                # File not in git status means it's not modified
                not_modified.append(path)

        passed = len(untracked) == 0 and len(not_modified) == 0

        return {
            "passed": passed,
            "untracked": untracked,
            "not_modified": not_modified
        }
    except subprocess.TimeoutExpired:
        return {"passed": False, "untracked": [], "not_modified": file_paths, "error": "git command timed out"}
    except Exception as e:
        return {"passed": False, "untracked": [], "not_modified": file_paths, "error": str(e)}


def verify_url_reachable(url: str) -> Dict:
    """
    HTTP request with redirect following.
    Check final URL matches expected domain.

    Args:
        url: URL to verify

    Returns:
        {"passed": bool, "status_code": int, "final_url": str, "reason": str}
    """
    try:
        if not url:
            return {"passed": False, "status_code": 0, "final_url": "", "reason": "No URL provided"}

        if not HAS_REQUESTS:
            return {"passed": False, "status_code": 0, "final_url": "", "reason": "requests library not available"}

        # Parse expected domain from original URL
        parsed_original = urlparse(url)
        expected_domain = parsed_original.netloc

        if not expected_domain:
            return {"passed": False, "status_code": 0, "final_url": "", "reason": "Invalid URL format"}

        # Make request with redirect following (default behavior)
        response = requests.get(url, timeout=30, allow_redirects=True)

        final_url = response.url
        parsed_final = urlparse(final_url)
        final_domain = parsed_final.netloc

        # Check if final domain matches expected
        domain_matches = final_domain == expected_domain or final_domain.endswith('.' + expected_domain)

        # Success is 2xx status and domain match
        passed = 200 <= response.status_code < 300 and domain_matches

        reason = "OK" if passed else ""
        if not passed:
            if not (200 <= response.status_code < 300):
                reason = f"HTTP {response.status_code}"
            elif not domain_matches:
                reason = f"Domain mismatch: expected {expected_domain}, got {final_domain}"

        return {
            "passed": passed,
            "status_code": response.status_code,
            "final_url": final_url,
            "reason": reason
        }
    except requests.Timeout:
        return {"passed": False, "status_code": 0, "final_url": "", "reason": "Request timed out"}
    except requests.RequestException as e:
        return {"passed": False, "status_code": 0, "final_url": "", "reason": str(e)}
    except Exception as e:
        return {"passed": False, "status_code": 0, "final_url": "", "reason": str(e)}


def verify_no_forbidden_patterns(file_paths: List[str]) -> Dict:
    """
    Scan files for forbidden patterns: emojis, TypeScript in JS, etc.

    Args:
        file_paths: List of file paths to scan

    Returns:
        {"passed": bool, "violations": list}
    """
    try:
        if not file_paths:
            return {"passed": False, "violations": [], "error": "No files provided"}

        violations = []

        # Emoji pattern - common emoji ranges
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F700-\U0001F77F"  # alchemical symbols
            "\U0001F780-\U0001F7FF"  # geometric shapes extended
            "\U0001F800-\U0001F8FF"  # supplemental arrows-c
            "\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
            "\U0001FA00-\U0001FA6F"  # chess symbols
            "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
            "\U00002702-\U000027B0"  # dingbats
            "\U0001F1E0-\U0001F1FF"  # flags
            "]+"
        )

        # TypeScript patterns that shouldn't be in JS files
        typescript_patterns = [
            (re.compile(r'\binterface\s+\w+\s*\{'), "interface declaration"),
            (re.compile(r':\s*(?:string|number|boolean|void|any|never|unknown)\s*[;=)]'), "type annotation"),
            (re.compile(r'<\w+>'), "generic type"),
            (re.compile(r'\bas\s+\w+'), "type assertion"),
            (re.compile(r'\benum\s+\w+'), "enum declaration"),
            (re.compile(r'\btype\s+\w+\s*='), "type alias"),
        ]

        for file_path in file_paths:
            if not os.path.isfile(file_path):
                violations.append({
                    "file": file_path,
                    "line": 0,
                    "pattern": "file_not_found",
                    "description": "File does not exist"
                })
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
            except Exception as e:
                violations.append({
                    "file": file_path,
                    "line": 0,
                    "pattern": "read_error",
                    "description": str(e)
                })
                continue

            is_js_file = file_path.endswith('.js') or file_path.endswith('.mjs') or file_path.endswith('.cjs')

            for line_num, line in enumerate(lines, start=1):
                # Check for emojis in all files
                if emoji_pattern.search(line):
                    violations.append({
                        "file": file_path,
                        "line": line_num,
                        "pattern": "emoji",
                        "description": "Emoji found in code"
                    })

                # Check for TypeScript patterns in JS files
                if is_js_file:
                    for ts_pattern, ts_desc in typescript_patterns:
                        if ts_pattern.search(line):
                            violations.append({
                                "file": file_path,
                                "line": line_num,
                                "pattern": "typescript_in_js",
                                "description": f"TypeScript {ts_desc} in JS file"
                            })

        return {
            "passed": len(violations) == 0,
            "violations": violations
        }
    except Exception as e:
        return {"passed": False, "violations": [], "error": str(e)}


def verify_tests_passed(project_dir: str, command: str) -> Dict:
    """
    Run test command via subprocess.run.

    Args:
        project_dir: Directory to run tests in
        command: Test command to execute

    Returns:
        {"passed": bool, "exit_code": int, "stdout": str, "stderr": str, "duration_seconds": float}
    """
    try:
        if not project_dir:
            return {
                "passed": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": "",
                "duration_seconds": 0.0,
                "error": "No project directory provided"
            }

        if not command:
            return {
                "passed": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": "",
                "duration_seconds": 0.0,
                "error": "No command provided"
            }

        if not os.path.isdir(project_dir):
            return {
                "passed": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": "",
                "duration_seconds": 0.0,
                "error": f"Project directory does not exist: {project_dir}"
            }

        start_time = time.time()

        result = subprocess.run(
            command,
            shell=True,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        duration = time.time() - start_time

        return {
            "passed": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration_seconds": round(duration, 2)
        }
    except subprocess.TimeoutExpired as e:
        duration = time.time() - start_time if 'start_time' in locals() else 0.0
        return {
            "passed": False,
            "exit_code": -1,
            "stdout": e.stdout if e.stdout else "",
            "stderr": e.stderr if e.stderr else "",
            "duration_seconds": round(duration, 2),
            "error": "Command timed out after 300 seconds"
        }
    except Exception as e:
        return {
            "passed": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
            "duration_seconds": 0.0,
            "error": str(e)
        }


def verify_test_artifacts(project_dir: str) -> Dict:
    """
    Check for test coverage/result artifacts and verify timestamps are recent.

    Args:
        project_dir: Project directory to search for artifacts

    Returns:
        {"passed": bool, "artifacts_found": list, "stale": list}
    """
    try:
        if not project_dir:
            return {"passed": False, "artifacts_found": [], "stale": [], "error": "No project directory provided"}

        if not os.path.isdir(project_dir):
            return {"passed": False, "artifacts_found": [], "stale": [], "error": f"Project directory does not exist: {project_dir}"}

        # Common test artifact paths
        artifact_patterns = [
            "coverage/lcov.info",
            "coverage/coverage-summary.json",
            "coverage/clover.xml",
            "jest-results.json",
            ".coverage",
            "htmlcov/index.html",
            "test-results.xml",
            "pytest.xml",
            "junit.xml",
            ".pytest_cache/v/cache/lastfailed",
            ".nyc_output/out.json",
        ]

        artifacts_found = []
        stale = []
        current_time = time.time()
        max_age_seconds = 5 * 60  # 5 minutes

        for pattern in artifact_patterns:
            artifact_path = os.path.join(project_dir, pattern)
            if os.path.isfile(artifact_path):
                artifacts_found.append(pattern)

                # Check if file is stale
                try:
                    mtime = os.path.getmtime(artifact_path)
                    age = current_time - mtime
                    if age > max_age_seconds:
                        stale.append({
                            "artifact": pattern,
                            "age_seconds": round(age, 0)
                        })
                except OSError:
                    stale.append({
                        "artifact": pattern,
                        "age_seconds": -1,
                        "error": "Could not read modification time"
                    })

        # Passed if we found at least one artifact and none are stale
        passed = len(artifacts_found) > 0 and len(stale) == 0

        return {
            "passed": passed,
            "artifacts_found": artifacts_found,
            "stale": stale
        }
    except Exception as e:
        return {"passed": False, "artifacts_found": [], "stale": [], "error": str(e)}


# Session state for degradation tracking
# Key: session_id, Value: {"failures": [{"timestamp": float, "reason": str}], "consecutive": int}
_degradation_state: Dict[str, Dict] = {}

# Degradation state file path for persistence
DEGRADATION_STATE_FILE = os.path.join(
    os.path.dirname(__file__), ".degradation_state.json"
)


def _load_degradation_state() -> Dict:
    """Load persisted degradation state from disk."""
    try:
        if os.path.isfile(DEGRADATION_STATE_FILE):
            with open(DEGRADATION_STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_degradation_state(state: Dict) -> None:
    """Persist degradation state to disk."""
    try:
        with open(DEGRADATION_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def detect_degradation(
    session_id: str,
    failure_reason: Optional[str] = None,
    success: bool = False
) -> Dict:
    """
    Track consecutive failures per Worker session and detect degradation.

    Degradation signs include:
    - Repeated failures on simple tasks
    - Ignoring clear instructions
    - Claiming completion without evidence
    - Instant results on complex tasks

    Args:
        session_id: Unique identifier for the Worker session
        failure_reason: Reason for the failure (if success=False)
        success: True if the task succeeded, False if it failed

    Returns:
        {
            "degraded": bool,        # True if 2+ consecutive failures
            "consecutive_failures": int,
            "total_failures": int,
            "recent_reasons": list,  # Last 5 failure reasons for analysis
            "recommendation": str    # "continue", "retry", or "restart_session"
        }
    """
    global _degradation_state

    try:
        if not session_id:
            return {
                "degraded": False,
                "consecutive_failures": 0,
                "total_failures": 0,
                "recent_reasons": [],
                "recommendation": "continue",
                "error": "No session_id provided"
            }

        # Load persisted state on first access
        if not _degradation_state:
            _degradation_state = _load_degradation_state()

        # Initialize session state if needed
        if session_id not in _degradation_state:
            _degradation_state[session_id] = {
                "failures": [],
                "consecutive": 0,
                "successes": 0
            }

        session = _degradation_state[session_id]

        if success:
            # Reset consecutive counter on success
            session["consecutive"] = 0
            session["successes"] += 1
        else:
            # Record failure
            session["consecutive"] += 1
            session["failures"].append({
                "timestamp": time.time(),
                "reason": failure_reason or "unspecified"
            })
            # Keep only last 20 failures to limit memory
            if len(session["failures"]) > 20:
                session["failures"] = session["failures"][-20:]

        # Persist state
        _save_degradation_state(_degradation_state)

        # Determine degradation status
        consecutive = session["consecutive"]
        total_failures = len(session["failures"])
        recent_reasons = [f["reason"] for f in session["failures"][-5:]]

        # Degraded if 2+ consecutive failures
        degraded = consecutive >= 2

        # Recommendation based on severity
        if consecutive >= 3:
            recommendation = "restart_session"
        elif consecutive >= 2:
            recommendation = "retry"
        else:
            recommendation = "continue"

        return {
            "degraded": degraded,
            "consecutive_failures": consecutive,
            "total_failures": total_failures,
            "recent_reasons": recent_reasons,
            "recommendation": recommendation
        }
    except Exception as e:
        # Fail-closed: assume not degraded but report error
        return {
            "degraded": False,
            "consecutive_failures": 0,
            "total_failures": 0,
            "recent_reasons": [],
            "recommendation": "continue",
            "error": str(e)
        }


def clear_degradation_state(session_id: Optional[str] = None) -> Dict:
    """
    Clear degradation state for a session or all sessions.

    Args:
        session_id: Session to clear, or None to clear all

    Returns:
        {"cleared": bool, "sessions_cleared": int}
    """
    global _degradation_state

    try:
        if not _degradation_state:
            _degradation_state = _load_degradation_state()

        if session_id:
            if session_id in _degradation_state:
                del _degradation_state[session_id]
                _save_degradation_state(_degradation_state)
                return {"cleared": True, "sessions_cleared": 1}
            return {"cleared": True, "sessions_cleared": 0}
        else:
            count = len(_degradation_state)
            _degradation_state = {}
            _save_degradation_state(_degradation_state)
            return {"cleared": True, "sessions_cleared": count}
    except Exception as e:
        return {"cleared": False, "sessions_cleared": 0, "error": str(e)}


def get_degradation_summary(session_id: str) -> Dict:
    """
    Get a summary of degradation state for a session.

    Args:
        session_id: Session to summarize

    Returns:
        {"exists": bool, "consecutive_failures": int, "total_failures": int, "successes": int}
    """
    global _degradation_state

    try:
        if not _degradation_state:
            _degradation_state = _load_degradation_state()

        if session_id not in _degradation_state:
            return {
                "exists": False,
                "consecutive_failures": 0,
                "total_failures": 0,
                "successes": 0
            }

        session = _degradation_state[session_id]
        return {
            "exists": True,
            "consecutive_failures": session.get("consecutive", 0),
            "total_failures": len(session.get("failures", [])),
            "successes": session.get("successes", 0)
        }
    except Exception as e:
        return {
            "exists": False,
            "consecutive_failures": 0,
            "total_failures": 0,
            "successes": 0,
            "error": str(e)
        }
