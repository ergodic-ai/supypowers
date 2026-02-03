#!/usr/bin/env bash
# Demo: files.py - File operations
set -e
cd "$(dirname "$0")"

echo "=== files:list_dir - List current directory ==="
uv run supypowers run --examples files:list_dir '{"path": "."}'

echo ""
echo "=== files:list_dir - List with pattern ==="
uv run supypowers run --examples files:list_dir '{"path": ".", "pattern": "*.sh"}'

echo ""
echo "=== files:read - Read a file ==="
uv run supypowers run --examples files:read '{"path": "README.md"}'

echo ""
echo "=== files:write - Write to a file ==="
uv run supypowers run --examples files:write '{"path": "/tmp/supypowers_test.txt", "content": "Hello from supypowers!"}'

echo ""
echo "=== files:read - Verify the write ==="
uv run supypowers run --examples files:read '{"path": "/tmp/supypowers_test.txt"}'
