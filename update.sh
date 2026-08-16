#!/usr/bin/env bash
set -Eeuo pipefail

# Re-execute from /tmp so replacing update.sh during deployment can never break
# the currently running updater process.
if [[ "${SPEEDYBOT_UPDATER_REEXEC:-0}" != "1" ]]; then
  SELF="$(mktemp /tmp/speedybot-updater.XXXXXX.sh)"
  cp -- "$0" "$SELF"
  chmod 700 "$SELF"
  exec env SPEEDYBOT_UPDATER_REEXEC=1 "$SELF" "$@"
fi

SERVICE_NAME="${SPEEDYBOT_SERVICE_NAME:-xui-bot.service}"
APP_DIR="${SPEEDYBOT_APP_DIR:-/root/SpeedyBot}"
REPO_URL="${SPEEDYBOT_REPO_URL:-https://github.com/roseshayan/SpeedyBot.git}"
BRANCH="${SPEEDYBOT_BRANCH:-main}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$APP_DIR/backups/deploy-$STAMP"
CURRENT_COMMIT_FILE="$APP_DIR/.deployed_commit"
TMP_DIR=""
CHECK_ONLY=0
FORCE=0

info(){ printf '[INFO] %s\n' "$*"; }
ok(){ printf '[OK] %s\n' "$*"; }
warn(){ printf '[WARN] %s\n' "$*" >&2; }
fail(){ printf '[ERROR] %s\n' "$*" >&2; exit 1; }
cleanup(){
  [[ -z "${TMP_DIR:-}" || ! -d "$TMP_DIR" ]] || rm -rf "$TMP_DIR"
  [[ "$0" != /tmp/speedybot-updater.*.sh ]] || rm -f "$0" 2>/dev/null || true
}
trap cleanup EXIT

for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=1 ;;
    --force) FORCE=1 ;;
    -h|--help)
      cat <<'EOF'
Usage: ./update.sh [--check] [--force]
  --check  compare installed commit with GitHub without changing anything
  --force  deploy the current remote commit even if it matches installed state
EOF
      exit 0
      ;;
    *) fail "Unknown argument: $arg" ;;
  esac
done

[[ "$EUID" -eq 0 ]] || fail "Run update.sh as root."
[[ -f "$APP_DIR/.env" ]] || fail "Existing installation not found at $APP_DIR (.env is missing)."

if ! command -v git >/dev/null 2>&1 || ! command -v rsync >/dev/null 2>&1; then
  apt-get update
  apt-get install -y git ca-certificates rsync
fi

write_runner(){
  cat > "$APP_DIR/run.sh" <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
source "$APP_DIR/.env"
exec "$APP_DIR/.venv/bin/python3" "$APP_DIR/main.py"
EOF
  chmod 700 "$APP_DIR/run.sh"
}

# Runtime state is never copied from GitHub and never removed by --delete.
RSYNC_EXCLUDES=(
  --exclude '.git/'
  --exclude '.env'
  --exclude '.venv/'
  --exclude 'speedping.db'
  --exclude 'speedping.db-wal'
  --exclude 'speedping.db-shm'
  --exclude 'backups/'
  --exclude 'run.sh'
  --exclude '.deployed_commit'
)

info "Checking GitHub repository: $REPO_URL ($BRANCH)"
REMOTE_LINE="$(git ls-remote "$REPO_URL" "refs/heads/$BRANCH" 2>&1)" || fail "Cannot reach GitHub: $REMOTE_LINE"
REMOTE_COMMIT="$(awk 'NR==1{print $1}' <<<"$REMOTE_LINE")"
[[ "$REMOTE_COMMIT" =~ ^[0-9a-fA-F]{40}$ ]] || fail "Could not resolve branch $BRANCH."
CURRENT_COMMIT=""
[[ -f "$CURRENT_COMMIT_FILE" ]] && CURRENT_COMMIT="$(tr -d '[:space:]' < "$CURRENT_COMMIT_FILE")"
info "Installed: ${CURRENT_COMMIT:-unknown}"
info "GitHub:    $REMOTE_COMMIT"

if [[ "$CHECK_ONLY" -eq 1 ]]; then
  [[ "$CURRENT_COMMIT" == "$REMOTE_COMMIT" ]] && ok "Already up to date." || warn "A newer/different GitHub commit is available."
  exit 0
fi
if [[ "$FORCE" -ne 1 && -n "$CURRENT_COMMIT" && "$CURRENT_COMMIT" == "$REMOTE_COMMIT" ]]; then
  ok "Already on latest version."
  exit 0
fi

TMP_DIR="$(mktemp -d /tmp/speedybot-update.XXXXXX)"
SOURCE_DIR="$TMP_DIR/repo"
info "Cloning complete repository..."
git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$SOURCE_DIR" || fail "git clone failed."
CLONED_COMMIT="$(git -C "$SOURCE_DIR" rev-parse HEAD)"

if [[ "$FORCE" -ne 1 && -f "$APP_DIR/VERSION.txt" && -f "$SOURCE_DIR/VERSION.txt" ]]; then
  LOCAL_VERSION="$(grep -oE '^[0-9]+(\.[0-9]+){1,2}' "$APP_DIR/VERSION.txt" | head -1 || true)"
  REMOTE_VERSION="$(grep -oE '^[0-9]+(\.[0-9]+){1,2}' "$SOURCE_DIR/VERSION.txt" | head -1 || true)"
  if [[ -n "$LOCAL_VERSION" && -n "$REMOTE_VERSION" ]]; then
    LOWEST="$(printf '%s\n%s\n' "$LOCAL_VERSION" "$REMOTE_VERSION" | sort -V | head -1)"
    if [[ "$LOWEST" == "$REMOTE_VERSION" && "$LOCAL_VERSION" != "$REMOTE_VERSION" ]]; then
      fail "GitHub version $REMOTE_VERSION is older than installed $LOCAL_VERSION. Use --force only for an intentional downgrade."
    fi
  fi
fi

[[ -f "$SOURCE_DIR/main.py" ]] || fail "main.py is missing from the repository."
[[ -d "$SOURCE_DIR/speedybot" ]] || fail "speedybot application package is missing from the repository."

info "Validating downloaded project before downtime..."
python3 -m py_compile "$SOURCE_DIR/main.py" "$SOURCE_DIR"/speedybot/*.py || fail "Python syntax validation failed."
bash -n "$SOURCE_DIR/update.sh" || fail "update.sh syntax validation failed."
[[ ! -f "$SOURCE_DIR/install.sh" ]] || bash -n "$SOURCE_DIR/install.sh" || fail "install.sh syntax validation failed."

if [[ ! -x "$APP_DIR/.venv/bin/python3" ]]; then
  apt-get update
  apt-get install -y python3 python3-pip python3-venv
  python3 -m venv "$APP_DIR/.venv"
fi

info "Installing Python dependencies before downtime..."
"$APP_DIR/.venv/bin/python3" -m pip install --upgrade pip >/dev/null
if [[ -f "$SOURCE_DIR/requirements.txt" ]]; then
  "$APP_DIR/.venv/bin/python3" -m pip install -r "$SOURCE_DIR/requirements.txt" || fail "Dependency installation failed."
fi

mkdir -p "$BACKUP_DIR/app"
info "Stopping bot and creating a complete rollback backup..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true

# Consistent runtime backup.
for f in .env speedping.db speedping.db-wal speedping.db-shm .deployed_commit run.sh; do
  [[ ! -f "$APP_DIR/$f" ]] || cp -a "$APP_DIR/$f" "$BACKUP_DIR/$f"
done

# Backup the complete deployed repository while excluding mutable runtime data.
rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$APP_DIR/" "$BACKUP_DIR/app/"

rollback(){
  warn "Deployment failed; restoring the previous complete application..."
  systemctl stop "$SERVICE_NAME" 2>/dev/null || true

  rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$BACKUP_DIR/app/" "$APP_DIR/" || true
  for f in .env speedping.db speedping.db-wal speedping.db-shm .deployed_commit; do
    if [[ -f "$BACKUP_DIR/$f" ]]; then
      cp -a "$BACKUP_DIR/$f" "$APP_DIR/$f"
    elif [[ "$f" != "speedping.db" && "$f" != ".env" ]]; then
      rm -f "$APP_DIR/$f"
    fi
  done
  write_runner
  chmod +x "$APP_DIR/install.sh" "$APP_DIR/update.sh" 2>/dev/null || true
  systemctl daemon-reload || true
  systemctl restart "$SERVICE_NAME" || true
  sleep 2
  journalctl -u "$SERVICE_NAME" -n 100 --no-pager || true
  fail "Rollback completed. Backup: $BACKUP_DIR"
}

info "Synchronizing the complete repository to $APP_DIR..."
rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$SOURCE_DIR/" "$APP_DIR/" || rollback

chmod +x "$APP_DIR/install.sh" "$APP_DIR/update.sh" 2>/dev/null || true
printf '%s\n' "$CLONED_COMMIT" > "$CURRENT_COMMIT_FILE"
write_runner

info "Validating deployed application..."
"$APP_DIR/.venv/bin/python3" -m py_compile "$APP_DIR/main.py" "$APP_DIR"/speedybot/*.py || rollback
bash -n "$APP_DIR/update.sh" || rollback
[[ ! -f "$APP_DIR/install.sh" ]] || bash -n "$APP_DIR/install.sh" || rollback

systemctl daemon-reload || rollback
systemctl restart "$SERVICE_NAME" || rollback
sleep 5
systemctl is-active --quiet "$SERVICE_NAME" || rollback

# Catch immediate crash loops, not just a single successful start.
sleep 3
systemctl is-active --quiet "$SERVICE_NAME" || rollback
RESTARTS="$(systemctl show "$SERVICE_NAME" -p NRestarts --value 2>/dev/null || echo 0)"
if [[ "$RESTARTS" =~ ^[0-9]+$ && "$RESTARTS" -ge 3 ]]; then
  warn "Service restarted $RESTARTS times immediately after deployment."
  rollback
fi

ok "SpeedyBot complete-project update finished successfully."
ok "Commit: $CLONED_COMMIT"
ok ".env, SQLite runtime data, virtualenv and backups were preserved."
info "Rollback backup: $BACKUP_DIR"
systemctl --no-pager --full status "$SERVICE_NAME" || true
