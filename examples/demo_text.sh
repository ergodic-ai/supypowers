#!/usr/bin/env bash
# Demo: text.py - Text processing
set -e
cd "$(dirname "$0")"

echo "=== text:regex_search - Find all numbers ==="
uv run supypowers run --examples text:regex_search '{"text": "Order 123 has 45 items at $99.99", "pattern": "\\d+"}'

echo ""
echo "=== text:regex_search - Find emails (case insensitive) ==="
uv run supypowers run --examples text:regex_search '{"text": "Contact: Admin@Example.COM or support@test.org", "pattern": "[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}", "flags": "i"}'

echo ""
echo "=== text:replace - Simple replacement ==="
uv run supypowers run --examples text:replace '{"text": "Hello World! Hello Universe!", "find": "Hello", "replace": "Hi"}'

echo ""
echo "=== text:replace - Regex replacement ==="
uv run supypowers run --examples text:replace '{"text": "Date: 2024-01-15", "find": "(\\d{4})-(\\d{2})-(\\d{2})", "replace": "\\2/\\3/\\1", "regex": true}'

echo ""
echo "=== text:extract_json - Extract JSON from text ==="
uv run supypowers run --examples text:extract_json '{"text": "Response: {\"status\": \"ok\", \"count\": 42} end"}'
