#!/usr/bin/env bash
# Demo: scrape.py - Web scraping
set -e
cd "$(dirname "$0")"

echo "=== scrape:get_text - Extract readable text from a page ==="
uv run supypowers run --examples scrape:get_text '{"url": "https://example.com"}'

echo ""
echo "=== scrape:get_links - Extract all links ==="
uv run supypowers run --examples scrape:get_links '{"url": "https://example.com"}'

echo ""
echo "=== scrape:css_select - Select elements by CSS selector ==="
uv run supypowers run --examples scrape:css_select '{"url": "https://example.com", "selector": "h1"}'

echo ""
echo "=== scrape:css_select - Get href attributes from links ==="
uv run supypowers run --examples scrape:css_select '{"url": "https://example.com", "selector": "a", "attribute": "href"}'
