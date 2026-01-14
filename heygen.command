#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PROFILE_DIR="Headless Test/chrome_profile"
PYTHON_BIN="${HEYGEN_PYTHON:-}"
VENV_DIR="$SCRIPT_DIR/.venv"

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

if [ -z "${VIRTUAL_ENV:-}" ] && [ -x "$VENV_DIR/bin/python" ]; then
  PYTHON_BIN="$VENV_DIR/bin/python"
  export VIRTUAL_ENV="$VENV_DIR"
  export PATH="$VENV_DIR/bin:$PATH"
fi

if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
  echo "pip not found for $PYTHON_BIN. Run: $PYTHON_BIN -m ensurepip --upgrade"
  exit 1
fi

PIP_ARGS=()
PIP_LAST_OUTPUT=""
INSTALLED_PLAYWRIGHT=0

set_pip_args() {
  PIP_ARGS=(install)
  if [ -z "${VIRTUAL_ENV:-}" ]; then
    PIP_ARGS+=(--user)
  fi
}

pip_install() {
  local output rc
  set +e
  output=$("$PYTHON_BIN" -m pip "$@" 2>&1)
  rc=$?
  set -e
  PIP_LAST_OUTPUT="$output"
  return $rc
}

ensure_venv() {
  if [ -n "${VIRTUAL_ENV:-}" ]; then
    return
  fi
  if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi
  PYTHON_BIN="$VENV_DIR/bin/python"
  export VIRTUAL_ENV="$VENV_DIR"
  export PATH="$VENV_DIR/bin:$PATH"
  if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
    echo "pip not found in virtual environment."
    exit 1
  fi
  set_pip_args
}

install_if_missing() {
  local import_name="$1"
  local package_name="$2"

  if "$PYTHON_BIN" -c "import $import_name" >/dev/null 2>&1; then
    return
  fi

  echo "Installing $package_name..."
  if pip_install "${PIP_ARGS[@]}" "$package_name"; then
    if [ "$package_name" = "playwright" ]; then
      INSTALLED_PLAYWRIGHT=1
    fi
    return
  fi

  if echo "$PIP_LAST_OUTPUT" | grep -qi "externally-managed-environment\\|PEP 668"; then
    echo "System Python is externally managed; using a virtual environment..."
    ensure_venv
    if ! "$PYTHON_BIN" -c "import $import_name" >/dev/null 2>&1; then
      "$PYTHON_BIN" -m pip install "$package_name"
    fi
    if [ "$package_name" = "playwright" ]; then
      INSTALLED_PLAYWRIGHT=1
    fi
    return
  fi

  echo "$PIP_LAST_OUTPUT"
  exit 1
}

set_pip_args

install_if_missing "flask" "flask"
install_if_missing "playwright" "playwright"
if [ "$INSTALLED_PLAYWRIGHT" -eq 1 ]; then
  echo "Ensuring Playwright browsers are installed..."
  "$PYTHON_BIN" -m playwright install
fi

if [ ! -d "$PROFILE_DIR" ]; then
  echo "Chrome profile not found. Launching first-time login..."
  "$PYTHON_BIN" "Headless Test/setup_profile.py"
fi

"$PYTHON_BIN" "Headless Test/ui_server.py"
