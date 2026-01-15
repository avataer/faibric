#!/bin/bash
# Faibric Claude Code Launcher
# Injects rules into system prompt for higher priority

cd /Users/abram/Code/Faibric

# Check if rules file exists
RULES_FILE="docs/archived/RULES_OF_PROJECT.md"
if [ ! -f "$RULES_FILE" ]; then
    echo "Warning: Rules file not found at $RULES_FILE"
    echo "Running without --append-system-prompt"
    exec claude "$@"
fi

# Run Claude with rules injected into system prompt
exec claude --append-system-prompt "$(cat $RULES_FILE)" "$@"
