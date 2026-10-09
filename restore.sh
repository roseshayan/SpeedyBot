#!/usr/bin/env bash
set -Eeuo pipefail

# Locate SpeedyBot application root
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

# Detect Python executable
if [[ -f "$APP_DIR/.venv/bin/python" ]]; then
    PYTHON_BIN="$APP_DIR/.venv/bin/python"
elif [[ -f "$APP_DIR/venv/bin/python" ]]; then
    PYTHON_BIN="$APP_DIR/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    PYTHON_BIN="python"
fi

exec "$PYTHON_BIN" "$APP_DIR/restore.py" "$@"
