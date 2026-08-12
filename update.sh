#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE_NAME="${SPEEDYBOT_SERVICE_NAME:-xui-bot.service}"
APP_DIR="${SPEEDYBOT_APP_DIR:-/root/SpeedyBot}"
REPO_URL="${SPEEDYBOT_REPO_URL:-git@github.com:roseshayan/SpeedyBot.git}"
BRANCH="${SPEEDYBOT_BRANCH:-main}"
DEPLOY_KEY="${SPEEDYBOT_DEPLOY_KEY:-/root/.ssh/speedybot_deploy}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$APP_DIR/backups/$STAMP"
CURRENT_COMMIT_FILE="$APP_DIR/.deployed_commit"
TMP_DIR=""
FORCE=0
CHECK_ONLY=0

log()  { printf '[INFO] %s\n' "$*"; }
ok()   { printf '[OK] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*" >&2; }
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

cleanup() {
  if [[ -n "${TMP_DIR:-}" && -d "$TMP_DIR" ]]; then
    rm -rf "$TMP_DIR"
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

  --check   Only compare the deployed commit with GitHub.
  --force   Reinstall the latest commit even if already deployed.

Environment overrides:
  SPEEDYBOT_REPO_URL     Git repository URL (default: $REPO_URL)
  SPEEDYBOT_BRANCH       Branch to deploy (default: $BRANCH)
  SPEEDYBOT_DEPLOY_KEY   SSH deploy key (default: $DEPLOY_KEY)
  SPEEDYBOT_APP_DIR      App directory (default: $APP_DIR)
USAGE
      exit 0
      ;;
    *) fail "Unknown argument: $arg" ;;
  esac
done

[[ "${EUID}" -eq 0 ]] || fail "Run update.sh as root."
[[ -f "$APP_DIR/.env" ]] || fail "Existing installation not found in $APP_DIR. Run install.sh for the first installation."

if ! command -v git >/dev/null 2>&1; then
  log "Installing git..."
  apt-get update
  apt-get install -y git openssh-client
fi

# Private repository authentication. A repo-scoped, read-only Deploy Key is preferred.
GIT_ENV=()
if [[ "$REPO_URL" == git@github.com:* || "$REPO_URL" == ssh://git@github.com/* ]]; then
  [[ -f "$DEPLOY_KEY" ]] || fail "GitHub deploy key not found: $DEPLOY_KEY. Create a read-only Deploy Key for roseshayan/SpeedyBot first."
  chmod 600 "$DEPLOY_KEY"
  mkdir -p /root/.ssh
  chmod 700 /root/.ssh
  [[ -f /root/.ssh/known_hosts ]] || touch /root/.ssh/known_hosts
  chmod 600 /root/.ssh/known_hosts
  if ! ssh-keygen -F github.com -f /root/.ssh/known_hosts >/dev/null 2>&1; then
    fail "github.com is not in /root/.ssh/known_hosts. Run: ssh-keyscan github.com >> /root/.ssh/known_hosts"
  fi
  GIT_ENV=(env GIT_SSH_COMMAND="ssh -i $DEPLOY_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes")
fi

log "Checking GitHub repository: $REPO_URL ($BRANCH)"
REMOTE_LINE="$("${GIT_ENV[@]}" git ls-remote "$REPO_URL" "refs/heads/$BRANCH" 2>&1)" || fail "Cannot access GitHub repository. Git said: $REMOTE_LINE"
REMOTE_COMMIT="$(awk '{print $1}' <<<"$REMOTE_LINE")"
[[ "$REMOTE_COMMIT" =~ ^[0-9a-fA-F]{40}$ ]] || fail "Could not resolve the latest commit for branch $BRANCH."
CURRENT_COMMIT=""
[[ -f "$CURRENT_COMMIT_FILE" ]] && CURRENT_COMMIT="$(tr -d '[:space:]' < "$CURRENT_COMMIT_FILE")"

log "Deployed commit: ${CURRENT_COMMIT:-unknown}"
log "GitHub latest:   $REMOTE_COMMIT"

if [[ "$CHECK_ONLY" -eq 1 ]]; then
  if [[ "$CURRENT_COMMIT" == "$REMOTE_COMMIT" ]]; then
    ok "SpeedyBot is already up to date."
  else
    warn "A newer/different commit is available on GitHub."
  fi
  exit 0
fi

if [[ "$FORCE" -ne 1 && -n "$CURRENT_COMMIT" && "$CURRENT_COMMIT" == "$REMOTE_COMMIT" ]]; then
  ok "Already on the latest GitHub version. Nothing to do."
  exit 0
fi

TMP_DIR="$(mktemp -d /tmp/speedybot-update.XXXXXX)"
log "Downloading latest source from GitHub..."
"${GIT_ENV[@]}" git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP_DIR/repo" || fail "git clone failed."
SOURCE_DIR="$TMP_DIR/repo"
CLONED_COMMIT="$(git -C "$SOURCE_DIR" rev-parse HEAD)"
[[ "$CLONED_COMMIT" == "$REMOTE_COMMIT" ]] || warn "Remote moved during update; deploying cloned commit $CLONED_COMMIT."

[[ -f "$SOURCE_DIR/main.py" ]] || fail "main.py is missing from GitHub repository."
[[ -f "$SOURCE_DIR/update.sh" ]] || fail "update.sh is missing from GitHub repository."
python3 -m py_compile "$SOURCE_DIR/main.py" || fail "New main.py failed Python syntax validation."
bash -n "$SOURCE_DIR/update.sh" || fail "New update.sh failed shell syntax validation."
[[ ! -f "$SOURCE_DIR/install.sh" ]] || bash -n "$SOURCE_DIR/install.sh" || fail "New install.sh failed shell syntax validation."

if [[ ! -x "$APP_DIR/.venv/bin/python3" ]]; then
  log "Creating Python virtual environment..."
  apt-get update
  apt-get install -y python3 python3-pip python3-venv
  python3 -m venv "$APP_DIR/.venv"
fi

mkdir -p "$BACKUP_DIR"
log "Stopping $SERVICE_NAME for a consistent backup..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true

# Backup runtime state and currently deployed source. .env is backed up but never overwritten.
[[ -f "$APP_DIR/.env" ]] && cp -a "$APP_DIR/.env" "$BACKUP_DIR/.env"
[[ -f "$APP_DIR/speedping.db" ]] && cp -a "$APP_DIR/speedping.db" "$BACKUP_DIR/speedping.db"
[[ -f "$CURRENT_COMMIT_FILE" ]] && cp -a "$CURRENT_COMMIT_FILE" "$BACKUP_DIR/.deployed_commit"
for file in main.py install.sh update.sh requirements.txt README.md README_FA.md CHANGELOG.md VERSION.txt .gitignore; do
  [[ -f "$APP_DIR/$file" ]] && cp -a "$APP_DIR/$file" "$BACKUP_DIR/$file"
done

rollback() {
  warn "Update failed. Restoring previous version..."
  for file in main.py install.sh update.sh requirements.txt README.md README_FA.md CHANGELOG.md VERSION.txt .gitignore; do
    if [[ -f "$BACKUP_DIR/$file" ]]; then
      cp -a "$BACKUP_DIR/$file" "$APP_DIR/$file"
    else
      rm -f "$APP_DIR/$file"
    fi
  done
  [[ -f "$BACKUP_DIR/speedping.db" ]] && cp -a "$BACKUP_DIR/speedping.db" "$APP_DIR/speedping.db"
  if [[ -f "$BACKUP_DIR/.deployed_commit" ]]; then
    cp -a "$BACKUP_DIR/.deployed_commit" "$CURRENT_COMMIT_FILE"
  else
    rm -f "$CURRENT_COMMIT_FILE"
  fi
  chmod +x "$APP_DIR/install.sh" "$APP_DIR/update.sh" 2>/dev/null || true
  systemctl daemon-reload || true
  systemctl restart "$SERVICE_NAME" || true
  journalctl -u "$SERVICE_NAME" -n 80 --no-pager || true
  fail "Update rolled back. Backup: $BACKUP_DIR"
}

log "Installing Python dependencies..."
"$APP_DIR/.venv/bin/python3" -m pip install --upgrade pip >/dev/null || rollback
if [[ -f "$SOURCE_DIR/requirements.txt" ]]; then
  "$APP_DIR/.venv/bin/python3" -m pip install -r "$SOURCE_DIR/requirements.txt" || rollback
else
  "$APP_DIR/.venv/bin/python3" -m pip install pyTelegramBotAPI requests || rollback
fi

log "Deploying GitHub commit $CLONED_COMMIT..."
for file in main.py install.sh update.sh requirements.txt README.md README_FA.md CHANGELOG.md VERSION.txt .gitignore; do
  if [[ -f "$SOURCE_DIR/$file" ]]; then
    cp -a "$SOURCE_DIR/$file" "$APP_DIR/$file" || rollback
  else
    rm -f "$APP_DIR/$file"
  fi
done
chmod +x "$APP_DIR/install.sh" "$APP_DIR/update.sh" 2>/dev/null || true
printf '%s\n' "$CLONED_COMMIT" > "$CURRENT_COMMIT_FILE"
"$APP_DIR/.venv/bin/python3" -m py_compile "$APP_DIR/main.py" || rollback

systemctl daemon-reload || rollback
systemctl restart "$SERVICE_NAME" || rollback
sleep 3

if ! systemctl is-active --quiet "$SERVICE_NAME"; then
  rollback
fi

ok "SpeedyBot updated successfully from GitHub."
ok "Deployed commit: $CLONED_COMMIT"
ok ".env and speedping.db were preserved."
log "Backup: $BACKUP_DIR"
systemctl --no-pager --full status "$SERVICE_NAME" || true
