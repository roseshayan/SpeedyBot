#!/usr/bin/env bash
set -Eeuo pipefail

# Always execute from a temporary copy. This makes it safe to replace
# /root/SpeedyBot/update.sh while an update is running.
if [[ "${SPEEDYBOT_UPDATER_REEXEC:-0}" != "1" ]]; then
  RUNNER="$(mktemp /tmp/speedybot-updater.XXXXXX.sh)"
  cp -- "$0" "$RUNNER"
  chmod 700 "$RUNNER"
  exec env SPEEDYBOT_UPDATER_REEXEC=1 SPEEDYBOT_ORIGINAL_UPDATER="$0" "$RUNNER" "$@"
fi

SERVICE_NAME="${SPEEDYBOT_SERVICE_NAME:-xui-bot.service}"
APP_DIR="${SPEEDYBOT_APP_DIR:-/root/SpeedyBot}"
REPO_URL="${SPEEDYBOT_REPO_URL:-https://github.com/roseshayan/SpeedyBot.git}"
BRANCH="${SPEEDYBOT_BRANCH:-main}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$APP_DIR/backups/$STAMP"
CURRENT_COMMIT_FILE="$APP_DIR/.deployed_commit"
TMP_DIR=""
FORCE=0
CHECK_ONLY=0
SERVICE_WAS_ACTIVE=0

log()  { printf '[INFO] %s\n' "$*"; }
ok()   { printf '[OK] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*" >&2; }
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

cleanup() {
  [[ -n "${TMP_DIR:-}" && -d "$TMP_DIR" ]] && rm -rf "$TMP_DIR"
  if [[ -n "${RUNNER:-}" && -f "$RUNNER" ]]; then rm -f "$RUNNER"; fi
  if [[ "${SPEEDYBOT_UPDATER_REEXEC:-0}" == "1" && "$0" == /tmp/speedybot-updater.*.sh ]]; then
    rm -f "$0" 2>/dev/null || true
  fi
}
trap cleanup EXIT

for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --check) CHECK_ONLY=1 ;;
    -h|--help)
      cat <<USAGE
Usage: ./update.sh [--check] [--force]

  --check   Only check whether GitHub has a different commit.
  --force   Reinstall the current GitHub commit even if already deployed.

Environment overrides:
  SPEEDYBOT_REPO_URL   Git URL (default: $REPO_URL)
  SPEEDYBOT_BRANCH     Branch (default: $BRANCH)
  SPEEDYBOT_APP_DIR    App directory (default: $APP_DIR)
USAGE
      exit 0
      ;;
    *) fail "Unknown argument: $arg" ;;
  esac
done

[[ "$EUID" -eq 0 ]] || fail "Run update.sh as root."
[[ -f "$APP_DIR/.env" ]] || fail "Existing installation not found in $APP_DIR (.env is missing)."

if ! command -v git >/dev/null 2>&1; then
  log "Installing git..."
  apt-get update
  apt-get install -y git ca-certificates
fi

log "Checking GitHub repository: $REPO_URL ($BRANCH)"
REMOTE_LINE="$(git ls-remote "$REPO_URL" "refs/heads/$BRANCH" 2>&1)" || fail "Cannot access GitHub: $REMOTE_LINE"
REMOTE_COMMIT="$(awk 'NR==1{print $1}' <<<"$REMOTE_LINE")"
[[ "$REMOTE_COMMIT" =~ ^[0-9a-fA-F]{40}$ ]] || fail "Could not resolve branch $BRANCH."

CURRENT_COMMIT=""
if [[ -f "$CURRENT_COMMIT_FILE" ]]; then
  CURRENT_COMMIT="$(tr -d '[:space:]' < "$CURRENT_COMMIT_FILE")"
fi

log "Deployed commit: ${CURRENT_COMMIT:-unknown}"
log "GitHub latest:   $REMOTE_COMMIT"

if [[ "$CHECK_ONLY" -eq 1 ]]; then
  if [[ "$CURRENT_COMMIT" == "$REMOTE_COMMIT" ]]; then
    ok "SpeedyBot is up to date."
  else
    warn "A different commit is available on GitHub."
  fi
  exit 0
fi

if [[ "$FORCE" -ne 1 && -n "$CURRENT_COMMIT" && "$CURRENT_COMMIT" == "$REMOTE_COMMIT" ]]; then
  ok "Already on the latest GitHub commit. Nothing to do."
  exit 0
fi

TMP_DIR="$(mktemp -d /tmp/speedybot-update.XXXXXX)"
SOURCE_DIR="$TMP_DIR/repo"
log "Downloading latest source..."
git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$SOURCE_DIR" || fail "git clone failed."
CLONED_COMMIT="$(git -C "$SOURCE_DIR" rev-parse HEAD)"

[[ -f "$SOURCE_DIR/main.py" ]] || fail "main.py is missing in GitHub."
[[ -f "$SOURCE_DIR/update.sh" ]] || fail "update.sh is missing in GitHub."

log "Validating downloaded files before touching the running bot..."
python3 -m py_compile "$SOURCE_DIR/main.py" || fail "New main.py has a Python syntax error."
bash -n "$SOURCE_DIR/update.sh" || fail "New update.sh has a shell syntax error."
if [[ -f "$SOURCE_DIR/install.sh" ]]; then
  bash -n "$SOURCE_DIR/install.sh" || fail "New install.sh has a shell syntax error."
fi

if [[ ! -x "$APP_DIR/.venv/bin/python3" ]]; then
  log "Creating Python virtual environment..."
  apt-get update
  apt-get install -y python3 python3-pip python3-venv
  python3 -m venv "$APP_DIR/.venv"
fi

# Install dependencies before stopping the bot to minimize downtime.
log "Installing/updating Python dependencies..."
"$APP_DIR/.venv/bin/python3" -m pip install --upgrade pip >/dev/null
if [[ -f "$SOURCE_DIR/requirements.txt" ]]; then
  "$APP_DIR/.venv/bin/python3" -m pip install -r "$SOURCE_DIR/requirements.txt"
else
  "$APP_DIR/.venv/bin/python3" -m pip install pyTelegramBotAPI requests
fi

mkdir -p "$BACKUP_DIR"
if systemctl is-active --quiet "$SERVICE_NAME"; then SERVICE_WAS_ACTIVE=1; fi

log "Stopping $SERVICE_NAME for a consistent SQLite backup..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true

# Back up runtime state and previous application files.
[[ -f "$APP_DIR/.env" ]] && cp -a "$APP_DIR/.env" "$BACKUP_DIR/.env"
[[ -f "$APP_DIR/speedping.db" ]] && cp -a "$APP_DIR/speedping.db" "$BACKUP_DIR/speedping.db"
[[ -f "$APP_DIR/speedping.db-wal" ]] && cp -a "$APP_DIR/speedping.db-wal" "$BACKUP_DIR/speedping.db-wal"
[[ -f "$APP_DIR/speedping.db-shm" ]] && cp -a "$APP_DIR/speedping.db-shm" "$BACKUP_DIR/speedping.db-shm"
[[ -f "$CURRENT_COMMIT_FILE" ]] && cp -a "$CURRENT_COMMIT_FILE" "$BACKUP_DIR/.deployed_commit"

FILES=(main.py install.sh update.sh requirements.txt README.md README_FA.md CHANGELOG.md VERSION.txt MIGRATION_NOTES.md .gitignore)
for file in "${FILES[@]}"; do
  [[ -f "$APP_DIR/$file" ]] && cp -a "$APP_DIR/$file" "$BACKUP_DIR/$file"
done

rollback() {
  warn "Deployment failed; restoring the previous application and database..."
  systemctl stop "$SERVICE_NAME" 2>/dev/null || true

  for file in "${FILES[@]}"; do
    if [[ -f "$BACKUP_DIR/$file" ]]; then
      cp -a "$BACKUP_DIR/$file" "$APP_DIR/$file"
    else
      rm -f "$APP_DIR/$file"
    fi
  done

  if [[ -f "$BACKUP_DIR/speedping.db" ]]; then
    cp -a "$BACKUP_DIR/speedping.db" "$APP_DIR/speedping.db"
    [[ -f "$BACKUP_DIR/speedping.db-wal" ]] && cp -a "$BACKUP_DIR/speedping.db-wal" "$APP_DIR/speedping.db-wal" || rm -f "$APP_DIR/speedping.db-wal"
    [[ -f "$BACKUP_DIR/speedping.db-shm" ]] && cp -a "$BACKUP_DIR/speedping.db-shm" "$APP_DIR/speedping.db-shm" || rm -f "$APP_DIR/speedping.db-shm"
  fi

  if [[ -f "$BACKUP_DIR/.deployed_commit" ]]; then
    cp -a "$BACKUP_DIR/.deployed_commit" "$CURRENT_COMMIT_FILE"
  else
    rm -f "$CURRENT_COMMIT_FILE"
  fi

  chmod +x "$APP_DIR/install.sh" "$APP_DIR/update.sh" 2>/dev/null || true
  systemctl daemon-reload || true
  systemctl restart "$SERVICE_NAME" || true
  sleep 2
  journalctl -u "$SERVICE_NAME" -n 80 --no-pager || true
  fail "Update rolled back. Backup directory: $BACKUP_DIR"
}

log "Deploying GitHub commit $CLONED_COMMIT..."
for file in "${FILES[@]}"; do
  if [[ -f "$SOURCE_DIR/$file" ]]; then
    cp -a "$SOURCE_DIR/$file" "$APP_DIR/$file" || rollback
  fi
done
chmod +x "$APP_DIR/install.sh" "$APP_DIR/update.sh" 2>/dev/null || true
printf '%s\n' "$CLONED_COMMIT" > "$CURRENT_COMMIT_FILE"

"$APP_DIR/.venv/bin/python3" -m py_compile "$APP_DIR/main.py" || rollback

systemctl daemon-reload || rollback
log "Starting $SERVICE_NAME..."
systemctl restart "$SERVICE_NAME" || rollback

# Health check: it must stay active and must not enter a rapid restart loop.
RESTARTS_BEFORE="$(systemctl show "$SERVICE_NAME" -p NRestarts --value 2>/dev/null || echo 0)"
sleep 5
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
  rollback
fi
RESTARTS_AFTER="$(systemctl show "$SERVICE_NAME" -p NRestarts --value 2>/dev/null || echo 0)"
if [[ "$RESTARTS_AFTER" =~ ^[0-9]+$ && "$RESTARTS_BEFORE" =~ ^[0-9]+$ ]] && (( RESTARTS_AFTER - RESTARTS_BEFORE >= 2 )); then
  warn "Service entered a rapid restart loop."
  rollback
fi

ok "SpeedyBot updated successfully from GitHub."
ok "Deployed commit: $CLONED_COMMIT"
ok ".env and speedping.db were preserved."
log "Backup directory: $BACKUP_DIR"
systemctl --no-pager --full status "$SERVICE_NAME" || true
