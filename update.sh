#!/usr/bin/env bash
set -Eeuo pipefail

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
cleanup(){ [[ -z "${TMP_DIR:-}" || ! -d "$TMP_DIR" ]] || rm -rf "$TMP_DIR"; }
trap cleanup EXIT

for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=1 ;;
    --force) FORCE=1 ;;
    -h|--help)
      cat <<USAGE
Usage: ./update.sh [--check] [--force]
  --check  only check whether GitHub has a different commit
  --force  reinstall latest main even if commit is unchanged
USAGE
      exit 0 ;;
    *) fail "Unknown argument: $arg" ;;
  esac
done

[[ "$EUID" -eq 0 ]] || fail "Run update.sh as root."
[[ -f "$APP_DIR/.env" ]] || fail "Existing installation not found at $APP_DIR (.env is missing)."

if ! command -v git >/dev/null 2>&1; then
  apt-get update
  apt-get install -y git ca-certificates
fi

info "Checking public GitHub repository ($BRANCH)..."
REMOTE_LINE="$(git ls-remote "$REPO_URL" "refs/heads/$BRANCH" 2>&1)" || fail "Cannot reach GitHub: $REMOTE_LINE"
REMOTE_COMMIT="$(awk '{print $1}' <<<"$REMOTE_LINE")"
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
info "Cloning latest SpeedyBot from GitHub..."
git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP_DIR/repo" || fail "git clone failed."
SOURCE_DIR="$TMP_DIR/repo"
CLONED_COMMIT="$(git -C "$SOURCE_DIR" rev-parse HEAD)"

# Refuse accidental downgrades (for example when a freshly uploaded server build is newer than GitHub).
if [[ "$FORCE" -ne 1 && -f "$APP_DIR/VERSION.txt" && -f "$SOURCE_DIR/VERSION.txt" ]]; then
  LOCAL_VERSION="$(grep -oE '^[0-9]+(\.[0-9]+){1,2}' "$APP_DIR/VERSION.txt" | head -1 || true)"
  REMOTE_VERSION="$(grep -oE '^[0-9]+(\.[0-9]+){1,2}' "$SOURCE_DIR/VERSION.txt" | head -1 || true)"
  if [[ -n "$LOCAL_VERSION" && -n "$REMOTE_VERSION" ]]; then
    LOWEST="$(printf '%s\n%s\n' "$LOCAL_VERSION" "$REMOTE_VERSION" | sort -V | head -1)"
    if [[ "$LOWEST" == "$REMOTE_VERSION" && "$LOCAL_VERSION" != "$REMOTE_VERSION" ]]; then
      fail "GitHub version $REMOTE_VERSION is older than installed $LOCAL_VERSION. Push the newer source to GitHub first, or use --force only if a downgrade is intentional."
    fi
  fi
fi

[[ -f "$SOURCE_DIR/main.py" ]] || fail "main.py missing in repository."
python3 -m py_compile "$SOURCE_DIR/main.py" || fail "New main.py has a syntax error."
bash -n "$SOURCE_DIR/update.sh" || fail "New update.sh has a syntax error."
[[ ! -f "$SOURCE_DIR/install.sh" ]] || bash -n "$SOURCE_DIR/install.sh" || fail "New install.sh has a syntax error."

if [[ ! -x "$APP_DIR/.venv/bin/python3" ]]; then
  apt-get update
  apt-get install -y python3 python3-pip python3-venv
  python3 -m venv "$APP_DIR/.venv"
fi

mkdir -p "$BACKUP_DIR"
info "Stopping bot and making a consistent backup..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
[[ -f "$APP_DIR/.env" ]] && cp -a "$APP_DIR/.env" "$BACKUP_DIR/.env"
[[ -f "$APP_DIR/speedping.db" ]] && cp -a "$APP_DIR/speedping.db" "$BACKUP_DIR/speedping.db"
[[ -f "$CURRENT_COMMIT_FILE" ]] && cp -a "$CURRENT_COMMIT_FILE" "$BACKUP_DIR/.deployed_commit"
FILES=(main.py install.sh update.sh requirements.txt README.md README_FA.md CHANGELOG.md VERSION.txt .gitignore)
for f in "${FILES[@]}"; do [[ ! -f "$APP_DIR/$f" ]] || cp -a "$APP_DIR/$f" "$BACKUP_DIR/$f"; done

rollback(){
  warn "Deployment failed; restoring previous source/database..."
  for f in "${FILES[@]}"; do
    if [[ -f "$BACKUP_DIR/$f" ]]; then cp -a "$BACKUP_DIR/$f" "$APP_DIR/$f"; else rm -f "$APP_DIR/$f"; fi
  done
  [[ ! -f "$BACKUP_DIR/speedping.db" ]] || cp -a "$BACKUP_DIR/speedping.db" "$APP_DIR/speedping.db"
  if [[ -f "$BACKUP_DIR/.deployed_commit" ]]; then cp -a "$BACKUP_DIR/.deployed_commit" "$CURRENT_COMMIT_FILE"; else rm -f "$CURRENT_COMMIT_FILE"; fi
  chmod +x "$APP_DIR/install.sh" "$APP_DIR/update.sh" 2>/dev/null || true
  systemctl daemon-reload || true
  systemctl restart "$SERVICE_NAME" || true
  journalctl -u "$SERVICE_NAME" -n 80 --no-pager || true
  fail "Rollback completed. Backup: $BACKUP_DIR"
}

info "Installing Python dependencies..."
"$APP_DIR/.venv/bin/python3" -m pip install --upgrade pip >/dev/null || rollback
if [[ -f "$SOURCE_DIR/requirements.txt" ]]; then
  "$APP_DIR/.venv/bin/python3" -m pip install -r "$SOURCE_DIR/requirements.txt" || rollback
else
  "$APP_DIR/.venv/bin/python3" -m pip install pyTelegramBotAPI requests 'qrcode[pil]' || rollback
fi

info "Deploying commit $CLONED_COMMIT..."
for f in "${FILES[@]}"; do
  if [[ -f "$SOURCE_DIR/$f" ]]; then cp -a "$SOURCE_DIR/$f" "$APP_DIR/$f" || rollback; else rm -f "$APP_DIR/$f"; fi
done
chmod +x "$APP_DIR/install.sh" "$APP_DIR/update.sh" 2>/dev/null || true
printf '%s\n' "$CLONED_COMMIT" > "$CURRENT_COMMIT_FILE"
"$APP_DIR/.venv/bin/python3" -m py_compile "$APP_DIR/main.py" || rollback
systemctl daemon-reload || rollback
systemctl restart "$SERVICE_NAME" || rollback
sleep 3
systemctl is-active --quiet "$SERVICE_NAME" || rollback

ok "SpeedyBot updated from GitHub successfully."
ok "Commit: $CLONED_COMMIT"
ok ".env and speedping.db preserved."
info "Backup: $BACKUP_DIR"
systemctl --no-pager --full status "$SERVICE_NAME" || true
