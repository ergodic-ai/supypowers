#!/usr/bin/env bash
# Demo: shell.py - Run shell commands
set -e
cd "$(dirname "$0")"

echo "=== shell:run - Simple command ==="
uv run supypowers run --examples shell:run '{"command": "echo Hello from shell!"}'

echo ""
echo "=== shell:run - Command with pipes ==="
uv run supypowers run --examples shell:run '{"command": "echo one two three | wc -w"}'

echo ""
echo "=== shell:run - List files ==="
uv run supypowers run --examples shell:run '{"command": "ls -la", "cwd": "/tmp"}'

echo ""
echo "=== shell:run - Environment variables ==="
uv run supypowers run --examples shell:run '{"command": "echo PATH is: $PATH | head -c 100"}'
