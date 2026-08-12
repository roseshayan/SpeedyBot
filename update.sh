#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE_NAME="xui-bot.service"
APP_DIR="/root/SpeedyBot"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$APP_DIR/backups"
MAIN_BACKUP="$BACKUP_DIR/main.py.$STAMP"
DB_BACKUP="$BACKUP_DIR/speedping.db.$STAMP"

if [[ "${EUID}" -ne 0 ]]; then
  echo "[ERROR] Run update.sh as root." >&2
  exit 1
fi
if [[ ! -f "$SOURCE_DIR/main.py" ]]; then
  echo "[ERROR] main.py is missing next to update.sh." >&2
  exit 1
fi
if [[ ! -f "$APP_DIR/.env" ]]; then
  echo "[ERROR] Existing installation not found in $APP_DIR. Use install.sh for the first installation." >&2
  exit 1
fi

# Validate the new Python source before touching the running installation.
python3 -m py_compile "$SOURCE_DIR/main.py"
bash -n "$SOURCE_DIR/update.sh"

if [[ ! -x "$APP_DIR/.venv/bin/python3" ]]; then
  apt-get update
  apt-get install -y python3 python3-pip python3-venv
  python3 -m venv "$APP_DIR/.venv"
fi

"$APP_DIR/.venv/bin/python3" -m pip install --upgrade pip >/dev/null
if [[ -f "$SOURCE_DIR/requirements.txt" ]]; then
  "$APP_DIR/.venv/bin/python3" -m pip install -r "$SOURCE_DIR/requirements.txt"
else
  "$APP_DIR/.venv/bin/python3" -m pip install pyTelegramBotAPI requests
fi

mkdir -p "$BACKUP_DIR"
echo "[INFO] Stopping bot for a consistent SQLite backup..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true

if [[ -f "$APP_DIR/main.py" ]]; then
  cp "$APP_DIR/main.py" "$MAIN_BACKUP"
fi
if [[ -f "$APP_DIR/speedping.db" ]]; then
  cp "$APP_DIR/speedping.db" "$DB_BACKUP"
fi

if [[ "$SOURCE_DIR" != "$APP_DIR" ]]; then
  # Replace application source/docs/scripts but deliberately preserve runtime state:
  # .env, speedping.db, .venv and backups are never copied or removed.
  for file in main.py install.sh update.sh requirements.txt README.md README_FA.md CHANGELOG.md VERSION.txt .gitignore; do
    if [[ -f "$SOURCE_DIR/$file" ]]; then
      cp "$SOURCE_DIR/$file" "$APP_DIR/$file"
    fi
  done
  chmod +x "$APP_DIR/install.sh" "$APP_DIR/update.sh" 2>/dev/null || true
fi
"$APP_DIR/.venv/bin/python3" -m py_compile "$APP_DIR/main.py"

systemctl daemon-reload
systemctl restart "$SERVICE_NAME"
sleep 2

if systemctl is-active --quiet "$SERVICE_NAME"; then
  echo "[OK] SpeedPing updated successfully."
  echo "[OK] Database and .env were preserved."
  echo "[INFO] Backup directory: $BACKUP_DIR"
  systemctl --no-pager --full status "$SERVICE_NAME" || true
  exit 0
fi

echo "[ERROR] New version failed to start. Rolling main.py back..." >&2
journalctl -u "$SERVICE_NAME" -n 60 --no-pager || true
if [[ -f "$MAIN_BACKUP" ]]; then
  cp "$MAIN_BACKUP" "$APP_DIR/main.py"
  systemctl restart "$SERVICE_NAME" || true
  echo "[WARN] Previous main.py was restored. The database backup is at: $DB_BACKUP" >&2
fi
exit 1
