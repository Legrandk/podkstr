#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "→ Installing PyInstaller..."
.venv/bin/pip install pyinstaller --quiet

echo "→ Building dist/podkster..."
.venv/bin/pyinstaller \
    --onefile \
    --name podkster \
    --collect-data textual \
    --collect-data feedparser \
    --add-data "sources.json:." \
    --distpath dist \
    --workpath build/_pyinstaller \
    --specpath build \
    --noconfirm \
    main.py

echo ""
echo "✓ Done → dist/podkster"
echo "  Run with: ./dist/podkster"
