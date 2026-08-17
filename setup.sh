#!/usr/bin/env bash
set -e

echo "=== Installing YouTube Summarizer Kit (chew) ==="

# 1. Install virtualenv & dependencies in editable mode
if command -v uv >/dev/null 2>&1; then
    uv pip install -e .
else
    pip install -e .
fi

# 2. Automatically register 'chew' alias in ~/.zshrc or ~/.bashrc
SHELL_RC=""
if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [ -n "$SHELL_RC" ]; then
    if ! grep -q "alias chew=" "$SHELL_RC"; then
        echo '' >> "$SHELL_RC"
        echo '# chew CLI alias' >> "$SHELL_RC"
        echo 'alias chew="uv run chew"' >> "$SHELL_RC"
        echo "Added 'chew' alias to $SHELL_RC"
    fi
fi

# 3. Automatically initialize default CHEW.md and .chew/profiles/
if command -v uv >/dev/null 2>&1; then
    uv run chew config --init >/dev/null 2>&1 || true
else
    python3 -m chew.cli config --init >/dev/null 2>&1 || true
fi

echo "=== Setup Complete! You can now run 'chew' directly in your terminal. ==="
