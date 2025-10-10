#!/usr/bin/env bash
set -euo pipefail

SPACE_HOME="${SPACE_HOME:-$HOME/space}"
BIN_DIR="${HOME}/bin"
REPO_URL="https://github.com/teebz/space-os"
VERSION="${SPACE_VERSION:-latest}"

echo "🚀 Installing space-os to $SPACE_HOME"

if [ -d "$SPACE_HOME" ]; then
    echo "⚠️  $SPACE_HOME already exists. Skipping directory creation."
else
    mkdir -p "$SPACE_HOME"
    echo "✓ Created $SPACE_HOME"
fi

mkdir -p "$SPACE_HOME/canon"
mkdir -p "$SPACE_HOME/projects"
mkdir -p "$BIN_DIR"

echo "✓ Workspace structure ready"

if command -v pipx &> /dev/null; then
    echo "📦 Installing space-os via pipx..."
    pipx install space-os || pipx upgrade space-os
elif command -v pip &> /dev/null; then
    echo "📦 Installing space-os via pip..."
    pip install --user space-os
else
    echo "❌ Neither pipx nor pip found. Install Python 3.12+ first."
    exit 1
fi

if ! echo "$PATH" | grep -q "$BIN_DIR"; then
    echo ""
    echo "⚠️  Add to your shell RC file (~/.bashrc, ~/.zshrc, etc.):"
    echo "   export PATH=\"\$HOME/bin:\$PATH\""
fi

echo ""
echo "✓ Installation complete!"
echo ""
echo "Next steps:"
echo "  cd $SPACE_HOME"
echo "  space init"
