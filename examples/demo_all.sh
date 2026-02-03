#!/usr/bin/env bash
# Run all demo scripts
set -e
cd "$(dirname "$0")"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║             SUPYPOWERS - Demo All Functions                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

for script in demo_crypto.sh demo_text.sh demo_files.sh demo_shell.sh demo_fetch.sh demo_scrape.sh; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Running: $script"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    bash "./$script"
    echo ""
done

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    All demos completed!                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
