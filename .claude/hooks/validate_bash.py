#!/usr/bin/env python3
"""Bash command allowlist validator. Fail-closed design."""

import json
import re
import shlex
import sys


# Allowlisted commands with their allowed subcommands/patterns
ALLOWLIST = {
    "git": {
        "subcommands": [
            "status", "diff", "log", "add", "commit", "push", "pull",
            "fetch", "checkout", "branch", "show", "stash", "merge",
            "rebase", "reset", "clone", "init", "remote", "tag"
        ]
    },
    "npm": {
        "subcommands": ["install", "run", "test", "build", "ci", "start", "exec"]
    },
    "python3": {
        "patterns": [
            r"^python3\s+-m\s+pytest(\s|$)",
            r"^python3\s+-m\s+pip\s+install(\s|$)",
            r"^python3\s+[\w./\-]+\.py(\s|$)"
        ]
    },
    "curl": {
        "patterns": [r"^curl\s+-I(\s|$)"]  # HEAD only
    },
    "ls": {"standalone": True, "allow_args": True},
    "pwd": {"standalone": True},
    "which": {"standalone": True, "allow_args": True},
    "cat": {"standalone": True, "allow_args": True},
    "mkdir": {"standalone": True, "allow_args": True},
    "rm": {"standalone": True, "allow_args": True},
    "echo": {"standalone": True, "allow_args": True},
    "head": {"standalone": True, "allow_args": True},
    "tail": {"standalone": True, "allow_args": True},
    "touch": {"standalone": True, "allow_args": True},
    "cp": {"standalone": True, "allow_args": True},
    "mv": {"standalone": True, "allow_args": True},
    "chmod": {"standalone": True, "allow_args": True},
    "cd": {"standalone": True, "allow_args": True},
    "test": {"standalone": True, "allow_args": True},
    "[": {"standalone": True, "allow_args": True},
}


def get_base_command(command_str):
    """Extract the base command from a command string."""
    try:
        # Handle command chaining - check each part
        # Split on && || ; | but preserve the operators
        parts = re.split(r'\s*(?:&&|\|\||;|\|)\s*', command_str)
        if parts:
            first_part = parts[0].strip()
            if first_part:
                tokens = shlex.split(first_part)
                if tokens:
                    return tokens[0]
    except ValueError:
        pass
    return None


def check_command_allowed(command_str):
    """Check if a command is allowed. Returns (allowed, reason)."""
    if not command_str or not command_str.strip():
        return False, "Empty command"

    command_str = command_str.strip()

    # Split on command separators to check each subcommand
    # Matches: && || ; |
    subcommands = re.split(r'\s*(?:&&|\|\||;|\|)\s*', command_str)

    for subcmd in subcommands:
        subcmd = subcmd.strip()
        if not subcmd:
            continue

        allowed, reason = check_single_command(subcmd)
        if not allowed:
            return False, reason

    return True, "All commands in chain are allowed"


def check_single_command(command_str):
    """Check if a single command (no chaining) is allowed."""
    try:
        tokens = shlex.split(command_str)
    except ValueError as e:
        return False, f"Failed to parse command: {e}"

    if not tokens:
        return False, "No command found"

    base_cmd = tokens[0]

    # Handle path-based commands (e.g., /usr/bin/git)
    if "/" in base_cmd:
        base_cmd = base_cmd.split("/")[-1]

    if base_cmd not in ALLOWLIST:
        return False, f"Command not in allowlist: {base_cmd}"

    rules = ALLOWLIST[base_cmd]

    # Check subcommands
    if "subcommands" in rules:
        if len(tokens) < 2:
            return False, f"{base_cmd} requires a subcommand"
        subcommand = tokens[1]
        # Handle flags before subcommand (e.g., git -C /path status)
        for i, token in enumerate(tokens[1:], 1):
            if not token.startswith("-"):
                subcommand = token
                break
        if subcommand not in rules["subcommands"]:
            return False, f"{base_cmd} subcommand not allowed: {subcommand}"
        return True, f"{base_cmd} {subcommand} is allowed"

    # Check patterns
    if "patterns" in rules:
        for pattern in rules["patterns"]:
            if re.match(pattern, command_str):
                return True, f"Matches allowed pattern"
        return False, f"{base_cmd} does not match any allowed pattern"

    # Standalone commands
    if rules.get("standalone"):
        return True, f"{base_cmd} is allowed as standalone"

    return False, f"No matching rule for {base_cmd}"


def main():
    """Main validator entry point."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        # Fail-closed: if we can't parse input, deny
        result = {
            "continueExecution": False,
            "message": f"Failed to parse input JSON: {e}"
        }
        print(json.dumps(result))
        return

    # Extract command from hook input
    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    if not command:
        result = {
            "continueExecution": False,
            "message": "No command provided"
        }
        print(json.dumps(result))
        return

    allowed, reason = check_command_allowed(command)

    result = {
        "continueExecution": allowed,
        "message": reason if not allowed else None
    }

    # Remove None values
    result = {k: v for k, v in result.items() if v is not None}

    print(json.dumps(result))


if __name__ == "__main__":
    main()
