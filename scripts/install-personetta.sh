#!/usr/bin/env bash
# Install the `personetta` CLI from PyPI, working around PEP 668
# (externally-managed) systems where a bare `pip install` is blocked.
#
# Cascade: pipx (best isolation) -> dedicated venv in ~/.personetta/venv.
# Also ensures ~/.local/bin is on PATH for interactive shells, and runs
# `personetta verify` at the end.
#
# Usage:  ./scripts/install-personetta.sh
set -euo pipefail

BIN="$HOME/.local/bin"
mkdir -p "$BIN"

echo "Installing personetta from PyPI..."
if command -v pipx >/dev/null 2>&1; then
    pipx install --force personetta
    echo "Installed via pipx."
elif python3 -c "import ensurepip" >/dev/null 2>&1; then
    VENV="$HOME/.personetta/venv"
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q --upgrade personetta
    ln -sf "$VENV/bin/personetta" "$BIN/personetta"
    echo "Installed via venv -> $VENV"
else
    echo "Neither pipx nor Python venv support (python3-venv) is available." >&2
    echo "Install one of them, or run: python3 -m pip install --user personetta" >&2
    exit 1
fi

# Ensure ~/.local/bin is on PATH for interactive shells.
BRC="$HOME/.bashrc"
if ! grep -q "personetta launcher PATH" "$BRC" 2>/dev/null; then
    {
        echo ""
        echo "# personetta launcher PATH (added by install-personetta.sh)"
        echo "case \":\$PATH:\" in *\":\$HOME/.local/bin:\"*) ;; *) export PATH=\"\$HOME/.local/bin:\$PATH\" ;; esac"
    } >> "$BRC"
    echo "Added ~/.local/bin to PATH in ~/.bashrc"
fi

echo ""
echo "Verifying install..."
if command -v personetta >/dev/null 2>&1; then
    personetta verify || true
elif [ -x "$BIN/personetta" ]; then
    "$BIN/personetta" verify || true
fi

echo ""
echo "Done. Open a new terminal (or run: source ~/.bashrc) so 'personetta' is on PATH."
