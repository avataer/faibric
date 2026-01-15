#!/usr/bin/env python3
"""
Worker Session Sentinel - creates a marker file when Worker task starts.
The marker is deleted when Worker sends IPC result.
Stop hook checks for marker existence - blocks if still present.
"""

import sys
import json
from pathlib import Path

SENTINEL_DIR = Path.home() / ".claude-manager" / "ipc" / "worker-sentinel"
SENTINEL_DIR.mkdir(parents=True, exist_ok=True)


def create_sentinel(task_id: str):
    """Create sentinel when Worker receives a task."""
    sentinel_file = SENTINEL_DIR / f"{task_id}.sentinel"
    sentinel_file.write_text(task_id)
    print(f"Session started for task: {task_id}", file=sys.stderr)


def delete_sentinel(task_id: str):
    """Delete sentinel when Worker sends IPC result."""
    sentinel_file = SENTINEL_DIR / f"{task_id}.sentinel"
    if sentinel_file.exists():
        sentinel_file.unlink()


def check_sentinel() -> tuple[bool, str]:
    """Check if any sentinel exists (Worker hasn't completed IPC)."""
    sentinels = list(SENTINEL_DIR.glob("*.sentinel"))
    if sentinels:
        task_ids = [s.stem for s in sentinels]
        return False, f"Must send IPC result for tasks: {task_ids}"
    return True, ""


if __name__ == "__main__":
    # Called as Stop hook - check for uncommitted sentinels
    passed, message = check_sentinel()
    if not passed:
        print(f"BLOCKED: {message}", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)
