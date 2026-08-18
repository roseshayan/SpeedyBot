#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE_NAME="xui-bot.service"
APP_DIR="/root/SpeedyBot"
ENV_FILE="$APP_DIR/.env"
RUNNER_FILE="$APP_DIR/run.sh"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED="\033[0;31m"; GREEN="\033[0;32m"; YELLOW="\033[1;33m"; BLUE="\033[0;34m"; NC="\033[0m"
info(){ printf "${BLUE}[INFO]${NC} %s\n" "$*"; }
ok(){ printf "${GREEN}[OK]${NC} %s\n" "$*"; }
warn(){ printf "${YELLOW}[WARN]${NC} %s\n" "$*" >&2; }
fail(){ printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; exit 1; }
trap 'printf "${RED}[ERROR]${NC} Installation failed at line %s.\n" "$LINENO" >&2' ERR

trim(){ local v="$1"; v="${v#"${v%%[![:space:]]*}"}"; v="${v%"${v##*[![:space:]]}"}"; printf '%s' "$v"; }
prompt(){ local p="$1" d="${2-}" v=""; while true; do if [[ -n "$d" ]]; then read -r -p "$p [$d]: " v || true; v="$(trim "${v:-$d}")"; else read -r -p "$p: " v || true; v="$(trim "${v:-}")"; fi; [[ -n "$v" ]] && { printf '%s' "$v"; return; }; warn "Value cannot be empty."; done; }
secret(){
  local p="$1" v=""
  while true; do
    printf '%s [input hidden — paste/type, then press Enter]: ' "$p" >&2
    IFS= read -r -s v || true
    printf '\n' >&2
    v="$(printf '%s' "$v" | tr -d '\n\r\t')"
    if [[ -n "$v" ]]; then
      printf "${GREEN}[OK]${NC} Secret received (%d characters).\n" "${#v}" >&2
      printf '%s' "$v"
      return
    fi
    warn "Nothing was received. Paste/type the value even though it is not shown, then press Enter."
  done
}
confirm(){ local a=""; read -r -p "$1 [y/N]: " a || true; [[ "${a,,}" =~ ^(y|yes)$ ]]; }
normalize_base_path(){ local v; v="$(trim "$1")"; [[ -z "$v" ]] && v="/"; [[ "$v" != /* ]] && v="/$v"; [[ "$v" != "/" ]] && v="${v%/}"; printf '%s' "$v"; }
normalize_sub_path(){ local v; v="$(trim "$1")"; [[ -z "$v" ]] && v="/sub/"; [[ "$v" != /* ]] && v="/$v"; [[ "$v" != */ ]] && v="$v/"; printf '%s' "$v"; }

write_runner(){
  cat > "$RUNNER_FILE" <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
source "$ENV_FILE"
exec "$APP_DIR/.venv/bin/python3" "$APP_DIR/main.py"
EOF
  chmod 700 "$RUNNER_FILE"
}

[[ "$EUID" -eq 0 ]] || fail "Run install.sh as root."
command -v apt-get >/dev/null 2>&1 || fail "apt-get was not found. Ubuntu/Debian is required."
[[ -f "$SOURCE_DIR/main.py" ]] || fail "main.py is missing next to install.sh."
[[ -d "$SOURCE_DIR/speedybot" ]] || fail "speedybot application package is missing."

printf '\n============================================================\n SpeedyBot installer\n Telegram sales + 3x-ui / Sanaei automation\n============================================================\n\n'
printf 'Note: Bot/API tokens are intentionally hidden while typing. Your paste still works; press Enter after pasting.\n\n'
while true; do
  BOT_TOKEN="$(secret "Telegram bot token")"
  if [[ "$BOT_TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]{20,}$ ]]; then
    break
  fi
  warn "Telegram bot token format looks invalid. Copy the full token from @BotFather and try again."
done
ADMIN_ID="$(prompt "Telegram admin numeric ID")"; [[ "$ADMIN_ID" =~ ^[0-9]+$ && "$ADMIN_ID" != "0" ]] || fail "Admin ID must be numeric."
XUI_API_URL="$(prompt "X-UI API base URL (scheme + host + port only)" "http://127.0.0.1:2053")"; XUI_API_URL="${XUI_API_URL%/}"; [[ "$XUI_API_URL" =~ ^https?://[^[:space:]/?#]+(:[0-9]{1,5})?$ ]] || fail "Invalid X-UI API base URL."
XUI_BASE_PATH="$(normalize_base_path "$(prompt "X-UI security base path" "/")")"
XUI_BEARER_TOKEN="$(secret "Panel Bearer API Token (plaintext value)")"
XUI_SUB_SERVER_URL="$(prompt "Subscription server base URL" "https://sub.example.com:2096")"; XUI_SUB_SERVER_URL="${XUI_SUB_SERVER_URL%/}"; [[ "$XUI_SUB_SERVER_URL" =~ ^https?://[^[:space:]/?#]+(:[0-9]{1,5})?$ ]] || fail "Invalid subscription base URL."
XUI_SUB_PATH="$(normalize_sub_path "$(prompt "Subscription URI path" "/sub/")")"

printf '\nConfiguration summary:\n  Admin ID: %s\n  API URL: %s\n  Base path: %s\n  Subscription: %s%s\n  App: %s\n\n' "$ADMIN_ID" "$XUI_API_URL" "$XUI_BASE_PATH" "$XUI_SUB_SERVER_URL" "$XUI_SUB_PATH" "$APP_DIR"
confirm "Continue installation" || { warn "Installation cancelled."; exit 0; }

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-pip python3-venv curl git ca-certificates rsync
mkdir -p "$APP_DIR"

if [[ "$SOURCE_DIR" != "$APP_DIR" ]]; then
  info "Installing the complete SpeedyBot repository..."
  rsync -a --delete \
    --exclude '.git/' \
    --exclude '.env' \
    --exclude '.venv/' \
    --exclude 'speedping.db' \
    --exclude 'speedping.db-wal' \
    --exclude 'speedping.db-shm' \
    --exclude 'backups/' \
    --exclude 'run.sh' \
    --exclude '.deployed_commit' \
    "$SOURCE_DIR/" "$APP_DIR/"
else
  info "Source is already $APP_DIR; using the repository in place."
fi
cd "$APP_DIR"

python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip setuptools wheel >/dev/null
if [[ -f requirements.txt ]]; then ./.venv/bin/python -m pip install -r requirements.txt; else ./.venv/bin/python -m pip install pyTelegramBotAPI requests 'qrcode[pil]'; fi
./.venv/bin/python -m py_compile main.py speedybot/*.py
bash -n install.sh
[[ ! -f update.sh ]] || bash -n update.sh

cat > "$ENV_FILE" <<EOF
export BOT_TOKEN=$(printf '%q' "$BOT_TOKEN")
export ADMIN_ID=$(printf '%q' "$ADMIN_ID")
export XUI_API_URL=$(printf '%q' "$XUI_API_URL")
export XUI_BASE_PATH=$(printf '%q' "$XUI_BASE_PATH")
export XUI_BEARER_TOKEN=$(printf '%q' "$XUI_BEARER_TOKEN")
export XUI_SUB_SERVER_URL=$(printf '%q' "$XUI_SUB_SERVER_URL")
export XUI_SUB_PATH=$(printf '%q' "$XUI_SUB_PATH")
EOF
chmod 600 "$ENV_FILE"

info "Testing 3x-ui API authentication (read-only)..."
set +e
PREFLIGHT="$(XUI_API_URL="$XUI_API_URL" XUI_BASE_PATH="$XUI_BASE_PATH" XUI_BEARER_TOKEN="$XUI_BEARER_TOKEN" "$APP_DIR/.venv/bin/python3" - <<'PY'
import os, requests, sys
base=os.environ['XUI_API_URL'].rstrip('/'); path=os.environ.get('XUI_BASE_PATH','').strip(); prefix='' if path in ('','/') else '/'+path.strip('/'); url=f"{base}{prefix}/panel/api/inbounds/list"
try: r=requests.get(url,headers={'Authorization':'Bearer '+os.environ['XUI_BEARER_TOKEN'],'Accept':'application/json'},timeout=15)
except Exception as e: print(f"NETWORK|{type(e).__name__}: {e}"); sys.exit(20)
print(f"HTTP_{r.status_code}|{url}|{(r.text or '').replace(chr(10),' ')[:400]}")
try: ok=r.status_code==200 and bool(r.json().get('success'))
except Exception: ok=False
if ok: sys.exit(0)
if r.status_code in (401,403): sys.exit(21)
if r.status_code==404: sys.exit(22)
sys.exit(23)
PY
)"; CODE=$?; set -e
[[ "$CODE" -eq 0 ]] || fail "3x-ui API preflight failed: $PREFLIGHT"
ok "3x-ui API preflight passed."

write_runner
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=SpeedyBot Telegram Bot
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=$RUNNER_FILE
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
sleep 4
if systemctl is-active --quiet "$SERVICE_NAME"; then
  ok "Installation completed successfully."
  systemctl --no-pager --full status "$SERVICE_NAME" || true
else
  journalctl -u "$SERVICE_NAME" -n 80 --no-pager || true
  fail "Service failed to start."
fi
