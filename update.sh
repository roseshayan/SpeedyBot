#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${SPEEDYBOT_UPDATER_REEXEC:-0}" != "1" ]]; then
  SELF="$(mktemp /tmp/speedybot-updater.XXXXXX.sh)"
  cp -- "$0" "$SELF"; chmod 700 "$SELF"
  exec env SPEEDYBOT_UPDATER_REEXEC=1 "$SELF" "$@"
fi

SERVICE_NAME="${SPEEDYBOT_SERVICE_NAME:-xui-bot.service}"
APP_DIR="${SPEEDYBOT_APP_DIR:-/root/SpeedyBot}"
REPO_URL="${SPEEDYBOT_REPO_URL:-https://github.com/roseshayan/SpeedyBot.git}"
BRANCH="${SPEEDYBOT_BRANCH:-main}"
STAMP="$(date +%Y%m%d-%H%M%S)"; BACKUP_DIR="$APP_DIR/backups/deploy-$STAMP"; CURRENT_COMMIT_FILE="$APP_DIR/.deployed_commit"
TMP_DIR=""; CHECK_ONLY=0; FORCE=0
FILES=(main.py app.py install.sh update.sh requirements.txt README.md README_FA.md CHANGELOG.md VERSION.txt MIGRATION_NOTES.md RELEASE_NOTES_v4.0.0.md .gitignore)
info(){ printf '[INFO] %s\n' "$*"; }; ok(){ printf '[OK] %s\n' "$*"; }; warn(){ printf '[WARN] %s\n' "$*" >&2; }; fail(){ printf '[ERROR] %s\n' "$*" >&2; exit 1; }
cleanup(){ [[ -z "${TMP_DIR:-}" || ! -d "$TMP_DIR" ]] || rm -rf "$TMP_DIR"; [[ "$0" != /tmp/speedybot-updater.*.sh ]] || rm -f "$0" 2>/dev/null || true; }; trap cleanup EXIT
for arg in "$@"; do case "$arg" in --check) CHECK_ONLY=1;; --force) FORCE=1;; -h|--help) echo 'Usage: ./update.sh [--check] [--force]'; exit 0;; *) fail "Unknown argument: $arg";; esac; done
[[ "$EUID" -eq 0 ]] || fail 'Run update.sh as root.'
[[ -f "$APP_DIR/.env" ]] || fail "Existing installation not found at $APP_DIR (.env is missing)."
command -v git >/dev/null 2>&1 || { apt-get update; apt-get install -y git ca-certificates; }

write_runner(){
  local target="$APP_DIR/main.py"; [[ -f "$APP_DIR/app.py" ]] && target="$APP_DIR/app.py"
  cat > "$APP_DIR/run.sh" <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
source "$APP_DIR/.env"
exec "$APP_DIR/.venv/bin/python3" "$target"
EOF
  chmod 700 "$APP_DIR/run.sh"
}

info "Checking public GitHub repository ($BRANCH)..."
REMOTE_LINE="$(git ls-remote "$REPO_URL" "refs/heads/$BRANCH" 2>&1)" || fail "Cannot reach GitHub: $REMOTE_LINE"
REMOTE_COMMIT="$(awk 'NR==1{print $1}' <<<"$REMOTE_LINE")"; [[ "$REMOTE_COMMIT" =~ ^[0-9a-fA-F]{40}$ ]] || fail "Could not resolve branch $BRANCH."
CURRENT_COMMIT=""; [[ -f "$CURRENT_COMMIT_FILE" ]] && CURRENT_COMMIT="$(tr -d '[:space:]' < "$CURRENT_COMMIT_FILE")"
info "Installed: ${CURRENT_COMMIT:-unknown}"; info "GitHub:    $REMOTE_COMMIT"
if [[ "$CHECK_ONLY" -eq 1 ]]; then [[ "$CURRENT_COMMIT" == "$REMOTE_COMMIT" ]] && ok 'Already up to date.' || warn 'A newer/different GitHub commit is available.'; exit 0; fi
if [[ "$FORCE" -ne 1 && -n "$CURRENT_COMMIT" && "$CURRENT_COMMIT" == "$REMOTE_COMMIT" ]]; then ok 'Already on latest version.'; exit 0; fi

TMP_DIR="$(mktemp -d /tmp/speedybot-update.XXXXXX)"; SOURCE_DIR="$TMP_DIR/repo"
git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$SOURCE_DIR" || fail 'git clone failed.'
CLONED_COMMIT="$(git -C "$SOURCE_DIR" rev-parse HEAD)"
if [[ "$FORCE" -ne 1 && -f "$APP_DIR/VERSION.txt" && -f "$SOURCE_DIR/VERSION.txt" ]]; then
  LOCAL_VERSION="$(grep -oE '^[0-9]+(\.[0-9]+){1,2}' "$APP_DIR/VERSION.txt" | head -1 || true)"; REMOTE_VERSION="$(grep -oE '^[0-9]+(\.[0-9]+){1,2}' "$SOURCE_DIR/VERSION.txt" | head -1 || true)"
  if [[ -n "$LOCAL_VERSION" && -n "$REMOTE_VERSION" ]]; then LOWEST="$(printf '%s\n%s\n' "$LOCAL_VERSION" "$REMOTE_VERSION" | sort -V | head -1)"; [[ "$LOWEST" != "$REMOTE_VERSION" || "$LOCAL_VERSION" == "$REMOTE_VERSION" ]] || fail "GitHub $REMOTE_VERSION is older than installed $LOCAL_VERSION."; fi
fi

info 'Validating downloaded source before downtime...'
python3 -m py_compile "$SOURCE_DIR/main.py"; [[ ! -f "$SOURCE_DIR/app.py" ]] || python3 -m py_compile "$SOURCE_DIR/app.py"; [[ ! -d "$SOURCE_DIR/speedybot_v4" ]] || python3 -m py_compile "$SOURCE_DIR"/speedybot_v4/*.py
bash -n "$SOURCE_DIR/update.sh"; [[ ! -f "$SOURCE_DIR/install.sh" ]] || bash -n "$SOURCE_DIR/install.sh"
if [[ ! -x "$APP_DIR/.venv/bin/python3" ]]; then apt-get update; apt-get install -y python3 python3-pip python3-venv; python3 -m venv "$APP_DIR/.venv"; fi
info 'Installing Python dependencies before downtime...'; "$APP_DIR/.venv/bin/python3" -m pip install --upgrade pip >/dev/null; [[ ! -f "$SOURCE_DIR/requirements.txt" ]] || "$APP_DIR/.venv/bin/python3" -m pip install -r "$SOURCE_DIR/requirements.txt"

mkdir -p "$BACKUP_DIR"; info 'Stopping bot and creating consistent backup...'; systemctl stop "$SERVICE_NAME" 2>/dev/null || true
for f in .env speedping.db speedping.db-wal speedping.db-shm .deployed_commit run.sh; do [[ ! -f "$APP_DIR/$f" ]] || cp -a "$APP_DIR/$f" "$BACKUP_DIR/$f"; done
for f in "${FILES[@]}"; do [[ ! -f "$APP_DIR/$f" ]] || cp -a "$APP_DIR/$f" "$BACKUP_DIR/$f"; done
for d in speedybot_v4 docs tests; do [[ ! -d "$APP_DIR/$d" ]] || cp -a "$APP_DIR/$d" "$BACKUP_DIR/$d"; done

rollback(){
  warn 'Deployment failed; restoring previous source/database...'; systemctl stop "$SERVICE_NAME" 2>/dev/null || true
  for f in "${FILES[@]}"; do if [[ -f "$BACKUP_DIR/$f" ]]; then cp -a "$BACKUP_DIR/$f" "$APP_DIR/$f"; else rm -f "$APP_DIR/$f"; fi; done
  for f in speedping.db speedping.db-wal speedping.db-shm .deployed_commit; do if [[ -f "$BACKUP_DIR/$f" ]]; then cp -a "$BACKUP_DIR/$f" "$APP_DIR/$f"; else [[ "$f" == speedping.db ]] || rm -f "$APP_DIR/$f"; fi; done
  for d in speedybot_v4 docs tests; do rm -rf "$APP_DIR/$d"; [[ ! -d "$BACKUP_DIR/$d" ]] || cp -a "$BACKUP_DIR/$d" "$APP_DIR/$d"; done
  write_runner; chmod +x "$APP_DIR/install.sh" "$APP_DIR/update.sh" 2>/dev/null || true; systemctl daemon-reload || true; systemctl restart "$SERVICE_NAME" || true; sleep 2; journalctl -u "$SERVICE_NAME" -n 100 --no-pager || true; fail "Rollback completed. Backup: $BACKUP_DIR"
}

info "Deploying commit $CLONED_COMMIT..."
for f in "${FILES[@]}"; do if [[ -f "$SOURCE_DIR/$f" ]]; then cp -a "$SOURCE_DIR/$f" "$APP_DIR/$f" || rollback; else rm -f "$APP_DIR/$f"; fi; done
for d in speedybot_v4 docs tests; do rm -rf "$APP_DIR/$d"; [[ ! -d "$SOURCE_DIR/$d" ]] || cp -a "$SOURCE_DIR/$d" "$APP_DIR/$d" || rollback; done
chmod +x "$APP_DIR/install.sh" "$APP_DIR/update.sh" 2>/dev/null || true; printf '%s\n' "$CLONED_COMMIT" > "$CURRENT_COMMIT_FILE"; write_runner
"$APP_DIR/.venv/bin/python3" -m py_compile "$APP_DIR/main.py" "$APP_DIR/app.py" "$APP_DIR"/speedybot_v4/*.py || rollback
systemctl daemon-reload || rollback; systemctl restart "$SERVICE_NAME" || rollback; sleep 5; systemctl is-active --quiet "$SERVICE_NAME" || rollback
ok 'SpeedyBot updated from GitHub successfully.'; ok "Commit: $CLONED_COMMIT"; ok '.env and SQLite runtime data preserved.'; info "Backup: $BACKUP_DIR"; systemctl --no-pager --full status "$SERVICE_NAME" || true
