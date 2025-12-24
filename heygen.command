#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PROFILE_DIR="Headless Test/chrome_profile"
PYTHON_BIN="${HEYGEN_PYTHON:-}"

if [ -z "$PYTHON_BIN" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "Python not found. Install Python 3 or set HEYGEN_PYTHON."
    exit 1
  fi
fi

if [ ! -d "$PROFILE_DIR" ]; then
  echo "Chrome profile not found. Launching first-time login..."
  "$PYTHON_BIN" "Headless Test/setup_profile.py"
fi

"$PYTHON_BIN" "Headless Test/ui_server.py"
