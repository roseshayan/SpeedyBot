#!/usr/bin/env bash
set -Eeuo pipefail

# Keep this process independent from the updater file being replaced.
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
STAMP="$(date +%Y%m%d-%H%M%S)-$$"
BACKUP_DIR="$APP_DIR/backups/deploy-$STAMP"
CURRENT_COMMIT_FILE="$APP_DIR/.deployed_commit"
TMP_DIR=""
STAGED_VENV=""
DEPLOYED=0
CHECK_ONLY=0
FORCE=0

info(){ printf '[INFO] %s\n' "$*"; }
ok(){ printf '[OK] %s\n' "$*"; }
warn(){ printf '[WARN] %s\n' "$*" >&2; }
fail(){ printf '[ERROR] %s\n' "$*" >&2; exit 1; }
cleanup(){
  [[ -z "${TMP_DIR:-}" || ! -d "$TMP_DIR" ]] || rm -rf -- "$TMP_DIR"
  if [[ "$DEPLOYED" -eq 0 && -n "$STAGED_VENV" && -d "$STAGED_VENV" && "$(readlink "$APP_DIR/.venv" 2>/dev/null || true)" != "$STAGED_VENV" ]]; then
    rm -rf -- "$STAGED_VENV"
  fi
  [[ "$0" != /tmp/speedybot-updater.*.sh ]] || rm -f -- "$0" 2>/dev/null || true
}
trap cleanup EXIT

for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=1 ;;
    --force) FORCE=1 ;;
    -h|--help)
      cat <<'EOF'
Usage: ./update.sh [--check] [--force]
  --check  compare installed commit with GitHub without deploying
  --force  deploy even if the commit is unchanged or the version is older
Environment: SPEEDYBOT_PYTHON selects Python 3.11+ for the staged virtualenv.
EOF
      exit 0
      ;;
    *) fail "Unknown argument: $arg" ;;
  esac
done

[[ "$EUID" -eq 0 ]] || fail "Run update.sh as root."
[[ "$APP_DIR" == /* && "$APP_DIR" != "/" ]] || fail "SPEEDYBOT_APP_DIR must be an absolute application directory, not /."
[[ -f "$APP_DIR/.env" ]] || fail "Existing installation not found at $APP_DIR (.env is missing)."

if ! command -v git >/dev/null 2>&1 || ! command -v rsync >/dev/null 2>&1; then
  apt-get update
  apt-get install -y git ca-certificates rsync
fi

write_runner(){
  cat > "$APP_DIR/run.sh" <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
cd "$APP_DIR"
exec "$APP_DIR/.venv/bin/python3" "$APP_DIR/main.py"
EOF
  chmod 700 "$APP_DIR/run.sh"
}

# Source synchronization never touches secrets, databases or Python environments.
RSYNC_EXCLUDES=(
  --exclude '.git/'
  --exclude '.env'
  --exclude '.venv'
  --exclude '.venvs/'
  --exclude 'speedping.db'
  --exclude 'speedping.db-wal'
  --exclude 'speedping.db-shm'
  --exclude 'backups/'
  --exclude 'run.sh'
  --exclude '.deployed_commit'
  --exclude '__pycache__/'
  --exclude '*.log'
)

info "Checking GitHub repository: $REPO_URL ($BRANCH)"
REMOTE_LINE="$(git ls-remote "$REPO_URL" "refs/heads/$BRANCH" 2>&1)" || fail "Cannot reach GitHub: $REMOTE_LINE"
REMOTE_COMMIT="$(awk 'NR==1{print $1}' <<<"$REMOTE_LINE")"
[[ "$REMOTE_COMMIT" =~ ^[0-9a-fA-F]{40}$ ]] || fail "Could not resolve branch $BRANCH."
CURRENT_COMMIT=""
[[ ! -f "$CURRENT_COMMIT_FILE" ]] || CURRENT_COMMIT="$(tr -d '[:space:]' < "$CURRENT_COMMIT_FILE")"
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
[[ "$CLONED_COMMIT" == "$REMOTE_COMMIT" ]] || fail "The remote branch changed during download. Retry to deploy a verified commit."

if [[ "$FORCE" -ne 1 && -f "$APP_DIR/VERSION.txt" && -f "$SOURCE_DIR/VERSION.txt" ]]; then
  LOCAL_VERSION="$(grep -oE '^[0-9]+(\.[0-9]+){1,2}' "$APP_DIR/VERSION.txt" | head -1 || true)"
  REMOTE_VERSION="$(grep -oE '^[0-9]+(\.[0-9]+){1,2}' "$SOURCE_DIR/VERSION.txt" | head -1 || true)"
  if [[ -n "$LOCAL_VERSION" && -n "$REMOTE_VERSION" ]]; then
    LOWEST="$(printf '%s\n%s\n' "$LOCAL_VERSION" "$REMOTE_VERSION" | sort -V | head -1)"
    if [[ "$LOWEST" == "$REMOTE_VERSION" && "$LOCAL_VERSION" != "$REMOTE_VERSION" ]]; then
      fail "GitHub version $REMOTE_VERSION is older than installed $LOCAL_VERSION. Use --force for an intentional downgrade."
    fi
  fi
fi

[[ -f "$SOURCE_DIR/main.py" && -d "$SOURCE_DIR/speedybot" && -f "$SOURCE_DIR/requirements.txt" ]] || fail "The repository has no complete SpeedyBot application."
PYTHON_BIN="${SPEEDYBOT_PYTHON:-python3}"
# Prefer an existing supported interpreter when the system default is older.
if [[ -z "${SPEEDYBOT_PYTHON:-}" && -x "$APP_DIR/.venv/bin/python3" ]]; then
  PYTHON_BIN="$APP_DIR/.venv/bin/python3"
fi
"$PYTHON_BIN" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || fail "Python 3.11+ is required. Set SPEEDYBOT_PYTHON to a supported interpreter; the running bot was not changed."

info "Preparing dependencies in an isolated virtualenv before downtime..."
# Keep this directory fixed: virtualenv scripts embed absolute paths.
mkdir -p "$APP_DIR/.venvs"
STAGED_VENV="$APP_DIR/.venvs/$STAMP"
"$PYTHON_BIN" -m venv "$STAGED_VENV" || fail "Cannot create staged virtualenv. Install the matching python3-venv package."
"$STAGED_VENV/bin/python3" -m pip install --upgrade pip >/dev/null
"$STAGED_VENV/bin/python3" -m pip install -r "$SOURCE_DIR/requirements.txt"
"$STAGED_VENV/bin/python3" -m pip check

info "Validating downloaded project before downtime..."
(
  cd "$SOURCE_DIR"
  "$STAGED_VENV/bin/python3" -m compileall -q main.py restore.py speedybot tests || exit 1
  "$STAGED_VENV/bin/python3" -m unittest discover -s tests -q || exit 1
  "$STAGED_VENV/bin/python3" -c "from pathlib import Path; import speedybot; assert speedybot.VERSION == Path('VERSION.txt').read_text().strip()" || exit 1
  for script in install.sh update.sh restore.sh; do bash -n "$script" || exit 1; done
  bash tests/test_update_shell.sh || exit 1
) || fail "Release validation failed; the running application and its dependencies were not changed."

mkdir -p "$BACKUP_DIR/app"
chmod 700 "$BACKUP_DIR"
info "Stopping bot and creating a rollback backup..."
systemctl stop "$SERVICE_NAME" || fail "Cannot stop the service safely. Deployment cancelled."
backup_previous(){
  for f in .env speedping.db speedping.db-wal speedping.db-shm .deployed_commit run.sh; do
    [[ ! -f "$APP_DIR/$f" ]] || cp -a "$APP_DIR/$f" "$BACKUP_DIR/$f" || return 1
  done
  rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$APP_DIR/" "$BACKUP_DIR/app/"
}
if ! backup_previous; then
  systemctl restart "$SERVICE_NAME" || true
  fail "Backup failed; the original application was kept and restart was attempted."
fi

rollback(){
  trap - ERR
  set +e
  warn "Deployment failed; restoring application, data and previous dependencies..."
  systemctl stop "$SERVICE_NAME"
  rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$BACKUP_DIR/app/" "$APP_DIR/"
  for f in .env speedping.db speedping.db-wal speedping.db-shm .deployed_commit run.sh; do
    if [[ -f "$BACKUP_DIR/$f" ]]; then
      cp -a "$BACKUP_DIR/$f" "$APP_DIR/$f"
    elif [[ "$f" != 'speedping.db' && "$f" != '.env' ]]; then
      rm -f -- "$APP_DIR/$f"
    fi
  done
  if [[ -L "$APP_DIR/.venv" && "$(readlink "$APP_DIR/.venv")" == "$STAGED_VENV" ]]; then
    rm -f -- "$APP_DIR/.venv"
  fi
  if [[ -e "$BACKUP_DIR/venv" || -L "$BACKUP_DIR/venv" ]]; then
    mv -- "$BACKUP_DIR/venv" "$APP_DIR/.venv"
  fi
  systemctl daemon-reload
  systemctl restart "$SERVICE_NAME"
  journalctl -u "$SERVICE_NAME" -n 50 --no-pager
  fail "Rollback attempted. Inspect service status. Backup: $BACKUP_DIR"
}
trap rollback ERR

# Move the directory or symlink itself. Existing symlink targets remain fixed.
if [[ -e "$APP_DIR/.venv" || -L "$APP_DIR/.venv" ]]; then
  mv -- "$APP_DIR/.venv" "$BACKUP_DIR/venv"
fi
ln -s -- "$STAGED_VENV" "$APP_DIR/.venv"
info "Synchronizing complete repository..."
rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$SOURCE_DIR/" "$APP_DIR/"
chmod +x "$APP_DIR/install.sh" "$APP_DIR/update.sh" "$APP_DIR/restore.sh"
printf '%s\n' "$CLONED_COMMIT" > "$CURRENT_COMMIT_FILE"
write_runner
systemctl daemon-reload
systemctl restart "$SERVICE_NAME"
sleep 5
systemctl is-active --quiet "$SERVICE_NAME" || rollback
sleep 3
systemctl is-active --quiet "$SERVICE_NAME" || rollback
RESTARTS="$(systemctl show "$SERVICE_NAME" -p NRestarts --value 2>/dev/null || echo 0)"
if [[ "$RESTARTS" =~ ^[0-9]+$ && "$RESTARTS" -ge 3 ]]; then
  warn "Service restarted $RESTARTS times immediately after deployment."
  rollback
fi
DEPLOYED=1
trap - ERR
ok "SpeedyBot update completed: $CLONED_COMMIT"
info "Rollback backup (including previous virtualenv): $BACKUP_DIR"
info "Old .venvs entries are retained for rollback; remove them only after verifying the release."
systemctl --no-pager --full status "$SERVICE_NAME" || true
