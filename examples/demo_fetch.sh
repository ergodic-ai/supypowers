#!/usr/bin/env bash
# Demo: fetch.py - HTTP requests
set -e
cd "$(dirname "$0")"

echo "=== fetch:get - Simple GET request ==="
uv run supypowers run --examples fetch:get '{"url": "https://httpbin.org/get"}'

echo ""
echo "=== fetch:get - With custom headers ==="
uv run supypowers run --examples fetch:get '{"url": "https://httpbin.org/headers", "headers": {"X-Custom": "test"}}'

echo ""
echo "=== fetch:post - POST with JSON body ==="
uv run supypowers run --examples fetch:post '{"url": "https://httpbin.org/post", "json_body": {"name": "agent", "value": 42}}'
