#!/usr/bin/env bash
# Demo: crypto.py - Encoding, hashing, UUIDs
set -e
cd "$(dirname "$0")"

echo "=== crypto:hash - SHA256 hash ==="
uv run supypowers run --examples crypto:hash '{"text": "hello world", "algorithm": "sha256"}'

echo ""
echo "=== crypto:hash - MD5 hash ==="
uv run supypowers run --examples crypto:hash '{"text": "hello world", "algorithm": "md5"}'

echo ""
echo "=== crypto:base64_encode - Encode to base64 ==="
uv run supypowers run --examples crypto:base64_encode '{"text": "Hello, World!"}'

echo ""
echo "=== crypto:base64_decode - Decode from base64 ==="
uv run supypowers run --examples crypto:base64_decode '{"text": "SGVsbG8sIFdvcmxkIQ=="}'

echo ""
echo "=== crypto:uuid - Generate UUID v4 ==="
uv run supypowers run --examples crypto:uuid '{}'

echo ""
echo "=== crypto:uuid - Generate UUID v1 (time-based) ==="
uv run supypowers run --examples crypto:uuid '{"version": 1}'
